"""Cross-module authorization regression tests from the 2026-07 audit."""
from __future__ import annotations

import uuid


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, username: str, email: str, admin_token: str | None = None):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "TestPass123!",
            "nickname": username,
            "phone": "13800000000",
        },
        headers=_auth(admin_token) if admin_token else None,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["user"]["id"], body["token"]["access_token"]


async def test_stale_token_is_rejected_by_non_project_business_router(client, app):
    user_id, token = await _register(client, "stale_suite", "stale_suite@example.com")
    project = await client.post(
        "/api/v1/projects", json={"name": "stale-project"}, headers=_auth(token)
    )
    assert project.status_code == 201

    from app.domain.user.service import UserService
    async with app.state.db_session_factory() as session:
        await UserService(session).bump_token_version(uuid.UUID(user_id))

    response = await client.get(
        f"/api/v1/projects/{project.json()['id']}/suites", headers=_auth(token)
    )
    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_INVALID"


async def test_disabled_user_is_rejected_by_role_read_router(client, app):
    user_id, token = await _register(client, "disabled_role", "disabled_role@example.com")
    from app.domain.user.model import User
    async with app.state.db_session_factory() as session:
        user = await session.get(User, uuid.UUID(user_id))
        assert user is not None
        user.status = 0
        await session.commit()

    response = await client.get("/api/v1/roles", headers=_auth(token))
    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_DISABLED"


async def test_regular_user_cannot_create_update_or_delete_roles(client):
    _, admin_token = await _register(client, "role_admin", "role_admin@example.com")
    _, regular_token = await _register(
        client, "role_regular", "role_regular@example.com", admin_token
    )

    create = await client.post(
        "/api/v1/roles",
        json={"name": "forbidden-role", "permissions": []},
        headers=_auth(regular_token),
    )
    assert create.status_code == 403

    admin_create = await client.post(
        "/api/v1/roles",
        json={"name": "managed-role", "permissions": []},
        headers=_auth(admin_token),
    )
    assert admin_create.status_code == 201, admin_create.text
    role_id = admin_create.json()["id"]

    update = await client.put(
        f"/api/v1/roles/{role_id}",
        json={"description": "forbidden"},
        headers=_auth(regular_token),
    )
    delete = await client.delete(
        f"/api/v1/roles/{role_id}", headers=_auth(regular_token)
    )
    assert update.status_code == 403
    assert delete.status_code == 403
