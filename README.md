# TomekAgent

A self-hosted Slack AI assistant built on LangChain Deep Agents. You @mention it in a channel, and each Slack thread becomes its own persistent agent session.

TomekAgent is a small, Dockerized Python service for team workspaces. It connects to Slack over **Socket Mode**, so it needs no public IP or inbound webhook. Each @mention goes to a [Deep Agents](https://github.com/langchain-ai/deepagents) agent (LangGraph), with the LLM served through **OpenRouter**. Conversation state is saved to SQLite, so a thread keeps its context after the bot restarts.

## Features

- **@mention-only interaction.** The bot replies only when mentioned in channels it has been invited to. It does not handle DMs or slash commands.
- **Thread = session.** Each Slack thread maps to its own LangGraph `thread_id`, and follow-ups in a thread share context. A top-level mention starts a new session.
- **Replies where it was mentioned.** If you mention it in a thread, it answers in that thread. If you mention it at the top level, it answers in the channel.
- **Thinking indicator.** The bot first posts a placeholder message, then edits that message to show the agent's answer.
- **Deep Agents capabilities.** It uses the default `create_deep_agent` middleware: task planning (todo list), a virtual filesystem scratchpad, conversation summarization, and tool-call patching.
- **Custom tool.** `get_current_time` returns the time for a given timezone (default `Europe/Warsaw`).
- **Persistent conversations.** An async SQLite checkpointer stores session state (`checkpoints.db`) on a Docker volume.
- **Per-user rate limiting.** Each user gets a configurable number of requests per day. The counter is in memory and resets daily (UTC).
- **Error handling.** If the agent fails, the user sees a friendly message and the error is logged.
- **Operational basics.** The service has structured JSON logging (structlog), an HTTP `/health` endpoint, and a Docker Compose healthcheck with log rotation.

## Tech stack

| Area | Technology |
|---|---|
| Language | Python 3.12 |
| Slack | `slack-bolt` (`AsyncApp` + `AsyncSocketModeHandler`), `slack-sdk` |
| Agent | `deepagents` (LangChain / LangGraph) |
| LLM | OpenRouter via `langchain-openai` (OpenAI-compatible API); default model `anthropic/claude-sonnet-4-20250514` |
| Persistence | `langgraph-checkpoint-sqlite` (`AsyncSqliteSaver`), LangGraph `InMemoryStore` |
| Config | `pydantic-settings` (`.env`) |
| Logging | `structlog` (JSON) |
| Runtime | Docker (multi-stage build with `uv`), Docker Compose |

## Architecture

```
Slack ──(WebSocket, Socket Mode)──► AsyncSocketModeHandler
                                         │
                                         ▼
                                  slack_bolt AsyncApp
                                  app_mention listener
                                   1. rate-limit check
                                   2. post placeholder message
                                   3. map channel + thread_ts → thread_id
                                   4. agent.ainvoke(...)
                                   5. update message with answer
                                         │
                                         ▼
                              Deep Agent (create_deep_agent)
                               ├─ LLM: OpenRouter (ChatOpenAI)
                               ├─ tools: get_current_time + built-ins
                               ├─ checkpointer: SQLite (/app/data)
                               └─ store: InMemoryStore

Side thread: HTTP health server → GET /health → {"status":"ok"}
```

## Getting started

### 1. Create a Slack app

1. Create an app at <https://api.slack.com/apps> ("From scratch").
2. **Socket Mode:** enable it and generate an app-level token with the `connections:write` scope. This is `SLACK_APP_TOKEN`.
3. **OAuth & Permissions:** add the bot scopes `app_mentions:read` and `chat:write`.
4. **Event Subscriptions:** enable events and subscribe to the `app_mention` bot event.
5. Install the app to your workspace and copy the Bot User OAuth Token. This is `SLACK_BOT_TOKEN`.
6. Invite the bot to a channel: `/invite @TomekAgent`.

### 2. Get an OpenRouter API key

Create a key at <https://openrouter.ai>. This is `OPENROUTER_API_KEY`.

### 3. Configure

```bash
cp .env.example .env
# fill in the values in .env
```

### 4. Run

With Docker (recommended):

```bash
docker compose up -d --build
curl http://localhost:3000/health   # {"status":"ok"}
```

Locally:

```bash
uv venv && uv pip install -e ".[dev]"
PYTHONPATH=src python -m tomek_agent.main
```

When running locally, set `DATA_DIR` to a writable path, because the default is `/app/data`.

### Usage

```
@TomekAgent What is the capital of France?
  └─ (reply in the same thread) And what's its population?   ← remembers context
@TomekAgent What time is it?                                  ← uses get_current_time
```

## Configuration

All settings are read from environment variables or `.env`. See `.env.example`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SLACK_BOT_TOKEN` | yes | | Slack bot token |
| `SLACK_APP_TOKEN` | yes | | Slack app-level token (Socket Mode) |
| `OPENROUTER_API_KEY` | yes | | OpenRouter API key |
| `LLM_MODEL` | no | `anthropic/claude-sonnet-4-20250514` | Any OpenRouter model ID |
| `MAX_TOKENS` | no | `4096` | Max tokens per LLM response |
| `DATA_DIR` | no | `/app/data` | Directory for `checkpoints.db` |
| `RATE_LIMIT_PER_USER` | no | `50` | Requests per user per day |
| `HEALTH_PORT` | no | `3000` | Port for the `/health` endpoint |
| `LOG_LEVEL` | no | `INFO` | Log level |

## Project structure

```
src/tomek_agent/
├── main.py              # async entrypoint: logging, health server, Socket Mode handler
├── config.py            # pydantic-settings Settings
├── bot/
│   ├── app.py           # AsyncApp factory
│   └── listeners.py     # @mention → agent pipeline, rate limiting
├── agent/
│   ├── factory.py       # create_deep_agent + OpenRouter LLM
│   ├── session.py       # Slack thread → LangGraph thread_id mapping
│   ├── tools.py         # custom tools (get_current_time)
│   └── prompts.py       # system prompt
└── storage/
    └── persistence.py   # AsyncSqliteSaver checkpointer + InMemoryStore
docs/                    # PRDs for Phase 1 / Phase 2 and progress notes (Polish)
Dockerfile
docker-compose.yml
```

## Notes and limitations

- The bot's system prompt and its user-facing messages are in **Polish**. The prompt tells the agent to reply in English when the user writes in English.
- The long-term memory store (`InMemoryStore`) and the rate-limit counters are kept in memory, so they reset on restart. Conversation checkpoints are saved to disk and survive restarts.
- Built with AI-assisted development (Claude Code).

## Roadmap

- Persist the long-term memory store in SQLite
- Add more tools (for example, web search)
- Unit tests
- A reproducible install from a lockfile
