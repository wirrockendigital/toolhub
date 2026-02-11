# docx-template-fill MCP Tool

Fills DOCX templates using `docxtpl`, writes outputs under `/output`, and reports the generated file path via MCP.

## Inputs
- `template` (string, required): DOCX filename in `/templates`.
- `data` (object, required): Flat mapping of placeholders to values.
- `output_subdir` (string, optional): Relative subdirectory under `/output` using letters, digits, `_`, `-`, `/`.
- `output_filename` (string, required): Filename ending with `.docx`, no slashes.

## Output
```json
{"output_file": "/output/<subdir>/name.docx"}
```

## Security & Validation
- Rejects absolute paths, `..`, backslashes, and invalid characters.
- Template and output must end with `.docx`.
- Output directories are created automatically; overwrites are blocked.

## Environment
- `DOCX_TEMPLATE_ROOT` (default `/templates`)
- `DOCX_OUTPUT_ROOT` (default `/output`)
- `DOCX_TEMPLATE_FILL_LOG_PATH` (default `/logs/docx-template-fill.log`)
- `DOCX_TEMPLATE_FILL_LOG_LEVEL` (default `INFO`)
