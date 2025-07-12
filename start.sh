#!/bin/bash
# start.sh - Bootstrap and launch Toolhub services

# Redirect all output (stdout and stderr) to /logs/start.log
# exec > /logs/start.log 2>&1

echo "[INIT] Starting bootstrap..."
BOOTSTRAP_SRC="/bootstrap"

# Ensure directories exist
for dir in /scripts /etc/cron.d /logs; do
  echo "[INIT] Creating directory if missing: $dir"
  mkdir -p "$dir"
done

# Populate scripts (overwrite)
echo "[INIT] Populating scripts..."
cp -r "$BOOTSTRAP_SRC/scripts/." /scripts/

# Populate cron.d (overwrite)
echo "[INIT] Populating cron.d..."
cp -r "$BOOTSTRAP_SRC/cron.d/." /etc/cron.d/

# Populate logs (overwrite)
echo "[INIT] Populating logs..."
cp -r "$BOOTSTRAP_SRC/logs/." /logs/

# Generate SSH host keys if missing
echo "[INIT] Generating SSH host keys..."
ssh-keygen -A

# Start SSH daemon
echo "[INIT] Starting SSH daemon..."
/usr/sbin/sshd &

# Start cron daemon
echo "[INIT] Starting cron daemon..."
cron &

# Launch webhook service
echo "[INIT] Launching webhook service..."
exec python3 /scripts/webhook.py
