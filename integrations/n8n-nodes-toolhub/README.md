# n8n-nodes-toolhub

Community nodes for integrating Toolhub with n8n.

## What is included

This package provides separate nodes per Toolhub function.

### Core

- `Toolhub Audio Split`
- `Toolhub Audio Split Compat`
- `Toolhub Audio Transcript Local`
- `Toolhub Audio Cleanup`
- `Toolhub WOL`
- `Toolhub DOCX Render`
- `Toolhub DOCX Template Fill`

### Document/PDF/OCR

- `Toolhub PDF Extract Text`
- `Toolhub PDF Info`
- `Toolhub OCR Image`
- `Toolhub HTML to Markdown`
- `Toolhub Markdown to HTML`
- `Toolhub Document Convert`
- `Toolhub XLSX Read`

### Media/Image/Data

- `Toolhub Image Convert`
- `Toolhub GIF Optimize`
- `Toolhub Image Metadata`
- `Toolhub Audio Convert`
- `Toolhub JSON Transform`
- `Toolhub YAML Transform`
- `Toolhub Array Stats`

### Utility/Network/Git

- `Toolhub HTTP Fetch`
- `Toolhub Download Aria2`
- `Toolhub Download Wget`
- `Toolhub Curl Request`
- `Toolhub Unzip`
- `Toolhub Tree List`
- `Toolhub BC Calc`
- `Toolhub Git`

## Credential

All nodes use a shared credential named `Toolhub API`:

- `Base URL` (required), example: `http://toolhub:5656`
- `API Key` (optional)
- `Auth Header Name` (default: `Authorization`)
- `Auth Scheme` (Bearer/Token/Raw)

## Install in n8n

1. Open **Settings -> Community Nodes** in n8n.
2. Install package: `n8n-nodes-toolhub`.
3. Create a `Toolhub API` credential.
4. Use the nodes from the **Toolhub** category.

## Build locally

```bash
cd integrations/n8n-nodes-toolhub
npm install
npm run build
```

## Notes

- File-first nodes call `POST /run-file`.
- JSON-first nodes call `POST /run`.
- `Toolhub Audio Split` calls `POST /n8n_audio_split`.
