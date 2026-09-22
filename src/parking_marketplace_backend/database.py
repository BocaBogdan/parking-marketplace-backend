from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from parking_marketplace_backend.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass
