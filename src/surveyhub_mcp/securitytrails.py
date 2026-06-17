"""SecurityTrails MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

ST_BASE_URL = "https://api.securitytrails.com/v1"
ST_KEY_URL = "https://securitytrails.com/app/account/credentials"

ST_RATE_LIMITER = AsyncRateLimiter(1.0)


def _st_key() -> str | None:
    return platform_key("SECURITYTRAILS_API_KEY")


def _missing_key() -> str:
    return missing_env_message(
        platform="SecurityTrails",
        env_var="US_SECURITYTRAILS_API_KEY",
        key_url=ST_KEY_URL,
    )


async def domain_st(
    *,
    hostname: str,
) -> str:
    """Call SecurityTrails Get Domain API."""
    key = _st_key()
    if not key:
        return _missing_key()

    await ST_RATE_LIMITER.wait()

    return await request_json(
        platform="SecurityTrails",
        method="GET",
        url=f"{ST_BASE_URL}/domain/{hostname}",
        params={"apikey": key},
        auth_hint="Authentication failed. Check US_SECURITYTRAILS_API_KEY.",
        forbidden_hint="Access forbidden. Your SecurityTrails plan may not have access to this endpoint.",
    )


async def subdomains_st(
    *,
    hostname: str,
) -> str:
    """Call SecurityTrails List Subdomains API."""
    key = _st_key()
    if not key:
        return _missing_key()

    await ST_RATE_LIMITER.wait()

    return await request_json(
        platform="SecurityTrails",
        method="GET",
        url=f"{ST_BASE_URL}/domain/{hostname}/subdomains",
        params={"apikey": key},
        auth_hint="Authentication failed. Check US_SECURITYTRAILS_API_KEY.",
        forbidden_hint="Access forbidden. Your SecurityTrails plan may not have access to this endpoint.",
    )


def register_securitytrails_tools(server: FastMCP) -> None:
    """Register SecurityTrails tools on a FastMCP server."""

    @server.tool(
        name="securitytrails_domain",
        title="SecurityTrails Domain Info",
        description=(
            "Get current domain data with GET /v1/domain/{hostname}. "
            "Returns DNS records (A, AAAA, MX, NS, SOA, TXT), subdomain count, "
            "WHOIS info, nameservers, Alexa rank, associated IPs, and domain "
            "tags/categories. Also includes current DNS statistics showing how "
            "many other domains share the same DNS records."
        ),
        structured_output=False,
    )
    async def securitytrails_domain(
        hostname: Annotated[
            str,
            Field(description="Domain name to look up, e.g. example.com."),
        ],
    ) -> str:
        return await domain_st(hostname=hostname)

    @server.tool(
        name="securitytrails_subdomains",
        title="SecurityTrails Subdomains",
        description=(
            "List all subdomains for a domain via GET /v1/domain/{hostname}/subdomains. "
            "Returns subdomains found through DNS records, SSL certificates, "
            "and passive DNS analysis. Essential for attack surface mapping "
            "and asset discovery."
        ),
        structured_output=False,
    )
    async def securitytrails_subdomains(
        hostname: Annotated[
            str,
            Field(description="Domain name to enumerate subdomains for, e.g. example.com."),
        ],
    ) -> str:
        return await subdomains_st(hostname=hostname)


def main() -> None:
    """Entry point for securitytrails-mcp."""
    server = FastMCP("surveyhub-securitytrails")
    register_securitytrails_tools(server)
    server.run()
