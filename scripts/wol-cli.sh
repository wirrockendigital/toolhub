#!/usr/bin/env bash
#==MCP==
# {
#   "description": "Send a Wake-on-LAN magic packet to a target MAC address or named device.",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "args": {
#         "type": "array",
#         "items": { "type": "string" },
#         "description": "Positional arguments forwarded to wol-cli.sh (for example ['livingroom-tv'])."
#       }
#     }
#   }
# }
#==/MCP==
set -euo pipefail

# Delegate to the canonical wol-cli implementation in the repository tools folder.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Resolve the real wol-cli path across image-only, mounted workspace, and local-dev layouts.
CANDIDATES=(
  "${TOOLHUB_PYTHON_ROOT:-/opt/toolhub}/tools/wol-cli/wol-cli.sh"
  "/opt/toolhub/tools/wol-cli/wol-cli.sh"
  "${REPO_ROOT}/tools/wol-cli/wol-cli.sh"
  "/workspace/tools/wol-cli/wol-cli.sh"
)

TARGET=""
for candidate in "${CANDIDATES[@]}"; do
  if [[ -x "${candidate}" ]]; then
    TARGET="${candidate}"
    break
  fi
done

if [[ -z "${TARGET}" ]]; then
  printf '{"ok":false,"error":"wol_cli_missing"}\n'
  exit 1
fi

exec "${TARGET}" "$@"
