"""
JWT validation for Supabase-issued tokens.

Every request to a protected endpoint passes through get_current_user(),
which decodes the Bearer token using the Supabase JWT secret and returns
the user_id (UUID string from the 'sub' claim).
"""

import logging
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

# Supabase signs JWTs with the service role secret (JWT_SECRET in the dashboard,
# same value as SUPABASE_SERVICE_KEY for HS256 validation).
_SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_SERVICE_KEY", "")
_ALGORITHM = "HS256"


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
        payload = jwt.decode(
            token,
            _SUPABASE_JWT_SECRET,
            algorithms=[_ALGORITHM],
            options={"verify_aud": False},
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise ValueError("Missing sub claim")
        return user_id
    except (JWTError, ValueError) as e:
        print(
            f"[AUTH DEBUG] JWT validation failed: {type(e).__name__}: {e} | "
            f"secret_len={len(_SUPABASE_JWT_SECRET)} | token_prefix={token[:20] if token else 'NONE'}",
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
