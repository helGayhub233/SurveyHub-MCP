"""Shared helpers for all SurveyHub-MCP platform tools."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_TIMEOUT = 15.0
MAX_RETRIES = 2
RETRY_BASE_DELAY = 1.0
MAX_RETRY_DELAY = 5.0
CIRCUIT_FAILURE_THRESHOLD = 2
CIRCUIT_RECOVERY_TIMEOUT = 15.0
CIRCUIT_BREAKER_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}


class AsyncRateLimiter:
    """Serialize calls so request start times are at least min_interval apart."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._last_started_at = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait_seconds = self._min_interval - (now - self._last_started_at)
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_started_at = time.monotonic()


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


_CIRCUIT_BREAKERS: dict[str, AsyncCircuitBreaker] = {}


def _circuit_breaker_for(platform: str) -> AsyncCircuitBreaker:
    breaker = _CIRCUIT_BREAKERS.get(platform)
    if breaker is None:
        breaker = AsyncCircuitBreaker(
            failure_threshold=CIRCUIT_FAILURE_THRESHOLD,
            recovery_timeout=CIRCUIT_RECOVERY_TIMEOUT,
        )
        _CIRCUIT_BREAKERS[platform] = breaker
    return breaker


def _circuit_open_message(platform: str, retry_after: float) -> str:
    return (
        f"{platform} API is temporarily unavailable because recent requests failed. "
        f"Retry after {max(1, int(retry_after))} seconds."
    )


def _cap_retry_delay(delay: float) -> float:
    return min(MAX_RETRY_DELAY, max(0.0, delay))


def encode_base64(text: str) -> str:
    """Encode text with standard Base64."""
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def encode_base64_url(text: str) -> str:
    """Encode text with URL-safe Base64."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def split_csv(value: str | None) -> list[str] | None:
    """Split a comma-separated string into a clean list."""
    if not value:
        return None

    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def render_json(data: Any) -> str:
    """Render API data as readable JSON text for MCP clients."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def render_response_body(response: httpx.Response) -> str:
    """Render successful API responses without assuming every body is JSON."""
    if not response.content:
        return ""

    try:
        return render_json(response.json())
    except ValueError:
        return response.text


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


def platform_key(var_name: str) -> str | None:
    """Read env var with region prefix: {PREFIX}_{VAR} only."""
    prefix = PLATFORM_PREFIX.get(var_name)
    if prefix:
        return os.getenv(f"{prefix}_{var_name}")
    return os.getenv(var_name)


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
) -> str:
    """Return a consistent missing-credential message."""
    env_lines = [f'        "{env_var}": "your_{env_var.lower()}"']
    if optional_env:
        env_lines.append(f'        "{optional_env}": "optional"')

    env_block = ",\n".join(env_lines)
    optional_note = f"\nNote: {optional_env} is optional." if optional_env else ""

    return (
        f"Configuration error: {env_var} environment variable is required for {platform}.\n\n"
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


def missing_any_env_message(
    *,
    platform: str,
    env_vars: tuple[str, ...],
    key_url: str,
) -> str:
    """Return a missing-credential message for tools accepting multiple env vars."""
    env_list = " or ".join(env_vars)
    env_lines = ",\n".join(f'        "{name}": "your_{name.lower()}"' for name in env_vars)

    return (
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


def format_http_error(
    *,
    platform: str,
    error: httpx.HTTPStatusError,
    auth_hint: str,
    forbidden_hint: str,
) -> str:
    """Format HTTP status errors as MCP-friendly text."""
    status_code = error.response.status_code
    message = f"{platform} API error (HTTP {status_code}): {error.response.text}\n\n"

    if status_code == 401:
        message += auth_hint
    elif status_code == 403:
        message += forbidden_hint

    return message.strip()


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return _cap_retry_delay(float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
            except (TypeError, ValueError):
                pass
            else:
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return _cap_retry_delay((retry_at - datetime.now(timezone.utc)).total_seconds())

    return _cap_retry_delay(RETRY_BASE_DELAY * (2**attempt))


def _should_trip_circuit(error: httpx.HTTPStatusError) -> bool:
    return error.response.status_code in CIRCUIT_BREAKER_HTTP_STATUSES


async def request_json(
    *,
    platform: str,
    method: str,
    url: str,
    auth_hint: str,
    forbidden_hint: str,
    rate_limiter: AsyncRateLimiter | None = None,
    **kwargs: Any,
) -> str:
    """Send an HTTP request and return a JSON or error text response.

    Automatically retries on HTTP 429 (rate-limit) with exponential backoff.
    """
    circuit_breaker = _circuit_breaker_for(platform)
    allowed, retry_after = await circuit_breaker.allow_request()
    if not allowed:
        return _circuit_open_message(platform, retry_after)

    for attempt in range(MAX_RETRIES + 1):
        try:
            if rate_limiter:
                await rate_limiter.wait()
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                await circuit_breaker.record_success()
                return render_response_body(response)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429 and attempt < MAX_RETRIES:
                await asyncio.sleep(_retry_delay(error.response, attempt))
                continue
            if _should_trip_circuit(error):
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
            return f"Request timeout: {platform} API did not respond within {DEFAULT_TIMEOUT:.0f} seconds."
        except httpx.RequestError as error:
            await circuit_breaker.record_failure()
            return f"Error querying {platform}: {type(error).__name__}: {error}"
        except Exception as error:
            return f"Error querying {platform}: {type(error).__name__}: {error}"


async def request_download(
    *,
    platform: str,
    method: str,
    url: str,
    output_path: str,
    auth_hint: str,
    forbidden_hint: str,
    rate_limiter: AsyncRateLimiter | None = None,
    **kwargs: Any,
) -> str:
    """Send an HTTP request and save the response body to a local file.

    Automatically retries on HTTP 429 (rate-limit) with exponential backoff.
    """
    circuit_breaker = _circuit_breaker_for(platform)
    allowed, retry_after = await circuit_breaker.allow_request()
    if not allowed:
        return _circuit_open_message(platform, retry_after)

    for attempt in range(MAX_RETRIES + 1):
        try:
            if rate_limiter:
                await rate_limiter.wait()
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                await circuit_breaker.record_success()

                content_type = response.headers.get("content-type", "")
                if "json" in content_type.lower():
                    try:
                        return render_json(response.json())
                    except ValueError:
                        return response.text

                path = Path(output_path).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
                return f"Downloaded {len(response.content)} bytes from {platform} to {path}."
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429 and attempt < MAX_RETRIES:
                await asyncio.sleep(_retry_delay(error.response, attempt))
                continue
            if _should_trip_circuit(error):
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
            return f"Request timeout: {platform} API did not respond within {DEFAULT_TIMEOUT:.0f} seconds."
        except httpx.RequestError as error:
            await circuit_breaker.record_failure()
            return f"Error downloading from {platform}: {type(error).__name__}: {error}"
        except Exception as error:
            return f"Error downloading from {platform}: {type(error).__name__}: {error}"
