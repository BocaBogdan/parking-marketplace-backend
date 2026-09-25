import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sqlalchemy import func, select

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.spot import Spot
from parking_marketplace_backend.schemas.spot import SpotRead, SpotCreate, SpotUpdate

router = APIRouter(prefix="/spots", tags=["spots"])


@router.post("/", response_model=SpotRead)
def create_spot(
        payload: SpotCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    new_spot = Spot(
        spot_number=payload.spot_number,
        user_id = current_user.id
    )

    db.add(new_spot)
    try:
        db.commit()
    except:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This spot already exists")

    db.refresh(new_spot)

    return new_spot

@router.get("/mine", response_model=list[SpotRead])
def get_my_spots(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    stmt = (
        select(Spot)
        .where(Spot.user_id == current_user.id)
        .order_by(Spot.spot_number.asc())
    )
    return db.scalars(stmt).all()

@router.put("/{spot_id}", response_model=SpotRead)
def update_spot(
        spot_id: uuid.UUID,
        payload: SpotUpdate,
        db: Session = Depends(get_db)
):
    current_spot = db.scalar(select(Spot).where(Spot.id == spot_id))

    if not current_spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data:
        current_spot.status = update_data["status"]
    if "spot_number" in update_data:
        current_spot.spot_number = update_data["spot_number"]

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This spot already exists")


    db.refresh(current_spot)
    return current_spot

@router.delete("/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spot(spot_id: uuid.UUID, db: Session = Depends(get_db)):
    current_spot = db.scalar(select(Spot).where(Spot.id == spot_id))

    if not current_spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")

    db.delete(current_spot)

    db.commit()
    return None