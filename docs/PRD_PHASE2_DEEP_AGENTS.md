# PRD: TomekAgent — Faza 2: Integracja z LangChain Deep Agents

## 1. Cel produktu

Rozszerzenie Slack bota z Fazy 1 o agenta AI opartego na LangChain Deep Agents. Każdy wątek Slack staje się niezależną sesją agenta z planowaniem, pamięcią kontekstową i narzędziami. LLM dostarczany przez OpenRouter (dostęp do wielu modeli z jednego API key).

### Zależność od Fazy 1
Ta faza wymaga działającego bota Slack z Fazy 1 (Socket Mode, Docker, @mention handling).

## 2. Użytkownicy

- Mały zespół (2-10 osób) w jednym workspace Slack
- Interakcja wyłącznie przez @mentions w kanałach
- Każdy użytkownik może mieć równoległe rozmowy w różnych wątkach

## 3. Funkcjonalności

| Funkcja | Opis | Priorytet |
|---|---|---|
| **Conversational AI** | `@TomekAgent <pytanie>` → odpowiedź AI w wątku | P0 |
| **Thread = Session** | Każdy wątek Slack = osobna sesja agenta z pełną historią | P0 |
| **Thinking indicator** | Bot postuje "Myślę..." i aktualizuje wiadomość z odpowiedzią | P0 |
| **Planning** | Agent automatycznie rozkłada złożone zadania na kroki (write_todos) | P1 |
| **Context management** | FilesystemMiddleware — wirtualny scratchpad per sesja | P1 |
| **Auto-summarization** | Automatyczne skracanie długich rozmów w kontekście | P1 |
| **Long-term memory** | Zapamiętywanie faktów między sesjami (MemoryMiddleware) | P2 |
| **Web search** | Narzędzie wyszukiwania w internecie (Tavily/inne) | P2 |
| **Per-user logging** | Logowanie użycia tokentów per user | P1 |
| **Rate limiting** | Basic limit zapytań per user (np. 50/dzień) | P2 |
| **Error handling** | Błędy agenta → przyjazna wiadomość w Slack, nie cichy crash | P0 |

## 4. Tech stack

| Komponent | Technologia | Uzasadnienie |
|---|---|---|
| Agent framework | `deepagents` | Built-in planning, filesystem, sub-agents, summarization |
| LLM provider | OpenRouter | Jeden API key, dostęp do wielu modeli (Claude, GPT, Gemini, open-source) |
| LLM SDK | `langchain-openai` | OpenRouter jest kompatybilny z OpenAI API (custom `base_url`) |
| State persistence | SQLite (LangGraph Checkpointer) | Lokalny, bez zewnętrznej bazy, Docker volume |
| Long-term memory | SQLite (LangGraph Store) | Persistence faktów między sesjami |
| Async | `AsyncApp` + `AsyncSocketModeHandler` | Agent calls są I/O-bound, async zapobiega blokowaniu |
| Storage | Docker named volume | Przetrwa restart kontenera |

## 5. Architektura

```
Slack Cloud
    │
    │ WebSocket (Socket Mode)
    │
    ▼
┌──────────────────────────────────────────────────┐
│  Docker Container                                │
│                                                  │
│  AsyncSocketModeHandler                          │
│       │                                          │
│       ▼                                          │
│  slack_bolt AsyncApp                             │
│       │                                          │
│       ├── @mention → agent pipeline:             │
│       │   1. Post "Myślę..." (chat.postMessage)  │
│       │   2. Map thread_ts → session_id          │
│       │   3. Invoke deep agent (async)           │
│       │   4. Update msg z odpowiedzią             │
│       │                                          │
│       └── /tomek → help/config                   │
│                                                  │
│  Agent Layer:                                    │
│  ┌────────────────────────────────────────┐      │
│  │ create_deep_agent()                    │      │
│  │   ├── model: OpenRouter LLM           │      │
│  │   ├── middleware:                      │      │
│  │   │   ├── TodoListMiddleware           │      │
│  │   │   ├── FilesystemMiddleware         │      │
│  │   │   ├── SummarizationMiddleware      │      │
│  │   │   └── MemoryMiddleware             │      │
│  │   └── tools: [web_search, time, ...]  │      │
│  └────────────────────────────────────────┘      │
│                                                  │
│  Storage (Docker volume → /app/data/):           │
│  ├── checkpoints.db (conversation state)         │
│  └── memory.db (long-term memory)                │
│                                                  │
│  HTTP health server (:3000)                      │
└──────────────────────────────────────────────────┘
```

## 6. Kluczowe decyzje projektowe

### 6.1 OpenRouter + Deep Agents

Deep Agents akceptuje zainicjalizowane instancje modeli LangChain. OpenRouter jest kompatybilny z OpenAI SDK:

```python
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4-20250514",  # dowolny model z OpenRouter
    openai_api_key=os.environ["OPENROUTER_API_KEY"],
    openai_api_base="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://tomekagent.local",
        "X-Title": "TomekAgent",
    },
)

agent = create_deep_agent(
    model=llm,
    tools=[web_search, get_current_time],
    system_prompt="Jesteś TomekAgent — pomocny asystent AI dla zespołu.",
)
```

### 6.2 Thread-to-Session mapping

Mapowanie Slack thread_ts → LangGraph thread_id:

```python
# session.py
def get_thread_id(channel_id: str, thread_ts: str | None, event_ts: str) -> str:
    """
    Generuje unikalny thread_id dla LangGraph.
    - Jeśli wiadomość jest w wątku: używa thread_ts
    - Jeśli to nowa wiadomość (bez wątku): używa event_ts (staje się nowym wątkiem)
    """
    ts = thread_ts or event_ts
    return f"{channel_id}:{ts}"
```

Efekt: każdy wątek Slack to osobna konwersacja z agentem. Follow-upy w wątku korzystają z pełnej historii.

### 6.3 Agent invocation flow

```
1. Slack event: app_mention
2. Listener extracts: user_id, channel_id, thread_ts, text
3. Post "Myślę..." message → get msg_ts
4. session.get_thread_id(channel_id, thread_ts, event_ts) → thread_id
5. agent.ainvoke(
     {"messages": [HumanMessage(content=text)]},
     config={"configurable": {"thread_id": thread_id}},
   )
6. Extract response text from result["messages"][-1].content
7. chat.update(channel, msg_ts, text=response)  # update "Myślę..."
8. Log: user_id, channel_id, thread_id, token_usage
```

### 6.4 Async migration

Faza 2 wymaga przejścia z sync na async:

```python
# main.py (Faza 2)
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

app = AsyncApp(token=settings.slack_bot_token)

# listeners używają async def
@app.event("app_mention")
async def handle_mention(event, say, client):
    ...
    result = await agent.ainvoke(...)
    ...

async def main():
    handler = AsyncSocketModeHandler(app, settings.slack_app_token)
    await handler.start_async()
```

### 6.5 Error handling

```python
try:
    result = await agent.ainvoke(...)
    response = result["messages"][-1].content
except Exception as e:
    logger.error("agent_error", error=str(e), user=user_id, thread=thread_id)
    response = "Przepraszam, wystąpił błąd. Spróbuj ponownie za chwilę."

await client.chat_update(channel=channel_id, ts=thinking_msg_ts, text=response)
```

## 7. Struktura projektu (rozszerzenie Fazy 1)

```
src/tomek_agent/
├── __init__.py
├── main.py                  # Zmieniony: AsyncApp + AsyncSocketModeHandler
├── config.py                # Rozszerzony: nowe env vars (OpenRouter, model, data_dir)
├── bot/
│   ├── __init__.py
│   ├── app.py               # Zmieniony: AsyncApp factory
│   └── listeners.py         # Zmieniony: agent invocation zamiast canned responses
├── agent/                   # NOWY moduł
│   ├── __init__.py
│   ├── factory.py           # create_deep_agent wrapper + OpenRouter LLM config
│   ├── tools.py             # Custom tools (web_search, get_current_time, ...)
│   ├── prompts.py           # System prompts
│   └── session.py           # thread_ts → thread_id mapping
└── storage/                 # NOWY moduł
    ├── __init__.py
    └── persistence.py       # SQLite checkpointer + store setup
```

## 8. Custom tools

### 8.1 get_current_time

```python
from datetime import datetime

def get_current_time(timezone: str = "Europe/Warsaw") -> str:
    """Zwraca aktualną datę i godzinę w podanej strefie czasowej."""
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo(timezone))
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")
```

### 8.2 web_search (opcjonalny)

```python
from tavily import TavilyClient

def web_search(query: str, max_results: int = 5) -> str:
    """Wyszukuje informacje w internecie."""
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    results = client.search(query, max_results=max_results)
    return "\n".join(
        f"- {r['title']}: {r['content'][:200]}" for r in results["results"]
    )
```

### 8.3 Potencjalne przyszłe tools

| Tool | Opis | Kiedy dodać |
|---|---|---|
| `search_slack_history` | Przeszukiwanie historii kanału | Gdy team będzie potrzebować |
| `create_reminder` | Ustawianie przypomnień | Gdy dojdzie productivity flow |
| `run_code` | Wykonywanie kodu Python w sandboxie | Dla code assistance |
| `read_url` | Odczyt treści ze strony WWW | Dla research tasks |

## 9. Konfiguracja (nowe zmienne środowiskowe)

| Zmienna | Wymagana | Opis | Przykład |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Tak | Klucz API z openrouter.ai | `sk-or-v1-...` |
| `LLM_MODEL` | Nie | Model z OpenRouter (default: `anthropic/claude-sonnet-4-20250514`) | `openai/gpt-4o` |
| `DATA_DIR` | Nie | Katalog na dane SQLite (default: `/app/data`) | `/app/data` |
| `MAX_TOKENS` | Nie | Max tokenów w odpowiedzi (default: 4096) | `4096` |
| `TAVILY_API_KEY` | Nie | Klucz API Tavily (web search) | `tvly-...` |
| `RATE_LIMIT_PER_USER` | Nie | Max zapytań/dzień per user (default: 50) | `100` |

### `.env.example` (rozszerzony)

```env
# Slack (z Fazy 1)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-level-token

# LLM
OPENROUTER_API_KEY=sk-or-v1-your-key
LLM_MODEL=anthropic/claude-sonnet-4-20250514

# Storage
DATA_DIR=/app/data

# Optional
LOG_LEVEL=INFO
HEALTH_PORT=3000
MAX_TOKENS=4096
TAVILY_API_KEY=tvly-your-key
RATE_LIMIT_PER_USER=50
```

## 10. Docker (zmiany względem Fazy 1)

### docker-compose.yml (zaktualizowany)

```yaml
services:
  bot:
    build: .
    env_file: .env
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - tomek_data:/app/data    # NOWE: persistence
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s         # Dłuższy start (ładowanie agenta)
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  tomek_data:                    # NOWE: named volume
```

## 11. Persistence & Storage

### SQLite Checkpointer (conversation state)
- Plik: `/app/data/checkpoints.db`
- Przechowuje stan konwersacji LangGraph per thread_id
- Umożliwia wznowienie rozmowy po restarcie kontenera

### SQLite Store (long-term memory)
- Plik: `/app/data/memory.db`
- Przechowuje fakty i wiedzę agenta między sesjami
- Używany przez MemoryMiddleware

```python
# storage/persistence.py
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore

async def create_checkpointer(data_dir: str) -> AsyncSqliteSaver:
    return AsyncSqliteSaver.from_conn_string(f"{data_dir}/checkpoints.db")

async def create_store(data_dir: str) -> AsyncSqliteStore:
    return AsyncSqliteStore.from_conn_string(f"{data_dir}/memory.db")
```

## 12. Rate limiting

Prosty mechanizm per-user:

```python
# Słownik: user_id -> [timestamps]
# Sprawdzany przed wywołaniem agenta
# Jeśli przekroczony limit → odpowiedź "Przekroczyłeś limit X zapytań dziennie"
# Reset o północy (UTC)
```

Nie wymaga bazy danych — in-memory wystarczy dla małego zespołu. Stan ginie przy restarcie (akceptowalne).

## 13. OpenRouter — setup krok po kroku

1. Wejdź na https://openrouter.ai
2. Załóż konto (GitHub/Google login)
3. Przejdź do **Keys** → **Create Key**
4. Skopiuj klucz (`sk-or-v1-...`) → to jest `OPENROUTER_API_KEY`
5. Dodaj credits (pay-as-you-go) — minimalna kwota ~$5
6. Dostępne modele: https://openrouter.ai/models
   - Rekomendacja: `anthropic/claude-sonnet-4-20250514` (dobry balans cena/jakość)
   - Alternatywy: `openai/gpt-4o`, `google/gemini-2.5-flash`, `meta-llama/llama-4-maverick`

## 14. Migracja z Fazy 1 → Faza 2

| Plik | Zmiana |
|---|---|
| `config.py` | Dodanie: `openrouter_api_key`, `llm_model`, `data_dir`, `max_tokens`, `rate_limit_per_user` |
| `bot/app.py` | Zmiana: `App` → `AsyncApp` |
| `bot/listeners.py` | Zmiana: canned responses → agent invocation, async def, thinking indicator |
| `main.py` | Zmiana: sync → async, `AsyncSocketModeHandler`, init storage |
| `agent/*` | NOWE: factory, tools, prompts, session |
| `storage/*` | NOWE: persistence setup |
| `docker-compose.yml` | Dodanie: volume `tomek_data` |
| `pyproject.toml` | Dodanie: `deepagents`, `langchain-openai`, `tavily-python` |

## 15. Weryfikacja

| # | Test | Oczekiwany rezultat |
|---|---|---|
| 1 | `docker compose up -d` | Kontener startuje, logi: "Agent initialized", "Bot connected" |
| 2 | `@TomekAgent Jaka jest stolica Francji?` | Bot postuje "Myślę...", po chwili aktualizuje z odpowiedzią AI |
| 3 | Follow-up w wątku: "A jaka jest populacja?" | Bot odpowiada z kontekstem (wie, że chodzi o Francję) |
| 4 | `docker compose restart bot` → wznów wątek | Bot pamięta historię konwersacji z SQLite |
| 5 | Sprawdź logi | Token usage per user, model info |
| 6 | Wyślij >50 wiadomości jednego dnia | Bot informuje o limicie |
| 7 | Złożone pytanie wymagające planowania | Bot używa write_todos, rozkłada na kroki |
| 8 | Wiadomość bez @mention | Bot NIE reaguje |
| 9 | Symuluj błąd LLM (zły API key) | Bot odpowiada przyjaznym komunikatem błędu |
| 10 | `curl http://localhost:3000/health` | HTTP 200 |

## 16. Ryzyka i mitygacja

| Ryzyko | Mitygacja |
|---|---|
| OpenRouter downtime | Retry z backoff (langchain-openai domyślnie 6 prób). Fallback model w env var. |
| Latencja LLM (5-30s) | "Myślę..." indicator. Async pattern — inni userzy nie są blokowani. |
| Koszty API | Rate limiting per user. Logowanie token usage. Tańsze modele jako opcja. |
| deepagents 0.x instability | Pin wersji w pyproject.toml. Abstraction layer w factory.py. |
| SQLite concurrent writes | Jeden writer wystarczy dla 2-10 userów. WAL mode dla lepszej wydajności. |
| Utrata danych (restart) | Docker named volume. SQLite z WAL przetrwa nawet nagły restart. |

## 17. Poza zakresem (Faza 2)

- Streaming responses (word-by-word update w Slack)
- Sub-agents spawning (wykorzystanie pełnego potencjału Deep Agents)
- Sandboxed code execution
- Multi-workspace support
- Obsługa DM/wiadomości prywatnych
- GUI / dashboard administracyjny
