import re


def resolve_follow_up_days(status: str) -> int:
    if not status or not isinstance(status, str):
        raise ValueError("Invalid follow up status")

    s = status.strip().lower()

    if s.startswith("follow up daily"):
        return 1
    if s.startswith("follow up weekly"):
        return 7
    if s.startswith("follow up monthly"):
        return 30

    if re.search(r"\bdaily\b", s):
        return 1
    if re.search(r"\bweekly\b", s):
        return 7
    if re.search(r"\bmonthly\b", s):
        return 30

    raise ValueError(f"Unrecognized follow up status: {status}")