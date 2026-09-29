import unittest
from unittest.mock import patch

from views.messenger.ws_handlers import _persist_private_message_media


class MessengerMediaPersistenceContractTests(unittest.TestCase):
    def test_private_image_metadata_is_replaced_with_saved_public_path(self):
        raw = {
            "files": [
                {
                    "url": "data:image/png;base64,private-payload",
                    "type": "image/png",
                    "name": "avatar.png",
                    "size": 42,
                }
            ]
        }
        persisted = [
            {
                "url": "/uploads/images/server-id.png",
                "type": "image/png",
                "name": "avatar.png",
                "size": 42,
            }
        ]

        with patch(
            "views.messenger.ws_handlers.save_message_files",
            return_value=persisted,
        ) as save:
            metadata, urls, total_bytes = _persist_private_message_media("image", raw)

        save.assert_called_once_with(raw["files"], content_type="image")
        self.assertEqual(metadata, {"files": persisted})
        self.assertEqual(urls, ["/uploads/images/server-id.png"])
        self.assertEqual(total_bytes, 42)
        self.assertNotIn("data:", str(metadata))

    def test_private_voice_metadata_is_replaced_with_saved_public_path(self):
        raw = {"voice": "data:audio/webm;base64,private-payload"}
        saved = {
            "url": "/uploads/audio/server-id.webm",
            "type": "audio/webm",
            "name": "voice-message.webm",
            "size": 42,
        }

        with patch(
            "views.messenger.ws_handlers.save_message_voice",
            return_value=saved,
        ) as save:
            metadata, urls, total_bytes = _persist_private_message_media("voice", raw)

        save.assert_called_once_with(raw["voice"])
        self.assertEqual(metadata, {"voice": "/uploads/audio/server-id.webm"})
        self.assertEqual(urls, ["/uploads/audio/server-id.webm"])
        self.assertEqual(total_bytes, 42)
        self.assertNotIn("data:", str(metadata))


if __name__ == "__main__":
    unittest.main()
