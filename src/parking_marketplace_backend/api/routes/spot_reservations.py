import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.car import Car
from parking_marketplace_backend.models.reservation import Reservation, ReservationStatus
from parking_marketplace_backend.models.spot import Spot
from parking_marketplace_backend.schemas.reservation import OwnerReservationRead

router = APIRouter(prefix="/spots/{spot_id}/reservations", tags=["reservations"])


def _get_spot_or_404(db: Session, spot_id: uuid.UUID) -> Spot:
    spot = db.scalar(select(Spot).where(Spot.id == spot_id))
    if not spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")
    return spot


def _require_owner(spot: Spot, current_user: User) -> None:
    if spot.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this spot")


@router.get("/", response_model=list[OwnerReservationRead])
def list_spot_reservations(
        spot_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    spot = _get_spot_or_404(db, spot_id)
    _require_owner(spot, current_user)

    stmt = (
        select(Reservation, User.name, User.phone, Car.plate)
        .join(User, User.id == Reservation.user_id)
        .join(Car, Car.id == Reservation.car_id)
        .where(
            Reservation.spot_id == spot_id,
            Reservation.status == ReservationStatus.CONFIRMED,
        )
        .order_by(Reservation.start_at.asc())
    )

    return [
        OwnerReservationRead(
            id=reservation.id,
            start_at=reservation.start_at,
            end_at=reservation.end_at,
            status=reservation.status,
            driver_name=driver_name,
            driver_phone=driver_phone,
            car_plate=car_plate,
        )
        for reservation, driver_name, driver_phone, car_plate in db.execute(stmt).all()
    ]
