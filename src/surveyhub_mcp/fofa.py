"""FOFA MCP tools."""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote

from mcp.server import MCPServer
from pydantic import Field

from . import __version__
from .common import (
    METERED_READ_ONLY_REMOTE_TOOL,
    READ_ONLY_REMOTE_TOOL,
    AsyncRateLimiter,
    StructuredToolResult,
    SurveyHubMCPServer,
    encode_base64,
    enrich_payload,
    error_payload,
    mcp_tool_result,
    missing_env_message,
    platform_key,
    request_json,
    split_csv,
)
from .reference import register_reference_resources

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
FOFA_SEARCH_RATE_LIMITER = AsyncRateLimiter(0.6)


def _fofa_key() -> str | None:
    return platform_key("FOFA_KEY")


def _missing_key() -> dict[str, Any]:
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

    email = platform_key("FOFA_EMAIL")
    if email:
        params["email"] = email

    return params


def _validate_search_size(*, fields: str, size: int) -> dict[str, Any] | None:
    requested_fields = set(split_csv(fields) or [])
    if "body" in requested_fields and size > 500:
        return error_payload(
            platform="FOFA",
            message='FOFA search size must be <= 500 when fields includes "body".',
            error_type="validation_error",
            details={"fields": fields, "size": size},
        )
    if requested_fields.intersection({"cert", "banner"}) and size > 2000:
        return error_payload(
            platform="FOFA",
            message='FOFA search size must be <= 2000 when fields includes "cert" or "banner".',
            error_type="validation_error",
            details={"fields": fields, "size": size},
        )
    return None


async def _request_fofa_search(
    *,
    url: str,
    params: dict[str, str | int | bool],
    query: str,
    full: bool,
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
    """Run one FOFA search without assigning semantics to undocumented fields."""
    result = await request_json(
        platform="FOFA",
        method="GET",
        url=url,
        rate_limiter=FOFA_SEARCH_RATE_LIMITER,
        params=params,
        retry_mode=retry_mode,
        metered_request=True,
        force_retry=force_retry,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )

    execution = dict(result.get("meta", {}).get("execution", {}))
    if full and result.get("ok"):
        execution["completeness"] = {
            "state": "unknown",
            "reason": "provider_did_not_acknowledge_full_range",
        }

    return enrich_payload(
        result,
        meta={
            "original_query": query,
            "executed_query": query,
            "partial_data": None,
            "execution": execution,
        },
        warnings=([{
            "type": "full_range_unverified",
            "message": "FOFA returned data but did not provide a documented acknowledgement that full-range search was applied.",
            "details": {"requested_full": True},
        }] if full and result.get("ok") else None),
    )


async def search_fofa(
    *,
    query: str,
    size: int = 100,
    page: int = 1,
    fields: str = "host,ip,port,domain,title",
    full: bool = False,
    r_type: str = "json",
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
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

    return await _request_fofa_search(
        url=f"{FOFA_BASE_URL}/api/v1/search/all",
        params=params,
        query=query,
        full=full,
        retry_mode=retry_mode,
        force_retry=force_retry,
    )


async def search_fofa_next(
    *,
    query: str,
    size: int = 100,
    next_id: str | None = None,
    fields: str = "host,ip,port,domain,title",
    full: bool = False,
    r_type: str = "json",
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
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

    return await _request_fofa_search(
        url=f"{FOFA_BASE_URL}/api/v1/search/next",
        params=params,
        query=query,
        full=full,
        retry_mode=retry_mode,
        force_retry=force_retry,
    )


async def search_fofa_stats(*, query: str, fields: str = "protocol,domain,port") -> dict[str, Any]:
    """Call FOFA statistics aggregation API."""
    if not _fofa_key():
        return _missing_key()

    params = _add_fofa_auth({"qbase64": encode_base64(query), "fields": fields})

    return await request_json(
        platform="FOFA",
        method="GET",
        url=f"{FOFA_BASE_URL}/api/v1/search/stats",
        rate_limiter=FOFA_STATS_RATE_LIMITER,
        params=params,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )


async def get_fofa_host(*, host: str, detail: bool = False) -> dict[str, Any]:
    """Call FOFA host aggregation API."""
    if not _fofa_key():
        return _missing_key()

    params = _add_fofa_auth({"detail": detail})

    return await request_json(
        platform="FOFA",
        method="GET",
        url=f"{FOFA_BASE_URL}/api/v1/host/{quote(host, safe='')}",
        rate_limiter=FOFA_HOST_RATE_LIMITER,
        params=params,
        auth_hint="Authentication failed. Check FOFA_KEY and FOFA_EMAIL if you use it.",
        forbidden_hint="Access forbidden. Your FOFA account may not have sufficient permissions.",
    )


async def get_fofa_user_info() -> dict[str, Any]:
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


def register_fofa_tools(server: MCPServer) -> None:
    """Register FOFA tools on an MCP server."""

    @server.tool(
        name="fofa_search",
        title="Search FOFA Assets by Page",
        description=(
            "Search FOFA assets with page-based pagination and selectable return fields. "
            "Use fofa_search_next for stable continuous pagination over a large result "
            "set, fofa_host for one host, or fofa_search_stats for aggregation. The "
            "query is Base64-encoded automatically; this read-only request consumes "
            "FOFA account quota, requires CN_FOFA_KEY, and is throttled to one call "
            "every 0.6 seconds. FOFA correlation pivots use domain=, ip=, icp=, "
            "icon_hash=, and cert= joined with &&; when remaining quota is unknown in a "
            "multi-source scan, call fofa_user_info first. safe_only never repeats a "
            "read/write timeout; use "
            "force_retry only when duplicate quota use is acceptable. full=true is "
            "reported as unverified unless FOFA explicitly acknowledges its range."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
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
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only retries only failures known to occur before sending the request; aggressive may duplicate quota use.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate quota use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await search_fofa(
            query=query,
            size=size,
            page=page,
            fields=fields,
            full=full,
            r_type=r_type,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))

    @server.tool(
        name="fofa_search_next",
        title="Search FOFA Assets with Cursor Pagination",
        description=(
            "Search FOFA assets using a stable next-token cursor for large result sets. "
            "Use fofa_search for ordinary page-based browsing. Pass the returned next "
            "value as next_id; this read-only request consumes FOFA account quota and "
            "requires CN_FOFA_KEY. It is throttled to one call every 0.6 seconds; "
            "safe_only never repeats a read/write timeout, and force_retry accepts "
            "possible duplicate quota use."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def fofa_search_next(
        query: Annotated[str, Field(description="FOFA query to encode as qbase64.")],
        size: Annotated[int, Field(ge=1, le=10000, description="Results per page.")] = 100,
        next_id: Annotated[str | None, Field(description="Next page token returned by the previous response.")] = None,
        fields: Annotated[str, Field(description="Comma-separated return fields.")] = "host,ip,port,domain,title",
        full: Annotated[bool, Field(description="Set true to search all data instead of one-year data.")] = False,
        r_type: Annotated[str, Field(description='Response type. Use "json" for JSON responses.')] = "json",
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only retries only failures known to occur before sending the request; aggressive may duplicate quota use.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate quota use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await search_fofa_next(
            query=query,
            size=size,
            next_id=next_id,
            fields=fields,
            full=full,
            r_type=r_type,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))

    @server.tool(
        name="fofa_search_stats",
        title="Aggregate FOFA Asset Search Statistics",
        description=(
            "Aggregate FOFA search results into counts for selected fields. Use "
            "fofa_search when individual asset records are required. This read-only "
            "request consumes FOFA quota and is throttled to one call every 5 seconds "
            "in this MCP process."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def fofa_search_stats(
        query: Annotated[str, Field(description="FOFA query to encode as qbase64.")],
        fields: Annotated[
            str,
            Field(description="Comma-separated aggregation fields, for example protocol,domain,port."),
        ] = "protocol,domain,port",
    ) -> StructuredToolResult:
        return mcp_tool_result(await search_fofa_stats(query=query, fields=fields))

    @server.tool(
        name="fofa_host",
        title="Inspect One FOFA Host and Its Services",
        description=(
            "Get FOFA aggregation data for one hostname or IP address. Use fofa_search "
            "for query-based discovery across multiple assets. This read-only request "
            "consumes FOFA quota and is throttled to one call per second."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def fofa_host(
        host: Annotated[str, Field(description="Host name or IP address, usually an IP.")],
        detail: Annotated[bool, Field(description="Set true to include port product details.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await get_fofa_host(host=host, detail=detail))

    @server.tool(
        name="fofa_user_info",
        title="Inspect FOFA Account and Remaining Quota",
        description=(
            "Inspect the configured FOFA account's status, remaining query quota, and "
            "membership details. Use this before fofa_search, fofa_search_next, or "
            "fofa_search_stats when authorization or capacity is uncertain; do not use "
            "it for asset discovery. This read-only operation requires configured FOFA "
            "credentials, retrieves only account metadata, and performs no asset search."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def fofa_user_info(    ) -> StructuredToolResult:
        return mcp_tool_result(await get_fofa_user_info())


def create_server() -> SurveyHubMCPServer:
    """Create a single-platform FOFA MCP server."""
    server = SurveyHubMCPServer(
        "fofa-mcp",
        title="FOFA MCP",
        description="FOFA cyberspace asset search and account APIs.",
        instructions="Use FOFA tools for FOFA cyberspace asset search and account APIs.",
        version=__version__,
    )
    register_fofa_tools(server)
    register_reference_resources(server, ("fofa-syntax", "fofa-api"))
    return server


def main() -> None:
    """Run the FOFA MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
