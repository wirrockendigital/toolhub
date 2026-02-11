# Milestone Log

## 2026-02-11

1. Projektstruktur gescannt (`README`, `README.mcp`, `scripts`, `src/mcp`, Docker/Compose).
2. Laufzeitarchitektur nachvollzogen: klassischer Toolhub-Container (`start.sh`, Flask/Gunicorn, `audio-split.sh`) plus separater TypeScript-MCP-Server.
3. Sicherheits- und Guardrail-Mechanik identifiziert (`SAFE_MODE`, Host-/Path-Allowlist, Rate-Limit, Output-Truncation).
4. Dokumentation und Implementierung gegengeprüft; Abweichungen für Review notiert (z. B. Request-Format bei `/audio-split`).
5. Ergebnisbericht vorbereitet mit aktuellem Stand, Komponentenrollen und offenen Risiken.
6. Dokumentation auf Ist-Verhalten der Flask-API angepasst (`README.md`, `docs/audio-split.md`): JSON-Request/JSON-Response, Endpoint-Übersicht ohne `/run`.
7. Projektziel und Reifegradanalyse durchgeführt: n8n-sidecar Nutzen, verfügbare Tool-Klassen, sowie nicht-funktionale/inkonsistente Bereiche (MCP-Tooling, Cron-Job, Dockerfile-Buildrisiken) identifiziert.

8. Merge-Konflikt in `src/mcp/tool-registry.ts` aufgelöst (vollständige Integration der `docx-template-fill`-Registry inkl. Manifest-Tool-Loader, fehlender Imports/Typen, Konfliktmarker entfernt, Datei wieder im normalen Modus gestaged).
9. PR-Merge-Konflikte beim Aktualisieren von `eric/audit-project-and-create-plan` mit `origin/main` gelöst (`CHANGELOG.md`, `src/mcp/tool-registry.ts`), Konfliktmarker entfernt und Branch für Commit vorbereitet.
10. Re-Scan auf nicht-funktionale Features durchgeführt (inkl. Verifikation per `py_compile`): Integrationslücken zwischen Webhook/MCP/Docker/Docs identifiziert und priorisierter Implementierungsplan mit Abnahmekriterien erstellt.
11. Phase 1 umgesetzt: `docx-template-fill` Syntaxfehler behoben, Cron-Aufruf auf aktuelle `audio-split.sh`-Flags migriert, Dockerfile-`fd`-Symlink robust gemacht und `docs/audio-split.md` auf JSON-API/JSON-Response korrigiert.
12. Phase 2 umgesetzt: MCP-Sidecar auf Toolhub-basierte Runtime mit Node/npm umgestellt (`Dockerfile.mcp` + `docker-compose.mcp.yml`), Build-Befehl auf vollständige Dependency-Installation korrigiert und Laufzeit-Allowlist/Volumes für reale Tool-Ausführung erweitert.
13. Phase 3 umgesetzt (Option B): Webhook `/run` erweitert um manifestbasierte CLI-Tools (`tool.json`), inklusive `args`- und `payload`-Support, Tool-Discovery beim Start und strukturierter CLI-Fehler-/Ergebnisrückgabe. README auf neue `/run`-Fähigkeiten und Env-Variablen aktualisiert.
14. Phase 4 umgesetzt: CI-Workflow für MCP-Build und Python-Tests ergänzt (`.github/workflows/ci.yml`), Release-Workflow auf GHCR vereinheitlicht (`docker-release.yml`) und README auf neue Release-/Webhook- und Env-Realität harmonisiert.
15. Vollständige Multi-Interface-Integration nachgezogen: `/run`-Script-Dispatch serialisiert verschachtelte Payload-Objekte (JSON), `docx-template-fill` in Python-Registry aufgenommen und Wrapper (`docx-render.py`, `docx-template-fill.py`) um direkte Flag-basierte Aufrufe erweitert, sodass SSH/Webhook/MCP dasselbe Toolset nutzen können.
16. MCP-Ergonomie und Discoverability verbessert: MCP-Metadatenblöcke für `audio-split.sh`, `transcript.py`, `cleanup.py`, `docx-render.py`, `docx-template-fill.py` und `wol-cli.sh` ergänzt; dadurch strukturierte Input-Schemas statt reiner `args`-Listen in MCP-Clients.
17. Container-Laufzeit gehärtet: Python-Toolmodule (`tools/`, `mcp_tools/`) werden ins Image nach `/opt/toolhub` kopiert, `TOOLHUB_PYTHON_ROOT` darauf standardisiert und Wrapper/Webhook mit Fallback auf `/workspace` versehen, damit Features auch ohne vollständigen Repo-Bind-Mount funktionsfähig bleiben.
18. E2E-Fixes aus Containerlauf: Leserechte auf `/opt/toolhub` explizit gesetzt, `netbase` für stabile `wakeonlan`-Ausführung ergänzt, `wol-cli`-Wrapper auf mehrere Runtime-Pfade robust gemacht und Start-Initialisierung um schreibbare DOCX-Verzeichnisse (`/templates`, `/output`, `/data/...`) erweitert.
19. Feature-Contract-Dokumentation ergänzt (`docs/features.md`): vollständige Matrix der verfügbaren Features pro Interface (SSH/Webhook/MCP), inklusive konkreter Aufrufbeispiele und Markierung optionaler/binär-abhängiger MCP-Tools.
20. Portainer-Deployment-Artefakt ergänzt (`toolhub.yaml`): einheitlicher Stack mit robusten Default-Variablen, Healthcheck, persistenten Volumes und stack-lokalem Netzwerk, damit Toolhub ohne zusätzlichen Compose-Merge direkt deploybar ist.
21. `toolhub.yaml` auf bestehende Netzwerkinfrastruktur angepasst: externes `allmydocker-net` verwendet und feste Container-IP `192.168.123.5` für den `toolhub`-Service gesetzt.
22. Portainer-Env-Setup erweitert: `toolhub.env` mit vollständigen Stack-/Runtime-Variablen erstellt und `toolhub.yaml` auf BASEDIR-basierten Volume-Pfadaufbau (`/volume2/docker`) umgestellt, inklusive variabler Netzwerk-/IP-Parameter.
23. Volume-Interpolation in `toolhub.yaml` auf strikt erforderliche Base-Variable umgestellt (`${TOOLHUB_BASEDIR:?TOOLHUB_BASEDIR is required}`), damit fehlende Portainer-Env-Variablen sofort als Konfigurationsfehler auffallen.
24. Alle Fallback-Interpolationen in `toolhub.yaml` entfernt: Variablen werden jetzt ausschließlich als `${VAR}` referenziert (keine `:-`/`:?`-Syntax), damit die Werte vollständig aus `toolhub.env` bzw. Portainer-Env stammen.
25. n8n-only OpenAI-Strategie im Stack umgesetzt: `OPENAI_*`-Variablen aus `toolhub.yaml` und `toolhub.env` entfernt, damit Toolhub keine OpenAI-Credentials erwartet und API-Anbindung vollständig in n8n verbleibt.
26. OpenAI-Integration vollständig aus Toolhub-Codebasis entfernt: `scripts/transcript.py` auf lokalen Whisper-Backend-only reduziert, zugehörige OpenAI-Dokumentation in `README.md`, `AGENTS.md` und `docs/features.md` bereinigt sowie veraltete Stack-Dateien `stack.yml`/`stack.env` durch `toolhub.yaml`/`toolhub.env` ersetzt.
27. README auf aktuellen Code-/Deployment-Stand harmonisiert: Referenzen auf `stack.yml`/`stack.env` und `/volume1` entfernt, Portainer-Flow auf `toolhub.yaml`/`toolhub.env` mit strikter Variablenauflösung dokumentiert, Variablenmatrix bereinigt und Feature-Contract (`docs/features.md`) als primäre Funktionsreferenz verlinkt.
28. Troubleshooting-Doku für Portainer-Deploy-Failures erweitert (`README.md`): konkreter Hinweis auf fehlende Bind-Mount-Verzeichnisse (inkl. `mkdir -p`-Snippet) sowie Netzwerkanforderung bei statischer IP (`ipv4_address` benötigt externes Netzwerk mit konfiguriertem Subnet).
