"""
JWT validation for Supabase-issued tokens.

Every request to a protected endpoint passes through get_current_user(),
which decodes the Bearer token and returns the user_id (UUID string from
the 'sub' claim).

Supabase may sign tokens with HS256 (Legacy JWT Secret) or ES256 (asymmetric
JWKS). This module handles both: it inspects the token header and uses the
appropriate key.
"""

import os
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

bearer_scheme = HTTPBearer(auto_error=False)

_SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_SERVICE_KEY", "")
_SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
_ALGORITHM_HS = "HS256"
_ALGORITHMS_ASYMMETRIC = ["RS256", "ES256"]


@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    """Fetch and cache the Supabase JWKS public keys (called once per process)."""
    url = f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _decode_token(token: str) -> dict:
    """
    Decode a Supabase JWT using the correct algorithm.
    Checks the token header to determine HS256 vs ES256/RS256.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise JWTError(f"Could not read token header: {e}") from e

    alg = header.get("alg", "HS256")

    if alg == "HS256":
        return jwt.decode(
            token,
            _SUPABASE_JWT_SECRET,
            algorithms=[_ALGORITHM_HS],
            options={"verify_aud": False},
        )
    else:
        jwks = _fetch_jwks()
        return jwt.decode(
            token,
            jwks,
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
    except (JWTError, ValueError, httpx.HTTPError) as e:
        print(
            f"[AUTH DEBUG] JWT validation failed: {type(e).__name__}: {e} | "
            f"secret_len={len(_SUPABASE_JWT_SECRET)} | supabase_url={_SUPABASE_URL[:30] if _SUPABASE_URL else 'MISSING'}",
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
