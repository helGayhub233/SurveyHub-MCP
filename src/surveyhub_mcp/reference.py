"""MCP resources and prompts for SurveyHub reference material."""

from __future__ import annotations

from pathlib import Path

from mcp.server import MCPServer

_PACKAGE_DOCS_DIR = Path(__file__).resolve().parent / "docs"
_REPO_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
_DOCS_DIR = _PACKAGE_DOCS_DIR if _PACKAGE_DOCS_DIR.exists() else _REPO_DOCS_DIR

_REFERENCE_FILES = {
    "fofa-syntax": ("FOFA Syntax", "docs/syntax/fofa_syntax.md"),
    "quake-syntax": ("Quake Syntax", "docs/syntax/quake_syntax.md"),
    "hunter-syntax": ("Hunter Syntax", "docs/syntax/hunter_syntax.md"),
    "zoomeye-syntax": ("ZoomEye Syntax", "docs/syntax/zoomeye_syntax.md"),
    "fofa-api": ("FOFA API", "docs/api/fofa_api.md"),
    "quake-api": ("Quake API", "docs/api/quake_api.md"),
    "hunter-personal-api": ("Hunter Personal API", "docs/api/hunter_personal_api.md"),
    "hunter-enterprise-api": ("Hunter Enterprise API", "docs/api/hunter_enterprise_api.md"),
    "zoomeye-api": ("ZoomEye API", "docs/api/zoomeye_api.md"),
    "daydaymap-api": ("DayDayMap API", "docs/api/daydaymap_api.md"),
}


def _read_doc(relative_path: str) -> str:
    path = _DOCS_DIR / relative_path.removeprefix("docs/")
    return path.read_text(encoding="utf-8")


def register_reference_resources(server: MCPServer, names: tuple[str, ...] | None = None) -> None:
    """Register read-only syntax and API reference documents."""
    selected_names = names or tuple(_REFERENCE_FILES)

    def make_reader(relative_path: str):
        def read_reference() -> str:
            return _read_doc(relative_path)

        return read_reference

    for resource_name in selected_names:
        title, relative_path = _REFERENCE_FILES[resource_name]

        server.resource(
            f"surveyhub://reference/{resource_name}",
            name=resource_name,
            title=title,
            description=f"Reference document for {title}.",
            mime_type="text/markdown",
        )(make_reader(relative_path))


def register_reference_prompts(server: MCPServer) -> None:
    """Register reusable prompts for common SurveyHub workflows."""

    @server.prompt(
        name="surveyhub_search_plan",
        title="SurveyHub Search Plan",
        description="Create a safe, multi-platform asset correlation search plan before calling SurveyHub tools.",
    )
    def surveyhub_search_plan(target: str, platform: str = "auto") -> str:
        return (
            "Build a concise multi-source cyberspace asset search plan.\n"
            f"Target: {target}\n"
            f"Preferred platform: {platform} (use 'auto' to query every configured platform)\n"
            "1. Sources: identify configured platforms from the server's runtime "
            "configuration; probe each one's remaining quota with its user_info tool "
            "before the first metered search (DayDayMap has no user_info; its "
            "insufficient-credits case surfaces as provider error code 2004).\n"
            "2. Seed: craft a narrow domain/IP/ICP seed query for the target on each "
            "configured platform, using that platform's own syntax from its search tool "
            "description.\n"
            "3. Correlate: expand along the chain domain -> IP -> ICP -> icon hash -> TLS "
            "certificate fingerprint; derive sibling values from returned assets and "
            "query them back across the other platforms (each platform has different "
            "pivot field syntax).\n"
            "4. Merge: combine and de-duplicate assets across sources; call out per-source "
            "coverage gaps instead of treating one platform's result as complete.\n"
            "Prefer narrow queries, explain quota-impacting options (full, page depth, "
            "retry), and avoid destructive actions. Never report a platform as "
            "unavailable when its key is merely not configured."
        )

    @server.prompt(
        name="surveyhub_query_help",
        title="SurveyHub Query Help",
        description="Explain or improve a FOFA, Quake, Hunter, ZoomEye, or DayDayMap query.",
    )
    def surveyhub_query_help(query: str, platform: str) -> str:
        return (
            f"Review this {platform} query and suggest a correct, narrower version if needed:\n"
            f"{query}\n"
            "Call out syntax issues, escaping requirements, pagination limits, and fields worth returning."
        )
