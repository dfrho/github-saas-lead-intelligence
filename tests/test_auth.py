"""Tests for Supabase JWT verification: only ES256/RS256 tokens signed by a JWKS key pass."""

import base64
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api import auth  # noqa: E402

_KEY = ec.generate_private_key(ec.SECP256R1())
_OTHER_KEY = ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def jwks():
    """Serve _KEY's public half as the only JWKS signing key."""
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = MagicMock(key=_KEY.public_key())
    with patch.object(auth, "_jwks_client", return_value=client):
        yield client


def _call(token: str):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return auth.get_current_user(creds)


def _claims(**extra):
    return {"sub": "user-1", "exp": int(time.time()) + 300, **extra}


def test_valid_es256_token_returns_user_id():
    assert _call(jwt.encode(_claims(), _KEY, algorithm="ES256", headers={"kid": "k1"})) == "user-1"


def test_token_signed_by_unknown_key_rejected():
    with pytest.raises(HTTPException) as exc:
        _call(jwt.encode(_claims(), _OTHER_KEY, algorithm="ES256"))
    assert exc.value.status_code == 401


def test_expired_token_rejected():
    with pytest.raises(HTTPException):
        _call(jwt.encode(_claims(exp=int(time.time()) - 10), _KEY, algorithm="ES256"))


def test_token_without_sub_rejected():
    token = jwt.encode({"exp": int(time.time()) + 300}, _KEY, algorithm="ES256")
    with pytest.raises(HTTPException):
        _call(token)


def test_hs256_with_leaked_secret_rejected(jwks):
    with pytest.raises(HTTPException):
        _call(jwt.encode(_claims(), "leaked-legacy-secret", algorithm="HS256"))
    jwks.get_signing_key_from_jwt.assert_not_called()


def test_hs256_signed_with_public_key_rejected():
    """Algorithm confusion (CVE-2026-85394 in python-jose): HMAC keyed with the public key."""
    import hashlib
    import hmac

    public_der = _KEY.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    signing_input = (
        f"{b64(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())}."
        f"{b64(json.dumps(_claims()).encode())}"
    )
    sig = hmac.new(public_der, signing_input.encode(), hashlib.sha256).digest()
    with pytest.raises(HTTPException):
        _call(f"{signing_input}.{b64(sig)}")


def test_alg_none_rejected():
    with pytest.raises(HTTPException):
        _call("eyJhbGciOiJub25lIn0.eyJzdWIiOiJ4In0.")


def test_jwks_fetch_failure_returns_401(jwks):
    jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError("down")
    with pytest.raises(HTTPException) as exc:
        _call(jwt.encode(_claims(), _KEY, algorithm="ES256"))
    assert exc.value.status_code == 401


def test_optional_user_returns_none_for_bad_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="garbage")
    assert auth.get_optional_user(creds) is None
