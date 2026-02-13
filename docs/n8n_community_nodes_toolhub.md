# Toolhub n8n Community Nodes

This guide documents the public community package:

- `n8n-nodes-toolhub`

## Installation

1. In n8n, open **Settings -> Community Nodes**.
2. Install `n8n-nodes-toolhub`.
3. Create a `Toolhub API` credential with your Toolhub base URL.

## Node naming

- n8n display names always start with `Toolhub ...`.
- Audio functions are grouped under `Toolhub Audio ...`.
- Toolhub backend aliases used by these nodes start with `n8n_audio_*` where applicable.

## Provided nodes

1. `Toolhub Audio Split`
2. `Toolhub Audio Split Compat`
3. `Toolhub Audio Transcript Local`
4. `Toolhub Audio Cleanup`
5. `Toolhub WOL`
6. `Toolhub DOCX Render`
7. `Toolhub DOCX Template Fill`

## Audio split behavior

`Toolhub Audio Split` uploads audio to `POST /n8n_audio_split` and returns one item per chunk with binary payload.

- `splitMode=hard` maps to `mode=fixed`
- `splitMode=silence` maps to `mode=silence`
- silence splitting selects the nearest detected silence before each hard boundary

## Example workflows

- `docs/workflows/n8n_toolhub_community_audio_split.json`
- `docs/workflows/n8n_toolhub_community_cleanup.json`
- `docs/workflows/n8n_toolhub_community_docx_render.json`
- `docs/workflows/n8n_toolhub_community_ios_audio_openai_notion.json`
