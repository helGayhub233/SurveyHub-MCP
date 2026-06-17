"""FullHunt MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

FH_BASE_URL = "https://fullhunt.io/api/v1"
FH_KEY_URL = "https://fullhunt.io/"

FH_RATE_LIMITER = AsyncRateLimiter(1.0)


def _fh_key() -> str | None:
    return platform_key("FULLHUNT_API_KEY")


def _fh_headers() -> dict[str, str]:
    key = _fh_key()
    return {"X-API-KEY": key} if key else {}


def _missing_key() -> str:
    return missing_env_message(
        platform="FullHunt",
        env_var="AE_FULLHUNT_API_KEY",
        key_url=FH_KEY_URL,
    )


async def domain_fh(
    *,
    domain: str,
) -> str:
    """Call FullHunt domain details API."""
    if not _fh_key():
        return _missing_key()

    await FH_RATE_LIMITER.wait()

    return await request_json(
        platform="FullHunt",
        method="GET",
        url=f"{FH_BASE_URL}/domain/{domain}/details",
        headers=_fh_headers(),
        auth_hint="Authentication failed. Check AE_FULLHUNT_API_KEY.",
        forbidden_hint="Access denied. Your FullHunt plan may not have access.",
    )


async def subdomains_fh(
    *,
    domain: str,
) -> str:
    """Call FullHunt subdomains API."""
    if not _fh_key():
        return _missing_key()

    await FH_RATE_LIMITER.wait()

    return await request_json(
        platform="FullHunt",
        method="GET",
        url=f"{FH_BASE_URL}/domain/{domain}/subdomains",
        headers=_fh_headers(),
        auth_hint="Authentication failed. Check AE_FULLHUNT_API_KEY.",
        forbidden_hint="Access denied. Your FullHunt plan may not have access.",
    )


async def host_fh(
    *,
    host: str,
) -> str:
    """Call FullHunt host details API."""
    if not _fh_key():
        return _missing_key()

    await FH_RATE_LIMITER.wait()

    return await request_json(
        platform="FullHunt",
        method="GET",
        url=f"{FH_BASE_URL}/host/{host}",
        headers=_fh_headers(),
        auth_hint="Authentication failed. Check AE_FULLHUNT_API_KEY.",
        forbidden_hint="Access denied. Your FullHunt plan may not have access.",
    )


async def account_fh() -> str:
    """Call FullHunt auth status API."""
    if not _fh_key():
        return _missing_key()

    await FH_RATE_LIMITER.wait()

    return await request_json(
        platform="FullHunt",
        method="GET",
        url=f"{FH_BASE_URL}/auth/status",
        headers=_fh_headers(),
        auth_hint="Authentication failed. Check AE_FULLHUNT_API_KEY.",
        forbidden_hint="Access denied. Check your FullHunt API key.",
    )


def register_fullhunt_tools(server: FastMCP) -> None:
    """Register FullHunt tools on a FastMCP server."""

    @server.tool(
        name="fullhunt_domain",
        title="FullHunt Domain Details",
        description=(
            "Get domain attack surface details with GET /api/v1/domain/{domain}/details. "
            "Returns all discovered hosts with IPs, open ports, services, products "
            "(with CPE), SSL certificates, web technologies, cloud/CDN info, "
            "WHOIS data, and DNS records."
        ),
        structured_output=False,
    )
    async def fullhunt_domain(
        domain: Annotated[
            str,
            Field(description="Domain name, e.g. kaspersky.com."),
        ],
    ) -> str:
        return await domain_fh(domain=domain)

    @server.tool(
        name="fullhunt_subdomains",
        title="FullHunt Subdomains",
        description=(
            "Get subdomain list with GET /api/v1/domain/{domain}/subdomains. "
            "Returns discovered subdomain hostnames for the target domain."
        ),
        structured_output=False,
    )
    async def fullhunt_subdomains(
        domain: Annotated[
            str,
            Field(description="Domain name, e.g. example.com."),
        ],
    ) -> str:
        return await subdomains_fh(domain=domain)

    @server.tool(
        name="fullhunt_host",
        title="FullHunt Host Details",
        description=(
            "Get single host details with GET /api/v1/host/{host}. "
            "Returns IP, ports, services, products (CPE), SSL certificates, "
            "web technologies, HTTP info, cloud/CDN data, and DNS records."
        ),
        structured_output=False,
    )
    async def fullhunt_host(
        host: Annotated[
            str,
            Field(description="Full hostname, e.g. www.example.com."),
        ],
    ) -> str:
        return await host_fh(host=host)

    @server.tool(
        name="fullhunt_account",
        title="FullHunt Account Info",
        description=(
            "Get FullHunt account info with GET /api/v1/auth/status. "
            "Returns user plan, email, credits usage, remaining credits, "
            "and max results per request."
        ),
        structured_output=False,
    )
    async def fullhunt_account() -> str:
        return await account_fh()


def main() -> None:
    """Entry point for fullhunt-mcp."""
    server = FastMCP("surveyhub-fullhunt")
    register_fullhunt_tools(server)
    server.run()
