import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from parking_marketplace_backend.models.spot import SpotStatus


class SpotCreate(BaseModel):
    spot_number: int
    notes: str | None = Field(default=None, max_length=1000)


class SpotUpdate(BaseModel):
    """Owner-facing update. Status is intentionally not settable here — it's only ever
    changed by the admin approve/reject endpoints, or auto-reset to PENDING on resubmission
    of a REJECTED spot (see update_spot)."""

    spot_number: int | None = None
    notes: str | None = Field(default=None, max_length=1000)


class SpotRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    status: SpotStatus
    spot_number: int
    notes: str | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class AdminSpotRead(BaseModel):
    """Spot view for admin review — includes the owner's name and apartment number."""

    id: uuid.UUID
    status: SpotStatus
    spot_number: int
    notes: str | None
    rejection_reason: str | None
    owner_name: str
    owner_apartment_number: str
    created_at: datetime
    updated_at: datetime


class RejectSpotRequest(BaseModel):
    rejection_reason: str = Field(min_length=1, max_length=1000)
