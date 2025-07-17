[wir.rocken.digital](https://wir.rocken.digital)  
Eric

# Toolhub
**Version:** 0.1 (2025-07-11)

**Toolhub** is a universal sidecar Docker container—a Swiss Army knife for modern automation stacks. It integrates with tools like n8n, Node-RED, Activepieces, Windmill, and Flowise to provide instant access to powerful command-line tools, Python scripts, cron jobs, and webhook-triggered automation logic.

**Note:** Toolhub is specifically optimized for plug-and-play use on Synology NAS systems, but also works seamlessly on other Docker-compatible environments.

---

## Features

- **CLI Tools**:
  - Core tools: `curl`, `wget`, `git`, `nano`, `less`, `tree`, `unzip`, `cron`, `openssh-server`, `build-essential`
  - Python: `python3`, `python3-pip`, `python3-venv`, `virtualenv`
  - Media processing: `ffmpeg`, `ffprobe`, `sox`, `imagemagick`, `gifsicle`, `exiftool`, `poppler-utils`, `tesseract-ocr`
  - Data & automation: `jq`, `yq`, `aria2`, `bc`

- **Python Libraries**:
  - Web & API clients: `requests`, `httpx`, `python-dotenv`, `flask`, `flask-cors`
  - CLI/Terminal formatting: `click`, `rich`, `loguru`, `colorama`, `tqdm`, `tabulate`
  - Filesystem & automation: `pyyaml`, `markdown`, `watchdog`
  - Media/audio: `ffmpeg-python`, `pydub`
  - Data handling: `numpy`, `openpyxl`
  - Text processing: `beautifulsoup4`, `html2text`, `markdownify`, `pypandoc`, `pdfminer.six`, `python-docx`

---

## Prerequisites

1. A Synology NAS or similar with Docker (Portainer recommended).  
2. A Docker network named `allmydocker-net` (e.g., subnet 192.168.123.0/24).  
3. Host directories:
   - `/volume1/docker/toolhub` (repository, Dockerfile, scripts, cron files)  
   - `/volume1/docker/toolhub/scripts` (mounted as `/scripts`)  
   - `/volume1/docker/toolhub/cron.d` (mounted as `/etc/cron.d`)  
   - `/volume1/docker/toolhub/logs` (mounted as `/logs`)
   - `/volume1/docker/shared` (shared work directory, mounted as `/shared`)

> **Note:** Toolhub is specifically designed for use on Synology NAS systems. Please manually create all required directories before deploying the container:
>
> - /volume1/docker/toolhub/
> - /volume1/docker/toolhub/conf
> - /volume1/docker/toolhub/cron.d
> - /volume1/docker/toolhub/scripts
> - /volume1/docker/toolhub/logs
> - /volume1/docker/shared
>
> Ensure all directories have appropriate write permissions based on your Synology NAS user (e.g., UID 1061). The UID and GID must match the values defined in your `stack.env` file to ensure proper permissions inside the container.
>
> When deploying using Portainer, upload a `stack.env` file via the stack creation interface. This file defines environment variables such as:
>
> - TOOLHUB_USER=toolhubuser
> - TOOLHUB_PASSWORD=toolhub123
> - TOOLHUB_UID=1061
> - TOOLHUB_GID=100
>
> These values can be modified in Portainer after uploading the `stack.env`

---

## Installation


### Using Portainer Stack

#### Example stack.yml (Portainer-compatible)

Below is a recommended `stack.yml` configuration for deploying Toolhub via Portainer:

```yaml
version: "3.9"

services:
  toolhub:
    image: ghcr.io/wirrockendigital/toolhub:latest
    container_name: toolhub
    hostname: toolhub
    restart: always
    stdin_open: true
    tty: true
    expose:
      - "22"
      - "5656"
    ports:
      - "2222:22"
      - "5656:5656"
    volumes:
      - /volume1/docker/toolhub:/workspace
      - /volume1/docker/toolhub/shared:/shared
      - /volume1/docker/toolhub/scripts:/scripts
      - /volume1/docker/toolhub/cron.d:/etc/cron.d
      - /volume1/docker/toolhub/logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "curl -fs http://localhost:5656/test || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      allmydocker-net:
        ipv4_address: 192.168.123.100

networks:
  allmydocker-net:
    external: true
```

1. In Portainer, go to **Stacks** → **Add Stack**.  
2. Paste the contents of `stack.yml` into the stack definition.  
3. Confirm that volumes and network settings are correct.
4. Upload the stack.env
5. Change the environment variables as needed.
6. Click **Deploy the Stack**.

### Using Docker CLI

```bash
cd /volume1/docker/toolhub
docker build -t toolhub:latest .

docker run -d \
  --name toolhub \
  --network allmydocker-net \
  --ip 192.168.123.100 \
  -v /volume1/docker/toolhub:/workspace \
  -v /volume1/docker/shared:/shared \
  -v /volume1/docker/toolhub/scripts:/scripts \
  -v /volume1/docker/toolhub/cron.d:/etc/cron.d \
  -v /volume1/docker/toolhub/logs:/logs \
  toolhub:latest
```

---

## Usage

### SSH

```bash
ssh toolhubuser@<NAS-IP> -p 22
# Password: (as set in the Dockerfile)
```

### Predefined Scripts

- `/scripts/audio-split.sh input.m4a audio/out/jobname`
- Add additional scripts to `/volume1/docker/toolhub/scripts`.

### Webhook API

- Send an HTTP POST to `http://<NAS-IP>:5656/run`  
- JSON payload example:
  ```json
  {
    "tool": "ffmpeg",
    "args": ["-i", "/shared/audio/in/audio.m4a", "/shared/audio/out/audio.mp3"]
  }
  ```
- Response JSON includes `stdout`, `stderr`, `cmd`, and `error` fields.

### Audio Split API

- Send an HTTP POST to `http://<NAS-IP>:5656/audio-split`
- Form-data parameters:
  - `file` — audio file to split
  - `mode` — `fixed` or `silence`
  - `chunk_length` — length of each chunk in seconds
  - `silence_seek`, `silence_duration`, `silence_threshold`, `padding` — optional silence-detection settings for `silence` mode
  - `enhance` — apply basic enhancement filters
  - `enhance_speech` — apply speech-optimized filters (mutually exclusive with `enhance`)
- The endpoint returns a ZIP file with the generated chunks.
- Example:
  ```bash
  curl -X POST http://<NAS-IP>:5656/audio-split \
    -F "file=@/path/to/audio.m4a" \
    -F "mode=fixed" \
    -F "chunk_length=30"
  ```

### Cron Jobs

- Place cron files in `/volume1/docker/toolhub/cron.d` (e.g., `split-audio`).  
- Example cron file content:
  ```cron
  SHELL=/bin/bash
  PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

  # Daily audio-split at 03:00
  0 3 * * * toolhubuser cd /shared && \
    for f in audio/in/*.m4a; do \
      [ -f "$f" ] && /scripts/audio-split.sh "$f" "audio/out/$(basename "$f" .m4a)"; \
    done
  ```

---

## Directory Structure

```text
/volume1/docker/toolhub
├── Dockerfile
├── requirements.txt
├── README.md
├── conf/
│   └── .env
├── scripts/
│   ├── audio-split.sh
│   └── webhook.py
├── cron.d/
│   └── split-audio
└── logs/
/volume1/docker/shared
└── audio/
    ├── in/
    ├── out/
    └── logs/
```
