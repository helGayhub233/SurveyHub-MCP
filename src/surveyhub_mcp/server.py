"""Aggregate MCP server for FOFA, Quake, Hunter, ZoomEye, and DayDayMap."""

from __future__ import annotations

from datetime import date, timedelta

from . import __version__
from .common import SurveyHubMCPServer, canonical_env_name, platform_key
from .daydaymap import register_daydaymap_tools
from .fofa import register_fofa_tools
from .hunter_enterprise import hunter_enterprise_key_source, register_hunter_enterprise_tools
from .hunter_personal import hunter_personal_key_source, register_hunter_personal_tools
from .quake import register_quake_tools
from .reference import register_reference_prompts, register_reference_resources
from .zoomeye import register_zoomeye_tools

SERVER_INSTRUCTIONS = (
    "This server exposes cyberspace asset search tools for FOFA, 360 Quake, "
    "the configured Hunter account edition, ZoomEye APIs, and DayDayMap APIs. "
    "Use the platform- and account-specific tool that matches the user's target data source. "
    "Never collapse Hunter Personal and Hunter Enterprise into a generic Hunter availability result. "
    "All search and aggregation calls are single-call bounded reads: use the returned "
    "returned_count/completeness/next_action fields, keep one page per tool call, and do not "
    "fan out pages or create a local script unless the user explicitly requests an exhaustive export."
)

_ASSET_CORRELATION_FORMULA = (
    "Official asset-correlation formula: ICP unit name <-> domain <-> IP <-> "
    "certificate fingerprint <-> icon hash. Classify the user's single target as one "
    "of those nodes, seed every configured platform with its native query syntax, and "
    "traverse the formula in both directions. Platform node support: FOFA domain, IP, "
    "ICP number, certificate text/subject, icon hash; Quake domain, IP, ICP number, "
    "certificate SHA256/SPKI, favicon MD5; Hunter domain, IP, ICP unit name/number, "
    "certificate SHA256, icon query; ZoomEye domain, IP, ICP unit name/number, "
    "certificate fingerprint, icon hash; DayDayMap domain, IP, ICP unit name/number, "
    "certificate MD5, icon. When a source cannot seed the supplied node, derive a "
    "supported sibling node from another configured source first (for example, ICP "
    "unit name -> domain or ICP number), then query that source."
)

_MVP_TARGET_DISCOVERY_INSTRUCTIONS = (
    "MVP target discovery: infer whether the single user target is a domain, IP/CIDR, "
    "ICP unit name, certificate fingerprint, or icon hash. Query every configured "
    "credential source in one batch when the MCP client supports parallel calls; if a "
    "source cannot query that node directly, first derive a supported sibling node from "
    "another source, then query it. Unless the user explicitly requests another range, "
    "restrict discovery to assets updated in the last 1 year: FOFA keeps full=false; "
    "Quake sets start_time to one year ago (UTC); Hunter sets start_time/end_time; "
    "ZoomEye appends after=\"YYYY-MM-DD\"; DayDayMap appends time>\"YYYY-MM-DD\". "
    "Platform formulas: FOFA domain=, ip=, icp= (number), icon_hash=, cert=; Quake "
    "domain:, ip:, icp:, favicon:, cert:, tls_sha256:, tls_SPKI:; Hunter domain=, ip=, "
    "icp.name=, icp.number=, web.icon=, cert.sha-256=; ZoomEye domain=, ip=, cidr=, "
    "icp.name=, icp.number=, iconhash=, ssl.cert.fingerprint=; DayDayMap domain=, ip=, "
    "icp.name=, icp.number=, web.icon=, cert.md5=, cert.subject.cn=. Icon hash is a "
    "supplemental pivot, not proof of ownership: mark an icon observed on the target's "
    "canonical official homepage as official_icon_hash (higher confidence), and a "
    "provider-derived or non-official-page icon as vendor_icon_hash (lower confidence; "
    "generic shared icons are lowest). Do not merge or discard relationships solely on "
    "icon-hash equality. After all source queries, normalize and deduplicate the "
    "relationship graph by node type and value (lowercase domains, canonical IPs, "
    "certificate fingerprint algorithm plus hash, icon hash plus provenance), union "
    "source evidence, then return one final asset and relationship result with source "
    "coverage gaps."
)

_ASSET_PIVOT_INSTRUCTIONS = (
    "Multi-source discovery workflow. When the user asks to map an organization's "
    "or target's assets without naming a tool: (1) identify the configured platforms "
    "from the runtime configuration below; (2) before the first metered search on each "
    "platform whose quota is unknown, call its user_info tool to verify remaining quota "
    "(DayDayMap exposes no user_info tool; insufficient credits there surface as provider "
    "error code 2004); (3) search every configured platform with adequate quota - never a "
    "single one - and expand the seed along the correlation chain domain -> IP -> ICP -> "
    "icon hash -> TLS certificate fingerprint: derive sibling values from returned assets "
    "(domains, IPs, ICP numbers, icon hashes, certificate subjects or fingerprints) and "
    "query each derived value back on the other platforms using each platform's own query "
    "syntax described in its search tool; (4) merge and de-duplicate assets across sources, "
    "preferring narrow chained queries over broad ones, and never report a platform as "
    "unavailable when its key is merely not configured - expose its setup guidance instead. "
    "Default to one bounded page per platform, at most 3 derived pivots and 100 total "
    "records. Do not fetch all pages, fan out recursively, or write a local script unless "
    "the user explicitly requests exhaustive collection or export; use cursor or batch "
    "tools only within an explicit user-supplied budget."
)


def platform_runtime_guidance() -> str:
    """Describe which platform credentials are configured without disclosing values."""

    def key_source(*var_names: str) -> str | None:
        for name in var_names:
            if platform_key(name):
                return canonical_env_name(name)
        return None

    fofa = key_source("FOFA_KEY")
    quake = key_source("QUAKE_KEY")
    zoomeye = key_source("ZOOMEYE_API_KEY")
    daydaymap = key_source("DAYDAYMAP_API_KEY")
    hunter_personal = hunter_personal_key_source()
    hunter_enterprise = hunter_enterprise_key_source()

    def status(label: str, source: str | None, *, probe: str | None = None) -> str:
        if source:
            suffix = f" (probe quota via {probe}) " if probe else " "
            return f"{label}: configured in {source}{suffix}"
        return f"{label}: not configured"

    return "Runtime platform configuration: " + " | ".join(
        [
            status("FOFA", fofa, probe="fofa_user_info"),
            status("Quake", quake, probe="quake_user_info"),
            status("Hunter Personal", hunter_personal, probe="hunter_personal_user_info"),
            status("Hunter Enterprise", hunter_enterprise, probe="hunter_enterprise_user_info"),
            status("ZoomEye", zoomeye, probe="zoomeye_user_info"),
            status("DayDayMap", daydaymap),
        ]
    )


def default_search_window_guidance() -> str:
    """Return the concrete default one-year discovery window."""
    today = date.today()
    one_year_ago = today - timedelta(days=365)
    return (
        f"Default one-year discovery window: {one_year_ago.isoformat()} to "
        f"{today.isoformat()}. Hunter queries older than 30 days may consume equity "
        "points; check quota before expanding the range."
    )


def hunter_runtime_guidance() -> str:
    """Describe credential routing without disclosing credential values."""
    personal_source = hunter_personal_key_source()
    enterprise_source = hunter_enterprise_key_source()
    if enterprise_source and not personal_source:
        status = (
            f"Hunter Enterprise is configured through {enterprise_source}; Hunter Personal is not configured. "
            "Only hunter_enterprise_* tools are exposed; use them and do not report Hunter as unavailable."
        )
    elif personal_source and not enterprise_source:
        status = (
            f"Hunter Personal is configured through {personal_source}; Hunter Enterprise is not configured. "
            "Only hunter_personal_* tools are exposed; use them and do not report Hunter as unavailable."
        )
    elif personal_source == enterprise_source == "CN_HUNTER_KEY":
        status = (
            "A shared CN_HUNTER_KEY is configured for both Hunter editions. Select hunter_personal_* or "
            "hunter_enterprise_* according to the user's account edition and requested fields."
        )
    elif personal_source and enterprise_source:
        status = (
            f"Both Hunter editions are configured: Personal through {personal_source}, Enterprise through "
            f"{enterprise_source}. Select the explicitly matching tool family."
        )
    else:
        status = (
            "No Hunter credentials are configured. Personal accepts CN_HUNTER_PERSONAL_KEY or CN_HUNTER_KEY; "
            "Enterprise accepts CN_HUNTER_ENTERPRISE_KEY or CN_HUNTER_KEY."
        )
    return f"Runtime credential routing: {status} Restart the MCP process after changing its environment."


def create_server() -> SurveyHubMCPServer:
    """Create the aggregate MCP server."""
    server = SurveyHubMCPServer(
        "surveyhub-mcp",
        title="SurveyHub MCP",
        description="Cyberspace asset search across FOFA, Quake, Hunter, ZoomEye, and DayDayMap.",
        instructions=(
            f"{SERVER_INSTRUCTIONS} {_ASSET_CORRELATION_FORMULA} "
            f"{_MVP_TARGET_DISCOVERY_INSTRUCTIONS} "
            f"{default_search_window_guidance()} "
            f"{_ASSET_PIVOT_INSTRUCTIONS} "
            f"{platform_runtime_guidance()} {hunter_runtime_guidance()}"
        ),
        version=__version__,
    )
    register_fofa_tools(server)
    register_quake_tools(server)
    personal_source = hunter_personal_key_source()
    enterprise_source = hunter_enterprise_key_source()
    # A version-specific credential is authoritative. Hide the unavailable
    # sibling so agents do not mistake an edition mismatch for total
    # unavailability. Expose both families when no credential is configured.
    if personal_source or not enterprise_source:
        register_hunter_personal_tools(server)
    if enterprise_source or not personal_source:
        register_hunter_enterprise_tools(server)
    register_zoomeye_tools(server)
    register_daydaymap_tools(server)
    register_reference_resources(server)
    register_reference_prompts(server)
    return server


def main() -> None:
    """Run the aggregate MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
