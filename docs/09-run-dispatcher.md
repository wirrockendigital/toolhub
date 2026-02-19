# Generic Tool Dispatcher `/run`

`POST /run` ist der zentrale Dispatcher für Python-Tools, Manifest-Tools und Script-Tools.

## SSH

Nicht relevant (Webhook-Dispatcher).

## Webhook

### Endpoint
- `POST /run`

### Minimale Struktur

```json
{
  "tool": "<toolname>",
  "payload": {}
}
```

### Unterstützte Payload-Muster

- `payload` als Objekt (empfohlen)
- `args` als Liste für positional Argumente
- Top-Level Felder ohne `payload` (werden ebenfalls gemappt)

### n8n-Aliasnamen

- `n8n_audio_cleanup` -> `cleanup`
- `n8n_audio_transcript_local` -> `transcript`
- `n8n_wol` -> `wol-cli`
- `n8n_docx_render` -> `docx-render`
- `n8n_docx_template_fill` -> `docx-template-fill`
- `n8n_audio_split_compat` -> `audio-split`

### Beispiele

```bash
curl -sS -X POST http://localhost:5656/run \
  -H "Content-Type: application/json" \
  -d '{"tool":"n8n_audio_cleanup","payload":{"dry_run":true}}'

curl -sS -X POST http://localhost:5656/run \
  -H "Content-Type: application/json" \
  -d '{"tool":"n8n_wol","payload":{"target":"AA:BB:CC:DD:EE:FF"}}'
```

## n8n Community Node

Fast alle Toolhub Community Nodes (außer `Toolhub Audio Split`) rufen intern `/run` auf.

## MCP

MCP hat einen eigenen Dispatcher/Registry-Mechanismus und nutzt nicht `/run`.
