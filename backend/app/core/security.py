"""
Authentication primitives based on Python's standard library.

The project keeps SQLite as requested, and this module avoids adding runtime
dependencies for JWT or password hashing.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any


JWT_ALGORITHM = "HS256"
PASSWORD_ITERATIONS = 260000
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))


class TokenError(ValueError):
    """Raised when a token is missing, expired, or invalid."""


def _secret_key() -> bytes:
    return os.getenv("JWT_SECRET_KEY", "dev-only-change-me-public-sentiment").encode("utf-8")


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${_base64url_encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt, expected = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return hmac.compare_digest(_base64url_encode(digest), expected)
    except (ValueError, TypeError):
        return False


def create_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hmac.new(_secret_key(), token.encode("utf-8"), hashlib.sha256).hexdigest()


def create_access_token(payload: dict[str, Any], expires_delta: timedelta | None = None) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    token_payload = {
        **payload,
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    signing_input = ".".join(
        [
            _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _base64url_encode(json.dumps(token_payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(_secret_key(), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_base64url_encode(signature)}", expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".", 2)
        signing_input = f"{header_part}.{payload_part}"
        expected_signature = hmac.new(_secret_key(), signing_input.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_base64url_encode(expected_signature), signature_part):
            raise TokenError("Invalid token signature")

        header = json.loads(_base64url_decode(header_part))
        if header.get("alg") != JWT_ALGORITHM:
            raise TokenError("Unsupported token algorithm")

        payload = json.loads(_base64url_decode(payload_part))
        expires_at = payload.get("exp")
        if not isinstance(expires_at, int) or expires_at < int(datetime.now(timezone.utc).timestamp()):
            raise TokenError("Token expired")
        return payload
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TokenError("Invalid token") from exc
