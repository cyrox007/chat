import unittest
from unittest.mock import patch

from settings import config
from utils.jwt import (
    create_access_token,
    create_refresh_token,
    validate_access_token,
    validate_refresh_token,
)


class JwtUniquenessContractTests(unittest.TestCase):
    def _security_patch(self):
        return patch.multiple(
            config,
            JWT_ACCESS_SECRET_KEY="a" * 40,
            JWT_REFRESH_SECRET_KEY="b" * 40,
        )

    def test_back_to_back_access_tokens_are_unique(self):
        with self._security_patch():
            first = create_access_token({"user_uid": "account-1"})
            second = create_access_token({"user_uid": "account-1"})
            self.assertNotEqual(first, second)
            self.assertEqual(validate_access_token(first), {"user_uid": "account-1"})
            self.assertEqual(validate_access_token(second), {"user_uid": "account-1"})

    def test_back_to_back_refresh_tokens_are_unique(self):
        with self._security_patch():
            first = create_refresh_token({"user_uid": "account-1"})
            second = create_refresh_token({"user_uid": "account-1"})
            self.assertNotEqual(first, second)
            self.assertEqual(validate_refresh_token(first), {"user_uid": "account-1"})
            self.assertEqual(validate_refresh_token(second), {"user_uid": "account-1"})


if __name__ == "__main__":
    unittest.main()
