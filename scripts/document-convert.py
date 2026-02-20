#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Convert documents with pypandoc.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "output_format": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["input_path"]
#   }
# }
#==/MCP==
"""Document conversion wrapper around pandoc."""

import argparse
import json
from pathlib import Path

import pypandoc


def main() -> int:
    """Convert an input document to another format using pandoc."""
    parser = argparse.ArgumentParser(description="Convert documents via pypandoc.")
    parser.add_argument("--input-path", required=True, help="Source document path.")
    parser.add_argument("--output-format", default="html", help="Target format, for example html, markdown, docx.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output filename.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input document not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Derive extension from output format when no filename is provided.
    suffix = args.output_format.replace("+", "_").replace("/", "_")
    output_name = args.output_filename or f"{input_path.stem}.{suffix}"
    output_path = output_dir / output_name

    try:
        pypandoc.convert_file(str(input_path), args.output_format, outputfile=str(output_path))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "input_path": str(input_path),
                "output_file": str(output_path),
                "output_format": args.output_format,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
