"""Shared helpers for all SurveyHub-MCP platform tools."""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import json
import logging
import os
import random
import sqlite3
import time
import uuid
from contextlib import closing
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, Union

import httpx
from mcp.server import MCPServer
from mcp.types import (
    CallToolResult,
    EmptyResult,
    LoggingMessageNotification,
    LoggingMessageNotificationParams,
    SetLevelRequestParams,
    TextContent,
    ToolAnnotations,
)
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypeAliasType

READ_ONLY_REMOTE_TOOL = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
METERED_READ_ONLY_REMOTE_TOOL = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    # A search does not mutate provider data, but replaying it can consume quota.
    idempotent_hint=False,
    open_world_hint=True,
)
MUTATING_REMOTE_TOOL = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
LOCAL_FILE_WRITE_TOOL = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)

_LOGGER = logging.getLogger(__name__)
_LOG_LEVELS = ("debug", "info", "notice", "warning", "error", "critical", "alert", "emergency")
_LOG_LEVEL_STATE_KEY = "surveyhub.logging.level"


@dataclass
class _MCPExecutionState:
    """Request-scoped MCP notification state shared by nested provider calls."""

    context: Any
    progress: float = 0


_CURRENT_MCP_EXECUTION: ContextVar[_MCPExecutionState | None] = ContextVar(
    "surveyhub_mcp_execution",
    default=None,
)


async def _execution_context_middleware(context: Any, call_next: Any) -> Any:
    """Expose the current tool request to the provider execution pipeline."""
    if context.method != "tools/call":
        return await call_next(context)
    token = _CURRENT_MCP_EXECUTION.set(_MCPExecutionState(context=context))
    try:
        return await call_next(context)
    finally:
        _CURRENT_MCP_EXECUTION.reset(token)


def _connection_for(context: Any) -> Any | None:
    """Return SDK connection state without exposing it in public tool schemas."""
    return getattr(context.session, "_connection", None)


def _log_level_enabled(context: Any, level: str) -> bool:
    """Apply legacy connection-level or modern request-level log filtering."""
    session = context.session
    if session.protocol_version >= "2026-07-28":
        return level in getattr(session, "_allowed_log_levels", ())
    connection = _connection_for(context)
    configured = connection.state.get(_LOG_LEVEL_STATE_KEY, "warning") if connection else "warning"
    try:
        return _LOG_LEVELS.index(level) >= _LOG_LEVELS.index(configured)
    except ValueError:
        return level in {"warning", "error", "critical", "alert", "emergency"}


class ExecutionReporter:
    """Emit best-effort progress and credential-safe structured MCP logs."""

    def __init__(self, *, platform: str, request_id: str) -> None:
        self.platform = platform
        self.request_id = request_id

    async def event(
        self,
        event: str,
        message: str,
        *,
        level: str = "info",
        report_progress: bool = True,
        **details: Any,
    ) -> None:
        state = _CURRENT_MCP_EXECUTION.get()
        if state is None:
            return
        context = state.context
        if report_progress:
            state.progress += 1
            try:
                await context.session.report_progress(state.progress, message=message)
            except Exception as error:  # Notifications must never fail the provider operation.
                _LOGGER.debug("Unable to publish MCP progress: %s", error)

        if not _log_level_enabled(context, level):
            return
        payload = {
            "event": event,
            "platform": self.platform,
            "request_id": self.request_id,
            **details,
        }
        try:
            await context.session.send_notification(
                LoggingMessageNotification(
                    params=LoggingMessageNotificationParams(
                        level=level,
                        data=payload,
                        logger="surveyhub.execution",
                    )
                ),
                related_request_id=context.request_id,
            )
        except Exception as error:  # Logging must remain observational.
            _LOGGER.debug("Unable to publish structured MCP log: %s", error)


class SurveyHubError(BaseModel):
    """Normalized error details returned by every SurveyHub provider."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Stable machine-readable error category.")
    message: str = Field(description="Human-readable error and recovery guidance.")
    status_code: int | None = Field(default=None, description="HTTP or provider status code, when available.")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Provider-specific diagnostic details that do not contain credentials.",
    )


class SurveyHubDownload(BaseModel):
    """Metadata for a provider export saved to local disk."""

    bytes: int = Field(ge=0, description="Number of bytes written.")
    path: str = Field(description="Expanded local path of the saved export.")


class SurveyHubWarning(BaseModel):
    """Non-fatal provider or compatibility warning."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Stable machine-readable warning category.")
    message: str = Field(description="Human-readable warning and its effect on the result.")
    details: dict[str, Any] | None = Field(default=None, description="Additional warning context.")


class SurveyHubRetryDecision(BaseModel):
    """Whether replaying the effective provider request is safe."""

    safety: Literal["safe", "conditional", "unsafe"]
    recommended: bool
    reason: str


class SurveyHubQuotaRisk(BaseModel):
    """Possible provider quota effect of the observed attempts."""

    risk: Literal["none", "possible_duplicate", "unknown"]
    charged_attempts: int | Literal["unknown"]


class SurveyHubCompleteness(BaseModel):
    """Whether the returned asset set can be treated as complete."""

    state: Literal["complete", "partial", "unknown"]
    reason: str


class SurveyHubExecution(BaseModel):
    """Machine-readable execution receipt used by agents to avoid unsafe retries."""

    request_id: str
    fingerprint: str | None = None
    duplicate_of: str | None = None
    cache_hit: bool = False
    final_state: Literal["confirmed_success", "confirmed_failure", "indeterminate"]
    transport_state: Literal["not_sent", "possibly_sent", "response_received"]
    attempts: int = Field(ge=0)
    timeout_phase: Literal["pool", "connect", "write", "read", "unknown"] | None = None
    retry: SurveyHubRetryDecision
    quota: SurveyHubQuotaRisk
    completeness: SurveyHubCompleteness


class SurveyHubMeta(BaseModel):
    """Execution metadata added by the MCP wrapper."""

    model_config = ConfigDict(extra="allow")

    original_query: str | None = Field(default=None, description="Query supplied by the caller.")
    executed_query: str | None = Field(default=None, description="Query sent to the provider.")
    attempts: int | None = Field(
        default=None,
        ge=0,
        description="HTTP attempts used by this invocation; 0 means a recent identical response was reused.",
    )
    partial_data: bool | None = Field(default=None, description="Whether provider warnings indicate incomplete data.")
    execution: SurveyHubExecution | None = Field(
        default=None,
        description=(
            "Machine-readable transport, retry-safety, quota-risk, and completeness receipt. "
            "Treat final_state=indeterminate as unknown rather than an empty result."
        ),
    )


JSONValue = TypeAliasType(
    "JSONValue",
    Union[dict[str, "JSONValue"], list["JSONValue"], str, int, float, bool, None],
)


class SurveyHubResponse(BaseModel):
    """Unified success, error, and download envelope for SurveyHub tools."""

    model_config = ConfigDict(extra="forbid")

    ok: bool = Field(description="Whether the tool operation succeeded.")
    platform: str = Field(description="Provider that handled the operation.")
    data: JSONValue = Field(default=None, description="Provider JSON response for successful API calls.")
    text: str | None = Field(default=None, description="Provider text response when JSON is unavailable.")
    error: SurveyHubError | None = Field(default=None, description="Normalized failure details.")
    download: SurveyHubDownload | None = Field(default=None, description="Local export metadata.")
    warnings: list[SurveyHubWarning] | None = Field(default=None, description="Non-fatal provider or wrapper warnings.")
    meta: SurveyHubMeta | None = Field(default=None, description="MCP execution metadata.")
    returned_count: int = Field(default=0, ge=0, description="Number of records returned in this page when detectable.")
    truncated: bool = Field(default=False, description="Whether the result is known to be partial or has more pages.")
    completeness: Literal["complete", "partial", "unknown"] = Field(default="unknown", description="Whether the returned result is complete, partial, or unknown.")
    next_action: Literal["stop", "call_next_page", "unknown"] = Field(default="unknown", description="Recommended continuation action; do not reconstruct results with a local script.")


StructuredToolResult = Annotated[CallToolResult, SurveyHubResponse]


def validated_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and serialize the unified public response envelope."""
    enriched = dict(payload)
    returned = _count_result_records(enriched.get("data"))
    execution = enriched.get("meta", {}).get("execution", {}) if isinstance(enriched.get("meta"), dict) else {}
    execution_completeness = execution.get("completeness", {}) if isinstance(execution, dict) else {}
    state = execution_completeness.get("state") if isinstance(execution_completeness, dict) else None
    if state not in {"complete", "partial", "unknown"}:
        state = "unknown"
    # Promote provider pagination signals into the stable MCP envelope. This
    # prevents the model from guessing whether another page is required.
    # Transport success is not proof that a dataset is exhausted.
    if state == "complete":
        state = "unknown"
    offset = enriched.get("meta", {}).get("result_offset", 0) if isinstance(enriched.get("meta"), dict) else 0
    provider_has_more: bool | None = None
    provider_total: int | None = None
    for candidate in _pagination_mappings(enriched.get("data"), enriched.get("meta")):
        if not isinstance(candidate, dict):
            continue
        for key in ("has_more", "hasMore", "has_next", "hasNextPage"):
            if isinstance(candidate.get(key), bool):
                provider_has_more = candidate[key]
                break
        for key in ("total", "total_count", "totalCount"):
            if type(candidate.get(key)) is int and candidate[key] >= 0:
                provider_total = candidate[key]
                break
    truncated = state == "partial" or provider_has_more is True or (
        provider_total is not None and provider_total > offset + returned
    )
    if provider_has_more is False and not truncated:
        state = "complete"
    elif provider_total is not None and provider_total <= offset + returned and not truncated:
        state = "complete"
    elif truncated:
        state = "partial"
    failed = enriched.get("ok") is False
    if failed:
        state, truncated = "unknown", False
    enriched.update(
        {
            "returned_count": returned,
            "truncated": truncated,
            "completeness": state,
            "next_action": "stop" if failed else ("call_next_page" if truncated else ("stop" if state == "complete" else "unknown")),
        }
    )
    return SurveyHubResponse.model_validate(enriched).model_dump(exclude_none=True)


def _pagination_mappings(*values: Any) -> list[dict[str, Any]]:
    """Return shallow/nested mappings that commonly carry page metadata."""
    mappings: list[dict[str, Any]] = []
    queue = [value for value in values if isinstance(value, dict)]
    seen: set[int] = set()
    while queue:
        current = queue.pop(0)
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        mappings.append(current)
        for key in ("data", "meta", "pagination", "page"):
            child = current.get(key)
            if isinstance(child, dict):
                queue.append(child)
    return mappings


def _count_result_records(value: Any) -> int:
    """Best-effort count for common provider result containers."""
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("results", "items", "records", "list", "data"):
            child = value.get(key)
            if isinstance(child, list):
                return len(child)
            if isinstance(child, dict):
                count = _count_result_records(child)
                if count:
                    return count
    return 0


def enrich_payload(
    payload: dict[str, Any],
    *,
    meta: dict[str, Any] | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge execution metadata and non-fatal warnings into a response."""
    enriched = dict(payload)
    if meta:
        enriched["meta"] = {**enriched.get("meta", {}), **meta}
    if warnings:
        enriched["warnings"] = [*enriched.get("warnings", []), *warnings]
    return validated_payload(enriched)


class SurveyHubMCPServer(MCPServer):
    """MCP server that advertises the unified Pydantic output contract."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.middleware.append(_execution_context_middleware)

        async def set_logging_level(context: Any, params: SetLevelRequestParams) -> EmptyResult:
            connection = _connection_for(context)
            if connection is not None:
                connection.state[_LOG_LEVEL_STATE_KEY] = params.level
            return EmptyResult()

        # MCPServer has no high-level decorator for the legacy logging method.
        # Registering this typed handler also advertises logging capability.
        self._lowlevel_server.add_request_handler(
            "logging/setLevel",
            SetLevelRequestParams,
            set_logging_level,
        )

    async def list_tools(self):
        tools = await super().list_tools()
        output_schema = SurveyHubResponse.model_json_schema(mode="serialization")
        return [tool.model_copy(update={"output_schema": output_schema}) for tool in tools]


@dataclass(frozen=True)
class HttpPolicy:
    attempt_timeout: float = 15.0
    total_timeout: float = 45.0
    max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_delay_cap: float = 5.0


@dataclass(frozen=True)
class RateLimitPolicy:
    queue_timeout: float = 15.0
    max_inline_cooldown: float = 10.0
    max_provider_cooldown: float = 120.0


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 3
    recovery_timeout: float = 15.0
    failure_statuses: frozenset[int] = frozenset({408, 500, 502, 503, 504})


DEFAULT_HTTP_POLICY = HttpPolicy()
DEFAULT_RATE_LIMIT_POLICY = RateLimitPolicy()
DEFAULT_CIRCUIT_BREAKER_POLICY = CircuitBreakerPolicy()


class AsyncRateLimiter:
    """Serialize calls and share provider cooldowns across concurrent requests."""

    def __init__(
        self,
        min_interval: float,
        *,
        policy: RateLimitPolicy = DEFAULT_RATE_LIMIT_POLICY,
        namespace: str | None = None,
        identity_provider: Callable[[], str | None] | None = None,
    ) -> None:
        self._min_interval = min_interval
        self._policy = policy
        self._last_started_at = 0.0
        self._cooldown_until = 0.0
        self._condition = asyncio.Condition()
        self._coordinator = SQLiteRateLimitCoordinator(namespace, policy=policy) if namespace else None
        self._identity_provider = identity_provider

    async def wait(self) -> None:
        queue_deadline = time.monotonic() + self._policy.queue_timeout
        async with self._condition:
            while True:
                now = time.monotonic()
                next_allowed_at = max(self._last_started_at + self._min_interval, self._cooldown_until)
                wait_seconds = next_allowed_at - now
                cooldown_wait = max(0.0, self._cooldown_until - now)
                if cooldown_wait > self._policy.max_inline_cooldown:
                    raise ProviderCooldownActive(cooldown_wait)
                if wait_seconds <= 0:
                    self._last_started_at = now
                    self._condition.notify_all()
                    break
                # Provider-directed cooldown does not consume the local queue budget.
                effective_deadline = max(queue_deadline, self._cooldown_until + self._policy.queue_timeout)
                remaining = effective_deadline - now
                if remaining <= 0:
                    raise RateLimitQueueTimeout(self._policy.queue_timeout)
                try:
                    await asyncio.wait_for(self._condition.wait(), timeout=min(wait_seconds, remaining))
                except asyncio.TimeoutError:
                    pass

        identity = self._identity_provider() if self._identity_provider else None
        if self._coordinator and identity:
            while True:
                delay = await asyncio.to_thread(
                    self._coordinator.reserve,
                    identity,
                    self._min_interval,
                    self._policy.queue_timeout,
                )
                if delay > self._policy.max_inline_cooldown:
                    raise ProviderCooldownActive(delay)
                if delay <= 0:
                    break
                await asyncio.sleep(delay)

    async def defer(self, delay: float) -> None:
        """Publish a provider cooldown that all waiting requests must observe."""
        identity = self._identity_provider() if self._identity_provider else None
        if self._coordinator and identity:
            await asyncio.to_thread(self._coordinator.defer, identity, delay)
        async with self._condition:
            now = time.monotonic()
            self._cooldown_until = max(self._cooldown_until, now + max(0.0, delay))
            self._condition.notify_all()


class RateLimitQueueTimeout(Exception):
    """Raised when a request waits too long behind a provider rate limiter."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(f"rate-limit queue wait exceeded {timeout:g} seconds")


class ProviderCooldownActive(Exception):
    """Raised instead of blocking an interactive MCP call for a long cooldown."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"provider cooldown active for {retry_after:g} seconds")


class TotalRequestTimeout(Exception):
    """Raised when an MCP tool exhausts its end-to-end HTTP time budget."""


class SQLiteRateLimitCoordinator:
    """Coordinate rate-limit reservations between processes on one machine."""

    def __init__(
        self,
        namespace: str,
        state_dir: Path | None = None,
        *,
        policy: RateLimitPolicy = DEFAULT_RATE_LIMIT_POLICY,
    ) -> None:
        self._namespace = namespace
        self._state_dir = state_dir or _rate_limit_state_dir()
        self._database_path = self._state_dir / "rate-limits.sqlite3"
        self._policy = policy

    def reserve(self, identity: str, min_interval: float, queue_timeout: float) -> float:
        now = time.time()

        def update(state: tuple[float, float] | None) -> tuple[float, float, float]:
            next_allowed_at, cooldown_until = state or (0.0, 0.0)
            cooldown_until = _bounded_timestamp(cooldown_until, now, self._policy)
            next_allowed_at = _bounded_timestamp(next_allowed_at, now, self._policy)
            reserved_at = max(now, cooldown_until, next_allowed_at)
            delay = reserved_at - now
            cooldown_delay = max(0.0, cooldown_until - now)
            if delay > cooldown_delay + queue_timeout:
                raise RateLimitQueueTimeout(queue_timeout)
            if delay > 0:
                return next_allowed_at, cooldown_until, delay
            return now + min_interval, cooldown_until, 0.0

        return self._update(identity, update)

    def defer(self, identity: str, delay: float) -> None:
        now = time.time()
        bounded_delay = min(self._policy.max_provider_cooldown, max(0.0, delay))

        def update(state: tuple[float, float] | None) -> tuple[float, float, None]:
            next_allowed_at, cooldown_until = state or (0.0, 0.0)
            return (
                _bounded_timestamp(next_allowed_at, now, self._policy),
                max(_bounded_timestamp(cooldown_until, now, self._policy), now + bounded_delay),
                None,
            )

        self._update(identity, update)

    @property
    def database_path(self) -> Path:
        return self._database_path

    def identity_hash(self, identity: str) -> str:
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def _update(
        self,
        identity: str,
        updater: Callable[[tuple[float, float] | None], tuple[float, float, Any]],
    ) -> Any:
        # POSIX 0700 intentionally restricts the state directory to its owner.
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions
        os.chmod(self._state_dir, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions
        database_descriptor = os.open(self._database_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(database_descriptor)
        key_hash = self.identity_hash(identity)
        with sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None) as connection:
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limit_state (
                    namespace TEXT NOT NULL,
                    identity_hash TEXT NOT NULL,
                    next_allowed_at REAL NOT NULL,
                    cooldown_until REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (namespace, identity_hash)
                )
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT next_allowed_at, cooldown_until
                FROM rate_limit_state
                WHERE namespace = ? AND identity_hash = ?
                """,
                (self._namespace, key_hash),
            ).fetchone()
            next_allowed_at, cooldown_until, result = updater(row)
            connection.execute(
                """
                INSERT INTO rate_limit_state (
                    namespace, identity_hash, next_allowed_at, cooldown_until, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(namespace, identity_hash) DO UPDATE SET
                    next_allowed_at = excluded.next_allowed_at,
                    cooldown_until = excluded.cooldown_until,
                    updated_at = excluded.updated_at
                """,
                (self._namespace, key_hash, next_allowed_at, cooldown_until, time.time()),
            )
            connection.execute(
                "DELETE FROM rate_limit_state WHERE updated_at < ?",
                (time.time() - 86400.0,),
            )
            connection.commit()
        os.chmod(self._database_path, 0o600)
        return result


def _rate_limit_state_dir() -> Path:
    configured = os.getenv("SURVEYHUB_STATE_DIR")
    if configured:
        return Path(configured).expanduser() / "rate-limits"
    cache_home = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "surveyhub-mcp" / "rate-limits"


def _bounded_timestamp(value: Any, now: float, policy: RateLimitPolicy = DEFAULT_RATE_LIMIT_POLICY) -> float:
    if not isinstance(value, (int, float)):
        return 0.0
    maximum = policy.max_provider_cooldown + policy.queue_timeout
    return min(max(0.0, float(value)), now + maximum)


class AsyncCircuitBreaker:
    """Track provider health and temporarily block repeated failing calls."""

    def __init__(self, *, failure_threshold: int, recovery_timeout: float) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._opened_until = 0.0
        self._half_open_in_flight = False
        self._lock = asyncio.Lock()

    async def allow_request(self) -> tuple[bool, float]:
        async with self._lock:
            now = time.monotonic()
            if self._opened_until <= now:
                if self._opened_until:
                    if self._half_open_in_flight:
                        return False, 0.0
                    self._half_open_in_flight = True
                return True, 0.0

            return False, self._opened_until - now

    async def record_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            self._opened_until = 0.0
            self._half_open_in_flight = False

    async def record_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._half_open_in_flight = False
            if self._failure_count >= self._failure_threshold:
                self._opened_until = time.monotonic() + self._recovery_timeout

    async def record_neutral(self) -> None:
        """Release a half-open probe without treating rate limiting as health failure."""
        async with self._lock:
            self._half_open_in_flight = False


_CIRCUIT_BREAKERS: dict[str, AsyncCircuitBreaker] = {}
_METERED_RESPONSE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
METERED_RESPONSE_CACHE_TTL = 60.0


def _circuit_breaker_for(platform: str) -> AsyncCircuitBreaker:
    breaker = _CIRCUIT_BREAKERS.get(platform)
    if breaker is None:
        breaker = AsyncCircuitBreaker(
            failure_threshold=DEFAULT_CIRCUIT_BREAKER_POLICY.failure_threshold,
            recovery_timeout=DEFAULT_CIRCUIT_BREAKER_POLICY.recovery_timeout,
        )
        _CIRCUIT_BREAKERS[platform] = breaker
    return breaker


def _circuit_open_message(platform: str, retry_after: float) -> str:
    return (
        f"{platform} API is temporarily unavailable because recent requests failed. "
        f"Retry after {max(1, int(retry_after))} seconds."
    )


def _cap_retry_delay(
    delay: float,
    *,
    server_provided: bool = False,
    http_policy: HttpPolicy = DEFAULT_HTTP_POLICY,
    rate_limit_policy: RateLimitPolicy = DEFAULT_RATE_LIMIT_POLICY,
) -> float:
    maximum = rate_limit_policy.max_provider_cooldown if server_provided else http_policy.retry_delay_cap
    return min(maximum, max(0.0, delay))


def encode_base64(text: str) -> str:
    """Encode text with standard Base64."""
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def encode_base64_url(text: str) -> str:
    """Encode text with URL-safe Base64."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


HUNTER_EXACT_SEARCH_EXCLUDED_FIELDS = {
    # Date range fields always use single = per Hunter syntax.
    "after", "before",
    # Text-search fields where Hunter's = already means "contains".
    # Converting these to == would silently shrink results to exact-only matches.
    "web.title",        # Search within website titles.
    "web.body",         # Search within website body text.
    "domain",           # Search within domain names.
    "header",           # Search within HTTP response headers.
    "protocol.banner",  # Search within service banners.
    "cert",             # Search within certificate content.
    "cert.subject",     # Search within certificate subjects.
    "icp.web_name",     # Search within registered website names.
    "icp.name",         # Search within registered organization names.
    "domain.cname",     # Search within CNAME values.
    "ip.tag",           # Search within IP tags.
    "web.tag",          # Search within asset tags.
    "web.similar",      # Perform similarity search rather than equality matching.
    "web.similar_id",   # Perform similarity search rather than equality matching.
}


def normalize_hunter_query(query: str, *, exact_search: bool = True) -> str:
    """Convert Hunter contains comparisons to exact comparisons by default.

    Callers can explicitly set exact_search=False when Hunter's native
    field="value" contains semantics are required.
    """
    if not exact_search:
        return query

    def quoted_end(start: int) -> int:
        index = start + 1
        while index < len(query):
            if query[index] == "\\":
                index += 2
                continue
            if query[index] == '"':
                return index + 1
            index += 1
        return len(query)

    output: list[str] = []
    index = 0
    while index < len(query):
        char = query[index]
        if char == '"':
            end = quoted_end(index)
            output.append(query[index:end])
            index = end
            continue
        if not ("A" <= char <= "Z" or "a" <= char <= "z"):
            output.append(char)
            index += 1
            continue

        field_end = index + 1
        while field_end < len(query):
            candidate = query[field_end]
            if candidate.isalnum() or candidate in "_.-":
                field_end += 1
                continue
            break

        field = query[index:field_end]
        operator = field_end
        while operator < len(query) and query[operator].isspace():
            operator += 1
        value_start = operator + 1
        while value_start < len(query) and query[value_start].isspace():
            value_start += 1

        is_contains_comparison = (
            operator < len(query)
            and query[operator] == "="
            and (operator + 1 >= len(query) or query[operator + 1] != "=")
            and value_start < len(query)
            and query[value_start] == '"'
        )
        if not is_contains_comparison:
            output.append(field)
            index = field_end
            continue

        value_end = quoted_end(value_start)
        output.append(field)
        output.append(query[field_end:operator])
        output.append("=" if field in HUNTER_EXACT_SEARCH_EXCLUDED_FIELDS else "==")
        output.append(query[operator + 1:value_end])
        index = value_end

    return "".join(output)


def split_csv(value: str | None) -> list[str] | None:
    """Split a comma-separated string into a clean list."""
    if not value:
        return None

    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def validate_batch_csv_file(
    file_path: str,
    *,
    platform: str,
    search_type: str,
    max_input_rows: int,
    provider_max_rows: int,
    max_file_bytes: int = 5 * 1024 * 1024,
) -> tuple[Path | None, dict[str, Any] | None]:
    """Validate a Hunter CSV locally before a potentially large remote batch call."""
    if max_input_rows < 1 or provider_max_rows < 1:
        return None, error_payload(
            platform=platform,
            message="Batch row limits must be positive integers.",
            error_type="validation_error",
            details={
                "max_input_rows": max_input_rows,
                "provider_max_rows": provider_max_rows,
            },
        )
    path = Path(file_path).expanduser()
    if not path.is_file():
        return None, error_payload(
            platform=platform,
            message=f"File not found: {path}",
            error_type="file_not_found",
            details={"path": str(path)},
        )
    file_bytes = path.stat().st_size
    if file_bytes > max_file_bytes:
        return None, error_payload(
            platform=platform,
            message="Batch CSV exceeds the 5 MiB MCP upload limit; split it into bounded batches.",
            error_type="batch_budget_exceeded",
            details={"path": str(path), "file_bytes": file_bytes, "max_file_bytes": max_file_bytes},
        )

    nonempty_rows: list[list[str]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            for row in csv.reader(file_obj):
                if any(cell.strip() for cell in row):
                    nonempty_rows.append(row)
                    if len(nonempty_rows) > min(max_input_rows, provider_max_rows) + 1:
                        break
    except (OSError, UnicodeError, csv.Error) as error:
        return None, error_payload(
            platform=platform,
            message=f"Unable to read batch CSV: {error}",
            error_type="invalid_batch_file",
            details={"path": str(path)},
        )

    header_names = {"ip", "domain", "company", "target", "query", "search", "value"}
    has_header = bool(nonempty_rows) and any(
        cell.strip().lower() in header_names for cell in nonempty_rows[0]
    )
    row_count = max(0, len(nonempty_rows) - int(has_header))
    if row_count == 0:
        return None, error_payload(
            platform=platform,
            message="Batch CSV contains no input rows.",
            error_type="invalid_batch_file",
            details={"path": str(path)},
        )
    effective_limit = min(max_input_rows, provider_max_rows)
    if row_count > effective_limit:
        return None, error_payload(
            platform=platform,
            message=(
                f"Batch CSV has more than {effective_limit} input rows. Split the file or, "
                "when the user explicitly requested a larger enterprise batch, increase max_input_rows."
            ),
            error_type="batch_budget_exceeded",
            details={
                "path": str(path),
                "detected_rows_at_least": row_count,
                "max_input_rows": max_input_rows,
                "provider_max_rows": provider_max_rows,
                "search_type": search_type,
            },
        )
    return path, None


def render_json(data: Any) -> str:
    """Render API data as readable JSON text for MCP clients."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def mcp_tool_result(payload: dict[str, Any]) -> CallToolResult:
    """Convert a platform payload into a spec-compliant MCP tool result."""
    payload = validated_payload(payload)
    return CallToolResult(
        content=[TextContent(type="text", text=render_json(payload))],
        structured_content=payload,
        is_error=not payload.get("ok", False),
    )


def response_payload(*, platform: str, response: httpx.Response, attempts: int = 1) -> dict[str, Any]:
    """Return an MCP-friendly structured payload for successful HTTP responses."""
    if not response.content:
        return validated_payload({"ok": True, "platform": platform, "data": None, "meta": {"attempts": attempts}})

    try:
        return validated_payload(
            {"ok": True, "platform": platform, "data": response.json(), "meta": {"attempts": attempts}}
        )
    except ValueError:
        return validated_payload(
            {"ok": True, "platform": platform, "text": response.text, "meta": {"attempts": attempts}}
        )


def error_payload(
    *,
    platform: str,
    message: str,
    error_type: str,
    status_code: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a consistent structured tool error payload."""
    payload: dict[str, Any] = {
        "ok": False,
        "platform": platform,
        "error": {
            "type": error_type,
            "message": message,
        },
    }
    if status_code is not None:
        payload["error"]["status_code"] = status_code
    if details:
        payload["error"]["details"] = details
    return validated_payload(payload)


def first_env(names: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Return the first configured environment variable name and value."""
    for name in names:
        value = os.getenv(name)
        if value:
            return name, value
    return None, None


# Region-prefixed environment variable helpers.

PLATFORM_PREFIX: dict[str, str] = {
    # The CN prefix identifies Chinese platform credentials.
    "FOFA_KEY": "CN",
    "FOFA_EMAIL": "CN",
    "QUAKE_KEY": "CN",
    "ZOOMEYE_API_KEY": "CN",
    "HUNTER_KEY": "CN",
    "HUNTER_PERSONAL_KEY": "CN",
    "HUNTER_ENTERPRISE_KEY": "CN",
    "DAYDAYMAP_API_KEY": "CN",
}


def canonical_env_name(var_name: str) -> str:
    """Return the public env var name callers should configure."""
    prefix = PLATFORM_PREFIX.get(var_name)
    if prefix:
        return f"{prefix}_{var_name}"
    return var_name


def platform_key(var_name: str) -> str | None:
    """Read env var with region prefix: {PREFIX}_{VAR} only."""
    return os.getenv(canonical_env_name(var_name))


def platform_env(*var_names: str) -> tuple[str | None, str | None]:
    """Like first_env but with region prefix for each name."""
    for name in var_names:
        value = platform_key(name)
        if value:
            return name, value
    return None, None


def missing_env_message(
    *,
    platform: str,
    env_var: str,
    key_url: str,
    optional_env: str | None = None,
) -> dict[str, Any]:
    """Return a consistent missing-credential message."""
    public_env_var = canonical_env_name(env_var)
    env_lines = [f'        "{public_env_var}": "your_{public_env_var.lower()}"']
    if optional_env:
        public_optional_env = canonical_env_name(optional_env)
        env_lines.append(f'        "{public_optional_env}": "optional"')

    env_block = ",\n".join(env_lines)
    optional_note = f"\nNote: {optional_env} is optional." if optional_env else ""

    message = (
        f"Configuration error: {public_env_var} environment variable is required for {platform}.\n\n"
        "Configure it in your MCP client, for example:\n"
        "{\n"
        '  "mcpServers": {\n'
        '    "surveyhub": {\n'
        '      "command": "uvx",\n'
        '      "args": ["surveyhub-mcp"],\n'
        '      "env": {\n'
        f"{env_block}\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        f"Get your API key from: {key_url}"
        f"{optional_note}"
    )
    return error_payload(
        platform=platform,
        message=message,
        error_type="missing_credentials",
        details={"env_var": public_env_var, "key_url": key_url},
    )


def missing_any_env_message(
    *,
    platform: str,
    env_vars: tuple[str, ...],
    key_url: str,
) -> dict[str, Any]:
    """Return a missing-credential message for tools accepting multiple env vars."""
    public_env_vars = tuple(canonical_env_name(name) for name in env_vars)
    env_list = " or ".join(public_env_vars)
    env_lines = ",\n".join(f'        "{name}": "your_{name.lower()}"' for name in public_env_vars)

    message = (
        f"Configuration error: {env_list} environment variable is required for {platform}.\n\n"
        "Configure one of them in your MCP client, for example:\n"
        "{\n"
        '  "mcpServers": {\n'
        '    "surveyhub": {\n'
        '      "command": "uvx",\n'
        '      "args": ["surveyhub-mcp"],\n'
        '      "env": {\n'
        f"{env_lines}\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        f"Get your API key from: {key_url}"
    )
    return error_payload(
        platform=platform,
        message=message,
        error_type="missing_credentials",
        details={"env_vars": public_env_vars, "key_url": key_url},
    )


def format_http_error(
    *,
    platform: str,
    error: httpx.HTTPStatusError,
    auth_hint: str,
    forbidden_hint: str,
) -> dict[str, Any]:
    """Format HTTP status errors as MCP-friendly text."""
    status_code = error.response.status_code
    message = f"{platform} API error (HTTP {status_code}): {error.response.text}\n\n"

    if status_code == 401:
        message += auth_hint
    elif status_code == 403:
        message += forbidden_hint

    return error_payload(
        platform=platform,
        message=message.strip(),
        error_type="http_error",
        status_code=status_code,
    )


def _retry_delay(
    response: httpx.Response,
    attempt: int,
    *,
    http_policy: HttpPolicy = DEFAULT_HTTP_POLICY,
    rate_limit_policy: RateLimitPolicy = DEFAULT_RATE_LIMIT_POLICY,
) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return _cap_retry_delay(
                float(retry_after),
                server_provided=True,
                http_policy=http_policy,
                rate_limit_policy=rate_limit_policy,
            )
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
            except (TypeError, ValueError):
                pass
            else:
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return _cap_retry_delay(
                    (retry_at - datetime.now(timezone.utc)).total_seconds(),
                    server_provided=True,
                    http_policy=http_policy,
                    rate_limit_policy=rate_limit_policy,
                )

    return _retry_backoff_delay(attempt, http_policy=http_policy, rate_limit_policy=rate_limit_policy)


def _retry_backoff_delay(
    attempt: int,
    *,
    http_policy: HttpPolicy = DEFAULT_HTTP_POLICY,
    rate_limit_policy: RateLimitPolicy = DEFAULT_RATE_LIMIT_POLICY,
) -> float:
    """Return capped exponential backoff with jitter when no response headers exist."""
    base_delay = http_policy.retry_base_delay * (2**attempt)
    return _cap_retry_delay(
        # Jitter avoids synchronized retries and is not security-sensitive.
        base_delay + random.uniform(0.0, base_delay * 0.25),  # nosec B311
        http_policy=http_policy,
        rate_limit_policy=rate_limit_policy,
    )


def _response_code(body: Any) -> int | None:
    if not isinstance(body, dict):
        return None
    code = body.get("code")
    if isinstance(code, int):
        return code
    if isinstance(code, str) and code.strip().isdigit():
        return int(code)
    return None


def _can_retry_method(method: str, retry_non_idempotent: bool) -> bool:
    return retry_non_idempotent or method.upper() in {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


SAFE_RETRY_EXCEPTIONS = (httpx.PoolTimeout, httpx.ConnectTimeout, httpx.ConnectError)


def _timeout_decision(error: BaseException) -> dict[str, Any]:
    """Describe what is known about a timed-out request without guessing provider execution."""
    if isinstance(error, httpx.PoolTimeout):
        return {"phase": "pool", "transport_state": "not_sent", "safety": "safe", "quota_risk": "none"}
    if isinstance(error, (httpx.ConnectTimeout, httpx.ConnectError)):
        return {"phase": "connect", "transport_state": "not_sent", "safety": "safe", "quota_risk": "none"}
    if isinstance(error, httpx.WriteTimeout):
        return {"phase": "write", "transport_state": "possibly_sent", "safety": "unsafe", "quota_risk": "possible_duplicate"}
    if isinstance(error, httpx.ReadTimeout):
        return {"phase": "read", "transport_state": "possibly_sent", "safety": "unsafe", "quota_risk": "possible_duplicate"}
    return {"phase": "unknown", "transport_state": "possibly_sent", "safety": "unsafe", "quota_risk": "unknown"}


def _execution_receipt(
    *,
    request_id: str,
    fingerprint: str | None,
    final_state: str,
    transport_state: str,
    attempts: int,
    retry_safety: str,
    retry_recommended: bool,
    reason: str,
    quota_risk: str,
    completeness: str,
    phase: str | None = None,
    duplicate_of: str | None = None,
    cache_hit: bool = False,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "request_id": request_id,
        "final_state": final_state,
        "transport_state": transport_state,
        "attempts": attempts,
        "retry": {"safety": retry_safety, "recommended": retry_recommended, "reason": reason},
        "quota": {
            "risk": quota_risk,
            "charged_attempts": attempts if final_state == "confirmed_success" and transport_state == "response_received" else "unknown",
        },
        "completeness": {"state": completeness, "reason": reason},
        "cache_hit": cache_hit,
    }
    if fingerprint:
        receipt["fingerprint"] = fingerprint
    if phase:
        receipt["timeout_phase"] = phase
    if duplicate_of:
        receipt["duplicate_of"] = duplicate_of
    return receipt


def _safe_fingerprint_value(value: Any) -> Any:
    """Remove credential-shaped values before hashing request identity."""
    if isinstance(value, dict):
        return {
            str(key): _safe_fingerprint_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key).lower() not in {"key", "email", "authorization", "x-quaketoken", "api-key", "apikey"}
        }
    if isinstance(value, (list, tuple)):
        return [_safe_fingerprint_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return type(value).__name__


def request_fingerprint(platform: str, method: str, url: str, request_kwargs: dict[str, Any]) -> str:
    identity = {
        "platform": platform,
        "method": method.upper(),
        "url": url,
        "request": _safe_fingerprint_value(request_kwargs),
    }
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RequestLedger:
    """Cross-process short-lived ledger for metered requests with indeterminate outcomes."""

    def __init__(self, state_dir: Path | None = None, *, ttl: float = 60.0) -> None:
        self._state_dir = state_dir or _request_state_dir()
        self._database_path = self._state_dir / "requests.sqlite3"
        self._ttl = ttl

    def begin(self, fingerprint: str, request_id: str, *, force: bool = False) -> dict[str, Any] | None:
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_id, state, updated_at FROM request_ledger WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
            if row and not force and now - float(row[2]) <= self._ttl and row[1] == "completed":
                connection.commit()
                return {"request_id": row[0], "state": row[1]}
            if row and not force and now - float(row[2]) <= self._ttl and row[1] in {"started", "indeterminate"}:
                connection.commit()
                return {"request_id": row[0], "state": row[1]}
            connection.execute(
                """
                INSERT INTO request_ledger (fingerprint, request_id, state, updated_at)
                VALUES (?, ?, 'started', ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    request_id=excluded.request_id, state='started', updated_at=excluded.updated_at
                """,
                (fingerprint, request_id, now),
            )
            connection.execute("DELETE FROM request_ledger WHERE updated_at < ?", (now - 86400.0,))
            connection.commit()
        return None

    def finish(self, fingerprint: str, request_id: str, state: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE request_ledger SET state = ?, updated_at = ? WHERE fingerprint = ? AND request_id = ?",
                (state, time.time(), fingerprint, request_id),
            )

    def _connect(self) -> sqlite3.Connection:
        # POSIX 0700 intentionally restricts the ledger directory to its owner.
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions
        os.chmod(self._state_dir, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions
        descriptor = os.open(self._database_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS request_ledger (
                fingerprint TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                state TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        os.chmod(self._database_path, 0o600)
        return connection


def _request_state_dir() -> Path:
    configured = os.getenv("SURVEYHUB_STATE_DIR")
    if configured:
        return Path(configured).expanduser() / "requests"
    cache_home = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "surveyhub-mcp" / "requests"


def _remaining_budget(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TotalRequestTimeout
    return remaining


async def _publish_retry_delay(
    rate_limiter: AsyncRateLimiter | None,
    delay: float,
    *,
    deadline: float,
) -> None:
    if rate_limiter:
        await rate_limiter.defer(delay)
    else:
        remaining = _remaining_budget(deadline)
        if delay > remaining:
            raise TotalRequestTimeout
        await asyncio.sleep(delay)


def _should_trip_circuit(error: httpx.HTTPStatusError) -> bool:
    return error.response.status_code in DEFAULT_CIRCUIT_BREAKER_POLICY.failure_statuses


async def request_json(
    *,
    platform: str,
    method: str,
    url: str,
    auth_hint: str,
    forbidden_hint: str,
    rate_limiter: AsyncRateLimiter | None = None,
    retryable_body_codes: set[int] | None = None,
    retry_non_idempotent: bool = False,
    retry_mode: str = "safe_only",
    metered_request: bool = False,
    force_retry: bool = False,
    http_policy: HttpPolicy = DEFAULT_HTTP_POLICY,
    **kwargs: Any,
) -> dict[str, Any]:
    """Send an HTTP request and return a JSON or error text response.

    By default, retries only failures known to happen before a request was sent.
    Metered requests receive a stable fingerprint and duplicate suppression after
    an indeterminate outcome.
    """
    if retry_mode not in {"never", "safe_only", "aggressive"}:
        return error_payload(
            platform=platform,
            message='retry_mode must be "never", "safe_only", or "aggressive".',
            error_type="validation_error",
            details={"retry_mode": retry_mode},
        )

    request_id = str(uuid.uuid4())
    reporter = ExecutionReporter(platform=platform, request_id=request_id)
    fingerprint = request_fingerprint(platform, method, url, kwargs) if metered_request else None
    ledger = RequestLedger() if fingerprint else None
    if fingerprint and not force_retry:
        now = time.monotonic()
        for key, (cached_at, _) in list(_METERED_RESPONSE_CACHE.items()):
            if now - cached_at > METERED_RESPONSE_CACHE_TTL:
                _METERED_RESPONSE_CACHE.pop(key, None)
        cached = _METERED_RESPONSE_CACHE.get(fingerprint)
        if cached:
            await reporter.event(
                "cache_hit",
                f"Reused a recent identical {platform} response without another provider request.",
                cache_hit=True,
                attempts=0,
            )
            cached_response = cached[1]
            prior_execution = cached_response.get("meta", {}).get("execution", {})
            prior_completeness = prior_execution.get("completeness", {})
            return enrich_payload(
                cached_response,
                meta={"attempts": 0, "execution": _execution_receipt(
                    request_id=request_id, fingerprint=fingerprint,
                    final_state="confirmed_success", transport_state="response_received", attempts=0,
                    retry_safety="safe", retry_recommended=False, reason="recent_identical_response_cache_hit",
                    quota_risk="none", completeness=prior_completeness.get("state", "complete"),
                    duplicate_of=prior_execution.get("request_id"), cache_hit=True,
                )},
            )
    circuit_breaker = _circuit_breaker_for(platform)
    deadline = time.monotonic() + http_policy.total_timeout
    accumulated_quota_risk = "none"
    allowed, retry_after = await circuit_breaker.allow_request()
    if not allowed:
        await reporter.event(
            "circuit_open",
            f"Skipped {platform} because its circuit breaker is open.",
            level="warning",
            retry_after_seconds=max(1, int(retry_after)),
        )
        return error_payload(
            platform=platform,
            message=_circuit_open_message(platform, retry_after),
            error_type="circuit_open",
            details={"retry_after_seconds": max(1, int(retry_after))},
        )

    if ledger and fingerprint:
        duplicate = await asyncio.to_thread(ledger.begin, fingerprint, request_id, force=force_retry)
        if duplicate:
            reason = (
                "A matching metered request completed recently in another process."
                if duplicate["state"] == "completed"
                else "A matching metered request is still running or recently ended without a response."
            )
            await reporter.event(
                "duplicate_suppressed",
                f"Suppressed an identical metered {platform} request to avoid possible duplicate quota use.",
                level="warning",
                duplicate_of=duplicate["request_id"],
                prior_state=duplicate["state"],
            )
            return enrich_payload(
                error_payload(
                    platform=platform,
                    message=f"Duplicate request suppressed. {reason} Use force_retry=true only if duplicate quota use is acceptable.",
                    error_type="duplicate_request_suppressed",
                ),
                meta={
                    "execution": _execution_receipt(
                        request_id=request_id,
                        fingerprint=fingerprint,
                        final_state="confirmed_success" if duplicate["state"] == "completed" else "indeterminate",
                        transport_state="response_received" if duplicate["state"] == "completed" else "possibly_sent",
                        attempts=0,
                        retry_safety="unsafe",
                        retry_recommended=False,
                        reason=reason,
                        quota_risk="possible_duplicate" if duplicate["state"] != "completed" else "none",
                        completeness="complete" if duplicate["state"] == "completed" else "unknown",
                        duplicate_of=duplicate["request_id"],
                    )
                },
            )

    request_dispatched = False
    response_received = False
    for attempt in range(http_policy.max_attempts):
        try:
            request_dispatched = accumulated_quota_risk != "none"
            response_received = False
            await reporter.event(
                "attempt_started",
                f"Starting {platform} provider attempt {attempt + 1}/{http_policy.max_attempts}.",
                attempt=attempt + 1,
                max_attempts=http_policy.max_attempts,
            )
            remaining = _remaining_budget(deadline)
            if rate_limiter:
                await asyncio.wait_for(rate_limiter.wait(), timeout=remaining)
            attempt_timeout = min(http_policy.attempt_timeout, _remaining_budget(deadline))
            async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                request_dispatched = True
                response = await asyncio.wait_for(
                    client.request(method, url, **kwargs),
                    timeout=_remaining_budget(deadline),
                )
                response_received = True
                response.raise_for_status()
                if retryable_body_codes:
                    try:
                        body = response.json()
                    except ValueError:
                        body = None
                    body_code = _response_code(body)
                    if body_code in retryable_body_codes:
                        response_received = False
                        delay = _retry_delay(response, attempt, http_policy=http_policy)
                        await reporter.event(
                            "retry_scheduled",
                            f"{platform} returned a retryable provider code; waiting before retry.",
                            level="warning",
                            attempt=attempt + 1,
                            delay_seconds=delay,
                            reason="provider_rate_limit_response",
                        )
                        await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                        if attempt + 1 < http_policy.max_attempts and retry_mode != "never":
                            accumulated_quota_risk = "unknown"
                            continue
                        await circuit_breaker.record_neutral()
                        if ledger and fingerprint:
                            await asyncio.to_thread(ledger.finish, fingerprint, request_id, "completed")
                        return enrich_payload(
                            error_payload(
                                platform=platform,
                                message=str(body.get("message") or f"{platform} API rate limit exceeded."),
                                error_type="rate_limit",
                                status_code=int(body_code),
                                details={"provider_response": body},
                            ),
                            meta={"execution": _execution_receipt(
                                request_id=request_id, fingerprint=fingerprint,
                                final_state="confirmed_failure", transport_state="response_received",
                                attempts=attempt + 1, retry_safety="conditional", retry_recommended=True,
                                reason="provider_rate_limit_response", quota_risk="unknown", completeness="unknown",
                            )},
                        )
                await circuit_breaker.record_success()
                request_data = kwargs.get("json") or kwargs.get("params") or {}
                page_size = next((request_data[k] for k in ("size", "page_size", "pagesize", "limit") if type(request_data.get(k)) is int), 0)
                result_offset = request_data.get("start", request_data.get("offset", (request_data.get("page", 1) - 1) * page_size))
                success_result = enrich_payload(
                    response_payload(platform=platform, response=response, attempts=attempt + 1),
                    meta={
                        "result_offset": result_offset,
                        "execution": _execution_receipt(
                            request_id=request_id,
                            fingerprint=fingerprint,
                            final_state="confirmed_success",
                            transport_state="response_received",
                            attempts=attempt + 1,
                            retry_safety="safe",
                            retry_recommended=False,
                            reason="provider_response_received",
                            quota_risk=accumulated_quota_risk,
                            completeness="complete",
                        )
                    },
                )
                if ledger and fingerprint:
                    await asyncio.to_thread(ledger.finish, fingerprint, request_id, "completed")
                    _METERED_RESPONSE_CACHE[fingerprint] = (time.monotonic(), success_result)
                await reporter.event(
                    "request_completed",
                    f"Received and validated the {platform} provider response.",
                    attempt=attempt + 1,
                    attempts=attempt + 1,
                )
                return success_result
        except asyncio.CancelledError:
            if ledger and fingerprint:
                await asyncio.shield(
                    asyncio.to_thread(
                        ledger.finish,
                        fingerprint,
                        request_id,
                        "completed" if response_received else ("indeterminate" if request_dispatched else "failed"),
                    )
                )
            await asyncio.shield(
                reporter.event(
                    "request_cancelled",
                    f"The {platform} request was cancelled by the MCP client.",
                    level="warning",
                    attempt=attempt + 1,
                    transport_state=(
                        "response_received"
                        if response_received
                        else ("possibly_sent" if request_dispatched else "not_sent")
                    ),
                )
            )
            raise
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                response_received = False
                delay = _retry_delay(error.response, attempt, http_policy=http_policy)
                await reporter.event(
                    "retry_scheduled",
                    f"{platform} returned HTTP 429; waiting before retry.",
                    level="warning",
                    attempt=attempt + 1,
                    delay_seconds=delay,
                    reason="http_429",
                )
                await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                if attempt + 1 < http_policy.max_attempts and retry_mode != "never":
                    accumulated_quota_risk = "unknown"
                    continue
            if error.response.status_code == 429:
                await circuit_breaker.record_neutral()
            elif _should_trip_circuit(error):
                await circuit_breaker.record_failure()
            else:
                await circuit_breaker.record_success()
            if ledger and fingerprint:
                await asyncio.to_thread(ledger.finish, fingerprint, request_id, "completed")
            await reporter.event(
                "request_failed",
                f"{platform} returned HTTP {error.response.status_code}.",
                level="warning",
                attempt=attempt + 1,
                status_code=error.response.status_code,
                reason="provider_http_error",
            )
            return enrich_payload(
                format_http_error(
                    platform=platform,
                    error=error,
                    auth_hint=auth_hint,
                    forbidden_hint=forbidden_hint,
                ),
                meta={"attempts": attempt + 1, "execution": _execution_receipt(
                    request_id=request_id, fingerprint=fingerprint,
                    final_state="confirmed_failure", transport_state="response_received",
                    attempts=attempt + 1,
                    retry_safety="conditional" if error.response.status_code in {429, 502, 503, 504} else "unsafe",
                    retry_recommended=error.response.status_code in {429, 502, 503, 504},
                    reason=f"provider_http_{error.response.status_code}", quota_risk="unknown", completeness="unknown",
                )},
            )
        except httpx.TimeoutException as error:
            decision = _timeout_decision(error)
            retry_allowed = (
                retry_mode == "aggressive"
                or (retry_mode == "safe_only" and isinstance(error, SAFE_RETRY_EXCEPTIONS))
            )
            if attempt + 1 < http_policy.max_attempts and retry_allowed:
                if decision["transport_state"] == "possibly_sent":
                    accumulated_quota_risk = "possible_duplicate"
                delay = _retry_backoff_delay(attempt, http_policy=http_policy)
                await reporter.event(
                    "retry_scheduled",
                    f"{platform} failed before a response; scheduling a policy-approved retry.",
                    level="warning",
                    attempt=attempt + 1,
                    delay_seconds=delay,
                    reason=f"{decision['phase']}_timeout",
                    retry_safety=decision["safety"],
                )
                await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                continue
            await circuit_breaker.record_failure()
            if ledger and fingerprint:
                await asyncio.to_thread(
                    ledger.finish,
                    fingerprint,
                    request_id,
                    "indeterminate" if decision["transport_state"] == "possibly_sent" else "failed",
                )
            reason = (
                "server_may_have_processed_request"
                if decision["transport_state"] == "possibly_sent"
                else "request_was_not_sent"
            )
            await reporter.event(
                "request_timed_out",
                f"{platform} timed out during the {decision['phase']} phase.",
                level="warning",
                attempt=attempt + 1,
                timeout_phase=decision["phase"],
                retry_safety=decision["safety"],
                transport_state=decision["transport_state"],
            )
            return enrich_payload(
                error_payload(
                    platform=platform,
                    message=f"Request timeout during {decision['phase']} phase. Retry safety is {decision['safety']}.",
                    error_type="timeout",
                    details={"attempts": attempt + 1, "timeout_phase": decision["phase"]},
                ),
                meta={
                    "attempts": attempt + 1,
                    "execution": _execution_receipt(
                        request_id=request_id,
                        fingerprint=fingerprint,
                        final_state=(
                            "indeterminate" if decision["transport_state"] == "possibly_sent" else "confirmed_failure"
                        ),
                        transport_state=decision["transport_state"],
                        attempts=attempt + 1,
                        retry_safety=decision["safety"],
                        retry_recommended=decision["safety"] == "safe",
                        reason=reason,
                        quota_risk=decision["quota_risk"],
                        completeness="unknown",
                        phase=decision["phase"],
                    )
                },
            )
        except (asyncio.TimeoutError, TotalRequestTimeout):
            if ledger and fingerprint:
                await asyncio.to_thread(ledger.finish, fingerprint, request_id, "indeterminate")
            await reporter.event(
                "total_timeout",
                f"{platform} exhausted its total request time budget.",
                level="error",
                attempt=attempt + 1,
                total_timeout_seconds=http_policy.total_timeout,
                transport_state="possibly_sent",
            )
            return enrich_payload(
                error_payload(
                    platform=platform,
                    message=f"{platform} request exceeded the {http_policy.total_timeout:.0f}-second total time budget.",
                    error_type="total_timeout",
                    details={"total_timeout_seconds": http_policy.total_timeout},
                ),
                meta={"attempts": attempt + 1, "execution": _execution_receipt(
                    request_id=request_id, fingerprint=fingerprint,
                    final_state="indeterminate", transport_state="possibly_sent", attempts=attempt + 1,
                    retry_safety="unsafe", retry_recommended=False, reason="total_budget_exhausted_execution_unknown",
                    quota_risk="possible_duplicate", completeness="unknown", phase="unknown",
                )},
            )
        except RateLimitQueueTimeout as error:
            if ledger and fingerprint:
                await asyncio.to_thread(ledger.finish, fingerprint, request_id, "failed")
            await reporter.event(
                "rate_limit_queue_timeout",
                f"{platform} waited too long in the local rate-limit queue.",
                level="warning",
                attempt=attempt,
                queue_timeout_seconds=error.timeout,
                transport_state="not_sent",
            )
            return enrich_payload(
                error_payload(
                    platform=platform,
                    message=f"{platform} request waited too long for the shared rate-limit queue.",
                    error_type="rate_limit_queue_timeout",
                    details={"queue_timeout_seconds": error.timeout},
                ),
                meta={"execution": _execution_receipt(
                    request_id=request_id, fingerprint=fingerprint,
                    final_state="confirmed_failure", transport_state="not_sent", attempts=attempt,
                    retry_safety="safe", retry_recommended=True, reason="local_rate_limit_queue_timeout",
                    quota_risk="none", completeness="unknown",
                )},
            )
        except ProviderCooldownActive as error:
            if ledger and fingerprint:
                await asyncio.to_thread(ledger.finish, fingerprint, request_id, "failed")
            await reporter.event(
                "provider_cooldown",
                f"{platform} remains inside a shared provider cooldown.",
                level="warning",
                attempt=attempt,
                retry_after_seconds=max(1, int(error.retry_after)),
                transport_state="not_sent",
            )
            return enrich_payload(
                error_payload(
                    platform=platform,
                    message=f"{platform} is rate limited; retry after the shared cooldown.",
                    error_type="rate_limit_cooldown",
                    status_code=429,
                    details={"retry_after_seconds": max(1, int(error.retry_after))},
                ),
                meta={"execution": _execution_receipt(
                    request_id=request_id, fingerprint=fingerprint,
                    final_state="confirmed_failure", transport_state="not_sent", attempts=attempt,
                    retry_safety="safe", retry_recommended=True, reason="local_provider_cooldown",
                    quota_risk="none", completeness="unknown",
                )},
            )
        except httpx.RequestError as error:
            safe_failure = isinstance(error, httpx.ConnectError)
            if safe_failure and retry_mode != "never" and attempt + 1 < http_policy.max_attempts:
                delay = _retry_backoff_delay(attempt, http_policy=http_policy)
                await reporter.event(
                    "retry_scheduled",
                    f"{platform} connection failed before send; scheduling a safe retry.",
                    level="warning",
                    attempt=attempt + 1,
                    delay_seconds=delay,
                    reason="connection_failed_before_send",
                    retry_safety="safe",
                )
                await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                continue
            await circuit_breaker.record_failure()
            if ledger and fingerprint:
                await asyncio.to_thread(ledger.finish, fingerprint, request_id, "failed" if safe_failure else "indeterminate")
            await reporter.event(
                "request_failed",
                f"{platform} failed before a confirmed provider response.",
                level="warning",
                attempt=attempt + 1,
                reason="connection_failed_before_send" if safe_failure else "request_execution_unknown",
                transport_state="not_sent" if safe_failure else "possibly_sent",
            )
            return enrich_payload(
                error_payload(
                    platform=platform,
                    message=f"Error querying {platform}: {type(error).__name__}: {error}",
                    error_type="request_error",
                ),
                meta={"attempts": attempt + 1, "execution": _execution_receipt(
                    request_id=request_id, fingerprint=fingerprint,
                    final_state="confirmed_failure" if safe_failure else "indeterminate",
                    transport_state="not_sent" if safe_failure else "possibly_sent", attempts=attempt + 1,
                    retry_safety="safe" if safe_failure else "unsafe", retry_recommended=safe_failure,
                    reason="connection_failed_before_send" if safe_failure else "request_execution_unknown",
                    quota_risk="none" if safe_failure else "unknown", completeness="unknown",
                    phase="connect" if safe_failure else "unknown",
                )},
            )
        except Exception as error:
            await reporter.event(
                "unexpected_error",
                f"{platform} failed with an unexpected internal error.",
                level="error",
                attempt=attempt + 1,
                error_type=type(error).__name__,
            )
            return error_payload(
                platform=platform,
                message=f"Error querying {platform}: {type(error).__name__}: {error}",
                error_type="unexpected_error",
            )


async def request_download(
    *,
    platform: str,
    method: str,
    url: str,
    output_path: str,
    auth_hint: str,
    forbidden_hint: str,
    rate_limiter: AsyncRateLimiter | None = None,
    retryable_body_codes: set[int] | None = None,
    http_policy: HttpPolicy = DEFAULT_HTTP_POLICY,
    **kwargs: Any,
) -> dict[str, Any]:
    """Send an HTTP request and save the response body to a local file.

    Automatically retries GET timeouts and HTTP 429 responses with exponential backoff.
    """
    request_id = str(uuid.uuid4())
    reporter = ExecutionReporter(platform=platform, request_id=request_id)
    circuit_breaker = _circuit_breaker_for(platform)
    deadline = time.monotonic() + http_policy.total_timeout
    allowed, retry_after = await circuit_breaker.allow_request()
    if not allowed:
        await reporter.event(
            "circuit_open",
            f"Skipped the {platform} download because its circuit breaker is open.",
            level="warning",
            retry_after_seconds=max(1, int(retry_after)),
        )
        return error_payload(
            platform=platform,
            message=_circuit_open_message(platform, retry_after),
            error_type="circuit_open",
            details={"retry_after_seconds": max(1, int(retry_after))},
        )

    for attempt in range(http_policy.max_attempts):
        try:
            await reporter.event(
                "download_attempt_started",
                f"Starting {platform} download attempt {attempt + 1}/{http_policy.max_attempts}.",
                attempt=attempt + 1,
                max_attempts=http_policy.max_attempts,
            )
            remaining = _remaining_budget(deadline)
            if rate_limiter:
                await asyncio.wait_for(rate_limiter.wait(), timeout=remaining)
            attempt_timeout = min(http_policy.attempt_timeout, _remaining_budget(deadline))
            async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                response = await asyncio.wait_for(
                    client.request(method, url, **kwargs),
                    timeout=_remaining_budget(deadline),
                )
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "json" in content_type.lower():
                    try:
                        body = response.json()
                    except ValueError:
                        body = None
                    body_code = _response_code(body)
                    if retryable_body_codes and body_code in retryable_body_codes:
                        delay = _retry_delay(response, attempt, http_policy=http_policy)
                        await reporter.event(
                            "retry_scheduled",
                            f"{platform} returned a retryable download response; waiting before retry.",
                            level="warning",
                            attempt=attempt + 1,
                            delay_seconds=delay,
                            reason="provider_rate_limit_response",
                        )
                        await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                        if attempt + 1 < http_policy.max_attempts:
                            continue
                        await circuit_breaker.record_neutral()
                        return error_payload(
                            platform=platform,
                            message=str(body.get("message") or f"{platform} API rate limit exceeded."),
                            error_type="rate_limit",
                            status_code=int(body_code),
                            details={"provider_response": body},
                        )
                    await circuit_breaker.record_success()
                    return response_payload(platform=platform, response=response, attempts=attempt + 1)

                path = Path(output_path).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
                await circuit_breaker.record_success()
                await reporter.event(
                    "download_completed",
                    f"Saved the {platform} export to local storage.",
                    attempt=attempt + 1,
                    bytes=len(response.content),
                )
                return validated_payload({
                    "ok": True,
                    "platform": platform,
                    "meta": {"attempts": attempt + 1},
                    "download": {
                        "bytes": len(response.content),
                        "path": str(path),
                    },
                })
        except asyncio.CancelledError:
            await asyncio.shield(
                reporter.event(
                    "download_cancelled",
                    f"The {platform} download was cancelled by the MCP client.",
                    level="warning",
                    attempt=attempt + 1,
                )
            )
            raise
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                delay = _retry_delay(error.response, attempt, http_policy=http_policy)
                await reporter.event(
                    "retry_scheduled",
                    f"{platform} returned HTTP 429 during download; waiting before retry.",
                    level="warning",
                    attempt=attempt + 1,
                    delay_seconds=delay,
                    reason="http_429",
                )
                await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                if attempt + 1 < http_policy.max_attempts:
                    continue
            if error.response.status_code == 429:
                await circuit_breaker.record_neutral()
            elif _should_trip_circuit(error):
                await circuit_breaker.record_failure()
            else:
                await circuit_breaker.record_success()
            return format_http_error(
                platform=platform,
                error=error,
                auth_hint=auth_hint,
                forbidden_hint=forbidden_hint,
            )
        except httpx.TimeoutException:
            if attempt + 1 < http_policy.max_attempts and _can_retry_method(method, False):
                delay = _retry_backoff_delay(attempt, http_policy=http_policy)
                await reporter.event(
                    "retry_scheduled",
                    f"{platform} download timed out; scheduling a safe GET retry.",
                    level="warning",
                    attempt=attempt + 1,
                    delay_seconds=delay,
                    reason="download_timeout",
                    retry_safety="safe",
                )
                await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                continue
            await circuit_breaker.record_failure()
            return error_payload(
                platform=platform,
                message=f"Request timeout: {platform} API did not respond within {http_policy.attempt_timeout:.0f} seconds.",
                error_type="timeout",
                details={"attempts": attempt + 1},
            )
        except (asyncio.TimeoutError, TotalRequestTimeout):
            return error_payload(
                platform=platform,
                message=f"{platform} request exceeded the {http_policy.total_timeout:.0f}-second total time budget.",
                error_type="total_timeout",
                details={"total_timeout_seconds": http_policy.total_timeout},
            )
        except RateLimitQueueTimeout as error:
            return error_payload(
                platform=platform,
                message=f"{platform} request waited too long for the shared rate-limit queue.",
                error_type="rate_limit_queue_timeout",
                details={"queue_timeout_seconds": error.timeout},
            )
        except ProviderCooldownActive as error:
            return error_payload(
                platform=platform,
                message=f"{platform} is rate limited; retry after the shared cooldown.",
                error_type="rate_limit_cooldown",
                status_code=429,
                details={"retry_after_seconds": max(1, int(error.retry_after))},
            )
        except httpx.RequestError as error:
            await circuit_breaker.record_failure()
            return error_payload(
                platform=platform,
                message=f"Error downloading from {platform}: {type(error).__name__}: {error}",
                error_type="request_error",
            )
        except Exception as error:
            return error_payload(
                platform=platform,
                message=f"Error downloading from {platform}: {type(error).__name__}: {error}",
                error_type="unexpected_error",
            )
