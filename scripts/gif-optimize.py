#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Optimize GIF files using gifsicle.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" },
#       "optimization_level": { "type": "number" }
#     },
#     "required": ["input_path"]
#   }
# }
#==/MCP==
"""Optimize GIF output size with gifsicle."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Run gifsicle optimization and produce a new GIF artifact."""
    parser = argparse.ArgumentParser(description="Optimize GIF files.")
    parser.add_argument("--input-path", required=True, help="Source GIF path.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional optimized GIF filename.")
    parser.add_argument("--optimization-level", type=int, default=3, help="gifsicle optimization level (1-3).")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input GIF not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or f"{input_path.stem}.optimized.gif"
    output_path = output_dir / output_name

    level = min(max(args.optimization_level, 1), 3)
    cmd = ["gifsicle", f"-O{level}", str(input_path), "-o", str(output_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "gifsicle_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    print(json.dumps({"status": "ok", "output_file": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
