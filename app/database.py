from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
if settings.DATABASE_URL.startswith("postgresql"):
    engine = create_async_engine(settings.DATABASE_URL, echo=False, connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0})
else:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
