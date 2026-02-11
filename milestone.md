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
