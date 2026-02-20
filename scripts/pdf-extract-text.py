#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Extract text from a PDF file via pdfminer.six.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["input_path"]
#   }
# }
#==/MCP==
"""Extract text from PDF documents."""

import argparse
import json
from pathlib import Path

from pdfminer.high_level import extract_text


def main() -> int:
    """Run PDF text extraction and persist a text artifact."""
    parser = argparse.ArgumentParser(description="Extract text from a PDF file.")
    parser.add_argument("--input-path", required=True, help="Path to the source PDF file.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output text filename.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input PDF not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Keep output naming deterministic for downstream automation.
    output_name = args.output_filename or f"{input_path.stem}.txt"
    output_path = output_dir / output_name

    try:
        text = extract_text(str(input_path))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1

    output_path.write_text(text or "", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "input_path": str(input_path),
                "output_file": str(output_path),
                "text_length": len(text or ""),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
