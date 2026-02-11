#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Rotate oversized logs and delete stale temp artifacts with safe prefix filtering.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "logs_dir": { "type": "string", "description": "Directory containing log files." },
#       "tmp_dir": { "type": "string", "description": "Temporary directory to clean." },
#       "max_log_size_mb": { "type": "number", "description": "Rotate logs larger than this threshold." },
#       "max_log_backups": { "type": "number", "description": "How many rotated backups to keep." },
#       "tmp_max_age_hours": { "type": "number", "description": "Delete temp entries older than this age." },
#       "tmp_prefixes": { "type": "string", "description": "Comma-separated allowed prefixes for temp cleanup." },
#       "dry_run": { "type": "boolean", "description": "Preview actions without writing changes." }
#     }
#   }
# }
#==/MCP==
"""Rotate log files and clean temporary artifacts for Toolhub.

This script provides a safe cleanup routine for log growth and stale temp files.
It is suitable for cron, SSH execution, webhook /run dispatch, and MCP invocation.
"""

import argparse
import json
import logging
import os
import shutil
import time
from pathlib import Path

LOG_PATH = os.getenv("CLEANUP_LOG_PATH", "/logs/cleanup.log")
LOG_LEVEL = os.getenv("CLEANUP_LOG_LEVEL", "INFO").upper()

LOGGER = logging.getLogger("cleanup")


def configure_logging() -> None:
    """Configure cleanup logging to file with fallback stderr handler."""
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


def rotate_log(log_file: Path, max_backups: int, dry_run: bool) -> bool:
    """Rotate one log file and return whether a rotation happened."""
    rotated = False
    for index in range(max_backups, 0, -1):
        source = log_file.with_suffix(f"{log_file.suffix}.{index}")
        target = log_file.with_suffix(f"{log_file.suffix}.{index + 1}")
        if source.exists():
            if index == max_backups:
                if dry_run:
                    LOGGER.info("Would remove backup log: %s", source)
                else:
                    source.unlink(missing_ok=True)
            else:
                if dry_run:
                    LOGGER.info("Would rename backup log: %s -> %s", source, target)
                else:
                    source.rename(target)

    first_backup = log_file.with_suffix(f"{log_file.suffix}.1")
    if dry_run:
        LOGGER.info("Would rotate log: %s -> %s", log_file, first_backup)
    else:
        log_file.rename(first_backup)
        log_file.touch()
    rotated = True
    return rotated


def cleanup_temp_entries(tmp_dir: Path, max_age_seconds: int, allowed_prefixes: list[str], dry_run: bool) -> int:
    """Remove old temp entries with safe prefix filtering."""
    removed = 0
    now = time.time()

    if not tmp_dir.is_dir():
        return removed

    for entry in tmp_dir.iterdir():
        if not any(entry.name.startswith(prefix) for prefix in allowed_prefixes):
            continue

        try:
            age = now - entry.stat().st_mtime
        except FileNotFoundError:
            continue

        if age < max_age_seconds:
            continue

        if dry_run:
            LOGGER.info("Would remove stale temp entry: %s", entry)
            removed += 1
            continue

        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)
        removed += 1

    return removed


def main() -> int:
    """CLI entrypoint for cleanup routines."""
    parser = argparse.ArgumentParser(description="Rotate logs and cleanup stale temporary artifacts.")
    parser.add_argument("--logs-dir", default="/logs", help="Directory containing log files.")
    parser.add_argument("--tmp-dir", default="/tmp", help="Temporary directory to clean.")
    parser.add_argument("--max-log-size-mb", type=int, default=50, help="Rotate logs larger than this threshold.")
    parser.add_argument("--max-log-backups", type=int, default=5, help="How many rotated backups to keep.")
    parser.add_argument("--tmp-max-age-hours", type=int, default=24, help="Max age for temp entries before deletion.")
    parser.add_argument(
        "--tmp-prefixes",
        default="audio-split-,docx-template-fill-,toolhub-transcript-",
        help="Comma-separated temp entry prefixes allowed for deletion.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing changes.")
    args = parser.parse_args()

    configure_logging()

    logs_dir = Path(args.logs_dir)
    tmp_dir = Path(args.tmp_dir)
    max_log_size_bytes = max(args.max_log_size_mb, 1) * 1024 * 1024
    max_age_seconds = max(args.tmp_max_age_hours, 1) * 3600
    allowed_prefixes = [prefix.strip() for prefix in args.tmp_prefixes.split(",") if prefix.strip()]

    rotated_logs = 0
    removed_temp_entries = 0

    try:
        if logs_dir.is_dir():
            for log_file in sorted(logs_dir.glob("*.log")):
                try:
                    if log_file.stat().st_size <= max_log_size_bytes:
                        continue
                except FileNotFoundError:
                    continue

                if rotate_log(log_file, args.max_log_backups, args.dry_run):
                    rotated_logs += 1

        removed_temp_entries = cleanup_temp_entries(tmp_dir, max_age_seconds, allowed_prefixes, args.dry_run)

        response = {
            "status": "ok",
            "dry_run": args.dry_run,
            "rotated_logs": rotated_logs,
            "removed_temp_entries": removed_temp_entries,
            "logs_dir": str(logs_dir),
            "tmp_dir": str(tmp_dir),
        }
        print(json.dumps(response, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Cleanup failed: %s", exc)
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
