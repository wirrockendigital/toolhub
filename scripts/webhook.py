#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file, after_this_request
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

# Ensure log directory exists and configure logging
LOG_DIR = '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logger
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'webhook.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


app = Flask(__name__)


# Limit max JSON payload to 1 GB
app.config['MAX_CONTENT_LENGTH'] = MAX_PAYLOAD_SIZE


# Allow only paths within these directories
ALLOWED_PATH_PREFIXES = ("/workspace/", "/shared/")

# List of allowed tools
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

    # Basic checks
    if not tool or not isinstance(args, list):
        return jsonify({
            "error": "Please provide 'tool' (string) and 'args' (list)"
        }), 400

    # Check if the tool is allowed
    if tool not in ALLOWED_TOOLS:
        return jsonify({
            "error": f"Tool not allowed: {tool}"
        }), 400

    # Security check for passed paths (absolute, no traversal)
    for a in args:
        if ".." in a or "~" in a:
            return jsonify({"error": f"Invalid path: {a}"}), 400
        abs_path = os.path.abspath(a)
        if not any(abs_path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
            return jsonify({"error": f"Invalid path: {a}"}), 400

    cmd = [tool] + args
    logger.info(f"Request for tool={tool}, args={args}")
    logger.info(f"Executing command: {cmd}")

    # Build and execute the command
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
    # Log request parameters
    logger.info(f"Audio split request: mode={request.form.get('mode')}, chunk_length={request.form.get('chunk_length')}, "
                f"silence_seek={request.form.get('silence_seek')}, silence_duration={request.form.get('silence_duration')}, "
                f"silence_threshold={request.form.get('silence_threshold')}, padding={request.form.get('padding')}")

    # 1) Receive file and parameters
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No audio file uploaded"}), 400

    # Check if filename is present and secure it
    if not file.filename:
        return jsonify({"error": "Uploaded file has no filename"}), 400
    filename = secure_filename(file.filename)

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

    logger.info(f"Enhance={request.form.get('enhance', 'false').lower() in ('1', 'true', 'yes')}, Enhance_speech={request.form.get('enhance_speech', 'false').lower() in ('1', 'true', 'yes')}")

    # Enhancement options
    enhance = request.form.get("enhance", "false").lower() in ("1", "true", "yes")
    enhance_speech = request.form.get("enhance_speech", "false").lower() in ("1", "true", "yes")
    if enhance and enhance_speech:
        return jsonify({"error": "Cannot use both enhance and enhance_speech simultaneously"}), 400

    # 2) Save uploaded file to shared input folder
    job_id = str(uuid.uuid4())
    input_dir = "/shared/audio/in"
    output_dir = f"/shared/audio/out/{job_id}"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    input_path = os.path.join(input_dir, filename)
    file.save(input_path)

    # 3) Call the split script with appropriate arguments
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

    # Append enhancement flags if specified
    if enhance_speech:
        cmd.append("--enhance-speech")
    elif enhance:
        cmd.append("--enhance")

    try:
        logger.info(f"Calling script with command: {' '.join(cmd)}")
        # Execute the split script with a 10-minute timeout to prevent hanging
        subprocess.run(cmd, check=True, timeout=600)
        logger.info(f"Split script finished successfully for job {job_id}")
        if not any(fname.endswith(('.mp3', '.m4a', '.wav')) for fname in os.listdir(output_dir)):
            logger.error(f"No audio chunks were generated for job {job_id} in {output_dir}")
        else:
            logger.info(f"Audio chunks generated: {os.listdir(output_dir)}")
    except subprocess.TimeoutExpired as e:
        logger.exception(f"Split script timed out after 600s")
        return jsonify({"error": "Audio split timed out", "detail": str(e)}), 504
    except subprocess.CalledProcessError as e:
        logger.exception("Error running split script")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return jsonify({"error": str(e), "stdout": e.stdout, "stderr": e.stderr}), 500

    zip_path = f"/shared/audio/out/{job_id}.zip"
    logger.info(f"Zipping output directory {output_dir} into {zip_path}")
    # 4) Zip the results from the output folder
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(output_dir):
            for f_name in files:
                file_path = os.path.join(root, f_name)
                arcname = os.path.relpath(file_path, output_dir)
                zf.write(file_path, arcname)

    # 5) Schedule cleanup of the output folder and zip file after sending the response
    @after_this_request
    def cleanup(response):
        try:
            logger.info(f"Cleaning up job {job_id} resources: {output_dir}, {zip_path}")
            shutil.rmtree(output_dir)
            os.remove(zip_path)
            logger.info(f"Cleaned up output: {output_dir} and zip: {zip_path}")
        except Exception as cleanup_error:
            logger.warning(f"Cleanup failed: {cleanup_error}")
        return response

    # 6) Return the zip file as a downloadable attachment
    return send_file(zip_path, mimetype="application/zip", as_attachment=True,
                     download_name=f"audio-split-{job_id}.zip")

if __name__ == "__main__":
    # Start the server on port 5656 (internal)
    app.run(host="0.0.0.0", port=5656)