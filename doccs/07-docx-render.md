# DOCX Render

Template Rendering via `tools.docx_render.handler`.

## SSH

Script: `scripts/docx-render.py`

```bash
/scripts/docx-render.py \
  --template invoice.docx \
  --output-name invoice_out.docx \
  --data '{"name":"Max Mustermann"}'
```

## Webhook

Über `POST /run` mit Alias `n8n_docx_render`.

```bash
curl -sS -X POST http://localhost:5656/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool":"n8n_docx_render",
    "payload":{
      "template":"invoice.docx",
      "output_name":"invoice_out.docx",
      "data":{"name":"Max Mustermann"}
    }
  }'
```

## n8n Community Node

Node: `Toolhub DOCX Render`

Felder:
- `Template`
- `Output Name`
- `Data JSON`

## MCP

Toolname:
- `py_docx_render`
