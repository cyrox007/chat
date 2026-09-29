import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from middlewares import apply_response_security_headers
from settings import config
from utils.file_handler import (
    save_file_record,
    save_message_files,
    save_uploaded_file,
)


PNG = b"\x89PNG\r\n\x1a\n" + b"safe-image-bytes"


def data_url(mime_type: str, content: bytes) -> str:
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def error_type(exc: HTTPException) -> str | None:
    return exc.detail.get("error_type") if isinstance(exc.detail, dict) else None


class UploadSecurityContractTests(unittest.TestCase):
    def test_valid_png_is_saved_with_server_normalized_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = save_file_record(
                {
                    "url": data_url("image/png", PNG),
                    "type": "image/png",
                    "name": "../../avatar.png",
                    "size": 1,
                },
                upload_root=root,
            )

            self.assertEqual(record["type"], "image/png")
            self.assertEqual(record["size"], len(PNG))
            self.assertEqual(record["name"], "avatar.png")
            self.assertRegex(record["url"], r"^/uploads/images/[0-9a-f-]+\.png$")

            stored = root / record["url"].removeprefix("/uploads/")
            self.assertEqual(stored.read_bytes(), PNG)

    def test_invalid_base64_is_rejected_without_creating_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(HTTPException) as raised:
                save_file_record(
                    {
                        "url": "data:image/png;base64,%%%not-base64%%%",
                        "type": "image/png",
                        "name": "broken.png",
                    },
                    upload_root=root,
                )
            self.assertEqual(error_type(raised.exception), "upload_base64_invalid")
            self.assertEqual(list(root.rglob("*")), [])

    def test_html_disguised_as_png_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"<html><script>alert(1)</script></html>"
            with self.assertRaises(HTTPException) as raised:
                save_file_record(
                    {
                        "url": data_url("image/png", payload),
                        "type": "image/png",
                        "name": "photo.png",
                    },
                    upload_root=root,
                )
            self.assertEqual(error_type(raised.exception), "upload_content_mismatch")

    def test_svg_and_unknown_mime_have_no_bin_fallback(self):
        for mime_type in ("image/svg+xml", "text/html", "application/octet-stream"):
            with self.subTest(mime_type=mime_type), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(HTTPException) as raised:
                    save_file_record(
                        {
                            "url": data_url(mime_type, b"<svg></svg>"),
                            "type": mime_type,
                            "name": "payload.bin",
                        },
                        upload_root=Path(directory),
                    )
                self.assertEqual(error_type(raised.exception), "upload_type_not_allowed")

    def test_declared_mime_must_match_data_url_mime(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(HTTPException) as raised:
                save_file_record(
                    {
                        "url": data_url("image/png", PNG),
                        "type": "image/jpeg",
                        "name": "mismatch.jpg",
                    },
                    upload_root=Path(directory),
                )
            self.assertEqual(error_type(raised.exception), "upload_mime_mismatch")

    def test_message_content_type_restricts_allowed_mime_family(self):
        pdf = b"%PDF-1.7\n%%EOF"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(HTTPException) as raised:
                save_message_files(
                    [
                        {
                            "url": data_url("application/pdf", pdf),
                            "type": "application/pdf",
                            "name": "not-an-image.pdf",
                        }
                    ],
                    content_type="image",
                    upload_root=Path(directory),
                )
            self.assertEqual(error_type(raised.exception), "upload_type_not_allowed")

    def test_total_message_cap_removes_all_files_written_before_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(config, "MAX_FILE_SIZE", 1024), patch.object(
                config, "MAX_MESSAGE_MEDIA_TOTAL_SIZE", len(PNG) + 2
            ):
                with self.assertRaises(HTTPException) as raised:
                    save_message_files(
                        [
                            {
                                "url": data_url("image/png", PNG),
                                "type": "image/png",
                                "name": "a.png",
                            },
                            {
                                "url": data_url("image/png", PNG),
                                "type": "image/png",
                                "name": "b.png",
                            },
                        ],
                        content_type="image",
                        upload_root=root,
                    )
            self.assertEqual(error_type(raised.exception), "upload_message_too_large")
            self.assertEqual([path for path in root.rglob("*") if path.is_file()], [])

    def test_actual_decoded_size_wins_over_client_size_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(config, "MAX_FILE_SIZE", 10):
                with self.assertRaises(HTTPException) as raised:
                    save_file_record(
                        {
                            "url": data_url("image/png", PNG),
                            "type": "image/png",
                            "name": "lied.png",
                            "size": 1,
                        },
                        upload_root=Path(directory),
                    )
            self.assertEqual(error_type(raised.exception), "upload_too_large")

    def test_multipart_stream_counts_actual_bytes_even_if_size_claim_is_small(self):
        with tempfile.TemporaryDirectory() as directory:
            upload = UploadFile(
                file=io.BytesIO(PNG),
                filename="avatar.png",
                size=1,
                headers=Headers({"content-type": "image/png"}),
            )
            with patch.object(config, "MAX_FILE_SIZE", 10):
                with self.assertRaises(HTTPException) as raised:
                    save_uploaded_file(upload, upload_root=Path(directory))
            self.assertEqual(error_type(raised.exception), "upload_too_large")
            self.assertEqual(
                [path for path in Path(directory).rglob("*") if path.is_file()],
                [],
            )

    def test_docx_must_be_a_real_office_zip_shape(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        content = buffer.getvalue()

        with tempfile.TemporaryDirectory() as directory:
            record = save_file_record(
                {
                    "url": data_url(
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        content,
                    ),
                    "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "name": "notes.docx",
                },
                upload_root=Path(directory),
            )
            self.assertTrue(record["url"].endswith(".docx"))

    def test_public_upload_headers_prevent_active_content_sniffing(self):
        request = SimpleNamespace(
            url=SimpleNamespace(path="/uploads/documents/report.pdf")
        )
        response = SimpleNamespace(headers={})
        apply_response_security_headers(request, response)

        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(
            response.headers["Content-Security-Policy"],
            "sandbox; default-src 'none'",
        )
        self.assertEqual(
            response.headers["Cross-Origin-Resource-Policy"],
            "same-origin",
        )
        self.assertEqual(response.headers["Content-Disposition"], "attachment")


if __name__ == "__main__":
    unittest.main()
