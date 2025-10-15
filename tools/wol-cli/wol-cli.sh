#!/usr/bin/env bash
set -euo pipefail

print_error() {
  local code="$1"
  printf '{"ok":false,"error":"%s"}\n' "$code"
  exit 1
}

target="${1:-}"
if [[ -z "$target" ]]; then
  print_error "target_required"
fi

mac=""
source="mac"
device_name=""

MAC_REGEX='^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'

if [[ "$target" =~ $MAC_REGEX ]]; then
  mac="$(printf '%s' "$target" | tr '[:lower:]' '[:upper:]')"
else
  source="mapping"
  device_name="$target"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  CONFIG_DIR="${ROOT_DIR}/config"

  map_file=""
  if [[ -f "${CONFIG_DIR}/wol-devices.json" ]]; then
    map_file="${CONFIG_DIR}/wol-devices.json"
  elif [[ -f "${CONFIG_DIR}/wol-devices.sample.json" ]]; then
    map_file="${CONFIG_DIR}/wol-devices.sample.json"
  else
    print_error "device_map_missing"
  fi

  if ! command -v jq >/dev/null 2>&1; then
    print_error "jq_not_found"
  fi

  lookup="$(jq -r \
    --arg key "$(printf '%s' "$device_name" | tr '[:upper:]' '[:lower:]')" \
    'with_entries(.key |= ascii_downcase) | .[$key] // empty' \
    "$map_file")"

  if [[ -z "$lookup" ]]; then
    print_error "device_not_found"
  fi

  if [[ ! "$lookup" =~ $MAC_REGEX ]]; then
    print_error "invalid_mac_mapping"
  fi

  mac="$(printf '%s' "$lookup" | tr '[:lower:]' '[:upper:]')"
fi

broadcast="${WOL_BROADCAST:-}"
cmd=(wakeonlan)
if [[ -n "$broadcast" ]]; then
  cmd+=(-i "$broadcast")
fi
cmd+=("$mac")

if ! "${cmd[@]}" >/dev/null 2>&1; then
  print_error "wakeonlan_failed"
fi

payload="{\"ok\":true,\"mac\":\"$mac\"}"
if [[ "$source" == "mapping" ]]; then
  payload="{\"ok\":true,\"mac\":\"$mac\",\"device\":\"$device_name\"}"
fi
if [[ -n "$broadcast" ]]; then
  payload="${payload::-1},\"broadcast\":\"$broadcast\"}"
fi

printf '%s\n' "$payload"
