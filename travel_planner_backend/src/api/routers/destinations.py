from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api import db
from src.api.models import APIError, Destination, DestinationCreate, DestinationUpdate

router = APIRouter(prefix="/destinations", tags=["Destinations"])


def _row_to_destination(row) -> Destination:
    return Destination(
        id=int(row["id"]),
        trip_id=int(row["trip_id"]),
        name=str(row["name"]),
        country=row["country"],
        lat=row["lat"],
        lng=row["lng"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[Destination],
    summary="List destinations",
    description="List destinations, optionally filtered by trip_id.",
)
def list_destinations(trip_id: Optional[int] = Query(default=None, description="Filter by trip id.")) -> List[Destination]:
    """List destinations."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        if trip_id is None:
            cur.execute("SELECT * FROM destinations ORDER BY updated_at DESC, id DESC")
        else:
            cur.execute(
                "SELECT * FROM destinations WHERE trip_id = ? ORDER BY updated_at DESC, id DESC",
                (trip_id,),
            )
        return [_row_to_destination(r) for r in cur.fetchall()]
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=Destination,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": APIError}},
    summary="Create destination",
    description="Create a destination for a trip.",
)
def create_destination(payload: DestinationCreate) -> Destination:
    """Create destination."""
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
            INSERT INTO destinations (trip_id, name, country, lat, lng, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.trip_id, payload.name, payload.country, payload.lat, payload.lng, payload.notes, now, now),
        )
        destination_id = int(cur.lastrowid)
        conn.commit()
        cur.execute("SELECT * FROM destinations WHERE id = ?", (destination_id,))
        return _row_to_destination(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.patch(
    "/{destination_id}",
    response_model=Destination,
    responses={404: {"model": APIError}},
    summary="Update destination",
    description="Partially update a destination by id.",
)
def update_destination(destination_id: int, payload: DestinationUpdate) -> Destination:
    """Update destination."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM destinations WHERE id = ?", (destination_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Destination not found")

        updated = {
            "name": payload.name if payload.name is not None else existing["name"],
            "country": payload.country if payload.country is not None else existing["country"],
            "lat": payload.lat if payload.lat is not None else existing["lat"],
            "lng": payload.lng if payload.lng is not None else existing["lng"],
            "notes": payload.notes if payload.notes is not None else existing["notes"],
            "updated_at": db._utc_now_iso(),
        }

        cur.execute(
            """
            UPDATE destinations
            SET name = ?, country = ?, lat = ?, lng = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["name"],
                updated["country"],
                updated["lat"],
                updated["lng"],
                updated["notes"],
                updated["updated_at"],
                destination_id,
            ),
        )
        conn.commit()
        cur.execute("SELECT * FROM destinations WHERE id = ?", (destination_id,))
        return _row_to_destination(cur.fetchone())
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.delete(
    "/{destination_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": APIError}},
    summary="Delete destination",
    description="Delete a destination by id.",
)
def delete_destination(destination_id: int) -> None:
    """Delete destination."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM destinations WHERE id = ?", (destination_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Destination not found")
        cur.execute("DELETE FROM destinations WHERE id = ?", (destination_id,))
        conn.commit()
        return None
    finally:
        conn.close()
