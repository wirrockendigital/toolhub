# Toolhub Dokumentation (funktional + kanalweise)

Diese Doku ist nach Funktionen strukturiert. Jede Funktion enthält die Kanäle:

- SSH
- Webhook
- n8n Community Node
- MCP

## Voraussetzungen

- Toolhub Webhook läuft auf `http://<host>:5656`
- Audio Shared Paths:
  - Input: `/shared/audio/in`
  - Output: `/shared/audio/out`
- n8n Credential: `Toolhub API`
  - `baseUrl` (Pflicht)
  - `apiKey` (optional)

## Funktionen

1. [Healthcheck & Service Info](./01-healthcheck.md)
2. [Audio Split (Upload-first)](./02-audio-split-upload-first.md)
3. [Audio Split (Compat / Shared-File)](./03-audio-split-compat.md)
4. [Audio Transcript Local](./04-audio-transcript-local.md)
5. [Audio Cleanup](./05-audio-cleanup.md)
6. [Wake-on-LAN](./06-wol.md)
7. [DOCX Render](./07-docx-render.md)
8. [DOCX Template Fill](./08-docx-template-fill.md)
9. [Generic Tool Dispatcher `/run`](./09-run-dispatcher.md)
10. [MCP Zusatztools (optional)](./10-mcp-zusatztools.md)
11. [Quickstart iOS -> n8n -> Toolhub -> OpenAI -> Notion](./11-quickstart-ios-n8n-toolhub-openai-notion.md)
12. [Generic File Dispatcher `/run-file`](./12-run-file-dispatcher.md)
