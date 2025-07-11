#!/bin/bash
# Redirect all output (stdout and stderr) to start.log
exec > /logs/start.log 2>&1

echo "[INIT] Checking if initial directories need setup..."


BOOTSTRAP_SRC="/bootstrap"

# Kopiere start.sh ins Workspace, wenn dort noch nicht vorhanden
if [ ! -f /workspace/start.sh ]; then
  echo "[INIT] Copying start.sh into /workspace..."
  cp "$BOOTSTRAP_SRC/start.sh" /workspace/start.sh
fi

# Zielverzeichnisse auf dem Host (werden vom Volume überlagert)
for dir in /workspace/scripts /workspace/cron.d /workspace/logs; do
  if [ ! -d "$dir" ]; then
    echo "[INIT] Creating missing directory: $dir"
    mkdir -p "$dir"
  fi
done

# Kopiere nur, wenn leer
if [ -z "$(ls -A /workspace/scripts 2>/dev/null)" ]; then
  echo "[INIT] Populating scripts..."
  cp -r "$BOOTSTRAP_SRC/scripts/"* /workspace/scripts/
fi

if [ -z "$(ls -A /workspace/cron.d 2>/dev/null)" ]; then
  echo "[INIT] Populating cron.d..."
  cp -r "$BOOTSTRAP_SRC/cron.d/"* /workspace/cron.d/
fi

# logs Ordner befüllen, wenn leer
if [ -z "$(ls -A /workspace/logs 2>/dev/null)" ]; then
  echo "[INIT] Populating logs..."
  cp -r "$BOOTSTRAP_SRC/logs/"* /workspace/logs/
fi

# Startet SSH, Cron und den Flask-Webserver

/usr/sbin/sshd &
cron &
exec python3 /scripts/webhook.py
