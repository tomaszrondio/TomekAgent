import signal
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import structlog

from tomek_agent.config import Settings
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
        pass  # suppress default http logs


def _start_health_server(port: int) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    settings = Settings()

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(settings.log_level)
        ),
    )

    logger = structlog.get_logger()

    app = create_app(settings)

    health_server = _start_health_server(settings.health_port)
    logger.info("health_server_started", port=settings.health_port)

    from slack_bolt.adapter.socket_mode import SocketModeHandler

    handler = SocketModeHandler(app, settings.slack_app_token)

    def shutdown(signum, frame):
        logger.info("shutdown_signal", signal=signum)
        health_server.shutdown()
        handler.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("bot_starting")
    handler.start()


if __name__ == "__main__":
    main()
