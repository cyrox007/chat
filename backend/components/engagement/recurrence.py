import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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


def _month_offset(anchor: datetime, current: datetime) -> int:
    return max(0, (current.year - anchor.year) * 12 + current.month - anchor.month)


def _timezone(name: str | None) -> ZoneInfo:
    normalized = (name or "UTC").strip() or "UTC"
    try:
        return ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"invalid IANA timezone: {normalized}") from exc


def _as_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _local_wall_to_utc_naive(local_value: datetime, zone: ZoneInfo) -> datetime:
    """Resolve one local wall-clock value into a durable UTC instant.

    Ambiguous fall-back times use fold=0 (the first occurrence). Non-existent
    spring-forward times shift forward by the DST gap via a UTC round-trip.
    """
    naive = local_value.replace(tzinfo=None)
    candidate = naive.replace(tzinfo=zone, fold=0)
    round_trip = candidate.astimezone(timezone.utc).astimezone(zone)
    if round_trip.replace(tzinfo=None) != naive:
        candidate = round_trip
    return candidate.astimezone(timezone.utc).replace(tzinfo=None)


def _local_anchor(starts_at: datetime, zone: ZoneInfo) -> datetime:
    return _as_utc_aware(starts_at).astimezone(zone).replace(tzinfo=None)


def _candidate_local(anchor: datetime, recurrence: str, index: int) -> datetime:
    if recurrence == "daily":
        return anchor + timedelta(days=index)
    if recurrence == "weekly":
        return anchor + timedelta(days=7 * index)
    if recurrence == "monthly":
        return add_months(anchor, index)
    return anchor


def _initial_index(anchor: datetime, current: datetime, recurrence: str) -> int:
    if recurrence == "daily":
        return max(0, (current.date() - anchor.date()).days)
    if recurrence == "weekly":
        return max(0, (current.date() - anchor.date()).days // 7)
    if recurrence == "monthly":
        return _month_offset(anchor, current)
    return 0


def next_occurrence(
    starts_at: datetime,
    recurrence: str,
    now: datetime | None = None,
    timezone_name: str = "UTC",
) -> datetime:
    """Return the next durable UTC instant while preserving local wall clock."""
    anchor_utc = utc_naive(starts_at)
    current_utc = utc_naive(now or datetime.now(timezone.utc))
    if recurrence == "none" or anchor_utc >= current_utc:
        return anchor_utc
    if recurrence not in {"daily", "weekly", "monthly"}:
        return anchor_utc

    zone = _timezone(timezone_name)
    anchor_local = _local_anchor(anchor_utc, zone)
    current_local = _as_utc_aware(current_utc).astimezone(zone).replace(tzinfo=None)
    index = _initial_index(anchor_local, current_local, recurrence)

    # The initial index is a close calendar estimate. At most a few increments
    # are needed around wall-clock/DST boundaries.
    for _ in range(4):
        candidate_utc = _local_wall_to_utc_naive(
            _candidate_local(anchor_local, recurrence, index),
            zone,
        )
        if candidate_utc >= current_utc:
            return candidate_utc
        index += 1

    # Defensive fallback for unexpected timezone transitions.
    while True:
        candidate_utc = _local_wall_to_utc_naive(
            _candidate_local(anchor_local, recurrence, index),
            zone,
        )
        if candidate_utc >= current_utc:
            return candidate_utc
        index += 1


def occurrences_between(
    starts_at: datetime,
    recurrence: str,
    window_start: datetime,
    window_end: datetime,
    *,
    timezone_name: str = "UTC",
    limit: int = 100,
) -> list[datetime]:
    """Return bounded UTC instants inside an inclusive window.

    Recurring calendar arithmetic happens in the stored IANA timezone so daily,
    weekly and monthly series keep their local wall-clock time across DST.
    """
    start = utc_naive(window_start)
    end = utc_naive(window_end)
    if end < start or limit <= 0:
        return []

    anchor = utc_naive(starts_at)
    if recurrence == "none":
        return [anchor] if start <= anchor <= end else []

    values: list[datetime] = []
    current = next_occurrence(
        anchor,
        recurrence,
        start,
        timezone_name=timezone_name,
    )
    while current <= end and len(values) < limit:
        values.append(current)
        current = next_occurrence(
            anchor,
            recurrence,
            current + timedelta(microseconds=1),
            timezone_name=timezone_name,
        )
    return values
