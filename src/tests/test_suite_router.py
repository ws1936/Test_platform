"""HTTP API tests for the suite management router (F006).

Covers the complete suite lifecycle + suite-case association
operations and authorization boundaries:

* Suite CRUD — 201 / 200 / 409 / 403 / 404 / 401
* SuiteCase bulk add — idempotent + reports added/already_present
* SuiteCase list / remove — sorted + idempotent
* Cross-project isolation — every URL mismatch returns 404

All tests use the real ``/api/v1/auth/register`` + JWT flow so they
exercise the same auth + exception-handling path as production.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest


pytestmark = pytest.mark.asyncio


# === Helpers (mirror test_environment_router.py's pattern) ===


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
        json={"name": name, "description": "suite test"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_suite(
    client,
    token: str,
    project_id: str,
    *,
    name: str,
    description: str = "auto",
):
    return await client.post(
        f"/api/v1/projects/{project_id}/suites",
        json={"name": name, "description": description},
        headers=_auth(token),
    )


# === 1) CREATE ===


async def test_create_suite_with_valid_data_returns_201(client):
    user = await _register_user(client, username="alice", email="alice@example.com")
    project = await _create_project(client, user["token"], name="P1")

    resp = await _create_suite(client, user["token"], project["id"], name="smoke")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "smoke"
    assert body["description"] == "auto"
    assert body["project_id"] == project["id"]
    assert body["sort_order"] == 0
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_suite_with_duplicate_name_returns_409(client):
    user = await _register_user(client, username="carol", email="carol@example.com")
    project = await _create_project(client, user["token"], name="P3")

    first = await _create_suite(client, user["token"], project["id"], name="smoke")
    assert first.status_code == 201

    dup = await _create_suite(client, user["token"], project["id"], name="smoke")
    assert dup.status_code == 409
    assert dup.json()["code"] == "CONFLICT"


async def test_create_suite_extra_project_id_is_rejected_with_422(client):
    """Security: clients cannot forge project_id — extra fields are 422."""
    user = await _register_user(client, username="erin", email="erin@example.com")
    project = await _create_project(client, user["token"], name="P5")

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites",
        json={
            "name": "smoke",
            "description": "auto",
            "project_id": str(uuid.uuid4()),
        },
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_create_suite_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice2", email="alice2@example.com")
    bob = await _register_user(
        client, username="bob2", email="bob2@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AP")

    resp = await _create_suite(client, bob["token"], alice_project["id"], name="x")
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


async def test_create_suite_on_missing_project_returns_404(client):
    user = await _register_user(client, username="ghost", email="ghost@example.com")
    resp = await _create_suite(client, user["token"], str(uuid.uuid4()), name="x")
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROJECT_NOT_FOUND"


async def test_create_suite_without_token_returns_401(client):
    resp = await client.post(
        f"/api/v1/projects/{uuid.uuid4()}/suites",
        json={"name": "x", "description": "auto"},
    )
    assert resp.status_code == 401


# === 2) LIST ===


async def test_list_suites_returns_current_projects_in_insertion_order(client):
    user = await _register_user(client, username="alice3", email="alice3@example.com")
    project = await _create_project(client, user["token"], name="P")

    for name in ("a", "b", "c"):
        r = await _create_suite(client, user["token"], project["id"], name=name)
        assert r.status_code == 201

    resp = await client.get(
        f"/api/v1/projects/{project['id']}/suites",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [s["name"] for s in body["items"]] == ["a", "b", "c"]
    assert body["total"] == 3


async def test_list_suites_with_search_filters_by_name(client):
    user = await _register_user(
        client, username="searcher", email="searcher@example.com"
    )
    project = await _create_project(client, user["token"], name="SP")
    for name in ("smoke", "smoker", "regression"):
        await _create_suite(client, user["token"], project["id"], name=name)

    resp = await client.get(
        f"/api/v1/projects/{project['id']}/suites?search=smoke",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    names = sorted(s["name"] for s in body["items"])
    assert names == ["smoke", "smoker"]


async def test_list_suites_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice4", email="alice4@example.com")
    bob = await _register_user(
        client, username="bob4", email="bob4@example.com", admin_token=alice["token"]
    )
    alice_project = await _create_project(client, alice["token"], name="AP")

    resp = await client.get(
        f"/api/v1/projects/{alice_project['id']}/suites",
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


# === 3) DETAIL ===


async def test_get_own_suite_returns_200(client):
    user = await _register_user(client, username="self", email="self@example.com")
    project = await _create_project(client, user["token"], name="SP")
    create = await _create_suite(client, user["token"], project["id"], name="x")
    sid = create.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{project['id']}/suites/{sid}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == sid
    assert resp.json()["cases"] == []


async def test_suite_detail_contains_cases_sorted_by_order(client, create_test_cases):
    user = await _register_user(client, username="detail", email="detail@example.com")
    project = await _create_project(client, user["token"], name="detail-project")
    suite = await _create_suite(client, user["token"], project["id"], name="ordered")
    suite_id = suite.json()["id"]
    case_ids = [str(uuid.uuid4()) for _ in range(3)]
    await create_test_cases(project["id"], case_ids)

    added = await _bulk_add(
        client,
        user["token"],
        project["id"],
        suite_id,
        [case_ids[2], case_ids[0], case_ids[1]],
    )
    assert added.status_code == 200, added.text

    detail = await client.get(
        f"/api/v1/projects/{project['id']}/suites/{suite_id}",
        headers=_auth(user["token"]),
    )
    assert detail.status_code == 200, detail.text
    cases = detail.json()["cases"]
    assert [case["test_case_id"] for case in cases] == [
        case_ids[2],
        case_ids[0],
        case_ids[1],
    ]
    assert [case["order"] for case in cases] == [0, 1, 2]


async def test_bulk_add_nonexistent_case_returns_404(client):
    user = await _register_user(
        client, username="missingcase", email="missingcase@example.com"
    )
    project = await _create_project(client, user["token"], name="missing-case-project")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    response = await _bulk_add(
        client, user["token"], project["id"], suite.json()["id"], [str(uuid.uuid4())]
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "TEST_CASE_NOT_FOUND"


async def test_get_suite_with_wrong_project_id_returns_404(client):
    """A valid suite under the wrong project must be treated as missing,
    not as a leaked resource."""
    alice = await _register_user(client, username="alice5", email="alice5@example.com")
    project_a = await _create_project(client, alice["token"], name="A")
    project_b = await _create_project(client, alice["token"], name="B")
    suite = await _create_suite(client, alice["token"], project_a["id"], name="x")

    resp = await client.get(
        f"/api/v1/projects/{project_b['id']}/suites/{suite.json()['id']}",
        headers=_auth(alice["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "SUITE_NOT_FOUND"


async def test_get_nonexistent_suite_returns_404(client):
    user = await _register_user(client, username="ghost2", email="ghost2@example.com")
    project = await _create_project(client, user["token"], name="GP")
    resp = await client.get(
        f"/api/v1/projects/{project['id']}/suites/{uuid.uuid4()}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "SUITE_NOT_FOUND"


# === 4) UPDATE ===


async def test_owner_can_update_suite_description(client):
    user = await _register_user(client, username="eve", email="eve@example.com")
    project = await _create_project(client, user["token"], name="EP")
    create = await _create_suite(client, user["token"], project["id"], name="x")
    sid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{project['id']}/suites/{sid}",
        json={"description": "updated by owner"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["description"] == "updated by owner"


async def test_update_with_duplicate_name_returns_409(client):
    user = await _register_user(client, username="frank", email="frank@example.com")
    project = await _create_project(client, user["token"], name="FP")
    await _create_suite(client, user["token"], project["id"], name="a")
    b = await _create_suite(client, user["token"], project["id"], name="b")

    resp = await client.put(
        f"/api/v1/projects/{project['id']}/suites/{b.json()['id']}",
        json={"name": "a"},
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 409


async def test_non_owner_cannot_update_suite(client):
    alice = await _register_user(client, username="alice6", email="alice6@example.com")
    bob = await _register_user(
        client, username="bob6", email="bob6@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="AP")
    create = await _create_suite(client, alice["token"], project["id"], name="x")

    resp = await client.put(
        f"/api/v1/projects/{project['id']}/suites/{create.json()['id']}",
        json={"description": "hijack"},
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


# === 5) DELETE ===


async def test_owner_can_delete_suite(client):
    user = await _register_user(client, username="ivy", email="ivy@example.com")
    project = await _create_project(client, user["token"], name="IP")
    create = await _create_suite(client, user["token"], project["id"], name="x")

    resp = await client.delete(
        f"/api/v1/projects/{project['id']}/suites/{create.json()['id']}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Suite deleted"

    after = await client.get(
        f"/api/v1/projects/{project['id']}/suites/{create.json()['id']}",
        headers=_auth(user["token"]),
    )
    assert after.status_code == 404


async def test_delete_with_wrong_project_id_returns_404(client):
    alice = await _register_user(client, username="alice7", email="alice7@example.com")
    project_a = await _create_project(client, alice["token"], name="A")
    project_b = await _create_project(client, alice["token"], name="B")
    suite = await _create_suite(client, alice["token"], project_a["id"], name="x")

    resp = await client.delete(
        f"/api/v1/projects/{project_b['id']}/suites/{suite.json()['id']}",
        headers=_auth(alice["token"]),
    )
    assert resp.status_code == 404


async def test_delete_without_token_returns_401(client):
    resp = await client.delete(f"/api/v1/projects/{uuid.uuid4()}/suites/{uuid.uuid4()}")
    assert resp.status_code == 401


# === 6) SuiteCase bulk add — ordering + idempotency at the HTTP layer ===


async def _bulk_add(
    client, token: str, project_id: str, suite_id: str, test_case_ids: list[str]
) -> Any:
    return await client.post(
        f"/api/v1/projects/{project_id}/suites/{suite_id}/cases",
        json={"test_case_ids": test_case_ids},
        headers=_auth(token),
    )


async def test_bulk_add_cases_returns_added_and_already_present(
    client, create_test_cases
):
    user = await _register_user(client, username="jack", email="jack@example.com")
    project = await _create_project(client, user["token"], name="JP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    tc_a, tc_b = str(uuid.uuid4()), str(uuid.uuid4())
    await create_test_cases(project["id"], [tc_a, tc_b])

    # First add — both are new.
    r1 = await _bulk_add(
        client, user["token"], project["id"], suite.json()["id"], [tc_a, tc_b]
    )
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert {a["test_case_id"] for a in body["added"]} == {tc_a, tc_b}
    assert body["already_present"] == []
    # Insertion order preserved on the wire.
    assert [a["test_case_id"] for a in body["added"]] == [tc_a, tc_b]

    # Second add — both are already present, returned in caller order.
    r2 = await _bulk_add(
        client, user["token"], project["id"], suite.json()["id"], [tc_a, tc_b]
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["added"] == []
    assert body["already_present"] == [tc_a, tc_b]


async def test_bulk_add_dedupes_repeated_test_case_ids_in_payload(
    client, create_test_cases
):
    user = await _register_user(client, username="kate", email="kate@example.com")
    project = await _create_project(client, user["token"], name="KP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    tc = str(uuid.uuid4())
    await create_test_cases(project["id"], [tc])
    r = await _bulk_add(
        client, user["token"], project["id"], suite.json()["id"], [tc, tc, tc]
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["added"]) == 1
    assert body["already_present"] == []


async def test_bulk_add_empty_list_returns_422(client):
    user = await _register_user(client, username="liam", email="liam@example.com")
    project = await _create_project(client, user["token"], name="LP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    r = await _bulk_add(client, user["token"], project["id"], suite.json()["id"], [])
    assert r.status_code == 422


async def test_bulk_add_on_other_users_project_returns_403(client):
    alice = await _register_user(client, username="alice8", email="alice8@example.com")
    bob = await _register_user(
        client, username="bob8", email="bob8@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="AP")
    suite = await _create_suite(client, alice["token"], project["id"], name="s")

    r = await _bulk_add(
        client,
        bob["token"],
        project["id"],
        suite.json()["id"],
        [str(uuid.uuid4())],
    )
    assert r.status_code == 403


# === 7) SuiteCase list + remove ===


async def test_list_suite_cases_returns_insertion_order(client, create_test_cases):
    user = await _register_user(client, username="mia", email="mia@example.com")
    project = await _create_project(client, user["token"], name="MP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    ids = [str(uuid.uuid4()) for _ in range(3)]
    await create_test_cases(project["id"], ids)
    await _bulk_add(client, user["token"], project["id"], suite.json()["id"], ids)

    resp = await client.get(
        f"/api/v1/projects/{project['id']}/suites/{suite.json()['id']}/cases",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [c["test_case_id"] for c in body] == ids


async def test_remove_case_is_idempotent(client, create_test_cases):
    user = await _register_user(client, username="nick", email="nick@example.com")
    project = await _create_project(client, user["token"], name="NP")
    suite = await _create_suite(client, user["token"], project["id"], name="s")

    tc = str(uuid.uuid4())
    await create_test_cases(project["id"], [tc])
    await _bulk_add(client, user["token"], project["id"], suite.json()["id"], [tc])

    # First remove — 200, row goes away.
    r1 = await client.delete(
        f"/api/v1/projects/{project['id']}/suites/{suite.json()['id']}/cases/{tc}",
        headers=_auth(user["token"]),
    )
    assert r1.status_code == 200
    assert r1.json()["message"] == "Case removed from suite"

    detail = await client.get(
        f"/api/v1/projects/{project['id']}/suites/{suite.json()['id']}",
        headers=_auth(user["token"]),
    )
    assert detail.status_code == 200
    assert all(case["test_case_id"] != tc for case in detail.json()["cases"])

    # Second remove — still 200 (idempotent).
    r2 = await client.delete(
        f"/api/v1/projects/{project['id']}/suites/{suite.json()['id']}/cases/{tc}",
        headers=_auth(user["token"]),
    )
    assert r2.status_code == 200


async def test_reorder_cases_changes_suite_detail_order(client, create_test_cases):
    user = await _register_user(client, username="reorder", email="reorder@example.com")
    project = await _create_project(client, user["token"], name="reorder-project")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    suite_id = suite.json()["id"]
    case_ids = [str(uuid.uuid4()) for _ in range(3)]
    await create_test_cases(project["id"], case_ids)
    added = await _bulk_add(client, user["token"], project["id"], suite_id, case_ids)
    assert added.status_code == 200, added.text

    reordered = [case_ids[2], case_ids[0], case_ids[1]]
    response = await client.put(
        f"/api/v1/projects/{project['id']}/suites/{suite_id}/cases/order",
        json={"case_ids": reordered},
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    assert [case["test_case_id"] for case in response.json()] == reordered
    assert [case["order"] for case in response.json()] == [0, 1, 2]

    detail = await client.get(
        f"/api/v1/projects/{project['id']}/suites/{suite_id}",
        headers=_auth(user["token"]),
    )
    assert [case["test_case_id"] for case in detail.json()["cases"]] == reordered


async def test_delete_suite_clears_associated_suite_cases(
    client, create_test_cases, db_session
):
    from sqlalchemy import select
    from app.domain.suite.model import ApiSuiteCase
    from uuid import UUID

    user = await _register_user(client, username="cascade", email="cascade@example.com")
    project = await _create_project(client, user["token"], name="cascade-project")
    suite = await _create_suite(client, user["token"], project["id"], name="s")
    suite_id = suite.json()["id"]
    case_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    await create_test_cases(project["id"], case_ids)
    added = await _bulk_add(client, user["token"], project["id"], suite_id, case_ids)
    assert added.status_code == 200, added.text

    response = await client.delete(
        f"/api/v1/projects/{project['id']}/suites/{suite_id}",
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    remaining = (
        (
            await db_session.execute(
                select(ApiSuiteCase).where(ApiSuiteCase.suite_id == UUID(suite_id))
            )
        )
        .scalars()
        .all()
    )
    assert remaining == []


async def test_remove_case_on_wrong_project_returns_404(client, create_test_cases):
    alice = await _register_user(client, username="alice9", email="alice9@example.com")
    project_a = await _create_project(client, alice["token"], name="A")
    project_b = await _create_project(client, alice["token"], name="B")
    suite = await _create_suite(client, alice["token"], project_a["id"], name="s")
    tc = str(uuid.uuid4())
    await create_test_cases(project_a["id"], [tc])
    await _bulk_add(client, alice["token"], project_a["id"], suite.json()["id"], [tc])

    r = await client.delete(
        f"/api/v1/projects/{project_b['id']}/suites/{suite.json()['id']}/cases/{tc}",
        headers=_auth(alice["token"]),
    )
    assert r.status_code == 404
