from slack_bolt import App

from tomek_agent.bot.listeners import register_listeners
from tomek_agent.config import Settings


def create_app(settings: Settings) -> App:
    app = App(token=settings.slack_bot_token)
    register_listeners(app)
    return app
