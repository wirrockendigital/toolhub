#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Execute HTTP requests with curl.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "url": { "type": "string" },
#       "method": { "type": "string" },
#       "headers_json": { "type": "string" },
#       "body_text": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["url"]
#   }
# }
#==/MCP==
"""Curl request wrapper with file output."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Execute curl and store response body as artifact."""
    parser = argparse.ArgumentParser(description="Run HTTP request using curl.")
    parser.add_argument("--url", required=True, help="Target URL.")
    parser.add_argument("--method", default="GET", help="HTTP method.")
    parser.add_argument("--headers-json", help="Optional JSON object of headers.")
    parser.add_argument("--body-text", help="Optional request body.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Destination directory.")
    parser.add_argument("--output-filename", help="Optional output filename.")
    args = parser.parse_args()

    headers = {}
    if args.headers_json:
        parsed = json.loads(args.headers_json)
        if not isinstance(parsed, dict):
            print(json.dumps({"status": "error", "error": "headers_json must be an object"}))
            return 1
        headers = parsed

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "curl_response.bin"
    output_path = output_dir / output_name

    cmd = ["curl", "-sS", "-L", "-X", args.method.upper(), args.url, "-o", str(output_path)]
    # Keep header injection explicit so callers can audit final command behavior.
    for key, value in headers.items():
        cmd.extend(["-H", f"{key}: {value}"])
    if args.body_text is not None:
        cmd.extend(["--data", args.body_text])

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "curl_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    print(json.dumps({"status": "ok", "output_file": str(output_path), "url": args.url}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
