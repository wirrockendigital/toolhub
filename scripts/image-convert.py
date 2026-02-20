#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Convert image formats via ImageMagick.",
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
"""Convert images with ImageMagick."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Convert source image to a target format."""
    parser = argparse.ArgumentParser(description="Convert image format.")
    parser.add_argument("--input-path", required=True, help="Source image path.")
    parser.add_argument("--output-format", default="png", help="Target image extension without dot.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output image filename.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input image not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or f"{input_path.stem}.{args.output_format.lstrip('.')}"
    output_path = output_dir / output_name

    # Prefer the modern "magick" entrypoint and keep stderr for debugging.
    cmd = ["magick", str(input_path), str(output_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "magick_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    print(json.dumps({"status": "ok", "output_file": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
