import base64
import os
from pathlib import Path
import re
import uuid
from fastapi import HTTPException, UploadFile
from utils.logger import setup_logger
from settings import config

logger = setup_logger(__name__)

MIME_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "audio/mpeg": ".mp3",
    "audio/webm": ".webm",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
}

def save_file(file_data: dict) -> str:
    """
    Сохраняет файл на диск и возвращает URL для доступа к нему.
    :param file_data: Словарь с данными файла (url, type, name, size).
    :return: URL для доступа к файлу.
    :raises HTTPException: В случае ошибки при обработке файла.
    """
    try:
        # Проверка формата входных данных
        if not file_data.get("url") or ',' not in file_data["url"]:
            raise HTTPException(status_code=400, detail="Invalid file format")

        # Извлекаем MIME-тип и кодировку из Base64
        mime_type, encoded_data = file_data["url"].split(',', 1)
        file_content = base64.b64decode(encoded_data)

        # Проверка размера файла
        if len(file_content) > config.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Извлекаем основной MIME-тип (удаляем data: и параметры)
        mime_type_base = re.sub(r"^data:|;.*$", "", mime_type)
        logger.debug(f"mime_type_base: {mime_type_base}")
        if not mime_type_base:
            raise HTTPException(status_code=400, detail="Invalid MIME type")

        # Определяем расширение
        extension = MIME_TO_EXTENSION.get(mime_type_base, ".bin")
        logger.debug(f"extension: {extension}")
        if not extension.startswith('.'):
            extension = f".{extension}"

        # Создаем папку для типа файла
        main_mime_type = mime_type_base.split('/')[0]  # Например, "image", "video"
        folder_name = {
            "image": "images",
            "video": "videos",
            "audio": "audio",
            "application": "documents",
        }.get(main_mime_type, "other")

        upload_dir = Path("uploads") / folder_name
        os.makedirs(upload_dir, exist_ok=True)

        # Генерируем уникальное имя файла
        file_name = f"{uuid.uuid4()}{extension}"
        file_path = upload_dir / file_name

        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Возвращаем относительный путь
        return f"/uploads/{folder_name}/{file_name}"

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
    

def save_uploaded_file(file: UploadFile) -> str:
    """
    Сохраняет файл, отправленный через multipart/form-data, и возвращает URL для доступа к нему.
    :param file: Объект UploadFile из FastAPI.
    :return: URL для доступа к файлу.
    :raises HTTPException: В случае ошибки при обработке файла.
    """
    try:
        # Проверка размера файла
        if file.size > config.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Определяем MIME-тип и расширение
        mime_type = file.content_type
        extension = MIME_TO_EXTENSION.get(mime_type, ".bin")
        logger.debug(f"mime_type: {mime_type}, extension: {extension}")

        # Создаем папку для типа файла
        folder_name = {
            "image": "images",
            "video": "videos",
            "audio": "audio",
            "application": "documents",
        }.get(mime_type.split('/')[0], "other")
        upload_dir = Path("uploads") / folder_name
        os.makedirs(upload_dir, exist_ok=True)

        # Генерируем уникальное имя файла
        file_name = f"{uuid.uuid4()}{extension}"
        file_path = upload_dir / file_name

        # Сохраняем файл
        with open(file_path, "wb") as f:
            while chunk := file.file.read(1024 * 1024):  # Читаем файл по частям (1 МБ)
                f.write(chunk)

        # Формируем URL для доступа к файлу
        # Возвращаем относительный путь
        return f"/uploads/{folder_name}/{file_name}"

    except Exception as e:
        logger.exception("Ошибка при сохранении загруженного файла")
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")