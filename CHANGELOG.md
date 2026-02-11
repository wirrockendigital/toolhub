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
