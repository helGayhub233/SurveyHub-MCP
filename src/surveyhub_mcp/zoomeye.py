"""ZoomEye MCP tools."""

from __future__ import annotations

import base64
import binascii
from typing import Annotated, Any, Literal

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
)
from .reference import register_reference_resources

ZOOMEYE_BASE_URL = "https://api.zoomeye.org"
ZOOMEYE_KEY_URL = "https://www.zoomeye.org -> Profile -> API Key"
ZOOMEYE_DEFAULT_FIELDS = "ip,port,domain,url,hostname,ssl.jarm,ssl.ja3s,update_time"
ZOOMEYE_FACETS = "country, subdivisions, city, product, service, device, os, port"
ZOOMEYE_RATE_LIMITER = AsyncRateLimiter(
    1.0, namespace="zoomeye-account", identity_provider=lambda: _zoomeye_key(),
)


def _zoomeye_key() -> str | None:
    return platform_key("ZOOMEYE_API_KEY")


def _missing_key() -> dict[str, Any]:
    return missing_env_message(
        platform="ZoomEye",
        env_var="ZOOMEYE_API_KEY",
        key_url=ZOOMEYE_KEY_URL,
    )


def _headers(*, json: bool = False) -> dict[str, str]:
    key = _zoomeye_key()
    headers = {"API-KEY": key} if key else {}
    if json:
        headers["Content-Type"] = "application/json"
    return headers


async def get_zoomeye_user_info() -> dict[str, Any]:
    """Call ZoomEye v2 user information API."""
    if not _zoomeye_key():
        return _missing_key()

    return await request_json(
        platform="ZoomEye",
        method="POST",
        url=f"{ZOOMEYE_BASE_URL}/v2/userinfo",
        rate_limiter=ZOOMEYE_RATE_LIMITER,
        headers=_headers(),
        auth_hint="Authentication failed. Check ZOOMEYE_API_KEY.",
        forbidden_hint="Access forbidden. Your ZoomEye paid account may not have sufficient permissions.",
    )


async def search_zoomeye_assets(
    *,
    query: str | None = None,
    qbase64: str | None = None,
    page: int = 1,
    pagesize: int = 10,
    fields: str = ZOOMEYE_DEFAULT_FIELDS,
    sub_type: Literal["v4", "v6", "web"] = "v4",
    facets: str | None = None,
    ignore_cache: bool = False,
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
    """Call the paid ZoomEye v2 asset search API."""
    if not _zoomeye_key():
        return _missing_key()

    if (query is None) == (qbase64 is None):
        return error_payload(
            platform="ZoomEye", message="Provide exactly one of query or qbase64.", error_type="validation_error",
        )
    if qbase64 is None:
        if not query or not query.strip():
            return error_payload(platform="ZoomEye", message="query must not be empty.", error_type="validation_error")
        qbase64 = encode_base64(query)
        executed_query = query
    else:
        try:
            executed_query = base64.b64decode(qbase64, validate=True).decode("utf-8")
        except (ValueError, binascii.Error, UnicodeDecodeError):
            return error_payload(platform="ZoomEye", message="qbase64 must encode a UTF-8 query using standard Base64; alternatively provide query for automatic encoding.", error_type="validation_error")
        if not executed_query.strip():
            return error_payload(platform="ZoomEye", message="qbase64 must encode a non-empty query.", error_type="validation_error")

    payload: dict[str, object] = {
        "qbase64": qbase64,
        "fields": fields,
        "sub_type": sub_type,
        "page": page,
        "pagesize": pagesize,
        "ignore_cache": ignore_cache,
    }
    if facets:
        payload["facets"] = facets

    result = await request_json(
        platform="ZoomEye",
        method="POST",
        url=f"{ZOOMEYE_BASE_URL}/v2/search",
        rate_limiter=ZOOMEYE_RATE_LIMITER,
        retry_non_idempotent=True,
        headers=_headers(json=True),
        json=payload,
        retry_mode=retry_mode,
        metered_request=True,
        force_retry=force_retry,
        auth_hint="Authentication failed. Check ZOOMEYE_API_KEY.",
        forbidden_hint="Access forbidden. This ZoomEye v2 endpoint requires sufficient paid account permissions and points.",
    )
    return enrich_payload(result, meta={"original_query": query, "executed_query": executed_query})


def register_zoomeye_tools(server: MCPServer) -> None:
    """Register ZoomEye tools on an MCP server."""

    @server.tool(
        name="zoomeye_user_info",
        title="Inspect ZoomEye Subscription and Remaining Points",
        description=(
            "Inspect the configured paid ZoomEye account's subscription, permissions, "
            "and remaining points. Use this before zoomeye_search when authorization or "
            "point capacity is uncertain; do not use it for asset discovery. This "
            "read-only operation requires a configured paid-account API key, retrieves "
            "only account metadata, and performs no asset search. Local account pacing "
            "is one call per second across processes sharing the state directory."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def zoomeye_user_info(    ) -> StructuredToolResult:
        return mcp_tool_result(await get_zoomeye_user_info())

    @server.tool(
        name="zoomeye_search",
        title="Search Paid ZoomEye v2 Cyberspace Assets",
        description=(
            "Search ZoomEye v2 assets using a paid account. Provide a raw query for "
            "automatic Base64 encoding, or qbase64 when it is already encoded; do not "
            "provide both. Free and legacy APIs are unsupported. This read-only remote "
            "request requires CN_ZOOMEYE_API_KEY and consumes ZoomEye points. ZoomEye "
            "correlation pivots use domain=, ip=, icp.number=, icp.name=, iconhash= "
            "(MD5 or MMH3), and ssl.cert.* fields; when remaining points are unknown in "
            "a multi-source scan, call zoomeye_user_info first. safe_only "
            "never repeats a read/write timeout; force_retry accepts possible duplicate "
            "point use. Each call returns one bounded page (maximum 1000 records); "
            "request later pages explicitly. Defaults include all-user hostname and "
            "SSL JARM/JA3S pivot fields; iconhash_md5 is available to request for "
            "Professional+ accounts but is not enabled by default. Local account pacing "
            "is one call per second; this is an MCP safeguard, not an upstream rate guarantee."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def zoomeye_search(
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Native ZoomEye v2 query. Use field=\"value\" and &&/||, never "
                    "Quake style field:\"value\" or AND/OR/NOT. For an ICP unit-name "
                    "seed, query icp.name=\"单位名称\" directly. Examples: "
                    'title="knownsec", port=443 && country="CN", '
                    'domain="example.com", icp.number="京ICP备10040895号-40", '
                    'after="2025-01-01" && icp.name="单位名称".'
                )
            ),
        ] = None,
        qbase64: Annotated[
            str | None,
            Field(description="Base64-encoded ZoomEye v2 query. Used as-is when provided."),
        ] = None,
        page: Annotated[int, Field(ge=1, description="Page number sorted by update time.")] = 1,
        pagesize: Annotated[
            int,
            Field(ge=1, le=1000, description="Results per page, capped at 1000 per MCP call (provider maximum is higher)."),
        ] = 10,
        fields: Annotated[
            str,
            Field(description="Comma-separated return fields, for example ip,port,domain,update_time."),
        ] = ZOOMEYE_DEFAULT_FIELDS,
        sub_type: Annotated[
            Literal["v4", "v6", "web"],
            Field(description="Asset data type: v4, v6, or web."),
        ] = "v4",
        facets: Annotated[
            str | None,
            Field(description=f"Comma-separated facet fields. Supported values: {ZOOMEYE_FACETS}."),
        ] = None,
        ignore_cache: Annotated[
            bool,
            Field(description="Whether to ignore cached data. Business plans and above support this."),
        ] = False,
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only retries only failures known to occur before sending; aggressive may consume points twice.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate point use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await search_zoomeye_assets(
            query=query,
            qbase64=qbase64,
            page=page,
            pagesize=pagesize,
            fields=fields,
            sub_type=sub_type,
            facets=facets,
            ignore_cache=ignore_cache,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))


def create_server() -> SurveyHubMCPServer:
    """Create a single-platform ZoomEye MCP server."""
    server = SurveyHubMCPServer(
        "zoomeye-mcp",
        title="ZoomEye MCP",
        description="ZoomEye cyberspace asset search and account APIs.",
        instructions="Use ZoomEye v2 tools as a paid-account asset query source.",
        version=__version__,
    )
    register_zoomeye_tools(server)
    register_reference_resources(server, ("zoomeye-syntax", "zoomeye-api"))
    return server


def main() -> None:
    """Run the ZoomEye MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
