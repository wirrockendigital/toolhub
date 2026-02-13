# Audio Split (Compat / Shared-File)

Legacy-kompatibler Split-Flow mit Datei aus `/shared/audio/in`.

## SSH

Script: `scripts/audio-split.sh`

Beispiel fixed:

```bash
/scripts/audio-split.sh \
  --mode fixed \
  --chunk-length 600 \
  --input meeting.m4a \
  --output /shared/audio/out/manual-job \
  --enhance-speech
```

Beispiel silence:

```bash
/scripts/audio-split.sh \
  --mode silence \
  --chunk-length 600 \
  --input meeting.m4a \
  --silence-seek 60 \
  --silence-duration 0.5 \
  --silence-threshold -30 \
  --padding 0.2
```

Hinweis:
- Bei mehreren stillen Stellen im Fenster wird die **nächste stille Stelle vor der Boundary** gewählt.

## Webhook

### `POST /audio-split`

JSON-Body:
- `filename` (Pflicht, Datei muss in `/shared/audio/in` liegen)
- `mode`: `fixed` | `silence`
- `chunk_length`
- optional: `enhance`, `enhance_speech`
- bei `silence`: `silence_seek`, `silence_duration`, `silence_threshold`, `padding`

Beispiel:

```bash
curl -sS -X POST http://localhost:5656/audio-split \
  -H "Content-Type: application/json" \
  -d '{
    "filename":"meeting.m4a",
    "mode":"fixed",
    "chunk_length":600,
    "enhance_speech":true
  }'
```

Response:

```json
{
  "job_id": "...",
  "output_dir": "/shared/audio/out/<job_id>",
  "files": ["part_01.m4a", "part_02.m4a"]
}
```

## n8n Community Node

Node: `Toolhub Audio Split Compat`

Felder:
- `Filename`
- `Mode`
- `Chunk Length Seconds`
- `Enhance Speech`
- bei Silence zusätzlich:
  - `Silence Seek Seconds`
  - `Silence Duration Seconds`
  - `Silence Threshold dB`
  - `Padding Seconds`

## MCP

Toolname:
- `sh_audio_split`
