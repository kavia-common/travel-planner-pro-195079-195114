import os
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    auth as auth_router,
    bookings as bookings_router,
    destinations as destinations_router,
    itinerary as itinerary_router,
    sharing as sharing_router,
    trips as trips_router,
)


def _get_cors_origins() -> list[str]:
    """
    Determine allowed CORS origins.

    We default to local React dev server to match the product requirement.
    If REACT_APP_FRONTEND_URL is set, we allow that too for deployed environments.
    """
    origins = {"http://localhost:3000"}
    env_origin = os.getenv("REACT_APP_FRONTEND_URL")
    if env_origin:
        origins.add(env_origin)
    return sorted(origins)


app = FastAPI(
    title="Travel Planner API",
    description=(
        "Backend API for the Travel Planner app. "
        "Provides CRUD for trips and itinerary items, plus supporting resources "
        "(destinations, bookings, sharing) and minimal auth."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service health and diagnostics."},
        {"name": "Auth", "description": "Minimal account/auth endpoints (dev-friendly)."},
        {"name": "Trips", "description": "Trip CRUD and related operations."},
        {"name": "Itinerary", "description": "Itinerary items CRUD under trips."},
        {"name": "Destinations", "description": "Destination CRUD and lookups."},
        {"name": "Bookings", "description": "Booking CRUD and trip associations."},
        {"name": "Sharing", "description": "Share trips with collaborators (tokens/links)."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health check", description="Simple liveness endpoint.")
def health_check() -> Dict[str, Any]:
    """Return a simple health status payload."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/docs/usage",
    tags=["Health"],
    summary="API usage notes",
    description="Short notes for local development and API base paths.",
)
def docs_usage() -> Dict[str, Any]:
    """Provide API usage notes for developers."""
    return {
        "basePath": "/api",
        "frontendDevOrigin": "http://localhost:3000",
        "example": {
            "listTrips": "GET /api/trips",
            "createTrip": "POST /api/trips",
            "listItinerary": "GET /api/trips/{trip_id}/itinerary",
        },
    }


# Routers mounted under /api to keep a clean base path.
app.include_router(auth_router.router, prefix="/api")
app.include_router(trips_router.router, prefix="/api")
app.include_router(itinerary_router.router, prefix="/api")
app.include_router(destinations_router.router, prefix="/api")
app.include_router(bookings_router.router, prefix="/api")
app.include_router(sharing_router.router, prefix="/api")
