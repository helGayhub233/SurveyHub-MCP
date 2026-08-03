"""Aggregate MCP server for FOFA, Quake, Hunter, ZoomEye, and DayDayMap."""

from __future__ import annotations

from . import __version__
from .common import SurveyHubMCPServer
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
    "Never collapse Hunter Personal and Hunter Enterprise into a generic Hunter availability result."
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
        instructions=f"{SERVER_INSTRUCTIONS} {hunter_runtime_guidance()}",
        version=__version__,
    )
    register_fofa_tools(server)
    register_quake_tools(server)
    personal_source = hunter_personal_key_source()
    enterprise_source = hunter_enterprise_key_source()
    # A version-specific credential is authoritative. Hiding the unavailable
    # sibling prevents agents from turning a wrong-edition credential error into
    # the false conclusion that Hunter itself is unavailable. With no credential,
    # both families remain discoverable so their schemas explain configuration.
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
