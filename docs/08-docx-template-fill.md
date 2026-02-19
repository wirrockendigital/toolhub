# DOCX Template Fill

Template Filling über `mcp_tools.docx_template_fill`.

## SSH

Script: `scripts/docx-template-fill.py`

```bash
/scripts/docx-template-fill.py \
  --template offer.docx \
  --output-filename offer_001.docx \
  --data '{"customer":"ACME"}'
```

## Webhook

Über `POST /run` mit Alias `n8n_docx_template_fill`.

```bash
curl -sS -X POST http://localhost:5656/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool":"n8n_docx_template_fill",
    "payload":{
      "template":"offer.docx",
      "output_filename":"offer_001.docx",
      "data":{"customer":"ACME"}
    }
  }'
```

## n8n Community Node

Node: `Toolhub DOCX Template Fill`

Felder:
- `Template`
- `Output Filename`
- `Data JSON`

## MCP

Toolnamen:
- `docx-template-fill.fill_docx_template`
- `py_docx_template_fill`
