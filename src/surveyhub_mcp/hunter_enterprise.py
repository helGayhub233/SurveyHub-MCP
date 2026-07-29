"""Hunter enterprise account MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from pydantic import Field

from . import __version__
from .common import (
    LOCAL_FILE_WRITE_TOOL,
    MUTATING_REMOTE_TOOL,
    READ_ONLY_REMOTE_TOOL,
    SurveyHubMCPServer,
    StructuredToolResult,
    AsyncRateLimiter,
    encode_base64_url,
    error_payload,
    missing_any_env_message,
    mcp_tool_result,
    normalize_hunter_query,
    platform_env,
    request_download,
    request_json,
)
from .reference import register_reference_resources

HUNTER_BASE_URL = "https://hunter.qianxin.com"
HUNTER_KEY_URL = "https://hunter.qianxin.com -> Personal Center -> API Management"
HUNTER_ENTERPRISE_ENV = ("HUNTER_ENTERPRISE_KEY", "HUNTER_KEY")

HUNTER_ENTERPRISE_FIELDS = (
    "ip,port,domain,ip_tag,url,web_title,is_risk_protocol,protocol,"
    "base_protocol,status_code,os,company,number,icp_exception,country,"
    "province,city,is_web,isp,as_org,cert_sha256,ssl_certificate,"
    "component,asset_tag,updated_at,header,header_server,banner,whois,body,vul_list"
)

HE_RATE_LIMITER = AsyncRateLimiter(
    1.0,
    namespace="hunter-enterprise",
    identity_provider=lambda: _hunter_key(),
)


def _hunter_key() -> str | None:
    return platform_env(*HUNTER_ENTERPRISE_ENV)[1]


def _missing_key() -> dict[str, Any]:
    return missing_any_env_message(
        platform="Hunter Enterprise",
        env_vars=HUNTER_ENTERPRISE_ENV,
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


async def search_hunter_enterprise(
    *,
    query: str,
    page: int = 1,
    page_size: Literal[10, 50, 100] = 10,
    is_web: Literal[1, 2, 3] = 3,
    status_code: str | None = None,
    fields: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    exact_search: bool = True,
) -> dict[str, Any]:
    """Call Hunter enterprise /openApi/search."""
    if not _hunter_key():
        return _missing_key()

    prepared_query = normalize_hunter_query(query, exact_search=exact_search)
    params: dict[str, str | int] = {
        **_auth_params(),
        "search": encode_base64_url(prepared_query),
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

    return await request_json(
        platform="Hunter Enterprise",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/search",
        rate_limiter=HE_RATE_LIMITER,
        retryable_body_codes={429},
        params=params,
        auth_hint="Authentication failed. Check HUNTER_ENTERPRISE_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter enterprise account may not have sufficient permissions or credits.",
    )


async def create_hunter_enterprise_batch_task(
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
    exact_search: bool = True,
) -> dict[str, Any]:
    """Create a Hunter enterprise batch search task."""
    if not _hunter_key():
        return _missing_key()
    if bool(query) == bool(file_path):
        return error_payload(
            platform="Hunter Enterprise",
            message="Provide exactly one of query or file_path for Hunter batch search.",
            error_type="validation_error",
        )

    params: dict[str, str | int] = {**_auth_params()}
    if query:
        prepared_query = normalize_hunter_query(query, exact_search=exact_search)
        params["search"] = encode_base64_url(prepared_query)
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
            return error_payload(
                platform="Hunter Enterprise",
                message=f"File not found: {path}",
                error_type="file_not_found",
                details={"path": str(path)},
            )
        with path.open("rb") as file_obj:
            return await request_json(
                platform="Hunter Enterprise",
                method="POST",
                url=f"{HUNTER_BASE_URL}/openApi/search/batch",
                rate_limiter=HE_RATE_LIMITER,
                retryable_body_codes={429},
                params=params,
                files={"file": (path.name, file_obj, "text/csv")},
                auth_hint="Authentication failed. Check HUNTER_ENTERPRISE_KEY or HUNTER_KEY.",
                forbidden_hint="Access forbidden. Your Hunter enterprise account may not have sufficient permissions or credits.",
            )

    return await request_json(
        platform="Hunter Enterprise",
        method="POST",
        url=f"{HUNTER_BASE_URL}/openApi/search/batch",
        rate_limiter=HE_RATE_LIMITER,
        retryable_body_codes={429},
        params=params,
        auth_hint="Authentication failed. Check HUNTER_ENTERPRISE_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter enterprise account may not have sufficient permissions or credits.",
    )


async def get_hunter_enterprise_batch_status(*, task_id: str) -> dict[str, Any]:
    """Get Hunter enterprise batch task progress."""
    if not _hunter_key():
        return _missing_key()

    return await request_json(
        platform="Hunter Enterprise",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/search/batch/{task_id}",
        rate_limiter=HE_RATE_LIMITER,
        retryable_body_codes={429},
        params=_auth_params(),
        auth_hint="Authentication failed. Check HUNTER_ENTERPRISE_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter enterprise account may not have sufficient permissions or credits.",
    )


async def download_hunter_enterprise_batch_file(*, task_id: str, output_path: str) -> dict[str, Any]:
    """Download Hunter enterprise batch export file."""
    if not _hunter_key():
        return _missing_key()

    return await request_download(
        platform="Hunter Enterprise",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/search/download/{task_id}",
        output_path=output_path,
        rate_limiter=HE_RATE_LIMITER,
        retryable_body_codes={429},
        params=_auth_params(),
        auth_hint="Authentication failed. Check HUNTER_ENTERPRISE_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter enterprise account may not have sufficient permissions or credits.",
    )


async def pull_hunter_enterprise_batch_results(
    *,
    task_id: str,
    page: int = 1,
    page_size: Literal[100, 200, 500, 1000] = 500,
) -> dict[str, Any]:
    """Pull Hunter enterprise batch task result data as JSON."""
    if not _hunter_key():
        return _missing_key()

    params: dict[str, str | int] = {
        **_auth_params(),
        "task_id": task_id,
        "page": page,
        "page_size": page_size,
    }

    return await request_json(
        platform="Hunter Enterprise",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/search/batch/pull",
        rate_limiter=HE_RATE_LIMITER,
        retryable_body_codes={429},
        params=params,
        auth_hint="Authentication failed. Check HUNTER_ENTERPRISE_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter enterprise account may not have sufficient permissions or credits.",
    )


async def get_hunter_enterprise_user_info() -> dict[str, Any]:
    """Get Hunter enterprise account information."""
    if not _hunter_key():
        return _missing_key()

    return await request_json(
        platform="Hunter Enterprise",
        method="GET",
        url=f"{HUNTER_BASE_URL}/openApi/userInfo",
        rate_limiter=HE_RATE_LIMITER,
        retryable_body_codes={429},
        params=_auth_params(),
        auth_hint="Authentication failed. Check HUNTER_ENTERPRISE_KEY or HUNTER_KEY.",
        forbidden_hint="Access forbidden. Your Hunter enterprise account may not have sufficient permissions or credits.",
    )


def register_hunter_enterprise_tools(server: MCPServer) -> None:
    """Register Hunter enterprise tools on an MCP server."""

    @server.tool(
        name="hunter_enterprise_search",
        title="Search Assets with a Hunter Enterprise Account",
        description=(
            "Search assets through a Hunter enterprise or sub-account, including "
            "enterprise-only whois, body, and vulnerability fields. Use "
            "hunter_personal_search for personal accounts. This read-only remote "
            "request consumes quota, is throttled to one call per second, and "
            "exact-matches quoted field values by default."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def hunter_enterprise_search(
        query: Annotated[str, Field(description='Hunter query, for example web.title="login".')],
        page: Annotated[int, Field(ge=1, description="Page number.")] = 1,
        page_size: Annotated[Literal[10, 50, 100], Field(description="Results per page.")] = 10,
        is_web: Annotated[Literal[1, 2, 3], Field(description="1=web, 2=non-web, 3=all.")] = 3,
        status_code: Annotated[str | None, Field(description='Comma-separated status codes, for example "200,401".')] = None,
        fields: Annotated[str | None, Field(description="Comma-separated return fields.")] = None,
        start_time: Annotated[str | None, Field(description="Start date in YYYY-MM-DD.")] = None,
        end_time: Annotated[str | None, Field(description="End date in YYYY-MM-DD.")] = None,
        exact_search: Annotated[
            bool,
            Field(description='Convert Hunter field="value" fuzzy comparisons to field=="value" exact comparisons by default.'),
        ] = True,
    ) -> StructuredToolResult:
        return mcp_tool_result(await search_hunter_enterprise(
            query=query,
            page=page,
            page_size=page_size,
            is_web=is_web,
            status_code=status_code,
            fields=fields,
            start_time=start_time,
            end_time=end_time,
            exact_search=exact_search,
        ))

    @server.tool(
        name="hunter_enterprise_batch_create",
        title="Create a Hunter Enterprise Batch Search Task",
        description=(
            "Create an asynchronous Hunter enterprise batch-search task from either a "
            "query or local CSV file. Use hunter_enterprise_batch_status until the task "
            "finishes, then use hunter_enterprise_batch_pull for paginated JSON or "
            "hunter_enterprise_batch_download for a local CSV. Creation is "
            "non-idempotent, consumes quota, is throttled to one call per second, and CSV limits are "
            "all<=10 or ip/domain/company<=10000."
        ),
        annotations=MUTATING_REMOTE_TOOL,
    )
    async def hunter_enterprise_batch_create(
        query: Annotated[str | None, Field(description="Hunter query. Required if file_path is not provided.")] = None,
        file_path: Annotated[str | None, Field(description="Local CSV file path. Required if query is not provided.")] = None,
        start_time: Annotated[str | None, Field(description="Start date in YYYY-MM-DD.")] = None,
        end_time: Annotated[str | None, Field(description="End date in YYYY-MM-DD.")] = None,
        is_web: Annotated[Literal[1, 2] | None, Field(description="1=web, 2=non-web.")] = None,
        status_code: Annotated[str | None, Field(description='Comma-separated status codes, for example "200,401".')] = None,
        fields: Annotated[str | None, Field(description="Comma-separated return fields.")] = None,
        search_type: Annotated[
            Literal["all", "ip", "domain", "company"],
            Field(description="CSV search type. Enterprise limits: all <=10; ip/domain/company <=10000."),
        ] = "all",
        assets_limit: Annotated[int | None, Field(ge=1, description="Expected exported asset count.")] = None,
        exact_search: Annotated[
            bool,
            Field(description='For query mode, convert Hunter field="value" fuzzy comparisons to field=="value" exact comparisons by default.'),
        ] = True,
    ) -> StructuredToolResult:
        return mcp_tool_result(await create_hunter_enterprise_batch_task(
            query=query,
            file_path=file_path,
            start_time=start_time,
            end_time=end_time,
            is_web=is_web,
            status_code=status_code,
            fields=fields,
            search_type=search_type,
            assets_limit=assets_limit,
            exact_search=exact_search,
        ))

    @server.tool(
        name="hunter_enterprise_batch_status",
        title="Check Hunter Enterprise Batch Search Progress",
        description=(
            "Get progress and completion state for a task created by "
            "hunter_enterprise_batch_create. Call this before "
            "hunter_enterprise_batch_pull or hunter_enterprise_batch_download. This "
            "operation is read-only, consumes Hunter quota, and is throttled to one "
            "call per second."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def hunter_enterprise_batch_status(
        task_id: Annotated[str, Field(description="Task ID returned by hunter_enterprise_batch_create.")],
    ) -> StructuredToolResult:
        return mcp_tool_result(await get_hunter_enterprise_batch_status(task_id=task_id))

    @server.tool(
        name="hunter_enterprise_batch_download",
        title="Download a Hunter Enterprise Batch CSV Export",
        description=(
            "Download a completed Hunter enterprise batch export to a local CSV path. "
            "Use hunter_enterprise_batch_pull for paginated JSON instead and check "
            "hunter_enterprise_batch_status first. This writes local state and may "
            "overwrite an existing output_path. The provider request is throttled to "
            "one call per second."
        ),
        annotations=LOCAL_FILE_WRITE_TOOL,
    )
    async def hunter_enterprise_batch_download(
        task_id: Annotated[str, Field(description="Task ID returned by hunter_enterprise_batch_create.")],
        output_path: Annotated[str, Field(description="Local output CSV path.")],
    ) -> StructuredToolResult:
        return mcp_tool_result(await download_hunter_enterprise_batch_file(task_id=task_id, output_path=output_path))

    @server.tool(
        name="hunter_enterprise_batch_pull",
        title="Pull Hunter Enterprise Batch Results as JSON",
        description=(
            "Pull a completed Hunter enterprise batch task as paginated JSON without "
            "writing a local file. Use hunter_enterprise_batch_download for a CSV file "
            "or hunter_enterprise_batch_status while the task is incomplete. This "
            "enterprise-only operation is read-only, consumes Hunter quota, and is "
            "throttled to one call per second."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def hunter_enterprise_batch_pull(
        task_id: Annotated[str, Field(description="Task ID returned by hunter_enterprise_batch_create.")],
        page: Annotated[int, Field(ge=1, description="Page number.")] = 1,
        page_size: Annotated[Literal[100, 200, 500, 1000], Field(description="Results per page.")] = 500,
    ) -> StructuredToolResult:
        return mcp_tool_result(await pull_hunter_enterprise_batch_results(
            task_id=task_id,
            page=page,
            page_size=page_size,
        ))

    @server.tool(
        name="hunter_enterprise_user_info",
        title="Inspect Hunter Enterprise Account and Quota",
        description=(
            "Get Hunter enterprise or sub-account identity, permissions, and remaining "
            "quota. Use hunter_personal_user_info for personal-account details. This "
            "operation is read-only and is throttled to one call per second."
        ),
        annotations=READ_ONLY_REMOTE_TOOL,
    )
    async def hunter_enterprise_user_info() -> StructuredToolResult:
        return mcp_tool_result(await get_hunter_enterprise_user_info())


def create_server() -> SurveyHubMCPServer:
    """Create a Hunter enterprise MCP server."""
    server = SurveyHubMCPServer(
        "hunter-enterprise-mcp",
        title="Hunter Enterprise MCP",
        description="Hunter enterprise cyberspace asset search and quota APIs.",
        instructions="Use Hunter enterprise tools for enterprise-account Hunter APIs.",
        version=__version__,
    )
    register_hunter_enterprise_tools(server)
    register_reference_resources(server, ("hunter-syntax", "hunter-enterprise-api"))
    return server


def main() -> None:
    """Run the Hunter enterprise MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
