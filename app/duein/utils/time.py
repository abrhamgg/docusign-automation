from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def calculate_due_date_utc(days: int) -> str:
    if days < 0:
        raise ValueError("days must be non-negative")

    tz_cst = ZoneInfo("America/Chicago")
    tz_utc = ZoneInfo("UTC")

    now_cst = datetime.now(tz_cst)
    target = (now_cst + timedelta(days=days)).replace(hour=10, minute=0, second=0, microsecond=0)
    target_utc = target.astimezone(tz_utc)

    iso = target_utc.isoformat()
    if iso.endswith("+00:00"):
        iso = iso.replace("+00:00", "Z")
    return iso