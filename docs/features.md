# Toolhub Feature Contract

Dieses Dokument beschreibt die aktuell unterstützten Features und deren Interfaces.

## Interfaces

- `SSH`: Direkter Script-Aufruf im Container
- `Webhook`: HTTP gegen `scripts/webhook.py`
- `MCP`: MCP-Toolaufrufe über den Sidecar-Server
- `n8n Community Nodes`: `n8n-nodes-toolhub` (öffentlich installierbar)

## Core Webhook Endpoints

- `GET /test`
- `GET /tools`
- `POST /run`
- `POST /run-file`
- `GET /artifacts/<job_id>/<filename>`
- Audio-spezifisch: `POST /n8n_audio_split`, `POST /audio-ingest-split`, `GET /audio-chunk/<job_id>/<filename>`, `POST /audio-split`

## Feature Matrix

| Feature | SSH | Webhook | MCP | n8n Community Node |
|---|---|---|---|---|
| Audio split upload-first | - | `POST /n8n_audio_split` | - | `Toolhub Audio Split` |
| Audio split compat | `scripts/audio-split.sh` | `POST /audio-split` | `sh_audio_split` | `Toolhub Audio Split Compat` |
| Transcript lokal | `scripts/transcript.py` | `/run` (`n8n_audio_transcript_local`) | `py_transcript` | `Toolhub Audio Transcript Local` |
| Cleanup | `scripts/cleanup.py` | `/run` (`n8n_audio_cleanup`) | `py_cleanup` | `Toolhub Audio Cleanup` |
| WOL | `scripts/wol-cli.sh` | `/run` (`n8n_wol`) | `sh_wol_cli`, `wol-cli` | `Toolhub WOL` |
| DOCX render | `scripts/docx-render.py` | `/run` (`n8n_docx_render`) | `py_docx_render` | `Toolhub DOCX Render` |
| DOCX template fill | `scripts/docx-template-fill.py` | `/run` (`n8n_docx_template_fill`) | `docx-template-fill.fill_docx_template` | `Toolhub DOCX Template Fill` |
| PDF extract text | `scripts/pdf-extract-text.py` | `/run-file` (`n8n_pdf_extract_text`) | `py_pdf_extract_text`, `pdf_extract_text` | `Toolhub PDF Extract Text` |
| PDF info read | `scripts/pdf-info-read.py` | `/run-file` (`n8n_pdf_info_read`) | `py_pdf_info_read`, `pdf_info_read` | `Toolhub PDF Info` |
| OCR image | `scripts/ocr-image.py` | `/run-file` (`n8n_ocr_image`) | `py_ocr_image`, `ocr_image` | `Toolhub OCR Image` |
| HTML to Markdown | `scripts/html-to-markdown.py` | `/run` (`n8n_html_to_markdown`) | `py_html_to_markdown`, `html_to_markdown` | `Toolhub HTML to Markdown` |
| Markdown to HTML | `scripts/markdown-to-html.py` | `/run` (`n8n_markdown_to_html`) | `py_markdown_to_html`, `markdown_to_html` | `Toolhub Markdown to HTML` |
| Document convert | `scripts/document-convert.py` | `/run-file` (`n8n_document_convert`) | `py_document_convert`, `document_convert` | `Toolhub Document Convert` |
| XLSX read | `scripts/xlsx-read.py` | `/run-file` (`n8n_xlsx_read`) | `py_xlsx_read`, `xlsx_read` | `Toolhub XLSX Read` |
| Image convert | `scripts/image-convert.py` | `/run-file` (`n8n_image_convert`) | `py_image_convert`, `image_convert` | `Toolhub Image Convert` |
| GIF optimize | `scripts/gif-optimize.py` | `/run-file` (`n8n_gif_optimize`) | `py_gif_optimize`, `gif_optimize` | `Toolhub GIF Optimize` |
| Image metadata | `scripts/image-metadata.py` | `/run-file` (`n8n_image_metadata`) | `py_image_metadata`, `image_metadata` | `Toolhub Image Metadata` |
| Audio convert | `scripts/audio-convert.py` | `/run-file` (`n8n_audio_convert`) | `py_audio_convert`, `audio_convert` | `Toolhub Audio Convert` |
| JSON transform | `scripts/json-transform.py` | `/run` (`n8n_json_transform`) | `py_json_transform`, `json_transform` | `Toolhub JSON Transform` |
| YAML transform | `scripts/yaml-transform.py` | `/run` (`n8n_yaml_transform`) | `py_yaml_transform`, `yaml_transform` | `Toolhub YAML Transform` |
| Array stats | `scripts/array-stats.py` | `/run` (`n8n_array_stats`) | `py_array_stats`, `array_stats` | `Toolhub Array Stats` |
| HTTP fetch | `scripts/http-fetch.py` | `/run` (`n8n_http_fetch`) | `py_http_fetch`, `http_fetch` | `Toolhub HTTP Fetch` |
| Download aria2 | `scripts/download-aria2.py` | `/run` (`n8n_download_aria2`) | `py_download_aria2`, `download_aria2` | `Toolhub Download Aria2` |
| Download wget | `scripts/download-wget.py` | `/run` (`n8n_download_wget`) | `py_download_wget`, `download_wget` | `Toolhub Download Wget` |
| Curl request | `scripts/curl-request.py` | `/run` (`n8n_curl_request`) | `py_curl_request`, `curl_request` | `Toolhub Curl Request` |
| Archive unzip | `scripts/archive-unzip.py` | `/run-file` (`n8n_archive_unzip`) | `py_archive_unzip`, `archive_unzip` | `Toolhub Unzip` |
| Tree list | `scripts/tree-list.py` | `/run` (`n8n_tree_list`) | `py_tree_list`, `tree_list` | `Toolhub Tree List` |
| BC calc | `scripts/calc-bc.py` | `/run` (`n8n_calc_bc`) | `py_calc_bc`, `calc_bc` | `Toolhub BC Calc` |
| Git ops | `scripts/git-ops.py` | `/run` (`n8n_git_ops`) | `py_git_ops`, `git_ops` | `Toolhub Git` |
| Watch path | `scripts/watch-path.py` | `/run` (`n8n_watch_path`, optional) | `py_watch_path`, `watch_path` | - |

## Optional/Conditional MCP CLI Tools

Diese Tools sind nur registriert, wenn das jeweilige Binary im Image vorhanden ist:

- `ffmpeg`, `sox`, `magick`, `tesseract`, `pdftotext`, `pdfinfo`, `jq`, `yq`, `curl`, `wget`, `aria2c`, `exiftool`, `gifsicle`, `tree`, `unzip`, `bc`, `git`, `wakeonlan`
- `syft`, `grype`, `trivy`, `nuclei`
- zusätzlich: `ffprobe_info`, `tesseract_ocr`, `pdftotext_extract`, `pdfinfo_read`, `nuclei_safe`
