from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from parking_marketplace_backend.config import get_settings

settings = get_settings()

async_url = settings.database_url.replace("+psycopg", "+psycopg_async", 1)

engine = create_async_engine(async_url)

async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


class Base(DeclarativeBase):
    pass
