#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Read image metadata with exiftool.",
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
"""Extract image metadata via exiftool."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Collect metadata as JSON artifact."""
    parser = argparse.ArgumentParser(description="Extract image metadata.")
    parser.add_argument("--input-path", required=True, help="Source image path.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output metadata filename.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input image not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or f"{input_path.stem}.metadata.json"
    output_path = output_dir / output_name

    cmd = ["exiftool", "-json", str(input_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "exiftool_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    output_path.write_text(result.stdout, encoding="utf-8")
    print(json.dumps({"status": "ok", "output_file": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
