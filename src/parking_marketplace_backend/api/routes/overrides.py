import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.override import SpotOverride
from parking_marketplace_backend.models.spot import Spot
from parking_marketplace_backend.schemas.override import OverrideCreate, OverrideRead

router = APIRouter(prefix="/spots/{spot_id}/overrides", tags=["overrides"])


def _get_spot_or_404(db: Session, spot_id: uuid.UUID) -> Spot:
    spot = db.scalar(select(Spot).where(Spot.id == spot_id))
    if not spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")
    return spot


def _require_owner(spot: Spot, current_user: User) -> None:
    if spot.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this spot")


@router.get("/", response_model=list[OverrideRead])
def list_overrides(
        spot_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    _get_spot_or_404(db, spot_id)

    stmt = (
        select(SpotOverride)
        .where(SpotOverride.spot_id == spot_id)
        .order_by(SpotOverride.date, SpotOverride.start_time)
    )
    return db.scalars(stmt).all()


@router.post("/", response_model=OverrideRead, status_code=status.HTTP_201_CREATED)
def create_override(
        spot_id: uuid.UUID,
        payload: OverrideCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    spot = _get_spot_or_404(db, spot_id)
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
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An override for this exact date/time already exists for this spot",
        )

    db.refresh(new_override)
    return new_override


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_override(
        spot_id: uuid.UUID,
        override_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    spot = _get_spot_or_404(db, spot_id)
    _require_owner(spot, current_user)

    override = db.scalar(
        select(SpotOverride).where(SpotOverride.id == override_id, SpotOverride.spot_id == spot_id)
    )
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")

    db.delete(override)
    db.commit()
    return None
