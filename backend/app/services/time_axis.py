"""Generate the canonical A-share intraday trading minute axis."""

from datetime import date, datetime, time, timedelta


def trading_minutes(trade_date: date) -> list[str]:
    """Return all HH:MM:SS slots for a standard A-share trading day.

    Morning session: 09:30 – 11:30 (121 minutes)
    Afternoon session: 13:00 – 15:00 (121 minutes)
    Total: 242 minutes
    """
    slots: list[str] = []
    for h, m in _minute_range(9, 30, 11, 30):
        slots.append(f"{h:02d}:{m:02d}:00")
    for h, m in _minute_range(13, 0, 15, 0):
        slots.append(f"{h:02d}:{m:02d}:00")
    return slots


def _minute_range(sh: int, sm: int, eh: int, em: int):
    current = datetime(2000, 1, 1, sh, sm)
    end = datetime(2000, 1, 1, eh, em)
    while current <= end:
        yield current.hour, current.minute
        current += timedelta(minutes=1)
