#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Perform HTTP requests with requests/httpx and save response body.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "url": { "type": "string" },
#       "method": { "type": "string" },
#       "backend": { "type": "string", "enum": ["requests", "httpx"] },
#       "headers_json": { "type": "string" },
#       "body_json": { "type": "string" },
#       "body_text": { "type": "string" },
#       "timeout_seconds": { "type": "number" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["url"]
#   }
# }
#==/MCP==
"""HTTP fetch helper with two Python client backends."""

import argparse
import json
from pathlib import Path

import httpx
import requests


def _load_json_map(raw_value):
    """Decode optional JSON objects for headers and body values."""
    if not raw_value:
        return None
    parsed = json.loads(raw_value)
    if not isinstance(parsed, dict):
        raise ValueError("JSON value must be an object")
    return parsed


def _call_requests(method, url, headers, body_json, body_text, timeout_seconds):
    """Execute HTTP request through requests backend."""
    return requests.request(method=method, url=url, headers=headers, json=body_json, data=body_text, timeout=timeout_seconds)


def _call_httpx(method, url, headers, body_json, body_text, timeout_seconds):
    """Execute HTTP request through httpx backend."""
    with httpx.Client(timeout=timeout_seconds) as client:
        return client.request(method=method, url=url, headers=headers, json=body_json, content=body_text)


def main() -> int:
    """Fetch HTTP response and persist body artifact."""
    parser = argparse.ArgumentParser(description="Fetch HTTP resources.")
    parser.add_argument("--url", required=True, help="Target URL.")
    parser.add_argument("--method", default="GET", help="HTTP method.")
    parser.add_argument("--backend", default="requests", choices=["requests", "httpx"])
    parser.add_argument("--headers-json", help="Optional JSON object for request headers.")
    parser.add_argument("--body-json", help="Optional JSON object request body.")
    parser.add_argument("--body-text", help="Optional raw request body string.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output file name.")
    args = parser.parse_args()

    try:
        headers = _load_json_map(args.headers_json) or {}
        body_json = _load_json_map(args.body_json)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": f"Invalid JSON argument: {exc}"}))
        return 1

    method = args.method.upper().strip() or "GET"
    try:
        if args.backend == "httpx":
            response = _call_httpx(method, args.url, headers, body_json, args.body_text, args.timeout_seconds)
        else:
            response = _call_requests(method, args.url, headers, body_json, args.body_text, args.timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "http_fetch_body.bin"
    output_path = output_dir / output_name
    output_path.write_bytes(response.content)

    print(
        json.dumps(
            {
                "status": "ok",
                "backend": args.backend,
                "status_code": int(response.status_code),
                "output_file": str(output_path),
                "content_type": response.headers.get("content-type", ""),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
