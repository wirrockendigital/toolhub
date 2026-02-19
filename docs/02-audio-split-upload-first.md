# Audio Split (Upload-first)

Primärer Pfad für n8n/iOS Uploads.

## SSH

Nicht direkt verfügbar, da Upload per multipart über HTTP erfolgt.

## Webhook

### `POST /n8n_audio_split`

`multipart/form-data`

Pflichtfeld:
- `audio` (binary)

Optionale Metadaten:
- `recordingId`
- `title`
- `source` (Default: `ios-webhook`)
- `language` (Default: `de`)
- `capturedAt`

Split-Parameter:
- `mode`: `fixed` | `silence` (Default: `fixed`)
- `chunk_length`: Sekunden (Default: `600`)
- `enhance`: bool (Default: `false`)
- `enhance_speech`: bool (Default: `true`)
- bei `mode=silence` zusätzlich:
  - `silence_seek`
  - `silence_duration`
  - `silence_threshold`
  - `padding`

Beispiel:

```bash
curl -sS -X POST http://localhost:5656/n8n_audio_split \
  -F "audio=@/tmp/meeting.m4a" \
  -F "mode=silence" \
  -F "chunk_length=600" \
  -F "silence_seek=60" \
  -F "silence_duration=0.5" \
  -F "silence_threshold=-30" \
  -F "padding=0.2" \
  -F "enhance_speech=true"
```

Response (Schema):

```json
{
  "recordingId": "...",
  "jobId": "...",
  "ingest": {
    "filename": "...",
    "path": "/shared/audio/in/..."
  },
  "meta": {
    "title": "...",
    "source": "...",
    "language": "de",
    "capturedAt": "..."
  },
  "chunks": [
    {
      "index": 1,
      "filename": "part_01.m4a",
      "path": "/shared/audio/out/<jobId>/part_01.m4a",
      "downloadUrl": "http://toolhub:5656/audio-chunk/<jobId>/part_01.m4a",
      "mimeType": "audio/mp4"
    }
  ]
}
```

### Kompatibilitätsroute

`POST /audio-ingest-split` ist funktional gleich und bleibt aus Kompatibilitätsgründen erhalten.

### Chunk Download

Chunks aus dem Manifest per `downloadUrl` laden oder direkt:

```bash
curl -sS -o part_01.m4a \
  "http://localhost:5656/audio-chunk/<jobId>/part_01.m4a"
```

## n8n Community Node

Node: `Toolhub Audio Split`

Wichtige Felder:
- `Input Binary Field` (Default: `audio`)
- `Output Binary Field` (Default: `audioChunk`)
- `Split Mode`: `Hard (Fixed Seconds)` oder `Silence Before Boundary`
- `Chunk Length Seconds`
- `Enhance Speech`
- `Recording ID`, `Title`, `Source`, `Language`, `Captured At`

Output:
- pro Chunk ein eigenes Item
- Binary im Feld `audioChunk` (oder dein konfigurierter Name)

## MCP

Kein eigener Upload-first MCP-Endpunkt.
