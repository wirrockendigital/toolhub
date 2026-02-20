#!/usr/bin/env python3
#==MCP==
# {
#   "description": "Execute git commands in a target repository.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "repo_path": { "type": "string" },
#       "command": { "type": "string" },
#       "args_json": { "type": "string" },
#       "output_dir": { "type": "string" },
#       "output_filename": { "type": "string" }
#     },
#     "required": ["repo_path", "command"]
#   }
# }
#==/MCP==
"""Git command execution helper."""

import argparse
import json
import subprocess
from pathlib import Path


def main() -> int:
    """Run git command in the requested repository path."""
    parser = argparse.ArgumentParser(description="Execute git operations.")
    parser.add_argument("--repo-path", required=True, help="Repository path for git command execution.")
    parser.add_argument("--command", required=True, help="Git subcommand, for example status or log.")
    parser.add_argument("--args-json", help="Optional JSON array with additional git args.")
    parser.add_argument("--output-dir", default="/shared/artifacts", help="Artifact output directory.")
    parser.add_argument("--output-filename", help="Optional output filename.")
    args = parser.parse_args()

    repo_path = Path(args.repo_path)
    if not repo_path.is_dir():
        print(json.dumps({"status": "error", "error": f"Repository path not found: {repo_path}"}))
        return 1

    extra_args = []
    if args.args_json:
        parsed = json.loads(args.args_json)
        if not isinstance(parsed, list):
            print(json.dumps({"status": "error", "error": "args_json must be a JSON array"}))
            return 1
        extra_args = [str(item) for item in parsed]

    cmd = ["git", "-C", str(repo_path), args.command, *extra_args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_filename or "git_ops_output.txt"
    output_path = output_dir / output_name
    output_path.write_text((result.stdout or "") + (result.stderr or ""), encoding="utf-8")

    if result.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "git_failed",
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "output_file": str(output_path),
                }
            )
        )
        return 1

    print(json.dumps({"status": "ok", "output_file": str(output_path), "command": cmd}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
