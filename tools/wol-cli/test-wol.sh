#!/usr/bin/env bash
set -euo pipefail

if ! command -v wakeonlan >/dev/null 2>&1; then
  echo "wakeonlan binary not found" >&2
  exit 1
fi

wakeonlan -h >/dev/null 2>&1 || {
  echo "wakeonlan -h failed" >&2
  exit 1
}

if [[ -n "${WOL_TEST_MAC:-}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CLI="${SCRIPT_DIR}/wol-cli.sh"
  if [[ ! -x "$CLI" ]]; then
    echo "wol-cli.sh is not executable" >&2
    exit 1
  fi
  "$CLI" "$WOL_TEST_MAC" >/dev/null
fi

echo "wol-cli checks passed"
