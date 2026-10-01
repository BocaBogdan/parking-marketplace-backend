import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models.car import Car
from parking_marketplace_backend.models.user import User
from parking_marketplace_backend.schemas.car import CarCreate, CarRead, CarUpdate

router = APIRouter(prefix="/users/me/cars", tags=["cars"])


async def _get_active_car_or_404(db: AsyncSession, user_id: uuid.UUID, car_id: uuid.UUID) -> Car:
    result = await db.execute(
        select(Car).where(Car.id == car_id, Car.user_id == user_id, Car.deleted_at.is_(None))
    )
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")
    return car


async def _unset_other_defaults(db: AsyncSession, user_id: uuid.UUID, except_car_id: uuid.UUID | None = None) -> None:
    stmt = select(Car).where(Car.user_id == user_id, Car.deleted_at.is_(None), Car.is_default.is_(True))
    if except_car_id is not None:
        stmt = stmt.where(Car.id != except_car_id)
    result = await db.execute(stmt)
    for other in result.scalars():
        other.is_default = False


@router.get("/", response_model=list[CarRead])
async def list_cars(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Car)
        .where(Car.user_id == current_user.id, Car.deleted_at.is_(None))
        .order_by(Car.is_default.desc(), Car.created_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=CarRead, status_code=status.HTTP_201_CREATED)
async def create_car(
    payload: CarCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Car.id).where(Car.user_id == current_user.id, Car.deleted_at.is_(None)).limit(1)
    )
    has_active_car = result.scalar_one_or_none() is not None
    make_default = payload.is_default or not has_active_car

    if make_default:
        await _unset_other_defaults(db, current_user.id)

    new_car = Car(
        user_id=current_user.id,
        plate=payload.plate,
        nickname=payload.nickname,
        is_default=make_default,
    )
    db.add(new_car)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a car with this plate",
        )

    await db.refresh(new_car)
    return new_car


@router.put("/{car_id}", response_model=CarRead)
async def update_car(
    car_id: uuid.UUID,
    payload: CarUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    car = await _get_active_car_or_404(db, current_user.id, car_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "plate" in update_data:
        car.plate = update_data["plate"]
    if "nickname" in update_data:
        car.nickname = update_data["nickname"]
    if "is_default" in update_data:
        if update_data["is_default"]:
            await _unset_other_defaults(db, current_user.id, except_car_id=car.id)
            car.is_default = True
        else:
            car.is_default = False

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a car with this plate",
        )

    await db.refresh(car)
    return car


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    car = await _get_active_car_or_404(db, current_user.id, car_id)
    was_default = car.is_default

    car.deleted_at = func.now()
    car.is_default = False

    if was_default:
        result = await db.execute(
            select(Car)
            .where(Car.user_id == current_user.id, Car.deleted_at.is_(None), Car.id != car.id)
            .order_by(Car.created_at.desc())
            .limit(1)
        )
        replacement = result.scalar_one_or_none()
        if replacement:
            replacement.is_default = True

    await db.commit()
    return None
