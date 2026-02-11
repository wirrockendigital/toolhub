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
import json
from pathlib import Path
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

# Resolve Python tool root from env, image defaults, or local working directory.
TOOLS_ROOT = os.getenv("TOOLHUB_PYTHON_ROOT", "/opt/toolhub")
if not os.path.isdir(TOOLS_ROOT) and os.path.isdir("/workspace"):
    TOOLS_ROOT = "/workspace"
if not os.path.isdir(TOOLS_ROOT):
    TOOLS_ROOT = os.getcwd()
if TOOLS_ROOT not in sys.path:
    sys.path.append(TOOLS_ROOT)

try:
    from tools import TOOLS
except Exception as exc:  # noqa: BLE001
    TOOLS = {}
    logger.exception("Failed to import tool registry", exc_info=exc)

MANIFEST_TOOLS_DIR = os.getenv("TOOLHUB_MANIFEST_TOOLS_DIR", os.path.join(TOOLS_ROOT, "tools"))
SCRIPT_TOOLS_DIR = os.getenv("TOOLHUB_SCRIPT_TOOLS_DIR", "/scripts")


def load_manifest_tools():
    """Load manifest-defined CLI tools from TOOLHUB_MANIFEST_TOOLS_DIR."""
    manifest_tools = {}
    if not os.path.isdir(MANIFEST_TOOLS_DIR):
        logger.info(f"Manifest tool directory not found: {MANIFEST_TOOLS_DIR}")
        return manifest_tools

    for entry in sorted(os.listdir(MANIFEST_TOOLS_DIR)):
        tool_dir = os.path.join(MANIFEST_TOOLS_DIR, entry)
        if not os.path.isdir(tool_dir):
            continue

        manifest_path = os.path.join(tool_dir, "tool.json")
        if not os.path.isfile(manifest_path):
            continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Skipping invalid manifest '{manifest_path}': {exc}")
            continue

        tool_name = manifest.get("name")
        command = manifest.get("command")
        if not isinstance(tool_name, str) or not tool_name:
            logger.warning(f"Skipping manifest without valid name: {manifest_path}")
            continue
        if not isinstance(command, str) or not command:
            logger.warning(f"Skipping manifest without valid command: {manifest_path}")
            continue

        # Resolve command relative to its manifest directory when necessary.
        command_path = command if os.path.isabs(command) else os.path.normpath(os.path.join(tool_dir, command))
        if not os.path.isfile(command_path) or not os.access(command_path, os.X_OK):
            logger.warning(f"Skipping tool '{tool_name}' because command is not executable: {command_path}")
            continue

        manifest_tools[tool_name] = {
            "name": tool_name,
            "description": manifest.get("description", ""),
            "args": manifest.get("args", []),
            "command_path": command_path,
        }

    logger.info(f"Loaded {len(manifest_tools)} manifest tool(s) from {MANIFEST_TOOLS_DIR}")
    return manifest_tools


# Load manifests once at startup; runtime requests only execute already discovered tools.
MANIFEST_TOOLS = load_manifest_tools()


def _normalise_tool_token(value):
    """Normalise tool identifiers to a lowercase underscore format."""
    return str(value).strip().lower().replace("-", "_")


def _flag_name(key):
    """Convert payload keys into CLI flag names."""
    return str(key).strip().replace("_", "-")


def _resolve_script_tools_dir():
    """Resolve script directory for container and local-dev execution contexts."""
    preferred = Path(SCRIPT_TOOLS_DIR)
    if preferred.is_dir():
        return preferred
    fallback = Path.cwd() / "scripts"
    if fallback.is_dir():
        return fallback
    return preferred


def load_script_tools():
    """Load executable script tools from the script directory."""
    script_tools = {}
    base_dir = _resolve_script_tools_dir()
    if not base_dir.is_dir():
        logger.info(f"Script tool directory not found: {base_dir}")
        return script_tools

    for entry in sorted(base_dir.iterdir(), key=lambda item: item.name):
        if not entry.is_file():
            continue
        if not os.access(entry, os.X_OK):
            continue
        if entry.suffix not in (".sh", ".py"):
            continue
        if entry.name == "webhook.py":
            continue

        stem_token = _normalise_tool_token(entry.stem)
        extension_prefix = "sh" if entry.suffix == ".sh" else "py"
        canonical = f"{extension_prefix}_{stem_token}"

        script_tools[canonical] = {
            "name": canonical,
            "path": str(entry),
            "kind": extension_prefix,
        }
        # Keep filename aliases for more ergonomic webhook calls.
        script_tools[_normalise_tool_token(entry.name)] = script_tools[canonical]
        script_tools[stem_token] = script_tools[canonical]

    logger.info(f"Loaded {len(script_tools)} script tool alias(es) from {base_dir}")
    return script_tools


# Load script tools once at startup; webhook requests only execute discovered scripts.
SCRIPT_TOOLS = load_script_tools()


def build_manifest_args(request_data, manifest):
    """Build positional args for a manifest tool from args[] or payload fields."""
    # Accept legacy 'args' for direct positional forwarding.
    raw_args = request_data.get("args")
    if raw_args is not None:
        if not isinstance(raw_args, list):
            raise ValueError("'args' must be an array when provided.")
        return [str(item) for item in raw_args]

    # Accept structured payload object and map values by manifest arg order.
    payload = request_data.get("payload")
    if payload is not None and not isinstance(payload, dict):
        raise ValueError("'payload' must be an object when provided.")

    # Also allow top-level arg keys as convenience for simple webhook clients.
    payload_map = payload if isinstance(payload, dict) else request_data
    arg_defs = manifest.get("args", []) if isinstance(manifest.get("args"), list) else []
    if not arg_defs:
        return []

    resolved_args = []
    for arg_def in arg_defs:
        arg_name = arg_def.get("name") if isinstance(arg_def, dict) else None
        required = arg_def.get("required", True) if isinstance(arg_def, dict) else True
        if not arg_name:
            continue
        value = payload_map.get(arg_name)
        if value is None:
            if required:
                raise ValueError(f"Missing required argument '{arg_name}'.")
            continue
        resolved_args.append(str(value))

    return resolved_args


def execute_manifest_tool(tool_name, manifest, request_data):
    """Execute a manifest CLI tool and normalize stdout into JSON when possible."""
    command_path = manifest["command_path"]
    args = build_manifest_args(request_data, manifest)
    cmd = [command_path, *args]
    logger.info(f"Executing manifest tool '{tool_name}': {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    except subprocess.TimeoutExpired as exc:
        logger.exception(f"Manifest tool timeout: {tool_name}")
        return jsonify({"status": "error", "tool": tool_name, "error": {"type": "TimeoutExpired", "message": str(exc)}}), 504

    stdout_text = (result.stdout or "").strip()
    stderr_text = (result.stderr or "").strip()

    # Parse JSON output when tool scripts return structured payloads.
    parsed_stdout = None
    if stdout_text:
        try:
            parsed_stdout = json.loads(stdout_text)
        except Exception:  # noqa: BLE001
            parsed_stdout = None

    if result.returncode != 0:
        error_payload = {
            "status": "error",
            "tool": tool_name,
            "exit_code": result.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
        }
        # Preserve structured script errors when available.
        if isinstance(parsed_stdout, dict):
            error_payload["result"] = parsed_stdout
        return jsonify(error_payload), 400

    # Return structured script result directly when possible.
    if isinstance(parsed_stdout, dict):
        return jsonify(parsed_stdout), 200

    return jsonify({"status": "ok", "tool": tool_name, "stdout": stdout_text, "stderr": stderr_text}), 200


def build_script_args(request_data):
    """Build script arguments from args[] or payload key/value flags."""
    raw_args = request_data.get("args")
    if raw_args is not None:
        if not isinstance(raw_args, list):
            raise ValueError("'args' must be an array when provided.")
        return [str(item) for item in raw_args]

    payload = request_data.get("payload")
    if payload is None:
        # Allow top-level fields for lightweight clients that skip nested payload objects.
        payload = {
            key: value
            for key, value in request_data.items()
            if key not in {"tool", "payload", "args"}
        }
    elif not isinstance(payload, dict):
        raise ValueError("'payload' must be an object when provided.")

    if not isinstance(payload, dict):
        return []

    args = []
    for key, value in payload.items():
        if value is None:
            continue
        flag = f"--{_flag_name(key)}"
        if isinstance(value, bool):
            if value:
                args.append(flag)
            continue
        # Preserve nested payload objects by forwarding valid JSON strings.
        if isinstance(value, dict):
            args.extend([flag, json.dumps(value, ensure_ascii=False)])
            continue
        if isinstance(value, list):
            # Forward primitive lists as repeated flags; fallback to JSON for complex members.
            if any(isinstance(item, (dict, list)) for item in value):
                args.extend([flag, json.dumps(value, ensure_ascii=False)])
                continue
            for item in value:
                if item is None:
                    continue
                args.extend([flag, str(item)])
            continue
        args.extend([flag, str(value)])
    return args


def execute_script_tool(tool_name, tool, request_data):
    """Execute discovered scripts with webhook-provided args or payload."""
    args = build_script_args(request_data)
    script_path = tool["path"]

    if tool["kind"] == "py":
        cmd = ["python3", script_path, *args]
    else:
        cmd = ["bash", script_path, *args]

    logger.info(f"Executing script tool '{tool_name}': {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
    except subprocess.TimeoutExpired as exc:
        logger.exception(f"Script tool timeout: {tool_name}")
        return jsonify({"status": "error", "tool": tool_name, "error": {"type": "TimeoutExpired", "message": str(exc)}}), 504

    stdout_text = (result.stdout or "").strip()
    stderr_text = (result.stderr or "").strip()

    parsed_stdout = None
    if stdout_text:
        try:
            parsed_stdout = json.loads(stdout_text)
        except Exception:  # noqa: BLE001
            parsed_stdout = None

    if result.returncode != 0:
        return jsonify(
            {
                "status": "error",
                "tool": tool_name,
                "exit_code": result.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "result": parsed_stdout if isinstance(parsed_stdout, dict) else None,
            }
        ), 400

    if isinstance(parsed_stdout, dict):
        return jsonify(parsed_stdout), 200

    return jsonify({"status": "ok", "tool": tool_name, "stdout": stdout_text, "stderr": stderr_text}), 200


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
            "/run":        "POST JSON {tool, payload|args} → run Python, manifest, or script tool"
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
    if not isinstance(payload, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    tool_name = payload.get("tool") if isinstance(payload, dict) else None
    tool_payload = payload.get("payload") if isinstance(payload, dict) else {}

    if not tool_name:
        return jsonify({"error": "tool is required"}), 400

    # Dispatch Python in-process handlers first.
    if tool_name in TOOLS:
        handler = TOOLS[tool_name].get("handler")
        if handler is None:
            logger.error(f"Handler missing for tool: {tool_name}")
            return jsonify({"error": f"Tool '{tool_name}' is not configured"}), 500

        logger.info(
            f"Dispatching Python tool '{tool_name}' with payload keys: {list(tool_payload.keys()) if isinstance(tool_payload, dict) else 'n/a'}"
        )
        try:
            result = handler(tool_payload if isinstance(tool_payload, dict) else {})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Python tool execution failed", exc_info=exc)
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

    # Fallback to manifest-based external CLI tools.
    if tool_name in MANIFEST_TOOLS:
        try:
            return execute_manifest_tool(tool_name, MANIFEST_TOOLS[tool_name], payload)
        except ValueError as exc:
            logger.warning(f"Invalid manifest tool request for '{tool_name}': {exc}")
            return jsonify({"status": "error", "tool": tool_name, "error": {"type": "ValidationError", "message": str(exc)}}), 400
        except Exception as exc:  # noqa: BLE001
            logger.exception("Manifest tool execution failed", exc_info=exc)
            return jsonify({"status": "error", "tool": tool_name, "error": {"type": exc.__class__.__name__, "message": str(exc)}}), 500

    normalised_tool_name = _normalise_tool_token(tool_name)
    if normalised_tool_name in SCRIPT_TOOLS:
        try:
            return execute_script_tool(normalised_tool_name, SCRIPT_TOOLS[normalised_tool_name], payload)
        except ValueError as exc:
            logger.warning(f"Invalid script tool request for '{tool_name}': {exc}")
            return jsonify({"status": "error", "tool": tool_name, "error": {"type": "ValidationError", "message": str(exc)}}), 400
        except Exception as exc:  # noqa: BLE001
            logger.exception("Script tool execution failed", exc_info=exc)
            return jsonify({"status": "error", "tool": tool_name, "error": {"type": exc.__class__.__name__, "message": str(exc)}}), 500

    logger.warning(f"Requested unknown tool: {tool_name}")
    return jsonify({
        "error": f"Unknown tool '{tool_name}'",
        "hint": "Use / (index) to inspect endpoints and ensure the tool exists in Python registry, manifest tools, or /scripts."
    }), 404


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
