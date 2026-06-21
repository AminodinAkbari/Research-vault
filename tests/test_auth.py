from __future__ import annotations

import pytest
from httpx import AsyncClient

REGISTER_PAYLOAD = {"email": "alice@example.com", "password": "supersecret123"}


@pytest.mark.asyncio
async def test_register_returns_user_and_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201

    body = response.json()
    assert body["email"] == REGISTER_PAYLOAD["email"]
    assert "id" in body
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post("/api/v1/auth/login", json=REGISTER_PAYLOAD)
    assert response.status_code == 200

    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_fails(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_fails(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/projects",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_valid_token(client: AsyncClient) -> None:
    register_response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    body = register_response.json()

    response = await client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert response.status_code == 200
    # A freshly registered user has no projects yet; the real list endpoint
    assert response.json() == []