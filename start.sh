
#!/bin/bash
# Dynamically set user parameters from environment or defaults
: "${TOOLHUB_USER:=toolhubuser}"
: "${TOOLHUB_PASSWORD:=toolhub123}"
: "${TOOLHUB_UID:=1061}"
: "${TOOLHUB_GID:=100}"

# Determine group name for TOOLHUB_GID
GROUP_NAME="$(getent group "$TOOLHUB_GID" | cut -d: -f1)"
if [[ -z "$GROUP_NAME" ]]; then
  GROUP_NAME="toolhub"
  groupadd -g "$TOOLHUB_GID" "$GROUP_NAME"
fi

# Create user if it doesn't exist
if ! id -u "$TOOLHUB_USER" >/dev/null 2>&1; then
  useradd -u "$TOOLHUB_UID" -g "$GROUP_NAME" -s /bin/bash -d /workspace "$TOOLHUB_USER"
  echo "$TOOLHUB_USER:$TOOLHUB_PASSWORD" | chpasswd
fi

echo "[INIT] Starting bootstrap..."
BOOTSTRAP_SRC="/bootstrap"

# Detect if /scripts is a mounted host volume vs. image content
if grep -qs ' /scripts ' /proc/mounts; then
  echo "[INIT] /scripts is a bind mount from host volume."
else
  echo "[INIT] /scripts is using embedded image content."
fi


# Ensure necessary directories exist with correct ownership
for dir in /scripts /etc/cron.d /logs /var/run/cron; do
  echo "[INIT] Creating or fixing directory: $dir"
  mkdir -p "$dir"
  chown "$TOOLHUB_USER:$GROUP_NAME" "$dir"
done

# Ensure shared audio directory structure exists
echo "[INIT] Creating shared audio directories..."
SHARED_DIR="/shared"
for d in "$SHARED_DIR" "$SHARED_DIR/audio" "$SHARED_DIR/audio/in" "$SHARED_DIR/audio/out"; do
  mkdir -p "$d"
  chown "$TOOLHUB_USER:$GROUP_NAME" "$d"
done




# Always copy default bootstrap content if not previously initialized
if [[ ! -f /scripts/.initialized ]]; then
  echo "[INIT] First-time bootstrap: copying default content..."
  cp -r "$BOOTSTRAP_SRC/scripts/." /scripts/
  cp -r "$BOOTSTRAP_SRC/cron.d/." /etc/cron.d/
  cp -r "$BOOTSTRAP_SRC/logs/." /logs/
  touch /scripts/.initialized
else
  echo "[INIT] /scripts already initialized – skipping bootstrap copy"
fi

echo "[INIT] Starting SSH daemon..."
/usr/sbin/sshd &

echo "[INIT] Starting cron daemon..."
cron &

# Launch webhook service with Gunicorn as toolhubuser
echo "[INIT] Launching webhook service with Gunicorn as $TOOLHUB_USER..."
exec su "$TOOLHUB_USER" -c "PYTHONPATH=/scripts gunicorn --chdir /scripts --bind 0.0.0.0:5656 webhook:app"

# Symlink .bashrc from /workspace/conf/.bashrc if it exists
if [[ -f /workspace/conf/.bashrc ]]; then
  echo "[INIT] Linking .bashrc from /workspace/conf/.bashrc"
  ln -sf /workspace/conf/.bashrc /workspace/.bashrc
fi