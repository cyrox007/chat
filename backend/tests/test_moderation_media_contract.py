import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from components.moderation.media_service import _move_file, _safe_private_path, _safe_public_path


class ModerationMediaContractTests(unittest.TestCase):
    def test_public_media_path_is_confined_to_upload_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "uploads"
            root.mkdir()
            path, relative = _safe_public_path(
                "/uploads/images/example.jpg",
                upload_root=root,
            )
            self.assertEqual(relative, "images/example.jpg")
            self.assertEqual(path, (root / "images/example.jpg").resolve())

    def test_public_media_path_rejects_traversal_and_external_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "uploads"
            root.mkdir()
            with self.assertRaises(HTTPException):
                _safe_public_path("/uploads/../secret.txt", upload_root=root)
            with self.assertRaises(HTTPException):
                _safe_public_path("https://example.com/file.jpg", upload_root=root)

    def test_move_file_falls_back_when_atomic_replace_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "public" / "reported.jpg"
            destination = root / "private" / "reported.jpg"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"evidence")
            with patch("components.moderation.media_service.os.replace", side_effect=OSError("cross-device")):
                _move_file(source, destination)
            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), b"evidence")

    def test_private_media_path_is_record_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "moderation"
            uid = uuid4()
            path, relative = _safe_private_path(uid, "../../unsafe.jpg", private_root=root)
            self.assertTrue(relative.startswith(str(uid)))
            self.assertEqual(path.name, "unsafe.jpg")


if __name__ == "__main__":
    unittest.main()
