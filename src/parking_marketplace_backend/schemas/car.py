import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _normalize_plate(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("plate must not be empty")
    return normalized


class CarCreate(BaseModel):
    plate: str = Field(min_length=1, max_length=20)
    nickname: str | None = Field(default=None, max_length=100)
    is_default: bool = False

    @field_validator("plate")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        return _normalize_plate(value)


class CarUpdate(BaseModel):
    plate: str | None = Field(default=None, min_length=1, max_length=20)
    nickname: str | None = Field(default=None, max_length=100)
    is_default: bool | None = None

    @field_validator("plate")
    @classmethod
    def validate_plate(cls, value: str | None) -> str | None:
        return None if value is None else _normalize_plate(value)


class CarRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    plate: str
    nickname: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime
