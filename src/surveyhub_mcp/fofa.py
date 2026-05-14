"""FOFA MCP tools."""

from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, encode_base64, missing_env_message, request_json, split_csv

FOFA_BASE_URL = "https://fofa.info"
FOFA_KEY_URL = "https://fofa.info -> Personal Center -> API Key"

FOFA_SEARCH_FIELDS = (
    "ip, port, protocol, country, country_name, region, city, longitude, latitude, "
    "asn, org, host, domain, os, server, icp, title, jarm, header, banner, cert, "
    "base_protocol, link, cert.issuer.org, cert.issuer.cn, cert.subject.org, "
    "cert.subject.cn, tls.ja3s, tls.version, cert.sn, cert.not_before, "
    "cert.not_after, cert.domain, status_code, header_hash, banner_hash, "
    "banner_fid, cname, lastupdatetime, product, product_category, "
    "product.version, icon_hash, cert.is_valid, cname_domain, body, "
    "cert.is_match, cert.is_equal, icon, fid, structinfo"
)

FOFA_STATS_FIELDS = (
    "protocol, domain, port, title, os, server, country, asn, org, "
    "asset_type, fid, icp"
)
FOFA_STATS_RATE_LIMITER = AsyncRateLimiter(5.0)
FOFA_HOST_RATE_LIMITER = AsyncRateLimiter(1.0)


def _fofa_key() -> str | None:
    return os.getenv("FOFA_KEY")


def _missing_key() -> str:
    return missing_env_message(
        platform="FOFA",
        env_var="FOFA_KEY",
        optional_env="FOFA_EMAIL",
        key_url=FOFA_KEY_URL,
    )


def _add_fofa_auth(params: dict[str, str | int | bool]) -> dict[str, str | int | bool]:
    key = _fofa_key()
    if key:
        params["key"] = key

    email = os.getenv("FOFA_EMAIL")
    if email:
        params["email"] = email

    return params


def _validate_search_size(*, fields: str, size: int) -> str | None:
    requested_fields = set(split_csv(fields) or [])
    if "body" in requested_fields and size > 500:
        return 'FOFA search size must be <= 500 when fields includes "body".'
    if requested_fields.intersection({"cert", "banner"}) and size > 2000:
        return 'FOFA search size must be <= 2000 when fields includes "cert" or "banner".'
    return None


async def search_fofa(
    *,
    query: str,
    size: int = 100,
    page: int = 1,
    fields: str = "host,ip,port,domain,title",
    full: bool = False,
    r_type: str = "json",
) -> str:
    """Call FOFA normal page-based search API."""
    if not _fofa_key():
        return _missing_key()
    if error := _validate_search_size(fields=fields, size=size):
        return error

    params = _add_fofa_auth(
        {
            "qbase64": encode_base64(query),
            "size": size,
            "page": page,
            "fields": fields,
            "full": full,
            "r_type": r_type,
        }
    )

    return await request_json(
        platform="FOFA",
        method="GET",
        url=f"{FOFA_BASE_URL}/api/v1/search/all",
        params=params,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )


async def search_fofa_next(
    *,
    query: str,
    size: int = 100,
    next_id: str | None = None,
    fields: str = "host,ip,port,domain,title",
    full: bool = False,
    r_type: str = "json",
) -> str:
    """Call FOFA continuous pagination API."""
    if not _fofa_key():
        return _missing_key()
    if error := _validate_search_size(fields=fields, size=size):
        return error

    params = _add_fofa_auth(
        {
            "qbase64": encode_base64(query),
            "size": size,
            "fields": fields,
            "full": full,
            "r_type": r_type,
        }
    )
    if next_id:
        params["next"] = next_id

    return await request_json(
        platform="FOFA",
        method="GET",
        url=f"{FOFA_BASE_URL}/api/v1/search/next",
        params=params,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )


async def search_fofa_stats(*, query: str, fields: str = "protocol,domain,port") -> str:
    """Call FOFA statistics aggregation API."""
    if not _fofa_key():
        return _missing_key()

    params = _add_fofa_auth({"qbase64": encode_base64(query), "fields": fields})
    await FOFA_STATS_RATE_LIMITER.wait()

    return await request_json(
        platform="FOFA",
        method="GET",
        url=f"{FOFA_BASE_URL}/api/v1/search/stats",
        params=params,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )


async def get_fofa_host(*, host: str, detail: bool = False) -> str:
    """Call FOFA host aggregation API."""
    if not _fofa_key():
        return _missing_key()

    params = _add_fofa_auth({"detail": detail})
    await FOFA_HOST_RATE_LIMITER.wait()

    return await request_json(
        platform="FOFA",
        method="GET",
        url=f"{FOFA_BASE_URL}/api/v1/host/{quote(host, safe='')}",
        params=params,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )


async def get_fofa_user_info() -> str:
    """Call FOFA account information API."""
    if not _fofa_key():
        return _missing_key()

    params = _add_fofa_auth({})

    return await request_json(
        platform="FOFA",
        method="GET",
        url=f"{FOFA_BASE_URL}/api/v1/info/my",
        params=params,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )


def register_fofa_tools(server: FastMCP) -> None:
    """Register FOFA tools on a FastMCP server."""

    @server.tool(
        name="fofa_search",
        title="FOFA Search",
        description=(
            "Search FOFA assets with /api/v1/search/all. Query is encoded as qbase64. "
            f"Supported fields include: {FOFA_SEARCH_FIELDS}."
        ),
        structured_output=False,
    )
    async def fofa_search(
        query: Annotated[
            str,
            Field(description='FOFA query, for example body="admin" or domain="example.com" && port="443".'),
        ],
        size: Annotated[int, Field(ge=1, le=10000, description="Results per page.")] = 100,
        page: Annotated[int, Field(ge=1, description="Page number, starting from 1.")] = 1,
        fields: Annotated[str, Field(description="Comma-separated return fields.")] = "host,ip,port,domain,title",
        full: Annotated[bool, Field(description="Set true to search all data instead of one-year data.")] = False,
        r_type: Annotated[str, Field(description='Response type. Use "json" for JSON responses.')] = "json",
    ) -> str:
        return await search_fofa(
            query=query,
            size=size,
            page=page,
            fields=fields,
            full=full,
            r_type=r_type,
        )

    @server.tool(
        name="fofa_search_next",
        title="FOFA Continuous Search",
        description=(
            "Search FOFA assets with /api/v1/search/next. Use returned next value "
            "for stable continuous pagination over a large result set."
        ),
        structured_output=False,
    )
    async def fofa_search_next(
        query: Annotated[str, Field(description="FOFA query to encode as qbase64.")],
        size: Annotated[int, Field(ge=1, le=10000, description="Results per page.")] = 100,
        next_id: Annotated[str | None, Field(description="Next page token returned by the previous response.")] = None,
        fields: Annotated[str, Field(description="Comma-separated return fields.")] = "host,ip,port,domain,title",
        full: Annotated[bool, Field(description="Set true to search all data instead of one-year data.")] = False,
        r_type: Annotated[str, Field(description='Response type. Use "json" for JSON responses.')] = "json",
    ) -> str:
        return await search_fofa_next(
            query=query,
            size=size,
            next_id=next_id,
            fields=fields,
            full=full,
            r_type=r_type,
        )

    @server.tool(
        name="fofa_search_stats",
        title="FOFA Search Stats",
        description=(
            "Aggregate FOFA search results with /api/v1/search/stats. "
            "Calls are throttled to one request every 5 seconds in this MCP process. "
            f"Supported fields: {FOFA_STATS_FIELDS}."
        ),
        structured_output=False,
    )
    async def fofa_search_stats(
        query: Annotated[str, Field(description="FOFA query to encode as qbase64.")],
        fields: Annotated[
            str,
            Field(description="Comma-separated aggregation fields, for example protocol,domain,port."),
        ] = "protocol,domain,port",
    ) -> str:
        return await search_fofa_stats(query=query, fields=fields)

    @server.tool(
        name="fofa_host",
        title="FOFA Host Aggregation",
        description=(
            "Get FOFA host aggregation data with /api/v1/host/{host}. "
            "Calls are throttled to one request every 1 second in this MCP process."
        ),
        structured_output=False,
    )
    async def fofa_host(
        host: Annotated[str, Field(description="Host name or IP address, usually an IP.")],
        detail: Annotated[bool, Field(description="Set true to include port product details.")] = False,
    ) -> str:
        return await get_fofa_host(host=host, detail=detail)

    @server.tool(
        name="fofa_user_info",
        title="FOFA User Info",
        description="Get FOFA account status, quota, and membership information with /api/v1/info/my.",
        structured_output=False,
    )
    async def fofa_user_info() -> str:
        return await get_fofa_user_info()


def create_server() -> FastMCP:
    """Create a single-platform FOFA MCP server."""
    server = FastMCP(
        "fofa-mcp",
        instructions="Use FOFA tools for FOFA cyberspace asset search and account APIs.",
    )
    register_fofa_tools(server)
    return server


def main() -> None:
    """Run the FOFA MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
