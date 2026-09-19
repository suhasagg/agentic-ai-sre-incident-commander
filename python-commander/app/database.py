from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings
class Base(DeclarativeBase): pass
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
async def init_db():
    from . import models
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
async def get_db():
    async with SessionLocal() as db: yield db
