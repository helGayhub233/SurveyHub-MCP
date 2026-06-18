"""Aggregate MCP server for FOFA, Quake, Hunter, ZoomEye, DayDayMap, Shodan, Censys, SecurityTrails, BinaryEdge, Netlas, Onyphe, LeakIX, FullHunt, and Criminal IP."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .binaryedge import register_binaryedge_tools
from .censys import register_censys_tools
from .criminalip import register_criminalip_tools
from .daydaymap import register_daydaymap_tools
from .fofa import register_fofa_tools
from .fullhunt import register_fullhunt_tools
from .leakix import register_leakix_tools
from .netlas import register_netlas_tools
from .onyphe import register_onyphe_tools
from .securitytrails import register_securitytrails_tools
from .shodan import register_shodan_tools
from .hunter_enterprise import register_hunter_enterprise_tools
from .hunter_personal import register_hunter_personal_tools
from .quake import register_quake_tools
from .zoomeye import register_zoomeye_tools

SERVER_INSTRUCTIONS = (
    "This server exposes cyberspace asset search tools for FOFA, 360 Quake, "
    "Hunter personal APIs, Hunter enterprise APIs, ZoomEye APIs, DayDayMap APIs, Shodan APIs, Censys APIs, SecurityTrails APIs, BinaryEdge APIs, Netlas APIs, Onyphe APIs, LeakIX APIs, FullHunt APIs, and Criminal IP APIs. "
    "Use the platform- and account-specific tool that matches the user's target data source."
)


def create_server() -> FastMCP:
    """Create the aggregate MCP server."""
    server = FastMCP("surveyhub-mcp", instructions=SERVER_INSTRUCTIONS)
    register_fofa_tools(server)
    register_quake_tools(server)
    register_hunter_personal_tools(server)
    register_hunter_enterprise_tools(server)
    register_zoomeye_tools(server)
    register_daydaymap_tools(server)
    register_shodan_tools(server)
    register_censys_tools(server)
    register_securitytrails_tools(server)
    register_binaryedge_tools(server)
    register_netlas_tools(server)
    register_onyphe_tools(server)
    register_leakix_tools(server)
    register_fullhunt_tools(server)
    register_criminalip_tools(server)
    return server


def main() -> None:
    """Run the aggregate MCP server over stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
