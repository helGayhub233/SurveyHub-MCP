"""MCP resources and prompts for SurveyHub reference material."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

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


def register_reference_resources(server: FastMCP, names: tuple[str, ...] | None = None) -> None:
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


def register_reference_prompts(server: FastMCP) -> None:
    """Register reusable prompts for common SurveyHub workflows."""

    @server.prompt(
        name="surveyhub_search_plan",
        title="SurveyHub Search Plan",
        description="Create a safe, platform-aware asset search plan before calling SurveyHub tools.",
    )
    def surveyhub_search_plan(target: str, platform: str = "auto") -> str:
        return (
            "Build a concise cyberspace asset search plan.\n"
            f"Target: {target}\n"
            f"Preferred platform: {platform}\n"
            "Use the matching SurveyHub syntax reference resource when needed. "
            "Prefer narrow queries, explain quota-impacting options, and avoid destructive actions."
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
