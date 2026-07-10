"""Tests for authentication endpoints."""

import pytest


pytestmark = pytest.mark.asyncio


async def test_register_first_user_success(client, user_payload):
    """POST /auth/register with no users returns 201 and tokens.

    The very first registered user is automatically promoted to
    superuser so the platform has an admin bootstrap (Review M-R1).
    """
    resp = await client.post("/api/v1/auth/register", json=user_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["username"] == user_payload["username"]
    assert body["user"]["email"] == user_payload["email"]
    # Login responses MUST NOT leak privileged fields (Review M-R2 / M-S6).
    assert "is_superuser" not in body["user"]
    assert "role_id" not in body["user"]
    assert "status" not in body["user"]
    assert "access_token" in body["token"]
    assert "refresh_token" in body["token"]
    assert body["token"]["token_type"] == "bearer"


async def test_register_duplicate_email_returns_409(client, user_payload):
    """Registering the same email twice returns 409 with business code."""
    await client.post("/api/v1/auth/register", json=user_payload)
    resp = await client.post(
        "/api/v1/auth/register",
        json={**user_payload, "username": "otheruser"},
    )
    assert resp.status_code == 409, resp.text
    body = resp.json()
    # ERROR_CODE.md §4 -> 20004 for email conflict
    assert body["code"] == "EMAIL_TAKEN"


async def test_register_duplicate_username_returns_409(client, user_payload):
    await client.post("/api/v1/auth/register", json=user_payload)
    resp = await client.post(
        "/api/v1/auth/register",
        json={**user_payload, "email": "other@example.com"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "USERNAME_TAKEN"


async def test_register_weak_password_rejected(client, user_payload):
    """Passwords shorter than 8 chars are rejected by Pydantic."""
    bad = {**user_payload, "username": "weakpwd", "password": "short"}
    resp = await client.post("/api/v1/auth/register", json=bad)
    assert resp.status_code == 422


async def test_register_password_too_long_rejected(client, user_payload):
    """Passwords longer than 72 bytes are rejected (bcrypt truncation)."""
    long_password = "a" * 80
    bad = {**user_payload, "username": "longpwd", "password": long_password}
    resp = await client.post("/api/v1/auth/register", json=bad)
    assert resp.status_code == 422


async def test_register_after_first_user_requires_superuser(client, user_payload):
    """Once any user exists, register without admin token returns 403."""
    await client.post("/api/v1/auth/register", json=user_payload)
    new_payload = {**user_payload, "username": "second", "email": "second@example.com"}
    resp = await client.post("/api/v1/auth/register", json=new_payload)
    assert resp.status_code == 403, resp.text


async def test_register_after_first_user_with_superuser_succeeds(client, user_payload, registered_user):
    """Once any user exists, register WITH admin token returns 201."""
    admin_token, _ = registered_user
    new_payload = {
        **user_payload,
        "username": "second",
        "email": "second@example.com",
    }
    resp = await client.post(
        "/api/v1/auth/register",
        json=new_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text


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
    """Wrong password returns 401 (INVALID_CREDENTIALS)."""
    await client.post("/api/v1/auth/register", json=user_payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_user_returns_401(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever1"},
    )
    assert resp.status_code == 401
    # Same error code as wrong-password to prevent user enumeration
    # (ERROR_CODE.md §6.4).
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_login_does_not_leak_privilege(client, user_payload):
    """Login response must not leak is_superuser / role_id (M-S6)."""
    await client.post("/api/v1/auth/register", json=user_payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    body = resp.json()
    assert "is_superuser" not in body["user"]
    assert "role_id" not in body["user"]


async def test_login_lockout_after_repeated_failures(client, user_payload):
    """Repeated failed logins from the same client trigger a lockout."""
    await client.post("/api/v1/auth/register", json=user_payload)
    for _ in range(5):
        bad = await client.post(
            "/api/v1/auth/login",
            json={"email": user_payload["email"], "password": "wrong"},
        )
        assert bad.status_code == 401
    # Subsequent attempts within the lockout window should be 429.
    locked = await client.post(
        "/api/v1/auth/login",
        json={"email": user_payload["email"], "password": "wrong"},
    )
    assert locked.status_code == 429, locked.text
    assert locked.json()["code"] == "TOO_MANY_REQUESTS"


async def test_get_me_requires_token_returns_401(client):
    """GET /auth/me without Authorization header returns 401 (M-S3)."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_get_me_invalid_token_returns_401(client):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert resp.status_code == 401


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
    assert "refresh_token" in resp.json()


async def test_refresh_with_access_token_returns_401(client, user_payload):
    """An access token cannot be used as a refresh token."""
    reg = await client.post("/api/v1/auth/register", json=user_payload)
    access = reg.json()["token"]["access_token"]
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access},
    )
    assert resp.status_code == 401


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


async def test_password_change_invalidates_existing_token(client, user_payload):
    """After changing the password, the old access token must be rejected (C-S5)."""
    reg = await client.post("/api/v1/auth/register", json=user_payload)
    token = reg.json()["token"]["access_token"]
    # Sanity: token works first.
    ok = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200
    # Change the password.
    resp = await client.put(
        "/api/v1/users/me/password",
        json={"old_password": user_payload["password"], "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    # Old token must no longer work.
    after = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.status_code == 401, after.text


async def test_password_change_invalidates_refresh_token(client, user_payload):
    """A refresh token issued before password change must be rejected."""
    reg = await client.post("/api/v1/auth/register", json=user_payload)
    access = reg.json()["token"]["access_token"]
    refresh = reg.json()["token"]["refresh_token"]
    # Change the password using the access token.
    change = await client.put(
        "/api/v1/users/me/password",
        json={"old_password": user_payload["password"], "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert change.status_code == 200, change.text
    # The pre-change refresh token must now be rejected.
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 401, resp.text