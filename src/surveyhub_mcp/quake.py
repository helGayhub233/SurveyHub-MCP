"""Quake MCP tools."""

from __future__ import annotations

import os
from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from . import __version__
from .common import (
    METERED_READ_ONLY_REMOTE_TOOL,
    READ_ONLY_REMOTE_TOOL,
    AsyncRateLimiter,
    StructuredToolResult,
    SurveyHubMCPServer,
    enrich_payload,
    error_payload,
    mcp_tool_result,
    missing_env_message,
    platform_key,
    request_json,
    split_csv,
)
from .reference import register_reference_resources

QUAKE_BASE_URL = "https://quake.360.net"
QUAKE_KEY_URL = "https://quake.360.net -> Personal Center -> Key Management"

QUAKE_FILTERABLE_FIELDS = (
    "components.product_level, components.product_catalog, location.country_cn, "
    "domain, service.http.favicon.hash, service.http.host, components.product_vendor, "
    "location.city_en, service.http.title, service.name, time, location.isp, "
    "transport, location.province_en, components.product_name_cn, asn, "
    "location.city_cn, location.province_cn, service.http.status_code, "
    "service.http.infomation.mail, org, service.http.icp.main_licence.unit, "
    "location.district_cn, service.cert, service.http.server, hostname, "
    "service.http.body, components.product_type, location.district_en, "
    "service.http.favicon.data, ip, service.http.icp.licence, components.version, "
    "location.country_en, port, service.response"
)
QUAKE_FILTERABLE_FIELD_SET = frozenset(field.strip() for field in QUAKE_FILTERABLE_FIELDS.split(","))
QUAKE_FILTER_FIELDS_DESCRIPTION = (
    "Comma-separated official Quake service fields. Unsupported names are removed and returned as warnings. "
    f"Supported values: {QUAKE_FILTERABLE_FIELDS}."
)

QUAKE_AGGREGATION_FIELDS = (
    "ip, port, service, product, os, asn, org, title, server, app, catalog, "
    "type, level, vendor, isp, status_code, powered_by, meta_keywords, "
    "page_type, icp, app_and_version, service_and_version, unique_ip, "
    "unique_domain, unique_port, unique_product, unique_asn, unique_org, "
    "unique_isp, unique_title, unique_server, unique_app, unique_catalog, "
    "unique_type, unique_level, unique_vendor, unique_country, unique_province, "
    "unique_city, province, province_cn, country, country_cn, country_code, "
    "city, city_cn, district, district_cn, province_of_china"
)

QUAKE_RATE_LIMITER = AsyncRateLimiter(5.0)


def _quake_key() -> str | None:
    return platform_key("QUAKE_KEY")


def _missing_key() -> dict[str, Any]:
    return missing_env_message(
        platform="Quake",
        env_var="QUAKE_KEY",
        key_url=QUAKE_KEY_URL,
    )


def _headers(*, json: bool = False) -> dict[str, str]:
    key = _quake_key()
    headers = {"X-QuakeToken": key} if key else {}
    if json:
        headers["Content-Type"] = "application/json"
    return headers


def _put_if_value(payload: dict[str, object], key: str, value: object | None) -> None:
    if value is not None and value != "":
        payload[key] = value


def _put_csv(payload: dict[str, object], key: str, value: str | None) -> None:
    if items := split_csv(value):
        payload[key] = items


def _filter_service_fields(value: str | None, *, parameter: str) -> tuple[str | None, dict[str, Any] | None]:
    """Remove Quake fields that the official filterable-fields endpoint does not accept."""
    requested = split_csv(value) or []
    accepted = [field for field in requested if field in QUAKE_FILTERABLE_FIELD_SET]
    removed = [field for field in requested if field not in QUAKE_FILTERABLE_FIELD_SET]
    warning = None
    if removed:
        warning = {
            "type": "unsupported_filter_fields",
            "message": f"Removed unsupported Quake {parameter} fields before sending the request.",
            "details": {
                "parameter": parameter,
                "removed_fields": removed,
                "accepted_fields": accepted,
                "official_source": "/api/v3/filterable/field/quake_service",
            },
        }
    return (",".join(accepted) or None), warning


def _prepare_service_fields(include: str | None, exclude: str | None) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    prepared_include, include_warning = _filter_service_fields(include, parameter="include")
    prepared_exclude, exclude_warning = _filter_service_fields(exclude, parameter="exclude")
    warnings = [warning for warning in (include_warning, exclude_warning) if warning]
    return prepared_include, prepared_exclude, warnings


def _retry_quota_warning(result: dict[str, Any]) -> list[dict[str, Any]]:
    attempts = result.get("meta", {}).get("attempts", 1)
    quota_risk = result.get("meta", {}).get("execution", {}).get("quota", {}).get("risk", "none")
    if not isinstance(attempts, int) or attempts <= 1 or quota_risk == "none":
        return []
    return [{
        "type": "retry_may_consume_quota",
        "message": "Quake required multiple HTTP attempts and at least one attempt has unknown quota impact.",
        "details": {"attempts": attempts, "quota_risk": quota_risk},
    }]


def _service_payload(
    *,
    query: str,
    size: int | None = None,
    start: int | None = None,
    pagination_id: str | None = None,
    rule: str | None = None,
    ip_list: str | None = None,
    include: str | None = None,
    exclude: str | None = None,
    shortcuts: str | None = None,
    ignore_cache: bool = False,
    latest: bool = True,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "query": query,
        "ignore_cache": ignore_cache,
        "latest": latest,
    }

    _put_if_value(payload, "size", size)
    _put_if_value(payload, "start", start)
    _put_if_value(payload, "pagination_id", pagination_id)
    _put_if_value(payload, "rule", rule)
    _put_if_value(payload, "start_time", start_time)
    _put_if_value(payload, "end_time", end_time)
    _put_csv(payload, "ip_list", ip_list)
    _put_csv(payload, "include", include)
    _put_csv(payload, "exclude", exclude)
    _put_csv(payload, "shortcuts", shortcuts)

    return payload


async def get_quake_user_info() -> dict[str, Any]:
    """Call Quake user information API."""
    if not _quake_key():
        return _missing_key()

    return await request_json(
        platform="Quake",
        method="GET",
        url=f"{QUAKE_BASE_URL}/api/v3/user/info",
        rate_limiter=QUAKE_RATE_LIMITER,
        headers=_headers(),
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions.",
    )


async def get_quake_filterable_fields() -> dict[str, Any]:
    """Call Quake service filterable fields API."""
    if not _quake_key():
        return _missing_key()

    return await request_json(
        platform="Quake",
        method="GET",
        url=f"{QUAKE_BASE_URL}/api/v3/filterable/field/quake_service",
        rate_limiter=QUAKE_RATE_LIMITER,
        headers=_headers(),
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions.",
    )


async def search_quake_service(
    *,
    query: str,
    start: int = 0,
    size: int = 10,
    rule: str | None = None,
    ip_list: str | None = None,
    include: str | None = None,
    exclude: str | None = None,
    shortcuts: str | None = None,
    ignore_cache: bool = False,
    latest: bool = True,
    start_time: str | None = None,
    end_time: str | None = None,
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
    """Call Quake real-time service search API."""
    if not _quake_key():
        return _missing_key()

    include, exclude, warnings = _prepare_service_fields(include, exclude)
    payload = _service_payload(
        query=query,
        start=start,
        size=size,
        rule=rule,
        ip_list=ip_list,
        include=include,
        exclude=exclude,
        shortcuts=shortcuts,
        ignore_cache=ignore_cache,
        latest=latest,
        start_time=start_time,
        end_time=end_time,
    )

    result = await request_json(
        platform="Quake",
        method="POST",
        url=f"{QUAKE_BASE_URL}/api/v3/search/quake_service",
        rate_limiter=QUAKE_RATE_LIMITER,
        retry_mode=retry_mode,
        metered_request=True,
        force_retry=force_retry,
        headers=_headers(json=True),
        json=payload,
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions or credits.",
    )
    return enrich_payload(
        result,
        meta={"original_query": query, "executed_query": query},
        warnings=[*warnings, *_retry_quota_warning(result)],
    )


async def scroll_quake_service(
    *,
    query: str,
    size: int = 100,
    pagination_id: str | None = None,
    rule: str | None = None,
    ip_list: str | None = None,
    include: str | None = None,
    exclude: str | None = None,
    shortcuts: str | None = None,
    ignore_cache: bool = False,
    latest: bool = True,
    start_time: str | None = None,
    end_time: str | None = None,
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
    """Call Quake scroll service search API."""
    if not _quake_key():
        return _missing_key()

    include, exclude, warnings = _prepare_service_fields(include, exclude)
    payload = _service_payload(
        query=query,
        size=size,
        pagination_id=pagination_id,
        rule=rule,
        ip_list=ip_list,
        include=include,
        exclude=exclude,
        shortcuts=shortcuts,
        ignore_cache=ignore_cache,
        latest=latest,
        start_time=start_time,
        end_time=end_time,
    )

    result = await request_json(
        platform="Quake",
        method="POST",
        url=f"{QUAKE_BASE_URL}/api/v3/scroll/quake_service",
        rate_limiter=QUAKE_RATE_LIMITER,
        retry_mode=retry_mode,
        metered_request=True,
        force_retry=force_retry,
        headers=_headers(json=True),
        json=payload,
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions or credits.",
    )
    return enrich_payload(
        result,
        meta={"original_query": query, "executed_query": query},
        warnings=[*warnings, *_retry_quota_warning(result)],
    )


async def get_quake_aggregation_fields() -> dict[str, Any]:
    """Call Quake aggregation fields API."""
    if not _quake_key():
        return _missing_key()

    return await request_json(
        platform="Quake",
        method="GET",
        url=f"{QUAKE_BASE_URL}/api/v3/aggregation/quake_service",
        rate_limiter=QUAKE_RATE_LIMITER,
        headers=_headers(),
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions.",
    )


async def aggregate_quake_service(
    *,
    query: str,
    aggregation_list: str,
    size: int = 5,
    rule: str | None = None,
    ip_list: str | None = None,
    ignore_cache: bool = False,
    latest: bool = True,
    start_time: str | None = None,
    end_time: str | None = None,
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
    """Call Quake service aggregation API."""
    if not _quake_key():
        return _missing_key()

    aggregations = split_csv(aggregation_list)
    if not aggregations:
        return error_payload(
            platform="Quake",
            message="aggregation_list is required. Provide one or two comma-separated aggregation fields.",
            error_type="validation_error",
        )
    if len(aggregations) > 2:
        return error_payload(
            platform="Quake",
            message="aggregation_list supports at most two fields.",
            error_type="validation_error",
            details={"aggregation_list": aggregation_list},
        )

    payload: dict[str, object] = {
        "query": query,
        "size": size,
        "ignore_cache": ignore_cache,
        "latest": latest,
        "aggregation_list": aggregations,
    }
    _put_if_value(payload, "rule", rule)
    _put_if_value(payload, "start_time", start_time)
    _put_if_value(payload, "end_time", end_time)
    _put_csv(payload, "ip_list", ip_list)

    result = await request_json(
        platform="Quake",
        method="POST",
        url=f"{QUAKE_BASE_URL}/api/v3/aggregation/quake_service",
        rate_limiter=QUAKE_RATE_LIMITER,
        retry_mode=retry_mode,
        metered_request=True,
        force_retry=force_retry,
        headers=_headers(json=True),
        json=payload,
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions or credits.",
    )
    return enrich_payload(
        result,
        meta={"original_query": query, "executed_query": query},
        warnings=_retry_quota_warning(result),
    )


def register_quake_tools(server: MCPServer) -> None:
    """Register Quake tools on an MCP server."""

    @server.tool(
        name="quake_user_info",
        title="Inspect Quake Account and Remaining Credits",
        description=(
            "Get Quake account details, remaining quota, token status, and role "
            "information. Use this before searches when permissions or credits are "
            "uncertain; do not use it for asset discovery. This read-only account "
            "lookup requires CN_QUAKE_KEY, consumes no search result, and is throttled "
            "to one call every 5 seconds."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def quake_user_info(    ) -> StructuredToolResult:
        return mcp_tool_result(await get_quake_user_info())

    @server.tool(
        name="quake_filterable_fields",
        title="List Quake Service Search Filter Fields",
        description=(
            "List Quake service fields accepted by the include and exclude parameters "
            "of search tools. Use quake_aggregation_fields instead when choosing an "
            "aggregation_list field. This operation is read-only and is throttled to "
            "one call every 5 seconds."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def quake_filterable_fields(    ) -> StructuredToolResult:
        return mcp_tool_result(await get_quake_filterable_fields())

    @server.tool(
        name="quake_service_search",
        title="Search Quake Services with Offset Pagination",
        description=(
            "Run a real-time Quake service search using offset pagination. Use this for "
            "small result sets; use quake_service_scroll for deep pagination. This "
            "read-only remote request consumes Quake quota and is throttled to one call "
            "every 5 seconds. Quake correlation pivots use domain:, ip:, icp:, favicon: "
            "(MD5), cert:, and tls_SAN: joined with AND/OR/NOT; when remaining quota is "
            "unknown in a multi-source scan, call quake_user_info first. It requires "
            "CN_QUAKE_KEY; safe_only never repeats a "
            "read/write timeout, while force_retry accepts possible duplicate quota use."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def quake_service_search(
        query: Annotated[str, Field(description='Quake query, for example service:http or port:443 AND country:"China".')],
        start: Annotated[int, Field(ge=0, description="Result start offset.")] = 0,
        size: Annotated[int, Field(ge=1, le=500, description="Number of results to return.")] = 10,
        rule: Annotated[str | None, Field(description="Service data collection rule name for IP-list collections.")] = None,
        ip_list: Annotated[str | None, Field(description="Comma-separated IP list.")] = None,
        include: Annotated[str | None, Field(description=QUAKE_FILTER_FIELDS_DESCRIPTION)] = None,
        exclude: Annotated[str | None, Field(description=QUAKE_FILTER_FIELDS_DESCRIPTION)] = None,
        shortcuts: Annotated[str | None, Field(description="Comma-separated shortcut filter IDs from the web UI.")] = None,
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data.")] = False,
        latest: Annotated[bool, Field(description="Whether to use latest data.")] = True,
        start_time: Annotated[str | None, Field(description="UTC start time, for example 2020-10-14 00:00:00.")] = None,
        end_time: Annotated[str | None, Field(description="UTC end time, for example 2020-10-14 00:00:00.")] = None,
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only never repeats a request after write/read timeout; aggressive may consume quota twice.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate quota use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await search_quake_service(
            query=query,
            start=start,
            size=size,
            rule=rule,
            ip_list=ip_list,
            include=include,
            exclude=exclude,
            shortcuts=shortcuts,
            ignore_cache=ignore_cache,
            latest=latest,
            start_time=start_time,
            end_time=end_time,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))

    @server.tool(
        name="quake_service_scroll",
        title="Search Quake Services with Cursor Pagination",
        description=(
            "Run a deep-pagination Quake service search using a five-minute cursor. Use "
            "quake_service_search for small offset-based result sets. Pass the returned "
            "meta.pagination_id to the next call; this read-only request consumes quota "
            "and is throttled to one call every 5 seconds. It requires CN_QUAKE_KEY; "
            "safe_only never repeats a read/write timeout, while force_retry accepts "
            "possible duplicate quota use."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def quake_service_scroll(
        query: Annotated[str, Field(description='Quake query, for example service:http or port:443 AND country:"China".')],
        size: Annotated[int, Field(ge=1, le=500, description="Results per page.")] = 100,
        pagination_id: Annotated[str | None, Field(description="Pagination ID from previous response. Expires in 5 minutes.")] = None,
        rule: Annotated[str | None, Field(description="Service data collection rule name for IP-list collections.")] = None,
        ip_list: Annotated[str | None, Field(description="Comma-separated IP list.")] = None,
        include: Annotated[str | None, Field(description=QUAKE_FILTER_FIELDS_DESCRIPTION)] = None,
        exclude: Annotated[str | None, Field(description=QUAKE_FILTER_FIELDS_DESCRIPTION)] = None,
        shortcuts: Annotated[str | None, Field(description="Comma-separated shortcut filter IDs from the web UI.")] = None,
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data.")] = False,
        latest: Annotated[bool, Field(description="Whether to use latest data.")] = True,
        start_time: Annotated[str | None, Field(description="UTC start time, for example 2020-10-14 00:00:00.")] = None,
        end_time: Annotated[str | None, Field(description="UTC end time, for example 2020-10-14 00:00:00.")] = None,
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only never repeats a request after write/read timeout; aggressive may consume quota twice.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate quota use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await scroll_quake_service(
            query=query,
            size=size,
            pagination_id=pagination_id,
            rule=rule,
            ip_list=ip_list,
            include=include,
            exclude=exclude,
            shortcuts=shortcuts,
            ignore_cache=ignore_cache,
            latest=latest,
            start_time=start_time,
            end_time=end_time,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))

    @server.tool(
        name="quake_search",
        title="Search Quake Services through the Legacy Alias",
        description=(
            "Compatibility alias that performs the same deep-pagination search as "
            "quake_service_scroll. Use only for clients that still reference this "
            "legacy name; use quake_service_scroll for all new calls. The operation is "
            "a read-only remote request that consumes Quake quota and is throttled to "
            "one call every 5 seconds. It requires CN_QUAKE_KEY and shares the same "
            "safe_only and force_retry behavior as quake_service_scroll."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def quake_search(
        query: Annotated[str, Field(description='Quake query, for example service:http or port:443 AND country:"China".')],
        size: Annotated[int, Field(ge=1, le=500, description="Results per page.")] = 100,
        pagination_id: Annotated[str | None, Field(description="Pagination ID from previous response.")] = None,
        rule: Annotated[str | None, Field(description="Service data collection rule name for IP-list collections.")] = None,
        ip_list: Annotated[str | None, Field(description="Comma-separated IP list.")] = None,
        include: Annotated[str | None, Field(description=QUAKE_FILTER_FIELDS_DESCRIPTION)] = None,
        exclude: Annotated[str | None, Field(description=QUAKE_FILTER_FIELDS_DESCRIPTION)] = None,
        shortcuts: Annotated[str | None, Field(description="Comma-separated shortcut filter IDs from the web UI.")] = None,
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data.")] = False,
        latest: Annotated[bool, Field(description="Whether to use latest data.")] = True,
        start_time: Annotated[str | None, Field(description="UTC start time.")] = None,
        end_time: Annotated[str | None, Field(description="UTC end time.")] = None,
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only never repeats a request after write/read timeout; aggressive may consume quota twice.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate quota use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await scroll_quake_service(
            query=query,
            size=size,
            pagination_id=pagination_id,
            rule=rule,
            ip_list=ip_list,
            include=include,
            exclude=exclude,
            shortcuts=shortcuts,
            ignore_cache=ignore_cache,
            latest=latest,
            start_time=start_time,
            end_time=end_time,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))

    @server.tool(
        name="quake_aggregation_fields",
        title="List Quake Service Aggregation Fields",
        description=(
            "List fields accepted by quake_service_aggregation in aggregation_list. "
            "Use quake_filterable_fields for search include/exclude fields instead. "
            "This operation is read-only and is throttled to one call every 5 seconds."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def quake_aggregation_fields(    ) -> StructuredToolResult:
        return mcp_tool_result(await get_quake_aggregation_fields())

    @server.tool(
        name="quake_service_aggregation",
        title="Aggregate Quake Service Search Matches",
        description=(
            "Aggregate Quake service matches into buckets for one or two fields. Use "
            "quake_service_search when individual service records are required, and "
            "quake_aggregation_fields to discover valid bucket fields. This read-only "
            "request requires CN_QUAKE_KEY, consumes quota, and is throttled to one call "
            "every 5 seconds. safe_only never repeats a read/write timeout; force_retry "
            "accepts possible duplicate quota use."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def quake_service_aggregation(
        query: Annotated[str, Field(description='Quake query, for example country:"China".')],
        aggregation_list: Annotated[str, Field(description="One or two comma-separated aggregation fields, for example service or country,service.")],
        size: Annotated[int, Field(ge=1, le=10000, description="Aggregation bucket count per field.")] = 5,
        rule: Annotated[str | None, Field(description="Service data collection rule name for IP-list collections.")] = None,
        ip_list: Annotated[str | None, Field(description="Comma-separated IP list.")] = None,
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data.")] = False,
        latest: Annotated[bool, Field(description="Whether to use latest data.")] = True,
        start_time: Annotated[str | None, Field(description="UTC start time, for example 2020-10-14 00:00:00.")] = None,
        end_time: Annotated[str | None, Field(description="UTC end time, for example 2020-10-14 00:00:00.")] = None,
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only never repeats a request after write/read timeout; aggressive may consume quota twice.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate quota use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await aggregate_quake_service(
            query=query,
            aggregation_list=aggregation_list,
            size=size,
            rule=rule,
            ip_list=ip_list,
            ignore_cache=ignore_cache,
            latest=latest,
            start_time=start_time,
            end_time=end_time,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))


def create_server() -> SurveyHubMCPServer:
    """Create a single-platform Quake MCP server."""
    server = SurveyHubMCPServer(
        "quake-mcp",
        title="Quake MCP",
        description="360 Quake cyberspace asset search and account APIs.",
        instructions="Use Quake tools for 360 Quake user, service search, scroll, and aggregation APIs.",
        version=__version__,
    )
    register_quake_tools(server)
    register_reference_resources(server, ("quake-syntax", "quake-api"))
    return server


def main() -> None:
    """Run the Quake MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
