"""
/users endpoints — profile management (company name, work domain).
Profiles are created on first login and updated as needed.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import get_current_user
from ..deps import get_db

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileRequest(BaseModel):
    company_name: str | None = None
    work_domain: str | None = None


class UserProfileResponse(BaseModel):
    user_id: str
    company_name: str | None
    work_domain: str | None
    created_at: str | None


@router.get("/me", response_model=UserProfileResponse)
def get_profile(user_id: str = Depends(get_current_user), conn=Depends(get_db)):
    """Fetch the current user's profile."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, company_name, work_domain, created_at FROM user_profiles WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()

    if not row:
        # Profile doesn't exist yet — return empty shell
        return UserProfileResponse(user_id=user_id, company_name=None, work_domain=None, created_at=None)

    return UserProfileResponse(
        user_id=str(row[0]),
        company_name=row[1],
        work_domain=row[2],
        created_at=row[3].isoformat() if row[3] else None,
    )


@router.post("/me", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
def upsert_profile(
    body: UserProfileRequest,
    user_id: str = Depends(get_current_user),
    conn=Depends(get_db),
):
    """Create or update the current user's profile (company name, work domain)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_profiles (id, company_name, work_domain)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                work_domain = EXCLUDED.work_domain
            RETURNING id, company_name, work_domain, created_at
            """,
            (user_id, body.company_name, body.work_domain),
        )
        row = cur.fetchone()
    conn.commit()

    return UserProfileResponse(
        user_id=str(row[0]),
        company_name=row[1],
        work_domain=row[2],
        created_at=row[3].isoformat() if row[3] else None,
    )
