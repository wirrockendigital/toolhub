#!/bin/bash
# Redirect all output (stdout and stderr) to start.log
exec > /logs/start.log 2>&1

echo "[INIT] Checking if initial directories need setup..."


BOOTSTRAP_SRC="/bootstrap"

# Kopiere start.sh ins Workspace, wenn dort noch nicht vorhanden
if [ ! -f /scripts/start.sh ]; then
  echo "[INIT] Copying start.sh into /scripts..."
  cp "$BOOTSTRAP_SRC/start.sh" /scripts/start.sh
fi

# Zielverzeichnisse auf dem Host (werden vom Volume überlagert)
for dir in /scripts /etc/cron.d /logs; do
  if [ ! -d "$dir" ]; then
    echo "[INIT] Creating missing directory: $dir"
    mkdir -p "$dir"
  fi
done

echo "[INIT] Populating scripts (overwrite)..."
cp -r "$BOOTSTRAP_SRC/scripts/"* /scripts/

echo "[INIT] Populating cron.d (overwrite)..."
cp -r "$BOOTSTRAP_SRC/cron.d/"* /etc/cron.d/

echo "[INIT] Populating logs (overwrite)..."
cp -r "$BOOTSTRAP_SRC/logs/"* /logs/

# Startet SSH, Cron und den Flask-Webserver

/usr/sbin/sshd &
cron &
exec python3 /scripts/webhook.py
