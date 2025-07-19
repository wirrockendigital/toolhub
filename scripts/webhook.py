#!/usr/bin/env python3
from flask import Flask, request, jsonify
import subprocess
import logging
import os
from werkzeug.utils import secure_filename
import uuid

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
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)
logger.debug(f"Environment variables: {dict(os.environ)}")


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
        logger.exception(f"Error running {cmd}: {e}")
        logger.debug(f"CalledProcessError details: returncode={e.returncode}")
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
    # Parse JSON payload
    data = request.get_json(force=True)

    # 1) Resolve existing shared-file path
    filename = secure_filename(data.get("filename", ""))
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    input_dir = "/shared/audio/in"
    input_path = os.path.join(input_dir, filename)
    if not os.path.isfile(input_path):
        return jsonify({"error": f"Input file not found: {input_path}"}), 404
    logger.info(f"Using shared input file: {input_path}")

    mode = data.get("mode")
    try:
        chunk_length = int(data.get("chunk_length", 0))
    except ValueError:
        return jsonify({"error": "Invalid chunk_length"}), 400

    # Validate mode
    if mode not in ("fixed", "silence"):
        return jsonify({"error": "mode must be 'fixed' or 'silence'"}), 400

    # Silence-specific parameters
    silence_seek = int(data.get("silence_seek", 0)) if mode == "silence" else 0
    try:
        silence_duration = float(data.get("silence_duration", 0.0)) if mode == "silence" else 0.0
    except ValueError:
        return jsonify({"error": "Invalid silence_duration"}), 400
    try:
        silence_threshold = float(data.get("silence_threshold", 0.0)) if mode == "silence" else 0.0
    except ValueError:
        return jsonify({"error": "Invalid silence_threshold"}), 400
    try:
        padding = float(data.get("padding", 0.0)) if mode == "silence" else 0.0
    except ValueError:
        return jsonify({"error": "Invalid padding"}), 400

    enhance = str(data.get("enhance", "false")).lower() in ("1", "true", "yes")
    enhance_speech = str(data.get("enhance_speech", "false")).lower() in ("1", "true", "yes")
    logger.info(f"Enhance={enhance}, Enhance_speech={enhance_speech}")
    if enhance and enhance_speech:
        return jsonify({"error": "Cannot use both enhance and enhance_speech simultaneously"}), 400

    # 2) Prepare output directory
    job_id = str(uuid.uuid4())
    output_dir = f"/shared/audio/out/{job_id}"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")

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
        logger.debug("Executing split script with command arguments:")
        for index, arg in enumerate(cmd):
            logger.debug(f"  cmd[{index}] = {arg}")
        logger.info(f"Starting external script: {' '.join(cmd)}")
        # Execute the split script with a 10-minute timeout to prevent hanging
        subprocess.run(cmd, check=True, timeout=600)
        logger.info(f"Split script returned with exit code 0 for job {job_id}")
        audio_files = [f for f in os.listdir(output_dir)
                       if f.endswith(('.mp3', '.m4a', '.wav'))]
        if not audio_files:
            logger.error(
                f"No audio chunks were generated for job {job_id} in {output_dir}")
            return jsonify({"error": "No audio chunks were generated"}), 500
        else:
            logger.info(f"Audio chunks generated: {audio_files}")
    except subprocess.TimeoutExpired as e:
        logger.exception(f"Split script timed out after 600s")
        logger.debug(f"Timeout exception details: {e}")
        return jsonify({"error": "Audio split timed out", "detail": str(e)}), 504
    except subprocess.CalledProcessError as e:
        logger.exception("Error running split script")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        logger.debug(f"CalledProcessError details: returncode={e.returncode}")
        log_tail = ""
        try:
            with open("/logs/audio-split.log", "r") as log_f:
                log_tail = "".join(log_f.readlines()[-20:])
        except Exception as log_err:
            log_tail = f"Failed to read log: {log_err}"
        return jsonify({
            "error": str(e),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "log_tail": log_tail,
        }), 500

    # Return the job ID and list of generated files
    return jsonify({
        "job_id": job_id,
        "output_dir": output_dir,
        "files": audio_files
    }), 200

if __name__ == "__main__":
    # Start the server on port 5656 (internal)
    app.run(host="0.0.0.0", port=5656)