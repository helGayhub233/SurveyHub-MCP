"""LeakIX MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

LX_BASE_URL = "https://leakix.net"
LX_KEY_URL = "https://leakix.net/"

LX_RATE_LIMITER = AsyncRateLimiter(1.0)


def _lx_key() -> str | None:
    return platform_key("LEAKIX_API_KEY")


def _lx_headers() -> dict[str, str]:
    key = _lx_key()
    return {"api-key": key, "accept": "application/json"} if key else {}


def _missing_key() -> str:
    return missing_env_message(
        platform="LeakIX",
        env_var="FR_LEAKIX_API_KEY",
        key_url=LX_KEY_URL,
    )


async def search_lx(
    *,
    scope: str,
    query: str,
    page: int = 0,
) -> str:
    """Call LeakIX search API."""
    if not _lx_key():
        return _missing_key()

    await LX_RATE_LIMITER.wait()

    return await request_json(
        platform="LeakIX",
        method="GET",
        url=f"{LX_BASE_URL}/search",
        params={"scope": scope, "q": query, "page": str(page)},
        headers=_lx_headers(),
        auth_hint="Authentication failed. Check FR_LEAKIX_API_KEY.",
        forbidden_hint="Access denied. Your LeakIX plan may not have access.",
    )


async def host_lx(
    *,
    ip: str,
) -> str:
    """Call LeakIX host details API."""
    if not _lx_key():
        return _missing_key()

    await LX_RATE_LIMITER.wait()

    return await request_json(
        platform="LeakIX",
        method="GET",
        url=f"{LX_BASE_URL}/host/{ip}",
        headers=_lx_headers(),
        auth_hint="Authentication failed. Check FR_LEAKIX_API_KEY.",
        forbidden_hint="Access denied. Your LeakIX plan may not have access.",
    )


async def subdomains_lx(
    *,
    domain: str,
) -> str:
    """Call LeakIX subdomains API."""
    if not _lx_key():
        return _missing_key()

    await LX_RATE_LIMITER.wait()

    return await request_json(
        platform="LeakIX",
        method="GET",
        url=f"{LX_BASE_URL}/api/subdomains/{domain}",
        headers=_lx_headers(),
        auth_hint="Authentication failed. Check FR_LEAKIX_API_KEY.",
        forbidden_hint="Access denied. Your LeakIX plan may not have access.",
    )


async def plugins_lx() -> str:
    """Call LeakIX plugins API."""
    if not _lx_key():
        return _missing_key()

    await LX_RATE_LIMITER.wait()

    return await request_json(
        platform="LeakIX",
        method="GET",
        url=f"{LX_BASE_URL}/api/plugins",
        headers=_lx_headers(),
        auth_hint="Authentication failed. Check FR_LEAKIX_API_KEY.",
        forbidden_hint="Access denied. Your LeakIX plan may not have access.",
    )


def register_leakix_tools(server: FastMCP) -> None:
    """Register LeakIX tools on a FastMCP server."""

    @server.tool(
        name="leakix_search",
        title="LeakIX Search",
        description=(
            "Search LeakIX internet scan data with GET /search. "
            "Uses YQL (Yaml Query Language) syntax. "
            "Supports service scope (open ports/services/SSL/certificates) "
            "and leak scope (misconfigured/vulnerable servers, data leaks). "
            "Query examples: +plugin:ElasticSearchOpenPlugin, "
            '+protocol:rdp +country:"France", '
            "+service.software.name:Apache."
        ),
        structured_output=False,
    )
    async def leakix_search(
        scope: Annotated[
            str,
            Field(
                description='Scope: "service" for exposed services, "leak" for data leaks/vulnerabilities.'
            ),
        ],
        query: Annotated[
            str,
            Field(
                description=(
                    "YQL query. Examples: +plugin:ElasticSearchOpenPlugin, "
                    '+protocol:rdp, +country:"France", '
                    "+service.software.name:Apache +port:8080. "
                    "Prefixes: +required, -exclude, no prefix = optional (OR)."
                )
            ),
        ],
        page: Annotated[
            int,
            Field(ge=0, description="Page number starting from 0."),
        ] = 0,
    ) -> str:
        return await search_lx(scope=scope, query=query, page=page)

    @server.tool(
        name="leakix_host",
        title="LeakIX Host Details",
        description=(
            "Get host details with GET /host/{ip}. "
            "Returns all Services and Leaks discovered on the IP. "
            "Includes ports, protocols, SSL certificates, software info, "
            "geolocation, and leak severity data."
        ),
        structured_output=False,
    )
    async def leakix_host(
        ip: Annotated[str, Field(description="IPv4 address, e.g. 8.8.8.8.")],
    ) -> str:
        return await host_lx(ip=ip)

    @server.tool(
        name="leakix_subdomains",
        title="LeakIX Subdomain Discovery",
        description=(
            "Discover subdomains with GET /api/subdomains/{domain}. "
            "Returns subdomain name, distinct IP count, and last seen date. "
            "Free tier: up to 50 results, Pro: up to 1,000."
        ),
        structured_output=False,
    )
    async def leakix_subdomains(
        domain: Annotated[
            str,
            Field(description="Domain name, e.g. example.com."),
        ],
    ) -> str:
        return await subdomains_lx(domain=domain)

    @server.tool(
        name="leakix_plugins",
        title="LeakIX Plugin List",
        description=(
            "List all LeakIX detection plugins with GET /api/plugins. "
            "Shows plugin name, description, and event counts (1h/24h/7d). "
            "Useful for discovering what types of services/leaks LeakIX detects "
            "and constructing targeted YQL queries with +plugin:PluginName."
        ),
        structured_output=False,
    )
    async def leakix_plugins() -> str:
        return await plugins_lx()


def main() -> None:
    """Entry point for leakix-mcp."""
    server = FastMCP("surveyhub-leakix")
    register_leakix_tools(server)
    server.run()
