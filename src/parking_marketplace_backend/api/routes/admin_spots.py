import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from parking_marketplace_backend.core.deps import require_admin
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.reservation import Reservation, ReservationStatus
from parking_marketplace_backend.models.spot import Spot, SpotStatus
from parking_marketplace_backend.schemas.spot import AdminSpotRead, RejectSpotRequest, SpotRead

router = APIRouter(prefix="/admin/spots", tags=["admin"])


async def _get_spot_or_404(db: AsyncSession, spot_id: uuid.UUID) -> Spot:
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")
    return spot


@router.get("/", response_model=list[AdminSpotRead])
async def list_spots_for_review(
        status_filter: SpotStatus | None = Query(default=None, alias="status"),
        _admin: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(Spot, User.name, User.apartment_number).join(User, User.id == Spot.user_id)
    if status_filter is not None:
        stmt = stmt.where(Spot.status == status_filter)
    stmt = stmt.order_by(Spot.created_at.asc())

    result = await db.execute(stmt)
    return [
        AdminSpotRead(
            id=spot.id,
            status=spot.status,
            spot_number=spot.spot_number,
            notes=spot.notes,
            rejection_reason=spot.rejection_reason,
            owner_name=owner_name,
            owner_apartment_number=owner_apartment_number,
            created_at=spot.created_at,
            updated_at=spot.updated_at,
        )
        for spot, owner_name, owner_apartment_number in result.all()
    ]


@router.patch("/{spot_id}/approve", response_model=SpotRead)
async def approve_spot(
        spot_id: uuid.UUID,
        _admin: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db),
):
    spot = await _get_spot_or_404(db, spot_id)

    if spot.status != SpotStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a PENDING spot can be approved",
        )

    spot.status = SpotStatus.APPROVED
    spot.rejection_reason = None

    await db.commit()
    await db.refresh(spot)
    return spot


@router.patch("/{spot_id}/reject", response_model=SpotRead)
async def reject_spot(
        spot_id: uuid.UUID,
        payload: RejectSpotRequest,
        _admin: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db),
):
    spot = await _get_spot_or_404(db, spot_id)

    if spot.status not in (SpotStatus.PENDING, SpotStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a PENDING or APPROVED spot can be rejected",
        )

    spot.status = SpotStatus.REJECTED
    spot.rejection_reason = payload.rejection_reason

    await db.execute(
        update(Reservation)
        .where(Reservation.spot_id == spot.id, Reservation.status == ReservationStatus.CONFIRMED)
        .values(status=ReservationStatus.CANCELLED_BY_ADMIN)
    )

    await db.commit()
    await db.refresh(spot)
    return spot
