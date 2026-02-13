# Wake-on-LAN (WOL)

Senden von Magic Packets via MAC oder Alias.

## SSH

Script: `scripts/wol-cli.sh`

```bash
/scripts/wol-cli.sh AA:BB:CC:DD:EE:FF
```

## Webhook

Über `POST /run` mit Alias `n8n_wol`.

```bash
curl -sS -X POST http://localhost:5656/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool":"n8n_wol",
    "payload":{"target":"AA:BB:CC:DD:EE:FF"}
  }'
```

## n8n Community Node

Node: `Toolhub WOL`

Feld:
- `Target` (MAC oder Device-Alias)

## MCP

Toolnamen:
- `sh_wol_cli`
- `wol-cli`
