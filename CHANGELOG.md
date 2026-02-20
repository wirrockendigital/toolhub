## [0.2.8] – 2026-02-20
### Fixed
- MCP schema conversion now supports JSON-schema `pattern` fields in `JsonSchema` and compiles regex constraints into zod validation.
- TypeScript MCP build error resolved by extending the internal schema type to include `pattern`.

### Changed
- Project version metadata bumped to `0.2.8` across VERSION/package/pyproject/MCP defaults.

## [0.2.7] – 2026-02-20
### Fixed
- MCP build dependency updated from unavailable `@modelcontextprotocol/sdk@^0.2.0` to available `@modelcontextprotocol/sdk@^0.7.0` for GitHub CI compatibility.

### Changed
- Project version metadata bumped to `0.2.7` across VERSION/package/pyproject/MCP defaults.

## [0.2.6] – 2026-02-20
### Fixed
- Toolhub CI Node setup no longer requires a root npm lockfile by removing npm cache binding from `actions/setup-node`.
- DOCX template-fill unit test now expects `TemplateValidationError` for missing templates, matching runtime behavior.

### Changed
- Project version metadata bumped to `0.2.6` across VERSION/package/pyproject/MCP defaults.

## [0.2.5] – 2026-02-20
### Added
- New webhook endpoints `GET /tools`, `POST /run-file`, and `GET /artifacts/<job_id>/<filename>` for unified tool discovery and file-first execution.
- Manifest-based Toolhub tool catalog for Wave 1-3 capabilities under `tools/*/tool.json` with `io_mode`, `n8n_alias`, and artifact metadata.
- New script tools for document/pdf/ocr, media/image/data, and utility/network/git workflows (`scripts/*.py`) including MCP metadata blocks.
- New n8n community nodes (one node per tool) for the newly exposed Toolhub features.
- New unit test `tests/tool_scripts/test_array_stats.py` and CI execution wiring.

### Changed
- Webhook tool dispatch refactored to shared dispatch path for Python tools, manifest tools, and script tools.
- MCP CLI whitelist extended with `yq`, `wget`, `aria2c`, `gifsicle`, `tree`, `unzip`, `bc`, `git`, and `wakeonlan`.
- Docker image now installs `pandoc` to support `pypandoc`-based conversions.
- Multi-arch release configuration updated for `linux/amd64,linux/arm64` (Synology-compatible).
- Project version metadata bumped to `0.2.5` across VERSION/package/pyproject/MCP defaults.

## [0.1.3] – 2025-12-06
### Added
- MCP tool `docx-template-fill.fill_docx_template` for rendering DOCX templates via docxtpl with safe output controls.
- Python package `mcp_tools.docx_template_fill` with validation, rendering, CLI entrypoint, and unit tests.

### Changed
- MCP server version metadata bumped to 0.1.3.

## [0.1.2] – 2025-12-05
### Added
- Debug-level logging for DOCX rendering to trace placeholder replacements across paragraphs and table cells.

### Changed
- DOCX renderer now records replacement counts for easier troubleshooting.

## [0.1.1] – 2025-12-05
### Added
- DOCX rendering tool to fill templates from placeholder data and save outputs to configurable directories.
- `/run` webhook endpoint to dispatch registered Python tools (initially `docx-render`).
- Version tracking via `VERSION` file.

### Changed
- Updated MCP default version metadata to match the new release.
