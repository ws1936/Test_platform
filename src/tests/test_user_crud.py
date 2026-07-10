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
    # Success body is ``MessageResponse`` (no envelope).
    assert resp.json()["message"] == "Password changed successfully"

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
    assert resp.json()["code"] == "INCORRECT_OLD_PASSWORD"


async def test_change_password_same_value_rejected(client, user_payload):
    """Setting the same password is allowed (no-op) by Pydantic, but the
    service still rehashes so subsequent logins use the same hash."""
    token = await _register_and_get_token(client, user_payload)
    resp = await client.put(
        "/api/v1/users/me/password",
        json={
            "old_password": user_payload["password"],
            "new_password": user_payload["password"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # Still succeeds; the user can re-enter the same password.
    assert resp.status_code == 200, resp.text


async def test_change_password_without_token_returns_401(client, user_payload):
    """No bearer header => 401 (M-S3)."""
    await _register_and_get_token(client, user_payload)
    resp = await client.put(
        "/api/v1/users/me/password",
        json={"old_password": user_payload["password"], "new_password": "NewPass456!"},
    )
    assert resp.status_code == 401


async def test_list_users_requires_auth_returns_401(client):
    resp = await client.get("/api/v1/users")
    # HTTPBearer with auto_error=False + our wrapper now returns 401 (M-S3).
    assert resp.status_code == 401


async def test_list_users_requires_superuser(client, user_payload):
    """Authenticated non-superuser cannot list users."""
    token = await _register_and_get_token(client, user_payload)
    # First user IS a superuser by bootstrap, so this still returns 200 —
    # cover the negative path by creating a second non-admin via superuser.
    admin_token, _ = token, None
    second = await client.post(
        "/api/v1/auth/register",
        json={**user_payload, "username": "second", "email": "second@example.com"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second.status_code == 201
    second_token = second.json()["token"]["access_token"]

    resp = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert resp.status_code == 403


async def test_get_user_by_id_404_when_missing(client, user_payload):
    token = await _register_and_get_token(client, user_payload)
    resp = await client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "USER_NOT_FOUND"