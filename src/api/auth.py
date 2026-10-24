"""
JWT validation for Supabase-issued tokens.

Every request to a protected endpoint passes through get_current_user(),
which decodes the Bearer token and returns the user_id (UUID string from
the 'sub' claim).

Tokens are verified only against Supabase's asymmetric signing keys, fetched
from the project's public JWKS endpoint. HS256 tokens signed with the Legacy
JWT Secret are rejected, so the backend holds no signing secret.
"""

import os
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
_ALGORITHMS_ASYMMETRIC = ["RS256", "ES256"]


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    """
    Client for the Supabase JWKS endpoint. Keys are cached and refetched when a
    token names a key ID it hasn't seen, so signing-key rotations need no redeploy.
    """
    return jwt.PyJWKClient(
        f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_keys=True, timeout=10
    )


def _decode_token(token: str) -> dict:
    """
    Decode a Supabase JWT against the project's JWKS public keys.
    Only ES256/RS256 are accepted; anything else (including HS256) is rejected.
    """
    header = jwt.get_unverified_header(token)

    alg = header.get("alg")
    if alg not in _ALGORITHMS_ASYMMETRIC:
        raise jwt.InvalidAlgorithmError(f"Unsupported token algorithm: {alg}")

    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=_ALGORITHMS_ASYMMETRIC,
        options={"verify_aud": False},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """
    Validate the Supabase JWT and return the user_id string.
    Raises HTTP 401 if the token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = _decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise ValueError("Missing sub claim")
        return user_id
    except (jwt.PyJWTError, ValueError) as e:
        print(
            f"[AUTH DEBUG] JWT validation failed: {type(e).__name__}: {e} | "
            f"supabase_url={_SUPABASE_URL[:30] if _SUPABASE_URL else 'MISSING'}",
            flush=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """
    Like get_current_user but returns None instead of raising for unauthenticated
    requests. Used on endpoints that allow anonymous access (e.g. triggering a
    pre-auth report run).
    """
    if not credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
