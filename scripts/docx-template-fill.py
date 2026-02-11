#!/usr/bin/env python3
"""CLI wrapper for mcp_tools.docx_template_fill.fill_docx_template."""
#==MCP==
# {
#   "description": "Fill a DOCX template with placeholder values and write the output file.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "template": { "type": "string", "description": "Template filename (for example invoice.docx)." },
#       "output_filename": { "type": "string", "description": "Output DOCX filename without path separators." },
#       "output_subdir": { "type": "string", "description": "Optional relative output subdirectory." },
#       "data": {
#         "type": "object",
#         "description": "Key/value placeholders for template rendering.",
#         "additionalProperties": { "type": "string" }
#       },
#       "payload": { "type": "string", "description": "Raw JSON payload as alternative input." },
#       "payload_file": { "type": "string", "description": "Path to a JSON payload file as alternative input." }
#     }
#   }
# }
#==/MCP==

import argparse
import json
import os
import sys

# Ensure project modules can be imported in container and local-dev modes.
TOOLS_ROOT = os.getenv("TOOLHUB_PYTHON_ROOT", "/opt/toolhub")
if not os.path.isdir(TOOLS_ROOT) and os.path.isdir("/workspace"):
    TOOLS_ROOT = "/workspace"
if not os.path.isdir(TOOLS_ROOT):
    TOOLS_ROOT = os.getcwd()
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

from mcp_tools.docx_template_fill.tool import fill_docx_template


def load_payload(args: argparse.Namespace) -> dict:
    """Load payload from inline/file JSON or from explicit CLI fields."""
    # Prefer explicit payload arguments when callers already provide full JSON.
    if args.payload:
        return json.loads(args.payload)
    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as fh:
            return json.load(fh)

    if not args.template:
        raise ValueError("Either --payload/--payload-file or --template is required.")
    if not args.output_filename:
        raise ValueError("--output-filename is required when using explicit CLI fields.")

    # Accept placeholder data from inline JSON or a JSON file path.
    data_value = {}
    if args.data:
        data_value = json.loads(args.data)
    elif args.data_file:
        with open(args.data_file, "r", encoding="utf-8") as fh:
            data_value = json.load(fh)

    return {
        "template": args.template,
        "output_filename": args.output_filename,
        "output_subdir": args.output_subdir,
        "data": data_value,
    }


def main() -> int:
    """Run docx template fill and emit structured JSON."""
    parser = argparse.ArgumentParser(description="Render DOCX template via mcp_tools.docx_template_fill.")
    parser.add_argument("--payload", help="Inline JSON payload.")
    parser.add_argument("--payload-file", help="Path to JSON payload file.")
    parser.add_argument("--template", help="Template filename.")
    parser.add_argument("--output-filename", help="Output DOCX filename.")
    parser.add_argument("--output-subdir", help="Optional relative output subdirectory.")
    parser.add_argument("--data", help="Inline JSON object with placeholder values.")
    parser.add_argument("--data-file", help="Path to JSON file with placeholder values.")
    args = parser.parse_args()

    try:
        payload = load_payload(args)
        result = fill_docx_template(payload)
        print(json.dumps({"status": "ok", **result}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
