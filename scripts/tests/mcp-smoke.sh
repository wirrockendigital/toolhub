#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "${ROOT_DIR}/.." && pwd)"

cd "${REPO_DIR}"

if [ ! -d node_modules ]; then
  if ! npm install --silent >/dev/null 2>&1; then
    echo "npm install failed; skipping MCP smoke test" >&2
    exit 0
  fi
fi

npm run mcp:dev -- --list-tools >/tmp/mcp-tools.json

if [ ! -s /tmp/mcp-tools.json ]; then
  echo "Tool discovery did not return any entries" >&2
  exit 1
fi

if command -v jq >/dev/null 2>&1; then
  jq '.[0] | {name, description}' /tmp/mcp-tools.json
else
  cat /tmp/mcp-tools.json
fi
