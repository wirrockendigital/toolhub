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
- **Logging:** Logs all activity to `/logs/split-audio.log`.

### 2. webhook.py
- **Location:** `/scripts/webhook.py`
- **Purpose:** Exposes HTTP endpoint `/audio-split` to trigger audio-split.sh via REST API.
- **Method:** `POST`
- **Input:** Multipart form-data with audio file and split parameters.
- **Output:** Returns a downloadable `.zip` of the split audio files.
- **Logging:** All events and errors go to `/logs/webhook.log`.

## Logging Policy
All agents must log to the `/logs` directory. No logging to `stderr`, `stdout`, or home/user directories is allowed in production.

## Planned Agents
- `transcript.py`: Future script to handle Whisper-based transcriptions.
- `cleanup.py`: Automated log rotation and temporary file deletion.

---

**Note:** All agents are designed to be used within a containerized environment (e.g., Docker with shared `/shared` and `/logs` mounts).