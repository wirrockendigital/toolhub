# Toolhub MCP Server

The Toolhub MCP server exposes every existing Toolhub script or curated CLI as a Model Context Protocol (MCP) tool. The server is written in TypeScript and runs as a lightweight sidecar that communicates with MCP compatible clients (for example Claude Desktop or Codex IDE integrations).

## Architecture overview

- **Server runtime** – `src/mcp/server.ts` boots the MCP server using `@modelcontextprotocol/sdk` and serves tools over stdio.
- **Configuration** – `src/mcp/config.ts` centralises environment variables such as safe-mode toggles, allowlists and rate limits.
- **Security guardrails** – `src/mcp/security.ts` applies safe-mode policies, per-tool rate limiting and bounded output.
- **Tool discovery** – `src/mcp/discovery.ts` auto-discovers executable `.sh` and `.py` scripts under `/app/scripts` and parses optional metadata blocks.
- **Tool registry** – `src/mcp/tool-registry.ts` registers discovered scripts, allowlisted CLIs and handcrafted wrappers (e.g. `pdftotext_extract`).
- **Command execution** – `src/mcp/util/run.ts` executes commands via `execa`, enforces timeouts and truncates large responses.

Every script is converted into an MCP tool whose name is prefixed with `sh_` or `py_`, while curated CLIs and wrappers receive descriptive names (`ffprobe_info`, `nuclei_safe`, `run_script`, …).

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `SAFE_MODE` | `true` | Enables all guardrails. Disable only in trusted environments. |
| `ALLOWLIST_PATHS` | `/data,/tmp` | Comma separated list of path prefixes allowed for read/write operations. Scripts under `/app/scripts` are always allowed. |
| `ALLOWLIST_HOSTS` | `localhost,127.0.0.1` | Comma separated list of hostnames allowed for network tools (`curl`, `nuclei`, …). |
| `MCP_COMMAND_TIMEOUT_MS` | `120000` | Command timeout in milliseconds. |
| `MCP_MAX_OUTPUT` | `20000` | Maximum characters returned per tool invocation. |
| `MCP_RATE_LIMIT_COUNT` | `5` | Allowed invocations per window (per tool). |
| `MCP_RATE_LIMIT_WINDOW_MS` | `10000` | Rate limit window in milliseconds. |
| `MCP_SCRIPTS_ROOT` | `/app/scripts` | Directory scanned for Toolhub scripts. |
| `NUCLEI_TEMPLATES` | `/root/nuclei-templates` | Optional nuclei templates directory used by `nuclei_safe`. |

## Quickstart

```bash
docker compose -f docker-compose.yml -f docker-compose.mcp.yml up -d
```

The MCP sidecar installs dependencies, builds the TypeScript sources and exposes the MCP stdio endpoint. Any MCP-compatible client can connect by launching the container and binding to the process' stdio (e.g. Claude Desktop custom server integration).

To verify the tool registry locally without containers:

```bash
npm install
npm run build
npm run mcp:dev -- --list-tools
```

## Safe-mode guardrails

- Destructive commands (`rm -rf`, `mkfs`, `shutdown`, `reboot`, fork bombs) are blocked.
- Path access is restricted to allowlisted prefixes (plus Toolhub scripts) and hostnames must be allowlisted for network operations.
- `nuclei_safe` enforces informational severities and ignores exploit/CVE templates.
- Output is truncated to 20k characters and each tool is limited to five invocations per ten seconds.

## Script metadata convention

Scripts may include a JSON metadata block at the top of the file to override the default tool schema or description:

```bash
#!/usr/bin/env bash
#==MCP==
# {
#   "description": "Split audio into short fragments",
#   "schema": {
#     "type": "object",
#     "properties": {
#       "mode": {"type": "string", "enum": ["fixed", "silence"]},
#       "args": {"type": "array", "items": {"type": "string"}}
#     },
#     "required": ["mode"]
#   }
# }
#==/MCP==
```

The JSON is parsed and used for input validation and tool descriptions. All other lines remain untouched.

## Example tools

- `pdftotext_extract(path)` – stream text from a PDF (`pdftotext path -`).
- `pdfinfo_read(path)` – emit PDF metadata via `pdfinfo`.
- `ffprobe_info(path)` – return media metadata as JSON.
- `tesseract_ocr(imagePath, lang?)` – run OCR and return stdout.
- `nuclei_safe(url, tags?)` – nuclei scanner locked to informational templates.
- `run_script(name, args?)` – execute any discovered Toolhub script by tool name.

## MCP client integration

1. Start the Toolhub stack with the MCP sidecar.
2. Configure your MCP client to spawn `npm run mcp:start` (or `node dist/mcp/server.js`) in the container and connect over stdio.
3. Invoke `list-tools` to inspect the catalog. Newly added scripts in `/app/scripts` are discovered automatically without code changes.

## Testing

Run the smoke test to confirm basic server health:

```bash
scripts/tests/mcp-smoke.sh
```

The script installs dependencies on demand, executes the server in discovery mode and prints the first discovered tool.

## Security & limitations

The server is safe-mode first. Disabling guardrails or relaxing allowlists is discouraged in shared or production environments. The current JSON schema support covers common object/array primitives; complex JSON Schema features may require manual wrappers. Ensure third-party CLIs (`nuclei`, `syft`, `grype`, `trivy`, …) are installed in the container before exposing their respective tools.
