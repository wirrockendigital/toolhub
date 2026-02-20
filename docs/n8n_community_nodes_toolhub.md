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
- Toolhub backend aliases used by these nodes start with `n8n_*`.

## Provided nodes

1. `Toolhub Audio Split`
2. `Toolhub Audio Split Compat`
3. `Toolhub Audio Transcript Local`
4. `Toolhub Audio Cleanup`
5. `Toolhub WOL`
6. `Toolhub DOCX Render`
7. `Toolhub DOCX Template Fill`
8. `Toolhub PDF Extract Text`
9. `Toolhub PDF Info`
10. `Toolhub OCR Image`
11. `Toolhub HTML to Markdown`
12. `Toolhub Markdown to HTML`
13. `Toolhub Document Convert`
14. `Toolhub XLSX Read`
15. `Toolhub Image Convert`
16. `Toolhub GIF Optimize`
17. `Toolhub Image Metadata`
18. `Toolhub Audio Convert`
19. `Toolhub JSON Transform`
20. `Toolhub YAML Transform`
21. `Toolhub Array Stats`
22. `Toolhub HTTP Fetch`
23. `Toolhub Download Aria2`
24. `Toolhub Download Wget`
25. `Toolhub Curl Request`
26. `Toolhub Unzip`
27. `Toolhub Tree List`
28. `Toolhub BC Calc`
29. `Toolhub Git`

## Endpoint mapping

- File-first nodes use `POST /run-file` and can optionally download the first artifact.
- JSON-first nodes use `POST /run`.
- Audio split upload-first uses `POST /n8n_audio_split`.

## Example workflows

- `docs/workflows/n8n_toolhub_community_audio_split.json`
- `docs/workflows/n8n_toolhub_community_cleanup.json`
- `docs/workflows/n8n_toolhub_community_docx_render.json`
- `docs/workflows/n8n_toolhub_community_ios_audio_openai_notion.json`
- `docs/workflows/n8n_toolhub_community_*.json` for dedicated examples of each newly added node
