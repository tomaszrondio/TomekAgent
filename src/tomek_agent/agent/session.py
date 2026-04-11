def get_thread_id(channel_id: str, thread_ts: str | None, event_ts: str) -> str:
    """Map a Slack event to a unique LangGraph thread_id.

    - Mention in a thread → uses thread_ts (all replies share one session)
    - Top-level mention  → uses event_ts (each message starts a new session)
    """
    ts = thread_ts or event_ts
    return f"{channel_id}:{ts}"
