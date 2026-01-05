from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _data_dir() -> Path:
    # Keep persistence inside repo workspace (container filesystem).
    # This is lightweight and requires no external DB container.
    root = Path(__file__).resolve().parents[3]  # .../travel_planner_backend
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data


def _db_path() -> str:
    return str(_data_dir() / "travel_planner.sqlite3")


def get_conn() -> sqlite3.Connection:
    """Create a sqlite3 connection with row factory as dict-like access."""
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _exec(conn: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def init_db() -> None:
    """Initialize database schema if it doesn't exist."""
    conn = get_conn()
    try:
        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
        )
        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        )
        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                notes TEXT,
                is_shared INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(owner_user_id) REFERENCES users(id)
            )
            """,
        )
        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS itinerary_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                date TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                notes TEXT,
                kind TEXT NOT NULL DEFAULT 'activity',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
            )
            """,
        )
        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                country TEXT,
                lat REAL,
                lng REAL,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
            )
            """,
        )
        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                provider TEXT,
                reference TEXT,
                kind TEXT NOT NULL DEFAULT 'generic',
                start_date TEXT,
                end_date TEXT,
                details TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
            )
            """,
        )
        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                email TEXT,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT NOT NULL,
                FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
            )
            """,
        )
        conn.commit()
    finally:
        conn.close()


def seed_sample_data() -> Dict[str, Any]:
    """
    Seed the database with a demo user and a sample trip with itinerary items.

    Returns a summary dict describing what was created/existed.
    """
    init_db()
    conn = get_conn()
    summary: Dict[str, Any] = {"created": [], "existing": []}
    try:
        # Demo user
        demo_email = os.getenv("TRAVEL_PLANNER_DEMO_EMAIL", "demo@example.com")
        demo_name = os.getenv("TRAVEL_PLANNER_DEMO_NAME", "Demo User")
        demo_password_hash = "dev-only:demo"  # minimal; not used for security

        cur = _exec(conn, "SELECT id FROM users WHERE email = ?", (demo_email,))
        row = cur.fetchone()
        if row:
            user_id = int(row["id"])
            summary["existing"].append({"user_id": user_id, "email": demo_email})
        else:
            cur = _exec(
                conn,
                "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (demo_email, demo_name, demo_password_hash, _utc_now_iso()),
            )
            user_id = int(cur.lastrowid)
            summary["created"].append({"user_id": user_id, "email": demo_email})

        # Sample trip
        cur = _exec(conn, "SELECT id FROM trips WHERE owner_user_id = ? ORDER BY id LIMIT 1", (user_id,))
        row = cur.fetchone()
        if row:
            trip_id = int(row["id"])
            summary["existing"].append({"trip_id": trip_id})
            conn.commit()
            return summary

        now = _utc_now_iso()
        cur = _exec(
            conn,
            """
            INSERT INTO trips (owner_user_id, name, start_date, end_date, notes, is_shared, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "Sample: Paris Weekend",
                "2026-03-20",
                "2026-03-23",
                "A quick weekend getaway to explore museums and cafes.",
                0,
                now,
                now,
            ),
        )
        trip_id = int(cur.lastrowid)
        summary["created"].append({"trip_id": trip_id})

        # Sample itinerary
        items = [
            ("Arrive + Check-in", "2026-03-20", "14:00", None, "Hotel", "Drop bags and rest.", "transport"),
            ("Louvre Museum", "2026-03-21", "10:00", "13:00", "Louvre", "Buy tickets in advance.", "activity"),
            ("Seine River Walk", "2026-03-21", "17:00", None, "Seine", "Sunset photos.", "activity"),
        ]
        for (title, dt, st, et, loc, notes, kind) in items:
            _exec(
                conn,
                """
                INSERT INTO itinerary_items
                (trip_id, title, date, start_time, end_time, location, notes, kind, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trip_id, title, dt, st, et, loc, notes, kind, now, now),
            )

        conn.commit()
        return summary
    finally:
        conn.close()


def random_token(prefix: str = "tok") -> str:
    """Generate an opaque token."""
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[Dict[str, Any]]:
    return [row_to_dict(r) for r in rows]


def parse_bool_int(value: Any) -> int:
    return 1 if bool(value) else 0


def require_env(name: str) -> Optional[str]:
    """Read env var (optional). Included for future expansion without hardcoding."""
    return os.getenv(name)
