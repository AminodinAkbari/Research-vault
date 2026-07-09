from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_redirects_to_login_when_logged_out(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_login_page_renders(client: AsyncClient) -> None:
    response = await client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Log in" in response.text
    assert 'id="login-form"' in response.text


@pytest.mark.asyncio
async def test_register_page_renders(client: AsyncClient) -> None:
    response = await client.get("/register")
    assert response.status_code == 200
    assert "Create your account" in response.text
    assert 'id="register-form"' in response.text


@pytest.mark.asyncio
async def test_dashboard_requires_auth_redirects_to_login(client: AsyncClient) -> None:
    response = await client.get("/dashboard")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_register_sets_cookie_and_grants_dashboard_access(client: AsyncClient) -> None:
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "cookie-user@example.com", "password": "supersecret123"},
    )
    assert register_resp.status_code == 201
    assert "access_token" in register_resp.cookies

    dashboard_resp = await client.get("/dashboard")
    assert dashboard_resp.status_code == 200
    assert "Your projects" in dashboard_resp.text
    assert "cookie-user@example.com" in dashboard_resp.text


@pytest.mark.asyncio
async def test_login_sets_cookie_and_grants_dashboard_access(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login-user@example.com", "password": "supersecret123"},
    )
    # Registering already authenticates the client; clear cookies to simulate
    # a fresh session and verify /login on its own sets the cookie too.
    client.cookies.clear()

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login-user@example.com", "password": "supersecret123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies

    dashboard_resp = await client.get("/dashboard")
    assert dashboard_resp.status_code == 200


@pytest.mark.asyncio
async def test_root_redirects_to_dashboard_when_logged_in(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "root-user@example.com", "password": "supersecret123"},
    )
    response = await client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


@pytest.mark.asyncio
async def test_create_project_via_htmx_returns_fragment(client: AsyncClient) -> None:
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "htmx-user@example.com", "password": "supersecret123"},
    )
    auth_headers = {"Authorization": f"Bearer {register_resp.json()['access_token']}"}

    response = await client.post(
        "/dashboard/projects",
        data={"name": "My HTMX Project", "description": "created via htmx"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert 'id="project-list"' in response.text
    assert "My HTMX Project" in response.text
    assert "created via htmx" in response.text

    # The underlying project was actually persisted via the shared service layer.
    api_resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert any(p["name"] == "My HTMX Project" for p in api_resp.json())


@pytest.mark.asyncio
async def test_create_project_without_htmx_redirects_to_dashboard(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "plain-form-user@example.com", "password": "supersecret123"},
    )

    response = await client.post(
        "/dashboard/projects",
        data={"name": "Plain Form Project"},
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


@pytest.mark.asyncio
async def test_logout_clears_cookie_and_locks_dashboard(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "logout-user@example.com", "password": "supersecret123"},
    )
    assert (await client.get("/dashboard")).status_code == 200

    logout_resp = await client.post("/logout")
    assert logout_resp.status_code == 303
    assert logout_resp.headers["location"] == "/login"

    dashboard_resp = await client.get("/dashboard")
    assert dashboard_resp.status_code == 303
    assert dashboard_resp.headers["location"] == "/login"