"""DayDayMap MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from . import __version__
from .common import (
    METERED_READ_ONLY_REMOTE_TOOL,
    READ_ONLY_REMOTE_TOOL,
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

DAYDAYMAP_BASE_URL = "https://www.daydaymap.com"
DAYDAYMAP_KEY_URL = "https://www.daydaymap.com -> 个人中心 -> 个人信息 -> 复制 API KEY"

DAYDAYMAP_FIELDS = (
    "ip, is_ipv6, is_website, port, protocol, url, continent, country, country_code, "
    "province, city, postal_code, asn, asn_org, longitude, latitude, isp, domain, "
    "icp_reg_name, industry, title, icon_md5, banner, header, body, os, device_type, "
    "manufacturer, server, lang, device, product, service, tags, time_stamp, cert, "
    "cert_selfsigned, SSL"
)

DAYDAYMAP_QUERY_CATEGORIES = (
    "IP: ip, ip.port, ip.isp, ip.os_family, ip.os, ip.tag, ip.industry, is_ipv6; "
    "域名: domain, domain.root, is_domain; "
    "地理位置: ip.country, ip.province, ip.city, ip.district; "
    "ICP 备案: icp.number, icp.name, icp.name_prefix, icp.webname; "
    "AS 域: asn.number, asn.org; "
    "WEB: is_web, web.server, web.status_code, web.header, web.title, web.lang, web.body, web.icon; "
    "协议: protocol.transport, protocol.service, protocol.banner; "
    "应用: app.name; 组件: product; "
    "设备: device.name, device.type, device.type_sub, brand, model, manufacturer; "
    "证书: cert.issuer, cert.subject, cert.sn, cert.org, cert.md5, cert.is_expired, cert.is_trust, cert.startdate, cert.enddate; "
    "时间: time; 漏洞: vul.cve, vul.dvb; 资产归属: org.name, org.name_prefix"
)

DAYDAYMAP_ERROR_CODES = {
    2001: "API KEY 错误，请检查 DAYDAYMAP_API_KEY 配置。",
    2002: "参数错误，请检查查询语法和请求参数。",
    2003: "会员权限不足，请在 DayDayMap 平台提升会员权限。",
    2004: "积分不足，请在 DayDayMap 平台充值后使用。",
    2005: "最多只能查看前 1 万条数据，请缩小查询范围。",
    2006: "数据获取失败，请重试。",
}

DAYDAYMAP_ERROR_TYPES = {
    2001: "authentication_error",
    2002: "validation_error",
    2003: "permission_denied",
    2004: "insufficient_credits",
    2005: "pagination_limit",
    2006: "provider_error",
}


def _daydaymap_key() -> str | None:
    return platform_key("DAYDAYMAP_API_KEY")


def _missing_key() -> dict[str, Any]:
    return missing_env_message(
        platform="DayDayMap",
        env_var="DAYDAYMAP_API_KEY",
        key_url=DAYDAYMAP_KEY_URL,
    )


def _headers() -> dict[str, str]:
    key = _daydaymap_key()
    headers = {"api-key": key} if key else {}
    headers["Content-Type"] = "application/json"
    return headers


async def search_daydaymap(
    *,
    query: str,
    page: int = 1,
    page_size: int = 10,
    fields: str | None = None,
    exclude_fields: str | None = None,
    retry_mode: str = "safe_only",
    force_retry: bool = False,
) -> dict[str, Any]:
    """Call DayDayMap search API with application-level error handling."""
    if not _daydaymap_key():
        return _missing_key()

    if not query.strip():
        return error_payload(
            platform="DayDayMap",
            message="DayDayMap query must not be empty.",
            error_type="validation_error",
        )

    if page < 1 or page_size < 1 or page * page_size > 10000:
        return error_payload(
            platform="DayDayMap",
            message="DayDayMap only allows access to the first 10,000 results (page x page_size <= 10000).",
            error_type="pagination_limit",
            details={"page": page, "page_size": page_size, "maximum_results": 10000},
        )

    payload: dict[str, object] = {
        "page": page,
        "page_size": page_size,
        "keyword": encode_base64(query),
    }
    if fields:
        payload["fields"] = fields
    if exclude_fields and not fields:
        payload["exclude_fields"] = exclude_fields

    result = await request_json(
        platform="DayDayMap",
        method="POST",
        url=f"{DAYDAYMAP_BASE_URL}/api/v1/raymap/search/all",
        headers=_headers(),
        json=payload,
        retry_mode=retry_mode,
        metered_request=True,
        force_retry=force_retry,
        auth_hint="Authentication failed. Check DAYDAYMAP_API_KEY.",
        forbidden_hint="Access forbidden. Your DayDayMap account may not have sufficient permissions.",
    )

    if not result.get("ok"):
        return result

    data = result.get("data")
    if not isinstance(data, dict):
        return result

    code = data.get("code")
    if code != 200:
        guidance = DAYDAYMAP_ERROR_CODES.get(code, f"未知错误 (code={code})")
        provider_message = data.get("msg")
        meta = dict(result.get("meta") or {})
        execution = dict(meta.get("execution") or {})
        execution["final_state"] = "confirmed_failure"
        meta["execution"] = execution
        return enrich_payload(
            error_payload(
                platform="DayDayMap",
                message=f"DayDayMap API 错误 (code={code}): {provider_message or guidance}",
                error_type=DAYDAYMAP_ERROR_TYPES.get(code, "api_error"),
                details={"code": code, "provider_message": provider_message, "guidance": guidance},
            ),
            meta=meta,
        )

    return result


def register_daydaymap_tools(server: MCPServer) -> None:
    """Register DayDayMap tools on an MCP server."""

    @server.tool(
        name="daydaymap_search",
        title="Search DayDayMap Cyberspace Assets",
        description=(
            "Search DayDayMap assets with automatic Base64 query encoding. Use English "
            "double quotes and && for logical AND. Results are limited to the first "
            "10,000 records (page x page_size <= 10000). See the daydaymap-api "
            "reference resource for complete query syntax. This read-only request "
            "requires CN_DAYDAYMAP_API_KEY and consumes provider quota. safe_only never "
            "repeats a read/write timeout; force_retry accepts possible duplicate quota use."
        ),
        annotations=METERED_READ_ONLY_REMOTE_TOOL,
    )
    async def daydaymap_search(
        query: Annotated[
            str,
            Field(
                min_length=1,
                description=(
                    "DayDayMap query string. Use English double quotes for values. "
                    'Examples: ip="1.1.1.1", domain="example.com", '
                    'ip.port="443" && protocol.service="https", '
                    'ip.country="中国" && web.title="管理系统", cert.subject.cn="example.com". '
                    f"Supported query fields by category: {DAYDAYMAP_QUERY_CATEGORIES}."
                )
            ),
        ],
        page: Annotated[int, Field(ge=1, le=10000, description="Page number, 1-10000.")] = 1,
        page_size: Annotated[int, Field(ge=1, le=10000, description="Results per page, max 10000.")] = 10,
        fields: Annotated[
            str | None,
            Field(
                description=(
                    f"Comma-separated fields to include in response. Supported values: "
                    f"{DAYDAYMAP_FIELDS}. When set, only these fields are returned and "
                    "the value takes priority over exclude_fields."
                )
            ),
        ] = None,
        exclude_fields: Annotated[
            str | None,
            Field(
                description="Comma-separated fields to exclude from response. Only effective when fields is not set."
            ),
        ] = None,
        retry_mode: Annotated[str, Field(pattern="^(never|safe_only|aggressive)$", description="Retry policy. safe_only retries only failures known to occur before sending; aggressive may consume quota twice.")] = "safe_only",
        force_retry: Annotated[bool, Field(description="Repeat a recently indeterminate identical request despite possible duplicate quota use.")] = False,
    ) -> StructuredToolResult:
        return mcp_tool_result(await search_daydaymap(
            query=query,
            page=page,
            page_size=page_size,
            fields=fields,
            exclude_fields=exclude_fields,
            retry_mode=retry_mode,
            force_retry=force_retry,
        ))


def create_server() -> SurveyHubMCPServer:
    """Create a single-platform DayDayMap MCP server."""
    server = SurveyHubMCPServer(
        "daydaymap-mcp",
        title="DayDayMap MCP",
        description="DayDayMap cyberspace asset search and account APIs.",
        instructions="Use DayDayMap tools for cyberspace asset search APIs.",
        version=__version__,
    )
    register_daydaymap_tools(server)
    register_reference_resources(server, ("daydaymap-api",))
    return server


def main() -> None:
    """Run the DayDayMap MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
