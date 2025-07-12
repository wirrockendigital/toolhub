#!/bin/bash
# start.sh - Bootstrap and launch Toolhub services

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

# Start SSH daemon
echo "[INIT] Starting SSH daemon..."
su - toolhubuser -c "/usr/sbin/sshd &"

# Start cron daemon, writing PID into /var/run/cron
echo "[INIT] Starting cron daemon..."
su - toolhubuser -c "cron &"

# Launch webhook service with Gunicorn as toolhubuser
echo "[INIT] Launching webhook service with Gunicorn as toolhubuser..."
exec su - toolhubuser -c "cd /scripts && gunicorn --bind 0.0.0.0:5656 webhook:app"
