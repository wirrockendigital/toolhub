# Audio Split

Dieses Dokument beschreibt die Audio-Splitting-Contracts in Toolhub.

## Überblick

Toolhub stellt drei relevante HTTP-Pfade bereit:

1. `POST /n8n_audio_split` (n8n-primär)
   - Multipart Upload + Split in einem Aufruf.
   - Liefert ein normiertes Chunk-Manifest.

2. `GET /audio-chunk/<job_id>/<filename>`
   - Liefert erzeugte Chunks als Binary.

3. `POST /audio-split` (Kompatibilität)
   - Erwartet vorhandene Datei in `/shared/audio/in`.

`POST /audio-ingest-split` bleibt zusätzlich als kompatibler Upload+Split-Pfad bestehen.

## Split-Logik

### Fixed Mode (`mode=fixed`)
- Harte Trennung exakt an `chunk_length`.

### Silence Mode (`mode=silence`)
- Sucht stille Stelle im Fenster `[boundary - silence_seek, boundary]`.
- Bei mehreren Treffern wird die **nächste stille Stelle vor boundary** gewählt.
- Ohne Treffer: fallback auf harte Trennung bei `boundary`.

## HTTP: `POST /n8n_audio_split`

### Request (multipart/form-data)

Pflicht:
- `audio` (binary)

Optional Meta:
- `recordingId`
- `title`
- `source` (default `ios-webhook`)
- `language` (default `de`)
- `capturedAt` (default server timestamp)

Optional Split:
- `mode` (`fixed`/`silence`, default `fixed`)
- `chunk_length` (default `600`)
- `enhance_speech` (default `true`)
- `enhance` (default `false`)
- `silence_seek` (nur silence)
- `silence_duration` (nur silence)
- `silence_threshold` (nur silence)
- `padding` (nur silence)

### Response (`200`)

```json
{
  "recordingId": "rec_123",
  "jobId": "6f4d5d64-9a61-4ef4-9b7a-e2710f5adbe0",
  "ingest": {
    "filename": "rec_123-meeting.m4a",
    "path": "/shared/audio/in/rec_123-meeting.m4a"
  },
  "meta": {
    "title": "Meeting",
    "source": "ios-webhook",
    "language": "de",
    "capturedAt": "2026-02-11T11:30:00Z"
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

### Beispiel

```bash
curl -sS -X POST http://localhost:5656/n8n_audio_split \
  -F "audio=@/tmp/session.m4a" \
  -F "mode=silence" \
  -F "chunk_length=600" \
  -F "silence_seek=60" \
  -F "silence_duration=0.5" \
  -F "silence_threshold=-30" \
  -F "padding=0.2" \
  -F "enhance_speech=true"
```

## HTTP: `GET /audio-chunk/<job_id>/<filename>`

```bash
curl -sS -o part_01.m4a \
  "http://localhost:5656/audio-chunk/6f4d5d64-9a61-4ef4-9b7a-e2710f5adbe0/part_01.m4a"
```

## HTTP: `POST /audio-split` (Kompatibilität)

- Content-Type: `application/json`
- Erwartet `filename` unter `/shared/audio/in`
- Liefert `job_id`, `output_dir`, `files[]`

## Fehlervertrag

Für neue Endpoints (`/n8n_audio_split`, `/audio-chunk`) gilt:

```json
{
  "error": "ValidationError",
  "message": "Missing multipart file field 'audio'",
  "detail": {}
}
```

`detail` ist optional.
