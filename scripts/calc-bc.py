#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Evaluate mathematical expressions via bc.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "expression": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["expression"]
#   }
# }
#==/MCP==
"""Calculator helper backed by bc."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Evaluate expression and save result to an artifact file."""
    parser = argparse.ArgumentParser(description="Evaluate expressions with bc.")
    parser.add_argument("--expression", required=True, help="Expression passed to bc -l.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output filename.")
    args = parser.parse_args()

    result = subprocess.run(["bc", "-l"], input=args.expression, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "bc_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "calc_result.txt"
    output_path = output_dir / output_name
    output_path.write_text(result.stdout.strip() + "\n", encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path), "result": result.stdout.strip()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
