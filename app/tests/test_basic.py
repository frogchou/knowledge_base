import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_register_login():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/register", params={"username": "u1", "password": "p1"})
        assert resp.status_code == 200
        resp = await client.post("/api/v1/auth/login", data={"username": "u1", "password": "p1"})
        assert resp.status_code == 200
        assert resp.json()["success"]


@pytest.mark.asyncio
async def test_ingest_text():
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/api/v1/auth/register", params={"username": "u2", "password": "p2"})
        token_resp = await client.post("/api/v1/auth/login", data={"username": "u2", "password": "p2"})
        token = token_resp.json()["data"]["access_token"]
        resp = await client.post("/api/v1/items/text", data={"title": "hello", "content_text": "world"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["success"]


@pytest.mark.asyncio
async def test_semantic_search_mock():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/search/semantic", params={"q": "hello"})
        assert resp.status_code == 200
        assert resp.json()["success"]
