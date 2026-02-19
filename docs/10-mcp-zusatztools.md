# MCP Zusatztools (optional)

Diese Tools sind MCP-spezifisch und nicht als Webhook-Endpunkt modelliert.

## SSH

Kein direkter Kanalbezug. Je nach Tool kann das Binary natürlich manuell per SSH aufgerufen werden.

## Webhook

Nicht über `/run` oder eigene HTTP-Endpunkte verfügbar (außer du baust gezielt eigene Wrapper).

## n8n Community Node

Derzeit keine dedizierten Nodes für diese MCP-Zusatztools.

## MCP

### CLI-basierte MCP Tools (wenn Binary vorhanden)

- `ffmpeg`
- `sox`
- `magick`
- `tesseract`
- `pdftotext`
- `pdfinfo`
- `jq`
- `curl`
- `exiftool`
- `syft`
- `grype`
- `trivy`
- `nuclei`

### Handcrafted MCP Tools

- `ffprobe_info`
- `tesseract_ocr`
- `pdftotext_extract`
- `pdfinfo_read`
- `nuclei_safe`
- `run_script`

Hinweise:
- Toolverfügbarkeit hängt vom Image und installierten Binaries ab.
- Sicherheit/Allowlist wird durch MCP-Konfiguration gesteuert (`SAFE_MODE`, `ALLOWLIST_PATHS`, `ALLOWLIST_HOSTS`).
