from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api import db
from src.api.models import APIError, Trip, TripCreate, TripUpdate

router = APIRouter(prefix="/trips", tags=["Trips"])


def _get_default_owner_user_id() -> int:
    """
    Resolve a default owner user id for demo usage.

    If no users exist, seed_sample_data will create one.
    """
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if row:
            return int(row["id"])
    finally:
        conn.close()

    # Create demo records if empty.
    summary = db.seed_sample_data()
    # Either created or existing will include user_id
    for bucket in ("created", "existing"):
        for item in summary.get(bucket, []):
            if "user_id" in item:
                return int(item["user_id"])
    # Should never happen
    raise HTTPException(status_code=500, detail="Unable to resolve default owner user")


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
@router.get(
    "",
    response_model=List[Trip],
    summary="List trips",
    description="List trips (optionally filtered by owner_user_id).",
)
def list_trips(
    owner_user_id: Optional[int] = Query(default=None, description="Filter by owner user id.")
) -> List[Trip]:
    """Return trips for an owner or all trips."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        if owner_user_id is None:
            cur.execute("SELECT * FROM trips ORDER BY updated_at DESC, id DESC")
        else:
            cur.execute(
                "SELECT * FROM trips WHERE owner_user_id = ? ORDER BY updated_at DESC, id DESC",
                (owner_user_id,),
            )
        return [_row_to_trip(r) for r in cur.fetchall()]
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=Trip,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": APIError}},
    summary="Create trip",
    description="Create a new trip.",
)
def create_trip(payload: TripCreate) -> Trip:
    """Create a trip."""
    db.init_db()
    owner_id = payload.owner_user_id or _get_default_owner_user_id()
    now = db._utc_now_iso()

    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO trips (owner_user_id, name, start_date, end_date, notes, is_shared, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                payload.name,
                payload.start_date.isoformat() if payload.start_date else None,
                payload.end_date.isoformat() if payload.end_date else None,
                payload.notes,
                db.parse_bool_int(payload.is_shared),
                now,
                now,
            ),
        )
        trip_id = int(cur.lastrowid)
        conn.commit()
        cur.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
        row = cur.fetchone()
        return _row_to_trip(row)
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.get(
    "/{trip_id}",
    response_model=Trip,
    responses={404: {"model": APIError}},
    summary="Get trip",
    description="Get a single trip by id.",
)
def get_trip(trip_id: int) -> Trip:
    """Get trip by id."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Trip not found")
        return _row_to_trip(row)
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.patch(
    "/{trip_id}",
    response_model=Trip,
    responses={404: {"model": APIError}},
    summary="Update trip",
    description="Update a trip by id (partial update).",
)
def update_trip(trip_id: int, payload: TripUpdate) -> Trip:
    """Partially update a trip."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Trip not found")

        updates = {
            "name": payload.name if payload.name is not None else existing["name"],
            "start_date": (
                payload.start_date.isoformat()
                if payload.start_date is not None
                else existing["start_date"]
            ),
            "end_date": (
                payload.end_date.isoformat() if payload.end_date is not None else existing["end_date"]
            ),
            "notes": payload.notes if payload.notes is not None else existing["notes"],
            "is_shared": (
                db.parse_bool_int(payload.is_shared)
                if payload.is_shared is not None
                else int(existing["is_shared"])
            ),
            "updated_at": db._utc_now_iso(),
        }

        cur.execute(
            """
            UPDATE trips
            SET name = ?, start_date = ?, end_date = ?, notes = ?, is_shared = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updates["name"],
                updates["start_date"],
                updates["end_date"],
                updates["notes"],
                updates["is_shared"],
                updates["updated_at"],
                trip_id,
            ),
        )
        conn.commit()
        cur.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
        return _row_to_trip(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": APIError}},
    summary="Delete trip",
    description="Delete a trip by id. Cascades to itinerary, destinations, bookings, and shares.",
)
def delete_trip(trip_id: int) -> None:
    """Delete trip and dependent records."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM trips WHERE id = ?", (trip_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Trip not found")
        cur.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
        conn.commit()
        return None
    finally:
        conn.close()
