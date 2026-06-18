"""Criminal IP MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

CI_BASE_URL = "https://api.criminalip.io/v1"
CI_KEY_URL = "https://www.criminalip.io/"

CI_RATE_LIMITER = AsyncRateLimiter(1.0)


def _ci_key() -> str | None:
    return platform_key("CRIMINALIP_API_KEY")


def _ci_headers() -> dict[str, str]:
    key = _ci_key()
    return {"x-api-key": key} if key else {}


def _missing_key() -> str:
    return missing_env_message(
        platform="Criminal IP",
        env_var="KR_CRIMINALIP_API_KEY",
        key_url=CI_KEY_URL,
    )


async def ip_ci(
    *,
    ip: str,
    full: bool = True,
) -> str:
    """Call Criminal IP asset IP report API."""
    if not _ci_key():
        return _missing_key()

    await CI_RATE_LIMITER.wait()

    return await request_json(
        platform="Criminal IP",
        method="GET",
        url=f"{CI_BASE_URL}/asset/ip/report",
        params={"ip": ip, "full": str(full).lower()},
        headers=_ci_headers(),
        auth_hint="Authentication failed. Check KR_CRIMINALIP_API_KEY.",
        forbidden_hint="Access denied. Your Criminal IP plan may not have access.",
    )


async def search_ci(
    *,
    query: str,
    offset: int = 0,
) -> str:
    """Call Criminal IP banner search API."""
    if not _ci_key():
        return _missing_key()

    await CI_RATE_LIMITER.wait()

    return await request_json(
        platform="Criminal IP",
        method="GET",
        url=f"{CI_BASE_URL}/banner/search",
        params={"query": query, "offset": str(offset)},
        headers=_ci_headers(),
        auth_hint="Authentication failed. Check KR_CRIMINALIP_API_KEY.",
        forbidden_hint="Access denied. Your Criminal IP plan may not have access.",
    )


async def domain_ci(
    *,
    domain: str,
) -> str:
    """Call Criminal IP domain reports API."""
    if not _ci_key():
        return _missing_key()

    await CI_RATE_LIMITER.wait()

    return await request_json(
        platform="Criminal IP",
        method="GET",
        url=f"{CI_BASE_URL}/domain/reports",
        params={"domain": domain},
        headers=_ci_headers(),
        auth_hint="Authentication failed. Check KR_CRIMINALIP_API_KEY.",
        forbidden_hint="Access denied. Your Criminal IP plan may not have access.",
    )


async def account_ci() -> str:
    """Call Criminal IP user/me API."""
    if not _ci_key():
        return _missing_key()

    await CI_RATE_LIMITER.wait()

    return await request_json(
        platform="Criminal IP",
        method="POST",
        url=f"{CI_BASE_URL}/user/me",
        headers=_ci_headers(),
        auth_hint="Authentication failed. Check KR_CRIMINALIP_API_KEY.",
        forbidden_hint="Access denied. Check your Criminal IP API key.",
    )


def register_criminalip_tools(server: FastMCP) -> None:
    """Register Criminal IP tools on a FastMCP server."""

    @server.tool(
        name="criminalip_ip",
        title="Criminal IP IP Report",
        description=(
            "Get comprehensive IP asset report with GET /v1/asset/ip/report. "
            "Returns open ports, service banners, SSL certificates, vulnerability info, "
            "malicious/suspicious scores, VPN/hosting detection, WHOIS data, "
            "and domain associations. Use full=true for complete data."
        ),
        structured_output=False,
    )
    async def criminalip_ip(
        ip: Annotated[str, Field(description="IPv4 address, e.g. 8.8.8.8.")],
        full: Annotated[
            bool,
            Field(description="Return full report with all detail sections."),
        ] = True,
    ) -> str:
        return await ip_ci(ip=ip, full=full)

    @server.tool(
        name="criminalip_search",
        title="Criminal IP Banner Search",
        description=(
            "Search internet-wide service banners with GET /v1/banner/search. "
            "Find IPs by service type, port, product, version, geolocation, "
            "vulnerability tags, and more. Supports pagination via offset. "
            "Example queries: protocol:rdp, port:3306, product:nginx, "
            "country:US, cve:CVE-2021-44228."
        ),
        structured_output=False,
    )
    async def criminalip_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "Search query with filter syntax. Examples: "
                    "protocol:rdp, port:3306, product:nginx, country:US, "
                    'title:"Admin Panel", cve:CVE-2021-44228.'
                )
            ),
        ],
        offset: Annotated[
            int,
            Field(ge=0, description="Offset for paginated results."),
        ] = 0,
    ) -> str:
        return await search_ci(query=query, offset=offset)

    @server.tool(
        name="criminalip_domain",
        title="Criminal IP Domain Reports",
        description=(
            "Get domain intelligence reports with GET /v1/domain/reports. "
            "Returns domain risk scores, web technologies, SSL certificates, "
            "subdomain info, phishing/malicious indicators, and abuse history."
        ),
        structured_output=False,
    )
    async def criminalip_domain(
        domain: Annotated[
            str,
            Field(description="Domain name, e.g. example.com."),
        ],
    ) -> str:
        return await domain_ci(domain=domain)

    @server.tool(
        name="criminalip_account",
        title="Criminal IP Account Info",
        description=(
            "Get Criminal IP account info with POST /v1/user/me. "
            "Returns user plan, credits balance, search quota, and membership tier."
        ),
        structured_output=False,
    )
    async def criminalip_account() -> str:
        return await account_ci()


def main() -> None:
    """Entry point for criminalip-mcp."""
    server = FastMCP("surveyhub-criminalip")
    register_criminalip_tools(server)
    server.run()
