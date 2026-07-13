"""Shared helpers for all SurveyHub-MCP platform tools."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import random
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable

import httpx
from mcp.types import CallToolResult, TextContent

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
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._state_dir, 0o700)
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


HUNTER_EXACT_SEARCH_EXCLUDED_FIELDS = {"after", "before"}


def normalize_hunter_query(query: str, *, exact_search: bool = True) -> str:
    """Use Hunter exact string comparisons by default.

    Hunter treats field="value" as a fuzzy contains query. For MCP callers, the
    safer default is field=="value"; callers can opt out for native fuzzy search.
    """
    if not exact_search:
        return query

    import re

    pattern = re.compile(r"(?P<field>[A-Za-z][\w.-]*)\s*=(?!=)\s*\"")

    def replace(match: re.Match[str]) -> str:
        field = match.group("field")
        if field in HUNTER_EXACT_SEARCH_EXCLUDED_FIELDS:
            return match.group(0)
        return f'{field}=="'

    return pattern.sub(replace, query)


def split_csv(value: str | None) -> list[str] | None:
    """Split a comma-separated string into a clean list."""
    if not value:
        return None

    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def render_json(data: Any) -> str:
    """Render API data as readable JSON text for MCP clients."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def mcp_tool_result(payload: dict[str, Any]) -> CallToolResult:
    """Convert a platform payload into a spec-compliant MCP tool result."""
    return CallToolResult(
        content=[TextContent(type="text", text=render_json(payload))],
        structuredContent=payload,
        isError=not payload.get("ok", False),
    )


def apply_server_metadata(server: Any) -> None:
    """Keep FastMCP handshake metadata aligned with package metadata."""
    from . import __version__

    mcp_server = getattr(server, "_mcp_server", None)
    if mcp_server is not None:
        mcp_server.version = __version__


def response_payload(*, platform: str, response: httpx.Response) -> dict[str, Any]:
    """Return an MCP-friendly structured payload for successful HTTP responses."""
    if not response.content:
        return {"ok": True, "platform": platform, "data": None}

    try:
        return {"ok": True, "platform": platform, "data": response.json()}
    except ValueError:
        return {"ok": True, "platform": platform, "text": response.text}


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
    return payload


def first_env(names: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Return the first configured environment variable name and value."""
    for name in names:
        value = os.getenv(name)
        if value:
            return name, value
    return None, None


# ---------------------------------------------------------------------------
# Region-prefixed env-var helpers (cn)
# ---------------------------------------------------------------------------

PLATFORM_PREFIX: dict[str, str] = {
    # cn: Chinese platforms
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

    base_delay = http_policy.retry_base_delay * (2**attempt)
    return _cap_retry_delay(
        base_delay + random.uniform(0.0, base_delay * 0.25),
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
    http_policy: HttpPolicy = DEFAULT_HTTP_POLICY,
    **kwargs: Any,
) -> dict[str, Any]:
    """Send an HTTP request and return a JSON or error text response.

    Automatically retries on HTTP 429 (rate-limit) with exponential backoff.
    """
    circuit_breaker = _circuit_breaker_for(platform)
    deadline = time.monotonic() + http_policy.total_timeout
    allowed, retry_after = await circuit_breaker.allow_request()
    if not allowed:
        return error_payload(
            platform=platform,
            message=_circuit_open_message(platform, retry_after),
            error_type="circuit_open",
            details={"retry_after_seconds": max(1, int(retry_after))},
        )

    for attempt in range(http_policy.max_attempts):
        try:
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
                if retryable_body_codes:
                    try:
                        body = response.json()
                    except ValueError:
                        body = None
                    body_code = _response_code(body)
                    if body_code in retryable_body_codes:
                        delay = _retry_delay(response, attempt, http_policy=http_policy)
                        await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                        if attempt + 1 < http_policy.max_attempts and _can_retry_method(method, retry_non_idempotent):
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
                return response_payload(platform=platform, response=response)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                delay = _retry_delay(error.response, attempt, http_policy=http_policy)
                await _publish_retry_delay(rate_limiter, delay, deadline=deadline)
                if attempt + 1 < http_policy.max_attempts and _can_retry_method(method, retry_non_idempotent):
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
            await circuit_breaker.record_failure()
            return error_payload(
                platform=platform,
                message=f"Request timeout: {platform} API did not respond within {http_policy.attempt_timeout:.0f} seconds.",
                error_type="timeout",
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
                message=f"Error querying {platform}: {type(error).__name__}: {error}",
                error_type="request_error",
            )
        except Exception as error:
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

    Automatically retries on HTTP 429 (rate-limit) with exponential backoff.
    """
    circuit_breaker = _circuit_breaker_for(platform)
    deadline = time.monotonic() + http_policy.total_timeout
    allowed, retry_after = await circuit_breaker.allow_request()
    if not allowed:
        return error_payload(
            platform=platform,
            message=_circuit_open_message(platform, retry_after),
            error_type="circuit_open",
            details={"retry_after_seconds": max(1, int(retry_after))},
        )

    for attempt in range(http_policy.max_attempts):
        try:
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
                    return response_payload(platform=platform, response=response)

                path = Path(output_path).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
                await circuit_breaker.record_success()
                return {
                    "ok": True,
                    "platform": platform,
                    "download": {
                        "bytes": len(response.content),
                        "path": str(path),
                    },
                }
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                delay = _retry_delay(error.response, attempt, http_policy=http_policy)
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
            await circuit_breaker.record_failure()
            return error_payload(
                platform=platform,
                message=f"Request timeout: {platform} API did not respond within {http_policy.attempt_timeout:.0f} seconds.",
                error_type="timeout",
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
