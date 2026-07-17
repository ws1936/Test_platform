"""Unit tests for the project management router (F004).

Covers the complete project lifecycle and authorization boundaries:

* Create  — valid payload returns 201, missing fields return 422
* List    — returns ONLY the caller's own projects
* Detail  — non-owner / non-admin gets 403, missing project gets 404
* Update  — only owner / admin can update, validation errors return 422
* Delete  — only owner / admin can delete, deleted project is invisible
* Isolation — a regular user cannot list, read, update, or delete another
  regular user's project

All tests use the real ``/api/v1/auth/register`` + JWT flow so they
exercise the same auth + exception-handling path as production.
"""

from __future__ import annotations

import uuid

import pytest




# === Helpers ===

async def _register_user(
    client,
    *,
    username: str,
    email: str,
    password: str = "TestPass123!",
    admin_token: str | None = None,
) -> dict:
    """Register a user; return ``{"id": ..., "token": ...}``.

    The first user created in a fresh DB is automatically promoted to
    superuser; every subsequent registration requires the superuser's
    access token in ``admin_token``.
    """
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


async def _create_project(
    client, token: str, *, name: str, description: str = "auto"
):
    response = await client.post(
        "/api/v1/projects",
        json={"name": name, "description": description},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response


# === 1) CREATE ===

async def test_create_project_with_valid_data_returns_201(client):
    user = await _register_user(client, username="alice", email="alice@example.com")
    resp = await _create_project(client, user["token"], name="Order Svc")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Order Svc"
    assert body["description"] == "auto"
    assert body["owner_id"] == user["id"]
    # Server-side fields are populated
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_project_missing_name_returns_422(client):
    user = await _register_user(client, username="bob", email="bob@example.com")
    resp = await client.post(
        "/api/v1/projects",
        json={"description": "no name"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    fields = [e["field"] for e in body["details"]]
    assert any("name" in f for f in fields)


async def test_create_project_extra_owner_id_is_rejected_with_422(client):
    """Security: clients cannot forge owner_id — extra fields are 422."""
    user = await _register_user(client, username="carol", email="carol@example.com")
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "x", "owner_id": str(uuid.uuid4())},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_create_project_name_too_long_returns_422(client):
    user = await _register_user(client, username="dave", email="dave@example.com")
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "x" * 101, "description": "auto"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


async def test_create_project_without_token_returns_401(client):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "x"},
    )
    assert resp.status_code == 401


# === 2) LIST (scoped to current user) ===

async def test_list_returns_only_current_users_projects(client):
    alice = await _register_user(client, username="alice2", email="alice2@example.com")
    bob = await _register_user(
        client, username="bob2", email="bob2@example.com", admin_token=alice["token"]
    )

    # Alice owns two, Bob owns one
    await _create_project(client, alice["token"], name="A1")
    await _create_project(client, alice["token"], name="A2")
    await _create_project(client, bob["token"], name="B1")

    # Alice lists → only A1, A2
    resp = await client.get("/api/v1/projects", headers=_auth(alice["token"]))
    assert resp.status_code == 200
    body = resp.json()
    names = sorted(p["name"] for p in body["items"])
    assert names == ["A1", "A2"]
    assert body["total"] == 2
    for p in body["items"]:
        assert p["owner_id"] == alice["id"]

    # Bob lists → only B1
    resp = await client.get("/api/v1/projects", headers=_auth(bob["token"]))
    assert resp.status_code == 200
    body = resp.json()
    names = sorted(p["name"] for p in body["items"])
    assert names == ["B1"]
    assert body["total"] == 1


async def test_list_with_search_filters_by_name(client):
    user = await _register_user(client, username="searcher", email="searcher@example.com")
    await _create_project(client, user["token"], name="Order Svc")
    await _create_project(client, user["token"], name="User Svc")
    await _create_project(client, user["token"], name="Billing Svc")

    resp = await client.get(
        "/api/v1/projects?search=order", headers=_auth(user["token"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Order Svc"


async def test_list_without_token_returns_401(client):
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401


async def test_regular_users_are_fully_isolated_from_each_others_projects(client):
    """User A cannot discover or operate user B's project.

    A separate bootstrap superuser creates two *regular* users so this test
    cannot pass accidentally via the service's documented admin override.
    """
    admin = await _register_user(
        client, username="bootstrap", email="bootstrap@example.com"
    )
    user_a = await _register_user(
        client,
        username="regular_a",
        email="regular_a@example.com",
        admin_token=admin["token"],
    )
    user_b = await _register_user(
        client,
        username="regular_b",
        email="regular_b@example.com",
        admin_token=admin["token"],
    )
    created = await _create_project(
        client, user_b["token"], name="B Private Project", description="original"
    )
    project_id = created.json()["id"]

    # A cannot discover B's project through the collection endpoint.
    listing = await client.get("/api/v1/projects", headers=_auth(user_a["token"]))
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 0
    assert all(item["id"] != project_id for item in listing.json()["items"])

    # A cannot read, mutate, or delete B's project by guessing its UUID.
    detail = await client.get(
        f"/api/v1/projects/{project_id}", headers=_auth(user_a["token"])
    )
    assert detail.status_code == 403
    assert detail.json()["code"] == "FORBIDDEN"

    update = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "taken over", "description": "tampered"},
        headers=_auth(user_a["token"]),
    )
    assert update.status_code == 403
    assert update.json()["code"] == "FORBIDDEN"

    delete = await client.delete(
        f"/api/v1/projects/{project_id}", headers=_auth(user_a["token"])
    )
    assert delete.status_code == 403
    assert delete.json()["code"] == "FORBIDDEN"

    # Failed cross-user operations leave B's project untouched.
    owner_detail = await client.get(
        f"/api/v1/projects/{project_id}", headers=_auth(user_b["token"])
    )
    assert owner_detail.status_code == 200, owner_detail.text
    assert owner_detail.json()["name"] == "B Private Project"
    assert owner_detail.json()["description"] == "original"
    assert owner_detail.json()["owner_id"] == user_b["id"]


# === 3) DETAIL (forbidden for non-owner) ===

async def test_get_others_project_returns_403(client):
    alice = await _register_user(client, username="alice3", email="alice3@example.com")
    bob = await _register_user(
        client, username="bob3", email="bob3@example.com", admin_token=alice["token"]
    )
    create = await _create_project(client, alice["token"], name="AliceProj")
    pid = create.json()["id"]

    # Bob requests Alice's project → 403
    resp = await client.get(f"/api/v1/projects/{pid}", headers=_auth(bob["token"]))
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


async def test_get_own_project_returns_200(client):
    user = await _register_user(client, username="self", email="self@example.com")
    create = await _create_project(client, user["token"], name="Mine")
    pid = create.json()["id"]

    resp = await client.get(f"/api/v1/projects/{pid}", headers=_auth(user["token"]))
    assert resp.status_code == 200
    assert resp.json()["id"] == pid


async def test_get_nonexistent_project_returns_404(client):
    user = await _register_user(client, username="ghost", email="ghost@example.com")
    resp = await client.get(
        f"/api/v1/projects/{uuid.uuid4()}", headers=_auth(user["token"])
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROJECT_NOT_FOUND"


async def test_get_others_nonexistent_project_returns_404_not_403(client):
    """404 takes precedence over 403 so we don't leak project-ID existence."""
    first = await _register_user(client, username="anchor", email="anchor@example.com")
    bob = await _register_user(
        client, username="bobx", email="bobx@example.com", admin_token=first["token"]
    )
    resp = await client.get(
        f"/api/v1/projects/{uuid.uuid4()}", headers=_auth(bob["token"])
    )
    assert resp.status_code == 404


# === 4) UPDATE (owner-only, with validation) ===

async def test_owner_can_update_project_description(client):
    user = await _register_user(client, username="eve", email="eve@example.com")
    create = await _create_project(client, user["token"], name="EveProj")
    pid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{pid}",
        json={"description": "updated by owner"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "updated by owner"


async def test_owner_can_update_project_name(client):
    user = await _register_user(client, username="eve2", email="eve2@example.com")
    create = await _create_project(client, user["token"], name="Old")
    pid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{pid}",
        json={"name": "New"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


async def test_non_owner_cannot_update_project(client):
    alice = await _register_user(client, username="alice4", email="alice4@example.com")
    bob = await _register_user(
        client, username="bob4", email="bob4@example.com", admin_token=alice["token"]
    )
    create = await _create_project(client, alice["token"], name="AliceOnly")
    pid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{pid}",
        json={"name": "hijacked"},
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"

    # Verify the name wasn't actually changed.
    resp = await client.get(f"/api/v1/projects/{pid}", headers=_auth(alice["token"]))
    assert resp.json()["name"] == "AliceOnly"


async def test_update_with_empty_name_returns_422(client):
    user = await _register_user(client, username="frank", email="frank@example.com")
    create = await _create_project(client, user["token"], name="FrankProj")
    pid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{pid}",
        json={"name": ""},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_update_nonexistent_project_returns_404(client):
    user = await _register_user(client, username="ghost2", email="ghost2@example.com")
    resp = await client.put(
        f"/api/v1/projects/{uuid.uuid4()}",
        json={"name": "x"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404


# === 5) DELETE (owner-only; resource disappears afterwards) ===

async def test_owner_can_delete_project_and_its_gone_afterwards(client):
    user = await _register_user(client, username="grace", email="grace@example.com")
    create = await _create_project(client, user["token"], name="GraceProj")
    pid = create.json()["id"]

    # Delete
    resp = await client.delete(
        f"/api/v1/projects/{pid}", headers=_auth(user["token"])
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Project deleted"

    # Detail → 404
    detail = await client.get(
        f"/api/v1/projects/{pid}", headers=_auth(user["token"])
    )
    assert detail.status_code == 404

    # List → not present
    listing = await client.get("/api/v1/projects", headers=_auth(user["token"]))
    assert listing.status_code == 200
    assert all(p["id"] != pid for p in listing.json()["items"])


async def test_non_owner_cannot_delete_project(client):
    alice = await _register_user(client, username="alice5", email="alice5@example.com")
    bob = await _register_user(
        client, username="bob5", email="bob5@example.com", admin_token=alice["token"]
    )
    create = await _create_project(client, alice["token"], name="Safe")
    pid = create.json()["id"]

    resp = await client.delete(
        f"/api/v1/projects/{pid}", headers=_auth(bob["token"])
    )
    assert resp.status_code == 403

    # Project should still exist
    detail = await client.get(
        f"/api/v1/projects/{pid}", headers=_auth(alice["token"])
    )
    assert detail.status_code == 200


async def test_delete_nonexistent_project_returns_404(client):
    user = await _register_user(client, username="ghost3", email="ghost3@example.com")
    resp = await client.delete(
        f"/api/v1/projects/{uuid.uuid4()}", headers=_auth(user["token"])
    )
    assert resp.status_code == 404


async def test_delete_without_token_returns_401(client):
    resp = await client.delete(f"/api/v1/projects/{uuid.uuid4()}")
    assert resp.status_code == 401


# === 6) P0 REGRESSION: token_version + is_active enforcement on create ===

async def test_create_with_stale_token_version_returns_401(client, _db_admin):
    """Stale access tokens (post password change / logout-everywhere) cannot create projects."""
    user = await _register_user(client, username="henry", email="henry@example.com")
    await _db_admin.bump_token_version(uuid.UUID(user["id"]))

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "HenryStale", "description": "stale"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "TOKEN_INVALID"


async def test_create_with_disabled_user_returns_403(client, _db_admin):
    """A disabled user (status=0) cannot create projects."""
    user = await _register_user(client, username="iris", email="iris@example.com")
    await _db_admin.disable(uuid.UUID(user["id"]))

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "IrisProj", "description": "disabled"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "ACCOUNT_DISABLED"


# === 7) P0 REGRESSION: project name conflict (30007 / 409) ===

async def test_create_duplicate_project_name_returns_409(client):
    """Creating two projects with the same name under the same owner should fail with 409."""
    user = await _register_user(client, username="jack", email="jack@example.com")
    first = await client.post(
        "/api/v1/projects",
        json={"name": "Duplicate", "description": "first"},
        headers=_auth(user["token"]),
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/projects",
        json={"name": "Duplicate", "description": "second"},
        headers=_auth(user["token"]),
    )
    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "PROJECT_NAME_TAKEN"


async def test_create_duplicate_name_across_users_is_allowed(client):
    """Two different users can use the same project name (no global uniqueness)."""
    alice = await _register_user(client, username="alice6", email="alice6@example.com")
    bob = await _register_user(
        client, username="bob6", email="bob6@example.com", admin_token=alice["token"]
    )

    a = await client.post(
        "/api/v1/projects",
        json={"name": "Shared", "description": "alice"},
        headers=_auth(alice["token"]),
    )
    b = await client.post(
        "/api/v1/projects",
        json={"name": "Shared", "description": "bob"},
        headers=_auth(bob["token"]),
    )
    assert a.status_code == 201
    assert b.status_code == 201
    assert a.json()["owner_id"] != b.json()["owner_id"]


# === Internal helpers for back-office mutations (token / status) ===
#
# These helpers use the engine that the ``app`` fixture built (which has
# the schema), not the production ``async_session_factory`` (which points
# to a separate in-memory engine that no test ever wrote to).


@pytest.fixture
def _db_admin(app):  # noqa: ANN001 - test helper
    """Yield a helper object bound to the test app's engine."""
    from app.domain.user.service import UserService
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.domain.user.model import User

    session_factory = async_sessionmaker(
        app.state.db_engine, expire_on_commit=False
    )

    class _Admin:
        def __init__(self) -> None:
            self.session_factory = session_factory
            self.User = User
            self.UserService = UserService
            self._select = select

        async def bump_token_version(self, user_id: uuid.UUID) -> None:
            async with self.session_factory() as session:
                await self.UserService(session).bump_token_version(user_id)

        async def disable(self, user_id: uuid.UUID) -> None:
            async with self.session_factory() as session:
                result = await session.execute(
                    self._select(self.User).where(self.User.id == user_id)
                )
                db_user = result.scalar_one()
                db_user.status = 0
                await session.commit()

    return _Admin()
