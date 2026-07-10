"""Tests for authentication endpoints."""

import pytest


pytestmark = pytest.mark.asyncio


async def test_register_user_success(client, user_payload):
    """POST /auth/register with valid payload returns 201 and tokens."""
    resp = await client.post("/api/v1/auth/register", json=user_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["username"] == user_payload["username"]
    assert body["user"]["email"] == user_payload["email"]
    assert "access_token" in body["token"]
    assert "refresh_token" in body["token"]
    assert body["token"]["token_type"] == "bearer"


async def test_register_duplicate_email_returns_400(client, user_payload):
    """Registering the same email twice returns 400."""
    await client.post("/api/v1/auth/register", json=user_payload)
    resp = await client.post(
        "/api/v1/auth/register",
        json={**user_payload, "username": "otheruser"},
    )
    assert resp.status_code == 400, resp.text


async def test_register_weak_password_rejected(client, user_payload):
    """Passwords shorter than 8 chars are rejected by Pydantic."""
    bad = {**user_payload, "username": "weakpwd", "password": "short"}
    resp = await client.post("/api/v1/auth/register", json=bad)
    assert resp.status_code == 422


async def test_login_success(client, user_payload):
    """Login with correct credentials returns tokens."""
    await client.post("/api/v1/auth/register", json=user_payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body["token"]


async def test_login_wrong_password_returns_401(client, user_payload):
    """Wrong password returns 401."""
    await client.post("/api/v1/auth/register", json=user_payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401, resp.text


async def test_login_unknown_user_returns_401(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever1"},
    )
    assert resp.status_code == 401


async def test_get_me_requires_token(client, user_payload):
    """GET /auth/me without Authorization header returns 403."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403


async def test_get_me_returns_current_user(client, user_payload):
    """GET /auth/me with a valid bearer token returns the user."""
    reg = await client.post("/api/v1/auth/register", json=user_payload)
    token = reg.json()["token"]["access_token"]
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == user_payload["email"]


async def test_refresh_token(client, user_payload):
    """Refresh returns a new access token."""
    reg = await client.post("/api/v1/auth/register", json=user_payload)
    refresh = reg.json()["token"]["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


async def test_logout_blacklists_token(client, user_payload):
    """After /auth/logout, the same access token should be invalid."""
    reg = await client.post("/api/v1/auth/register", json=user_payload)
    token = reg.json()["token"]["access_token"]
    # First request works
    ok = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200
    # Logout
    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout.status_code == 200
    # Subsequent request fails
    after = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.status_code == 401
