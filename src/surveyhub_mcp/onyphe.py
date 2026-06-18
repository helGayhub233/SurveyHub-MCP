"""Onyphe MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

ON_BASE_URL = "https://www.onyphe.io/api/v2"
ON_KEY_URL = "https://www.onyphe.io/"

ON_RATE_LIMITER = AsyncRateLimiter(1.0)


def _on_key() -> str | None:
    return platform_key("ONYPHE_API_KEY")


def _on_headers() -> dict[str, str]:
    key = _on_key()
    return {"Authorization": f"bearer {key}"} if key else {}


def _missing_key() -> str:
    return missing_env_message(
        platform="Onyphe",
        env_var="FR_ONYPHE_API_KEY",
        key_url=ON_KEY_URL,
    )


async def search_on(
    *,
    query: str,
    page: int = 1,
) -> str:
    """Call Onyphe search API."""
    if not _on_key():
        return _missing_key()

    await ON_RATE_LIMITER.wait()

    return await request_json(
        platform="Onyphe",
        method="GET",
        url=f"{ON_BASE_URL}/search/",
        params={"q": query, "page": str(page)},
        headers=_on_headers(),
        auth_hint="Authentication failed. Check FR_ONYPHE_API_KEY.",
        forbidden_hint="Access denied. Your Onyphe plan may not have access.",
    )


async def summary_ip_on(
    *,
    ip: str,
) -> str:
    """Call Onyphe IP summary API."""
    if not _on_key():
        return _missing_key()

    await ON_RATE_LIMITER.wait()

    return await request_json(
        platform="Onyphe",
        method="GET",
        url=f"{ON_BASE_URL}/summary/ip/{ip}",
        headers=_on_headers(),
        auth_hint="Authentication failed. Check FR_ONYPHE_API_KEY.",
        forbidden_hint="Access denied. Your Onyphe plan may not have access.",
    )


async def summary_domain_on(
    *,
    domain: str,
) -> str:
    """Call Onyphe domain summary API."""
    if not _on_key():
        return _missing_key()

    await ON_RATE_LIMITER.wait()

    return await request_json(
        platform="Onyphe",
        method="GET",
        url=f"{ON_BASE_URL}/summary/domain/{domain}",
        headers=_on_headers(),
        auth_hint="Authentication failed. Check FR_ONYPHE_API_KEY.",
        forbidden_hint="Access denied. Your Onyphe plan may not have access.",
    )


async def user_on() -> str:
    """Call Onyphe user API."""
    if not _on_key():
        return _missing_key()

    await ON_RATE_LIMITER.wait()

    return await request_json(
        platform="Onyphe",
        method="GET",
        url=f"{ON_BASE_URL}/user",
        headers=_on_headers(),
        auth_hint="Authentication failed. Check FR_ONYPHE_API_KEY.",
        forbidden_hint="Access denied. Check your Onyphe API key.",
    )


def register_onyphe_tools(server: FastMCP) -> None:
    """Register Onyphe tools on a FastMCP server."""

    @server.tool(
        name="onyphe_search",
        title="Onyphe Search",
        description=(
            "Search Onyphe internet scan data with GET /api/v2/search/. "
            "Uses OQL (Onyphe Query Language). Covers datascan (open ports/services), "
            "synscan, resolver (DNS), geoloc, inetnum (WHOIS), threatlist, "
            "vulnscan (CISA KEV), ctl (certificates), and more. "
            "Max 10,000 results via page pagination. "
            "Query examples: protocol:rdp, domain:example.com, "
            "category:datascan ip:8.8.8.8, os:windows country:CN."
        ),
        structured_output=False,
    )
    async def onyphe_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "OQL query. Examples: protocol:rdp, domain:example.com, "
                    'ip:8.8.8.8, os:windows, country:CN, port:443, '
                    'app.http.title:"Admin".'
                )
            ),
        ],
        page: Annotated[
            int,
            Field(ge=1, description="Page number for paginated results."),
        ] = 1,
    ) -> str:
        return await search_on(query=query, page=page)

    @server.tool(
        name="onyphe_summary_ip",
        title="Onyphe IP Summary",
        description=(
            "Get IP asset summary with GET /api/v2/summary/ip/{ip}. "
            "Aggregates data from all categories (datascan, resolver, geoloc, "
            "inetnum, threatlist, pastries, sniffer, onionscan, vulnscan, whois) "
            "for the last 30 days. Returns the last 10 or 100 results per category "
            "depending on license."
        ),
        structured_output=False,
    )
    async def onyphe_summary_ip(
        ip: Annotated[str, Field(description="IPv4/IPv6 address, e.g. 8.8.8.8.")],
    ) -> str:
        return await summary_ip_on(ip=ip)

    @server.tool(
        name="onyphe_summary_domain",
        title="Onyphe Domain Summary",
        description=(
            "Get domain asset summary with GET /api/v2/summary/domain/{domain}. "
            "Returns aggregated data from resolver, ctl, datascan, threatlist, "
            "and whois categories for the given domain."
        ),
        structured_output=False,
    )
    async def onyphe_summary_domain(
        domain: Annotated[
            str,
            Field(description="Domain name, e.g. example.com."),
        ],
    ) -> str:
        return await summary_domain_on(domain=domain)

    @server.tool(
        name="onyphe_account",
        title="Onyphe Account Info",
        description=(
            "Get Onyphe account info with GET /api/v2/user. "
            "Returns license type, remaining credits, expiration date, "
            "available categories/fields, scan ports, and vulnscan CVE list."
        ),
        structured_output=False,
    )
    async def onyphe_account() -> str:
        return await user_on()


def main() -> None:
    """Entry point for onyphe-mcp."""
    server = FastMCP("surveyhub-onyphe")
    register_onyphe_tools(server)
    server.run()
