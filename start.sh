
#!/bin/bash
# Dynamically set user parameters from environment or defaults
: "${TOOLHUB_USER:=toolhubuser}"
: "${TOOLHUB_PASSWORD:=toolhub123}"
: "${TOOLHUB_UID:=1061}"
: "${TOOLHUB_GID:=100}"

# Create group if it doesn't exist
if ! getent group "$TOOLHUB_GID" >/dev/null; then
  groupadd -g "$TOOLHUB_GID" "$TOOLHUB_USER"
fi

# Create user if it doesn't exist
if ! id -u "$TOOLHUB_USER" >/dev/null 2>&1; then
  useradd -m -u "$TOOLHUB_UID" -g "$TOOLHUB_GID" -s /bin/bash "$TOOLHUB_USER"
  echo "$TOOLHUB_USER:$TOOLHUB_PASSWORD" | chpasswd
fi

echo "[INIT] Starting bootstrap..."
BOOTSTRAP_SRC="/bootstrap"

# Ensure necessary directories exist with correct ownership
for dir in /scripts /etc/cron.d /logs /var/run/cron; do
  echo "[INIT] Creating or fixing directory: $dir"
  mkdir -p "$dir"
  chown "$TOOLHUB_USER:$TOOLHUB_USER" "$dir"
done

# Ensure shared audio directory structure exists
echo "[INIT] Creating shared audio directories..."
SHARED_DIR="/shared"
for d in "$SHARED_DIR" "$SHARED_DIR/audio" "$SHARED_DIR/audio/in" "$SHARED_DIR/audio/out"; do
  mkdir -p "$d"
  chown "$TOOLHUB_USER:$TOOLHUB_USER" "$d"
done

# Populate scripts (overwrite)
echo "[INIT] Populating scripts..."
cp -r "$BOOTSTRAP_SRC/scripts/." /scripts/

# Populate cron jobs (overwrite)
echo "[INIT] Populating cron.d..."
cp -r "$BOOTSTRAP_SRC/cron.d/." /etc/cron.d/

# Populate logs (overwrite)
echo "[INIT] Populating logs..."
cp -r "$BOOTSTRAP_SRC/logs/." /logs/

echo "[INIT] Starting SSH daemon..."
/usr/sbin/sshd &

echo "[INIT] Starting cron daemon..."
cron &

# Launch webhook service with Gunicorn as toolhubuser
echo "[INIT] Launching webhook service with Gunicorn as $TOOLHUB_USER..."
exec su - "$TOOLHUB_USER" -c "cd /scripts && gunicorn --bind 0.0.0.0:5656 webhook:app"
