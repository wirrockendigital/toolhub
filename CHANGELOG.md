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
