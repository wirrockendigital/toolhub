#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Read PDF metadata using pdfinfo.",
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
"""Extract PDF metadata via poppler-utils."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Run pdfinfo and write plain-text metadata output."""
    parser = argparse.ArgumentParser(description="Read PDF metadata via pdfinfo.")
    parser.add_argument("--input-path", required=True, help="Path to the source PDF file.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output metadata filename.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input PDF not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or f"{input_path.stem}.pdfinfo.txt"
    output_path = output_dir / output_name

    # Keep CLI execution explicit so errors are visible to callers.
    result = subprocess.run(["pdfinfo", str(input_path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "pdfinfo_failed",
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        )
        return 1

    output_path.write_text(result.stdout, encoding="utf-8")
    print(json.dumps({"status": "ok", "input_path": str(input_path), "output_file": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
