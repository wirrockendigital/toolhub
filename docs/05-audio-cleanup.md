# Audio Cleanup

Rotiert große Logs und entfernt alte Temp-Artefakte.

## SSH

Script: `scripts/cleanup.py`

Beispiel:

```bash
/scripts/cleanup.py \
  --dry-run \
  --logs-dir /logs \
  --tmp-dir /tmp \
  --tmp-max-age-hours 24
```

Wichtige Parameter:
- `--logs-dir`
- `--tmp-dir`
- `--max-log-size-mb`
- `--max-log-backups`
- `--tmp-max-age-hours`
- `--tmp-prefixes`
- `--dry-run`

## Webhook

Über `POST /run` mit Alias `n8n_audio_cleanup`.

```bash
curl -sS -X POST http://localhost:5656/run \
  -H "Content-Type: application/json" \
  -d '{
    "tool":"n8n_audio_cleanup",
    "payload":{
      "dry_run":true,
      "tmp_max_age_hours":24
    }
  }'
```

## n8n Community Node

Node: `Toolhub Audio Cleanup`

Felder:
- `Dry Run`
- `Logs Directory`
- `Temp Directory`
- `Temp Max Age Hours`

## MCP

Toolname:
- `py_cleanup`
