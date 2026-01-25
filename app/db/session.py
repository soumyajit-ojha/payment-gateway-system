from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# 1. Create the engine
# print(settings.DATABASE_URL)
engine = create_async_engine(settings.DATABASE_URL)

# 2. Create the Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


# 3. Create the Base for models to inherit from
class Base(DeclarativeBase):
    pass


# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
