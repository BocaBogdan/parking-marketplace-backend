import enum
import uuid
from datetime import date as date_
from datetime import datetime, time

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from parking_marketplace_backend.database import Base


class OverrideStatus(str, enum.Enum):
    FREE = "FREE"
    BUSY = "BUSY"


class SpotOverride(Base):
    __tablename__ = "spot_override"
    __table_args__ = (
        UniqueConstraint("spot_id", "date", "start_time", "end_time", name="uq_override_spot_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    spot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spot.id"), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[OverrideStatus] = mapped_column(Enum(OverrideStatus, name="override_status"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
