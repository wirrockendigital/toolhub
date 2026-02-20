#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Convert HTML content to Markdown.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "html": { "type": "string" },
#       "backend": { "type": "string", "enum": ["markdownify", "html2text"] },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     }
#   }
# }
#==/MCP==
"""HTML to Markdown conversion utility."""

import argparse
import json
from pathlib import Path

import html2text
from markdownify import markdownify as markdownify_html


def main() -> int:
    """Convert HTML input from file or inline payload to Markdown text."""
    parser = argparse.ArgumentParser(description="Convert HTML to Markdown.")
    parser.add_argument("--input-path", help="Path to an HTML file.")
    parser.add_argument("--html", help="Inline HTML content.")
    parser.add_argument("--backend", default="markdownify", choices=["markdownify", "html2text"])
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output Markdown filename.")
    args = parser.parse_args()

    # Keep input precedence explicit for predictable automation behavior.
    html_value = args.html
    if not html_value and args.input_path:
        source_path = Path(args.input_path)
        if not source_path.is_file():
            print(json.dumps({"status": "error", "error": f"Input HTML file not found: {source_path}"}))
            return 1
        html_value = source_path.read_text(encoding="utf-8")

    if not html_value:
        print(json.dumps({"status": "error", "error": "Either --html or --input-path is required."}))
        return 1

    if args.backend == "html2text":
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        markdown_value = converter.handle(html_value)
    else:
        markdown_value = markdownify_html(html_value)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "html_to_markdown.md"
    output_path = output_dir / output_name
    output_path.write_text(markdown_value, encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path), "backend": args.backend}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
