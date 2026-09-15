import calendar
from datetime import datetime, timedelta, timezone


def utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return f"{value.isoformat()}Z"
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def add_months(anchor: datetime, months: int) -> datetime:
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return anchor.replace(year=year, month=month, day=day)


def next_occurrence(
    starts_at: datetime,
    recurrence: str,
    now: datetime | None = None,
) -> datetime:
    anchor = utc_naive(starts_at)
    current = utc_naive(now or datetime.now(timezone.utc))
    if recurrence == "none" or anchor >= current:
        return anchor

    if recurrence in {"daily", "weekly"}:
        step = timedelta(days=1 if recurrence == "daily" else 7)
        steps = max(0, int((current - anchor).total_seconds() // step.total_seconds()))
        candidate = anchor + (step * steps)
        return candidate if candidate >= current else candidate + step

    if recurrence == "monthly":
        months = max(0, (current.year - anchor.year) * 12 + current.month - anchor.month)
        candidate = add_months(anchor, months)
        return candidate if candidate >= current else add_months(anchor, months + 1)

    return anchor


def occurrences_between(
    starts_at: datetime,
    recurrence: str,
    window_start: datetime,
    window_end: datetime,
    *,
    limit: int = 100,
) -> list[datetime]:
    """Return bounded concrete occurrence starts inside an inclusive UTC-naive window."""
    start = utc_naive(window_start)
    end = utc_naive(window_end)
    if end < start or limit <= 0:
        return []

    anchor = utc_naive(starts_at)
    if recurrence == "none":
        return [anchor] if start <= anchor <= end else []

    current = next_occurrence(anchor, recurrence, start)
    values: list[datetime] = []
    while current <= end and len(values) < limit:
        if current >= start:
            values.append(current)
        if recurrence == "daily":
            current += timedelta(days=1)
        elif recurrence == "weekly":
            current += timedelta(days=7)
        elif recurrence == "monthly":
            current = add_months(current, 1)
        else:
            break
    return values
