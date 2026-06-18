"""Shodan MCP tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .common import AsyncRateLimiter, missing_env_message, platform_key, request_json

SHODAN_BASE_URL = "https://api.shodan.io"
SHODAN_KEY_URL = "https://account.shodan.io"

SHODAN_SEARCH_FILTERS = (
    "General: asn, city, country, cpe, device, domain, geo, has_ssl, has_vuln, "
    "hostname, ip, isp, net, org, os, port, product, region, version. "
    "HTTP: http.title, http.status, http.html, http.favicon.hash, http.component "
    "http.waf, http.robots_hash. "
    "SSL: ssl, ssl.cert.expired, ssl.cert.issuer.cn, ssl.cert.subject.cn, "
    "ssl.ja3s, ssl.jarm, ssl.version, ssl.cipher.name, ssl.cert.fingerprint. "
    "Cloud: cloud.provider, cloud.region, cloud.service. "
    "Others: ssh.hassh, ssh.type, bitcoin.ip, tag, vuln, screenshot.label."
)

SHODAN_FACETS = (
    "asn, bitcoin.ip, bitcoin.ip_count, bitcoin.port, cloud.provider, "
    "cloud.service, country, cpe, device, domain, has_ssl, hostname, "
    "http.component, http.component_category, http.favicon.hash, http.html_hash, "
    "http.robots_hash, http.securitytxt, http.status, http.title, "
    "http.waf, ip, isp, ntp.ip, ntp.ip_count, ntp.more, ntp.port, "
    "org, os, port, product, region, screenshot.label, shodan.module, "
    "ssh.hassh, ssh.type, ssl, ssl.alpn, ssl.cert.alg, ssl.cert.expired, "
    "ssl.cert.pubkey.bits, ssl.cert.pubkey.type, ssl.cipher.name, "
    "ssl.cipher.version, ssl.ja3s, ssl.jarm, ssl.version, state, tag, "
    "version, vuln"
)

SHODAN_SEARCH_RATE_LIMITER = AsyncRateLimiter(1.1)


def _shodan_key() -> str | None:
    return platform_key("SHODAN_API_KEY")


def _missing_key() -> str:
    return missing_env_message(
        platform="Shodan",
        env_var="US_SHODAN_API_KEY",
        key_url=SHODAN_KEY_URL,
    )


def _auth_params() -> dict[str, str]:
    key = _shodan_key()
    return {"key": key} if key else {}


def _build_url(path: str, params: dict[str, str | int | bool]) -> str:
    """Build a Shodan API URL with auth params."""
    import urllib.parse

    query = urllib.parse.urlencode({k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()})
    return f"{SHODAN_BASE_URL}{path}?{query}"


async def search_shodan(
    *,
    query: str,
    page: int = 1,
    facets: str | None = None,
) -> str:
    """Call Shodan search API."""
    if not _shodan_key():
        return _missing_key()

    params: dict[str, str | int] = _auth_params()
    params["query"] = query
    params["page"] = page
    if facets:
        params["facets"] = facets

    await SHODAN_SEARCH_RATE_LIMITER.wait()

    return await request_json(
        platform="Shodan",
        method="GET",
        url=_build_url("/shodan/host/search", params),
        auth_hint="Authentication failed. Check US_SHODAN_API_KEY.",
        forbidden_hint="Access forbidden. Your Shodan plan may not have sufficient permissions.",
    )


async def search_shodan_count(
    *,
    query: str,
    facets: str | None = None,
) -> str:
    """Call Shodan count API (no query credits consumed)."""
    if not _shodan_key():
        return _missing_key()

    params: dict[str, str | int] = _auth_params()
    params["query"] = query
    if facets:
        params["facets"] = facets

    await SHODAN_SEARCH_RATE_LIMITER.wait()

    return await request_json(
        platform="Shodan",
        method="GET",
        url=_build_url("/shodan/host/count", params),
        auth_hint="Authentication failed. Check US_SHODAN_API_KEY.",
        forbidden_hint="Access forbidden. Your Shodan plan may not have sufficient permissions.",
    )


async def get_shodan_host(*, ip: str, history: bool = False, minify: bool = False) -> str:
    """Call Shodan host info API."""
    if not _shodan_key():
        return _missing_key()

    params: dict[str, str | int | bool] = _auth_params()
    if history:
        params["history"] = True
    if minify:
        params["minify"] = True

    await SHODAN_SEARCH_RATE_LIMITER.wait()

    return await request_json(
        platform="Shodan",
        method="GET",
        url=_build_url(f"/shodan/host/{ip}", params),
        auth_hint="Authentication failed. Check US_SHODAN_API_KEY.",
        forbidden_hint="Access forbidden. Your Shodan plan may not have sufficient permissions.",
    )


async def get_shodan_api_info() -> str:
    """Call Shodan API plan info."""
    if not _shodan_key():
        return _missing_key()

    params = _auth_params()

    await SHODAN_SEARCH_RATE_LIMITER.wait()

    return await request_json(
        platform="Shodan",
        method="GET",
        url=_build_url("/api-info", params),
        auth_hint="Authentication failed. Check US_SHODAN_API_KEY.",
        forbidden_hint="Access forbidden. Your Shodan account may not have sufficient permissions.",
    )


async def get_shodan_domain(*, domain: str) -> str:
    """Call Shodan domain info API (subdomains and DNS records)."""
    if not _shodan_key():
        return _missing_key()

    params = _auth_params()

    await SHODAN_SEARCH_RATE_LIMITER.wait()

    return await request_json(
        platform="Shodan",
        method="GET",
        url=_build_url(f"/dns/domain/{domain}", params),
        auth_hint="Authentication failed. Check US_SHODAN_API_KEY.",
        forbidden_hint="Access forbidden. Your Shodan plan may not have sufficient permissions.",
    )


async def resolve_shodan_dns(*, hostnames: str) -> str:
    """Call Shodan DNS forward lookup."""
    if not _shodan_key():
        return _missing_key()

    params: dict[str, str | int] = _auth_params()
    params["hostnames"] = hostnames

    await SHODAN_SEARCH_RATE_LIMITER.wait()

    return await request_json(
        platform="Shodan",
        method="GET",
        url=_build_url("/dns/resolve", params),
        auth_hint="Authentication failed. Check US_SHODAN_API_KEY.",
        forbidden_hint="Access forbidden. Your Shodan plan may not have sufficient permissions.",
    )


async def reverse_shodan_dns(*, ips: str) -> str:
    """Call Shodan DNS reverse lookup."""
    if not _shodan_key():
        return _missing_key()

    params: dict[str, str | int] = _auth_params()
    params["ips"] = ips

    await SHODAN_SEARCH_RATE_LIMITER.wait()

    return await request_json(
        platform="Shodan",
        method="GET",
        url=_build_url("/dns/reverse", params),
        auth_hint="Authentication failed. Check US_SHODAN_API_KEY.",
        forbidden_hint="Access forbidden. Your Shodan plan may not have sufficient permissions.",
    )


def register_shodan_tools(server: FastMCP) -> None:
    """Register Shodan tools on a FastMCP server."""

    @server.tool(
        name="shodan_search",
        title="Shodan Search",
        description=(
            "Search Shodan assets with GET /shodan/host/search. "
            "Uses Shodan query syntax with filter:value format. "
            "Consumes 1 query credit per filtered search or past page 1. "
            f"Supported filters: {SHODAN_SEARCH_FILTERS}. "
            "Negate with - prefix (e.g., -port:22). Multiple filter values use comma as OR."
        ),
        structured_output=False,
    )
    async def shodan_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "Shodan search query using filter:value syntax. "
                    'Examples: apache, product:"Apache httpd" country:CN, '
                    "port:22 country:US, org:\"Google\", has_vuln:true"
                )
            ),
        ],
        page: Annotated[int, Field(ge=1, description="Page number. 100 results per page.")] = 1,
        facets: Annotated[
            str | None,
            Field(description=f"Comma-separated facet names, e.g. org,os,country. Supported: {SHODAN_FACETS}."),
        ] = None,
    ) -> str:
        return await search_shodan(
            query=query,
            page=page,
            facets=facets,
        )

    @server.tool(
        name="shodan_search_count",
        title="Shodan Search Count",
        description=(
            "Get Shodan search result count with optional facet aggregation via GET /shodan/host/count. "
            "Does NOT consume query credits. Use this before shodan_search to preview result size."
        ),
        structured_output=False,
    )
    async def shodan_search_count(
        query: Annotated[str, Field(description="Shodan search query using filter:value syntax.")],
        facets: Annotated[
            str | None,
            Field(description=f"Comma-separated facet names, e.g. org,os,country:100."),
        ] = None,
    ) -> str:
        return await search_shodan_count(query=query, facets=facets)

    @server.tool(
        name="shodan_host",
        title="Shodan Host Info",
        description=(
            "Get all services found on an IP address with GET /shodan/host/{ip}. "
            "Returns banners, ports, SSL info, location, organization, and more. "
            "Calls are throttled to 1 request per second."
        ),
        structured_output=False,
    )
    async def shodan_host(
        ip: Annotated[str, Field(description="IP address, e.g. 8.8.8.8.")],
        history: Annotated[bool, Field(description="Set true to return all historical banners.")] = False,
        minify: Annotated[bool, Field(description="Set true to return only ports and general info, no banners.")] = False,
    ) -> str:
        return await get_shodan_host(ip=ip, history=history, minify=minify)

    @server.tool(
        name="shodan_api_info",
        title="Shodan API Info",
        description="Get Shodan API plan details: query credits, scan credits, monitored IPs, and plan name.",
        structured_output=False,
    )
    async def shodan_api_info() -> str:
        return await get_shodan_api_info()

    @server.tool(
        name="shodan_domain",
        title="Shodan Domain Info",
        description=(
            "Get Shodan domain information (subdomains + DNS records) with GET /dns/domain/{domain}. "
            "Consumes 1 query credit per lookup."
        ),
        structured_output=False,
    )
    async def shodan_domain(
        domain: Annotated[str, Field(description="Domain name, e.g. google.com.")],
    ) -> str:
        return await get_shodan_domain(domain=domain)

    @server.tool(
        name="shodan_dns_resolve",
        title="Shodan DNS Resolve",
        description="Forward DNS lookup: resolves one or more hostnames to IP addresses via GET /dns/resolve.",
        structured_output=False,
    )
    async def shodan_dns_resolve(
        hostnames: Annotated[str, Field(description="Comma-separated hostnames, e.g. google.com,bing.com.")],
    ) -> str:
        return await resolve_shodan_dns(hostnames=hostnames)

    @server.tool(
        name="shodan_dns_reverse",
        title="Shodan DNS Reverse",
        description="Reverse DNS lookup: resolves one or more IPs to hostnames via GET /dns/reverse.",
        structured_output=False,
    )
    async def shodan_dns_reverse(
        ips: Annotated[str, Field(description="Comma-separated IP addresses, e.g. 8.8.8.8,1.1.1.1.")],
    ) -> str:
        return await reverse_shodan_dns(ips=ips)


def create_server() -> FastMCP:
    """Create a single-platform Shodan MCP server."""
    server = FastMCP(
        "shodan-mcp",
        instructions="Use Shodan tools for cyberspace asset search, host intelligence, and DNS APIs.",
    )
    register_shodan_tools(server)
    return server


def main() -> None:
    """Run the Shodan MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
