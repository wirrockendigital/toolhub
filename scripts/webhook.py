#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import subprocess
import logging
import os
from werkzeug.utils import secure_filename
import uuid
import zipfile
import shutil

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
    logger.info(f"Executing command: {cmd}")

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


# --- TEST ENDPOINT ---
@app.route("/test", methods=["GET", "POST"])
def test():
    if request.method == "GET":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(force=True)
    return jsonify({"status": "ok", "message": "Toolhub webhook service is running", "received": data})


# --- AUDIO SPLIT ENDPOINT ---
@app.route("/audio-split", methods=["POST"])
def audio_split():
    logger.info(f"Audio split request: mode={request.form.get('mode')}, chunk_length={request.form.get('chunk_length')}, "
                f"silence_seek={request.form.get('silence_seek')}, silence_duration={request.form.get('silence_duration')}, "
                f"silence_threshold={request.form.get('silence_threshold')}, padding={request.form.get('padding')}")
    # 1) Receive file and parameters
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No audio file uploaded"}), 400

    mode = request.form.get("mode")
    try:
        chunk_length = int(request.form.get("chunk_length", 0))
    except ValueError:
        return jsonify({"error": "Invalid chunk_length"}), 400

    # Validate mode
    if mode not in ("fixed", "silence"):
        return jsonify({"error": "mode must be 'fixed' or 'silence'"}), 400

    # Silence-specific parameters
    silence_seek = int(request.form.get("silence_seek", 0)) if mode == "silence" else 0
    try:
        silence_duration = float(request.form.get("silence_duration", 0.0)) if mode == "silence" else 0.0
    except ValueError:
        return jsonify({"error": "Invalid silence_duration"}), 400
    try:
        silence_threshold = float(request.form.get("silence_threshold", 0.0)) if mode == "silence" else 0.0
    except ValueError:
        return jsonify({"error": "Invalid silence_threshold"}), 400
    try:
        padding = float(request.form.get("padding", 0.0)) if mode == "silence" else 0.0
    except ValueError:
        return jsonify({"error": "Invalid padding"}), 400

    # Enhancement options
    enhance = request.form.get("enhance", "false").lower() in ("1", "true", "yes")
    enhance_speech = request.form.get("enhance_speech", "false").lower() in ("1", "true", "yes")
    if enhance and enhance_speech:
        return jsonify({"error": "Cannot use both enhance and enhance_speech simultaneously"}), 400

    # 2) Save upload to shared input folder
    job_id = str(uuid.uuid4())
    input_dir = "/shared/audio/in"
    output_dir = f"/shared/audio/out/{job_id}"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    input_path = os.path.join(input_dir, filename)
    file.save(input_path)

    # 3) Call the split script
    cmd = [
        "/scripts/audio-split.sh",
        "--mode", mode,
        "--chunk-length", str(chunk_length),
        "--input", input_path,
        "--output", output_dir
    ]
    if mode == "silence":
        cmd += [
            "--silence-seek", str(silence_seek),
            "--silence-duration", str(silence_duration),
            "--silence-threshold", str(silence_threshold),
            "--padding", str(padding)
        ]

    # Append enhancement flags
    if enhance_speech:
        cmd.append("--enhance-speech")
    elif enhance:
        cmd.append("--enhance")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running split script: {e}")
        return jsonify({"error": str(e)}), 500

    # 4) Zip the results
    zip_path = f"/shared/audio/out/{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(output_dir):
            for f_name in files:
                file_path = os.path.join(root, f_name)
                arcname = os.path.relpath(file_path, output_dir)
                zf.write(file_path, arcname)

    # 5) Clean up the folder
    shutil.rmtree(output_dir)

    # 6) Return the zip
    return send_file(zip_path, mimetype="application/zip", as_attachment=True,
                     download_name=f"audio-split-{job_id}.zip")

if __name__ == "__main__":
    # Starte den Server auf Port 5656 (intern)
    app.run(host="0.0.0.0", port=5656)