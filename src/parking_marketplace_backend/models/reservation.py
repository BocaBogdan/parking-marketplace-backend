import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from parking_marketplace_backend.database import Base


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    CANCELLED_BY_ADMIN = "CANCELLED_BY_ADMIN"


class Reservation(Base):
    __tablename__ = "reservation"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_reservation_end_after_start"),
        # Two CONFIRMED reservations on the same spot can never overlap in time.
        # Requires the btree_gist extension (enabled in the migration) for the
        # equality operator class on spot_id to work inside a GiST index.
        ExcludeConstraint(
            ("spot_id", "="),
            (text("tsrange(start_at, end_at)"), "&&"),
            where=text("status = 'CONFIRMED'"),
            using="gist",
            name="no_overlapping_confirmed_reservations",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    spot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spot.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    car_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cars.id"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
        default=ReservationStatus.CONFIRMED,
        server_default=ReservationStatus.CONFIRMED.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
