
**Author & Creator:**  
**Eric Herrmannsdörfer**  
[wir.rocken.digital](https://wir.rocken.digital)  


# Toolhub
**Version:** 0.1 (2025-07-11)

**Toolhub** is a universal sidecar Docker container that offers a collection of useful command-line tools, SSH access, HTTP webhooks, and cron jobs. You can invoke installed tools via SSH, predefined scripts, or a flexible webhook API—ideal for automations in n8n, scheduled tasks, and manual interventions.

---

## Features

- **CLI Tools**: `curl`, `wget`, `git`, `ffmpeg` (including `ffprobe`), `jq`, `yq`, `unzip`, `imagemagick`, `sox`, `bc`, `lsof`, `tree`, `htop`, `exiftool`, and more.  
- **Python Support**: Python 3 + pip3, with additional libraries installed via `requirements.txt` (e.g. `flask`, `ffmpeg-python`, `requests`, `numpy`).  
- **SSH Access**: Secure SSH (port 22) access within your network.  
- **HTTP Webhook**: Flexible API endpoint (port 5656) to run any CLI tool.  
- **Cron Jobs**: Drop cron files into `/etc/cron.d` to schedule daily or hourly tasks.  
- **Custom Scripts**: Mount `/scripts` for your own shell or Python scripts (e.g. `split-audio.sh`).  
- **Persistent Logs**: All logs are stored under `/logs` and persisted via a host volume.

---

## Prerequisites

1. A Synology NAS or similar with Docker (Portainer recommended).  
2. A Docker network named `alle-meine-docker-net` (e.g., subnet 192.168.128.0/24).  
3. Host directories:
   - `/volume1/docker/toolhub` (repository, Dockerfile, scripts, cron files)  
   - `/volume1/docker/shared` (shared work directory, mounted as `/shared`)  
   - `/volume1/docker/toolhub/scripts` (mounted as `/scripts`)  
   - `/volume1/docker/toolhub/cron.d` (mounted as `/etc/cron.d`)  
   - `/volume1/docker/toolhub/logs` (mounted as `/logs`)

---

## Installation

### Using Portainer Stack

1. In Portainer, go to **Stacks** → **Add Stack**.  
2. Paste the contents of `stack.yml` into the stack definition.  
3. Confirm that volumes and network settings are correct.  
4. Click **Deploy the Stack**.

### Using Docker CLI

```bash
cd /volume1/docker/toolhub
docker build -t toolhub:latest .

docker run -d \
  --name toolhub \
  --network alle-meine-docker-net \
  --ip 192.168.128.100 \
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

- `/scripts/split-audio.sh input.m4a audio/out/jobname`  
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

### Cron Jobs

- Place cron files in `/volume1/docker/toolhub/cron.d` (e.g., `split-audio`).  
- Example cron file content:
  ```cron
  SHELL=/bin/bash
  PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

  # Daily audio-split at 03:00
  0 3 * * * toolhubuser cd /shared && \
    for f in audio/in/*.m4a; do \
      [ -f "$f" ] && /scripts/split-audio.sh "$f" "audio/out/$(basename "$f" .m4a)"; \
    done
  ```

---

## Directory Structure

```text
/volume1/docker/toolhub
├── Dockerfile
├── requirements.txt
├── README.md
├── scripts/
│   ├── split-audio.sh
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
