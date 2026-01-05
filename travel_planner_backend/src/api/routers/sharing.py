from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api import db
from src.api.models import APIError, ShareCreateRequest, ShareLink, Trip

router = APIRouter(prefix="/sharing", tags=["Sharing"])


class ShareResolveResponse(BaseModel):
    trip: Trip = Field(..., description="Trip shared by this token.")
    share: ShareLink = Field(..., description="Share link metadata.")


def _row_to_share(row) -> ShareLink:
    return ShareLink(
        id=int(row["id"]),
        trip_id=int(row["trip_id"]),
        token=str(row["token"]),
        email=row["email"],
        role=str(row["role"]),
        created_at=row["created_at"],
    )


def _row_to_trip(row) -> Trip:
    return Trip(
        id=int(row["id"]),
        owner_user_id=int(row["owner_user_id"]),
        name=str(row["name"]),
        start_date=row["start_date"],
        end_date=row["end_date"],
        notes=row["notes"],
        is_shared=bool(row["is_shared"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# PUBLIC_INTERFACE
@router.post(
    "/shares",
    response_model=ShareLink,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": APIError}},
    summary="Create share link",
    description="Create a share link/token for a trip.",
)
def create_share(payload: ShareCreateRequest) -> ShareLink:
    """Create a share token for a trip."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM trips WHERE id = ?", (payload.trip_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Trip not found")

        token = db.random_token("share")
        now = db._utc_now_iso()
        cur.execute(
            "INSERT INTO shares (trip_id, token, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (payload.trip_id, token, payload.email, payload.role, now),
        )
        # mark trip shared
        cur.execute(
            "UPDATE trips SET is_shared = 1, updated_at = ? WHERE id = ?",
            (now, payload.trip_id),
        )
        share_id = int(cur.lastrowid)
        conn.commit()
        cur.execute("SELECT * FROM shares WHERE id = ?", (share_id,))
        return _row_to_share(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.get(
    "/shares",
    response_model=List[ShareLink],
    summary="List share links",
    description="List shares, optionally filtered by trip_id or email.",
)
def list_shares(
    trip_id: Optional[int] = Query(default=None, description="Filter by trip id."),
    email: Optional[str] = Query(default=None, description="Filter by invitee email."),
) -> List[ShareLink]:
    """List share links."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        if trip_id is None and email is None:
            cur.execute("SELECT * FROM shares ORDER BY id DESC")
        elif trip_id is not None and email is None:
            cur.execute("SELECT * FROM shares WHERE trip_id = ? ORDER BY id DESC", (trip_id,))
        elif trip_id is None and email is not None:
            cur.execute("SELECT * FROM shares WHERE email = ? ORDER BY id DESC", (email,))
        else:
            cur.execute(
                "SELECT * FROM shares WHERE trip_id = ? AND email = ? ORDER BY id DESC",
                (trip_id, email),
            )
        return [_row_to_share(r) for r in cur.fetchall()]
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.get(
    "/resolve",
    response_model=ShareResolveResponse,
    responses={404: {"model": APIError}},
    summary="Resolve a share token",
    description="Resolve a share token and return the associated trip and share metadata.",
)
def resolve_share(token: str = Query(..., description="Share token to resolve.")) -> ShareResolveResponse:
    """Resolve token and return shared trip."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM shares WHERE token = ?", (token,))
        share_row = cur.fetchone()
        if not share_row:
            raise HTTPException(status_code=404, detail="Share token not found")

        cur.execute("SELECT * FROM trips WHERE id = ?", (int(share_row["trip_id"]),))
        trip_row = cur.fetchone()
        if not trip_row:
            raise HTTPException(status_code=404, detail="Trip not found")

        return ShareResolveResponse(trip=_row_to_trip(trip_row), share=_row_to_share(share_row))
    finally:
        conn.close()
