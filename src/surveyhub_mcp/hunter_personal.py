"""Hunter personal account MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import (
    AsyncRateLimiter,
    encode_base64_url,
    missing_any_env_message,
    platform_env,
    request_download,
    request_json,
)

HUNTER_BASE_URL = "https://hunter.qianxin.com"
HUNTER_KEY_URL = "https://hunter.qianxin.com -> Personal Center -> API Management"
HUNTER_PERSONAL_ENV = ("HUNTER_PERSONAL_KEY", "HUNTER_KEY")

HUNTER_PERSONAL_FIELDS = (
    "ip,port,domain,ip_tag,url,web_title,is_risk_protocol,protocol,"
    "base_protocol,status_code,os,company,number,icp_exception,country,"
    "province,city,is_web,isp,as_org,cert_sha256,ssl_certificate,"
    "component,asset_tag,updated_at,header,header_server,banner"
)

HP_RATE_LIMITER = AsyncRateLimiter(1.0)


def _hunter_key() -> str | None:
    return platform_env(*HUNTER_PERSONAL_ENV)[1]


def _missing_key() -> str:
    return missing_any_env_message(
        platform="Hunter Personal",
        env_vars=HUNTER_PERSONAL_ENV,
        key_url=HUNTER_KEY_URL,
    )


def _auth_params() -> dict[str, str]:
    key = _hunter_key()
    return {"api-key": key} if key else {}


def _add_optional_params(
    params: dict[str, str | int],
    *,
    start_time: str | None = None,
    end_time: str | None = None,
    is_web: int | None = None,
    status_code: str | None = None,
    fields: str | None = None,
    search_type: str | None = None,
    assets_limit: int | None = None,
) -> dict[str, str | int]:
    optional: dict[str, str | int | None] = {
        "start_time": start_time,
        "end_time": end_time,
        "is_web": is_web,
        "status_code": status_code,
        "fields": fields,
        "search_type": search_type,
        "assets_limit": assets_limit,
    }
    params.update({key: value for key, value in optional.items() if value is not None and value != ""})
    return params


async def search_hunter_personal(
    *,
    query: str,
    page: int = 1,
    page_size: Literal[10, 50, 100] = 10,
    is_web: Literal[1, 2, 3] = 3,
    status_code: str | None = None,
    fields: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """Call Hunter personal /openApi/search."""
    if not _hunter_key():
        return _missing_key()

    params: dict[str, str | int] = {
        **_auth_params(),
        "search": encode_base64_url(query),
        "page": page,
        "page_size": page_size,
        "is_web": is_web,
    }
    _add_optional_params(
        params,
        status_code=status_code,
        fields=fields,
        start_time=start_time,
        end_time=end_time,
    )

    await HP_RATE_LIMITER.wait()

    return await request_json(
        platform="Hunter Personal",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/search",
        params=params,
        auth_hint="Authentication failed. Check HUNTER_PERSONAL_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter personal account may not have sufficient permissions or credits.",
    )


async def create_hunter_personal_batch_task(
    *,
    query: str | None = None,
    file_path: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    is_web: Literal[1, 2] | None = None,
    status_code: str | None = None,
    fields: str | None = None,
    search_type: Literal["all", "ip", "domain", "company"] = "all",
    assets_limit: int | None = None,
) -> str:
    """Create a Hunter personal batch search task."""
    if not _hunter_key():
        return _missing_key()
    if bool(query) == bool(file_path):
        return "Provide exactly one of query or file_path for Hunter batch search."

    params: dict[str, str | int] = {**_auth_params()}
    if query:
        params["search"] = encode_base64_url(query)
    _add_optional_params(
        params,
        start_time=start_time,
        end_time=end_time,
        is_web=is_web,
        status_code=status_code,
        fields=fields,
        search_type=search_type,
        assets_limit=assets_limit,
    )

    if file_path:
        path = Path(file_path).expanduser()
        if not path.is_file():
            return f"File not found: {path}"
        with path.open("rb") as file_obj:
            await HP_RATE_LIMITER.wait()
            return await request_json(
                platform="Hunter Personal",
                method="POST",
                url=f"{HUNTER_BASE_URL}/openApi/search/batch",
                params=params,
                files={"file": (path.name, file_obj, "text/csv")},
                auth_hint="Authentication failed. Check HUNTER_PERSONAL_KEY or HUNTER_KEY.",
                forbidden_hint="Access forbidden. Your Hunter personal account may not have sufficient permissions or credits.",
            )

    await HP_RATE_LIMITER.wait()

    return await request_json(
        platform="Hunter Personal",
        method="POST",
        url=f"{HUNTER_BASE_URL}/openApi/search/batch",
        params=params,
        auth_hint="Authentication failed. Check HUNTER_PERSONAL_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter personal account may not have sufficient permissions or credits.",
    )


async def get_hunter_personal_batch_status(*, task_id: str) -> str:
    """Get Hunter personal batch task progress."""
    if not _hunter_key():
        return _missing_key()

    await HP_RATE_LIMITER.wait()

    return await request_json(
        platform="Hunter Personal",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/search/batch/{task_id}",
        params=_auth_params(),
        auth_hint="Authentication failed. Check HUNTER_PERSONAL_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter personal account may not have sufficient permissions or credits.",
    )


async def download_hunter_personal_batch_file(*, task_id: str, output_path: str) -> str:
    """Download Hunter personal batch export file."""
    if not _hunter_key():
        return _missing_key()

    await HP_RATE_LIMITER.wait()

    return await request_download(
        platform="Hunter Personal",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/search/download/{task_id}",
        output_path=output_path,
        params=_auth_params(),
        auth_hint="Authentication failed. Check HUNTER_PERSONAL_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter personal account may not have sufficient permissions or credits.",
    )


async def get_hunter_personal_user_info() -> str:
    """Get Hunter personal account information."""
    if not _hunter_key():
        return _missing_key()

    await HP_RATE_LIMITER.wait()

    return await request_json(
        platform="Hunter Personal",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/userInfo",
        params=_auth_params(),
        auth_hint="Authentication failed. Check HUNTER_PERSONAL_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter personal account may not have sufficient permissions or credits.",
    )


def register_hunter_personal_tools(server: FastMCP) -> None:
    """Register Hunter personal tools on a FastMCP server."""

    @server.tool(
        name="hunter_personal_search",
        title="Hunter Personal Search",
        description=f"Search Hunter personal API /openApi/search. Personal fields: {HUNTER_PERSONAL_FIELDS}.",
        structured_output=False,
    )
    async def hunter_personal_search(
        query: Annotated[str, Field(description='Hunter query, for example web.title="login".')],
        page: Annotated[int, Field(ge=1, description="Page number.")] = 1,
        page_size: Annotated[Literal[10, 50, 100], Field(description="Results per page.")] = 10,
        is_web: Annotated[Literal[1, 2, 3], Field(description="1=web, 2=non-web, 3=all.")] = 3,
        status_code: Annotated[str | None, Field(description='Comma-separated status codes, for example "200,401".')] = None,
        fields: Annotated[str | None, Field(description="Comma-separated return fields.")] = None,
        start_time: Annotated[str | None, Field(description="Start date in YYYY-MM-DD. Beyond 30 days consumes equity points.")] = None,
        end_time: Annotated[str | None, Field(description="End date in YYYY-MM-DD. Beyond 30 days consumes equity points.")] = None,
    ) -> str:
        return await search_hunter_personal(
            query=query,
            page=page,
            page_size=page_size,
            is_web=is_web,
            status_code=status_code,
            fields=fields,
            start_time=start_time,
            end_time=end_time,
        )

    @server.tool(
        name="hunter_personal_batch_create",
        title="Hunter Personal Batch Create",
        description="Create a Hunter personal batch search task with query or CSV file upload.",
        structured_output=False,
    )
    async def hunter_personal_batch_create(
        query: Annotated[str | None, Field(description="Hunter query. Required if file_path is not provided.")] = None,
        file_path: Annotated[str | None, Field(description="Local CSV file path. Required if query is not provided.")] = None,
        start_time: Annotated[str | None, Field(description="Start date in YYYY-MM-DD.")] = None,
        end_time: Annotated[str | None, Field(description="End date in YYYY-MM-DD.")] = None,
        is_web: Annotated[Literal[1, 2] | None, Field(description="1=web, 2=non-web.")] = None,
        status_code: Annotated[str | None, Field(description='Comma-separated status codes, for example "200,401".')] = None,
        fields: Annotated[str | None, Field(description="Comma-separated return fields.")] = None,
        search_type: Annotated[
            Literal["all", "ip", "domain", "company"],
            Field(description="CSV search type. Personal limits: all <=10; ip/domain/company <=100."),
        ] = "all",
        assets_limit: Annotated[int | None, Field(ge=1, description="Expected exported asset count.")] = None,
    ) -> str:
        return await create_hunter_personal_batch_task(
            query=query,
            file_path=file_path,
            start_time=start_time,
            end_time=end_time,
            is_web=is_web,
            status_code=status_code,
            fields=fields,
            search_type=search_type,
            assets_limit=assets_limit,
        )

    @server.tool(
        name="hunter_personal_batch_status",
        title="Hunter Personal Batch Status",
        description="Get Hunter personal batch task progress.",
        structured_output=False,
    )
    async def hunter_personal_batch_status(
        task_id: Annotated[str, Field(description="Task ID returned by hunter_personal_batch_create.")],
    ) -> str:
        return await get_hunter_personal_batch_status(task_id=task_id)

    @server.tool(
        name="hunter_personal_batch_download",
        title="Hunter Personal Batch Download",
        description="Download Hunter personal batch task export file to output_path.",
        structured_output=False,
    )
    async def hunter_personal_batch_download(
        task_id: Annotated[str, Field(description="Task ID returned by hunter_personal_batch_create.")],
        output_path: Annotated[str, Field(description="Local output CSV path.")],
    ) -> str:
        return await download_hunter_personal_batch_file(task_id=task_id, output_path=output_path)

    @server.tool(
        name="hunter_personal_user_info",
        title="Hunter Personal User Info",
        description="Get Hunter personal account quota and account information.",
        structured_output=False,
    )
    async def hunter_personal_user_info() -> str:
        return await get_hunter_personal_user_info()


def create_server() -> FastMCP:
    """Create a Hunter personal MCP server."""
    server = FastMCP(
        "hunter-personal-mcp",
        instructions="Use Hunter personal tools for personal-account Hunter APIs.",
    )
    register_hunter_personal_tools(server)
    return server


def main() -> None:
    """Run the Hunter personal MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
