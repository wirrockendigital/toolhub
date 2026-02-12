# n8n Workflow: iOS Audio -> Toolhub Ingest Split -> OpenAI -> Notion (0 JS Nodes)

Dieses Dokument beschreibt den importierbaren Workflow:

- `docs/workflows/n8n_ios_audio_toolhub_whisper_notion.json`
- `docs/workflows/n8n_ios_audio_toolhub_whisper_notion_low_expression.json`

Der Workflow nutzt nur Standard-Nodes (kein `Code`-Node).

Für eine Node-basierte Alternative mit öffentlichen Community Nodes siehe:

- `docs/n8n_community_nodes_toolhub.md`
- `docs/workflows/n8n_toolhub_community_audio_split.json`

## Varianten

1. `n8n_ios_audio_toolhub_whisper_notion.json`
- Kompakt, mit komplexeren Expressions in wenigen `Set`-Nodes.

2. `n8n_ios_audio_toolhub_whisper_notion_low_expression.json`
- Gleicher Funktionsumfang, aber kleinere und einfacher zu wartende Expressions über mehr Zwischenschritte.
- Empfehlung, wenn du im n8n-UI leichter debuggen möchtest.

## Zielpfad

1. iOS lädt Audio per Webhook hoch (`multipart/form-data`, Binary-Feld `audio`)
2. n8n ruft `POST /audio-ingest-split` auf (Upload + Split in einem Schritt)
3. n8n splittet `chunks` in einzelne Items
4. n8n lädt pro Chunk Binary per `GET /audio-chunk/<jobId>/<filename>`
5. OpenAI Node transkribiert jeden Chunk
6. n8n sortiert und rekonstruiert das Gesamtranskript
7. OpenAI Node reichert via Prompt-ID an (`gpt-5.2`)
8. Notion Node schreibt eine Datenbank-Zeile pro Aufnahme
9. `Respond to Webhook` liefert `recordingId`, `status`, `notionPageId`

## Voraussetzungen

- n8n und Toolhub im selben Netzwerk
- Toolhub in n8n erreichbar (Default: `http://toolhub:5656`)
- Optional gleiche Shared-Mounts sind nicht mehr nötig für Chunk-Verarbeitung, da Download über `/audio-chunk/...` läuft
- n8n Env:
  - `TOOLHUB_BASE_URL` (optional, Default im Workflow: `http://toolhub:5656`)
  - `NOTION_DATABASE_ID` (required)
- n8n Credentials:
  - OpenAI (`openAiApi`)
  - Notion (`notionApi`)

## OpenAI Konfiguration

### Transcription-Node

- Resource: `Audio`
- Operation: `Transcribe a Recording`
- Binary field: `data`
- Sprache: `{{$json.language || 'de'}}`

### Enrichment-Node

- Resource: `Text`
- Operation: `Message a Model`
- Model: `gpt-5.2`
- Prompt-ID: `pmpt_698c7fb03f9881969e81d41faa8b70780705e6b67ad926b7`
- Input: `{{$json.transcript}}`
- Format: `json_object`

## Notion Mapping (aktuell im Workflow)

Der Notion-Node schreibt aktuell in folgende Property-Keys:

- `Name` (title)
- `RecordingId` (rich_text)
- `Source` (rich_text)
- `CapturedAt` (rich_text)
- `Language` (rich_text)
- `DurationClass` (rich_text)
- `ChunkCount` (number)
- `ToolhubJobId` (rich_text)
- `Summary` (rich_text)
- `FullTranscript` (rich_text)
- `FollowUps` (rich_text)
- `ActionItems` (rich_text)
- `KeyPoints` (rich_text)
- `Tags` (rich_text)
- `RiskFlags` (rich_text)

Wenn deine DB andere Namen nutzt, passe nur den Notion-Node an.

## Import

1. Workflow importieren: `docs/workflows/n8n_ios_audio_toolhub_whisper_notion.json`
2. OpenAI- und Notion-Credentials zuweisen
3. Webhook-Path prüfen (`ios-audio-ingest`)
4. Notion Property-Keys prüfen
5. Aktivieren und mit kurzem + langem Audio testen

## Test-Checklist

1. Upload `<10 min`: ein Chunk, Notion-Eintrag vorhanden
2. Upload `>10 min`: mehrere Chunks, richtige Reihenfolge im Gesamtranskript
3. Multipart ohne `audio`: klarer 400-Fehler von Toolhub
4. Toolhub down: n8n bricht klar im HTTP-Node ab
5. OpenAI Fehler: Workflow stoppt fail-fast
6. Notion Validierungsfehler: klarer Fehler im Notion-Node
