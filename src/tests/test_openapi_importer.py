"""Tests for F012 OpenAPI importer (parser unit + HTTP route)."""
from __future__ import annotations
import uuid
import pytest
from app.domain.openapi_importer.exceptions import (
    OpenApiFetchError, OpenApiParseError,
)
from app.domain.openapi_importer.parser import OpenApiSpecParser, ParsedSpec


# Process-local preview cache reset (autouse, this-file scope only).
# ``OpenApiImportService._preview_cache`` is a class variable shared
# by every service instance within a process — see SPEC §10 and the
# service's own comment. Without reset, stale ``preview_id`` values
# from one test would leak into another and mask real bugs in the
# commit path.
@pytest.fixture(autouse=True)
def _reset_openapi_preview_cache():
    from app.domain.openapi_importer.service import OpenApiImportService
    OpenApiImportService._preview_cache.clear()
    yield
    OpenApiImportService._preview_cache.clear()




SAMPLE_OPENAPI_3_0 = {
    "openapi": "3.0.0",
    "info": {"title": "Petstore", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com/v1"}],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "tags": ["pets"],
                "parameters": [
                    {"name": "limit", "in": "query",
                     "schema": {"type": "integer", "example": 10}}
                ],
                "responses": {"200": {"description": "ok"}},
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "tags": ["pets"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                            "example": {"name": "fluffy"},
                        }
                    }
                },
                "responses": {"201": {"description": "created"}},
            },
        },
        "/pets/{id}": {
            "get": {
                "operationId": "getPet",
                "summary": "Get a pet by id",
                "tags": ["pets"],
                "parameters": [
                    {"name": "id", "in": "path", "required": True,
                     "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
    "components": {"schemas": {}},
}


# === 1. Parser unit tests =================================================


def test_parser_extracts_metadata():
    parsed = OpenApiSpecParser().parse(SAMPLE_OPENAPI_3_0)
    assert isinstance(parsed, ParsedSpec)
    assert parsed.version == "3.0.0"
    assert parsed.title == "Petstore"
    assert parsed.base_path == "/v1"
    assert len(parsed.operations) == 3


def test_parser_extracts_methods_paths_and_names():
    parsed = OpenApiSpecParser().parse(SAMPLE_OPENAPI_3_0)
    methods = {(op.method, op.path) for op in parsed.operations}
    assert methods == {
        ("GET", "/v1/pets"),
        ("POST", "/v1/pets"),
        ("GET", "/v1/pets/{id}"),
    }


def test_parser_extracts_query_parameter_examples():
    parsed = OpenApiSpecParser().parse(SAMPLE_OPENAPI_3_0)
    list_pets = next(
        op for op in parsed.operations
        if op.method == "GET" and op.path == "/v1/pets"
    )
    assert list_pets.request_query == {"limit": 10}


def test_parser_extracts_header_parameters_with_examples():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/x": {
                "get": {
                    "parameters": [
                        {"name": "X-Token", "in": "header",
                         "schema": {"type": "string", "example": "abc"}}
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    parsed = OpenApiSpecParser().parse(spec)
    assert parsed.operations[0].request_headers == {"X-Token": "abc"}


def test_parser_extracts_request_body_example():
    parsed = OpenApiSpecParser().parse(SAMPLE_OPENAPI_3_0)
    create_pet = next(op for op in parsed.operations if op.method == "POST")
    assert create_pet.request_body == {"name": "fluffy"}
    assert create_pet.request_body_type == "json"


def test_parser_rejects_unsupported_openapi_version():
    with pytest.raises(OpenApiParseError) as exc:
        OpenApiSpecParser().parse({"openapi": "2.0", "info": {}})
    assert "2.0" in str(exc.value)


def test_parser_rejects_missing_openapi_field():
    with pytest.raises(OpenApiParseError):
        OpenApiSpecParser().parse({"info": {}})


def test_parser_filters_by_tags():
    parsed = OpenApiSpecParser().parse(SAMPLE_OPENAPI_3_0, tags=["pets"])
    assert all(op.tags == ["pets"] for op in parsed.operations)


def test_parser_filters_to_zero_when_no_tag_match():
    parsed = OpenApiSpecParser().parse(
        SAMPLE_OPENAPI_3_0, tags=["nonexistent"]
    )
    assert parsed.operations == []


def test_parser_resolves_dollar_ref_in_request_body():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/x": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"},
                                "example": {"name": "x"},
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {"schemas": {"Pet": {"type": "object"}}},
    }
    parsed = OpenApiSpecParser().parse(spec)
    assert parsed.operations[0].request_body == {"name": "x"}


def test_parser_extracts_path_parameter_without_breaking():
    parsed = OpenApiSpecParser().parse(SAMPLE_OPENAPI_3_0)
    by_id = next(op for op in parsed.operations if op.path == "/v1/pets/{id}")
    assert by_id.path == "/v1/pets/{id}"


def test_parser_returns_empty_for_no_paths():
    parsed = OpenApiSpecParser().parse({
        "openapi": "3.0.0",
        "info": {"title": "Empty", "version": "1"},
        "paths": {},
    })
    assert parsed.operations == []


# === 2. HTTP route integration tests =========================================


async def _create_project_and_suite(client, token):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": f"P_{uuid.uuid4().hex[:6]}", "description": "t"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    project = resp.json()
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites",
        json={"name": f"s_{uuid.uuid4().hex[:6]}", "description": "t"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    suite = resp.json()
    return project, suite


async def test_openapi_preview_endpoint_creates_three_cases(client, db_session):
    user = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"u_{uuid.uuid4().hex[:6]}", "email": f"u@e.com",
            "password": "TestPass123!", "nickname": "u",
            "phone": "13800000000",
        },
    )
    assert user.status_code == 201, user.text
    token = user.json()["token"]["access_token"]
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        json={"source_content": SAMPLE_OPENAPI_3_0, "dry_run": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3
    assert body["new_count"] == 3
    assert body["existing_count"] == 0
    assert body["spec_version"] == "3.0.0"
    assert body["base_path"] == "/v1"


async def test_openapi_preview_400_when_both_url_and_content_provided(
    client, db_session
):
    user = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"u_{uuid.uuid4().hex[:6]}", "email": f"u@e.com",
            "password": "TestPass123!", "nickname": "u",
            "phone": "13800000000",
        },
    )
    token = user.json()["token"]["access_token"]
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        json={
            "source_url": "https://example.com/spec.json",
            "source_content": SAMPLE_OPENAPI_3_0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_openapi_preview_400_when_neither_url_nor_content_provided(
    client, db_session
):
    user = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"u_{uuid.uuid4().hex[:6]}", "email": f"u@e.com",
            "password": "TestPass123!", "nickname": "u",
            "phone": "13800000000",
        },
    )
    token = user.json()["token"]["access_token"]
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_openapi_preview_400_for_unsupported_url_scheme(
    client, db_session
):
    user = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"u_{uuid.uuid4().hex[:6]}", "email": f"u@e.com",
            "password": "TestPass123!", "nickname": "u",
            "phone": "13800000000",
        },
    )
    token = user.json()["token"]["access_token"]
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        json={"source_url": "ftp://example.com/spec.json"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_openapi_preview_403_for_non_owner(client, db_session):
    owner = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"o_{uuid.uuid4().hex[:6]}", "email": f"o@e.com",
            "password": "TestPass123!", "nickname": "o",
            "phone": "13800000000",
        },
    )
    owner_token = owner.json()["token"]["access_token"]
    project, suite = await _create_project_and_suite(client, owner_token)

    other = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"x_{uuid.uuid4().hex[:6]}", "email": f"x@e.com",
            "password": "TestPass123!", "nickname": "x",
            "phone": "13800000000",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    other_token = other.json()["token"]["access_token"]

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        json={"source_content": SAMPLE_OPENAPI_3_0, "dry_run": True},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403


async def test_openapi_preview_404_for_missing_project(client, db_session):
    user = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"u_{uuid.uuid4().hex[:6]}", "email": f"u@e.com",
            "password": "TestPass123!", "nickname": "u",
            "phone": "13800000000",
        },
    )
    token = user.json()["token"]["access_token"]
    resp = await client.post(
        f"/api/v1/projects/{uuid.uuid4()}/suites/{uuid.uuid4()}/import/openapi",
        json={"source_content": SAMPLE_OPENAPI_3_0, "dry_run": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_openapi_preview_401_without_token(client):
    resp = await client.post(
        f"/api/v1/projects/{uuid.uuid4()}/suites/{uuid.uuid4()}/import/openapi",
        json={"source_content": SAMPLE_OPENAPI_3_0, "dry_run": True},
    )
    assert resp.status_code == 401


# ============================================================================
# F013 — batch import (multi-document) tests
#
# Style: extends ``test_openapi_importer.py``. Re-uses the F012 helper
# ``_create_project_and_suite`` and the SAMPLE_OPENAPI_3_0 fixture above.
#
# Cross-reference: ``docs/01-product/F013_SPEC.md`` §9.1 (T1..T13).
# ============================================================================


SAMPLE_OPENAPI_3_0_DOC_B: dict = {
    "openapi": "3.0.0",
    "info": {"title": "B", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com/v2"}],
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List users",
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/users/{id}": {
            "get": {
                "operationId": "getUser",
                "summary": "Get a user",
                "parameters": [
                    {
                        "name": "id", "in": "path", "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
    "components": {"schemas": {}},
}


async def _register_and_get_token(
    client, tag: str, admin_token: str | None = None
) -> str:
    """Register a fresh user and return its access token.

    Username / email carry a uuid suffix so per-test isolation holds.
    The first user in a test session is open-registration (admin_token
    may be None); subsequent users must carry an admin token in the
    Authorization header (matches F012 ``test_openapi_preview_403_*``
    multi-user pattern).
    """
    headers = (
        {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
    )
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"{tag}_{uuid.uuid4().hex[:6]}",
            "email": f"{tag}_{uuid.uuid4().hex[:6]}@e.com",
            "password": "TestPass123!",
            "nickname": tag,
            "phone": "13800000000",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---- T1: preview batch 返回每文档明细，含 preview_id -----------------------


async def test_openapi_batch_preview_returns_per_doc_summaries(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t1")
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={
            "documents": [
                {"source_content": SAMPLE_OPENAPI_3_0},
                {"source_content": SAMPLE_OPENAPI_3_0_DOC_B},
            ],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_documents"] == 2
    assert len(body["documents"]) == 2
    assert body["documents"][0]["spec_version"] == "3.0.0"
    assert body["documents"][0]["new_count"] == 3
    assert body["documents"][1]["new_count"] == 2
    assert isinstance(body["preview_id"], str) and len(body["preview_id"]) > 8


# ---- T2: commit batch 真创建用例 ------------------------------------------


async def test_openapi_batch_commit_creates_cases(client, db_session):
    token = await _register_and_get_token(client, "f013t2")
    project, suite = await _create_project_and_suite(client, token)

    # Step 1: preview to obtain preview_id
    preview = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={
            "documents": [
                {"source_content": SAMPLE_OPENAPI_3_0},
                {"source_content": SAMPLE_OPENAPI_3_0_DOC_B},
            ],
        },
        headers=_auth(token),
    )
    assert preview.status_code == 200
    preview_id = preview.json()["preview_id"]

    # Step 2: commit
    commit = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={
            "batch": "true", "dry_run": "false", "preview_id": preview_id,
        },
        json={"documents": [{"source_content": SAMPLE_OPENAPI_3_0}]},
        headers=_auth(token),
    )
    assert commit.status_code == 200, commit.text
    body = commit.json()
    assert body["total_documents"] == 2
    assert body["total_attempted"] == 5
    assert body["total_succeeded"] == 5
    assert len(body["documents"]) == 2
    # All freshly created (no existing cases yet)
    assert sum(len(d["created"]) for d in body["documents"]) == 5


# ---- T3: batch=true 单文档（?documents=[d]）与单文档端点结果一致 --------


async def test_openapi_batch_single_document_matches_f012(
    client, db_session
):
    token_a = await _register_and_get_token(client, "f013t3a")
    token_b = await _register_and_get_token(client, "f013t3b", admin_token=token_a)
    proj_a, suite_a = await _create_project_and_suite(client, token_a)
    proj_b, suite_b = await _create_project_and_suite(client, token_b)

    # F012 single-doc
    resp_a = await client.post(
        f"/api/v1/projects/{proj_a['id']}/suites/{suite_a['id']}/import/openapi",
        json={"source_content": SAMPLE_OPENAPI_3_0, "dry_run": True},
        headers=_auth(token_a),
    )
    # F013 batch with one document
    resp_b = await client.post(
        f"/api/v1/projects/{proj_b['id']}/suites/{suite_b['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={"documents": [{"source_content": SAMPLE_OPENAPI_3_0}]},
        headers=_auth(token_b),
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    a_total = resp_a.json()["total"]
    b_total = sum(d["total"] for d in resp_b.json()["documents"])
    assert a_total == b_total == 3


# ---- T4: documents=[] → 422 -------------------------------------------------


async def test_openapi_batch_empty_documents_returns_422(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t4")
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={"documents": []},
        headers=_auth(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


# ---- T5: documents 数 > N → 422 --------------------------------------------


async def test_openapi_batch_too_many_documents_returns_422(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t5")
    project, suite = await _create_project_and_suite(client, token)

    # OPENAPI_BATCH_MAX_DOCS = 5 → 6 必须被拒
    docs = [
        {"source_content": SAMPLE_OPENAPI_3_0_DOC_B}
        for _ in range(6)
    ]
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={"documents": docs},
        headers=_auth(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


# ---- T6: 单文档 operation > M → 400 OPENAPI_BATCH_LIMIT_EXCEEDED ----------


async def test_openapi_batch_per_doc_operation_limit_returns_400(
    client, db_session, monkeypatch
):
    # 通过 monkeypatch 把 OPENAPI_BATCH_MAX_OPS_PER_DOC 临时改为 1，
    # 这样 SAMPLE_OPENAPI_3_0 的 3 operations 必定超过上限。
    from app.config import settings
    monkeypatch.setattr(settings, "OPENAPI_BATCH_MAX_OPS_PER_DOC", 1)

    token = await _register_and_get_token(client, "f013t6")
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={"documents": [{"source_content": SAMPLE_OPENAPI_3_0}]},
        headers=_auth(token),
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "OPENAPI_BATCH_LIMIT_EXCEEDED"


# ---- T7: 部分文档失败 + 部分成功隔离 --------------------------------------


async def test_openapi_batch_partial_failure_does_not_abort_siblings(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t7")
    project, suite = await _create_project_and_suite(client, token)

    # doc 0 valid, doc 1 invalid (unsupported version)
    bad_doc = {"openapi": "2.0", "info": {"title": "bad", "version": "0"}}
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={
            "documents": [
                {"source_content": SAMPLE_OPENAPI_3_0},
                {"source_content": bad_doc},
            ],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_documents"] == 2
    # doc 0 succeeded
    assert body["documents"][0]["new_count"] == 3
    assert body["documents"][0]["errors"] == []
    # doc 1 isolated failure
    assert body["documents"][1]["new_count"] == 0
    assert body["documents"][1]["errors"]  # OPENAPI_PARSE_ERROR


# ---- T8: documents[] 与单文档字段同传 → 422（互斥）------------------------


async def test_openapi_batch_documents_mutually_exclusive_with_single(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t8")
    project, suite = await _create_project_and_suite(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={
            "source_url": "https://example.com/spec.json",
            "documents": [
                {"source_content": SAMPLE_OPENAPI_3_0},
            ],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


# ---- T9: batch=true&dry_run=true 不落库 ------------------------------------


async def test_openapi_batch_dry_run_does_not_persist_cases(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t9")
    project, suite = await _create_project_and_suite(client, token)

    # 仅 dry_run，不调 commit
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={
            "documents": [{"source_content": SAMPLE_OPENAPI_3_0}],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200

    # 校验 suite 下零用例
    list_resp = await client.get(
        f"/api/v1/collections/{suite['id']}/cases",
        headers=_auth(token),
    )
    assert list_resp.status_code == 200, list_resp.text
    # F007 endpoint returns a bare list of cases, not an envelope.
    items = list_resp.json()
    assert isinstance(items, list)
    assert items == []


# ---- T10: batch=true&on_conflict=overwrite 重复提交 -----------------------


async def test_openapi_batch_overwrite_replaces_existing_cases(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t10")
    project, suite = await _create_project_and_suite(client, token)

    payload = {
        "documents": [{"source_content": SAMPLE_OPENAPI_3_0}],
    }

    # First import: dry-run + commit (skip)
    pv1 = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json=payload,
        headers=_auth(token),
    )
    assert pv1.status_code == 200
    pid1 = pv1.json()["preview_id"]
    commit1 = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={
            "batch": "true", "dry_run": "false",
            "preview_id": pid1, "on_conflict": "skip",
        },
        json=payload,
        headers=_auth(token),
    )
    assert commit1.status_code == 200

    # Second import: same doc, overwrite
    pv2 = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json=payload,
        headers=_auth(token),
    )
    pid2 = pv2.json()["preview_id"]
    commit2 = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={
            "batch": "true", "dry_run": "false",
            "preview_id": pid2, "on_conflict": "overwrite",
        },
        json=payload,
        headers=_auth(token),
    )
    assert commit2.status_code == 200, commit2.text
    doc0 = commit2.json()["documents"][0]
    # 旧用例被删 + 新用例落库 = overwritten + created
    assert len(doc0["created"]) == 3
    assert len(doc0["overwritten"]) == 3
    assert len(doc0["skipped"]) == 0


# ---- T11: batch=true&on_conflict=skip 重复提交 -----------------------------


async def test_openapi_batch_skip_repeat_leaves_cases_untouched(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t11")
    project, suite = await _create_project_and_suite(client, token)

    payload = {
        "documents": [{"source_content": SAMPLE_OPENAPI_3_0}],
    }

    # First import (skip)
    pv1 = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json=payload, headers=_auth(token),
    )
    pid1 = pv1.json()["preview_id"]
    await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={
            "batch": "true", "dry_run": "false",
            "preview_id": pid1, "on_conflict": "skip",
        },
        json=payload, headers=_auth(token),
    )

    # Second import (skip) → should report all skipped, zero created
    pv2 = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json=payload, headers=_auth(token),
    )
    pid2 = pv2.json()["preview_id"]
    commit2 = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={
            "batch": "true", "dry_run": "false",
            "preview_id": pid2, "on_conflict": "skip",
        },
        json=payload, headers=_auth(token),
    )
    assert commit2.status_code == 200
    doc0 = commit2.json()["documents"][0]
    assert len(doc0["created"]) == 0
    assert len(doc0["skipped"]) == 3
    assert len(doc0["overwritten"]) == 0


# ---- T12: 跨用户调用：非 owner → 403 ---------------------------------------


async def test_openapi_batch_non_owner_forbidden(client, db_session):
    owner_token = await _register_and_get_token(client, "f013t12o")
    other_token = await _register_and_get_token(
        client, "f013t12x", admin_token=owner_token
    )
    project, suite = await _create_project_and_suite(client, owner_token)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites/{suite['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={"documents": [{"source_content": SAMPLE_OPENAPI_3_0}]},
        headers=_auth(other_token),
    )
    assert resp.status_code == 403


# ---- T13: 跨项目调用：suite.project_id != path.project_id → 404 -------------


async def test_openapi_batch_cross_project_returns_404(
    client, db_session
):
    token = await _register_and_get_token(client, "f013t13")
    proj_a, suite_a = await _create_project_and_suite(client, token)
    # 第二个项目下的随机 suite_id
    proj_b, suite_b = await _create_project_and_suite(client, token)
    # 用 proj_a 的 path + proj_b 的 suite_id → 应被 _load_project_suite 拒绝
    resp = await client.post(
        f"/api/v1/projects/{proj_a['id']}/suites/{suite_b['id']}/import/openapi",
        params={"batch": "true", "dry_run": "true"},
        json={"documents": [{"source_content": SAMPLE_OPENAPI_3_0}]},
        headers=_auth(token),
    )
    assert resp.status_code == 404
