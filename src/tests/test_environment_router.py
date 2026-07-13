"""HTTP API tests for the environment management router (F005).

Covers the complete environment lifecycle and authorization boundaries:

* Create  — valid payload returns 201, duplicate name returns 409,
            extra fields are 422, invalid base_url returns 422,
            missing auth returns 401.
* List    — returns ONLY environments of the caller's project, search
            filters by name.
* Detail  — non-owner / non-admin gets 403, missing env returns 404.
* Update  — owner can update fields; renaming to a duplicate returns
            409; promoting a default demotes the previous one.
* Delete  — owner can delete a non-default env; default env returns
            409.
* Set-default — promotes an environment and demotes the previous one.

All tests use the real ``/api/v1/auth/register`` + JWT flow so they
exercise the same auth + exception-handling path as production.
"""

from __future__ import annotations

import uuid

import pytest


pytestmark = pytest.mark.asyncio


# === Helpers (mirror test_project_router.py's pattern) ===


async def _register_user(
    client,
    *,
    username: str,
    email: str,
    password: str = "TestPass123!",
    admin_token: str | None = None,
) -> dict:
    """Register a user; return ``{"id": ..., "token": ...}``."""
    headers = _auth(admin_token) if admin_token else None
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "nickname": username.capitalize(),
            "phone": "13800000000",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {
        "id": body["user"]["id"],
        "token": body["token"]["access_token"],
    }


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client, token: str, *, name: str):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "description": "env test"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_environment(
    client,
    token: str,
    project_id: str,
    *,
    name: str,
    base_url: str = "https://api.dev.example.com",
    is_default: bool = False,
    headers: dict | None = None,
    variables: dict | None = None,
):
    payload = {
        "name": name,
        "base_url": base_url,
        "is_default": is_default,
    }
    if headers is not None:
        payload["headers"] = headers
    if variables is not None:
        payload["variables"] = variables
    return await client.post(
        f"/api/v1/projects/{project_id}/environments",
        json=payload,
        headers=_auth(token),
    )


# === 1) CREATE ===


async def test_create_environment_with_valid_data_returns_201(client):
    user = await _register_user(client, username="alice", email="alice@example.com")
    project = await _create_project(client, user["token"], name="P1")

    resp = await _create_environment(
        client, user["token"], project["id"], name="dev"
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "dev"
    assert body["base_url"] == "https://api.dev.example.com"
    assert body["project_id"] == project["id"]
    assert body["is_default"] is False
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_environment_with_headers_and_variables_persists_them(
    client,
):
    user = await _register_user(client, username="bob", email="bob@example.com")
    project = await _create_project(client, user["token"], name="P2")

    resp = await _create_environment(
        client,
        user["token"],
        project["id"],
        name="staging",
        headers={"Accept": "application/json", "X-Tenant": "acme"},
        variables={"token": "abc", "user_id": "10001"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["headers"] == {"Accept": "application/json", "X-Tenant": "acme"}
    assert body["variables"] == {"token": "abc", "user_id": "10001"}


async def test_create_environment_with_duplicate_name_returns_409(client):
    user = await _register_user(client, username="carol", email="carol@example.com")
    project = await _create_project(client, user["token"], name="P3")

    first = await _create_environment(
        client, user["token"], project["id"], name="dev"
    )
    assert first.status_code == 201

    dup = await _create_environment(
        client, user["token"], project["id"], name="dev"
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "CONFLICT"


async def test_create_environment_with_invalid_base_url_returns_422(client):
    user = await _register_user(client, username="dave", email="dave@example.com")
    project = await _create_project(client, user["token"], name="P4")

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/environments",
        json={"name": "dev", "base_url": "ftp://nope"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


async def test_create_environment_extra_project_id_is_rejected_with_422(client):
    """Security: clients cannot forge project_id — extra fields are 422."""
    user = await _register_user(client, username="erin", email="erin@example.com")
    project = await _create_project(client, user["token"], name="P5")

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/environments",
        json={
            "name": "dev",
            "base_url": "https://x.example.com",
            "project_id": str(uuid.uuid4()),
        },
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_create_environment_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice2", email="alice2@example.com")
    bob = await _register_user(
        client, username="bob2", email="bob2@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AliceProj")

    resp = await _create_environment(
        client, bob["token"], alice_project["id"], name="dev"
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


async def test_create_environment_on_missing_project_returns_404(client):
    user = await _register_user(client, username="ghost", email="ghost@example.com")
    resp = await _create_environment(
        client, user["token"], str(uuid.uuid4()), name="dev"
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROJECT_NOT_FOUND"


async def test_create_environment_without_token_returns_401(client):
    resp = await client.post(
        f"/api/v1/projects/{uuid.uuid4()}/environments",
        json={"name": "dev", "base_url": "https://x.example.com"},
    )
    assert resp.status_code == 401


# === 2) LIST ===


async def test_list_returns_only_current_projects_environments(client):
    alice = await _register_user(client, username="alice3", email="alice3@example.com")
    bob = await _register_user(
        client, username="bob3", email="bob3@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AP")
    bob_project = await _create_project(client, bob["token"], name="BP")

    await _create_environment(client, alice["token"], alice_project["id"], name="dev")
    await _create_environment(
        client, alice["token"], alice_project["id"], name="staging"
    )
    await _create_environment(client, bob["token"], bob_project["id"], name="dev")

    resp = await client.get(
        f"/api/v1/projects/{alice_project['id']}/environments",
        headers=_auth(alice["token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = sorted(e["name"] for e in body["items"])
    assert names == ["dev", "staging"]
    assert body["total"] == 2


async def test_list_with_search_filters_by_name(client):
    user = await _register_user(client, username="searcher", email="searcher@example.com")
    project = await _create_project(client, user["token"], name="SP")
    await _create_environment(client, user["token"], project["id"], name="dev")
    await _create_environment(client, user["token"], project["id"], name="staging")
    await _create_environment(client, user["token"], project["id"], name="prod")

    resp = await client.get(
        f"/api/v1/projects/{project['id']}/environments?search=stag",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "staging"


async def test_list_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice4", email="alice4@example.com")
    bob = await _register_user(
        client, username="bob4", email="bob4@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AP")

    resp = await client.get(
        f"/api/v1/projects/{alice_project['id']}/environments",
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


# === 3) DETAIL ===


async def test_get_own_environment_returns_200(client):
    user = await _register_user(client, username="self", email="self@example.com")
    project = await _create_project(client, user["token"], name="SP")
    create = await _create_environment(
        client, user["token"], project["id"], name="dev"
    )
    eid = create.json()["id"]

    resp = await client.get(
        f"/api/v1/environments/{eid}", headers=_auth(user["token"])
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == eid


async def test_get_others_environment_returns_403(client):
    alice = await _register_user(client, username="alice5", email="alice5@example.com")
    bob = await _register_user(
        client, username="bob5", email="bob5@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="AP")
    create = await _create_environment(
        client, alice["token"], project["id"], name="dev"
    )
    eid = create.json()["id"]

    resp = await client.get(
        f"/api/v1/environments/{eid}", headers=_auth(bob["token"])
    )
    assert resp.status_code == 403


async def test_get_nonexistent_environment_returns_404(client):
    user = await _register_user(client, username="ghost2", email="ghost2@example.com")
    resp = await client.get(
        f"/api/v1/environments/{uuid.uuid4()}", headers=_auth(user["token"])
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "ENVIRONMENT_NOT_FOUND"


# === 4) UPDATE ===


async def test_owner_can_update_environment_fields(client):
    user = await _register_user(client, username="eve", email="eve@example.com")
    project = await _create_project(client, user["token"], name="EP")
    create = await _create_environment(
        client, user["token"], project["id"], name="dev"
    )
    eid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/environments/{eid}",
        json={"base_url": "https://api.staging.example.com"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["base_url"] == "https://api.staging.example.com"


async def test_update_with_duplicate_name_returns_409(client):
    user = await _register_user(client, username="frank", email="frank@example.com")
    project = await _create_project(client, user["token"], name="FP")
    await _create_environment(client, user["token"], project["id"], name="dev")
    staging = await _create_environment(
        client, user["token"], project["id"], name="staging"
    )

    resp = await client.put(
        f"/api/v1/environments/{staging.json()['id']}",
        json={"name": "dev"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"


async def test_non_owner_cannot_update_environment(client):
    alice = await _register_user(client, username="alice6", email="alice6@example.com")
    bob = await _register_user(
        client, username="bob6", email="bob6@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="AP")
    create = await _create_environment(
        client, alice["token"], project["id"], name="dev"
    )

    resp = await client.put(
        f"/api/v1/environments/{create.json()['id']}",
        json={"base_url": "https://hijack.example.com"},
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


# === 5) DEFAULT ENVIRONMENT BEHAVIOR ===


async def test_promoting_one_default_demotes_previous(client):
    user = await _register_user(client, username="grace", email="grace@example.com")
    project = await _create_project(client, user["token"], name="GP")
    dev = await _create_environment(
        client, user["token"], project["id"], name="dev", is_default=True
    )
    staging = await _create_environment(
        client, user["token"], project["id"], name="staging"
    )

    # Promote staging to default.
    resp = await client.post(
        f"/api/v1/environments/{staging.json()['id']}/set-default",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_default"] is True

    # dev must now be demoted.
    after = await client.get(
        f"/api/v1/environments/{dev.json()['id']}", headers=_auth(user["token"])
    )
    assert after.status_code == 200
    assert after.json()["is_default"] is False


async def test_creating_two_defaults_demotes_first(client):
    user = await _register_user(client, username="henry", email="henry@example.com")
    project = await _create_project(client, user["token"], name="HP")

    dev = await _create_environment(
        client, user["token"], project["id"], name="dev", is_default=True
    )
    assert dev.json()["is_default"] is True

    staging = await _create_environment(
        client, user["token"], project["id"], name="staging", is_default=True
    )
    assert staging.json()["is_default"] is True

    # dev must have been demoted.
    after = await client.get(
        f"/api/v1/environments/{dev.json()['id']}", headers=_auth(user["token"])
    )
    assert after.json()["is_default"] is False


# === 6) DELETE ===


async def test_owner_can_delete_non_default_environment(client):
    user = await _register_user(client, username="ivy", email="ivy@example.com")
    project = await _create_project(client, user["token"], name="IP")
    await _create_environment(
        client, user["token"], project["id"], name="dev", is_default=True
    )
    staging = await _create_environment(
        client, user["token"], project["id"], name="staging"
    )

    resp = await client.delete(
        f"/api/v1/environments/{staging.json()['id']}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Environment deleted"

    # And it's actually gone.
    after = await client.get(
        f"/api/v1/environments/{staging.json()['id']}", headers=_auth(user["token"])
    )
    assert after.status_code == 404


async def test_delete_default_environment_returns_409(client):
    user = await _register_user(client, username="jack", email="jack@example.com")
    project = await _create_project(client, user["token"], name="JP")
    dev = await _create_environment(
        client, user["token"], project["id"], name="dev", is_default=True
    )

    resp = await client.delete(
        f"/api/v1/environments/{dev.json()['id']}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"

    # Still present.
    after = await client.get(
        f"/api/v1/environments/{dev.json()['id']}", headers=_auth(user["token"])
    )
    assert after.status_code == 200


async def test_delete_nonexistent_environment_returns_404(client):
    user = await _register_user(client, username="ghost3", email="ghost3@example.com")
    resp = await client.delete(
        f"/api/v1/environments/{uuid.uuid4()}", headers=_auth(user["token"])
    )
    assert resp.status_code == 404


async def test_delete_without_token_returns_401(client):
    resp = await client.delete(f"/api/v1/environments/{uuid.uuid4()}")
    assert resp.status_code == 401
