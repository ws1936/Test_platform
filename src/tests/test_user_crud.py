"""Tests for user management endpoints."""

import pytest


pytestmark = pytest.mark.asyncio


async def _register_and_get_token(client, payload):
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]["access_token"]


async def test_change_password_flow(client, user_payload):
    """User can change their own password; old password stops working."""
    token = await _register_and_get_token(client, user_payload)

    # Change password
    resp = await client.put(
        "/api/v1/users/me/password",
        json={"old_password": user_payload["password"], "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    # Old password rejected
    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert bad.status_code == 401

    # New password works
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": "NewPass456!"},
    )
    assert ok.status_code == 200


async def test_change_password_wrong_old_returns_400(client, user_payload):
    token = await _register_and_get_token(client, user_payload)
    resp = await client.put(
        "/api/v1/users/me/password",
        json={"old_password": "wrongpassword", "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


async def test_list_users_requires_auth(client):
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 403


async def test_get_user_by_id_404_when_missing(client, user_payload):
    token = await _register_and_get_token(client, user_payload)
    resp = await client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
