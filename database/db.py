from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    from database import models  # noqa: F401
    from database.seed import seed_reference_data, seed_sample_sale_houses

    async with engine.begin() as connection:
        await connection.run_sync(models.Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed_reference_data(session)
        await seed_sample_sale_houses(session)
        await session.commit()
