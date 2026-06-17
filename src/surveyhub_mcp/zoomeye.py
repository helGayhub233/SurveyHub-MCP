"""ZoomEye MCP tools."""

from __future__ import annotations

import os
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import encode_base64, missing_env_message, platform_key, request_json

ZOOMEYE_BASE_URL = "https://api.zoomeye.org"
ZOOMEYE_KEY_URL = "https://www.zoomeye.org -> Profile -> API Key"
ZOOMEYE_DEFAULT_FIELDS = "ip,port,domain,update_time"
ZOOMEYE_FACETS = "country, subdivisions, city, product, service, device, os, port"


def _zoomeye_key() -> str | None:
    return platform_key("ZOOMEYE_API_KEY")


def _missing_key() -> str:
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


async def get_zoomeye_user_info() -> str:
    """Call ZoomEye user information API."""
    if not _zoomeye_key():
        return _missing_key()

    return await request_json(
        platform="ZoomEye",
        method="POST",
        url=f"{ZOOMEYE_BASE_URL}/v2/userinfo",
        headers=_headers(),
        auth_hint="Authentication failed. Check ZOOMEYE_API_KEY.",
        forbidden_hint="Access forbidden. Your ZoomEye account may not have sufficient permissions.",
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
) -> str:
    """Call ZoomEye asset search API."""
    if not _zoomeye_key():
        return _missing_key()

    if not qbase64:
        if not query:
            return "Either query or qbase64 is required."
        qbase64 = encode_base64(query)

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

    return await request_json(
        platform="ZoomEye",
        method="POST",
        url=f"{ZOOMEYE_BASE_URL}/v2/search",
        headers=_headers(json=True),
        json=payload,
        auth_hint="Authentication failed. Check ZOOMEYE_API_KEY.",
        forbidden_hint="Access forbidden. Your ZoomEye account may not have sufficient permissions or points.",
    )


def register_zoomeye_tools(server: FastMCP) -> None:
    """Register ZoomEye tools on a FastMCP server."""

    @server.tool(
        name="zoomeye_user_info",
        title="ZoomEye User Info",
        description="Get ZoomEye user, subscription, and points information with POST /v2/userinfo.",
        structured_output=False,
    )
    async def zoomeye_user_info() -> str:
        return await get_zoomeye_user_info()

    @server.tool(
        name="zoomeye_search",
        title="ZoomEye Asset Search",
        description=(
            "Search ZoomEye assets with POST /v2/search. Provide raw query for automatic "
            "Base64 encoding, or pass qbase64 directly for compatibility with the API docs."
        ),
        structured_output=False,
    )
    async def zoomeye_search(
        query: Annotated[
            str | None,
            Field(description='Raw ZoomEye query, for example title="knownsec" or port=443 && country="CN".'),
        ] = None,
        qbase64: Annotated[
            str | None,
            Field(description="Base64-encoded ZoomEye query. Used as-is when provided."),
        ] = None,
        page: Annotated[int, Field(ge=1, description="Page number sorted by update time.")] = 1,
        pagesize: Annotated[int, Field(ge=1, le=10000, description="Results per page. Official max is 10000.")] = 10,
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
        ignore_cache: Annotated[bool, Field(description="Whether to ignore cached data. Business plans and above support this.")] = False,
    ) -> str:
        return await search_zoomeye_assets(
            query=query,
            qbase64=qbase64,
            page=page,
            pagesize=pagesize,
            fields=fields,
            sub_type=sub_type,
            facets=facets,
            ignore_cache=ignore_cache,
        )


def create_server() -> FastMCP:
    """Create a single-platform ZoomEye MCP server."""
    server = FastMCP(
        "zoomeye-mcp",
        instructions="Use ZoomEye tools for user information and asset search APIs.",
    )
    register_zoomeye_tools(server)
    return server


def main() -> None:
    """Run the ZoomEye MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
