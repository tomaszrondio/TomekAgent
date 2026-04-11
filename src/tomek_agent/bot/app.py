from slack_bolt.async_app import AsyncApp

from tomek_agent.bot.listeners import register_listeners
from tomek_agent.config import Settings


def create_app(settings: Settings, agent) -> AsyncApp:
    app = AsyncApp(token=settings.slack_bot_token)
    register_listeners(app, agent, settings)
    return app
