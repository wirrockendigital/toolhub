#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Transcribe an audio file via local Whisper CLI.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "input": { "type": "string", "description": "Input audio path (absolute or relative to TRANSCRIPT_INPUT_ROOT)." },
#       "output": { "type": "string", "description": "Optional output path (absolute or relative to TRANSCRIPT_OUTPUT_ROOT)." },
#       "format": { "type": "string", "enum": ["json", "txt"] },
#       "backend": { "type": "string", "enum": ["auto", "whisper-cli"] },
#       "language": { "type": "string", "description": "Optional language code (for example de, en)." },
#       "model": { "type": "string", "description": "Optional backend model name." }
#     },
#     "required": ["input"]
#   }
# }
#==/MCP==
"""Transcribe audio files using local Whisper CLI.

This script is designed for Toolhub automation flows and writes structured logs
under /logs. It accepts an input audio path, chooses an available backend,
and stores the transcript as JSON or TXT.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

LOG_PATH = os.getenv("TRANSCRIPT_LOG_PATH", "/logs/transcript.log")
LOG_LEVEL = os.getenv("TRANSCRIPT_LOG_LEVEL", "INFO").upper()
DEFAULT_INPUT_ROOT = Path(os.getenv("TRANSCRIPT_INPUT_ROOT", "/shared/audio/in"))
DEFAULT_OUTPUT_ROOT = Path(os.getenv("TRANSCRIPT_OUTPUT_ROOT", "/shared/audio/out/transcripts"))

LOGGER = logging.getLogger("transcript")


def configure_logging() -> None:
    """Configure file logging with a safe fallback to stderr."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    LOGGER.setLevel(level)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    if LOGGER.handlers:
        return

    try:
        log_path = Path(LOG_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        LOGGER.addHandler(file_handler)
    except Exception:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(level)
        LOGGER.addHandler(stream_handler)


def resolve_input_path(input_value: str) -> Path:
    """Resolve a user input path against the configured input root."""
    input_candidate = Path(input_value)
    if input_candidate.is_absolute():
        resolved = input_candidate
    else:
        resolved = DEFAULT_INPUT_ROOT / input_candidate

    if not resolved.is_file():
        raise FileNotFoundError(f"Input audio file not found: {resolved}")
    return resolved


def resolve_output_path(input_path: Path, output_value: str | None, output_format: str) -> Path:
    """Resolve output path and ensure its parent directory exists."""
    suffix = ".json" if output_format == "json" else ".txt"

    if output_value:
        output_candidate = Path(output_value)
        if output_candidate.is_absolute():
            output_path = output_candidate
        else:
            output_path = DEFAULT_OUTPUT_ROOT / output_candidate
    else:
        output_path = DEFAULT_OUTPUT_ROOT / f"{input_path.stem}{suffix}"

    if output_path.suffix.lower() != suffix:
        output_path = output_path.with_suffix(suffix)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def run_whisper_cli(input_path: Path, language: str | None, model: str | None) -> dict:
    """Run local Whisper CLI and return parsed JSON output."""
    whisper_cmd = shutil.which("whisper")
    if not whisper_cmd:
        raise RuntimeError("Whisper CLI is not installed or not available in PATH.")

    with tempfile.TemporaryDirectory(prefix="toolhub-transcript-") as tmp_dir:
        args = [
            whisper_cmd,
            str(input_path),
            "--output_dir",
            tmp_dir,
            "--output_format",
            "json",
        ]
        if language:
            args.extend(["--language", language])
        if model:
            args.extend(["--model", model])

        LOGGER.info("Executing Whisper CLI transcription")
        result = subprocess.run(args, capture_output=True, text=True, check=False, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(
                f"Whisper CLI failed with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )

        transcript_file = Path(tmp_dir) / f"{input_path.stem}.json"
        if not transcript_file.is_file():
            raise RuntimeError(f"Whisper CLI did not produce output file: {transcript_file}")

        return json.loads(transcript_file.read_text(encoding="utf-8"))


def extract_text(result: dict) -> str:
    """Extract normalized text from backend results."""
    text = result.get("text")
    if isinstance(text, str):
        return text
    return json.dumps(result, ensure_ascii=False)


def choose_backend(requested_backend: str) -> str:
    """Select transcription backend based on availability and user preference."""
    if requested_backend == "whisper-cli":
        return requested_backend

    if shutil.which("whisper"):
        return "whisper-cli"

    raise RuntimeError("No transcription backend available. Install Whisper CLI.")


def main() -> int:
    """CLI entrypoint for transcription automation."""
    parser = argparse.ArgumentParser(description="Transcribe audio with local Whisper CLI.")
    parser.add_argument("--input", required=True, help="Input audio path (absolute or relative to /shared/audio/in).")
    parser.add_argument("--output", help="Output path (absolute or relative to /shared/audio/out/transcripts).")
    parser.add_argument("--format", choices=["json", "txt"], default="json", help="Output format.")
    parser.add_argument("--backend", choices=["auto", "whisper-cli"], default="auto", help="Transcription backend.")
    parser.add_argument("--language", help="Optional language code (for example de, en).")
    parser.add_argument("--model", help="Optional backend model name.")
    args = parser.parse_args()

    configure_logging()

    try:
        input_path = resolve_input_path(args.input)
        backend = choose_backend(args.backend)
        output_path = resolve_output_path(input_path, args.output, args.format)

        result = run_whisper_cli(input_path, args.language, args.model)

        if args.format == "json":
            output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            output_path.write_text(extract_text(result), encoding="utf-8")

        response = {
            "status": "ok",
            "backend": backend,
            "input": str(input_path),
            "output": str(output_path),
            "format": args.format,
            "text_length": len(extract_text(result)),
        }
        print(json.dumps(response, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Transcription failed: %s", exc)
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
