#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Run OCR on an image file with tesseract.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" },
#       "lang": { "type": "string" }
#     },
#     "required": ["input_path"]
#   }
# }
#==/MCP==
"""OCR wrapper around tesseract."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Execute OCR and store extracted text."""
    parser = argparse.ArgumentParser(description="Extract text from image using tesseract.")
    parser.add_argument("--input-path", required=True, help="Path to image file.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output .txt filename.")
    parser.add_argument("--lang", help="Optional tesseract language code, for example de or eng.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input image not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or f"{input_path.stem}.ocr.txt"
    output_path = output_dir / output_name

    # Use tesseract stdout mode to avoid temporary intermediate files.
    cmd = ["tesseract", str(input_path), "stdout"]
    if args.lang:
        cmd.extend(["-l", args.lang])

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "tesseract_failed",
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        )
        return 1

    output_path.write_text(result.stdout or "", encoding="utf-8")
    print(json.dumps({"status": "ok", "input_path": str(input_path), "output_file": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
