# Toolhub

Universal sidecar container for automation platforms, MCP clients, and self-hosted workflows.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture & Modes](#architecture--modes)
- [Quickstart](#quickstart)
- [Installation & Setup](#installation--setup)
- [Using Toolhub as an MCP Server](#using-toolhub-as-an-mcp-server)
- [CLI & Tools](#cli--tools)
- [Examples](#examples)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Development](#development)
- [Versioning & Changelog](#versioning--changelog)
- [License](#license)
- [Credits / Acknowledgements](#credits--acknowledgements)

## Project Overview
Toolhub is a universal sidecar Docker container designed to complement automation stacks such as n8n, Node-RED, Activepieces, Windmill, and Flowise. It bundles battle-tested CLI utilities, Python tooling, cron scheduling, and webhook-triggered automation so that self-hosters can add powerful helper scripts without maintaining dozens of bespoke containers.

**Key features**
- Rich CLI base image with networking, media, data, and developer tools (`curl`, `wget`, `git`, `ffmpeg`, `tesseract-ocr`, `jq`, `yq`, and more).
- Curated Python environment with web, automation, media, and parsing libraries (`requests`, `flask`, `pydub`, `numpy`, `beautifulsoup4`, ...).
- Audio automation out of the box via `audio-split.sh` (CLI) and a Flask webhook exposed through Gunicorn on port `5656`.
- Cron-ready layout with persistent scripts/logs shared via host mounts for reproducible workflows.
- Optional Model Context Protocol (MCP) server that exposes every Toolhub script or curated CLI as an MCP tool for AI assistants.
- Opinionated Synology NAS setup that still works on any Docker-compatible host.

## Architecture & Modes
Toolhub can run in different modes depending on which services you enable.

```
+-------------------+        +------------------------+
| Automation Client |  HTTP  |  Gunicorn + Flask API  |
| (n8n, cron, etc.) | <----> |  scripts/webhook.py    |
+-------------------+        +------------------------+
          |                              |
          | executes scripts             | spawns scripts
          v                              v
+-------------------+        +------------------------+
| /scripts/*.sh,py  | <----> |  MCP Server (optional) |
| (e.g. audio-split)|  stdio |  src/mcp/server.ts     |
+-------------------+        +------------------------+
          |                              |
          +------------------------------+
                         writes to
                    /shared and /logs
```

- **Base container** – Built from `Dockerfile`; entrypoint `start.sh` creates the `toolhubuser` user, prepares `/scripts`, `/shared`, `/logs`, starts SSH (`22`), cron, and Gunicorn for the webhook service (`5656`).
- **Cron & scripts** – Host-mounted under `/volume1/docker/toolhub/scripts` and `/volume1/docker/toolhub/cron.d` (see `stack.yml`). Logs go to `/logs` (`audio-split.log`, `webhook.log`).
- **Webhook mode** – `scripts/webhook.py` offers `/`, `/test`, and `/audio-split` endpoints to orchestrate automation from HTTP clients.
- **MCP mode (optional)** – Add the `docker-compose.mcp.yml` sidecar to run `src/mcp/server.ts`, discover shell/Python scripts, and expose them as MCP tools over stdio.
- **Source layout highlights**:
  - `scripts/` – Shell & Python helpers (`audio-split.sh`, `webhook.py`).
  - `scripts/tests/` – Automated smoke tests (`mcp-smoke.sh`).
  - `src/mcp/` – TypeScript MCP implementation (`server.ts`, `config.ts`, `tool-registry.ts`, ...).
  - `stack.yml`, `docker-compose.mcp.yml` – Deployment descriptors.
  - `stack.env` – Example environment variable definitions for Portainer stacks.

## Quickstart
The fastest way to launch Toolhub (webhook + optional MCP) is via Docker Compose on a Docker-capable host (e.g. Synology NAS).

```bash
# 1. Prepare host directories with matching permissions
mkdir -p /volume1/docker/toolhub/{conf,cron.d,logs,scripts} \
         /volume1/docker/shared/audio/{in,out}

# 2. Copy stack files from this repository
cp stack.yml stack.env /volume1/docker/toolhub/

# 3. Deploy Toolhub (base container only)
docker compose -f stack.yml up -d

# 4. (Optional) Bring up the MCP sidecar alongside the base container
docker compose -f stack.yml -f docker-compose.mcp.yml up -d

# 5. Smoke-test the webhook API
curl http://localhost:5656/test
```

The `/test` endpoint replies with `{ "status": "ok" }`, confirming that SSH, cron, and the webhook service booted correctly.

## Installation & Setup

### Docker / Docker Compose
Toolhub is optimized for Synology NAS deployments but runs on any Docker host. The recommended Portainer-compatible `stack.yml`:

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
      - /volume1/docker/toolhub/scripts:/scripts
      - /volume1/docker/toolhub/cron.d:/etc/cron.d
      - /volume1/docker/toolhub/logs:/logs
      - /volume1/docker/shared:/shared
    deploy:
      resources:
        reservations:
          memory: 256M
        limits:
          memory: 2G
    networks:
      allmydocker-net:
        ipv4_address: 192.168.123.100

networks:
  allmydocker-net:
    external: true
```

1. Create the `allmydocker-net` Docker network (e.g., `docker network create --subnet 192.168.123.0/24 allmydocker-net`).
2. Ensure the host directories listed under `volumes` exist and have writable permissions for the `TOOLHUB_UID` and `TOOLHUB_GID` values.
3. Upload `stack.yml` and `stack.env` in Portainer (or run `docker compose -f stack.yml up -d` on the CLI).
4. Adjust `stack.env` values as needed, then deploy.

**Standalone Docker CLI**

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

### MCP Sidecar with Docker Compose
Include `docker-compose.mcp.yml` to run the MCP server alongside Toolhub:

```yaml
version: "3.9"

services:
  toolhub-mcp:
    image: node:20-alpine
    container_name: toolhub-mcp
    working_dir: /app
    command: ["sh", "-c", "npm install --omit=dev && npm run build && npm run mcp:start"]
    restart: unless-stopped
    depends_on:
      - toolhub
    network_mode: "service:toolhub"
    environment:
      SAFE_MODE: '${SAFE_MODE:-true}'
      ALLOWLIST_PATHS: '${ALLOWLIST_PATHS:-/data,/tmp}'
      ALLOWLIST_HOSTS: '${ALLOWLIST_HOSTS:-localhost,127.0.0.1}'
      MCP_SCRIPTS_ROOT: '${MCP_SCRIPTS_ROOT:-/app/scripts}'
      MCP_COMMAND_TIMEOUT_MS: '${MCP_COMMAND_TIMEOUT_MS:-120000}'
      MCP_MAX_OUTPUT: '${MCP_MAX_OUTPUT:-20000}'
      MCP_RATE_LIMIT_COUNT: '${MCP_RATE_LIMIT_COUNT:-5}'
      MCP_RATE_LIMIT_WINDOW_MS: '${MCP_RATE_LIMIT_WINDOW_MS:-10000}'
      NUCLEI_TEMPLATES: '${NUCLEI_TEMPLATES:-/root/nuclei-templates}'
    volumes:
      - .:/app
      - ./scripts:/app/scripts:ro
      - ./data:/data
      - /tmp/toolhub:/tmp
      - /var/run/docker.sock:/var/run/docker.sock
```

### Environment variables

| Variable | Default / Example | Description |
| --- | --- | --- |
| `TOOLHUB_USER` | `toolhubuser` | User created inside the container for SSH and cron execution (`start.sh`). |
| `TOOLHUB_PASSWORD` | `toolhub123` | Password for `TOOLHUB_USER`; change after deployment. |
| `TOOLHUB_UID` | `1061` | UID mapped to host user for proper volume permissions. |
| `TOOLHUB_GID` | `100` | GID mapped to host group; must match host permissions. |
| `SAFE_MODE` | `true` | Enables MCP guardrails (blocks destructive commands). |
| `ALLOWLIST_PATHS` | `/data,/tmp` | Comma-separated allowed path prefixes for MCP tools (scripts under `/app/scripts` always allowed). |
| `ALLOWLIST_HOSTS` | `localhost,127.0.0.1` | Allowed hostnames for MCP networking tools. |
| `MCP_COMMAND_TIMEOUT_MS` | `120000` | MCP command execution timeout in milliseconds. |
| `MCP_MAX_OUTPUT` | `20000` | Max characters returned per MCP tool invocation. |
| `MCP_RATE_LIMIT_COUNT` | `5` | Number of MCP invocations allowed per rate window. |
| `MCP_RATE_LIMIT_WINDOW_MS` | `10000` | Rate-limiting window for MCP tools (ms). |
| `MCP_SCRIPTS_ROOT` | `/app/scripts` | Directory scanned for MCP-compatible scripts. |
| `NUCLEI_TEMPLATES` | `/root/nuclei-templates` | Optional templates path for the `nuclei_safe` MCP tool. |

> **Tip:** When deploying via Portainer, upload `stack.env` first. The file includes `TOOLHUB_*` entries and can be edited directly in the Portainer UI.

### Bare-metal / local installs
TODO: Document bare-metal installation beyond Docker.

### Configuration notes
- `start.sh` ensures `/scripts`, `/etc/cron.d`, `/logs`, and `/shared/audio/{in,out}` exist and are owned by `TOOLHUB_USER`.
- Cron entries placed in `/etc/cron.d` run as `toolhubuser`; remember to add an empty newline at the end of each cron file.
- All agent logs must live under `/logs` (see `AGENTS.md`).

## Using Toolhub as an MCP Server
The TypeScript MCP server turns every Toolhub script or curated CLI wrapper into an MCP tool.

1. Launch the MCP sidecar (`docker compose -f stack.yml -f docker-compose.mcp.yml up -d`).
2. The sidecar installs dependencies, builds TypeScript sources, and runs `npm run mcp:start`, which boots `src/mcp/server.ts`.
3. Tools are exposed over stdio for MCP clients (Claude Desktop custom servers, Codex IDE integrations, etc.).

**Server components**
- `src/mcp/server.ts` – Bootstraps the MCP server with `@modelcontextprotocol/sdk`.
- `src/mcp/config.ts` – Centralizes environment variables for safe-mode toggles, allowlists, and rate limits.
- `src/mcp/security.ts` – Enforces safe-mode, per-tool rate limiting, and bounded output.
- `src/mcp/discovery.ts` – Auto-discovers executable `.sh`/`.py` files inside `MCP_SCRIPTS_ROOT` and parses optional metadata.
- `src/mcp/tool-registry.ts` – Registers discovered scripts and curated CLI wrappers (e.g., `pdftotext_extract`, `ffprobe_info`, `nuclei_safe`, `run_script`).
- `src/mcp/util/run.ts` – Executes commands via `execa`, enforcing timeouts and output truncation.

**Safe-mode guardrails**
- Blocks destructive commands (`rm -rf`, `shutdown`, etc.).
- Restricts filesystem and network access to allowlisted prefixes and hosts.
- Rate-limits each tool to five invocations per ten seconds.
- Truncates output to 20k characters; long results should be redirected to files in `/shared`.
- `nuclei_safe` forces informational severities and ignores exploit templates.

**Script metadata convention**
Scripts can embed an MCP metadata block to override descriptions or JSON schemas:

```bash
#!/usr/bin/env bash
#==MCP==
# {
#   "description": "Split audio into short fragments",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "mode": {"type": "string", "enum": ["fixed", "silence"]},
#       "args": {"type": "array", "items": {"type": "string"}}
#     },
#     "required": ["mode"]
#   }
# }
#==/MCP==
```

**Client integration workflow**
1. Start the stack with the MCP sidecar running.
2. Configure the MCP client to spawn `npm run mcp:start` (or `node dist/mcp/server.js`) inside the sidecar container and connect over stdio.
3. Run `list-tools` to confirm discovery; scripts added to `/app/scripts` become available without redeploying.
4. Optional smoke test: `scripts/tests/mcp-smoke.sh` installs dependencies (if missing) and prints the first discovered MCP tool.

## CLI & Tools

### `/scripts/audio-split.sh`
- **Purpose**: Split audio files into fixed-length or silence-detected segments with optional enhancement filters.
- **Usage**:
  ```bash
  /scripts/audio-split.sh \
    --mode fixed|silence \
    --chunk-length <seconds> \
    --input <file> \
    [--output <dir>] \
    [--silence-seek <seconds>] \
    [--silence-duration <seconds>] \
    [--silence-threshold <dB>] \
    [--padding <seconds>] \
    [--enhance | --enhance-speech]
  ```
- **Inputs**: Source audio file inside `/shared/audio/in` (unless an absolute path is given). Optional silence-detection and enhancement flags.
- **Outputs**: Chunked files saved under `/shared/audio/out/<job>/part_XX.m4a`; logs written to `/logs/audio-split.log`.
- **Notes**: Requires `ffmpeg`, `ffprobe`, and `bc` (preinstalled). Enhancements enforce mono 16 kHz audio before splitting.

### `scripts/webhook.py`
- **Purpose**: Flask service (served by Gunicorn) that orchestrates audio splitting over HTTP.
- **Endpoints**:
  - `GET /` – Returns service metadata and available routes.
  - `GET /test` – Health probe returning `{"status": "ok"}`.
  - `POST /test` – Echoes JSON payloads for integration tests.
  - `POST /audio-split` – JSON body triggers `audio-split.sh` using files from `/shared/audio/in` and returns generated chunk metadata.
- **Inputs**: JSON payload with `filename`, `mode`, `chunk_length`, and optional silence/enhancement parameters.
- **Outputs**: JSON containing `job_id`, `output_dir`, and chunk filenames. Errors include log excerpts when available. Logs stored in `/logs/webhook.log`.

### `scripts/tests/mcp-smoke.sh`
- **Purpose**: Validates MCP discovery locally.
- **Usage**:
  ```bash
  scripts/tests/mcp-smoke.sh
  ```
- **Behavior**: Installs `node_modules` if missing, runs `npm run mcp:dev -- --list-tools`, and prints the first discovered tool (uses `jq` when present).

### Wake-on-LAN (`wol-cli`)
- **Purpose**: Send Wake-on-LAN Magic Packets to physical devices from the MCP tool runner.
- **Setup**:
  1. Copy `config/wol-devices.sample.json` to `config/wol-devices.json` and edit the MAC addresses for your hosts.
  2. Optionally export `WOL_BROADCAST=192.168.123.255` (or another subnet broadcast) before starting the MCP server to override the default broadcast address.
- **Invocation examples**:
  ```bash
  # Direct MAC target
  curl -X POST http://toolhub:PORT/run \
    -H 'Content-Type: application/json' \
    -d '{"tool":"wol-cli","args":["3C:07:71:AA:BB:CC"]}'

  # Named target resolved from config/wol-devices.json
  curl -X POST http://toolhub:PORT/run \
    -H 'Content-Type: application/json' \
    -d '{"tool":"wol-cli","args":["macstudio"]}'
  ```
- **Networking note**: UDP broadcast from containers may require host networking. Create a `docker-compose.override.yml` with:
  ```yaml
  services:
    toolhub:
      network_mode: "host"
  ```
  Only enable host networking if you understand the security implications, as it exposes all container ports directly on the host.
- **Platform reminder**: On macOS, ensure “Wake for network access” is enabled. Wake-on-LAN resumes devices from sleep/standby and does not power on machines that are fully shut down.

## Examples

### Split audio locally via CLI
```bash
# Place input file under /shared/audio/in on the host volume
cp ~/Downloads/interview.m4a /volume1/docker/shared/audio/in/

# Run fixed-length splitting (30-second chunks)
docker exec -it toolhub \
  /scripts/audio-split.sh \
  --mode fixed \
  --chunk-length 30 \
  --input interview.m4a
```

### Trigger the audio split webhook
```bash
curl -X POST http://localhost:5656/audio-split \
  -H "Content-Type: application/json" \
  -d '{
        "filename": "interview.m4a",
        "mode": "silence",
        "chunk_length": 45,
        "silence_seek": 10,
        "silence_duration": 1.5,
        "silence_threshold": 30,
        "padding": 0.5,
        "enhance": false,
        "enhance_speech": true
      }'
```

### Enumerate MCP tools locally
```bash
npm install
npm run build
npm run mcp:dev -- --list-tools | jq '.[0:5]'
```

## Troubleshooting & FAQ
- **Permission denied on mounted volumes** – Ensure `TOOLHUB_UID` and `TOOLHUB_GID` match the host user's UID/GID and that all `/volume1/docker/toolhub/*` directories exist before deployment.
- **No audio chunks generated** – Check `/logs/audio-split.log`; the script aborts if the input file cannot be found or if `ffmpeg`/`ffprobe` are missing. The webhook also returns `log_tail` snippets when failures occur.
- **MCP client cannot connect** – Verify the MCP sidecar is running, `SAFE_MODE` settings allow the requested paths/hosts, and the client connects over stdio (not HTTP).
- **Cron job not firing** – Confirm cron files in `/volume1/docker/toolhub/cron.d` end with a newline and use absolute paths or paths relative to `/shared`.

## Development
- Install Node dependencies for the MCP server: `npm install`.
- Build TypeScript sources: `npm run build`.
- Run the MCP server in development mode: `npm run mcp:dev`.
- Project layout:
  - `Dockerfile` – Builds the base container with CLI tools, Python libraries, and Gunicorn.
  - `start.sh` – Container entrypoint bootstrapping users, directories, SSH, cron, and the webhook.
  - `requirements.txt` – Python packages baked into the image for script development.
  - `src/` – TypeScript MCP implementation.
  - `scripts/` – Operational shell/Python tools mounted into the container at runtime.

## Versioning & Changelog
- Current release: **0.1 (2025-07-11)** as documented in prior README.
- TODO: Document formal changelog/versioning strategy (e.g., semantic releases or conventional commits).

## License
TODO: Add explicit license information for Toolhub.

## Credits / Acknowledgements
- Maintained by [wir.rocken.digital](https://wir.rocken.digital) — thanks to Eric and the community of Toolhub contributors.
