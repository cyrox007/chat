from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.moderation.media_model import ModerationMediaRecord
from components.moderation.media_service import PRIVATE_MEDIA_ROOT, PUBLIC_UPLOAD_ROOT, _validate_storage_roots
from components.moderation.model import (
    PlatformRestriction,
    PlatformRestrictionAppeal,
    TrustSafetyAuditEvent,
    TrustSafetyReport,
)
from settings import config


FINAL_REPORT_STATUSES = frozenset({"resolved", "dismissed"})


@dataclass(slots=True)
class MediaRetentionStats:
    candidates: int = 0
    purged: int = 0
    already_missing: int = 0
    deferred_active_report: int = 0
    deferred_pending_appeal: int = 0
    extended_after_finality: int = 0
    failed: int = 0


def _private_path_for_record(
    record: ModerationMediaRecord,
    *,
    private_root: Path = PRIVATE_MEDIA_ROOT,
) -> Path | None:
    """Resolve only this record's own private evidence path.

    The record UID is part of the confinement boundary so a corrupted relative
    path cannot make the retention worker unlink another evidence record.
    """
    raw = record.private_relative_path
    if not raw:
        return None

    relative = Path(raw)
    if relative.is_absolute() or len(relative.parts) < 2 or relative.parts[0] != str(record.uid):
        raise ValueError("invalid moderation evidence relative path")

    root = private_root.resolve()
    record_root = (root / str(record.uid)).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(record_root)
    except ValueError as exc:
        raise ValueError("moderation evidence path escapes record directory") from exc
    return candidate


def _durable_unlink(path: Path) -> bool:
    """Unlink one private evidence file and best-effort fsync its directory.

    This is application-level expiry, not a forensic secure-wipe guarantee for
    SSD/COW/storage snapshots. Storage-layer lifecycle policies remain separate.
    """
    if not path.exists():
        return False
    if not path.is_file():
        raise OSError("moderation evidence path is not a regular file")

    parent = path.parent
    path.unlink()

    try:
        fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        # Directory fsync is not uniformly supported across all dev filesystems.
        pass

    try:
        parent.rmdir()
    except OSError:
        pass
    return True


async def _has_pending_linked_appeal(db: AsyncSession, report_uid) -> bool:
    count = int(
        (
            await db.execute(
                select(func.count(PlatformRestrictionAppeal.uid))
                .join(
                    PlatformRestriction,
                    PlatformRestriction.uid == PlatformRestrictionAppeal.restriction_uid,
                )
                .where(
                    PlatformRestriction.report_uid == report_uid,
                    PlatformRestrictionAppeal.status == "pending",
                )
            )
        ).scalar_one()
        or 0
    )
    return count > 0


async def _latest_resolved_linked_appeal_at(
    db: AsyncSession,
    report_uid,
) -> datetime | None:
    return (
        await db.execute(
            select(func.max(PlatformRestrictionAppeal.resolved_at))
            .join(
                PlatformRestriction,
                PlatformRestriction.uid == PlatformRestrictionAppeal.restriction_uid,
            )
            .where(
                PlatformRestriction.report_uid == report_uid,
                PlatformRestrictionAppeal.resolved_at.is_not(None),
            )
        )
    ).scalar_one_or_none()


async def expire_due_media_evidence(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    batch_size: int | None = None,
    private_root: Path = PRIVATE_MEDIA_ROOT,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
) -> MediaRetentionStats:
    """Expire due removed evidence while preserving review and appeal safety."""
    _validate_storage_roots(upload_root, private_root)
    now = now or datetime.utcnow()
    batch_size = max(
        1,
        min(
            500,
            int(batch_size or config.MODERATION_MEDIA_RETENTION_BATCH_SIZE),
        ),
    )
    stats = MediaRetentionStats()

    result = await db.execute(
        select(ModerationMediaRecord)
        .where(
            ModerationMediaRecord.status == "removed",
            ModerationMediaRecord.purged_at.is_(None),
            ModerationMediaRecord.retention_due_at.is_not(None),
            ModerationMediaRecord.retention_due_at <= now,
        )
        .order_by(ModerationMediaRecord.retention_due_at.asc())
        .with_for_update(skip_locked=True)
        .limit(batch_size)
    )
    records = list(result.scalars().all())
    stats.candidates = len(records)

    for record in records:
        report = await db.get(TrustSafetyReport, record.report_uid)
        if report is None or report.status not in FINAL_REPORT_STATUSES:
            stats.deferred_active_report += 1
            continue

        if await _has_pending_linked_appeal(db, record.report_uid):
            stats.deferred_pending_appeal += 1
            continue

        latest_appeal_at = await _latest_resolved_linked_appeal_at(
            db, record.report_uid
        )
        finality_anchors = [
            value
            for value in (record.removed_at, report.resolved_at, latest_appeal_at)
            if value is not None
        ]
        if finality_anchors:
            effective_due_at = max(finality_anchors) + timedelta(
                days=config.MODERATION_MEDIA_REMOVED_RETENTION_DAYS
            )
            if record.retention_due_at is None or record.retention_due_at < effective_due_at:
                record.retention_due_at = effective_due_at
                record.updated_at = now
                if effective_due_at > now:
                    stats.extended_after_finality += 1
                    continue

        try:
            path = _private_path_for_record(record, private_root=private_root)
            deleted = _durable_unlink(path) if path is not None else False
        except (OSError, ValueError):
            stats.failed += 1
            continue

        if not deleted:
            stats.already_missing += 1

        # Keep the moderation decision/audit linkage, but scrub file-locating
        # metadata once the private evidence bytes have expired.
        record.private_relative_path = None
        record.original_url = None
        record.original_relative_path = None
        record.original_name = None
        record.mime_type = None
        record.purged_at = now
        record.updated_at = now
        db.add(
            TrustSafetyAuditEvent(
                report_uid=record.report_uid,
                actor_account_uid=None,
                event_type="media_evidence_expired",
                previous_status=None,
                next_status=None,
                note=(
                    f"record={record.uid};"
                    f"outcome={'deleted' if deleted else 'already_missing'}"
                ),
            )
        )
        stats.purged += 1

    await db.commit()
    return stats
