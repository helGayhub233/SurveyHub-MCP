"""DayDayMap MCP tools."""

from __future__ import annotations

import json
import os
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import encode_base64, missing_env_message, platform_key, request_json

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


def _daydaymap_key() -> str | None:
    return platform_key("DAYDAYMAP_API_KEY")


def _missing_key() -> str:
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
) -> str:
    """Call DayDayMap search API with application-level error handling."""
    if not _daydaymap_key():
        return _missing_key()

    payload: dict[str, object] = {
        "page": page,
        "page_size": page_size,
        "keyword": encode_base64(query),
    }
    if fields:
        payload["fields"] = fields
    if exclude_fields and not fields:
        payload["exclude_fields"] = exclude_fields

    raw = await request_json(
        platform="DayDayMap",
        method="POST",
        url=f"{DAYDAYMAP_BASE_URL}/api/v1/raymap/search/all",
        headers=_headers(),
        json=payload,
        auth_hint="Authentication failed. Check DAYDAYMAP_API_KEY.",
        forbidden_hint="Access forbidden. Your DayDayMap account may not have sufficient permissions.",
    )

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    code = data.get("code")
    if code != 200:
        message = DAYDAYMAP_ERROR_CODES.get(code, f"未知错误 (code={code})")
        return f"DayDayMap API 错误 (code={code}): {data.get('msg', message)}"

    return raw


def register_daydaymap_tools(server: FastMCP) -> None:
    """Register DayDayMap tools on a FastMCP server."""

    @server.tool(
        name="daydaymap_search",
        title="DayDayMap Search",
        description=(
            "Search DayDayMap assets with POST /api/v1/raymap/search/all. "
            "Query is automatically Base64-encoded for the keyword parameter. "
            "Strings in queries must use English double quotes and are case-insensitive. "
            f"Supported return fields: {DAYDAYMAP_FIELDS}. "
            f"Query syntax categories: {DAYDAYMAP_QUERY_CATEGORIES}. "
            "Logical AND uses &&. Maximum 10,000 results total (page x page_size <= 10000)."
        ),
        structured_output=False,
    )
    async def daydaymap_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "DayDayMap query string. Use English double quotes for values. "
                    'Examples: ip="1.1.1.1", domain="example.com", port="443" && service="https", '
                    'ip.country="中国" && web.title="管理系统", cert.subject.cn="example.com".'
                )
            ),
        ],
        page: Annotated[int, Field(ge=1, le=10000, description="Page number, 1-10000.")] = 1,
        page_size: Annotated[int, Field(ge=1, le=10000, description="Results per page, max 10000.")] = 10,
        fields: Annotated[
            str | None,
            Field(
                description=(
                    "Comma-separated fields to include in response. "
                    "When set, only these fields are returned. Takes priority over exclude_fields."
                )
            ),
        ] = None,
        exclude_fields: Annotated[
            str | None,
            Field(description="Comma-separated fields to exclude from response. Only effective when fields is not set."),
        ] = None,
    ) -> str:
        return await search_daydaymap(
            query=query,
            page=page,
            page_size=page_size,
            fields=fields,
            exclude_fields=exclude_fields,
        )


def create_server() -> FastMCP:
    """Create a single-platform DayDayMap MCP server."""
    server = FastMCP(
        "daydaymap-mcp",
        instructions="Use DayDayMap tools for cyberspace asset search APIs.",
    )
    register_daydaymap_tools(server)
    return server


def main() -> None:
    """Run the DayDayMap MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
