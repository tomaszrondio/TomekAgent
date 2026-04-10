# TomekAgent — Postepy projektu

## Status: Faza 1 MVP — gotowa do testow

### Co jest zrobione

**Faza 1: Slack Bot MVP (Socket Mode)**
- [x] Struktura projektu (src/tomek_agent/, tests/, docs/)
- [x] `config.py` — Pydantic Settings (SLACK_BOT_TOKEN, SLACK_APP_TOKEN, LOG_LEVEL, HEALTH_PORT)
- [x] `bot/app.py` — fabryka slack_bolt App
- [x] `bot/listeners.py` — handlery @mention (ping, help, echo) + /tomek slash command
- [x] `main.py` — entrypoint: structlog, health server (:3000), SocketModeHandler, graceful shutdown
- [x] `Dockerfile` — multi-stage build (uv + python:3.12-slim)
- [x] `docker-compose.yml` — env_file, restart: unless-stopped, healthcheck
- [x] PRD Phase 1 (`docs/PRD_PHASE1_MVP.md`)
- [x] PRD Phase 2 (`docs/PRD_PHASE2_DEEP_AGENTS.md`)

### Co trzeba przetestowac (Faza 1)

1. Skonfigurowac Slack App wg `docs/PRD_PHASE1_MVP.md` sekcja 9
2. Skopiowac `.env.example` -> `.env`, uzupelnic tokeny
3. `docker compose up -d` — sprawdzic czy kontener startuje
4. `@TomekAgent ping` — powinno odpowiedziec "pong! Uptime: Xs"
5. `@TomekAgent help` — lista komend
6. `@TomekAgent echo test` — powtorzy "test"
7. `/tomek` — menu pomocy
8. `curl http://localhost:3000/health` — powinno zwrocic 200
9. `docker compose restart bot` — bot reconnectuje

### Co zostalo do zrobienia

**Faza 2: Deep Agents Integration (nie rozpoczeta)**
- [ ] Konto OpenRouter + API key
- [ ] `agent/factory.py` — create_deep_agent wrapper z OpenRouter LLM
- [ ] `agent/session.py` — mapowanie thread_ts -> thread_id
- [ ] `agent/tools.py` — custom tools (get_current_time, web_search)
- [ ] `agent/prompts.py` — system prompts
- [ ] `storage/persistence.py` — SQLite checkpointer + store
- [ ] Migracja na AsyncApp + AsyncSocketModeHandler
- [ ] Refactor listeners.py — agent invocation zamiast canned responses
- [ ] Docker volume dla persistence
- [ ] Rate limiting per user
- [ ] Testy

### Decyzje projektowe

- **LLM Provider**: OpenRouter (kompatybilny z OpenAI SDK, base_url: openrouter.ai/api/v1)
- **Model domyslny**: anthropic/claude-sonnet-4-20250514
- **Bot reaguje TYLKO na @mentions** w kanalach — zero DM
- **Hosting**: lokalny serwer Linux, Docker, brak publicznego IP (Socket Mode)
- **Zespol**: 2-10 osob
