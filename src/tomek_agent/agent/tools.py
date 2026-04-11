from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_time(timezone: str = "Europe/Warsaw") -> str:
    """Zwraca aktualną datę i godzinę w podanej strefie czasowej."""
    now = datetime.now(ZoneInfo(timezone))
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")
