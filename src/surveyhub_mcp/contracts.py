"""Provider response semantics independent of HTTP and MCP transports."""

from __future__ import annotations

from typing import Any


SUCCESS_CODES = {
    "Quake": 0,
    "Hunter Personal": 200,
    "Hunter Enterprise": 200,
    "ZoomEye": 60000,
    "DayDayMap": 200,
}
DAYDAYMAP_ERRORS = {
    2001: ("authentication_error", "Check CN_DAYDAYMAP_API_KEY."),
    2002: ("validation_error", "Correct the query or parameters using the DayDayMap reference."),
    2003: ("permission_denied", "Check the account's membership permissions."),
    2004: ("insufficient_credits", "Check or replenish the account's points before searching."),
    2005: ("pagination_limit", "Narrow the query; only the first 10,000 results are accessible."),
    2006: ("provider_error", "Check provider status before retrying the request."),
}
QUAKE_STRING_ERRORS = {
    # Observed live: {"code":"q2001","message":"筛选字段传参错误: [...],
    # 请调用可筛选字段接口查看可筛选字段"} when include/exclude carry
    # fields the account is not allowed to filter on.
    "q2001": (
        "validation_error",
        "Correct include/exclude fields using the Quake filterable-fields reference.",
    ),
}


def integer_code(value: Any) -> int | None:
    """Accept documented numeric codes without treating booleans as integers."""
    if type(value) is int:
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def business_code(value: Any) -> int | str | None:
    """Accept documented numeric codes plus provider string status codes.

    Quake reports some business errors with string codes such as "q2001"
    (rejected include/exclude fields). Treating those as a missing status
    turned a clear provider error into invalid_response and dropped the real
    error message.
    """
    if type(value) is int:
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.lstrip("-").isdigit():
            return int(stripped)
        return stripped
    return None


def provider_error(platform: str, body: Any) -> dict[str, Any] | None:
    """Recognize only documented provider error flags/codes, not arbitrary data."""
    if platform != "FOFA" and platform not in SUCCESS_CODES:
        return None
    code = business_code(body.get("code")) if isinstance(body, dict) else None
    invalid = not isinstance(body, dict) or (
        type(body.get("error")) is not bool if platform == "FOFA" else code is None
    )
    if invalid:
        return {
            "type": "invalid_response",
            "message": f"{platform} did not return its documented business status. Execution and quota use are unknown; inspect provider status before replaying the request.",
        }
    if platform == "FOFA":
        failed = body.get("error") is True
    else:
        failed = platform in SUCCESS_CODES and code is not None and code != SUCCESS_CODES[platform]
    if not failed:
        return None

    message = str(body.get("errmsg") or body.get("message") or body.get("msg") or "Provider rejected the request.")
    error_type, guidance = {
        400: ("validation_error", "Correct the query or parameters using the platform reference."),
        401: ("authentication_error", "Check the configured credential and account edition."),
        403: ("permission_denied", "Check the account's permissions and remaining quota."),
        429: ("rate_limit", "Wait for the provider cooldown before retrying."),
    }.get(code, ("provider_error", "Consult the platform API reference and correct the reported error before retrying."))
    if platform == "DayDayMap":
        error_type, guidance = DAYDAYMAP_ERRORS.get(code, (error_type, guidance))
    elif platform == "Quake" and isinstance(code, str):
        error_type, guidance = QUAKE_STRING_ERRORS.get(code, (error_type, guidance))
    result: dict[str, Any] = {
        "type": error_type,
        "message": f"{platform}: {message} {guidance}",
        "details": {"provider_message": message, "guidance": guidance},
    }
    if isinstance(code, int):
        result["status_code"] = code
        result["details"]["provider_code"] = code
    elif code is not None:
        result["details"]["provider_code"] = code
    return result


def record_container(value: Any, path: tuple[str, ...] = ()) -> tuple[list[Any], tuple[str, ...]] | None:
    """Locate a documented/common record container, preserving empty arrays."""
    if isinstance(value, list):
        return value, path
    if isinstance(value, dict):
        for key in ("results", "items", "records", "list", "arr", "data"):
            child = value.get(key)
            if isinstance(child, (list, dict)):
                found = record_container(child, (*path, key))
                if found is not None:
                    return found
    return None


def pagination_mappings(*values: Any) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    queue = [value for value in values if isinstance(value, dict)]
    while queue:
        current = queue.pop(0)
        mappings.append(current)
        for key in ("data", "meta", "pagination", "page"):
            child = current.get(key)
            if isinstance(child, dict):
                queue.append(child)
    return mappings


def pagination_info(platform: str, body: Any, meta: dict[str, Any], count: int) -> dict[str, Any]:
    """Expose exact totals and reusable cursors without guessing from page length."""
    info: dict[str, Any] = {}
    offset = meta.get("result_offset", None if meta.get("offset_known") is False else 0)
    if type(offset) is int and offset >= 0:
        info["offset"] = offset
    more_signals: list[bool] = []
    totals: list[tuple[int, str]] = []
    for candidate in pagination_mappings(body):
        for key in ("has_more", "hasMore", "has_next", "hasNextPage"):
            if isinstance(candidate.get(key), bool):
                more_signals.append(candidate[key])
        for key in ("total", "total_count", "totalCount"):
            total = candidate.get(key)
            relation = "eq"
            if isinstance(total, dict):
                relation = total.get("relation", "unknown")
                if relation not in {"eq", "gte"}:
                    relation = "unknown"
                total = total.get("value")
            if type(total) is int and total >= 0:
                totals.append((total, relation))
        # FOFA's size is a total only in its search response, not a generic page size.
        if platform == "FOFA" and isinstance(candidate.get("results"), list):
            total = candidate.get("size")
            if type(total) is int and total >= 0:
                totals.append((total, "eq"))
        for key in ("next", "pagination_id", "next_cursor", "nextCursor"):
            cursor = candidate.get(key)
            if isinstance(cursor, str) and cursor:
                info["next_cursor"] = cursor
                info["cursor_parameter"] = "next_id" if platform == "FOFA" else key
            # A Quake pagination_id is a session handle, not proof of another page.
            if platform == "FOFA" and key == "next" and key in candidate:
                more_signals.append(bool(cursor))

    if totals:
        total, relation = max(totals, key=lambda item: item[0])
        info.update(total=total, total_relation=relation)
        if "offset" in info:
            end = info["offset"] + count
            if total > end:
                more_signals.append(True)
            elif relation == "eq":
                more_signals.append(False)
    if more_signals:
        # Contradictory evidence must never produce a false claim of completeness.
        info["has_more"] = any(more_signals)
    if info.get("has_more") is True:
        if type(meta.get("page")) is int:
            info["next_page"] = meta["page"] + 1
        elif meta.get("pagination_mode") == "offset" and "offset" in info:
            info["next_offset"] = info["offset"] + count
    return info
