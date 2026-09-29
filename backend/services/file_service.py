from fastapi import HTTPException

from utils.file_handler import save_file


def process_files(files: list):
    saved_files = []
    errors = []
    for file_data in files:
        try:
            saved_files.append(save_file(file_data))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            errors.append(
                {
                    "file_name": str(file_data.get("name") or "")[:255],
                    "error": detail.get("error_type", "upload_failed"),
                }
            )
        except Exception:
            errors.append(
                {
                    "file_name": str(file_data.get("name") or "")[:255],
                    "error": "upload_failed",
                }
            )
    return saved_files, errors
