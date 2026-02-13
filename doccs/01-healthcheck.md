# Healthcheck & Service Info

## SSH

Nicht verfügbar als eigener SSH-Befehl.

## Webhook

### `GET /`
Liefert Service-Info und Endpunkt-Übersicht.

### `GET /test`
Liefert:

```json
{"status":"ok"}
```

### `POST /test`
Echo-Test mit JSON-Body.

Beispiel:

```bash
curl -sS http://localhost:5656/test
curl -sS -X POST http://localhost:5656/test \
  -H "Content-Type: application/json" \
  -d '{"ping":"pong"}'
```

## n8n Community Node

Kein eigener Node. Nutze `HTTP Request`.

## MCP

Nicht als eigener MCP-Toolname verfügbar.
