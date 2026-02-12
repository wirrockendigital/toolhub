#!/bin/bash
set -euo pipefail

# Enable verbose debugging if DEBUG=true.
if [[ "${DEBUG:-false}" == "true" ]]; then
  set -x
fi

# Resolve runtime identity and project root from environment.
: "${TOOLHUB_USER:=toolhubuser}"
: "${TOOLHUB_PASSWORD:=toolhub123}"
: "${TOOLHUB_UID:=1061}"
: "${TOOLHUB_GID:=100}"
: "${TOOLHUB_PROJECT_ROOT:=/workspace}"
GROUP_NAME="users"
BOOTSTRAP_SRC="/bootstrap"

# Determine group name for TOOLHUB_GID.
GROUP_NAME="$(getent group "$TOOLHUB_GID" | cut -d: -f1)"
if [[ -z "$GROUP_NAME" ]]; then
  GROUP_NAME="users"
  # Create the users group if it does not exist.
  if ! getent group "$GROUP_NAME" >/dev/null; then
    groupadd -g "$TOOLHUB_GID" "$GROUP_NAME"
  fi
fi

# Create runtime user if it does not exist yet.
if ! id -u "$TOOLHUB_USER" >/dev/null 2>&1; then
  useradd -u "$TOOLHUB_UID" -g "$GROUP_NAME" -s /bin/bash -d "$TOOLHUB_PROJECT_ROOT" "$TOOLHUB_USER"
  echo "$TOOLHUB_USER:$TOOLHUB_PASSWORD" | chpasswd
fi

echo "[INIT] Starting bootstrap..."

# Ensure canonical project directories exist under TOOLHUB_PROJECT_ROOT.
for dir in \
  "$TOOLHUB_PROJECT_ROOT" \
  "$TOOLHUB_PROJECT_ROOT/scripts" \
  "$TOOLHUB_PROJECT_ROOT/cron.d" \
  "$TOOLHUB_PROJECT_ROOT/logs" \
  "$TOOLHUB_PROJECT_ROOT/shared/audio/in" \
  "$TOOLHUB_PROJECT_ROOT/shared/audio/out" \
  "$TOOLHUB_PROJECT_ROOT/data/templates" \
  "$TOOLHUB_PROJECT_ROOT/data/output" \
  "$TOOLHUB_PROJECT_ROOT/conf"
do
  echo "[INIT] Creating or fixing directory: $dir"
  mkdir -p "$dir"
  chown "$TOOLHUB_USER:$GROUP_NAME" "$dir"
done

# Link legacy container paths to the single-root project layout.
ensure_symlink() {
  local target="$1"
  local link_path="$2"

  # Keep explicit external mounts untouched to preserve compatibility.
  if grep -qs " ${link_path} " /proc/mounts; then
    echo "[INIT] Keeping mounted path: ${link_path}"
    return
  fi

  # Replace existing local paths so all tools resolve to canonical project dirs.
  rm -rf "${link_path}"
  ln -s "${target}" "${link_path}"
  echo "[INIT] Linked ${link_path} -> ${target}"
}

ensure_symlink "$TOOLHUB_PROJECT_ROOT/scripts" "/scripts"
ensure_symlink "$TOOLHUB_PROJECT_ROOT/logs" "/logs"
ensure_symlink "$TOOLHUB_PROJECT_ROOT/shared" "/shared"
ensure_symlink "$TOOLHUB_PROJECT_ROOT/data" "/data"
ensure_symlink "$TOOLHUB_PROJECT_ROOT/data/templates" "/templates"
ensure_symlink "$TOOLHUB_PROJECT_ROOT/data/output" "/output"

# Keep cron runtime directory available.
mkdir -p /var/run/cron
chown "$TOOLHUB_USER:$GROUP_NAME" /var/run/cron

# Bootstrap defaults into the project root when scripts are not initialized.
if [[ ! -f "$TOOLHUB_PROJECT_ROOT/scripts/.initialized" || -z "$(ls -A "$TOOLHUB_PROJECT_ROOT/scripts" | grep -v '^.initialized$')" ]]; then
  echo "[INIT] First-time bootstrap: copying default content into project root..."
  cp -r "$BOOTSTRAP_SRC/scripts/." "$TOOLHUB_PROJECT_ROOT/scripts/" || exit 1
  cp -r "$BOOTSTRAP_SRC/cron.d/." "$TOOLHUB_PROJECT_ROOT/cron.d/" || exit 1
  cp -r "$BOOTSTRAP_SRC/logs/." "$TOOLHUB_PROJECT_ROOT/logs/" || exit 1
  touch "$TOOLHUB_PROJECT_ROOT/scripts/.initialized"
else
  echo "[INIT] Scripts already initialized in project root – skipping bootstrap copy"
fi

# Sync cron files from project root into /etc/cron.d for cron daemon pickup.
mkdir -p /etc/cron.d
cp -f "$TOOLHUB_PROJECT_ROOT/cron.d/"* /etc/cron.d/ 2>/dev/null || true

echo "[INIT] Starting SSH daemon..."
/usr/sbin/sshd &

echo "[INIT] Starting cron daemon..."
cron &

# Link .bashrc from project conf when available.
if [[ -f "$TOOLHUB_PROJECT_ROOT/conf/.bashrc" ]]; then
  echo "[INIT] Linking .bashrc from $TOOLHUB_PROJECT_ROOT/conf/.bashrc"
  ln -sf "$TOOLHUB_PROJECT_ROOT/conf/.bashrc" "$TOOLHUB_PROJECT_ROOT/.bashrc" || exit 1
fi

# Launch webhook service with Gunicorn as runtime user.
echo "[INIT] Launching webhook service with Gunicorn as $TOOLHUB_USER..."
exec su "$TOOLHUB_USER" -c "cd /scripts && exec gunicorn --timeout 600 --bind 0.0.0.0:5656 webhook:app"
