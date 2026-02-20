#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Extract ZIP archives with unzip.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "output_dir": { "type": "string" }
#     },
#     "required": ["input_path"]
#   }
# }
#==/MCP==
"""ZIP extraction helper."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Extract ZIP archive content into artifact directory."""
    parser = argparse.ArgumentParser(description="Extract zip archives.")
    parser.add_argument("--input-path", required=True, help="Path to source .zip file.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Destination directory.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input zip not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["unzip", "-o", str(input_path), "-d", str(output_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "unzip_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    extracted = [str(path) for path in sorted(output_dir.rglob("*")) if path.is_file()]
    print(json.dumps({"status": "ok", "output_dir": str(output_dir), "extracted_files": extracted}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
