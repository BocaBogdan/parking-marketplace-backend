import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.override import SpotOverride
from parking_marketplace_backend.models.spot import Spot
from parking_marketplace_backend.schemas.override import OverrideCreate, OverrideRead

router = APIRouter(prefix="/spots/{spot_id}/overrides", tags=["overrides"])


async def _get_spot_or_404(db: AsyncSession, spot_id: uuid.UUID) -> Spot:
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")
    return spot


def _require_owner(spot: Spot, current_user: User) -> None:
    if spot.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this spot")


@router.get("/", response_model=list[OverrideRead])
async def list_overrides(
        spot_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    await _get_spot_or_404(db, spot_id)

    stmt = (
        select(SpotOverride)
        .where(SpotOverride.spot_id == spot_id)
        .order_by(SpotOverride.date, SpotOverride.start_time)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=OverrideRead, status_code=status.HTTP_201_CREATED)
async def create_override(
        spot_id: uuid.UUID,
        payload: OverrideCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    spot = await _get_spot_or_404(db, spot_id)
    _require_owner(spot, current_user)

    new_override = SpotOverride(
        spot_id=spot_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=payload.status,
    )
    db.add(new_override)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An override for this exact date/time already exists for this spot",
        )

    await db.refresh(new_override)
    return new_override


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
        spot_id: uuid.UUID,
        override_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    spot = await _get_spot_or_404(db, spot_id)
    _require_owner(spot, current_user)

    result = await db.execute(
        select(SpotOverride).where(SpotOverride.id == override_id, SpotOverride.spot_id == spot_id)
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")

    await db.delete(override)
    await db.commit()
    return None
