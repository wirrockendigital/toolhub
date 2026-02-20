#!/usr/bin/env python3
"""
Toolhub Webhook Service

Exposes REST endpoints:
  GET  /             Service info & available routes
  GET/POST /test     Health check
  GET  /tools        Tool discovery catalog
  POST /n8n_audio_split  n8n-friendly upload + split endpoint
  POST /audio-ingest-split  Upload + split audio in one request
  GET  /audio-chunk/<job_id>/<filename>  Download generated chunk binary
  POST /audio-split  Split audio files from /shared/audio/in
  POST /run          Dispatch registered Toolhub tools (JSON-first)
  POST /run-file     Dispatch file-first Toolhub tools
  GET  /artifacts/<job_id>/<filename>  Download run-file artifacts

Logs all activity to /logs/webhook.log.
"""
from flask import Flask, request, jsonify, send_file
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
import re
import mimetypes

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
SHARED_ARTIFACTS_DIR = os.getenv("TOOLHUB_ARTIFACTS_DIR", "/shared/artifacts")


def _infer_command_kind(command_path):
    """Infer command execution mode from file extension."""
    suffix = Path(command_path).suffix.lower()
    if suffix == ".py":
        return "py"
    if suffix == ".sh":
        return "sh"
    return "bin"


def _manifest_command_runnable(command_path, command_kind):
    """Validate whether manifest command can be executed."""
    if not os.path.isfile(command_path):
        return False
    if command_kind in {"py", "sh"}:
        return True
    return os.access(command_path, os.X_OK)


def _resolve_manifest_command_path(tool_dir, command):
    """Resolve manifest command paths across container and local-dev layouts."""
    if os.path.isabs(command):
        candidates = [command]
        base_name = os.path.basename(command)
        # Fall back to common script roots when /scripts is not mounted in local dev.
        candidates.append(str(Path("/scripts") / base_name))
        candidates.append(str(Path.cwd() / "scripts" / base_name))
    else:
        candidates = [os.path.normpath(os.path.join(tool_dir, command))]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]


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

        # Resolve command path with local-dev fallback support.
        command_path = _resolve_manifest_command_path(tool_dir, command)
        command_kind = _infer_command_kind(command_path)
        if not _manifest_command_runnable(command_path, command_kind):
            logger.warning(f"Skipping tool '{tool_name}' because command is not runnable: {command_path}")
            continue

        try:
            timeout_seconds = int(manifest.get("timeout_seconds", 120))
        except Exception:  # noqa: BLE001
            timeout_seconds = 120

        manifest_tools[tool_name] = {
            "name": tool_name,
            "description": manifest.get("description", ""),
            "args": manifest.get("args", []),
            "command_path": command_path,
            "command_kind": command_kind,
            "io_mode": str(manifest.get("io_mode", "json")).strip().lower(),
            "n8n_alias": manifest.get("n8n_alias"),
            "output_artifacts": bool(manifest.get("output_artifacts", False)),
            "timeout_seconds": timeout_seconds,
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

SHARED_AUDIO_IN_DIR = "/shared/audio/in"
SHARED_AUDIO_OUT_DIR = "/shared/audio/out"
SAFE_JOB_ID_PATTERN = re.compile(r"^[a-f0-9-]{36}$")
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav"}
DEFAULT_INGEST_SOURCE = "ios-webhook"
DEFAULT_INGEST_LANGUAGE = "de"
N8N_TOOL_ALIASES = {
    "n8n_audio_cleanup": "cleanup",
    "n8n_audio_transcript_local": "transcript",
    "n8n_wol": "wol-cli",
    "n8n_docx_render": "docx-render",
    "n8n_docx_template_fill": "docx-template-fill",
    "n8n_audio_split_compat": "audio-split",
}
TOOL_ALIASES = dict(N8N_TOOL_ALIASES)
for manifest_name, manifest in MANIFEST_TOOLS.items():
    # Register explicit aliases from tool manifests.
    explicit_alias = manifest.get("n8n_alias")
    if isinstance(explicit_alias, str) and explicit_alias.strip():
        TOOL_ALIASES[_normalise_tool_token(explicit_alias)] = manifest_name
    # Register deterministic default aliases for n8n nodes.
    TOOL_ALIASES.setdefault(f"n8n_{_normalise_tool_token(manifest_name)}", manifest_name)


def parse_bool(value, default=False):
    """Parse boolean-like values from form/json payloads."""
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def resolve_requested_tool_name(tool_name):
    """Resolve n8n alias names to canonical Toolhub tool names."""
    normalized = _normalise_tool_token(tool_name)
    # Keep backward compatibility with static aliases and manifest-defined aliases.
    if normalized in TOOL_ALIASES:
        return TOOL_ALIASES[normalized]
    return tool_name


def parse_int(value, field_name, default=None):
    """Parse integer values with field-specific validation errors."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid {field_name}") from exc


def parse_float(value, field_name, default=None):
    """Parse float values with field-specific validation errors."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid {field_name}") from exc


def build_split_command(input_path, output_dir, mode, chunk_length, split_options):
    """Build audio split command arguments from validated options."""
    cmd = [
        "/scripts/audio-split.sh",
        "--mode",
        mode,
        "--chunk-length",
        str(chunk_length),
        "--input",
        input_path,
        "--output",
        output_dir,
    ]

    if mode == "silence":
        cmd += [
            "--silence-seek",
            str(split_options["silence_seek"]),
            "--silence-duration",
            str(split_options["silence_duration"]),
            "--silence-threshold",
            str(split_options["silence_threshold"]),
            "--padding",
            str(split_options["padding"]),
        ]

    if split_options["enhance_speech"]:
        cmd.append("--enhance-speech")
    elif split_options["enhance"]:
        cmd.append("--enhance")

    return cmd


def extract_sorted_chunk_files(output_dir):
    """List generated chunk files and sort by part index and file name."""
    files = [name for name in os.listdir(output_dir) if Path(name).suffix.lower() in ALLOWED_AUDIO_EXTENSIONS]
    if not files:
        return []

    def sort_key(file_name):
        match = re.search(r"part_(\d+)", file_name, flags=re.IGNORECASE)
        if match:
            return (int(match.group(1)), file_name)
        return (10**9, file_name)

    return sorted(files, key=sort_key)


def audio_mime_type(file_name):
    """Return response MIME type based on chunk file extension."""
    suffix = Path(file_name).suffix.lower()
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".m4a":
        return "audio/mp4"
    if suffix == ".wav":
        return "audio/wav"
    return "application/octet-stream"


def resolve_upload_filename(uploaded_file):
    """Validate upload filename and return a secure file name."""
    safe_filename = secure_filename(uploaded_file.filename or "")
    if not safe_filename:
        raise ValueError("Uploaded audio filename is empty")

    file_extension = Path(safe_filename).suffix.lower()
    if file_extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError("Unsupported audio file extension")
    return safe_filename


def resolve_recording_id(raw_recording_id):
    """Generate or sanitize recording identifiers used in file names."""
    requested_id = (raw_recording_id or "").strip()
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", requested_id) if requested_id else ""
    return sanitized or str(uuid.uuid4())


def resolve_ingest_meta(form_data, recording_id):
    """Resolve optional ingest metadata with deterministic defaults."""
    return {
        "title": (form_data.get("title", "").strip() or f"Audio Note {recording_id}"),
        "source": (form_data.get("source", "").strip() or DEFAULT_INGEST_SOURCE),
        "language": (form_data.get("language", "").strip() or DEFAULT_INGEST_LANGUAGE),
        "capturedAt": (form_data.get("capturedAt", "").strip() or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    }


def build_chunk_manifest(host_base, job_id, output_dir, chunk_files):
    """Build a stable chunk manifest sorted by numeric part index."""
    chunks = []
    for index, chunk_filename in enumerate(chunk_files, start=1):
        chunk_path = os.path.join(output_dir, chunk_filename)
        chunks.append(
            {
                "index": index,
                "filename": chunk_filename,
                "path": chunk_path,
                "downloadUrl": f"{host_base}/audio-chunk/{job_id}/{chunk_filename}",
                "mimeType": audio_mime_type(chunk_filename),
            }
        )
    return chunks


def execute_audio_split(input_path, mode, chunk_length, split_options):
    """Execute the split script and return job metadata and sorted chunk files."""
    job_id = str(uuid.uuid4())
    output_dir = f"{SHARED_AUDIO_OUT_DIR}/{job_id}"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")

    cmd = build_split_command(input_path, output_dir, mode, chunk_length, split_options)

    logger.debug("Executing split script with command arguments:")
    for index, arg in enumerate(cmd):
        logger.debug(f"  cmd[{index}] = {arg}")

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
    duration = time.time() - start

    logger.debug(f"Split script stdout: {result.stdout}")
    logger.debug(f"Split script stderr: {result.stderr}")
    logger.info(f"Split script returned with exit code {result.returncode} for job {job_id} in {duration:.3f}s")

    chunk_files = extract_sorted_chunk_files(output_dir)
    if not chunk_files:
        raise RuntimeError("No audio chunks were generated")

    return job_id, output_dir, chunk_files


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
        style = arg_def.get("style", "positional") if isinstance(arg_def, dict) else "positional"
        flag_name = arg_def.get("flag") if isinstance(arg_def, dict) else None
        if not arg_name:
            continue
        value = payload_map.get(arg_name)
        if value is None:
            if required:
                raise ValueError(f"Missing required argument '{arg_name}'.")
            continue
        if style == "flag":
            flag = str(flag_name).strip() if isinstance(flag_name, str) and flag_name.strip() else f"--{_flag_name(arg_name)}"
            # Allow boolean flags to be passed without explicit value.
            if isinstance(value, bool):
                if value:
                    resolved_args.append(flag)
                continue
            if isinstance(value, list):
                for item in value:
                    resolved_args.extend([flag, str(item)])
                continue
            resolved_args.extend([flag, str(value)])
            continue
        resolved_args.append(str(value))

    return resolved_args


def _parse_stdout_payload(stdout_text):
    """Parse JSON payload from command stdout when available."""
    if not stdout_text:
        return None
    try:
        parsed = json.loads(stdout_text)
    except Exception:  # noqa: BLE001
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_manifest_command(manifest, args):
    """Build runnable command for manifest tools based on command kind."""
    command_path = manifest["command_path"]
    command_kind = manifest.get("command_kind", "bin")
    if command_kind == "py":
        return ["python3", command_path, *args]
    if command_kind == "sh":
        return ["bash", command_path, *args]
    return [command_path, *args]


def _run_external_tool(tool_name, cmd, timeout_seconds):
    """Execute a subprocess tool and normalize result payload."""
    logger.info(f"Executing tool '{tool_name}': {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        logger.exception(f"Tool timeout: {tool_name}")
        return {
            "status": "error",
            "tool": tool_name,
            "error": {"type": "TimeoutExpired", "message": str(exc)},
        }, 504

    stdout_text = (result.stdout or "").strip()
    stderr_text = (result.stderr or "").strip()
    parsed_stdout = _parse_stdout_payload(stdout_text)

    if result.returncode != 0:
        payload = {
            "status": "error",
            "tool": tool_name,
            "exit_code": result.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
        }
        # Preserve structured script errors when available.
        if parsed_stdout is not None:
            payload["result"] = parsed_stdout
        return payload, 400

    if parsed_stdout is not None:
        return parsed_stdout, 200

    return {"status": "ok", "tool": tool_name, "stdout": stdout_text, "stderr": stderr_text}, 200


def execute_manifest_tool(tool_name, manifest, request_data):
    """Execute a manifest CLI tool and return normalized payload tuple."""
    args = build_manifest_args(request_data, manifest)
    cmd = _build_manifest_command(manifest, args)
    timeout_seconds = int(manifest.get("timeout_seconds", 120))
    return _run_external_tool(tool_name, cmd, timeout_seconds)


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

    return _run_external_tool(tool_name, cmd, 600)


def execute_python_tool(tool_name, tool_payload):
    """Execute in-process Python registry tools with normalized error handling."""
    handler = TOOLS[tool_name].get("handler")
    if handler is None:
        logger.error(f"Handler missing for tool: {tool_name}")
        return {"status": "error", "error": {"type": "ConfigError", "message": f"Tool '{tool_name}' is not configured"}}, 500

    logger.info(
        f"Dispatching Python tool '{tool_name}' with payload keys: {list(tool_payload.keys()) if isinstance(tool_payload, dict) else 'n/a'}"
    )
    try:
        result = handler(tool_payload if isinstance(tool_payload, dict) else {})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Python tool execution failed", exc_info=exc)
        return {
            "status": "error",
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
        }, 500

    status_code = 200 if isinstance(result, dict) and result.get("status") == "ok" else 400
    if isinstance(result, dict):
        return result, status_code
    return {"status": "ok", "result": result}, status_code


def dispatch_tool_payload(request_payload, requested_tool_name):
    """Dispatch payload to python, manifest, or script tools."""
    tool_payload = request_payload.get("payload") if isinstance(request_payload, dict) else {}
    tool_name = resolve_requested_tool_name(requested_tool_name)
    logger.info(f"Resolved tool request: requested_tool='{requested_tool_name}', resolved_tool='{tool_name}'")

    if tool_name in TOOLS:
        return execute_python_tool(tool_name, tool_payload if isinstance(tool_payload, dict) else {})

    if tool_name in MANIFEST_TOOLS:
        return execute_manifest_tool(tool_name, MANIFEST_TOOLS[tool_name], request_payload)

    normalised_tool_name = _normalise_tool_token(tool_name)
    if normalised_tool_name in SCRIPT_TOOLS:
        return execute_script_tool(normalised_tool_name, SCRIPT_TOOLS[normalised_tool_name], request_payload)

    logger.warning(f"Requested unknown tool: {tool_name}")
    return {
        "status": "error",
        "error": f"Unknown tool '{requested_tool_name}'",
        "resolved_tool": tool_name,
        "hint": "Use /tools to inspect available tool names and aliases.",
    }, 404


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


def parse_split_options_from_payload(payload, *, defaults):
    """Parse split-related options from payload/form values."""
    mode = (payload.get("mode") or defaults["mode"]).strip().lower()
    if mode not in {"fixed", "silence"}:
        raise ValueError("mode must be 'fixed' or 'silence'")

    chunk_length = parse_int(payload.get("chunk_length"), "chunk_length", defaults["chunk_length"])
    if chunk_length is None or chunk_length <= 0:
        raise ValueError("Invalid chunk_length")

    split_options = {
        "enhance": parse_bool(payload.get("enhance"), defaults["enhance"]),
        "enhance_speech": parse_bool(payload.get("enhance_speech"), defaults["enhance_speech"]),
        "silence_seek": 0,
        "silence_duration": 0.0,
        "silence_threshold": 0.0,
        "padding": 0.0,
    }
    if split_options["enhance"] and split_options["enhance_speech"]:
        raise ValueError("Cannot use both enhance and enhance_speech simultaneously")

    if mode == "silence":
        split_options["silence_seek"] = parse_int(payload.get("silence_seek"), "silence_seek", defaults["silence_seek"])
        split_options["silence_duration"] = parse_float(payload.get("silence_duration"), "silence_duration", defaults["silence_duration"])
        split_options["silence_threshold"] = parse_float(payload.get("silence_threshold"), "silence_threshold", defaults["silence_threshold"])
        split_options["padding"] = parse_float(payload.get("padding"), "padding", defaults["padding"])

        if split_options["silence_seek"] is None or split_options["silence_duration"] is None:
            raise ValueError("silence_seek and silence_duration are required for silence mode")

    return mode, chunk_length, split_options

@app.route("/", methods=["GET"])
def index():
    """Return service info with available routes."""
    return jsonify({
        "service": "Toolhub Webhook",
        "endpoints": {
            "/":           "This help message",
            "/test":       "GET or POST health-check",
            "/tools":      "GET discovered tools and aliases",
            "/n8n_audio_split": "POST multipart/form-data {audio,...} → n8n-first upload + split + chunk manifest",
            "/audio-ingest-split": "POST multipart/form-data {audio,...} → ingest + split + chunk manifest",
            "/audio-chunk/<job_id>/<filename>": "GET chunk binary from /shared/audio/out/<job_id>",
            "/audio-split":"POST JSON {filename, mode, …} → split audio from /shared",
            "/run":        "POST JSON {tool, payload|args} → run JSON/CLI tools",
            "/run-file":   "POST multipart/form-data {tool,file,payload?} → run file-first tools",
            "/artifacts/<job_id>/<filename>": "GET artifact binary from /shared/artifacts/<job_id>",
        }
    }), 200


# --- TEST ENDPOINT ---
@app.route("/test", methods=["GET", "POST"])
def test():
    if request.method == "GET":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(force=True)
    return jsonify({"status": "ok", "message": "Toolhub webhook service is running", "received": data})


def _collect_tool_catalog():
    """Build a serializable list of discovered tools across all backends."""
    catalog = []

    # Keep Python registry tools visible even when they do not expose argument schemas.
    for name, config in sorted(TOOLS.items()):
        catalog.append(
            {
                "name": name,
                "kind": "python",
                "description": config.get("description", ""),
                "io_mode": "json",
                "n8n_alias": TOOL_ALIASES.get(f"n8n_{_normalise_tool_token(name)}", f"n8n_{_normalise_tool_token(name)}"),
            }
        )

    # Include manifest tools because they carry explicit argument contracts.
    for name, manifest in sorted(MANIFEST_TOOLS.items()):
        catalog.append(
            {
                "name": name,
                "kind": "manifest",
                "description": manifest.get("description", ""),
                "args": manifest.get("args", []),
                "io_mode": manifest.get("io_mode", "json"),
                "n8n_alias": manifest.get("n8n_alias") or f"n8n_{_normalise_tool_token(name)}",
                "output_artifacts": bool(manifest.get("output_artifacts", False)),
            }
        )

    # Include canonical script names only to avoid duplicate alias rows.
    seen_script_names = set()
    for key, script in sorted(SCRIPT_TOOLS.items()):
        canonical = script.get("name")
        if key != canonical or canonical in seen_script_names:
            continue
        seen_script_names.add(canonical)
        catalog.append(
            {
                "name": canonical,
                "kind": "script",
                "description": f"Discovered script tool from {script.get('path')}",
                "io_mode": "json",
            }
        )

    return catalog


def _artifact_mime_type(file_name):
    """Resolve best-effort MIME type for generic artifacts."""
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or "application/octet-stream"


def _list_artifacts(job_id, output_dir):
    """Collect generated artifact metadata for run-file responses."""
    host_base = request.host_url.rstrip("/")
    artifacts = []
    if not os.path.isdir(output_dir):
        return artifacts

    for root, _dirs, files in os.walk(output_dir):
        for file_name in sorted(files):
            abs_path = os.path.join(root, file_name)
            if not os.path.isfile(abs_path):
                continue
            rel_path = os.path.relpath(abs_path, output_dir).replace(os.sep, "/")
            artifacts.append(
                {
                    "filename": rel_path,
                    "path": abs_path,
                    "size": os.path.getsize(abs_path),
                    "mimeType": _artifact_mime_type(rel_path),
                    "downloadUrl": f"{host_base}/artifacts/{job_id}/{rel_path}",
                }
            )
    return artifacts


@app.route("/tools", methods=["GET"])
def tools():
    """Expose discovered tool metadata for API clients and n8n nodes."""
    return jsonify({"status": "ok", "aliases": TOOL_ALIASES, "tools": _collect_tool_catalog()}), 200


# --- GENERIC TOOL DISPATCH ---
@app.route("/run", methods=["POST"])
def run_tool():
    payload = request.get_json(force=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    requested_tool_name = payload.get("tool")
    if not requested_tool_name:
        return jsonify({"error": "tool is required"}), 400

    try:
        result_payload, status_code = dispatch_tool_payload(payload, requested_tool_name)
    except ValueError as exc:
        logger.warning("Validation error while dispatching tool", exc_info=exc)
        return jsonify({"status": "error", "error": {"type": "ValidationError", "message": str(exc)}}), 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected dispatch error", exc_info=exc)
        return jsonify({"status": "error", "error": {"type": exc.__class__.__name__, "message": str(exc)}}), 500

    return jsonify(result_payload), status_code


@app.route("/run-file", methods=["POST"])
def run_file_tool():
    """Dispatch file-first tool calls with artifact tracking."""
    requested_tool_name = (request.form.get("tool") or "").strip()
    if not requested_tool_name:
        return jsonify({"status": "error", "error": {"type": "ValidationError", "message": "Missing form field 'tool'"}}), 400

    if "file" not in request.files:
        return jsonify({"status": "error", "error": {"type": "ValidationError", "message": "Missing multipart file field 'file'"}}), 400

    payload_field = (request.form.get("payload") or "").strip()
    payload_obj = {}
    if payload_field:
        try:
            decoded = json.loads(payload_field)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "error", "error": {"type": "ValidationError", "message": f"Invalid payload JSON: {exc}"}}), 400
        if not isinstance(decoded, dict):
            return jsonify({"status": "error", "error": {"type": "ValidationError", "message": "payload must decode to a JSON object"}}), 400
        payload_obj = decoded

    # Allow simple form fields in addition to the JSON payload field.
    for key, value in request.form.items():
        if key in {"tool", "payload"}:
            continue
        payload_obj.setdefault(key, value)

    upload_file = request.files["file"]
    safe_name = secure_filename(upload_file.filename or "")
    if not safe_name:
        safe_name = "input.bin"

    # Store each run-file request in its own artifact directory.
    job_id = str(uuid.uuid4())
    output_dir = os.path.join(SHARED_ARTIFACTS_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)

    input_path = os.path.join(output_dir, f"input_{safe_name}")
    upload_file.save(input_path)

    # Inject deterministic defaults so wrappers can consume paths without boilerplate.
    payload_obj.setdefault("input_path", input_path)
    payload_obj.setdefault("output_dir", output_dir)
    payload_obj.setdefault("input_filename", safe_name)

    dispatch_request = {"tool": requested_tool_name, "payload": payload_obj}
    try:
        tool_result, status_code = dispatch_tool_payload(dispatch_request, requested_tool_name)
    except ValueError as exc:
        logger.warning("Validation error while dispatching file tool", exc_info=exc)
        tool_result = {"status": "error", "error": {"type": "ValidationError", "message": str(exc)}}
        status_code = 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected file dispatch error", exc_info=exc)
        tool_result = {"status": "error", "error": {"type": exc.__class__.__name__, "message": str(exc)}}
        status_code = 500

    artifacts = _list_artifacts(job_id, output_dir)
    # Hide the uploaded source file from artifact output by default.
    artifacts = [artifact for artifact in artifacts if artifact.get("path") != input_path]
    response_payload = {
        "status": "ok" if status_code < 400 else "error",
        "requested_tool": requested_tool_name,
        "resolved_tool": resolve_requested_tool_name(requested_tool_name),
        "job_id": job_id,
        "input": {"filename": safe_name, "path": input_path},
        "result": tool_result,
        "artifacts": artifacts,
    }
    return jsonify(response_payload), status_code


@app.route("/artifacts/<job_id>/<path:filename>", methods=["GET"])
def artifact_download(job_id, filename):
    """Download generated artifacts from run-file jobs."""
    if not SAFE_JOB_ID_PATTERN.match(job_id):
        return jsonify({"error": "ValidationError", "message": "Invalid job_id format"}), 400

    raw_name = (filename or "").strip()
    if not raw_name:
        return jsonify({"error": "ValidationError", "message": "Invalid artifact filename"}), 400

    # Keep nested artifact paths but sanitize every path segment.
    path_obj = Path(raw_name)
    if path_obj.is_absolute() or ".." in path_obj.parts:
        return jsonify({"error": "ValidationError", "message": "Invalid artifact path"}), 400

    safe_parts = [secure_filename(part) for part in path_obj.parts if part not in {"", "."}]
    if not safe_parts or any(not part for part in safe_parts):
        return jsonify({"error": "ValidationError", "message": "Invalid artifact filename"}), 400
    safe_name = "/".join(safe_parts)

    job_root = os.path.realpath(os.path.join(SHARED_ARTIFACTS_DIR, job_id))
    target_path = os.path.realpath(os.path.join(job_root, safe_name))
    if not target_path.startswith(job_root + os.sep):
        return jsonify({"error": "ValidationError", "message": "Invalid artifact path"}), 400

    if not os.path.isfile(target_path):
        return jsonify({"error": "NotFound", "message": "Artifact file not found"}), 404

    return send_file(
        target_path,
        mimetype=_artifact_mime_type(safe_name),
        as_attachment=False,
        download_name=safe_name,
    )


def handle_multipart_audio_split(endpoint_label):
    """Handle multipart upload + split and return a normalized chunk manifest."""
    # Validate multipart payload and mandatory binary input for upload-first APIs.
    if "audio" not in request.files:
        return jsonify({"error": "ValidationError", "message": "Missing multipart file field 'audio'"}), 400

    audio_file = request.files["audio"]
    try:
        original_filename = resolve_upload_filename(audio_file)
    except ValueError as exc:
        return jsonify({"error": "ValidationError", "message": str(exc)}), 400

    # Resolve recording and metadata defaults before storing and splitting.
    recording_id = resolve_recording_id(request.form.get("recordingId"))
    ingest_meta = resolve_ingest_meta(request.form, recording_id)

    # Parse split settings before persisting files to fail early on invalid options.
    try:
        mode, chunk_length, split_options = parse_split_options_from_payload(
            request.form,
            defaults={
                "mode": "fixed",
                "chunk_length": 600,
                "enhance": False,
                "enhance_speech": True,
                "silence_seek": 60,
                "silence_duration": 0.5,
                "silence_threshold": -30.0,
                "padding": 0.0,
            },
        )
    except ValueError as exc:
        return jsonify({"error": "ValidationError", "message": str(exc)}), 400

    # Log split parameters so n8n execution traces remain auditable.
    logger.info(
        "Split request accepted: endpoint=%s, recording_id=%s, mode=%s, chunk_length=%s, enhance=%s, enhance_speech=%s",
        endpoint_label,
        recording_id,
        mode,
        chunk_length,
        split_options["enhance"],
        split_options["enhance_speech"],
    )

    # Persist uploaded file into shared ingest directory.
    os.makedirs(SHARED_AUDIO_IN_DIR, exist_ok=True)
    ingest_filename = f"{recording_id}-{original_filename}"
    ingest_path = os.path.join(SHARED_AUDIO_IN_DIR, ingest_filename)
    audio_file.save(ingest_path)
    logger.info(f"Stored multipart upload at: {ingest_path}")

    try:
        job_id, output_dir, chunk_files = execute_audio_split(ingest_path, mode, chunk_length, split_options)
    except subprocess.TimeoutExpired as exc:
        return jsonify({"error": "TimeoutError", "message": "Audio split timed out", "detail": str(exc)}), 504
    except subprocess.CalledProcessError as exc:
        logger.exception(f"Error running split script for {endpoint_label}")
        return jsonify(
            {
                "error": "SplitFailed",
                "message": "Audio split failed",
                "detail": {
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                },
            }
        ), 500
    except RuntimeError as exc:
        return jsonify({"error": "SplitFailed", "message": str(exc)}), 500

    host_base = request.host_url.rstrip("/")
    chunks = build_chunk_manifest(host_base, job_id, output_dir, chunk_files)

    return jsonify(
        {
            "recordingId": recording_id,
            "jobId": job_id,
            "ingest": {
                "filename": ingest_filename,
                "path": ingest_path,
            },
            "meta": ingest_meta,
            "chunks": chunks,
        }
    ), 200


# --- N8N AUDIO SPLIT ENDPOINT ---
@app.route("/n8n_audio_split", methods=["POST"])
def n8n_audio_split():
    # This endpoint is the n8n-first alias for upload + split behavior.
    return handle_multipart_audio_split("n8n_audio_split")


# --- AUDIO INGEST + SPLIT ENDPOINT ---
@app.route("/audio-ingest-split", methods=["POST"])
def audio_ingest_split():
    # This endpoint remains for backward compatibility.
    return handle_multipart_audio_split("audio-ingest-split")


# --- CHUNK DOWNLOAD ENDPOINT ---
@app.route("/audio-chunk/<job_id>/<path:filename>", methods=["GET"])
def audio_chunk(job_id, filename):
    # Validate job identifiers and file names before resolving file paths.
    if not SAFE_JOB_ID_PATTERN.match(job_id):
        return jsonify({"error": "ValidationError", "message": "Invalid job_id format"}), 400

    safe_name = secure_filename(filename or "")
    if not safe_name or safe_name != filename:
        return jsonify({"error": "ValidationError", "message": "Invalid filename"}), 400

    if Path(safe_name).suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({"error": "ValidationError", "message": "Unsupported chunk file extension"}), 400

    output_dir = os.path.realpath(os.path.join(SHARED_AUDIO_OUT_DIR, job_id))
    chunk_path = os.path.realpath(os.path.join(output_dir, safe_name))
    if not chunk_path.startswith(output_dir + os.sep):
        return jsonify({"error": "ValidationError", "message": "Invalid chunk path"}), 400

    if not os.path.isfile(chunk_path):
        return jsonify({"error": "NotFound", "message": "Chunk file not found"}), 404

    return send_file(
        chunk_path,
        mimetype=audio_mime_type(safe_name),
        as_attachment=False,
        download_name=safe_name,
    )


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
