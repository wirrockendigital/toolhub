#!/usr/bin/env python3
#==MCP==
# {
#   "description": "List directory trees using the tree command.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "root_path": { "type": "string" },
#       "max_depth": { "type": "number" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     }
#   }
# }
#==/MCP==
"""Directory tree listing helper."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Render directory tree output to a text artifact."""
    parser = argparse.ArgumentParser(description="Render tree listing.")
    parser.add_argument("--root-path", default=".", help="Root directory for tree listing.")
    parser.add_argument("--max-depth", type=int, default=4, help="Maximum tree depth.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output text filename.")
    args = parser.parse_args()

    root_path = Path(args.root_path)
    if not root_path.exists():
        print(json.dumps({"status": "error", "error": f"Root path not found: {root_path}"}))
        return 1

    cmd = ["tree", "-a", "-L", str(max(args.max_depth, 1)), str(root_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "tree_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "tree_list.txt"
    output_path = output_dir / output_name
    output_path.write_text(result.stdout, encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path), "root_path": str(root_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
