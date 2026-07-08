# Changelog

All notable changes to SurveyHub-MCP will be documented in this file.

## [1.15.0] - 2026-07-08

### Added

- Added MCP reference resources for platform syntax and API documentation.
- Added aggregate-server prompts for search planning and query help.

### Changed

- Raised the MCP Python SDK minimum version to `>=1.28.0`.
- Switched tool results to structured MCP output with consistent `ok`, `platform`, `data`, `text`, and `error` fields.
- Aligned MCP handshake server version with the package version.
- Included documentation resources in the built wheel.

## [1.14.0] - 2026-07-06

### Changed

- Hunter personal and enterprise queries now default to exact string comparisons by converting `field="value"` to `field=="value"`.
- Added `exact_search=false` opt-out for Hunter search and query-based batch tasks to preserve native fuzzy matching when needed.

### Removed

- Removed the tracked unit test file from the production package repository.

## [1.13.0] - 2026-06-26

### Changed

- Tuned Quake's process-local rate limit from 1 second to 5 seconds per request.

## [1.12.0] - 2026-06-26

### Added

- Added process-local circuit breaker protection for all platform HTTP requests.
- Added unit tests for circuit breaker state transitions and retry delay caps.

### Changed

- Tuned default HTTP timeout and retry delays for interactive MCP clients.
- Capped `Retry-After` wait time to avoid long IDE/tool-call stalls.

## [1.11.0] - 2026-06-25

### Removed

- Removed Shodan platform support (`shodan.py`, `shodan-mcp` entry point, `docs/api/shodan_api.md`).
- Removed Censys platform support (`censys.py`, `censys-mcp` entry point, `docs/api/censys_api.md`).
- Removed SecurityTrails platform support (`securitytrails.py`, `securitytrails-mcp` entry point, `docs/api/securitytrails_api.md`).
- Removed BinaryEdge platform support (`binaryedge.py`, `binaryedge-mcp` entry point, `docs/api/binaryedge_api.md`).
- Removed Netlas platform support (`netlas.py`, `netlas-mcp` entry point, `docs/api/netlas_api.md`).
- Removed Onyphe platform support (`onyphe.py`, `onyphe-mcp` entry point, `docs/api/onyphe_api.md`).
- Removed LeakIX platform support (`leakix.py`, `leakix-mcp` entry point, `docs/api/leakix_api.md`).
- Removed FullHunt platform support (`fullhunt.py`, `fullhunt-mcp` entry point, `docs/api/fullhunt_api.md`).
- Removed Criminal IP platform support (`criminalip.py`, `criminalip-mcp` entry point, `docs/api/criminalip_api.md`).
- Removed all non-CN region prefixes (US_, PT_, CY_, FR_, AE_, KR_) from `PLATFORM_PREFIX`, `.env.example`, `mcp.json.example`, and README — project now focuses exclusively on Chinese cyberspace mapping platforms.

### Added

- Added `AsyncRateLimiter` (1 req/s) to Quake tools to prevent HTTP 429 rate-limit errors.
- Added `AsyncRateLimiter` (1 req/s) to Hunter Personal tools to prevent HTTP 429 rate-limit errors.
- Added `AsyncRateLimiter` (1 req/s) to Hunter Enterprise tools to prevent HTTP 429 rate-limit errors.

### Changed

- README simplified to reflect Chinese-platform-only focus.
- `pyproject.toml` shortened description and keywords, removed 9 single-platform entry points.
- Centralized rate limiting in the shared HTTP helpers so 429 retries are throttled along with initial requests.
- Improved 429 `Retry-After` handling to support both seconds and HTTP-date values.

## [1.10.0] - 2026-06-17

### Added

- Added Criminal IP platform support with 4 tools: `criminalip_ip`, `criminalip_search`, `criminalip_domain`, `criminalip_account`.

### Changed

- Merged per-platform tool tables in README into a single unified 61-tool overview table with platform column.

### Removed

- Removed `securitytrails_ip` (IP WHOIS) and `securitytrails_dns_history` (DNS history) — IP attribution and historical DNS records are intelligence-class data, not asset discovery.
- Removed `netlas_whois_ip` (IP WHOIS) — IP attribution is intelligence-class data, not asset discovery.

## [1.9.0] - 2026-06-17

### Added

- Added FullHunt platform support with 4 tools: `fullhunt_domain`, `fullhunt_subdomains`, `fullhunt_host`, `fullhunt_account`.

## [1.8.0] - 2026-06-17

### Added

- Added LeakIX platform support with 4 tools: `leakix_search`, `leakix_host`, `leakix_subdomains`, `leakix_plugins`.

## [1.7.0] - 2026-06-17

### Added

- Added Onyphe platform support with 4 tools: `onyphe_search`, `onyphe_summary_ip`, `onyphe_summary_domain`, `onyphe_account`.

## [1.6.0] - 2026-06-17

### Added

- Added Netlas platform support with 3 tools: `netlas_search`, `netlas_domain`, `netlas_account`.

## [1.5.0] - 2026-06-17

### Added

- Added BinaryEdge platform support with 3 tools: `binaryedge_search`, `binaryedge_subdomains`, `binaryedge_account`.

### Changed

- Renamed environment variable prefix for BinaryEdge from `ES_` to `PT_`.

## [1.4.0] - 2026-06-17

### Added

- Added SecurityTrails platform support with 2 tools: `securitytrails_domain`, `securitytrails_subdomains`.

## [1.3.0] - 2026-06-17

### Added

- Added Censys platform support with 4 tools: `censys_search`, `censys_aggregate`, `censys_view_host`, `censys_account`.
- Censys authentication uses HTTP Basic Auth with API ID + API Secret.
- Added `censys-mcp` single-platform entry point.
- Added Censys API documentation at `docs/api/censys_api.md`.
- Added `US_CENSYS_API_ID` and `US_CENSYS_API_SECRET` environment variables.

## [1.2.0] - 2026-06-17

### Added

- Added Shodan platform support with 7 tools: `shodan_search`, `shodan_search_count`, `shodan_host`, `shodan_api_info`, `shodan_domain`, `shodan_dns_resolve`, `shodan_dns_reverse`.
- Added `shodan-mcp` single-platform entry point.
- Added Shodan API documentation at `docs/api/shodan_api.md`.
- Added `US_SHODAN_API_KEY` environment variable (with `SHODAN_API_KEY` fallback).

### Changed

- Refactored environment variable naming to region-based prefix convention (`CN_` / `US_` / `PT_` / `CY_` / `FR_` / `AE_` / `KR_`).
- Added `platform_key()` and `platform_env()` helpers to `common.py` that try the prefixed env var first and fall back to the unprefixed name, ensuring backward compatibility.
- All platform modules now use the new helpers instead of direct `os.getenv()` / `first_env()` calls.
- Updated `.env.example`, `mcp.json.example`, and README to document the prefix convention and reserved international platform slots.

## [1.1.0] - 2026-06-17

### Added

- Added DayDayMap platform support with asset search via `/api/v1/raymap/search/all`.
- Added `daydaymap_search` tool with Base64 keyword encoding and application-level error code handling.
- Added `daydaymap-mcp` single-platform entry point.
- Added DayDayMap API documentation at `docs/api/daydaymap_api.md`.
- Added `DAYDAYMAP_API_KEY` environment variable.

## [1.0.2] - 2026-06-17

### Fixed

- Add `AsyncRateLimiter` (0.6s) to `fofa_search` and `fofa_search_next` to comply with FOFA's recommended 2 requests/second rate limit.
- Add HTTP 429 automatic retry with exponential backoff (max 3 retries) to `request_json` and `request_download` to handle rate-limit errors gracefully.

## [1.0.1] - 2026-05-14

### Changed

- Lowered the published Python requirement from `>=3.12` to `>=3.10`, matching the current source syntax and dependency requirements.
- Improved missing-credential examples to use the PyPI `uvx surveyhub-mcp` workflow.

### Fixed

- Handle successful non-JSON API responses without reporting them as query errors.
- Return JSON responses from download endpoints instead of writing API status payloads to CSV output files.
- Reject ambiguous Hunter batch task requests that provide both `query` and `file_path`.

## [1.0] - 2026-05-14

### Changed

- Renamed the distribution, package, aggregate server, command, and documentation from the previous project identity to SurveyHub-MCP.
- Updated project metadata and repository links for `https://github.com/helGayhub233/SurveyHub-MCP`.
- Aligned the Python package directory with the published import name `surveyhub_mcp`.
- Moved source code into the `src/surveyhub_mcp` layout for cleaner PyPI packaging.

### Added

- Added this release iteration record for pre-release tracking.
