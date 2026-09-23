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
    user_id, token = await _register(
        client, "disabled_role", "disabled_role@example.com"
    )
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


# ===========================================================================
# F023 — authorization regressions for ?design=schema
# ===========================================================================
#
# The F023 ``?design=`` query parameter MUST NOT relax the existing
# authorization rules. The service reuses F012's ``_load_project_suite``
# so the same boundaries hold; we verify with three regression tests
# mirroring FT-R05 / FT-R06 / FT-R07 in F023_SPEC §10.3.

SAMPLE_OPENAPI_3_0_SCHEMA = {
    "openapi": "3.0.0",
    "info": {"title": "Sensors", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/sensors": {
            "post": {
                "operationId": "createSensor",
                "summary": "Create sensor",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                            "example": {"name": "x"},
                        }
                    }
                },
                "responses": {"201": {"description": "ok"}},
            }
        }
    },
    "components": {"schemas": {}},
}


async def _create_project_and_suite(
    client, token: str, suffix: str = ""
) -> tuple[dict, dict]:
    proj = await client.post(
        "/api/v1/projects",
        json={"name": f"f023-authz-{suffix or 'a'}"},
        headers=_auth(token),
    )
    assert proj.status_code == 201, proj.text
    suite = await client.post(
        f"/api/v1/projects/{proj.json()['id']}/suites",
        json={"name": f"f023-authz-suite-{suffix or 'a'}"},
        headers=_auth(token),
    )
    assert suite.status_code == 201, suite.text
    return proj.json(), suite.json()


# FT-A01 — non-owner with ?design=schema → 403
async def test_ft_a01_non_owner_with_design_schema_returns_403(client):
    _, admin_token = await _register(client, "f023a_admin", "f023a_a@e.com")
    _, regular_token = await _register(
        client, "f023a_reg", "f023a_r@e.com", admin_token
    )
    project, suite = await _create_project_and_suite(client, admin_token)
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"design": "schema", "dry_run": "true"},
        json={"source_content": SAMPLE_OPENAPI_3_0_SCHEMA},
        headers=_auth(regular_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "FORBIDDEN"


# FT-A02 — cross-project path → 404
async def test_ft_a02_cross_project_with_design_schema_returns_404(client):
    _, admin_token = await _register(client, "f023b_admin", "f023b_a@e.com")
    proj_a, suite_a = await _create_project_and_suite(client, admin_token, suffix="a")
    proj_b, suite_b = await _create_project_and_suite(client, admin_token, suffix="b")
    # suite_b belongs to proj_b; request targets proj_a/suite_b path →
    # _assert_path_scope rejects with 404.
    resp = await client.post(
        f"/api/v1/projects/{proj_a['id']}/suites/{suite_b['id']}/import/openapi",
        params={"design": "schema", "dry_run": "true"},
        json={"source_content": SAMPLE_OPENAPI_3_0_SCHEMA},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404, resp.text


# FT-A03 — no token with ?design=schema → 401
async def test_ft_a03_no_token_with_design_schema_returns_401(client):
    _, admin_token = await _register(client, "f023c_admin", "f023c_a@e.com")
    project, suite = await _create_project_and_suite(client, admin_token)
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"design": "schema", "dry_run": "true"},
        json={"source_content": SAMPLE_OPENAPI_3_0_SCHEMA},
        # no Authorization header at all
    )
    assert resp.status_code == 401, resp.text
