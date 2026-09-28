import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from parking_marketplace_backend.models.reservation import ReservationStatus


def _validate_slot_alignment(value: datetime) -> datetime:
    if value.minute not in (0, 30) or value.second != 0 or value.microsecond != 0:
        raise ValueError("must be aligned to :00 or :30")
    return value


class ReservationCreate(BaseModel):
    spot_id: uuid.UUID
    car_id: uuid.UUID
    start_at: datetime
    # Optional: defaults to a single 30-min slot (start_at + 30min) when omitted.
    end_at: datetime | None = None

    @field_validator("start_at")
    @classmethod
    def validate_start_alignment(cls, value: datetime) -> datetime:
        return _validate_slot_alignment(value)

    @field_validator("end_at")
    @classmethod
    def validate_end_alignment(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _validate_slot_alignment(value)

    @model_validator(mode="after")
    def validate_range(self) -> "ReservationCreate":
        if self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class ReservationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    spot_id: uuid.UUID
    car_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime


class OwnerReservationRead(BaseModel):
    """Reservation view for the spot's owner only — includes the driver's contact info,
    which must never appear in a public or driver-facing response."""

    id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: ReservationStatus
    driver_name: str
    driver_phone: str
    car_plate: str


class AdminReservationRead(BaseModel):
    """Audit view for admins — spans every spot, not just ones the caller owns."""

    id: uuid.UUID
    spot_id: uuid.UUID
    spot_number: int
    driver_name: str
    driver_apartment_number: str
    car_plate: str
    start_at: datetime
    end_at: datetime
    status: ReservationStatus


class PaginatedAdminReservations(BaseModel):
    items: list[AdminReservationRead]
    total: int
    page: int
    page_size: int
