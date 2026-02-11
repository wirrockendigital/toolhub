# Audio Split

A comprehensive guide to the **audio-split** functionality, covering both the standalone shell script (`audio-split.sh`) and the HTTP webhook endpoint (`/audio-split`).

---

## 1. Functionality Overview

The **audio-split** feature splits long audio recordings into smaller chunks using one of two modes:

- **Fixed Mode (`fixed`)**  
  Splits audio at exact intervals defined by `chunk_length`.

- **Silence Mode (`silence`)**  
  Attempts to split at silence near the end of each chunk window (default: 600s).
  The script searches for silence starting at `(chunk_length - silence_seek)` up to `chunk_length`.
  If no silence is found, it may continue beyond `chunk_length` until a suitable silence is detected.

Silence parameters:
- `chunk_length` (seconds): Target maximum length of each chunk.
- `silence_seek` (seconds): Defines a window of ±`silence_seek` seconds around each `chunk_length` point to search for silence (e.g. 60 means search from 540s to 660s).
- `silence_duration` (seconds): Minimum detected silence length to trigger a cut.
- `silence_threshold` (dB): Volume level below which audio is considered silence. Lower values (e.g. -40 dB) are stricter and only detect very quiet audio as silence. Higher values (e.g. -15 dB) are more lenient and may detect louder audio with background noise as silence.
- `padding` (seconds): Seconds to subtract before cut point to preserve some leading context.

Example usage:

/scripts/audio-split.sh \
  --mode silence \
  --chunk-length 600 \
  --input myfile.m4a \
  --output '' \
  --silence-seek 60 \
  --silence-duration 0.5 \
  --silence-threshold -30 \
  --padding 0.5 \
  --enhance-speech

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
  [--padding <seconds>] \
  [--enhance] [--enhance-speech]
```

- **`--mode`**: `fixed` or `silence`.
- **`--chunk-length`**: Maximum segment length in seconds.
- **`--input`**: Path to the source audio file (absolute or relative to `/shared/audio/in`).
- **`--output`**: (Optional) Subdirectory under `/shared/audio/out` for this run. Defaults to a timestamp directory.
- Silence-specific flags (`--silence-seek`, `--silence-duration`, `--silence-threshold`, `--padding`) apply only when `--mode silence`.

### 2.3.1 Audio Enhancement Options

In addition to splitting modes, the script supports optional audio enhancement to improve transcription quality for ASR systems like Whisper:

- `--enhance`  
  Preprocesses input audio by converting to mono, resampling to 16 kHz, setting bitrate to 64 k, and applying noise reduction filters (`highpass=f=100, lowpass=f=3000, afftdn`). This reduces background noise and improves clarity.

- `--enhance-speech`  
  Preprocesses input audio by converting to mono, resampling to 16 kHz, setting bitrate to 64 k, and applying speech-focused filters (`highpass=f=80, lowpass=f=4000, equalizer=f=1000:width_type=o:width=2:g=6, afftdn`). This boosts voice frequencies and highlights speech.

Both options optimize audio for automatic speech recognition by matching Whisper’s recommended input format and improving signal-to-noise ratio, leading to more accurate and reliable transcriptions.

### 2.4. Examples

- **Fixed mode – 10-minute segments:**

  ```bash
  audio-split.sh \
    --mode fixed \
    --chunk-length 600 \
    --input /shared/audio/in/session.m4a
  ```

- **Silence mode – 10-minute target chunks, cut at silence 60s before each boundary:**

  ```bash
  audio-split.sh \
    --mode silence \
    --chunk-length 600 \
    --input session.m4a \
    --silence-seek 60 \
    --silence-duration 0.5 \
    --silence-threshold -30 \
    --padding 0.2
  ```

Output goes to:
`/shared/audio/out/<timestamp>/part_01.m4a`, `part_02.m4a`, …

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

- **Content-Type:** `application/json`
- **Fields:**
  - `filename` (string, required): File name that must already exist in `/shared/audio/in`.
  - `mode` (string, required): `fixed` or `silence`.
  - `chunk_length` (number, required): Maximum segment length in seconds.
  - `silence_seek` (number, optional): Seek window before chunk end (only `silence`).
  - `silence_duration` (number, optional): Minimum silence duration (only `silence`).
  - `silence_threshold` (number, optional): Silence threshold in dB (only `silence`).
  - `padding` (number, optional): Padding before cut point (only `silence`).
  - `enhance` (boolean, optional): Apply generic enhancement filters.
  - `enhance_speech` (boolean, optional): Apply speech-optimized filters.

### 3.3. Response

- **Success (200):**  
  Returns JSON with:
  - `job_id`
  - `output_dir`
  - `files` (array with generated chunk file names)

- **Error (4xx/5xx):**  
  Returns JSON with an `error` message and, depending on failure type, additional details.

### 3.4. Example using `curl`

```bash
curl -X POST http://NAS_IP:5656/audio-split \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "session.m4a",
    "mode": "silence",
    "chunk_length": 600,
    "silence_seek": 60,
    "silence_duration": 0.5,
    "silence_threshold": -30,
    "padding": 0.2,
    "enhance_speech": true
  }'
```

### 2.5 SSH Usage

You can also execute the `audio-split.sh` script remotely via SSH. Make sure your audio file is already placed in the shared input directory (`/shared/audio/in/`).

- **From a macOS host (outside Docker)**, connect to your NAS by IP:
  ```bash
  ssh toolhubuser@NAS_IP \
    "/scripts/audio-split.sh \
      --mode silence \
      --chunk-length 600 \
      --input myfile.m4a \
      --output '' \
      --silence-seek 60 \
      --silence-duration 0.5 \
      --silence-threshold -30 \
      --padding 0.5 \
      --enhance-speech"
  ```

- **From another container on the same Docker network** (e.g., n8n), use the Toolhub service hostname or internal IP:
  ```bash
  ssh toolhubuser@toolhub \
    "/scripts/audio-split.sh \
      --mode silence \
      --chunk-length 600 \
      --input myfile.m4a \
      --output '' \
      --silence-seek 60 \
      --silence-duration 0.5 \
      --silence-threshold -30 \
      --padding 0.5 \
      --enhance-speech"
  ```
