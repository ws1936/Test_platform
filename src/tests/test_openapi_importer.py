"""Tests for F012 OpenAPI importer (parser unit + HTTP route)."""
from __future__ import annotations
import uuid
import pytest
from app.domain.openapi_importer.exceptions import (
    OpenApiFetchError, OpenApiParseError,
)
from app.domain.openapi_importer.parser import OpenApiSpecParser, ParsedSpec


pytestmark = pytest.mark.asyncio


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
