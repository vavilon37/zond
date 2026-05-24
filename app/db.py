import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

log = logging.getLogger(__name__)

_engine = None
_sessionmaker = None


def init_db(db_path: str) -> None:
    global _engine, _sessionmaker
    parent = os.path.dirname(os.path.abspath(db_path))
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
            log.info("Created DB directory %s", parent)
        except OSError as e:
            log.warning("Could not create DB directory %s: %s", parent, e)
    log.info("DB path: %s", db_path)
    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    _sessionmaker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    if _engine is None:
        raise RuntimeError("init_db() must be called first")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def session() -> AsyncSession:
    if _sessionmaker is None:
        raise RuntimeError("init_db() must be called first")
    return _sessionmaker()
