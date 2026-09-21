import unittest
from unittest.mock import patch

from starlette.requests import Request

from settings import config
from utils.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, generate_csrf_token, validate_csrf_token


def _request(*, cookie_token: str | None = None, header_token: str | None = None) -> Request:
    headers = []
    if cookie_token is not None:
        headers.append((b"cookie", f"{CSRF_COOKIE_NAME}={cookie_token}".encode("latin1")))
    if header_token is not None:
        headers.append((CSRF_HEADER_NAME.lower().encode("latin1"), header_token.encode("latin1")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/identity/v2/login",
            "raw_path": b"/identity/v2/login",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )


class CsrfContractTests(unittest.TestCase):
    def _security_patch(self):
        return patch.multiple(
            config,
            JWT_ACCESS_SECRET_KEY="a" * 40,
            JWT_REFRESH_SECRET_KEY="b" * 40,
            CSRF_SECRET_KEY="c" * 40,
        )

    def test_valid_signed_cookie_requires_matching_explicit_header(self):
        with self._security_patch():
            token = generate_csrf_token("browser-session")
            self.assertTrue(
                validate_csrf_token(
                    _request(cookie_token=token, header_token=token)
                )
            )

    def test_cookie_alone_is_not_a_csrf_proof(self):
        with self._security_patch():
            token = generate_csrf_token("browser-session")
            self.assertFalse(
                validate_csrf_token(_request(cookie_token=token))
            )

    def test_header_alone_is_not_a_csrf_proof(self):
        with self._security_patch():
            token = generate_csrf_token("browser-session")
            self.assertFalse(
                validate_csrf_token(_request(header_token=token))
            )

    def test_mismatched_header_is_rejected(self):
        with self._security_patch():
            cookie_token = generate_csrf_token("browser-session-a")
            header_token = generate_csrf_token("browser-session-b")
            self.assertFalse(
                validate_csrf_token(
                    _request(
                        cookie_token=cookie_token,
                        header_token=header_token,
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()
