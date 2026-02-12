# Toolhub Feature Contract

Dieses Dokument beschreibt die aktuell unterstützten Features und deren Interfaces.

## Interfaces

- `SSH`: Direkter Script-Aufruf im Container
- `Webhook`: HTTP gegen `scripts/webhook.py`
- `MCP`: MCP-Toolaufrufe über den Sidecar-Server
- `n8n Community Nodes`: `n8n-nodes-toolhub` (öffentlich installierbar)

## Feature Matrix

| Feature | SSH | Webhook | MCP | n8n Community Node | Notes |
|---|---|---|---|---|---|
| Healthcheck | - | `GET /test` | - | - | `{"status":"ok"}` |
| Audio split (n8n upload-first) | - | `POST /n8n_audio_split` | - | `Toolhub Audio Split` | Multipart upload + sortiertes Chunk-Manifest |
| Audio chunk download | - | `GET /audio-chunk/<job_id>/<filename>` | - | intern von `Toolhub Audio Split` | Binary-Download pro Chunk |
| Audio split (compat) | `scripts/audio-split.sh` | `POST /audio-split` | `sh_audio_split` | `Toolhub Audio Split Compat` | Datei muss in `/shared/audio/in` liegen |
| Transcript (lokal) | `scripts/transcript.py` | `/run` (`n8n_audio_transcript_local`) | `py_transcript` | `Toolhub Audio Transcript Local` | Nutzt lokalen Whisper-CLI-Backend |
| Cleanup | `scripts/cleanup.py` | `/run` (`n8n_audio_cleanup`) | `py_cleanup` | `Toolhub Audio Cleanup` | Unterstützt `--dry-run` |
| Wake-on-LAN | `scripts/wol-cli.sh` | `/run` (`n8n_wol`) | `sh_wol_cli`, `wol-cli` | `Toolhub WOL` | Magic Packet per MAC oder Alias |
| DOCX render | `scripts/docx-render.py` | `/run` (`n8n_docx_render`) | `py_docx_render` | `Toolhub DOCX Render` | Templates in `/data/templates`, Output in `/data/output` |
| DOCX template fill | `scripts/docx-template-fill.py` | `/run` (`n8n_docx_template_fill`) | `docx-template-fill.fill_docx_template`, `py_docx_template_fill` | `Toolhub DOCX Template Fill` | Templates in `/templates`, Output in `/output` |

## Webhook Contracts

### 1) Healthcheck

```bash
curl -sS http://localhost:5656/test
```

### 2) n8n Audio Split (`POST /n8n_audio_split`)

```bash
curl -sS -X POST http://localhost:5656/n8n_audio_split \
  -F "audio=@/tmp/e2e.m4a" \
  -F "mode=silence" \
  -F "chunk_length=600" \
  -F "silence_seek=60" \
  -F "silence_duration=0.5" \
  -F "silence_threshold=-30" \
  -F "padding=0.2" \
  -F "enhance_speech=true"
```

### 3) Audio Chunk Download (`GET /audio-chunk/<job_id>/<filename>`)

```bash
curl -sS -o part_01.m4a \
  "http://localhost:5656/audio-chunk/6f4d5d64-9a61-4ef4-9b7a-e2710f5adbe0/part_01.m4a"
```

### 4) Audio Split Compatibility (`POST /audio-split`)

```bash
curl -sS -X POST http://localhost:5656/audio-split \
  -H 'Content-Type: application/json' \
  -d '{
    "filename": "e2e.wav",
    "mode": "fixed",
    "chunk_length": 600,
    "enhance_speech": true
  }'
```

### 5) Generic Tool Run (`POST /run` with n8n aliases)

```bash
curl -sS -X POST http://localhost:5656/run \
  -H 'Content-Type: application/json' \
  -d '{
    "tool": "n8n_audio_cleanup",
    "payload": {
      "dry_run": true
    }
  }'
```

## n8n Community Package

- Package: `n8n-nodes-toolhub`
- Install in n8n via **Settings -> Community Nodes**
- Credential: `Toolhub API` (`baseUrl` required, `apiKey` optional)
- Guide: `docs/n8n_community_nodes_toolhub.md`
- Package source: `integrations/n8n-nodes-toolhub`

## Optional/Conditional MCP CLI Tools

Diese Tools sind nur registriert, wenn das jeweilige Binary im Image vorhanden ist:

- `ffmpeg`, `sox`, `magick`, `tesseract`, `pdftotext`, `pdfinfo`, `jq`, `curl`, `exiftool`
- `syft`, `grype`, `trivy`, `nuclei`
- zusätzlich: `ffprobe_info`, `tesseract_ocr`, `pdftotext_extract`, `pdfinfo_read`, `nuclei_safe`
