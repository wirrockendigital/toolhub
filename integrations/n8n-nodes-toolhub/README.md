# n8n-nodes-toolhub

Community nodes for integrating Toolhub with n8n.

## What is included

This package provides separate nodes per Toolhub function:

- `Toolhub Audio Split`
- `Toolhub Audio Split Compat`
- `Toolhub Audio Transcript Local`
- `Toolhub Audio Cleanup`
- `Toolhub WOL`
- `Toolhub DOCX Render`
- `Toolhub DOCX Template Fill`

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

- `Toolhub Audio Split` calls `POST /n8n_audio_split`, downloads chunk binaries, and returns one item per chunk.
- `Toolhub Audio Cleanup` calls `/run` with `tool: n8n_audio_cleanup`.
- Existing Toolhub endpoints remain compatible for legacy workflows.
