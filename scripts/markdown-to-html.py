#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Convert Markdown content to HTML.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "markdown_text": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     }
#   }
# }
#==/MCP==
"""Markdown to HTML conversion utility."""

import argparse
import json
from pathlib import Path

import markdown


def main() -> int:
    """Convert Markdown input from file or inline text to HTML output."""
    parser = argparse.ArgumentParser(description="Convert Markdown to HTML.")
    parser.add_argument("--input-path", help="Path to a Markdown file.")
    parser.add_argument("--markdown-text", help="Inline Markdown content.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output HTML filename.")
    args = parser.parse_args()

    markdown_value = args.markdown_text
    if not markdown_value and args.input_path:
        source_path = Path(args.input_path)
        if not source_path.is_file():
            print(json.dumps({"status": "error", "error": f"Input Markdown file not found: {source_path}"}))
            return 1
        markdown_value = source_path.read_text(encoding="utf-8")

    if not markdown_value:
        print(json.dumps({"status": "error", "error": "Either --markdown-text or --input-path is required."}))
        return 1

    # Keep rendering basic and deterministic for machine-driven workflows.
    html_value = markdown.markdown(markdown_value, extensions=["tables", "fenced_code"])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "markdown_to_html.html"
    output_path = output_dir / output_name
    output_path.write_text(html_value, encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
