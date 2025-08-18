from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text
from ..core.config import settings

_engine: AsyncEngine | None = None

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        if not settings.db_url:
            raise RuntimeError("DATABASE_URL not configured")
        _engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    return _engine

async def fetch_one(query: str, **params):
    eng = get_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text(query), params)
        row = res.mappings().first()
        return dict(row) if row else None

async def fetch_all(query: str, **params):
    eng = get_engine()
    async with eng.connect() as conn:
        res = await conn.execute(text(query), params)
        rows = res.mappings().all()
        return [dict(r) for r in rows]
