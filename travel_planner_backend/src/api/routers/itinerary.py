from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from src.api import db
from src.api.models import APIError, ItineraryItem, ItineraryItemCreate, ItineraryItemUpdate

router = APIRouter(prefix="/trips/{trip_id}/itinerary", tags=["Itinerary"])


def _row_to_item(row) -> ItineraryItem:
    return ItineraryItem(
        id=int(row["id"]),
        trip_id=int(row["trip_id"]),
        title=str(row["title"]),
        date=row["date"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        location=row["location"],
        notes=row["notes"],
        kind=str(row["kind"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _ensure_trip_exists(conn, trip_id: int) -> None:
    cur = conn.cursor()
    cur.execute("SELECT id FROM trips WHERE id = ?", (trip_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Trip not found")


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[ItineraryItem],
    responses={404: {"model": APIError}},
    summary="List itinerary items",
    description="List itinerary items for a trip.",
)
def list_itinerary(trip_id: int) -> List[ItineraryItem]:
    """List itinerary items for the trip."""
    db.init_db()
    conn = db.get_conn()
    try:
        _ensure_trip_exists(conn, trip_id)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM itinerary_items WHERE trip_id = ? ORDER BY date ASC, start_time ASC, id ASC",
            (trip_id,),
        )
        return [_row_to_item(r) for r in cur.fetchall()]
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=ItineraryItem,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": APIError}},
    summary="Create itinerary item",
    description="Create an itinerary item under a trip.",
)
def create_itinerary_item(trip_id: int, payload: ItineraryItemCreate) -> ItineraryItem:
    """Create a new itinerary item for the trip."""
    db.init_db()
    conn = db.get_conn()
    try:
        _ensure_trip_exists(conn, trip_id)
        now = db._utc_now_iso()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO itinerary_items
            (trip_id, title, date, start_time, end_time, location, notes, kind, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trip_id,
                payload.title,
                payload.date.isoformat() if payload.date else None,
                payload.start_time,
                payload.end_time,
                payload.location,
                payload.notes,
                payload.kind,
                now,
                now,
            ),
        )
        item_id = int(cur.lastrowid)
        conn.commit()
        cur.execute("SELECT * FROM itinerary_items WHERE id = ? AND trip_id = ?", (item_id, trip_id))
        return _row_to_item(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.get(
    "/{item_id}",
    response_model=ItineraryItem,
    responses={404: {"model": APIError}},
    summary="Get itinerary item",
    description="Get an itinerary item by id under a trip.",
)
def get_itinerary_item(trip_id: int, item_id: int) -> ItineraryItem:
    """Get itinerary item by id."""
    db.init_db()
    conn = db.get_conn()
    try:
        _ensure_trip_exists(conn, trip_id)
        cur = conn.cursor()
        cur.execute("SELECT * FROM itinerary_items WHERE id = ? AND trip_id = ?", (item_id, trip_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Itinerary item not found")
        return _row_to_item(row)
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.patch(
    "/{item_id}",
    response_model=ItineraryItem,
    responses={404: {"model": APIError}},
    summary="Update itinerary item",
    description="Partially update an itinerary item under a trip.",
)
def update_itinerary_item(trip_id: int, item_id: int, payload: ItineraryItemUpdate) -> ItineraryItem:
    """Update itinerary item by id."""
    db.init_db()
    conn = db.get_conn()
    try:
        _ensure_trip_exists(conn, trip_id)
        cur = conn.cursor()
        cur.execute("SELECT * FROM itinerary_items WHERE id = ? AND trip_id = ?", (item_id, trip_id))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Itinerary item not found")

        updated = {
            "title": payload.title if payload.title is not None else existing["title"],
            "date": payload.date.isoformat() if payload.date is not None else existing["date"],
            "start_time": payload.start_time if payload.start_time is not None else existing["start_time"],
            "end_time": payload.end_time if payload.end_time is not None else existing["end_time"],
            "location": payload.location if payload.location is not None else existing["location"],
            "notes": payload.notes if payload.notes is not None else existing["notes"],
            "kind": payload.kind if payload.kind is not None else existing["kind"],
            "updated_at": db._utc_now_iso(),
        }

        cur.execute(
            """
            UPDATE itinerary_items
            SET title = ?, date = ?, start_time = ?, end_time = ?, location = ?, notes = ?, kind = ?, updated_at = ?
            WHERE id = ? AND trip_id = ?
            """,
            (
                updated["title"],
                updated["date"],
                updated["start_time"],
                updated["end_time"],
                updated["location"],
                updated["notes"],
                updated["kind"],
                updated["updated_at"],
                item_id,
                trip_id,
            ),
        )
        conn.commit()
        cur.execute("SELECT * FROM itinerary_items WHERE id = ? AND trip_id = ?", (item_id, trip_id))
        return _row_to_item(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": APIError}},
    summary="Delete itinerary item",
    description="Delete an itinerary item by id under a trip.",
)
def delete_itinerary_item(trip_id: int, item_id: int) -> None:
    """Delete an itinerary item."""
    db.init_db()
    conn = db.get_conn()
    try:
        _ensure_trip_exists(conn, trip_id)
        cur = conn.cursor()
        cur.execute("SELECT id FROM itinerary_items WHERE id = ? AND trip_id = ?", (item_id, trip_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Itinerary item not found")
        cur.execute("DELETE FROM itinerary_items WHERE id = ? AND trip_id = ?", (item_id, trip_id))
        conn.commit()
        return None
    finally:
        conn.close()
