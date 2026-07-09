from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 210_000


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        [
            PASSWORD_HASH_ALGORITHM,
            str(PASSWORD_HASH_ITERATIONS),
            _base64url_encode(salt),
            _base64url_encode(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = _base64url_decode(salt_text)
        expected_digest = _base64url_decode(digest_text)
    except (ValueError, TypeError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(
    *,
    user_id: str,
    secret_key: str,
    expires_at: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = expires_at or now + (expires_delta or timedelta(minutes=1440))
    payload = {
        "sub": user_id,
        "exp": int(expires_at.timestamp()),
    }
    payload_text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_part = _base64url_encode(payload_text.encode("utf-8"))
    signature = hmac.new(secret_key.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_base64url_encode(signature)}"


def decode_access_token(
    token: str,
    *,
    secret_key: str,
    now: datetime | None = None,
) -> str | None:
    try:
        payload_part, signature_part = token.split(".", 1)
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            payload_part.encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual_signature = _base64url_decode(signature_part)
        if not hmac.compare_digest(actual_signature, expected_signature):
            return None

        payload = json.loads(_base64url_decode(payload_part).decode("utf-8"))
        user_id = payload.get("sub")
        exp = payload.get("exp")
        if not isinstance(user_id, str) or not isinstance(exp, int):
            return None

        current_time = now or datetime.now(timezone.utc)
        if current_time.timestamp() >= exp:
            return None
        return user_id
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
