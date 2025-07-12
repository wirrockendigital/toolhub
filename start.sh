#!/bin/bash
# Dynamically set TOOLHUB_UID and TOOLHUB_GID from environment or defaults
: "${TOOLHUB_UID:=1061}"
: "${TOOLHUB_GID:=100}"

# Ensure group exists or update its GID
if getent group toolhubuser >/dev/null 2>&1; then
  groupmod -g "$TOOLHUB_GID" toolhubuser
else
  groupadd -g "$TOOLHUB_GID" toolhubuser
fi

# Ensure user exists or update its UID and primary group
if id -u toolhubuser >/dev/null 2>&1; then
  usermod -u "$TOOLHUB_UID" -g "$TOOLHUB_GID" toolhubuser
else
  useradd -m -u "$TOOLHUB_UID" -g "$TOOLHUB_GID" -s /bin/bash toolhubuser
  echo "toolhubuser:changeme" | chpasswd
fi

echo "[INIT] Starting bootstrap..."
BOOTSTRAP_SRC="/bootstrap"

# Ensure necessary directories exist with correct ownership
for dir in /scripts /etc/cron.d /logs /var/run/cron; do
  echo "[INIT] Creating or fixing directory: $dir"
  mkdir -p "$dir"
  chown toolhubuser:toolhubuser "$dir"
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
echo "[INIT] Launching webhook service with Gunicorn as toolhubuser..."
exec su - toolhubuser -c "cd /scripts && gunicorn --bind 0.0.0.0:5656 webhook:app"
