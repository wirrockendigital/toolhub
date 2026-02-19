# Quickstart: iOS -> n8n -> Toolhub -> OpenAI -> Notion

Ziel: In 20-30 Minuten einen lauffähigen End-to-End-Flow aufsetzen, ohne JavaScript-Node in n8n.

Fertige Workflow-Datei:

- `docs/workflows/n8n_toolhub_community_ios_audio_openai_notion.json`

## 1) Voraussetzungen

- Toolhub läuft und ist aus n8n erreichbar (z. B. `http://toolhub:5656`)
- n8n Community Node Paket installiert: `n8n-nodes-toolhub`
- n8n Credentials vorhanden:
  - `Toolhub API`
  - `OpenAI API`
  - `Notion API`
- Notion Database existiert

## 2) Import oder manuell bauen

Option A (empfohlen): Workflow direkt importieren

- `docs/workflows/n8n_toolhub_community_ios_audio_openai_notion.json`

Option B: Workflow manuell bauen

Baue diesen Pfad:

1. `Webhook` (POST, Binary Feld `audio`)
2. `Toolhub Audio Split`
3. `OpenAI` (`Audio -> Transcribe a Recording`)
4. `Aggregate` (alle Chunk-Texte zusammenführen)
5. `OpenAI` (`Text -> Message a Model`) für Anreicherung
6. `Notion` (`Database Page -> Create`)
7. `Respond to Webhook`

## 3) Node-Konfiguration

## 3.1 Webhook

- Method: `POST`
- Path: z. B. `ios-audio-ingest`
- Binary Property: `audio`

## 3.2 Toolhub Audio Split

- Credentials: `Toolhub API`
- `Input Binary Field`: `audio`
- `Output Binary Field`: `audioChunk`
- `Split Mode`: 
  - `Hard (Fixed Seconds)` fuer harte Schnitte oder
  - `Silence Before Boundary` fuer Schnitt vor Boundary an stiller Stelle
- `Chunk Length Seconds`: `600`
- `Enhance Speech`: `true`
- optional `Language`: `de`

## 3.3 OpenAI Transcribe

- Resource: `Audio`
- Operation: `Transcribe a Recording`
- Input Binary Field: `audioChunk`
- Language: `de` (optional)

## 3.4 Transcript aggregieren

Nutze `Aggregate`/`Item Lists`, um alle Chunk-Texte in ein Feld `transcript` zusammenzufassen.

Empfehlung:
- Vorher nach `chunkIndex` sortieren (falls nötig).

## 3.5 OpenAI Anreicherung

- Resource: `Text`
- Operation: `Message a Model`
- Model: `gpt-5.2`
- Prompt ID: `pmpt_698c7fb03f9881969e81d41faa8b70780705e6b67ad926b7`
- Input: dein aggregiertes Feld `transcript`
- Text Format: `json_object`

Entspricht inhaltlich:

```json
{
  "model": "gpt-5.2",
  "prompt": {
    "id": "pmpt_698c7fb03f9881969e81d41faa8b70780705e6b67ad926b7"
  },
  "input": "{{ $json.transcript }}"
}
```

## 3.6 Notion

- Resource: `Database Page`
- Operation: `Create`
- Database: deine bestehende DB
- Mappe mindestens:
  - Titel
  - Summary
  - FullTranscript
  - FollowUps
  - ActionItems
  - RecordingId
  - ToolhubJobId

## 3.7 Respond to Webhook

Antwort z. B.:

```json
{
  "status": "ok",
  "recordingId": "{{ $json.recordingId }}"
}
```

## 4) iOS Upload testen

## Option A: Kurzbefehle (empfohlen)

1. Neuer Shortcut
2. Aktion `Datei auswählen`
3. Aktion `Inhalt von URL abrufen`
   - URL: `https://<deine-n8n-domain>/webhook/ios-audio-ingest`
   - Methode: `POST`
   - Request Body: `Form`
   - Feld `audio`: die ausgewählte Datei
4. Ausführen

## Option B: a-Shell / iSH mit curl

```bash
curl -X POST "https://<deine-n8n-domain>/webhook/ios-audio-ingest" \
  -F "audio=@/path/to/file.m4a"
```

## 5) Schneller Fehlerscan (wenn "Datei kommt nicht an")

1. Prüfe im Webhook-Node, ob Binary-Property wirklich `audio` heißt.
2. Prüfe im `Toolhub Audio Split` Node `Input Binary Field = audio`.
3. Prüfe Webhook-URL:
   - `.../webhook-test/...` nur im Testmodus
   - `.../webhook/...` im aktiven Workflow
4. Prüfe Dateigröße und Dateityp (`.m4a`, `.mp3`, `.wav`).
5. Prüfe Toolhub erreichbar aus n8n:

```bash
curl -sS http://toolhub:5656/test
```

## 6) Erwartetes Ergebnis

- n8n Execution ist erfolgreich
- bei langen Aufnahmen mehrere Chunks
- Transkript + Anreicherung in Notion gespeichert
- Webhook-Response liefert `status=ok`

## 7) Referenzen

- `docs/02-audio-split-upload-first.md`
- `docs/09-run-dispatcher.md`
- `docs/n8n_audio_pipeline.md`
