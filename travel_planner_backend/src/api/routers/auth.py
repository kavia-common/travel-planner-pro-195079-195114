from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.api import db
from src.api.models import APIError, AuthToken, LoginRequest, SignupRequest, UserPublic

router = APIRouter(tags=["Auth"])


def _hash_password(password: str) -> str:
    # Minimal hashing for demo usage. Not intended for production.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip() or None


# PUBLIC_INTERFACE
@router.post(
    "/auth/signup",
    response_model=AuthToken,
    responses={400: {"model": APIError}},
    summary="Sign up (minimal)",
    description="Create a user and return a bearer token. Dev-friendly minimal auth.",
)
def signup(payload: SignupRequest) -> AuthToken:
    """Create a user and return an auth token."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", (payload.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        cur.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (payload.email, payload.name, _hash_password(payload.password), db._utc_now_iso()),
        )
        user_id = int(cur.lastrowid)
        token = db.random_token("auth")

        cur.execute(
            "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, db._utc_now_iso()),
        )
        conn.commit()
        return AuthToken(token=token, user=UserPublic(id=user_id, email=payload.email, name=payload.name))
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.post(
    "/auth/login",
    response_model=AuthToken,
    responses={401: {"model": APIError}},
    summary="Login (minimal)",
    description="Validate email+password and return a bearer token.",
)
def login(payload: LoginRequest) -> AuthToken:
    """Validate user credentials and return token."""
    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?", (payload.email,))
        row = cur.fetchone()
        if not row or row["password_hash"] != _hash_password(payload.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = db.random_token("auth")
        cur.execute(
            "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, int(row["id"]), db._utc_now_iso()),
        )
        conn.commit()
        return AuthToken(
            token=token,
            user=UserPublic(id=int(row["id"]), email=str(row["email"]), name=str(row["name"])),
        )
    finally:
        conn.close()


class SeedResponse(BaseModel):
    seeded: Dict[str, Any] = Field(..., description="Summary of created/existing seed records.")


# PUBLIC_INTERFACE
@router.post(
    "/auth/seed",
    response_model=SeedResponse,
    summary="Seed sample data",
    description="Create a demo user and a sample trip+itinerary if none exist.",
)
def seed() -> SeedResponse:
    """Seed sample data helpful for UI development."""
    summary = db.seed_sample_data()
    return SeedResponse(seeded=summary)


def _require_user_id_from_auth(authorization: Optional[str] = Header(default=None)) -> int:
    token = _bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    db.init_db()
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM auth_tokens WHERE token = ?", (token,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return int(row["user_id"])
    finally:
        conn.close()


# PUBLIC_INTERFACE
@router.get(
    "/auth/me",
    response_model=UserPublic,
    responses={401: {"model": APIError}},
    summary="Current user",
    description="Return the current user based on Bearer token.",
)
def me(user_id: int = Depends(_require_user_id_from_auth)) -> UserPublic:
    """Return current user profile."""
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, name FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return UserPublic(id=int(row["id"]), email=str(row["email"]), name=str(row["name"]))
    finally:
        conn.close()
