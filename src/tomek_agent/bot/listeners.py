import re
from collections import defaultdict
from datetime import datetime, timezone

import structlog
from langchain_core.messages import HumanMessage
from slack_bolt.async_app import AsyncApp

from tomek_agent.agent.session import get_thread_id
from tomek_agent.config import Settings

logger = structlog.get_logger()

# Rate limiting: user_id -> list of UTC dates (YYYY-MM-DD strings)
_user_requests: dict[str, list[str]] = defaultdict(list)


def _check_rate_limit(user_id: str, limit: int) -> bool:
    """Returns True if user is within the daily rate limit."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _user_requests[user_id] = [d for d in _user_requests[user_id] if d == today]
    if len(_user_requests[user_id]) >= limit:
        return False
    _user_requests[user_id].append(today)
    return True


def _strip_mention(text: str) -> str:
    """Remove the @mention prefix from the message text."""
    return re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()


def register_listeners(app: AsyncApp, agent, settings: Settings) -> None:
    @app.event("app_mention")
    async def handle_mention(event: dict, client, say) -> None:
        user_id = event.get("user", "unknown")
        channel_id = event.get("channel", "")
        thread_ts = event.get("thread_ts")
        event_ts = event.get("ts", "")
        raw_text = event.get("text", "")
        user_text = _strip_mention(raw_text)

        logger.info("mention_received", user=user_id, channel=channel_id, in_thread=thread_ts is not None)

        if not _check_rate_limit(user_id, settings.rate_limit_per_user):
            await say(
                f"<@{user_id}> Przekroczyłeś dzienny limit {settings.rate_limit_per_user} zapytań. Spróbuj jutro.",
                thread_ts=thread_ts,
            )
            return

        # Post "Thinking..." indicator
        thinking_response = await client.chat_postMessage(
            channel=channel_id,
            text=":hourglass_flowing_sand: Myślę...",
            thread_ts=thread_ts,
        )
        thinking_ts = thinking_response["ts"]

        thread_id = get_thread_id(channel_id, thread_ts, event_ts)
        logger.info("agent_invoke", user=user_id, thread_id=thread_id)

        try:
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_text)]},
                config={"configurable": {"thread_id": thread_id}},
            )
            response = result["messages"][-1].content
        except Exception as exc:
            logger.error("agent_error", error=str(exc), user=user_id, thread_id=thread_id)
            response = "Przepraszam, coś poszło nie tak. Spróbuj ponownie za chwilę."

        await client.chat_update(
            channel=channel_id,
            ts=thinking_ts,
            text=f"<@{user_id}> {response}",
        )

        logger.info("agent_done", user=user_id, thread_id=thread_id)
