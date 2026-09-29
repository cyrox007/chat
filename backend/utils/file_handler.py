from __future__ import annotations

import base64
import binascii
import io
import os
from pathlib import Path
import re
import uuid
import zipfile

from fastapi import HTTPException, UploadFile, status

from settings import config
from utils.logger import setup_logger


logger = setup_logger(__name__)

PUBLIC_UPLOAD_ROOT = Path("uploads")

MIME_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "audio/mpeg": ".mp3",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/vnd.rar": ".rar",
}

IMAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
VIDEO_MIME_TYPES = frozenset(
    {"video/mp4", "video/webm", "video/ogg"}
)
AUDIO_MIME_TYPES = frozenset(
    {
        "audio/mpeg",
        "audio/webm",
        "audio/ogg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/x-m4a",
    }
)
DOCUMENT_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/x-rar-compressed",
        "application/vnd.rar",
    }
)


def allowed_mime_types_for_message(content_type: str) -> frozenset[str]:
    normalized = str(content_type or "").strip().lower()
    if normalized == "image":
        return IMAGE_MIME_TYPES
    if normalized == "video":
        return VIDEO_MIME_TYPES
    if normalized in {"voice", "audio"}:
        return AUDIO_MIME_TYPES
    if normalized == "file":
        return DOCUMENT_MIME_TYPES
    return frozenset()

_DATA_URL_RE = re.compile(
    r"^data:(?P<mime>[^;,]+)(?P<params>(?:;[^,]*)*?),(?P<payload>.*)$",
    re.IGNORECASE | re.DOTALL,
)


def _upload_error(error_type: str, message: str, *, status_code: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_type": error_type, "message": message},
    )


def normalize_mime_type(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw.startswith("data:"):
        raw = raw[5:]
    raw = raw.split(";", 1)[0].strip()
    if raw not in MIME_TO_EXTENSION:
        raise _upload_error("upload_type_not_allowed", "Этот тип файла не поддерживается.")
    return raw


def _safe_original_name(value: str | None, extension: str) -> str:
    raw = Path(str(value or "file")).name
    cleaned = "".join(
        char for char in raw
        if char.isprintable() and char not in {"\x00", "/", "\\"}
    ).strip()
    if not cleaned:
        cleaned = f"file{extension}"
    return cleaned[:255]


def _decode_base64_payload(value: str, *, declared_mime: str | None = None) -> tuple[bytes, str]:
    if not isinstance(value, str) or not value.strip():
        raise _upload_error("upload_payload_invalid", "Пустой или некорректный файл.")

    raw = value.strip()
    mime_from_data_url: str | None = None
    encoded = raw

    if raw.lower().startswith("data:"):
        match = _DATA_URL_RE.match(raw)
        if not match:
            raise _upload_error("upload_data_url_invalid", "Некорректный data URL.")
        params = match.group("params").lower().split(";")
        if "base64" not in {item.strip() for item in params if item.strip()}:
            raise _upload_error("upload_encoding_not_allowed", "Файл должен быть передан в base64.")
        mime_from_data_url = normalize_mime_type(match.group("mime"))
        encoded = match.group("payload")

    declared = normalize_mime_type(declared_mime) if declared_mime else None
    if mime_from_data_url and declared and mime_from_data_url != declared:
        raise _upload_error(
            "upload_mime_mismatch",
            "Заявленный тип файла не совпадает с data URL.",
        )
    mime_type = mime_from_data_url or declared
    if not mime_type:
        raise _upload_error("upload_mime_missing", "Не указан тип файла.")

    compact = "".join(encoded.split())
    # Reject oversized encoded payloads before allocating decoded bytes.
    max_encoded = ((int(config.MAX_FILE_SIZE) + 2) // 3) * 4 + 8
    if len(compact) > max_encoded:
        raise _upload_error("upload_too_large", "Файл превышает допустимый размер.")

    try:
        content = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise _upload_error("upload_base64_invalid", "Некорректные base64-данные.") from exc

    if not content:
        raise _upload_error("upload_payload_invalid", "Пустой файл.")
    if len(content) > int(config.MAX_FILE_SIZE):
        raise _upload_error("upload_too_large", "Файл превышает допустимый размер.")
    return content, mime_type


def _zip_names(content: bytes) -> set[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if len(names) > 4096:
                return set()
            return set(names)
    except (zipfile.BadZipFile, OSError):
        return set()


def _matches_declared_type(content: bytes, mime_type: str) -> bool:
    head = content[:32]

    if mime_type == "image/jpeg":
        return head.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/gif":
        return head.startswith((b"GIF87a", b"GIF89a"))
    if mime_type == "image/webp":
        return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP"

    if mime_type in {"video/mp4", "audio/mp4", "audio/x-m4a"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"
    if mime_type == "video/webm" or mime_type == "audio/webm":
        return head.startswith(b"\x1aE\xdf\xa3")
    if mime_type in {"video/ogg", "audio/ogg"}:
        return head.startswith(b"OggS")
    if mime_type in {"audio/wav", "audio/x-wav"}:
        return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if mime_type == "audio/mpeg":
        return head.startswith(b"ID3") or (
            len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0
        )

    if mime_type == "application/pdf":
        return head.startswith(b"%PDF-")
    if mime_type in {"application/msword", "application/vnd.ms-excel"}:
        return head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if mime_type == "application/zip":
        return head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
    if mime_type in {"application/x-rar-compressed", "application/vnd.rar"}:
        return head.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"))

    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        names = _zip_names(content)
        return "[Content_Types].xml" in names and any(name.startswith("word/") for name in names)
    if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        names = _zip_names(content)
        return "[Content_Types].xml" in names and any(name.startswith("xl/") for name in names)

    return False


def _validate_content(content: bytes, mime_type: str) -> None:
    if not _matches_declared_type(content, mime_type):
        raise _upload_error(
            "upload_content_mismatch",
            "Содержимое файла не соответствует заявленному типу.",
        )


def _folder_for_mime(mime_type: str) -> str:
    family = mime_type.split("/", 1)[0]
    return {
        "image": "images",
        "video": "videos",
        "audio": "audio",
        "application": "documents",
    }.get(family, "other")


def _write_public_upload(
    content: bytes,
    mime_type: str,
    *,
    original_name: str | None = None,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
) -> dict:
    extension = MIME_TO_EXTENSION[mime_type]
    folder_name = _folder_for_mime(mime_type)
    root = upload_root.resolve()
    upload_dir = (root / folder_name).resolve()
    try:
        upload_dir.relative_to(root)
    except ValueError as exc:
        raise _upload_error("upload_path_invalid", "Некорректный путь загрузки.") from exc

    upload_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
    file_name = f"{uuid.uuid4()}{extension}"
    destination = upload_dir / file_name
    temporary = upload_dir / f".{file_name}.tmp"

    try:
        with open(temporary, "xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return {
        "url": f"/uploads/{folder_name}/{file_name}",
        "type": mime_type,
        "name": _safe_original_name(original_name, extension),
        "size": len(content),
    }


def save_file_record(
    file_data: dict,
    *,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
    allowed_mime_types: set[str] | frozenset[str] | None = None,
) -> dict:
    if not isinstance(file_data, dict):
        raise _upload_error("upload_payload_invalid", "Некорректное описание файла.")

    content, mime_type = _decode_base64_payload(
        file_data.get("url"),
        declared_mime=file_data.get("type"),
    )
    if allowed_mime_types is not None and mime_type not in allowed_mime_types:
        raise _upload_error("upload_type_not_allowed", "Этот тип файла не поддерживается здесь.")
    _validate_content(content, mime_type)
    return _write_public_upload(
        content,
        mime_type,
        original_name=file_data.get("name"),
        upload_root=upload_root,
    )


def save_file(file_data: dict, *, upload_root: Path = PUBLIC_UPLOAD_ROOT) -> str:
    """Backward-compatible wrapper returning only the public URL."""
    return save_file_record(file_data, upload_root=upload_root)["url"]


def save_data_url(
    value: str,
    *,
    original_name: str | None = None,
    allowed_mime_types: set[str] | frozenset[str] | None = None,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
) -> dict:
    return save_file_record(
        {"url": value, "type": None, "name": original_name},
        upload_root=upload_root,
        allowed_mime_types=allowed_mime_types,
    )


def save_message_files(
    files: list,
    *,
    content_type: str,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
) -> list[dict]:
    if not isinstance(files, list) or not files:
        raise _upload_error("upload_files_missing", "В сообщении нет файлов.")
    if len(files) > int(config.MAX_FILES_LIMIT):
        raise _upload_error(
            "upload_too_many_files",
            "Слишком много файлов в одном сообщении.",
        )

    allowed = allowed_mime_types_for_message(content_type)
    if not allowed:
        raise _upload_error("upload_type_not_allowed", "Этот тип сообщения не поддерживает файлы.")

    saved: list[dict] = []
    total_size = 0
    try:
        for item in files:
            record = save_file_record(
                item,
                upload_root=upload_root,
                allowed_mime_types=allowed,
            )
            saved.append(record)
            total_size += int(record["size"])
            if total_size > int(config.MAX_MESSAGE_MEDIA_TOTAL_SIZE):
                raise _upload_error(
                    "upload_message_too_large",
                    "Общий размер файлов в сообщении превышает допустимый.",
                )
        return saved
    except Exception:
        for record in saved:
            remove_saved_file(record.get("url"), upload_root=upload_root)
        raise


def save_message_voice(
    value: str,
    *,
    upload_root: Path = PUBLIC_UPLOAD_ROOT,
) -> dict:
    return save_data_url(
        value,
        original_name="voice-message",
        allowed_mime_types=AUDIO_MIME_TYPES,
        upload_root=upload_root,
    )


def remove_saved_file(url: str, *, upload_root: Path = PUBLIC_UPLOAD_ROOT) -> None:
    if not isinstance(url, str) or not url.startswith("/uploads/"):
        return
    relative = url[len("/uploads/"):].lstrip("/")
    root = upload_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return
    try:
        candidate.unlink(missing_ok=True)
    except OSError:
        logger.warning("Не удалось удалить orphan upload", exc_info=True)


def save_uploaded_file(file: UploadFile, *, upload_root: Path = PUBLIC_UPLOAD_ROOT) -> str:
    """Store one multipart upload with a streaming byte cap and content signature check."""
    mime_type = normalize_mime_type(file.content_type)
    extension = MIME_TO_EXTENSION[mime_type]
    folder_name = _folder_for_mime(mime_type)
    root = upload_root.resolve()
    upload_dir = (root / folder_name).resolve()
    try:
        upload_dir.relative_to(root)
    except ValueError as exc:
        raise _upload_error("upload_path_invalid", "Некорректный путь загрузки.") from exc

    upload_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
    file_name = f"{uuid.uuid4()}{extension}"
    temporary = upload_dir / f".{file_name}.tmp"
    destination = upload_dir / file_name
    total = 0

    try:
        file.file.seek(0)
        with open(temporary, "xb") as handle:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > int(config.MAX_FILE_SIZE):
                    raise _upload_error("upload_too_large", "Файл превышает допустимый размер.")
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())

        content = temporary.read_bytes()
        if not content:
            raise _upload_error("upload_payload_invalid", "Пустой файл.")
        _validate_content(content, mime_type)
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
        return f"/uploads/{folder_name}/{file_name}"
    except HTTPException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    except Exception as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        logger.exception("Ошибка при сохранении загруженного файла")
        raise _upload_error(
            "upload_processing_failed",
            "Не удалось обработать файл.",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc
