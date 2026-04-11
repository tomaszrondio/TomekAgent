# TomekAgent — Postepy projektu

## Status: Faza 2 zaimplementowana — wymaga OPENROUTER_API_KEY do testow

### Co jest zrobione

**Faza 1: Slack Bot MVP (Socket Mode)** ✅
- [x] Socket Mode (WebSocket, brak publicznego IP)
- [x] @mention handler — reaguje tylko w kanałach, zero DM
- [x] Odpowiada na tym samym poziomie co mention (kanał lub wątek)
- [x] Health check endpoint (:3000)
- [x] Structured JSON logging
- [x] Graceful shutdown
- [x] Docker + docker-compose

**Faza 2: Deep Agents Integration** ✅
- [x] `AsyncApp` + `AsyncSocketModeHandler` (async, non-blocking)
- [x] `create_deep_agent` z OpenRouter LLM (claude-sonnet-4-20250514)
- [x] Wbudowane middleware: TodoListMiddleware, FilesystemMiddleware, SummarizationMiddleware
- [x] Thread = Session (Slack thread_ts → LangGraph thread_id)
- [x] Thinking indicator ("Myślę..." → aktualizacja z odpowiedzią)
- [x] SQLite checkpointer — persistence rozmów (Docker volume `/app/data`)
- [x] InMemoryStore — cross-session memory agenta
- [x] Rate limiting per user (in-memory, daily reset)
- [x] Error handling z przyjaznym komunikatem
- [x] Custom tool: `get_current_time`

### Co trzeba zrobic przed uruchomieniem

1. Dodać `OPENROUTER_API_KEY=sk-or-v1-...` do pliku `.env`
   - Załóż konto na https://openrouter.ai, Keys → Create Key
   - Dodaj credits (~$5 na start)

2. Uruchomić lokalnie:
   ```
   PYTHONPATH=src python -m tomek_agent.main
   ```
   (lub `docker compose up -d` na serwerze)

### Jak testowac

1. `@TomekAgent Jaka jest stolica Francji?`
   → Bot postuje "Myślę...", po chwili aktualizuje z odpowiedzią AI
2. Follow-up w tym samym wątku: "A jaka jest populacja?"
   → Bot pamięta kontekst (wie, że chodzi o Francję)
3. Restart bota → wznów wątek
   → Kontekst odtworzony z SQLite (checkpoints.db)
4. `@TomekAgent która jest godzina?`
   → Używa narzędzia `get_current_time`
5. Złożone zadanie: "Zaplanuj mi roadmapę dla projektu X"
   → Agent użyje `write_todos` do planowania

### Struktura plików

```
src/tomek_agent/
├── main.py              # async entrypoint
├── config.py            # Settings (Slack + OpenRouter + storage)
├── bot/
│   ├── app.py           # AsyncApp factory
│   └── listeners.py     # @mention → agent pipeline + rate limiting
├── agent/
│   ├── factory.py       # create_deep_agent + OpenRouter LLM
│   ├── session.py       # thread_ts → thread_id mapping
│   ├── tools.py         # custom tools (get_current_time)
│   └── prompts.py       # system prompt
└── storage/
    └── persistence.py   # AsyncSqliteSaver + InMemoryStore
```

### Kluczowe decyzje projektowe

- **LLM**: OpenRouter (base_url: openrouter.ai/api/v1) — kompatybilny z OpenAI SDK
- **Model domyslny**: `anthropic/claude-sonnet-4-20250514`
- **Bot reaguje TYLKO na @mentions** w kanałach — zero DM
- **Checkpointing**: SQLite na Docker volume `/app/data/checkpoints.db`
- **Memory**: InMemoryStore (ginie przy restarcie — wystarczy na start)
- **Rate limiting**: 50 zapytań/dzień per user (in-memory, reset o północy UTC)
- **Middleware**: deepagents domyślnie dodaje TodoList + Filesystem + Summarization

### Co zostalo do zrobienia (opcjonalnie)

- [ ] Persistent InMemoryStore → SQLite store (gdy memory musi przeżywać restart)
- [ ] Dodatkowe tools (web search z Tavily, inne)
- [ ] Testy jednostkowe
- [ ] Upgrade Dockerfile do instalacji z uv.lock
