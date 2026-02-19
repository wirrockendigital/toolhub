# Audio Transcript Local

Lokale Transkription über Whisper CLI.

## SSH

Script: `scripts/transcript.py`

Beispiel:

```bash
/scripts/transcript.py \
  --input meeting.m4a \
  --format json \
  --backend auto \
  --language de
```

Wichtige Parameter:
- `--input` (Pflicht)
- `--output` (optional)
- `--format` (`json` | `txt`)
- `--backend` (`auto` | `whisper-cli`)
- `--language`
- `--model`

## Webhook

Über `POST /run` mit Alias `n8n_audio_transcript_local`.

```bash
curl -sS -X POST http://localhost:5656/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool":"n8n_audio_transcript_local",
    "payload":{
      "input":"meeting.m4a",
      "format":"json",
      "backend":"auto",
      "language":"de"
    }
  }'
```

## n8n Community Node

Node: `Toolhub Audio Transcript Local`

Felder:
- `Input`
- `Output`
- `Format`
- `Backend`
- `Language`
- `Model`

Wichtiger Hinweis:
- Der Node bietet `SRT` als Option, das Backend-Script akzeptiert aber aktuell nur `json` und `txt`.

## MCP

Toolname:
- `py_transcript`
