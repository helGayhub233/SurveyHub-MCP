"""BinaryEdge MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

BE_BASE_URL = "https://api.binaryedge.io/v2"
BE_KEY_URL = "https://app.binaryedge.io/account"

BE_RATE_LIMITER = AsyncRateLimiter(1.0)


def _be_key() -> str | None:
    return platform_key("BINARYEDGE_API_KEY")


def _be_headers() -> dict[str, str]:
    """Return auth header if key is configured."""
    key = _be_key()
    return {"X-Key": key} if key else {}


def _missing_key() -> str:
    return missing_env_message(
        platform="BinaryEdge",
        env_var="PT_BINARYEDGE_API_KEY",
        key_url=BE_KEY_URL,
    )


async def search_be(
    *,
    query: str,
    page: int = 1,
) -> str:
    """Call BinaryEdge v2 search API."""
    if not _be_key():
        return _missing_key()

    await BE_RATE_LIMITER.wait()

    return await request_json(
        platform="BinaryEdge",
        method="GET",
        url=f"{BE_BASE_URL}/query/search",
        params={"query": query, "page": str(page)},
        headers=_be_headers(),
        auth_hint="Authentication failed. Check PT_BINARYEDGE_API_KEY.",
        forbidden_hint="Access forbidden. Your BinaryEdge plan may not have access to this endpoint.",
    )


async def subdomains_be(
    *,
    domain: str,
    page: int = 1,
) -> str:
    """Call BinaryEdge v2 subdomain enumeration API."""
    if not _be_key():
        return _missing_key()

    await BE_RATE_LIMITER.wait()

    return await request_json(
        platform="BinaryEdge",
        method="GET",
        url=f"{BE_BASE_URL}/query/domains/subdomain/{domain}",
        params={"page": str(page)},
        headers=_be_headers(),
        auth_hint="Authentication failed. Check PT_BINARYEDGE_API_KEY.",
        forbidden_hint="Access forbidden. Your BinaryEdge plan may not have access to this endpoint.",
    )


async def subscription_be() -> str:
    """Call BinaryEdge v2 subscription API."""
    if not _be_key():
        return _missing_key()

    await BE_RATE_LIMITER.wait()

    return await request_json(
        platform="BinaryEdge",
        method="GET",
        url=f"{BE_BASE_URL}/user/subscription",
        headers=_be_headers(),
        auth_hint="Authentication failed. Check PT_BINARYEDGE_API_KEY.",
        forbidden_hint="Access forbidden. Check your BinaryEdge API key.",
    )


def register_binaryedge_tools(server: FastMCP) -> None:
    """Register BinaryEdge tools on a FastMCP server."""

    @server.tool(
        name="binaryedge_search",
        title="BinaryEdge Search",
        description=(
            "Search BinaryEdge global data with GET /v2/query/search. "
            "Query syntax: product:nginx, country:CN, port:80, tags:cve. "
            "Supports AND/OR and full-text matching. Returns up to 10,000 results "
            "across 500 pages. Each result contains IP, port, protocol, product, "
            "version, country, and related scan metadata."
        ),
        structured_output=False,
    )
    async def binaryedge_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "Search query. Syntax: product:nginx, port:80, country:CN, "
                    "tags:cve, cve:CVE-2021-44228. Supports AND/OR."
                )
            ),
        ],
        page: Annotated[
            int,
            Field(ge=1, le=500, description="Page number (max 500 pages, 10,000 results)."),
        ] = 1,
    ) -> str:
        return await search_be(query=query, page=page)

    @server.tool(
        name="binaryedge_subdomains",
        title="BinaryEdge Subdomains",
        description=(
            "Enumerate subdomains via GET /v2/query/domains/subdomain/{domain}. "
            "Returns known subdomains discovered through passive DNS analysis. "
            "Supports pagination for large result sets."
        ),
        structured_output=False,
    )
    async def binaryedge_subdomains(
        domain: Annotated[
            str,
            Field(description="Target domain, e.g. example.com."),
        ],
        page: Annotated[
            int,
            Field(ge=1, description="Page number for paginated results."),
        ] = 1,
    ) -> str:
        return await subdomains_be(domain=domain, page=page)

    @server.tool(
        name="binaryedge_account",
        title="BinaryEdge Account Info",
        description=(
            "Get account subscription and quota information via GET /v2/user/subscription. "
            "Returns plan details, API quota usage, and remaining credits."
        ),
        structured_output=False,
    )
    async def binaryedge_account() -> str:
        return await subscription_be()


def main() -> None:
    """Entry point for binaryedge-mcp."""
    server = FastMCP("surveyhub-binaryedge")
    register_binaryedge_tools(server)
    server.run()
