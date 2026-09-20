from __future__ import annotations

import os
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from components.message.model import Message, PrivateMessage
from components.moderation.media_model import ModerationMediaRecord
from components.moderation.policy import assert_higher_authority
from components.moderation.trust_safety import _audit, _require_claim_owner


MEDIA_MANAGE_PERMISSION = "moderation.platform.media.manage"
PUBLIC_UPLOAD_ROOT = Path("uploads")
PRIVATE_MEDIA_ROOT = Path("moderation_media")


def _move_file(source: Path, destination: Path) -> None:
    """Move a file safely even when moderation storage is on another filesystem."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(source, destination)
        return
    except OSError:
        pass

    try:
        shutil.copy2(source, destination)
        source.unlink()
    except OSError:
        # Avoid leaving a partial destination behind when the source still exists.
        if source.exists() and destination.exists():
            try:
                destination.unlink()
            except OSError:
                pass
        raise


def _safe_public_path(url: str, *, upload_root: Path = PUBLIC_UPLOAD_ROOT) -> tuple[Path, str]:
    if not isinstance(url, str) or not url.startswith("/uploads/"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_not_local_upload"},
        )
    relative = url[len("/uploads/"):].lstrip("/")
    if not relative:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_invalid_path"},
        )
    root = upload_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_invalid_path"},
        ) from exc
    return candidate, relative


def _safe_private_path(
    record_uid: UUID,
    filename: str,
    *,
    private_root: Path = PRIVATE_MEDIA_ROOT,
) -> tuple[Path, str]:
    safe_name = Path(filename).name
    if not safe_name:
        safe_name = "attachment.bin"
    relative = f"{record_uid}/{safe_name}"
    root = private_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_invalid_private_path"},
        ) from exc
    return candidate, relative


async def _reported_message(db: AsyncSession, source_type: str, source_uid: UUID):
    if source_type == "messenger_message":
        result = await db.execute(
            select(PrivateMessage).where(PrivateMessage.uid == source_uid).limit(1)
        )
        return result.scalar_one_or_none()
    if source_type == "space_message":
        return await db.get(Message, source_uid)
    return None


def _attachment(message, attachment_index: int) -> tuple[dict, dict]:
    metadata = deepcopy(message.media_metadata or {})
    files = metadata.get("files")
    if not isinstance(files, list) or attachment_index < 0 or attachment_index >= len(files):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "moderation_media_attachment_not_found"},
        )
    item = files[attachment_index]
    if not isinstance(item, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_attachment_invalid"},
        )
    return metadata, item


def _set_attachment_status(message, attachment_index: int, value: str | None) -> None:
    metadata = deepcopy(message.media_metadata or {})
    files = metadata.get("files")
    if not isinstance(files, list) or attachment_index < 0 or attachment_index >= len(files):
        return
    item = dict(files[attachment_index] or {})
    if value:
        item["moderation_status"] = value
    else:
        item.pop("moderation_status", None)
    files[attachment_index] = item
    metadata["files"] = files
    message.media_metadata = metadata


def media_record_projection(item: ModerationMediaRecord) -> dict:
    return {
        "uid": str(item.uid),
        "report_uid": str(item.report_uid),
        "source_type": item.source_type,
        "source_uid": str(item.source_uid),
        "attachment_index": item.attachment_index,
        "target_account_uid": str(item.target_account_uid) if item.target_account_uid else None,
        "original_url": item.original_url,
        "mime_type": item.mime_type,
        "original_name": item.original_name,
        "status": item.status,
        "reason": item.reason,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "restored_at": item.restored_at.isoformat() if item.restored_at else None,
        "removed_at": item.removed_at.isoformat() if item.removed_at else None,
    }


async def quarantine_report_attachment(
    db: AsyncSession,
    *,
    report_uid: UUID,
    attachment_index: int,
    moderator_account_uid: UUID,
    reason: str,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
    private_root: Path = PRIVATE_MEDIA_ROOT,
) -> dict:
    report = await _require_claim_owner(db, report_uid, moderator_account_uid)
    if report.source_type not in {"messenger_message", "space_message"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_report_source_unsupported"},
        )
    if report.target_account_uid:
        await assert_higher_authority(db, moderator_account_uid, report.target_account_uid)

    message = await _reported_message(db, report.source_type, report.source_uid)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "trust_safety_source_not_found"},
        )
    _, attachment = _attachment(message, attachment_index)
    original_url = attachment.get("url")
    source_path, source_relative = _safe_public_path(original_url, upload_root=upload_root)

    existing_result = await db.execute(
        select(ModerationMediaRecord)
        .where(
            ModerationMediaRecord.report_uid == report.uid,
            ModerationMediaRecord.source_uid == report.source_uid,
            ModerationMediaRecord.attachment_index == attachment_index,
        )
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()
    if existing and existing.status in {"quarantined", "removed"}:
        return media_record_projection(existing)

    if not source_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_file_missing"},
        )

    record_uid = existing.uid if existing else uuid4()
    private_path, private_relative = _safe_private_path(
        record_uid,
        source_path.name,
        private_root=private_root,
    )
    private_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _move_file(source_path, private_path)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "moderation_media_quarantine_failed"},
        ) from exc

    now = datetime.utcnow()
    record = existing or ModerationMediaRecord(
        uid=record_uid,
        report_uid=report.uid,
        source_type=report.source_type,
        source_uid=report.source_uid,
        attachment_index=attachment_index,
        target_account_uid=report.target_account_uid,
        actor_account_uid=moderator_account_uid,
        original_url=original_url,
        original_relative_path=source_relative,
        private_relative_path=private_relative,
        mime_type=(attachment.get("type") or "")[:128] or None,
        original_name=(attachment.get("name") or "")[:255] or None,
        reason=reason.strip()[:1000],
    )
    if existing:
        record.actor_account_uid = moderator_account_uid
        record.reason = reason.strip()[:1000]
        record.private_relative_path = private_relative
    record.status = "quarantined"
    record.updated_at = now
    record.restored_at = None
    record.removed_at = None
    if not existing:
        db.add(record)

    _set_attachment_status(message, attachment_index, "quarantined")
    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "media_quarantined",
        note=f"attachment_index={attachment_index};record={record.uid}",
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        source_path.parent.mkdir(parents=True, exist_ok=True)
        if private_path.exists() and not source_path.exists():
            try:
                _move_file(private_path, source_path)
            except OSError:
                # Durable DB state was rolled back; preserve the evidence copy
                # rather than deleting it if filesystem compensation also fails.
                pass
        raise
    await db.refresh(record)
    return media_record_projection(record)


async def list_report_media_records(
    db: AsyncSession,
    *,
    report_uid: UUID,
    moderator_account_uid: UUID,
) -> list[dict]:
    await _require_claim_owner(db, report_uid, moderator_account_uid)
    result = await db.execute(
        select(ModerationMediaRecord)
        .where(ModerationMediaRecord.report_uid == report_uid)
        .order_by(ModerationMediaRecord.created_at.asc())
    )
    return [media_record_projection(item) for item in result.scalars().all()]


async def restore_report_attachment(
    db: AsyncSession,
    *,
    report_uid: UUID,
    record_uid: UUID,
    moderator_account_uid: UUID,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
    private_root: Path = PRIVATE_MEDIA_ROOT,
) -> dict:
    report = await _require_claim_owner(db, report_uid, moderator_account_uid)
    if report.target_account_uid:
        await assert_higher_authority(db, moderator_account_uid, report.target_account_uid)

    result = await db.execute(
        select(ModerationMediaRecord)
        .where(
            ModerationMediaRecord.uid == record_uid,
            ModerationMediaRecord.report_uid == report.uid,
        )
        .with_for_update()
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail={"error_type": "moderation_media_record_not_found"})
    if record.status == "removed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_removed_not_restorable"},
        )
    if record.status == "restored":
        return media_record_projection(record)

    public_root = upload_root.resolve()
    source_path = (private_root.resolve() / record.private_relative_path).resolve()
    destination = (public_root / record.original_relative_path).resolve()
    try:
        source_path.relative_to(private_root.resolve())
        destination.relative_to(public_root)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error_type": "moderation_media_invalid_path"}) from exc
    if not source_path.is_file():
        raise HTTPException(status_code=409, detail={"error_type": "moderation_media_private_file_missing"})
    if destination.exists():
        raise HTTPException(status_code=409, detail={"error_type": "moderation_media_restore_conflict"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        _move_file(source_path, destination)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_type": "moderation_media_restore_failed"},
        ) from exc

    message = await _reported_message(db, record.source_type, record.source_uid)
    if message:
        _set_attachment_status(message, record.attachment_index, None)
    record.status = "restored"
    record.restored_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "media_restored",
        note=f"record={record.uid}",
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        source_path.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not source_path.exists():
            try:
                _move_file(destination, source_path)
            except OSError:
                pass
        raise
    await db.refresh(record)
    return media_record_projection(record)


async def remove_report_attachment(
    db: AsyncSession,
    *,
    report_uid: UUID,
    record_uid: UUID,
    moderator_account_uid: UUID,
    reason: str,
) -> dict:
    report = await _require_claim_owner(db, report_uid, moderator_account_uid)
    if report.target_account_uid:
        await assert_higher_authority(db, moderator_account_uid, report.target_account_uid)
    result = await db.execute(
        select(ModerationMediaRecord)
        .where(
            ModerationMediaRecord.uid == record_uid,
            ModerationMediaRecord.report_uid == report.uid,
        )
        .with_for_update()
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail={"error_type": "moderation_media_record_not_found"})
    if record.status != "quarantined":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_media_must_be_quarantined_first"},
        )

    # "removed" means removed from public delivery. The private evidence copy is
    # retained until the future retention policy decides when secure deletion is due.
    record.status = "removed"
    record.reason = reason.strip()[:1000]
    record.removed_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    message = await _reported_message(db, record.source_type, record.source_uid)
    if message:
        _set_attachment_status(message, record.attachment_index, "removed")
    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "media_removed",
        note=f"record={record.uid}",
    )
    await db.commit()
    await db.refresh(record)
    return media_record_projection(record)
