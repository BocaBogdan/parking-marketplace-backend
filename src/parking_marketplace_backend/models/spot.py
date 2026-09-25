import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from parking_marketplace_backend.database import Base


class SpotStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class Spot(Base):
    __tablename__ = "spot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[SpotStatus] = mapped_column(
        Enum(SpotStatus, name="status"),
        default=SpotStatus.PENDING,
        server_default=SpotStatus.PENDING.value,
        nullable=False
    )
    spot_number: Mapped[int] = mapped_column(nullable=False, unique=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
