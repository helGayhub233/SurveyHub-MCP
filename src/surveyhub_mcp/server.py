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
    "Cyberspace asset search: FOFA, 360 Quake, Hunter Personal/Enterprise, ZoomEye, DayDayMap. "
    "Use the connected server's tools/list as the current tool and schema catalog. "
    "Select the matching platform/account tool; keep Hunter editions distinct. "
    "Use returned_count/completeness/next_action and pagination's reusable cursors. "
    "next_action=refine_query and meta.output mean local clipping: narrow fields or page size "
    "before continuing; repeat calls may consume quota. Full response field documentation: "
    "surveyhub://reference/response-schema."
)

_ASSET_CORRELATION_FORMULA = (
    "Official asset-correlation formula: ICP unit name <-> domain <-> IP <-> "
    "certificate fingerprint <-> icon hash. Classify the user's single target as a domain, "
    "IP/CIDR, ICP unit name, certificate fingerprint, or icon hash and traverse both directions. "
    "Platform node support follows the formulas below. FOFA cert searches text/subject; "
    "Quake supports certificate SHA256/SPKI and favicon MD5; Hunter supports SHA256; "
    "ZoomEye supports fingerprints; DayDayMap queries certificate MD5 (SHA256 is output-only). "
    "For an unsupported seed, derive a supported sibling from another configured source first."
)

_MVP_TARGET_DISCOVERY_INSTRUCTIONS = (
    "MVP target discovery: Query every configured credential source in one batch when "
    "the client supports parallel calls. Unless the user requests another range, "
    "restrict discovery to assets updated in the last 1 year: FOFA keeps full=false; "
    "Quake sets start_time to one year ago (UTC); Hunter sets start_time/end_time; "
    "ZoomEye appends after=\"YYYY-MM-DD\"; DayDayMap appends time>\"YYYY-MM-DD\". "
    "Platform formulas: FOFA domain=, ip=, icp= (number), icon_hash=, cert=; Quake "
    "domain:, ip:, icp:, favicon:, cert:, tls_sha256:, tls_SPKI:; Hunter domain=, ip=, "
    "icp.name=, icp.number=, web.icon=, cert.sha-256=; ZoomEye domain=, ip=, cidr=, "
    "icp.name=, icp.number=, iconhash=, ssl.cert.fingerprint=; DayDayMap domain=, ip=, "
    "icp.name=, icp.number=, web.icon=, cert.md5=, cert.subject.cn=. Icon hash is "
    "supplemental evidence: official_icon_hash comes from the target's canonical homepage; "
    "vendor_icon_hash comes from a provider or other page and has lower confidence "
    "(generic shared icons lowest). Icon equality alone must not merge or discard relationships. "
    "Normalize and deduplicate the relationship graph by node type/value: lowercase domains, "
    "canonical IPs, certificate algorithm+hash, icon hash+provenance. Union source evidence "
    "and return one asset/relationship result with source coverage gaps."
)

_ASSET_PIVOT_INSTRUCTIONS = (
    "Default to one bounded page per platform, at most 3 derived pivots and 100 total "
    "records. Do not fetch all pages, fan out recursively, or write a local script unless "
    "explicitly requested; cursor/batch tools require a user budget. Aggregate record/pivot "
    "budgets are client guidance; per-call page, CSV, and output limits are enforced."
)

_STARTUP_AND_SYNTAX_STATE_MACHINE = (
    "Startup and syntax state machine: runtime credentials are a launch-time snapshot; "
    "restart after environment changes. For configured platforms with unknown quota, "
    "run user_info before a metered search; search sources with adequate quota. DayDayMap "
    "has no user_info; error 2004 means insufficient credits. For missing_key, skip "
    "search and user_info, show the required environment variable and record a coverage gap; "
    "missing_key is a preflight state, not a provider failure. Translate every seed/pivot: "
    "FOFA and ZoomEye use field=\"value\" with &&/||; Quake "
    "uses field:\"value\" with AND/OR/NOT; Hunter and DayDayMap use field=\"value\" "
    "with &&/||. On syntax errors, correct the destination grammar using its reference "
    "or derive a supported sibling; do not label the platform unavailable. For ICP unit "
    "names, use icp.name sources first, derive domain or ICP number, then use FOFA icp= "
    "or Quake icp:; do not send an ICP "
    "unit-name query to FOFA or Quake."
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
            next_step = f"{probe} -> search" if probe else "search directly (no quota probe)"
            return f"{label}: state=configured, credential_env={source}, next={next_step}"
        required_env = {
            "FOFA": "CN_FOFA_KEY",
            "Quake": "CN_QUAKE_KEY",
            "Hunter Personal": "CN_HUNTER_PERSONAL_KEY or CN_HUNTER_KEY",
            "Hunter Enterprise": "CN_HUNTER_ENTERPRISE_KEY or CN_HUNTER_KEY",
            "ZoomEye": "CN_ZOOMEYE_API_KEY",
            "DayDayMap": "CN_DAYDAYMAP_API_KEY",
        }[label]
        return (
            f"{label}: state=missing_key, required_env={required_env}, "
            "next=skip search + setup guidance + coverage gap"
        )

    return "Startup platform state machine: " + " | ".join(
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
            f"{_STARTUP_AND_SYNTAX_STATE_MACHINE} "
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
