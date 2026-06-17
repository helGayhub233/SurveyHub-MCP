# Changelog

All notable changes to SurveyHub-MCP will be documented in this file.

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
