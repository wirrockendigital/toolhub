#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Watch filesystem changes for a limited time window.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "watch_path": { "type": "string" },
#       "timeout_seconds": { "type": "number" },
#       "max_events": { "type": "number" },
#       "recursive": { "type": "boolean" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     }
#   }
# }
#==/MCP==
"""Filesystem watch helper using watchdog."""

import argparse
import json
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class EventCollector(FileSystemEventHandler):
    """Collect filesystem events in memory for bounded monitoring."""

    def __init__(self, max_events: int) -> None:
        super().__init__()
        self.max_events = max_events
        self.events: list[dict] = []

    def on_any_event(self, event):  # noqa: ANN001
        """Store event payload until the configured maximum is reached."""
        if len(self.events) >= self.max_events:
            return
        self.events.append(
            {
                "event_type": event.event_type,
                "is_directory": bool(event.is_directory),
                "src_path": event.src_path,
                "dest_path": getattr(event, "dest_path", None),
                "timestamp": time.time(),
            }
        )


def main() -> int:
    """Watch a path for a fixed duration and write captured events."""
    parser = argparse.ArgumentParser(description="Watch filesystem events.")
    parser.add_argument("--watch-path", default=".", help="Path to monitor.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0, help="Watch duration in seconds.")
    parser.add_argument("--max-events", type=int, default=200, help="Maximum number of events to keep.")
    parser.add_argument("--recursive", action="store_true", help="Watch subdirectories recursively.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output JSON filename.")
    args = parser.parse_args()

    watch_path = Path(args.watch_path)
    if not watch_path.exists():
        print(json.dumps({"status": "error", "error": f"Watch path not found: {watch_path}"}))
        return 1

    collector = EventCollector(max(max(args.max_events, 1), 1))
    observer = Observer()

    # Keep observer lifecycle explicit for predictable cleanup on errors.
    observer.schedule(collector, str(watch_path), recursive=bool(args.recursive))
    observer.start()
    try:
        time.sleep(max(args.timeout_seconds, 0.1))
    finally:
        observer.stop()
        observer.join(timeout=5)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "watch_path_events.json"
    output_path = output_dir / output_name
    output_path.write_text(json.dumps(collector.events, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path), "event_count": len(collector.events)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
