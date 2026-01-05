from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class APIError(BaseModel):
    """Standard error response schema."""

    detail: str = Field(..., description="Human-readable error detail.")


# -----------------------
# Auth (minimal/dev)
# -----------------------
class UserPublic(BaseModel):
    """Public user data returned by the API."""

    id: int = Field(..., description="User id.")
    email: str = Field(..., description="User email.")
    name: str = Field(..., description="Display name.")


class SignupRequest(BaseModel):
    email: str = Field(..., description="Email address.")
    name: str = Field(..., description="Display name.")
    password: str = Field(..., description="Password (stored as a salted hash).")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email address.")
    password: str = Field(..., description="Password.")


class AuthToken(BaseModel):
    token: str = Field(..., description="Opaque bearer token for demo auth.")
    user: UserPublic = Field(..., description="Authenticated user.")


# -----------------------
# Trips
# -----------------------
class TripBase(BaseModel):
    name: str = Field(..., min_length=1, description="Trip name.")
    start_date: Optional[date] = Field(None, description="Trip start date.")
    end_date: Optional[date] = Field(None, description="Trip end date.")
    notes: Optional[str] = Field(None, description="Free-form trip notes.")
    is_shared: bool = Field(False, description="Whether trip is shared with others.")


class TripCreate(TripBase):
    owner_user_id: Optional[int] = Field(
        None, description="Owner user id. If omitted, defaults to demo user."
    )


class TripUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Trip name.")
    start_date: Optional[date] = Field(None, description="Trip start date.")
    end_date: Optional[date] = Field(None, description="Trip end date.")
    notes: Optional[str] = Field(None, description="Free-form trip notes.")
    is_shared: Optional[bool] = Field(None, description="Whether trip is shared with others.")


class Trip(TripBase):
    id: int = Field(..., description="Trip id.")
    owner_user_id: int = Field(..., description="Owner user id.")
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC).")


# -----------------------
# Itinerary items
# -----------------------
class ItineraryItemBase(BaseModel):
    title: str = Field(..., min_length=1, description="Title of itinerary item.")
    date: Optional[date] = Field(None, description="Calendar date.")
    start_time: Optional[str] = Field(
        None, description="Start time in HH:MM (local to destination)."
    )
    end_time: Optional[str] = Field(None, description="End time in HH:MM (local).")
    location: Optional[str] = Field(None, description="Location name/address.")
    notes: Optional[str] = Field(None, description="Additional notes.")
    kind: str = Field("activity", description="Type of itinerary item (activity/transport/etc).")


class ItineraryItemCreate(ItineraryItemBase):
    pass


class ItineraryItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="Title of itinerary item.")
    date: Optional[date] = Field(None, description="Calendar date.")
    start_time: Optional[str] = Field(None, description="Start time in HH:MM.")
    end_time: Optional[str] = Field(None, description="End time in HH:MM.")
    location: Optional[str] = Field(None, description="Location name/address.")
    notes: Optional[str] = Field(None, description="Additional notes.")
    kind: Optional[str] = Field(None, description="Type of itinerary item.")


class ItineraryItem(ItineraryItemBase):
    id: int = Field(..., description="Itinerary item id.")
    trip_id: int = Field(..., description="Trip id.")
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC).")


# -----------------------
# Destinations
# -----------------------
class DestinationBase(BaseModel):
    trip_id: int = Field(..., description="Trip id.")
    name: str = Field(..., min_length=1, description="Destination name.")
    country: Optional[str] = Field(None, description="Country name/iso.")
    lat: Optional[float] = Field(None, description="Latitude.")
    lng: Optional[float] = Field(None, description="Longitude.")
    notes: Optional[str] = Field(None, description="Notes about the destination.")


class DestinationCreate(DestinationBase):
    pass


class DestinationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Destination name.")
    country: Optional[str] = Field(None, description="Country name/iso.")
    lat: Optional[float] = Field(None, description="Latitude.")
    lng: Optional[float] = Field(None, description="Longitude.")
    notes: Optional[str] = Field(None, description="Notes about the destination.")


class Destination(DestinationBase):
    id: int = Field(..., description="Destination id.")
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC).")


# -----------------------
# Bookings
# -----------------------
class BookingBase(BaseModel):
    trip_id: int = Field(..., description="Trip id.")
    provider: Optional[str] = Field(None, description="Provider name (airline/hotel/etc).")
    reference: Optional[str] = Field(None, description="Booking reference.")
    kind: str = Field("generic", description="Booking type (flight/hotel/car/generic).")
    start_date: Optional[date] = Field(None, description="Start date for this booking.")
    end_date: Optional[date] = Field(None, description="End date for this booking.")
    details: Optional[str] = Field(None, description="Free-form booking details.")


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    provider: Optional[str] = Field(None, description="Provider name.")
    reference: Optional[str] = Field(None, description="Booking reference.")
    kind: Optional[str] = Field(None, description="Booking type.")
    start_date: Optional[date] = Field(None, description="Start date.")
    end_date: Optional[date] = Field(None, description="End date.")
    details: Optional[str] = Field(None, description="Details.")


class Booking(BookingBase):
    id: int = Field(..., description="Booking id.")
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC).")


# -----------------------
# Sharing
# -----------------------
class ShareCreateRequest(BaseModel):
    trip_id: int = Field(..., description="Trip id to share.")
    email: Optional[str] = Field(None, description="Invitee email (optional).")
    role: str = Field("viewer", description="Role for share (viewer/editor).")


class ShareLink(BaseModel):
    id: int = Field(..., description="Share record id.")
    trip_id: int = Field(..., description="Trip id.")
    token: str = Field(..., description="Opaque share token.")
    email: Optional[str] = Field(None, description="Invitee email.")
    role: str = Field(..., description="Share role.")
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")
