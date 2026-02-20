#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Transform JSON data via jq filter expressions.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "json_input": { "type": "string" },
#       "filter": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     }
#   }
# }
#==/MCP==
"""JSON transform helper using jq."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Apply jq filter and persist transformed JSON output."""
    parser = argparse.ArgumentParser(description="Transform JSON with jq.")
    parser.add_argument("--input-path", help="Path to input JSON file.")
    parser.add_argument("--json-input", help="Inline JSON payload.")
    parser.add_argument("--filter", default=".", help="jq filter expression.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output JSON filename.")
    args = parser.parse_args()

    json_source = args.json_input
    if not json_source and args.input_path:
        source_path = Path(args.input_path)
        if not source_path.is_file():
            print(json.dumps({"status": "error", "error": f"Input JSON not found: {source_path}"}))
            return 1
        json_source = source_path.read_text(encoding="utf-8")

    if not json_source:
        print(json.dumps({"status": "error", "error": "Either --json-input or --input-path is required."}))
        return 1

    # Validate source JSON before passing data to jq for clearer errors.
    try:
        json.loads(json_source)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": f"Invalid JSON input: {exc}"}))
        return 1

    result = subprocess.run(["jq", args.filter], input=json_source, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "jq_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "json_transform.json"
    output_path = output_dir / output_name
    output_path.write_text(result.stdout, encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path), "filter": args.filter}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
