#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Download files with aria2c.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "url": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["url"]
#   }
# }
#==/MCP==
"""Downloader wrapper for aria2."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Download URL with aria2 and return output metadata."""
    parser = argparse.ArgumentParser(description="Download files using aria2c.")
    parser.add_argument("--url", required=True, help="Source URL to download.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Destination directory.")
    parser.add_argument("--output-filename", help="Optional destination filename.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["aria2c", "--allow-overwrite=true", "--dir", str(output_dir)]
    if args.output_filename:
        cmd.extend(["--out", args.output_filename])
    cmd.append(args.url)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "aria2_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    resolved_name = args.output_filename or Path(args.url.split("?")[0]).name or "download.bin"
    output_path = output_dir / resolved_name
    print(json.dumps({"status": "ok", "output_file": str(output_path), "url": args.url}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
