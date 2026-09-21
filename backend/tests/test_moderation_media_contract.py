import tempfile
from datetime import datetime
import unittest
from unittest.mock import patch
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from components.moderation.media_model import ModerationMediaRecord
from components.moderation.media_retention import _durable_unlink, _private_path_for_record
from components.moderation.media_service import (
    _move_file,
    _safe_private_path,
    _safe_public_path,
    _validate_storage_roots,
    media_record_projection,
)


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

    def test_private_storage_must_be_disjoint_from_public_uploads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "uploads"
            public.mkdir()
            with self.assertRaises(RuntimeError):
                _validate_storage_roots(public, public / "moderation")
            with self.assertRaises(RuntimeError):
                _validate_storage_roots(public, root)
            _validate_storage_roots(public, root / "moderation")

    def test_retention_path_is_confined_to_record_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "moderation"
            uid = uuid4()
            record = ModerationMediaRecord(
                uid=uid,
                private_relative_path=f"{uid}/reported.jpg",
            )
            path = _private_path_for_record(record, private_root=root)
            self.assertEqual(path, (root / str(uid) / "reported.jpg").resolve())

            other_uid = uuid4()
            record.private_relative_path = f"{other_uid}/other.jpg"
            with self.assertRaises(ValueError):
                _private_path_for_record(record, private_root=root)

            record.private_relative_path = f"{uid}/../{other_uid}/other.jpg"
            with self.assertRaises(ValueError):
                _private_path_for_record(record, private_root=root)

            record.private_relative_path = f"{uid}/../../outside.jpg"
            with self.assertRaises(ValueError):
                _private_path_for_record(record, private_root=root)

    def test_application_level_expiry_unlinks_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record" / "evidence.bin"
            path.parent.mkdir()
            path.write_bytes(b"private-evidence")
            self.assertTrue(_durable_unlink(path))
            self.assertFalse(path.exists())
            self.assertFalse(_durable_unlink(path))

    def test_private_filesystem_path_is_never_projected(self):
        uid = uuid4()
        now = datetime.utcnow()
        record = ModerationMediaRecord(
            uid=uid,
            report_uid=uuid4(),
            source_type="messenger_message",
            source_uid=uuid4(),
            attachment_index=0,
            original_url="/uploads/images/reported.jpg",
            original_relative_path="images/reported.jpg",
            private_relative_path=f"{uid}/reported.jpg",
            status="removed",
            reason="policy",
            created_at=now,
            updated_at=now,
        )
        projection = media_record_projection(record)
        self.assertNotIn("private_relative_path", projection)
        self.assertNotIn("original_relative_path", projection)
        self.assertNotIn(str(record.private_relative_path), str(projection))

    def test_private_media_path_is_record_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "moderation"
            uid = uuid4()
            path, relative = _safe_private_path(uid, "../../unsafe.jpg", private_root=root)
            self.assertTrue(relative.startswith(str(uid)))
            self.assertEqual(path.name, "unsafe.jpg")


if __name__ == "__main__":
    unittest.main()
