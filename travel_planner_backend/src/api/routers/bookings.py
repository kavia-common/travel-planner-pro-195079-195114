from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api import db
from src.api.models import APIError, Booking, BookingCreate, BookingUpdate

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def _row_to_booking(row) -> Booking:
    return Booking(
        id=int(row["id"]),
        trip_id=int(row["trip_id"]),
        provider=row["provider"],
        reference=row["reference"],
        kind=str(row["kind"]),
        start_date=row["start_date"],
        end_date=row["end_date"],
        details=row["details"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[Booking],
    summary="List bookings",
    description="List bookings, optionally filtered by trip_id.",
)
def list_bookings(trip_id: Optional[int] = Query(default=None, description="Filter by trip id.")) -> List[Booking]:
    """List bookings."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        if trip_id is None:
            cur.execute("SELECT * FROM bookings ORDER BY updated_at DESC, id DESC")
        else:
            cur.execute("SELECT * FROM bookings WHERE trip_id = ? ORDER BY updated_at DESC, id DESC", (trip_id,))
        return [_row_to_booking(r) for r in cur.fetchall()]
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=Booking,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": APIError}},
    summary="Create booking",
    description="Create a booking record for a trip.",
)
def create_booking(payload: BookingCreate) -> Booking:
    """Create booking."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM trips WHERE id = ?", (payload.trip_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Trip not found")

        now = db._utc_now_iso()
        cur.execute(
            """
            INSERT INTO bookings (trip_id, provider, reference, kind, start_date, end_date, details, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.trip_id,
                payload.provider,
                payload.reference,
                payload.kind,
                payload.start_date.isoformat() if payload.start_date else None,
                payload.end_date.isoformat() if payload.end_date else None,
                payload.details,
                now,
                now,
            ),
        )
        booking_id = int(cur.lastrowid)
        conn.commit()
        cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        return _row_to_booking(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.patch(
    "/{booking_id}",
    response_model=Booking,
    responses={404: {"model": APIError}},
    summary="Update booking",
    description="Partially update a booking record by id.",
)
def update_booking(booking_id: int, payload: BookingUpdate) -> Booking:
    """Update booking."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Booking not found")

        updated = {
            "provider": payload.provider if payload.provider is not None else existing["provider"],
            "reference": payload.reference if payload.reference is not None else existing["reference"],
            "kind": payload.kind if payload.kind is not None else existing["kind"],
            "start_date": (
                payload.start_date.isoformat() if payload.start_date is not None else existing["start_date"]
            ),
            "end_date": payload.end_date.isoformat() if payload.end_date is not None else existing["end_date"],
            "details": payload.details if payload.details is not None else existing["details"],
            "updated_at": db._utc_now_iso(),
        }

        cur.execute(
            """
            UPDATE bookings
            SET provider = ?, reference = ?, kind = ?, start_date = ?, end_date = ?, details = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["provider"],
                updated["reference"],
                updated["kind"],
                updated["start_date"],
                updated["end_date"],
                updated["details"],
                updated["updated_at"],
                booking_id,
            ),
        )
        conn.commit()
        cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        return _row_to_booking(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.delete(
    "/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": APIError}},
    summary="Delete booking",
    description="Delete a booking by id.",
)
def delete_booking(booking_id: int) -> None:
    """Delete booking."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM bookings WHERE id = ?", (booking_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Booking not found")
        cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()
        return None
    finally:
        conn.close()
