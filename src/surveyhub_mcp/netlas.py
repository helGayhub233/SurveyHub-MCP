"""Netlas MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

NL_BASE_URL = "https://app.netlas.io/api"
NL_KEY_URL = "https://app.netlas.io/profile/"

NL_RATE_LIMITER = AsyncRateLimiter(1.0)


def _nl_key() -> str | None:
    return platform_key("NETLAS_API_KEY")


def _nl_headers() -> dict[str, str]:
    key = _nl_key()
    return {"Authorization": f"Bearer {key}"} if key else {}


def _missing_key() -> str:
    return missing_env_message(
        platform="Netlas",
        env_var="CY_NETLAS_API_KEY",
        key_url=NL_KEY_URL,
    )


async def responses_nl(
    *,
    query: str,
    start: int = 0,
) -> str:
    """Call Netlas responses search API."""
    if not _nl_key():
        return _missing_key()

    await NL_RATE_LIMITER.wait()

    return await request_json(
        platform="Netlas",
        method="GET",
        url=f"{NL_BASE_URL}/responses/",
        params={"q": query, "start": str(start)},
        headers=_nl_headers(),
        auth_hint="Authentication failed. Check CY_NETLAS_API_KEY.",
        forbidden_hint="Access denied. Your Netlas plan may not have access.",
    )


async def domains_nl(
    *,
    query: str,
    start: int = 0,
) -> str:
    """Call Netlas domains search API."""
    if not _nl_key():
        return _missing_key()

    await NL_RATE_LIMITER.wait()

    return await request_json(
        platform="Netlas",
        method="GET",
        url=f"{NL_BASE_URL}/domains/",
        params={"q": query, "start": str(start)},
        headers=_nl_headers(),
        auth_hint="Authentication failed. Check CY_NETLAS_API_KEY.",
        forbidden_hint="Access denied. Your Netlas plan may not have DNS access.",
    )


async def profile_nl() -> str:
    """Call Netlas user profile API."""
    if not _nl_key():
        return _missing_key()

    await NL_RATE_LIMITER.wait()

    return await request_json(
        platform="Netlas",
        method="GET",
        url=f"{NL_BASE_URL}/users/profile_data/",
        headers=_nl_headers(),
        auth_hint="Authentication failed. Check CY_NETLAS_API_KEY.",
        forbidden_hint="Access denied. Check your Netlas API key.",
    )


def register_netlas_tools(server: FastMCP) -> None:
    """Register Netlas tools on a FastMCP server."""

    @server.tool(
        name="netlas_search",
        title="Netlas Internet Scan Search",
        description=(
            "Search Netlas internet scan data with GET /api/responses/. "
            "Find internet-facing assets by IP, domain, port, protocol, "
            "product, HTTP title/body, SSL certificate, JARM fingerprint, "
            "and geographic location. Uses Lucene query syntax. "
            "Max 10,000 results via `start` offset pagination (0–9980). "
            "Query examples: host:example.com, port:443 protocol:http, "
            "http.title:\"Login\", certificate.subject_dn:\"*.example.com\"."
        ),
        structured_output=False,
    )
    async def netlas_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "Lucene query. Examples: host:example.com, port:443, "
                    "protocol:http, http.title:\"Admin\", "
                    "certificate.subject_dn:\"*.example.com\"."
                )
            ),
        ],
        start: Annotated[
            int,
            Field(ge=0, le=9980, description="Pagination offset (0–9980, step 20)."),
        ] = 0,
    ) -> str:
        return await responses_nl(query=query, start=start)

    @server.tool(
        name="netlas_domain",
        title="Netlas DNS Search",
        description=(
            "Search Netlas DNS records with GET /api/domains/. "
            "Find domains by DNS records: A, AAAA, NS, MX, TXT, CNAME. "
            "Supports wildcard: domain:*.example.com. "
            "Returns domain, zone, level, and all DNS record types."
        ),
        structured_output=False,
    )
    async def netlas_domain(
        query: Annotated[
            str,
            Field(
                description=(
                    "Lucene query. Examples: domain:example.com, "
                    "domain:*.example.com a:*, ns:*.google*.com."
                )
            ),
        ],
        start: Annotated[
            int,
            Field(ge=0, le=9980, description="Pagination offset (0–9980)."),
        ] = 0,
    ) -> str:
        return await domains_nl(query=query, start=start)

    @server.tool(
        name="netlas_account",
        title="Netlas Account Info",
        description=(
            "Get Netlas account profile and quota via GET /api/users/profile_data/. "
            "Returns requests_left, coins balance, scan_coins, "
            "and next refresh time."
        ),
        structured_output=False,
    )
    async def netlas_account() -> str:
        return await profile_nl()


def main() -> None:
    """Entry point for netlas-mcp."""
    server = FastMCP("surveyhub-netlas")
    register_netlas_tools(server)
    server.run()
