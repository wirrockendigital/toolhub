
#!/bin/bash
# Dynamically set user parameters from environment or defaults
: "${TOOLHUB_USER:=toolhubuser}"
: "${TOOLHUB_PASSWORD:=toolhub123}"
: "${TOOLHUB_UID:=1061}"
: "${TOOLHUB_GID:=100}"
GROUP_NAME="users"

# Use system group 'users', assume it exists (Debian default)
GROUP_NAME="users"

# Create user if it doesn't exist
if ! id -u "$TOOLHUB_USER" >/dev/null 2>&1; then
  useradd -m -u "$TOOLHUB_UID" -g "$GROUP_NAME" -s /bin/bash "$TOOLHUB_USER"
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

 # Populate scripts (conditional overwrite)
if [[ "$TOOLHUB_FORCE_UPDATE" == "1" ]]; then
  echo "[INIT] Overwriting scripts (TOOLHUB_FORCE_UPDATE=1)..."
  cp -r "$BOOTSTRAP_SRC/scripts/." /scripts/
  echo "[INIT] Overwriting cron.d (TOOLHUB_FORCE_UPDATE=1)..."
  cp -r "$BOOTSTRAP_SRC/cron.d/." /etc/cron.d/
  echo "[INIT] Overwriting logs (TOOLHUB_FORCE_UPDATE=1)..."
  cp -r "$BOOTSTRAP_SRC/logs/." /logs/
else
  echo "[INIT] Skipping script/cron/log overwrite (TOOLHUB_FORCE_UPDATE not set)"
fi

echo "[INIT] Starting SSH daemon..."
/usr/sbin/sshd &

echo "[INIT] Starting cron daemon..."
cron &

# Launch webhook service with Gunicorn as toolhubuser
echo "[INIT] Launching webhook service with Gunicorn as $TOOLHUB_USER..."
exec su - "$TOOLHUB_USER" -c "cd /scripts && gunicorn --bind 0.0.0.0:5656 webhook:app"
