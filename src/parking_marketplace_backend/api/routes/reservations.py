import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from parking_marketplace_backend.core.availability import is_spot_available
from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.car import Car
from parking_marketplace_backend.models.reservation import Reservation, ReservationStatus
from parking_marketplace_backend.models.spot import Spot, SpotStatus
from parking_marketplace_backend.schemas.reservation import ReservationCreate, ReservationRead

router = APIRouter(prefix="/reservations", tags=["reservations"])

SLOT_DURATION = timedelta(minutes=30)
CANCELLATION_CUTOFF = timedelta(minutes=15)


@router.post("/", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
def create_reservation(
        payload: ReservationCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    spot = db.scalar(select(Spot).where(Spot.id == payload.spot_id))
    if not spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")

    if spot.status != SpotStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Spot is not approved",
        )

    if spot.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot reserve your own spot",
        )

    car = db.scalar(
        select(Car).where(
            Car.id == payload.car_id,
            Car.user_id == current_user.id,
            Car.deleted_at.is_(None),
        )
    )
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")

    end_at = payload.end_at or (payload.start_at + SLOT_DURATION)

    if not is_spot_available(db, spot.id, payload.start_at, end_at):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Spot is not available for this window",
        )

    new_reservation = Reservation(
        spot_id=spot.id,
        user_id=current_user.id,
        car_id=car.id,
        start_at=payload.start_at,
        end_at=end_at,
    )
    db.add(new_reservation)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This spot is already reserved for an overlapping window",
        )

    db.refresh(new_reservation)
    return ReservationRead(
        id=new_reservation.id,
        spot_id=new_reservation.spot_id,
        spot_number=spot.spot_number,
        car_id=new_reservation.car_id,
        start_at=new_reservation.start_at,
        end_at=new_reservation.end_at,
        status=new_reservation.status,
        created_at=new_reservation.created_at,
        updated_at=new_reservation.updated_at,
    )


@router.get("/mine", response_model=list[ReservationRead])
def get_my_reservations(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    stmt = (
        select(Reservation, Spot.spot_number)
        .join(Spot, Spot.id == Reservation.spot_id)
        .where(Reservation.user_id == current_user.id)
        .order_by(Reservation.start_at.desc())
    )
    return [
        ReservationRead(
            id=reservation.id,
            spot_id=reservation.spot_id,
            spot_number=spot_number,
            car_id=reservation.car_id,
            start_at=reservation.start_at,
            end_at=reservation.end_at,
            status=reservation.status,
            created_at=reservation.created_at,
            updated_at=reservation.updated_at,
        )
        for reservation, spot_number in db.execute(stmt).all()
    ]


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_reservation(
        reservation_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    reservation = db.scalar(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id,
        )
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status != ReservationStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservation is already cancelled",
        )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if now_utc > reservation.start_at - CANCELLATION_CUTOFF:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reservations can only be cancelled at least 15 minutes before they start",
        )

    reservation.status = ReservationStatus.CANCELLED
    db.commit()
    return None
