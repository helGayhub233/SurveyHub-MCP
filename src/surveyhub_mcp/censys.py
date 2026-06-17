"""Censys MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

CENSYS_BASE_URL = "https://search.censys.io/api"
CENSYS_KEY_URL = "https://search.censys.io/account/api"

CENSYS_SEARCH_FIELDS = (
    "ip, location.country, location.country_code, location.city, "
    "location.province, location.postal_code, location.timezone, "
    "location.continent, location.coordinates, "
    "autonomous_system.asn, autonomous_system.name, autonomous_system.organization, "
    "autonomous_system.country_code, autonomous_system.bgp_prefix, "
    "services.port, services.service_name, services.transport_protocol, "
    "services.banner, services.certificate, services.http.response.body, "
    "services.http.response.status_code, services.http.response.headers, "
    "services.http.response.html_title, services.software, services.tls, "
    "operating_system.product, operating_system.version, operating_system.source, "
    "dns.names, dns.reverse_dns, last_updated_at, labels"
)

CENSYS_AGGREGATION_FIELDS = (
    "services.port, services.service_name, autonomous_system.asn, "
    "location.country, location.country_code, operating_system.product, "
    "protocols, labels"
)

CENSYS_RATE_LIMITER = AsyncRateLimiter(1.1)


def _censys_auth() -> tuple[str, str] | None:
    """Return (api_id, api_secret) tuple for HTTP Basic Auth."""
    api_id = platform_key("CENSYS_API_ID")
    api_secret = platform_key("CENSYS_API_SECRET")
    if api_id and api_secret:
        return api_id, api_secret
    return None


def _missing_key() -> str:
    return missing_env_message(
        platform="Censys",
        env_var="US_CENSYS_API_ID",
        optional_env="US_CENSYS_API_SECRET",
        key_url=CENSYS_KEY_URL,
    ).replace("US_CENSYS_API_ID", "US_CENSYS_API_ID and US_CENSYS_API_SECRET")


async def search_censys(
    *,
    query: str,
    per_page: int = 50,
    cursor: str | None = None,
    fields: str | None = None,
    virtual_hosts: str | None = None,
) -> str:
    """Call Censys v2 hosts search API."""
    if not _censys_auth():
        return _missing_key()

    params: dict[str, str | int] = {}
    if query:
        params["q"] = query
    params["per_page"] = min(per_page, 100)
    if cursor:
        params["cursor"] = cursor
    if fields:
        params["fields"] = fields
    if virtual_hosts:
        params["virtual_hosts"] = virtual_hosts

    await CENSYS_RATE_LIMITER.wait()

    return await request_json(
        platform="Censys",
        method="GET",
        url=f"{CENSYS_BASE_URL}/v2/hosts/search",
        params=params,
        auth=_censys_auth(),
        auth_hint="Authentication failed. Check US_CENSYS_API_ID and US_CENSYS_API_SECRET.",
        forbidden_hint="Access forbidden. Your Censys account may not have sufficient permissions or credits.",
    )


async def aggregate_censys(
    *,
    query: str,
    field: str,
    num_buckets: int = 50,
) -> str:
    """Call Censys v2 hosts aggregate API."""
    if not _censys_auth():
        return _missing_key()

    params: dict[str, str | int] = {
        "q": query,
        "field": field,
        "num_buckets": min(num_buckets, 500),
    }

    await CENSYS_RATE_LIMITER.wait()

    return await request_json(
        platform="Censys",
        method="GET",
        url=f"{CENSYS_BASE_URL}/v2/hosts/aggregate",
        params=params,
        auth=_censys_auth(),
        auth_hint="Authentication failed. Check US_CENSYS_API_ID and US_CENSYS_API_SECRET.",
        forbidden_hint="Access forbidden. Your Censys account may not have sufficient permissions or credits.",
    )


async def view_censys_host(*, ip: str, at_time: str | None = None) -> str:
    """Call Censys v2 host detail API."""
    if not _censys_auth():
        return _missing_key()

    params: dict[str, str] = {}
    if at_time:
        params["at_time"] = at_time

    await CENSYS_RATE_LIMITER.wait()

    return await request_json(
        platform="Censys",
        method="GET",
        url=f"{CENSYS_BASE_URL}/v2/hosts/{ip}",
        params=params,
        auth=_censys_auth(),
        auth_hint="Authentication failed. Check US_CENSYS_API_ID and US_CENSYS_API_SECRET.",
        forbidden_hint="Access forbidden. Your Censys account may not have sufficient permissions or credits.",
    )


async def get_censys_account() -> str:
    """Call Censys v1 account quota API."""
    if not _censys_auth():
        return _missing_key()

    await CENSYS_RATE_LIMITER.wait()

    return await request_json(
        platform="Censys",
        method="GET",
        url=f"{CENSYS_BASE_URL}/v1/account",
        auth=_censys_auth(),
        auth_hint="Authentication failed. Check US_CENSYS_API_ID and US_CENSYS_API_SECRET.",
        forbidden_hint="Access forbidden. Your Censys account may not have sufficient permissions or credits.",
    )


def register_censys_tools(server: FastMCP) -> None:
    """Register Censys tools on a FastMCP server."""

    @server.tool(
        name="censys_search",
        title="Censys Search",
        description=(
            "Search Censys hosts with GET /v2/hosts/search. "
            "Uses Lucene-like query syntax with field:value format. "
            "Consumes 5 credits per query (8 with regex). "
            "Supports nested queries, boolean operators (AND/OR/NOT), "
            "and comparison operators (=, :, =~, >, <). "
            f"Common fields: {CENSYS_SEARCH_FIELDS}."
        ),
        structured_output=False,
    )
    async def censys_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "Censys search query using field:value syntax. "
                    'Examples: services.service_name: HTTP, '
                    'location.country: "United States" and services.port: 443, '
                    "autonomous_system.name: Google"
                )
            ),
        ],
        per_page: Annotated[int, Field(ge=1, le=100, description="Results per page (max 100).")] = 50,
        cursor: Annotated[
            str | None,
            Field(description="Base64 page cursor from previous response links.next for pagination."),
        ] = None,
        fields: Annotated[
            str | None,
            Field(description="Comma-separated dot-notation fields to return (max 25)."),
        ] = None,
        virtual_hosts: Annotated[
            str | None,
            Field(description="Virtual host handling: EXCLUDE, INCLUDE, or ONLY."),
        ] = None,
    ) -> str:
        return await search_censys(
            query=query,
            per_page=per_page,
            cursor=cursor,
            fields=fields,
            virtual_hosts=virtual_hosts,
        )

    @server.tool(
        name="censys_aggregate",
        title="Censys Aggregate",
        description=(
            "Aggregate Censys host search results by a field with GET /v2/hosts/aggregate. "
            "Useful for distribution analysis (e.g., ports, countries, services). "
            f"Suggested fields: {CENSYS_AGGREGATION_FIELDS}."
        ),
        structured_output=False,
    )
    async def censys_aggregate(
        query: Annotated[str, Field(description="Censys search query.")],
        field: Annotated[
            str,
            Field(description="Field to aggregate on, e.g. services.port, location.country."),
        ],
        num_buckets: Annotated[int, Field(ge=1, le=500, description="Number of buckets (max 500).")] = 50,
    ) -> str:
        return await aggregate_censys(query=query, field=field, num_buckets=num_buckets)

    @server.tool(
        name="censys_view_host",
        title="Censys View Host",
        description=(
            "Get detailed Censys host information for a single IP with GET /v2/hosts/{ip}. "
            "Returns services, location, autonomous system, operating system, DNS records, and labels."
        ),
        structured_output=False,
    )
    async def censys_view_host(
        ip: Annotated[str, Field(description="IP address, e.g. 8.8.8.8.")],
        at_time: Annotated[
            str | None,
            Field(description="Historical snapshot timestamp in RFC 3339 format, e.g. 2025-01-01T00:00:00Z."),
        ] = None,
    ) -> str:
        return await view_censys_host(ip=ip, at_time=at_time)

    @server.tool(
        name="censys_account",
        title="Censys Account",
        description="Get Censys account quota information: used credits, allowance, and resets_at with GET /v1/account.",
        structured_output=False,
    )
    async def censys_account() -> str:
        return await get_censys_account()


def create_server() -> FastMCP:
    """Create a single-platform Censys MCP server."""
    server = FastMCP(
        "censys-mcp",
        instructions="Use Censys tools for cyberspace host search, aggregation, and host intelligence APIs.",
    )
    register_censys_tools(server)
    return server


def main() -> None:
    """Run the Censys MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
