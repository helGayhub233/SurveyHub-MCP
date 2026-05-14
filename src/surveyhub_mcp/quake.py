"""Quake MCP tools."""

from __future__ import annotations

import os
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import missing_env_message, request_json, split_csv

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


def _quake_key() -> str | None:
    return os.getenv("QUAKE_KEY")


def _missing_key() -> str:
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


async def get_quake_user_info() -> str:
    """Call Quake user information API."""
    if not _quake_key():
        return _missing_key()

    return await request_json(
        platform="Quake",
        method="GET",
        url=f"{QUAKE_BASE_URL}/api/v3/user/info",
        headers=_headers(),
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions.",
    )


async def get_quake_filterable_fields() -> str:
    """Call Quake service filterable fields API."""
    if not _quake_key():
        return _missing_key()

    return await request_json(
        platform="Quake",
        method="GET",
        url=f"{QUAKE_BASE_URL}/api/v3/filterable/field/quake_service",
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
) -> str:
    """Call Quake real-time service search API."""
    if not _quake_key():
        return _missing_key()

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

    return await request_json(
        platform="Quake",
        method="POST",
        url=f"{QUAKE_BASE_URL}/api/v3/search/quake_service",
        headers=_headers(json=True),
        json=payload,
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions or credits.",
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
) -> str:
    """Call Quake scroll service search API."""
    if not _quake_key():
        return _missing_key()

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

    return await request_json(
        platform="Quake",
        method="POST",
        url=f"{QUAKE_BASE_URL}/api/v3/scroll/quake_service",
        headers=_headers(json=True),
        json=payload,
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions or credits.",
    )


async def get_quake_aggregation_fields() -> str:
    """Call Quake aggregation fields API."""
    if not _quake_key():
        return _missing_key()

    return await request_json(
        platform="Quake",
        method="GET",
        url=f"{QUAKE_BASE_URL}/api/v3/aggregation/quake_service",
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
) -> str:
    """Call Quake service aggregation API."""
    if not _quake_key():
        return _missing_key()

    aggregations = split_csv(aggregation_list)
    if not aggregations:
        return "aggregation_list is required. Provide one or two comma-separated aggregation fields."
    if len(aggregations) > 2:
        return "aggregation_list supports at most two fields."

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

    return await request_json(
        platform="Quake",
        method="POST",
        url=f"{QUAKE_BASE_URL}/api/v3/aggregation/quake_service",
        headers=_headers(json=True),
        json=payload,
        auth_hint="Authentication failed. Check QUAKE_KEY.",
        forbidden_hint="Access forbidden. Your Quake account may not have sufficient permissions or credits.",
    )


def register_quake_tools(server: FastMCP) -> None:
    """Register Quake tools on a FastMCP server."""

    @server.tool(
        name="quake_user_info",
        title="Quake User Info",
        description="Get Quake user details, quota, token, and role information with /api/v3/user/info.",
        structured_output=False,
    )
    async def quake_user_info() -> str:
        return await get_quake_user_info()

    @server.tool(
        name="quake_filterable_fields",
        title="Quake Filterable Fields",
        description=(
            "Get Quake service fields usable in include/exclude with "
            f"/api/v3/filterable/field/quake_service. Examples: {QUAKE_FILTERABLE_FIELDS}."
        ),
        structured_output=False,
    )
    async def quake_filterable_fields() -> str:
        return await get_quake_filterable_fields()

    @server.tool(
        name="quake_service_search",
        title="Quake Service Search",
        description=(
            "Run real-time Quake service search with /api/v3/search/quake_service. "
            "Use this for small result sets; use quake_service_scroll for deep pagination."
        ),
        structured_output=False,
    )
    async def quake_service_search(
        query: Annotated[str, Field(description='Quake query, for example service:http or port:443 AND country:"China".')],
        start: Annotated[int, Field(ge=0, description="Result start offset.")] = 0,
        size: Annotated[int, Field(ge=1, le=500, description="Number of results to return.")] = 10,
        rule: Annotated[str | None, Field(description="Service data collection rule name for IP-list collections.")] = None,
        ip_list: Annotated[str | None, Field(description="Comma-separated IP list.")] = None,
        include: Annotated[str | None, Field(description="Comma-separated fields to include.")] = None,
        exclude: Annotated[str | None, Field(description="Comma-separated fields to exclude.")] = None,
        shortcuts: Annotated[str | None, Field(description="Comma-separated shortcut filter IDs from the web UI.")] = None,
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data.")] = False,
        latest: Annotated[bool, Field(description="Whether to use latest data.")] = True,
        start_time: Annotated[str | None, Field(description="UTC start time, for example 2020-10-14 00:00:00.")] = None,
        end_time: Annotated[str | None, Field(description="UTC end time, for example 2020-10-14 00:00:00.")] = None,
    ) -> str:
        return await search_quake_service(
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

    @server.tool(
        name="quake_service_scroll",
        title="Quake Service Scroll",
        description=(
            "Run deep-pagination Quake service search with /api/v3/scroll/quake_service. "
            "Use meta.pagination_id from the response as pagination_id for the next page."
        ),
        structured_output=False,
    )
    async def quake_service_scroll(
        query: Annotated[str, Field(description='Quake query, for example service:http or port:443 AND country:"China".')],
        size: Annotated[int, Field(ge=1, le=500, description="Results per page.")] = 100,
        pagination_id: Annotated[str | None, Field(description="Pagination ID from previous response. Expires in 5 minutes.")] = None,
        rule: Annotated[str | None, Field(description="Service data collection rule name for IP-list collections.")] = None,
        ip_list: Annotated[str | None, Field(description="Comma-separated IP list.")] = None,
        include: Annotated[str | None, Field(description="Comma-separated fields to include.")] = None,
        exclude: Annotated[str | None, Field(description="Comma-separated fields to exclude.")] = None,
        shortcuts: Annotated[str | None, Field(description="Comma-separated shortcut filter IDs from the web UI.")] = None,
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data.")] = False,
        latest: Annotated[bool, Field(description="Whether to use latest data.")] = True,
        start_time: Annotated[str | None, Field(description="UTC start time, for example 2020-10-14 00:00:00.")] = None,
        end_time: Annotated[str | None, Field(description="UTC end time, for example 2020-10-14 00:00:00.")] = None,
    ) -> str:
        return await scroll_quake_service(
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

    @server.tool(
        name="quake_search",
        title="Quake Search (Scroll Compatibility)",
        description="Backward-compatible alias for quake_service_scroll.",
        structured_output=False,
    )
    async def quake_search(
        query: Annotated[str, Field(description='Quake query, for example service:http or port:443 AND country:"China".')],
        size: Annotated[int, Field(ge=1, le=500, description="Results per page.")] = 100,
        pagination_id: Annotated[str | None, Field(description="Pagination ID from previous response.")] = None,
        include: Annotated[str | None, Field(description="Comma-separated fields to include.")] = None,
        exclude: Annotated[str | None, Field(description="Comma-separated fields to exclude.")] = None,
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data.")] = False,
        latest: Annotated[bool, Field(description="Whether to use latest data.")] = True,
        start_time: Annotated[str | None, Field(description="UTC start time.")] = None,
        end_time: Annotated[str | None, Field(description="UTC end time.")] = None,
    ) -> str:
        return await scroll_quake_service(
            query=query,
            size=size,
            pagination_id=pagination_id,
            include=include,
            exclude=exclude,
            ignore_cache=ignore_cache,
            latest=latest,
            start_time=start_time,
            end_time=end_time,
        )

    @server.tool(
        name="quake_aggregation_fields",
        title="Quake Aggregation Fields",
        description=(
            "Get Quake service aggregation fields with /api/v3/aggregation/quake_service. "
            f"Examples: {QUAKE_AGGREGATION_FIELDS}."
        ),
        structured_output=False,
    )
    async def quake_aggregation_fields() -> str:
        return await get_quake_aggregation_fields()

    @server.tool(
        name="quake_service_aggregation",
        title="Quake Service Aggregation",
        description="Run Quake service aggregation query with /api/v3/aggregation/quake_service.",
        structured_output=False,
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
    ) -> str:
        return await aggregate_quake_service(
            query=query,
            aggregation_list=aggregation_list,
            size=size,
            rule=rule,
            ip_list=ip_list,
            ignore_cache=ignore_cache,
            latest=latest,
            start_time=start_time,
            end_time=end_time,
        )


def create_server() -> FastMCP:
    """Create a single-platform Quake MCP server."""
    server = FastMCP(
        "quake-mcp",
        instructions="Use Quake tools for 360 Quake user, service search, scroll, and aggregation APIs.",
    )
    register_quake_tools(server)
    return server


def main() -> None:
    """Run the Quake MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
