

# Audio Split

A comprehensive guide to the **audio-split** functionality, covering both the standalone shell script (`audio-split.sh`) and the HTTP webhook endpoint (`/audio-split`).

---

## 1. Functionality Overview

The **audio-split** feature allows you to divide large audio files into smaller segments according to one of two modes:

- **Fixed Mode (`fixed`)**  
  Splits the input file into equal-length chunks, each up to a specified maximum duration.

- **Silence Mode (`silence`)**  
  Splits the input into segments that are at most the given maximum length, but attempts to cut at detected silence points within a defined seek window at the end of each chunk. If no suitable silence is found, it falls back to a hard cut.

Key parameters for both modes:

- `chunk_length` (seconds): Maximum duration for each segment.
- `silence_seek` (seconds): How many seconds before the chunk end to look for silence (only for `silence` mode).
- `silence_duration` (seconds): Minimum duration of silence to trigger a cut (only for `silence` mode).
- `silence_threshold` (dB): Volume threshold under which audio is considered silence (optional for `silence` mode).
- `padding` (seconds): Amount of time to include before the detected silence point (optional for `silence` mode).

---

## 2. Using the `audio-split.sh` Shell Script

### 2.1. Prerequisites

- A Linux environment with `bash`.
- `ffmpeg` and `ffprobe` installed and available in `PATH`.
- The script located at `scripts/audio-split.sh`.
- A shared directory mounted at `/shared/audio` (the script will create subfolders if missing).

### 2.2. Script Location

```bash
/volume1/docker/toolhub/scripts/audio-split.sh
```

Ensure it is executable:

```bash
chmod +x /volume1/docker/toolhub/scripts/audio-split.sh
```

### 2.3. Usage Syntax

```bash
audio-split.sh \
  --mode fixed|silence \
  --chunk-length <seconds> \
  --input <input-file> \
  [--output <output-subdir>] \
  [--silence-seek <seconds>] \
  [--silence-duration <seconds>] \
  [--silence-threshold <dB>] \
  [--padding <seconds>]
```

- **`--mode`**: `fixed` or `silence`.
- **`--chunk-length`**: Maximum segment length in seconds.
- **`--input`**: Path to the source audio file (absolute or relative to `/shared/audio/in`).
- **`--output`**: (Optional) Subdirectory under `/shared/audio/out` for this run. Defaults to a timestamp directory.
- Silence-specific flags (`--silence-seek`, `--silence-duration`, `--silence-threshold`, `--padding`) apply only when `--mode silence`.

### 2.4. Examples

- **Fixed mode, 5-minute segments:**

  ```bash
  audio-split.sh \
    --mode fixed \
    --chunk-length 300 \
    --input /shared/audio/in/lecture.mp3
  ```

- **Silence mode, up to 10-minute segments, seek 120s for silence ≥1.5s at -30dB, keep 0.5s padding:**

  ```bash
  audio-split.sh \
    --mode silence \
    --chunk-length 600 \
    --input lecture.mp3 \
    --silence-seek 120 \
    --silence-duration 1.5 \
    --silence-threshold 30 \
    --padding 0.5
  ```

Output files will appear in:

- `/shared/audio/out/<timestamp>/part_01.m4a`, `part_02.m4a`, …

---

## 3. Using the `/audio-split` HTTP Webhook Endpoint

### 3.1. Endpoint URL

From outside Docker (e.g. from your NAS, browser, or host machine):

```
POST http://NAS_IP:5656/audio-split
```

From within another Docker container in the same `alle-meine-docker-net`:

```
POST http://toolhub:5656/audio-split
```

Make sure the container making the request is part of the same Docker network.

### 3.2. Request Format

- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file` (file): The audio file to split.
  - `mode` (text): `fixed` or `silence`.
  - `chunk_length` (text): Maximum segment length in seconds.
  - `silence_seek` (text, optional): Seek window before chunk end (only `silence`).
  - `silence_duration` (text, optional): Minimum silence duration (only `silence`).
  - `silence_threshold` (text, optional): Silence threshold in dB (only `silence`).
  - `padding` (text, optional): Padding before cut point (only `silence`).

### 3.3. Response

- **Success (200):**  
  Returns a ZIP archive containing all split segments.  
  - **Headers:**
    - `Content-Type: application/zip`
    - `Content-Disposition: attachment; filename="split-audio-<job_id>.zip"`

- **Error (4xx/5xx):**  
  Returns JSON with an `error` message.

### 3.4. Example using `curl`

```bash
curl -X POST http://NAS_IP:5656/audio-split \
  -F "file=@/path/to/lecture.mp3" \
  -F "mode=silence" \
  -F "chunk_length=600" \
  -F "silence_seek=120" \
  -F "silence_duration=1.5" \
  -F "silence_threshold=30" \
  -F "padding=0.5" \
  --output split-results.zip
```

This will download `split-results.zip` containing all the split audio parts.
