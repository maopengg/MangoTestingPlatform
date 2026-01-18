import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database.session import Base
from src.main import app
from httpx import AsyncClient


@pytest.fixture(scope=""session"")
def engine():
    return create_async_engine(
        ""sqlite+aiosqlite:///./test_db.sqlite3"",
        poolclass=StaticPool,
        echo=True
    )


@pytest.fixture(scope=""session"")
async def tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(engine, tables):
    from sqlalchemy.ext.asyncio import AsyncSession
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url=""http://testserver"") as client:
        yield client
