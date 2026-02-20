# AGENTS.md

## Overview

This file documents the responsibilities and capabilities of automated agents or scripts used within the Toolhub project.

## Agents

### 1. audio-split.sh
- **Location:** `/scripts/audio-split.sh`
- **Purpose:** Splits audio files into fixed-length or silence-based chunks.
- **Modes:** `fixed`, `silence`
- **Parameters:**
  - `--mode`: Defines split mode.
  - `--chunk-length`: Duration of each chunk in seconds.
  - `--input`: Path to the input file.
  - `--output`: Output directory (optional).
  - `--silence-seek`, `--silence-duration`, `--silence-threshold`: Silence detection parameters.
  - `--padding`: Optional trim before split point.
  - `--enhance`, `--enhance-speech`: Optional filters for audio enhancement.
- **Logging:** Logs all activity to `/logs/audio-split.log`.

### 2. webhook.py
- **Location:** `/scripts/webhook.py`
- **Purpose:** Exposes orchestration endpoints (`/audio-split`, `/run`) for Toolhub scripts and tools.
- **Methods:** `GET`, `POST`
- **Input:** JSON payloads for `/audio-split` and `/run`.
- **Output:** JSON responses with execution metadata, output paths, and error details.
- **Logging:** All events and errors go to `/logs/webhook.log`.

### 3. transcript.py
- **Location:** `/scripts/transcript.py`
- **Purpose:** Transcribes audio using local Whisper CLI backend.
- **Modes/Backends:** `auto`, `whisper-cli`
- **Parameters:**
  - `--input`, `--output`, `--format`
  - `--backend`, `--language`, `--model`
- **Logging:** Logs all activity to `/logs/transcript.log` (configurable).

### 4. cleanup.py
- **Location:** `/scripts/cleanup.py`
- **Purpose:** Rotates large log files and removes stale temporary artifacts.
- **Parameters:**
  - `--logs-dir`, `--tmp-dir`
  - `--max-log-size-mb`, `--max-log-backups`
  - `--tmp-max-age-hours`, `--tmp-prefixes`, `--dry-run`
- **Logging:** Logs all activity to `/logs/cleanup.log` (configurable).

### 5. docx-render.py
- **Location:** `/scripts/docx-render.py`
- **Purpose:** CLI wrapper to expose `tools.docx_render.handler` for SSH/MCP/webhook script dispatch.
- **Parameters:**
  - `--payload` or `--payload-file`
- **Logging:** Delegates rendering logs to `/logs/docx-render.log` via underlying tool.

### 6. docx-template-fill.py
- **Location:** `/scripts/docx-template-fill.py`
- **Purpose:** CLI wrapper for `mcp_tools.docx_template_fill.fill_docx_template`.
- **Parameters:**
  - `--payload` or `--payload-file`
- **Logging:** Uses `/logs/docx-template-fill.log` via underlying module settings.

### 7. wol-cli.sh
- **Location:** `/scripts/wol-cli.sh`
- **Purpose:** Wrapper that delegates to `tools/wol-cli/wol-cli.sh` so WOL is reachable through `/scripts`.
- **Parameters:**
  - Positional target argument (MAC address or mapped device name)
- **Logging:** Returns JSON to caller; errors are captured by caller logs (`webhook.log`/MCP output).

### 8. Wave Tool Scripts (Document/Media/Utility)
- **Location:** `/scripts/*.py`
- **Purpose:** Additional file-first and JSON-first tools that are exposed uniformly via webhook (`/run`, `/run-file`), MCP discovery, and n8n community nodes.
- **Included scripts:**
  - Document/PDF/OCR: `pdf-extract-text.py`, `pdf-info-read.py`, `ocr-image.py`, `html-to-markdown.py`, `markdown-to-html.py`, `document-convert.py`, `xlsx-read.py`
  - Media/Image/Data: `image-convert.py`, `gif-optimize.py`, `image-metadata.py`, `audio-convert.py`, `json-transform.py`, `yaml-transform.py`, `array-stats.py`
  - Utility/Network/Git: `http-fetch.py`, `download-aria2.py`, `download-wget.py`, `curl-request.py`, `archive-unzip.py`, `tree-list.py`, `calc-bc.py`, `git-ops.py`, `watch-path.py`
- **Parameters:** Each script accepts CLI flags (`--input-path`, `--output-dir`, etc.) documented in MCP metadata blocks and `tools/*/tool.json`.
- **Logging/Output:** Scripts emit compact JSON on stdout; webhook and MCP return this output directly and expose generated files through artifact paths.

## Logging Policy
All agents should log to the `/logs` directory. In integration workflows (webhook/MCP), compact JSON on stdout is allowed for machine-readable responses.

## Planned Agents
- None currently. Planned capabilities have been implemented as script tools.

---

**Note:** All agents are designed to be used within a containerized environment (e.g., Docker with shared `/shared` and `/logs` mounts).
