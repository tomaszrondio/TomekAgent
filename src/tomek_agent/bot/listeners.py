import re
import time

import structlog

from slack_bolt import App

logger = structlog.get_logger()

_start_time = time.monotonic()


def _uptime() -> str:
    elapsed = int(time.monotonic() - _start_time)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _parse_mention_text(text: str) -> str:
    """Strip the @mention prefix and return the command text."""
    return re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()


def register_listeners(app: App) -> None:
    @app.event("app_mention")
    def handle_mention(event: dict, say, client) -> None:
        user_id = event.get("user", "unknown")
        channel = event.get("channel", "")
        thread_ts = event.get("thread_ts") or event.get("ts")
        raw_text = event.get("text", "")
        command = _parse_mention_text(raw_text).lower()

        logger.info(
            "mention_received",
            user=user_id,
            channel=channel,
            command=command,
        )

        if command == "ping":
            say(f"pong! Uptime: {_uptime()}", thread_ts=thread_ts)

        elif command == "help":
            say(
                "*TomekAgent — dostepne komendy:*\n"
                "• `@TomekAgent ping` — sprawdz czy bot dziala\n"
                "• `@TomekAgent help` — ta wiadomosc\n"
                "• `@TomekAgent echo <tekst>` — powtorz tekst\n"
                "• `/tomek` — menu pomocy",
                thread_ts=thread_ts,
            )

        elif command.startswith("echo "):
            echo_text = _parse_mention_text(raw_text)[5:]  # preserve original case
            say(echo_text, thread_ts=thread_ts)

        else:
            say(
                f"Nie rozumiem komendy `{command}`. "
                "Wpisz `@TomekAgent help` zeby zobaczyc dostepne komendy.",
                thread_ts=thread_ts,
            )

    @app.command("/tomek")
    def handle_tomek_command(ack, respond) -> None:
        ack()
        logger.info("slash_command", command="/tomek")
        respond(
            "*TomekAgent*\n"
            "Bot asystent AI dla zespolu.\n\n"
            "*Uzycie:*\n"
            "• Wspomnij `@TomekAgent` na kanale z komenda\n"
            "• Dostepne komendy: `ping`, `help`, `echo <tekst>`\n\n"
            "_Faza 2: integracja z AI (w przygotowaniu)_"
        )
