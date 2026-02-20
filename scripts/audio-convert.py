#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Convert audio files with ffmpeg.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input_path": { "type": "string" },
#       "output_format": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" },
#       "audio_codec": { "type": "string" }
#     },
#     "required": ["input_path"]
#   }
# }
#==/MCP==
"""Audio conversion utility based on ffmpeg."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Convert audio input to a selected target format."""
    parser = argparse.ArgumentParser(description="Convert audio files.")
    parser.add_argument("--input-path", required=True, help="Source media file path.")
    parser.add_argument("--output-format", default="mp3", help="Target extension, for example mp3, wav, m4a.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output filename.")
    parser.add_argument("--audio-codec", help="Optional ffmpeg codec value, for example libmp3lame.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(json.dumps({"status": "error", "error": f"Input media not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or f"{input_path.stem}.{args.output_format.lstrip('.')}"
    output_path = output_dir / output_name

    cmd = ["ffmpeg", "-y", "-i", str(input_path)]
    if args.audio_codec:
        cmd.extend(["-c:a", args.audio_codec])
    cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": "ffmpeg_failed", "stderr": result.stderr, "stdout": result.stdout}))
        return 1

    print(json.dumps({"status": "ok", "output_file": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
