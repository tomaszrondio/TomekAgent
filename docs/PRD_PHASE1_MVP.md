# PRD: TomekAgent — Faza 1: MVP Slack Bot

## 1. Cel produktu

Działający Slack bot uruchomiony w Socket Mode wewnątrz kontenera Docker na lokalnym serwerze Linux (bez publicznego IP). Bot reaguje wyłącznie na @mentions w kanałach, do których jest zaproszony. Faza 1 stanowi fundament infrastrukturalny pod przyszłą integrację z LangChain Deep Agents.

## 2. Użytkownicy

- Mały zespół (2-10 osób) w jednym workspace Slack
- Bot odpowiada tylko w kanałach, do których został zaproszony
- Brak obsługi wiadomości prywatnych (DM)

## 3. Funkcjonalności

| Funkcja | Opis | Priorytet |
|---|---|---|
| **Ping** | `@TomekAgent ping` → odpowiada "pong" + czas działania bota | P0 |
| **Help** | `@TomekAgent help` → lista dostępnych komend | P0 |
| **Slash command** | `/tomek` → menu pomocy z opisem bota | P0 |
| **Echo** | `@TomekAgent echo <tekst>` → powtarza tekst (test komunikacji) | P0 |
| **Health check** | HTTP endpoint `:3000/health` → 200 OK (dla Docker HEALTHCHECK) | P0 |
| **Structured logging** | JSON logi do stdout z identyfikacją usera i kanału | P1 |
| **Graceful shutdown** | Obsługa SIGTERM/SIGINT — czyste zamknięcie WebSocket | P1 |

## 4. Tech stack

| Komponent | Technologia | Wersja | Uzasadnienie |
|---|---|---|---|
| Język | Python | 3.12 | Kompatybilność z deepagents (>=3.11) |
| Framework Slack | slack_bolt | >=1.2.0 | Oficjalny SDK, natywny Socket Mode |
| Socket adapter | slack_bolt.adapter.socket_mode | built-in | Najprostszy adapter, bazuje na websocket-client |
| Konfiguracja | pydantic-settings | >=2.0 | Type-safe env vars, wsparcie .env |
| Logging | structlog | >=24.0 | JSON structured logging |
| Konteneryzacja | Docker + docker-compose | latest | Deployment na lokalnym serwerze |
| Package manager | uv | latest | Szybka instalacja zależności |

## 5. Architektura

```
Slack Cloud
    │
    │ WebSocket (Socket Mode)
    │
    ▼
┌─────────────────────────────────┐
│  Docker Container               │
│                                 │
│  SocketModeHandler              │
│       │                         │
│       ▼                         │
│  slack_bolt App                 │
│       ├── @mention listener     │
│       └── /tomek command        │
│                                 │
│  HTTP health server (:3000)     │
└─────────────────────────────────┘
```

### Flow obsługi wiadomości

1. User pisze `@TomekAgent ping` w kanale
2. Slack wysyła event `app_mention` przez WebSocket
3. `SocketModeHandler` odbiera event i przekazuje do `slack_bolt App`
4. Listener matchuje komendę "ping" i wywołuje `say("pong! Uptime: ...")`
5. Bot odpowiada w wątku (thread)

## 6. Struktura projektu

```
TomekAgent/
├── docs/
│   ├── PRD_PHASE1_MVP.md          # Ten dokument
│   └── PRD_PHASE2_DEEP_AGENTS.md  # PRD fazy 2
├── src/
│   └── tomek_agent/
│       ├── __init__.py
│       ├── main.py                 # Entrypoint: uruchamia SocketModeHandler + health server
│       ├── config.py               # Pydantic Settings — ładuje env vars
│       └── bot/
│           ├── __init__.py
│           ├── app.py              # Fabryka slack_bolt App
│           └── listeners.py        # Handlery: @mention, /tomek
├── tests/
│   ├── conftest.py
│   └── test_bot.py
├── Dockerfile                      # Multi-stage build
├── docker-compose.yml              # Orchestracja
├── pyproject.toml                  # Zależności + metadata
├── .env.example                    # Template zmiennych środowiskowych
└── .gitignore
```

## 7. Konfiguracja (zmienne środowiskowe)

| Zmienna | Wymagana | Opis | Przykład |
|---|---|---|---|
| `SLACK_BOT_TOKEN` | Tak | Bot User OAuth Token | `xoxb-...` |
| `SLACK_APP_TOKEN` | Tak | App-Level Token (Socket Mode) | `xapp-...` |
| `LOG_LEVEL` | Nie | Poziom logowania (default: INFO) | `DEBUG` |
| `HEALTH_PORT` | Nie | Port health check (default: 3000) | `3000` |

### `.env.example`
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-level-token
LOG_LEVEL=INFO
HEALTH_PORT=3000
```

## 8. Docker

### Dockerfile (multi-stage)

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder
RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 3000
ENTRYPOINT ["python", "-m", "tomek_agent.main"]
```

### docker-compose.yml

```yaml
services:
  bot:
    build: .
    env_file: .env
    restart: unless-stopped
    ports:
      - "3000:3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

## 9. Konfiguracja Slack App — krok po kroku

### 9.1 Utworzenie workspace (jeśli nie masz)
1. Wejdź na https://slack.com/get-started#/createnew
2. Utwórz nowy workspace (darmowy plan wystarczy)

### 9.2 Utworzenie aplikacji
1. Wejdź na https://api.slack.com/apps
2. Kliknij **"Create New App"** → **"From scratch"**
3. Nazwa: `TomekAgent`, wybierz swój workspace
4. Kliknij **"Create App"**

### 9.3 Włączenie Socket Mode
1. W panelu bocznym: **Settings** → **Socket Mode**
2. Włącz toggle **"Enable Socket Mode"**
3. Pojawi się prompt o App-Level Token:
   - Name: `socket-token`
   - Scope: `connections:write`
   - Kliknij **"Generate"**
4. **Skopiuj token** (`xapp-...`) → to jest `SLACK_APP_TOKEN`

### 9.4 Dodanie uprawnień bota
1. W panelu: **Features** → **OAuth & Permissions**
2. Sekcja **"Bot Token Scopes"** → **"Add an OAuth Scope"**
3. Dodaj następujące scopes:
   - `app_mentions:read` — odczyt @mentions
   - `chat:write` — wysyłanie wiadomości
   - `channels:history` — odczyt historii kanałów (kontekst)
   - `channels:read` — lista kanałów
   - `commands` — slash commands

### 9.5 Subskrypcja eventów
1. W panelu: **Features** → **Event Subscriptions**
2. Włącz toggle **"Enable Events"**
3. Sekcja **"Subscribe to bot events"** → **"Add Bot User Event"**
4. Dodaj: `app_mention`
5. Kliknij **"Save Changes"**

### 9.6 Slash command
1. W panelu: **Features** → **Slash Commands**
2. Kliknij **"Create New Command"**
3. Command: `/tomek`
4. Short Description: `TomekAgent — pomoc i komendy`
5. Kliknij **"Save"** (Request URL nie jest potrzebny w Socket Mode)

### 9.7 Instalacja w workspace
1. W panelu: **Settings** → **Install App**
2. Kliknij **"Install to Workspace"**
3. Autoryzuj uprawnienia
4. **Skopiuj "Bot User OAuth Token"** (`xoxb-...`) → to jest `SLACK_BOT_TOKEN`

### 9.8 Zaproszenie bota na kanał
1. W Slacku wejdź na kanał, na którym chcesz używać bota
2. Wpisz `/invite @TomekAgent` lub kliknij nazwę kanału → Integrations → Add apps

## 10. Opis modułów

### `src/tomek_agent/config.py`
Klasa `Settings(BaseSettings)` z pydantic-settings:
- Ładuje `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `LOG_LEVEL`, `HEALTH_PORT` z `.env`
- Walidacja typów na starcie

### `src/tomek_agent/bot/app.py`
Fabryka `create_app(settings) -> App`:
- Tworzy instancję `slack_bolt.App(token=settings.slack_bot_token)`
- Rejestruje listenery z `listeners.py`

### `src/tomek_agent/bot/listeners.py`
Handlery eventów:
- `handle_mention(event, say)` — parsuje tekst po @mention, dispatchuje komendy (ping, help, echo)
- `handle_tomek_command(ack, respond)` — obsługuje `/tomek`

### `src/tomek_agent/main.py`
Entrypoint:
- Inicjalizuje `Settings`
- Konfiguruje structlog
- Tworzy App via `create_app()`
- Uruchamia health server (threading + http.server) na `HEALTH_PORT`
- Uruchamia `SocketModeHandler(app, settings.slack_app_token).start()`
- Obsługuje SIGTERM/SIGINT dla graceful shutdown

## 11. Weryfikacja

| # | Test | Oczekiwany rezultat |
|---|---|---|
| 1 | `docker compose up -d` | Kontener startuje bez błędów |
| 2 | `docker compose logs -f bot` | Widać "Bot connected" w logach |
| 3 | `@TomekAgent ping` w kanale | Bot odpowiada "pong! Uptime: Xs" w wątku |
| 4 | `@TomekAgent help` w kanale | Bot wyświetla listę komend |
| 5 | `@TomekAgent echo test 123` | Bot odpowiada "test 123" |
| 6 | `/tomek` w kanale | Bot wyświetla menu pomocy (ephemeral) |
| 7 | `curl http://localhost:3000/health` | Zwraca HTTP 200 |
| 8 | `docker compose restart bot` | Bot reconnectuje w ciągu sekund |
| 9 | Wiadomość na kanale BEZ @mention | Bot NIE reaguje |
| 10 | DM do bota | Bot NIE odpowiada |

## 12. Poza zakresem (Faza 1)

- Integracja z AI/LLM (→ Faza 2)
- Obsługa DM/wiadomości prywatnych
- Baza danych / persistence
- Rate limiting (→ Faza 2)
- Monitoring / metryki (→ opcjonalnie)
