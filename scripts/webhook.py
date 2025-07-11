#!/usr/bin/env python3
from flask import Flask, request, jsonify
import subprocess
import logging
import os

# Define size units
KB = 1024
MB = 1024 * KB
GB = 1024 * MB

# Maximum JSON payload size (in bytes)
MAX_PAYLOAD_SIZE = 1 * GB  # 1 GB

# Logging-Verzeichnis sicherstellen
LOG_DIR = '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

# Logger konfigurieren
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'webhook.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Max JSON-Payload auf 1 GB begrenzen
app.config['MAX_CONTENT_LENGTH'] = MAX_PAYLOAD_SIZE


# Nur Pfade innerhalb dieser Verzeichnisse erlauben
ALLOWED_PATH_PREFIXES = ("/workspace/", "/shared/")

# Liste der erlaubten Tools
ALLOWED_TOOLS = {
    "curl", "wget", "git", "ffmpeg", "jq", "yq",
    "unzip", "convert", "sox", "python3", "pip3",
    "nano", "less", "lsof", "tree", "htop", "exiftool"
}

@app.route("/run", methods=["POST"])
def run_tool():
    data = request.get_json(force=True)

    tool = data.get("tool")
    args = data.get("args", [])

    # Basis-Checks
    if not tool or not isinstance(args, list):
        return jsonify({
            "error": "Bitte 'tool' (String) und 'args' (Liste) angeben"
        }), 400

    # Prüfen, ob das Tool erlaubt ist
    if tool not in ALLOWED_TOOLS:
        return jsonify({
            "error": f"Tool nicht erlaubt: {tool}"
        }), 400

    # Sicherheits-Check für übergebene Pfade (Absolut, keine Traversal)
    for a in args:
        if ".." in a or "~" in a:
            return jsonify({"error": f"Ungültiger Pfad: {a}"}), 400
        abs_path = os.path.abspath(a)
        if not any(abs_path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
            return jsonify({"error": f"Ungültiger Pfad: {a}"}), 400

    logger.info(f"Request for tool={tool}, args={args}")

    # Kommando zusammenbauen und ausführen
    cmd = [tool] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600
        )
        logger.info(f"Request for tool={tool}, args={args}")
        return jsonify({
            "cmd": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {cmd}: {e}")
        return jsonify({
            "cmd": cmd,
            "error": str(e),
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500

if __name__ == "__main__":
    # Starte den Server auf Port 5656 (intern)
    app.run(host="0.0.0.0", port=5656)