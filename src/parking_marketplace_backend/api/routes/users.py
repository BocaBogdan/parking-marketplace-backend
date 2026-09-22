import os
import uuid
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.schemas.user import UserCreate, UserRead
from parking_marketplace_backend.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

def hash_password(plain: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 100_000)
    return salt.hex() + digest.hex()

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    password = hash_password(user.password)
    
    new_user = User(username=user.username, email=user.email, password=password)
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

@router.get("/", response_model=list[UserRead])
def get_users(db: Session = Depends(get_db)):
    return db.scalars(select(User)).all()

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user