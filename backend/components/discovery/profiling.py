from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from components.discovery.service import discover_spaces


@dataclass(frozen=True, slots=True)
class DiscoveryProfile:
    result_count: int
    statement_count: int
    select_count: int
    database_elapsed_ms: float
    wall_elapsed_ms: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


async def profile_discovery(
    db: AsyncSession,
    viewer_uid: UUID | str,
    *,
    query: str | None = None,
    purpose: str | None = None,
    tag: str | None = None,
    limit: int = 30,
    offset: int = 0,
) -> tuple[list[dict], DiscoveryProfile]:
    """Measure one discovery call without changing its ranking semantics.

    The profiler counts actual SQL cursor executions on this session's bind and
    records database/wall time. It never records SQL parameters, identifiers or
    result payloads, so it is safe to use as an operational diagnostic.
    """
    bind = db.get_bind()
    statement_count = 0
    select_count = 0
    database_elapsed_seconds = 0.0

    def before_cursor_execute(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        nonlocal statement_count, select_count
        statement_count += 1
        normalized = str(statement).lstrip().upper()
        if normalized.startswith(("SELECT", "WITH")):
            select_count += 1
        context._pubchat_discovery_profile_started = perf_counter()

    def after_cursor_execute(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        nonlocal database_elapsed_seconds
        started = getattr(context, "_pubchat_discovery_profile_started", None)
        if started is not None:
            database_elapsed_seconds += perf_counter() - started

    event.listen(bind, "before_cursor_execute", before_cursor_execute)
    event.listen(bind, "after_cursor_execute", after_cursor_execute)
    started = perf_counter()
    try:
        result = await discover_spaces(
            db,
            viewer_uid,
            query=query,
            purpose=purpose,
            tag=tag,
            limit=limit,
            offset=offset,
        )
    finally:
        wall_elapsed_seconds = perf_counter() - started
        event.remove(bind, "before_cursor_execute", before_cursor_execute)
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    return result, DiscoveryProfile(
        result_count=len(result),
        statement_count=statement_count,
        select_count=select_count,
        database_elapsed_ms=round(database_elapsed_seconds * 1000, 3),
        wall_elapsed_ms=round(wall_elapsed_seconds * 1000, 3),
    )
