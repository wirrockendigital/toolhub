#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Calculate descriptive statistics from numeric arrays.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "numbers_json": { "type": "string" },
#       "input_path": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     }
#   }
# }
#==/MCP==
"""Array statistics helper backed by numpy."""

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> int:
    """Read numeric values and write summary statistics."""
    parser = argparse.ArgumentParser(description="Calculate array statistics.")
    parser.add_argument("--numbers-json", help="Inline JSON array of numbers.")
    parser.add_argument("--input-path", help="Path to a JSON file containing an array.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output JSON filename.")
    args = parser.parse_args()

    raw = args.numbers_json
    if not raw and args.input_path:
        source_path = Path(args.input_path)
        if not source_path.is_file():
            print(json.dumps({"status": "error", "error": f"Input JSON not found: {source_path}"}))
            return 1
        raw = source_path.read_text(encoding="utf-8")

    if not raw:
        print(json.dumps({"status": "error", "error": "Either --numbers-json or --input-path is required."}))
        return 1

    try:
        values = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": f"Invalid JSON input: {exc}"}))
        return 1

    if not isinstance(values, list) or not values:
        print(json.dumps({"status": "error", "error": "Input array must contain at least one number."}))
        return 1

    # Convert values to numpy array for stable numeric calculations.
    try:
        arr = np.array(values, dtype=float)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "error", "error": f"Non-numeric values in input: {exc}"}))
        return 1

    stats = {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "sum": float(np.sum(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "array_stats.json"
    output_path = output_dir / output_name
    output_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"status": "ok", "output_file": str(output_path), "stats": stats}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
