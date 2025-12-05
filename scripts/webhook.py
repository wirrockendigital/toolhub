#!/usr/bin/env python3
"""
Toolhub Webhook Service

Exposes REST endpoints:
  GET  /             Service info & available routes
  GET/POST /test     Health check
  POST /audio-split  Split audio files from /shared/audio/in
  POST /run          Dispatch registered Toolhub tools (e.g. docx-render)

Logs all activity to /logs/webhook.log.
"""
from flask import Flask, request, jsonify
import subprocess
import logging
import os
import sys
from werkzeug.utils import secure_filename
import uuid
from werkzeug.exceptions import HTTPException
import time

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

TOOLS_ROOT = os.getenv("TOOLHUB_PYTHON_ROOT", "/workspace")
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

try:
    from tools import TOOLS
except Exception as exc:  # noqa: BLE001
    TOOLS = {}
    logger.exception("Failed to import tool registry", exc_info=exc)


app = Flask(__name__)

# Detailed request/response logging with timing
@app.before_request
def log_request_start():
    request.start_time = time.time()
    logger.info(
        f"Incoming request: {request.method} {request.path} "
        f"from {request.remote_addr}, args={request.args}, json={request.get_json(silent=True)}"
    )

@app.after_request
def log_request_end(response):
    duration = time.time() - getattr(request, 'start_time', time.time())
    logger.info(
        f"Handled request: {request.method} {request.path} "
        f"status={response.status_code} in {duration:.3f}s"
    )
    return response


# Limit max JSON payload to 1 GB
app.config['MAX_CONTENT_LENGTH'] = MAX_PAYLOAD_SIZE

# Helper to centralize error logging and JSON response
def respond_error(name, message, code=500, exc=None):
    if exc:
        logger.exception(name)
    else:
        logger.error(f"{name}: {message}")
    return jsonify({"error": name, "message": message}), code

@app.route("/", methods=["GET"])
def index():
    """Return service info with available routes."""
    return jsonify({
        "service": "Toolhub Webhook",
        "endpoints": {
            "/":           "This help message",
            "/test":       "GET or POST health-check",
            "/audio-split":"POST JSON {filename, mode, …} → split audio from /shared",
            "/run":        "POST JSON {tool, payload} → run registered Toolhub tool"
        }
    }), 200


# --- TEST ENDPOINT ---
@app.route("/test", methods=["GET", "POST"])
def test():
    if request.method == "GET":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(force=True)
    return jsonify({"status": "ok", "message": "Toolhub webhook service is running", "received": data})


# --- GENERIC TOOL DISPATCH ---
@app.route("/run", methods=["POST"])
def run_tool():
    payload = request.get_json(force=True)

    tool_name = payload.get("tool") if isinstance(payload, dict) else None
    tool_payload = payload.get("payload") if isinstance(payload, dict) else None

    if not tool_name:
        return jsonify({"error": "tool is required"}), 400

    if tool_name not in TOOLS:
        logger.warning(f"Requested unknown tool: {tool_name}")
        return jsonify({"error": f"Unknown tool '{tool_name}'"}), 404

    handler = TOOLS[tool_name].get("handler")
    if handler is None:
        logger.error(f"Handler missing for tool: {tool_name}")
        return jsonify({"error": f"Tool '{tool_name}' is not configured"}), 500

    logger.info(
        f"Dispatching tool '{tool_name}' with payload keys: {list(tool_payload.keys()) if isinstance(tool_payload, dict) else 'n/a'}"
    )

    try:
        result = handler(tool_payload if isinstance(tool_payload, dict) else {})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool execution failed", exc_info=exc)
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"type": exc.__class__.__name__, "message": str(exc)},
                }
            ),
            500,
        )

    status_code = 200 if isinstance(result, dict) and result.get("status") == "ok" else 400
    return jsonify(result), status_code


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
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
        duration = time.time() - start
        logger.debug(f"Split script stdout: {result.stdout}")
        logger.debug(f"Split script stderr: {result.stderr}")
        logger.info(f"Split script returned with exit code {result.returncode} for job {job_id} in {duration:.3f}s")
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

# Error handler for HTTP exceptions (e.g., 400, 404)
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return respond_error(e.name, e.description, code=e.code, exc=e)

# Global exception handler to return JSON on uncaught errors
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    return respond_error("Internal server error", str(e), code=500, exc=e)

if __name__ == "__main__":
    # Start the server on port 5656 (internal)
    app.run(host="0.0.0.0", port=5656)