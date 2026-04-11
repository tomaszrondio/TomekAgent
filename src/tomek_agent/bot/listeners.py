import structlog

from slack_bolt import App

logger = structlog.get_logger()


def register_listeners(app: App) -> None:
    @app.event("app_mention")
    def handle_mention(event: dict, say) -> None:
        user_id = event.get("user", "unknown")
        channel = event.get("channel", "")
        thread_ts = event.get("thread_ts") or event.get("ts")

        logger.info("mention_received", user=user_id, channel=channel)

        say(f"<@{user_id}> Hej! Jestem TomekAgent. Integracja z AI juz wkrotce.", thread_ts=thread_ts)
