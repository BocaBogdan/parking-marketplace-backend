import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from parking_marketplace_backend.core.deps import require_admin
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.car import Car
from parking_marketplace_backend.models.reservation import Reservation, ReservationStatus
from parking_marketplace_backend.models.spot import Spot
from parking_marketplace_backend.schemas.reservation import AdminReservationRead, PaginatedAdminReservations

router = APIRouter(prefix="/admin/reservations", tags=["admin"])


@router.get("/", response_model=PaginatedAdminReservations)
def list_all_reservations(
        spot_id: uuid.UUID | None = Query(default=None),
        from_: datetime | None = Query(default=None, alias="from"),
        to: datetime | None = Query(default=None),
        status_filter: ReservationStatus | None = Query(default=None, alias="status"),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=200),
        _admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
):
    if from_ is not None and to is not None and to < from_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must not be before 'from'",
        )

    base_stmt = (
        select(Reservation, Spot.spot_number, User.name, User.apartment_number, Car.plate)
        .join(Spot, Spot.id == Reservation.spot_id)
        .join(User, User.id == Reservation.user_id)
        .join(Car, Car.id == Reservation.car_id)
    )

    if spot_id is not None:
        base_stmt = base_stmt.where(Reservation.spot_id == spot_id)
    if from_ is not None:
        base_stmt = base_stmt.where(Reservation.start_at >= from_)
    if to is not None:
        base_stmt = base_stmt.where(Reservation.start_at <= to)
    if status_filter is not None:
        base_stmt = base_stmt.where(Reservation.status == status_filter)

    total = db.scalar(select(func.count()).select_from(base_stmt.subquery()))

    page_stmt = (
        base_stmt
        .order_by(Reservation.start_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    items = [
        AdminReservationRead(
            id=reservation.id,
            spot_id=reservation.spot_id,
            spot_number=spot_number,
            driver_name=driver_name,
            driver_apartment_number=driver_apartment_number,
            car_plate=car_plate,
            start_at=reservation.start_at,
            end_at=reservation.end_at,
            status=reservation.status,
        )
        for reservation, spot_number, driver_name, driver_apartment_number, car_plate in db.execute(page_stmt).all()
    ]

    return PaginatedAdminReservations(items=items, total=total, page=page, page_size=page_size)
