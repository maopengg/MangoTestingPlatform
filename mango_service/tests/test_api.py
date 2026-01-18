import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url=""http://testserver"") as ac:
        response = await ac.get(""/health"")
    assert response.status_code == 200
    assert response.json()[""status""] == ""healthy""


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(app=app, base_url=""http://testserver"") as ac:
        response = await ac.get(""/"")
    assert response.status_code == 200
    assert ""message"" in response.json()
    assert ""automation testing platform"" in response.json()[""message""]
