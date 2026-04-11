import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import structlog

from tomek_agent.config import Settings
from tomek_agent.storage.persistence import create_checkpointer, create_store
from tomek_agent.agent.factory import create_agent
from tomek_agent.bot.app import create_app


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def _start_health_server(port: int) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def _run() -> None:
    settings = Settings()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )
    logger = structlog.get_logger()

    health_server = _start_health_server(settings.health_port)
    logger.info("health_server_started", port=settings.health_port)

    store = create_store()

    async with create_checkpointer(settings.data_dir) as checkpointer:
        agent = create_agent(settings, checkpointer, store)
        app = create_app(settings, agent)

        from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
        handler = AsyncSocketModeHandler(app, settings.slack_app_token)

        logger.info("bot_starting")
        try:
            await handler.start_async()
        finally:
            health_server.shutdown()
            logger.info("bot_stopped")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
