#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Transform YAML data via yq expressions.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "expression": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["input_path"]
#   }
# }
#==/MCP==
"""YAML transform helper using yq."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Apply yq expression and emit YAML output artifact."""
    parser = argparse.ArgumentParser(description="Transform YAML with yq.")
    parser.add_argument("--input-path", required=True, help="Path to input YAML file.")
    parser.add_argument("--expression", default=".", help="yq expression.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output YAML filename.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input YAML not found: {input_path}"}))
        return 1

    result = subprocess.run(["yq", args.expression, str(input_path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "yq_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or f"{input_path.stem}.transformed.yaml"
    output_path = output_dir / output_name
    output_path.write_text(result.stdout, encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path), "expression": args.expression}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
