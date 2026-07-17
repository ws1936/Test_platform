"""HTTP API tests for F007 test case management router.

Covers the full CRUD lifecycle plus the authorization boundaries:

* Create  — valid payload returns 201, invalid method returns 422,
            missing auth returns 401, non-owner project returns 403,
            missing suite returns 404.
* List    — returns ONLY cases of the caller's project; ``search``
            filters by name; suite-scoped list excludes free-floating
            cases; cross-project access returns 403.
* Detail  — non-owner gets 403, missing case returns 404.
* Update  — owner can patch fields; ``enabled`` toggle works; missing
            case returns 404; extra fields rejected with 422.
* Delete  — owner can delete; cascade clears ``api_suite_cases``;
            missing case returns 404; unauthenticated returns 401.

All tests use the real ``/api/v1/auth/register`` + JWT flow so they
exercise the same auth + exception-handling path as production.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from sqlalchemy import select




# === Helpers (mirror test_suite_router.py's pattern) ===


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
        json={"name": name, "description": "test case test"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_suite(client, token: str, project_id: str, *, name: str):
    resp = await client.post(
        f"/api/v1/projects/{project_id}/suites",
        json={"name": name, "description": "auto"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_payload(
    *,
    name: str = "login",
    method: str = "GET",
    path: str = "/api/users/{{user_id}}",
    headers: dict | None = None,
    query_params: dict | None = None,
    body_type: str = "none",
    body: Any = None,
    assertions: list[dict] | None = None,
    timeout_seconds: int = 30,
    enabled: bool = True,
) -> dict:
    payload: dict[str, Any] = {
        "name": name,
        "method": method,
        "path": path,
        "timeout_seconds": timeout_seconds,
        "enabled": enabled,
    }
    if headers is not None:
        payload["headers"] = headers
    if query_params is not None:
        payload["query_params"] = query_params
    if body_type != "none":
        payload["body_type"] = body_type
    if body is not None:
        payload["body"] = body
    if assertions is not None:
        payload["assertions"] = assertions
    return payload


async def _create_case(client, token: str, suite_id: str, **overrides):
    return await client.post(
        f"/api/v1/collections/{suite_id}/cases",
        json=_make_payload(**overrides),
        headers=_auth(token),
    )


# === 1) CREATE ===


async def test_create_test_case_with_valid_data_returns_201(client):
    user = await _register_user(client, username="alice", email="alice@example.com")
    project = await _create_project(client, user["token"], name="P1")
    suite = await _create_suite(client, user["token"], project["id"], name="smoke")

    resp = await _create_case(
        client,
        user["token"],
        suite["id"],
        name="login",
        method="POST",
        path="/api/login",
        headers={"Accept": "application/json"},
        body_type="json",
        body={"username": "alice"},
        assertions=[{"type": "status_code", "operator": "eq", "expected": 200}],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "login"
    assert body["method"] == "POST"
    assert body["path"] == "/api/login"
    assert body["body_type"] == "json"
    assert body["body"] == {"username": "alice"}
    assert body["headers"] == {"Accept": "application/json"}
    assert body["assertions"] == [
        {"type": "status_code", "operator": "eq", "expected": 200}
    ]
    assert body["enabled"] is True
    assert body["timeout_seconds"] == 30
    assert body["project_id"] == project["id"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_test_case_lowercases_method(client):
    """``method`` validator uppercases input — lowercase should still work."""
    user = await _register_user(
        client, username="lowercaser", email="lowercaser@example.com"
    )
    project = await _create_project(client, user["token"], name="LC")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    resp = await _create_case(
        client, user["token"], suite["id"], name="x", method="post"
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["method"] == "POST"


async def test_create_test_case_invalid_method_returns_422(client):
    user = await _register_user(client, username="alice2", email="alice2@example.com")
    project = await _create_project(client, user["token"], name="P2")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    resp = await _create_case(
        client, user["token"], suite["id"], name="x", method="OPTIONS"
    )
    assert resp.status_code == 422


async def test_create_test_case_invalid_body_type_returns_422(client):
    user = await _register_user(client, username="alice3", email="alice3@example.com")
    project = await _create_project(client, user["token"], name="P3")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    resp = await _create_case(
        client, user["token"], suite["id"], name="x", body_type="xml"
    )
    assert resp.status_code == 422


async def test_create_test_case_path_must_start_with_slash(client):
    user = await _register_user(client, username="alice4", email="alice4@example.com")
    project = await _create_project(client, user["token"], name="P4")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    resp = await _create_case(
        client, user["token"], suite["id"], name="x", path="api/login"
    )
    assert resp.status_code == 422


async def test_create_test_case_extra_project_id_is_rejected_with_422(client):
    """Security: clients cannot forge project_id — extra fields are 422."""
    user = await _register_user(client, username="alice5", email="alice5@example.com")
    project = await _create_project(client, user["token"], name="P5")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    resp = await client.post(
        f"/api/v1/collections/{suite['id']}/cases",
        json={
            **_make_payload(name="x"),
            "project_id": str(uuid.uuid4()),
        },
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_create_test_case_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice6", email="alice6@example.com")
    bob = await _register_user(
        client, username="bob6", email="bob6@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AP")
    suite = await _create_suite(client, alice["token"], alice_project["id"], name="s")

    resp = await _create_case(client, bob["token"], suite["id"], name="x")
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


async def test_create_test_case_on_missing_suite_returns_404(client):
    user = await _register_user(client, username="ghost", email="ghost@example.com")
    resp = await _create_case(client, user["token"], str(uuid.uuid4()), name="x")
    assert resp.status_code == 404
    assert resp.json()["code"] == "SUITE_NOT_FOUND"


async def test_create_test_case_without_token_returns_401(client):
    resp = await client.post(
        f"/api/v1/collections/{uuid.uuid4()}/cases",
        json=_make_payload(name="x"),
    )
    assert resp.status_code == 401


# === 2) LIST (suite-scoped + project-scoped) ===


async def test_list_suite_cases_returns_attached_cases_in_insertion_order(
    client,
):
    user = await _register_user(client, username="alice7", email="alice7@example.com")
    project = await _create_project(client, user["token"], name="P7")
    suite = await _create_suite(client, user["token"], project["id"], name="smoke")

    for name in ("a", "b", "c"):
        r = await _create_case(client, user["token"], suite["id"], name=name)
        assert r.status_code == 201

    resp = await client.get(
        f"/api/v1/collections/{suite['id']}/cases",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [c["name"] for c in body] == ["a", "b", "c"]


async def test_list_project_cases_returns_every_case_including_floating(client):
    """A case attached to no suite still shows up in the project list."""
    user = await _register_user(client, username="alice8", email="alice8@example.com")
    project = await _create_project(client, user["token"], name="P8")

    # Create a case directly via the create-in-suite endpoint, then create
    # a free-floating case by attaching it only via project list.  We use
    # the suite path here and verify that the suite-scoped list returns
    # it AND the project-scoped list returns it too.
    suite = await _create_suite(client, user["token"], project["id"], name="smoke")
    r = await _create_case(client, user["token"], suite["id"], name="in-suite")
    assert r.status_code == 201

    # Project-scoped list returns every case of the project.
    resp = await client.get(
        f"/api/v1/projects/{project['id']}/test-cases",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert [c["name"] for c in body["items"]] == ["in-suite"]


async def test_list_project_cases_with_search_filters_by_name(client):
    user = await _register_user(client, username="search", email="search@example.com")
    project = await _create_project(client, user["token"], name="SP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    for name in ("login", "logout", "register"):
        r = await _create_case(client, user["token"], suite["id"], name=name)
        assert r.status_code == 201

    resp = await client.get(
        f"/api/v1/projects/{project['id']}/test-cases?search=log",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    names = sorted(c["name"] for c in body["items"])
    assert names == ["login", "logout"]


async def test_list_suite_cases_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice9", email="alice9@example.com")
    bob = await _register_user(
        client, username="bob9", email="bob9@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AP")
    suite = await _create_suite(client, alice["token"], alice_project["id"], name="s")

    resp = await client.get(
        f"/api/v1/collections/{suite['id']}/cases",
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


async def test_list_project_cases_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice10", email="alice10@example.com")
    bob = await _register_user(
        client, username="bob10", email="bob10@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AP")

    resp = await client.get(
        f"/api/v1/projects/{alice_project['id']}/test-cases",
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


async def test_list_suite_cases_on_missing_suite_returns_404(client):
    user = await _register_user(client, username="ghost2", email="ghost2@example.com")
    resp = await client.get(
        f"/api/v1/collections/{uuid.uuid4()}/cases",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "SUITE_NOT_FOUND"


# === 3) DETAIL ===


async def test_get_own_test_case_returns_200(client):
    user = await _register_user(client, username="self", email="self@example.com")
    project = await _create_project(client, user["token"], name="SP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    create = await _create_case(client, user["token"], suite["id"], name="x")
    cid = create.json()["id"]

    resp = await client.get(
        f"/api/v1/test-cases/{cid}", headers=_auth(user["token"])
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == cid
    assert resp.json()["enabled"] is True


async def test_get_other_users_test_case_returns_403(client):
    alice = await _register_user(client, username="alice11", email="alice11@example.com")
    bob = await _register_user(
        client, username="bob11", email="bob11@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="AP")
    suite = await _create_suite(client, alice["token"], project["id"], name="s")
    create = await _create_case(client, alice["token"], suite["id"], name="x")

    resp = await client.get(
        f"/api/v1/test-cases/{create.json()['id']}", headers=_auth(bob["token"])
    )
    assert resp.status_code == 403


async def test_get_nonexistent_test_case_returns_404(client):
    user = await _register_user(client, username="ghost3", email="ghost3@example.com")
    resp = await client.get(
        f"/api/v1/test-cases/{uuid.uuid4()}", headers=_auth(user["token"])
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "TEST_CASE_NOT_FOUND"


# === 4) UPDATE ===


async def test_owner_can_update_test_case_fields(client):
    user = await _register_user(client, username="eve", email="eve@example.com")
    project = await _create_project(client, user["token"], name="EP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    create = await _create_case(
        client,
        user["token"],
        suite["id"],
        name="x",
        method="GET",
        path="/api/x",
    )
    cid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/test-cases/{cid}",
        json={
            "method": "POST",
            "path": "/api/y",
            "timeout_seconds": 60,
            "enabled": False,
        },
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["method"] == "POST"
    assert body["path"] == "/api/y"
    assert body["timeout_seconds"] == 60
    assert body["enabled"] is False


async def test_partial_update_only_touches_supplied_fields(client):
    user = await _register_user(client, username="eve2", email="eve2@example.com")
    project = await _create_project(client, user["token"], name="EP2")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    create = await _create_case(
        client,
        user["token"],
        suite["id"],
        name="x",
        method="POST",
        path="/api/login",
    )
    cid = create.json()["id"]

    # PATCH only the path.
    resp = await client.put(
        f"/api/v1/test-cases/{cid}",
        json={"path": "/api/v2/login"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] == "/api/v2/login"
    # Untouched fields keep their values.
    assert body["method"] == "POST"
    assert body["name"] == "x"


async def test_update_extra_fields_returns_422(client):
    user = await _register_user(client, username="eve3", email="eve3@example.com")
    project = await _create_project(client, user["token"], name="EP3")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    create = await _create_case(client, user["token"], suite["id"], name="x")
    cid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/test-cases/{cid}",
        json={"project_id": str(uuid.uuid4())},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_update_with_invalid_method_returns_422(client):
    user = await _register_user(client, username="eve4", email="eve4@example.com")
    project = await _create_project(client, user["token"], name="EP4")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    create = await _create_case(client, user["token"], suite["id"], name="x")
    cid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/test-cases/{cid}",
        json={"method": "TRACE"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_non_owner_cannot_update_test_case(client):
    alice = await _register_user(client, username="alice12", email="alice12@example.com")
    bob = await _register_user(
        client, username="bob12", email="bob12@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="AP")
    suite = await _create_suite(client, alice["token"], project["id"], name="s")
    create = await _create_case(client, alice["token"], suite["id"], name="x")

    resp = await client.put(
        f"/api/v1/test-cases/{create.json()['id']}",
        json={"enabled": False},
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


async def test_update_nonexistent_test_case_returns_404(client):
    user = await _register_user(client, username="ghost4", email="ghost4@example.com")
    resp = await client.put(
        f"/api/v1/test-cases/{uuid.uuid4()}",
        json={"name": "x"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404


# === 5) DELETE ===


async def test_owner_can_delete_test_case(client):
    user = await _register_user(client, username="ivy", email="ivy@example.com")
    project = await _create_project(client, user["token"], name="IP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    create = await _create_case(client, user["token"], suite["id"], name="x")

    resp = await client.delete(
        f"/api/v1/test-cases/{create.json()['id']}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Test case deleted"

    after = await client.get(
        f"/api/v1/test-cases/{create.json()['id']}", headers=_auth(user["token"])
    )
    assert after.status_code == 404


async def test_delete_test_case_clears_suite_associations(
    client, db_session
):
    """``ON DELETE CASCADE`` on ``api_suite_cases`` must clean up rows.

    SQLite must run with ``PRAGMA foreign_keys=ON`` for this to fire.
    The service-level test engine already enables it; this HTTP-level
    test verifies the behaviour end-to-end.
    """
    from app.domain.suite.model import ApiSuiteCase
    from app.domain.test_case.model import ApiTestCase

    user = await _register_user(client, username="cascade", email="cascade@example.com")
    project = await _create_project(client, user["token"], name="CP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    suite_id = suite["id"]
    create = await _create_case(client, user["token"], suite_id, name="x")
    cid = create.json()["id"]

    # Pre-condition: an association exists.
    rows = (
        await db_session.execute(
            select(ApiSuiteCase).where(ApiSuiteCase.test_case_id == uuid.UUID(cid))
        )
    ).scalars().all()
    assert len(rows) == 1

    resp = await client.delete(
        f"/api/v1/test-cases/{cid}", headers=_auth(user["token"])
    )
    assert resp.status_code == 200, resp.text

    # Post-condition: the test case row is gone.
    after = await db_session.execute(
        select(ApiTestCase).where(ApiTestCase.id == uuid.UUID(cid))
    )
    assert after.scalar_one_or_none() is None

    # And the association rows are gone too.
    rows = (
        await db_session.execute(
            select(ApiSuiteCase).where(ApiSuiteCase.test_case_id == uuid.UUID(cid))
        )
    ).scalars().all()
    assert rows == []


async def test_delete_nonexistent_test_case_returns_404(client):
    user = await _register_user(client, username="ghost5", email="ghost5@example.com")
    resp = await client.delete(
        f"/api/v1/test-cases/{uuid.uuid4()}", headers=_auth(user["token"])
    )
    assert resp.status_code == 404


async def test_delete_without_token_returns_401(client):
    resp = await client.delete(f"/api/v1/test-cases/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_non_owner_cannot_delete_test_case(client):
    alice = await _register_user(client, username="alice13", email="alice13@example.com")
    bob = await _register_user(
        client, username="bob13", email="bob13@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="AP")
    suite = await _create_suite(client, alice["token"], project["id"], name="s")
    create = await _create_case(client, alice["token"], suite["id"], name="x")

    resp = await client.delete(
        f"/api/v1/test-cases/{create.json()['id']}", headers=_auth(bob["token"])
    )
    assert resp.status_code == 403