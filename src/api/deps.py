"""
FastAPI dependency injection helpers.

Import these with Depends() in route handlers.
"""

import os
import psycopg
from fastapi import Depends
from .auth import get_current_user, get_optional_user  # noqa: F401 — re-export for routes


def get_db():
    """Yield a psycopg3 connection, closing it after the request."""
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    try:
        yield conn
    finally:
        conn.close()
