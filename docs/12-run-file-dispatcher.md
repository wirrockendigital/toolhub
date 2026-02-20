# Generic File Dispatcher `/run-file`

`POST /run-file` ist der zentrale Dispatcher für file-first Tools.

## SSH

Nicht relevant (Webhook-Dispatcher).

## Webhook

### Endpoint
- `POST /run-file`

### Multipart-Felder

- `tool` (Pflicht)
- `file` (Pflicht, Binary)
- `payload` (optional, JSON-String)

### Response

- `job_id`
- `result` (Tool-Ausgabe)
- `artifacts[]` mit `downloadUrl` für `GET /artifacts/<job_id>/<filename>`

### Beispiel

```bash
curl -X POST http://localhost:5656/run-file \
  -F "tool=n8n_pdf_extract_text" \
  -F "file=@/tmp/example.pdf" \
  -F 'payload={"output_filename":"example.txt"}'
```

## n8n Community Node

File-first Nodes (z. B. PDF/OCR/Image/Convert/Unzip) rufen intern `/run-file` auf.

## MCP

MCP nutzt eigene Tool-Aufrufe; `/run-file` ist ein Webhook-Kontrakt.
