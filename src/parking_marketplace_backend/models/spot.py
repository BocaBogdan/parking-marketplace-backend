import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from parking_marketplace_backend.database import Base


class SpotStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INACTIVE = "INACTIVE"

class Spot(Base):
    __tablename__ = "spot"
    __table_args__ = (
        # spot_number must be unique, but only among active (non-INACTIVE) spots,
        # so a number frees up for reuse once its spot is deactivated.
        Index(
            "uq_spot_number_active",
            "spot_number",
            unique=True,
            postgresql_where=text("status <> 'INACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[SpotStatus] = mapped_column(
        Enum(SpotStatus, name="status"),
        default=SpotStatus.PENDING,
        server_default=SpotStatus.PENDING.value,
        nullable=False
    )
    spot_number: Mapped[int] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
