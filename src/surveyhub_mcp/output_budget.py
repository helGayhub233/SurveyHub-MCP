"""Bound public MCP payloads while preserving provider/control state."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .contracts import record_container


@dataclass(frozen=True)
class OutputPolicy:
    max_bytes: int = 65536
    max_string_chars: int = 4096

    def __post_init__(self) -> None:
        if self.max_bytes < 2048 or self.max_string_chars < 1:
            raise ValueError("Output budget must allow at least 2048 bytes and one character per string.")


DEFAULT_OUTPUT_POLICY = OutputPolicy()
_CONTROL_KEYS = {"next", "next_id", "next_cursor", "nextCursor", "pagination_id", "task_id", "query"}


def serialized_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))


def bounded_payload(payload: dict[str, Any], policy: OutputPolicy = DEFAULT_OUTPUT_POLICY) -> dict[str, Any]:
    """Clip data fields/record prefixes; never advance past locally omitted records."""
    result = deepcopy(payload)
    fields_truncated = 0

    def clip(value: Any, key: str = "") -> Any:
        nonlocal fields_truncated
        if isinstance(value, str) and key not in _CONTROL_KEYS and len(value) > policy.max_string_chars:
            fields_truncated += 1
            return value[:policy.max_string_chars] + "… [truncated]"
        if isinstance(value, list):
            return [clip(item) for item in value]
        if isinstance(value, dict):
            return {name: clip(item, name) for name, item in value.items()}
        return value

    result["data"] = clip(result.get("data"))
    if "text" in result:
        result["text"] = clip(result["text"])
    container = record_container(result.get("data"))
    received_count = len(container[0]) if container is not None else 0
    if not fields_truncated and serialized_size(result) <= policy.max_bytes:
        return payload

    output = {
        "max_bytes": policy.max_bytes,
        "max_string_chars": policy.max_string_chars,
        "received_count": received_count,
        "omitted_records": 0,
        "truncated_fields": fields_truncated,
    }
    result.setdefault("meta", {})["output"] = output
    warning = {
        "type": "output_truncated",
        "message": (
            "The provider response exceeded the MCP output budget. Narrow fields/query or reduce page size "
            "before continuing; advancing pages can skip locally omitted records. "
            "A successful provider request may already have consumed quota."
        ),
    }
    result.setdefault("warnings", []).append(warning)
    if result.get("ok"):
        result.update(truncated=True, completeness="partial", next_action="refine_query")
        execution = result["meta"].get("execution")
        if isinstance(execution, dict):
            execution["completeness"] = {"state": "partial", "reason": "local_output_budget"}

    def retain(count: int) -> None:
        if container is None:
            return
        records, path = container
        if not path:
            result["data"] = records[:count]
        else:
            parent = result["data"]
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = records[:count]
        result["returned_count"] = count
        output["omitted_records"] = received_count - count

    if container is not None and serialized_size(result) > policy.max_bytes:
        low, high = 0, received_count
        while low < high:
            middle = (low + high + 1) // 2
            retain(middle)
            if serialized_size(result) <= policy.max_bytes:
                low = middle
            else:
                high = middle - 1
        retain(low)

    if serialized_size(result) > policy.max_bytes:
        # A giant scalar/object or metadata can exceed the budget even with no records.
        result["data"] = None
        result.pop("text", None)
        result["returned_count"] = 0
        output["omitted_records"] = received_count
        result["warnings"] = [warning]
        result["meta"] = {"output": output, **{
            key: value for key, value in result["meta"].items() if key == "execution"
        }}
        if result.get("error"):
            result["error"] = {
                "type": result["error"]["type"],
                "message": result["error"]["message"][:512],
            }
        if serialized_size(result) > policy.max_bytes:
            result.pop("pagination", None)
            result["meta"].pop("execution", None)
        if serialized_size(result) > policy.max_bytes:
            result = {
                "ok": bool(payload["ok"]), "platform": str(payload["platform"])[:128],
                "returned_count": 0, "truncated": bool(payload["ok"]),
                "completeness": "partial" if payload["ok"] else "unknown",
                "next_action": "refine_query" if payload["ok"] else "stop",
                "meta": {"output": output}, "warnings": [warning],
            }
            if not payload["ok"]:
                result["error"] = {"type": "output_budget", "message": "Provider failure details exceeded the output budget; inspect the provider account before retrying."}
    return result
