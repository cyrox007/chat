import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from components.moderation.media_service import _safe_private_path, _safe_public_path


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

    def test_private_media_path_is_record_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "moderation"
            uid = uuid4()
            path, relative = _safe_private_path(uid, "../../unsafe.jpg", private_root=root)
            self.assertTrue(relative.startswith(str(uid)))
            self.assertEqual(path.name, "unsafe.jpg")


if __name__ == "__main__":
    unittest.main()
