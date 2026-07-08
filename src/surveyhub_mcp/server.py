"""Aggregate MCP server for FOFA, Quake, Hunter, ZoomEye, and DayDayMap."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .common import apply_server_metadata
from .daydaymap import register_daydaymap_tools
from .fofa import register_fofa_tools
from .hunter_enterprise import register_hunter_enterprise_tools
from .hunter_personal import register_hunter_personal_tools
from .quake import register_quake_tools
from .reference import register_reference_prompts, register_reference_resources
from .zoomeye import register_zoomeye_tools

SERVER_INSTRUCTIONS = (
    "This server exposes cyberspace asset search tools for FOFA, 360 Quake, "
    "Hunter personal APIs, Hunter enterprise APIs, ZoomEye APIs, and DayDayMap APIs. "
    "Use the platform- and account-specific tool that matches the user's target data source."
)


def create_server() -> FastMCP:
    """Create the aggregate MCP server."""
    server = FastMCP("surveyhub-mcp", instructions=SERVER_INSTRUCTIONS)
    apply_server_metadata(server)
    register_fofa_tools(server)
    register_quake_tools(server)
    register_hunter_personal_tools(server)
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
