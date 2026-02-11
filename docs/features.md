# Toolhub Feature Contract

This document lists the currently available Toolhub features, where they can be called, and exact invocation examples.

## Interfaces

- `SSH`: Direct shell invocation inside the Toolhub container (or via `docker exec`).
- `Webhook`: HTTP calls against `POST /audio-split` and `POST /run`.
- `MCP`: Tool invocation through the MCP sidecar.

## Feature Matrix

| Feature | SSH | Webhook | MCP | Notes |
|---|---|---|---|---|
| Healthcheck | - | `GET /test` | - | Returns `{"status":"ok"}`. |
| Audio split | `scripts/audio-split.sh` | `/audio-split` and `/run` script-dispatch | `sh_audio_split` | Requires input file under `/shared/audio/in` (or absolute path). |
| DOCX render | `scripts/docx-render.py` | `/run` tool: `docx-render` or `docx_render` | `py_docx_render` | Reads templates from `/data/templates`, writes to `/data/output`. |
| DOCX template fill | `scripts/docx-template-fill.py` | `/run` tool: `docx-template-fill` or `docx_template_fill` | `docx-template-fill.fill_docx_template`, `py_docx_template_fill` | Reads templates from `/templates`, writes to `/output`. |
| Wake-on-LAN | `scripts/wol-cli.sh` | `/run` tool: `wol-cli`, `wol_cli` | `sh_wol_cli`, `wol-cli` | Sends magic packet by MAC or configured device alias. |
| Cleanup | `scripts/cleanup.py` | `/run` tool: `cleanup` | `py_cleanup` | Supports safe preview with `--dry-run`. |
| Transcript | `scripts/transcript.py` | `/run` tool: `transcript` | `py_transcript` | Needs local `whisper` CLI backend. |

## Webhook Contracts

### 1) Healthcheck

```bash
curl -sS http://localhost:5656/test
```

### 2) Audio Split (`POST /audio-split`)

```bash
curl -sS -X POST http://localhost:5656/audio-split \
  -H 'Content-Type: application/json' \
  -d '{
    "filename": "e2e.wav",
    "mode": "fixed",
    "chunk_length": 1
  }'
```

### 3) Generic Tool Run (`POST /run`)

#### Cleanup (script tool)

```bash
curl -sS -X POST http://localhost:5656/run \
  -H 'Content-Type: application/json' \
  -d '{
    "tool": "cleanup",
    "dry_run": true
  }'
```

#### DOCX render (python registry tool)

```bash
curl -sS -X POST http://localhost:5656/run \
  -H 'Content-Type: application/json' \
  -d '{
    "tool": "docx-render",
    "payload": {
      "template": "e2e-render.docx",
      "output_name": "rendered-now.docx",
      "data": { "NAME": "Toolhub" }
    }
  }'
```

#### DOCX template fill (python registry tool)

```bash
curl -sS -X POST http://localhost:5656/run \
  -H 'Content-Type: application/json' \
  -d '{
    "tool": "docx-template-fill",
    "payload": {
      "template": "e2e-fill.docx",
      "output_filename": "filled-now.docx",
      "data": { "name": "Toolhub" }
    }
  }'
```

#### Wake-on-LAN (manifest or script alias)

```bash
curl -sS -X POST http://localhost:5656/run \
  -H 'Content-Type: application/json' \
  -d '{
    "tool": "wol-cli",
    "args": ["00:11:22:33:44:55"]
  }'
```

#### Transcript (backend required)

```bash
curl -sS -X POST http://localhost:5656/run \
  -H 'Content-Type: application/json' \
  -d '{
    "tool": "transcript",
    "payload": { "input": "meeting.m4a", "format": "json", "backend": "auto" }
  }'
```

## SSH Contracts

```bash
# Audio split
/scripts/audio-split.sh --mode fixed --chunk-length 600 --input /shared/audio/in/input.m4a --output /shared/audio/out/job-1

# DOCX render
/scripts/docx-render.py --template e2e-render.docx --output-name out.docx --data '{"NAME":"Toolhub"}'

# DOCX template fill
/scripts/docx-template-fill.py --template e2e-fill.docx --output-filename out.docx --data '{"name":"Toolhub"}'

# Wake-on-LAN
/scripts/wol-cli.sh 00:11:22:33:44:55

# Cleanup
/scripts/cleanup.py --dry-run

# Transcript
/scripts/transcript.py --input meeting.m4a --format json --backend auto
```

## MCP Contracts

The MCP server exposes script tools with normalized names (`sh_*`/`py_*`) and additional curated tools.

### Common examples (tool name + input JSON)

```json
{
  "tool": "sh_audio_split",
  "input": {
    "mode": "fixed",
    "chunk_length": 600,
    "input": "/shared/audio/in/input.m4a",
    "output": "/shared/audio/out/job-1"
  }
}
```

```json
{
  "tool": "py_cleanup",
  "input": {
    "dry_run": true
  }
}
```

```json
{
  "tool": "docx-template-fill.fill_docx_template",
  "input": {
    "template": "e2e-fill.docx",
    "output_filename": "filled-from-mcp.docx",
    "data": {
      "name": "Toolhub"
    }
  }
}
```

```json
{
  "tool": "run_script",
  "input": {
    "name": "sh_wol_cli",
    "args": ["00:11:22:33:44:55"]
  }
}
```

## Optional/Conditional MCP CLI Tools

The following are only registered when the binaries exist in the running image:

- `ffmpeg`, `sox`, `magick`, `tesseract`, `pdftotext`, `pdfinfo`, `jq`, `curl`, `exiftool`
- `syft`, `grype`, `trivy`, `nuclei` (typically not installed in the base image)

Additionally available when binaries are present:

- `ffprobe_info`
- `tesseract_ocr`
- `pdftotext_extract`
- `pdfinfo_read`
- `nuclei_safe` (guardrailed nuclei execution)
