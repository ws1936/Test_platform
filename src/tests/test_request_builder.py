"""Unit tests for ``app.domain.test_engine.request_builder`` (F010).

Covers:

* URL joining (trailing slash, missing leading slash, empty inputs).
* Headers merging (env → case overrides).
* Query parameter substitution.
* ``body_type`` dispatch (``none`` / ``json`` / ``form`` / ``raw``).
* Recursive variable substitution for dict / list bodies.
* Timeout pulled from case.
"""

from __future__ import annotations

from typing import Any

from app.domain.environment.model import ApiEnvironment
from app.domain.test_case.model import ApiTestCase
from app.domain.test_engine.request_builder import BuiltRequest, RequestBuilder


# === Test helpers ===========================================================


def _env(
    *,
    base_url: str = "https://api.example.com",
    headers: dict[str, str] | None = None,
    variables: dict[str, Any] | None = None,
) -> ApiEnvironment:
    """Build an ``ApiEnvironment`` with sensible defaults."""
    return ApiEnvironment(
        id="00000000-0000-0000-0000-000000000001",
        project_id="00000000-0000-0000-0000-000000000002",
        name="dev",
        base_url=base_url,
        headers=headers or {},
        variables=variables or {},
        is_default=False,
    )


def _case(
    *,
    method: str = "GET",
    path: str = "/api/users",
    headers: dict[str, str] | None = None,
    query_params: dict[str, Any] | None = None,
    body_type: str = "none",
    body: Any = None,
    timeout_seconds: int = 30,
) -> ApiTestCase:
    return ApiTestCase(
        id="00000000-0000-0000-0000-000000000003",
        project_id="00000000-0000-0000-0000-000000000002",
        name="case",
        method=method,
        path=path,
        headers=headers or {},
        query_params=query_params or {},
        body_type=body_type,
        body=body,
        assertions=None,
        timeout_seconds=timeout_seconds,
        status=1,
        sort_order=0,
    )


# === 1. URL joining =========================================================


def test_url_join_no_trailing_slash():
    """base + path → exactly one '/' between them."""
    built = RequestBuilder.build(_env(base_url="https://api.example.com"), _case())
    assert built.url == "https://api.example.com/api/users"


def test_url_join_with_trailing_slash_on_base():
    """Trailing ``/`` on ``base_url`` is collapsed."""
    built = RequestBuilder.build(
        _env(base_url="https://api.example.com/"), _case()
    )
    assert built.url == "https://api.example.com/api/users"


def test_url_join_multiple_trailing_slashes_collapsed():
    built = RequestBuilder.build(
        _env(base_url="https://api.example.com///"), _case()
    )
    assert built.url == "https://api.example.com/api/users"


def test_url_join_adds_leading_slash_if_missing():
    """Path without leading slash is normalized."""
    built = RequestBuilder.build(
        _env(base_url="https://api.example.com"), _case(path="api/users")
    )
    assert built.url == "https://api.example.com/api/users"


# === 2. Headers merging ===================================================


def test_headers_env_only():
    built = RequestBuilder.build(
        _env(headers={"X-Env": "env-value"}), _case()
    )
    assert built.headers == {"X-Env": "env-value"}


def test_headers_case_only():
    built = RequestBuilder.build(
        _env(), _case(headers={"X-Case": "case-value"})
    )
    assert built.headers == {"X-Case": "case-value"}


def test_headers_case_overrides_env_on_conflict():
    """Same key → case wins."""
    built = RequestBuilder.build(
        _env(headers={"X-Same": "env", "X-Only-Env": "env-only"}),
        _case(headers={"X-Same": "case", "X-Only-Case": "case-only"}),
    )
    assert built.headers == {
        "X-Same": "case",
        "X-Only-Env": "env-only",
        "X-Only-Case": "case-only",
    }


def test_headers_substitute_variables():
    built = RequestBuilder.build(
        _env(headers={"Authorization": "Bearer ${token}"}),
        _case(),
        variables={"token": "abc-123"},
    )
    assert built.headers["Authorization"] == "Bearer abc-123"


# === 3. Query parameters ===================================================


def test_query_params_substitute_variables():
    built = RequestBuilder.build(
        _env(),
        _case(query_params={"limit": 10, "filter": "${category}"}),
        variables={"category": "admin"},
    )
    assert built.params == {"limit": "10", "filter": "admin"}


def test_query_params_empty_when_case_has_none():
    built = RequestBuilder.build(_env(), _case())
    assert built.params == {}


# === 4. Body dispatch ======================================================


def test_body_none_emits_no_kwargs():
    built = RequestBuilder.build(
        _env(), _case(body_type="none", body=None)
    )
    assert built.body_kwargs == {}


def test_body_none_with_value_still_emits_no_kwargs():
    built = RequestBuilder.build(
        _env(), _case(body_type="none", body={"ignored": True})
    )
    assert built.body_kwargs == {}


def test_body_json_serializes_dict():
    built = RequestBuilder.build(
        _env(),
        _case(method="POST", body_type="json", body={"name": "alice"}),
    )
    assert built.body_kwargs == {"json": {"name": "alice"}}
    assert built.method == "POST"


def test_body_json_substitutes_strings_recursively():
    built = RequestBuilder.build(
        _env(),
        _case(
            method="POST",
            body_type="json",
            body={"user": "${name}", "tags": ["a", "${tag}"]},
        ),
        variables={"name": "alice", "tag": "vip"},
    )
    assert built.body_kwargs == {
        "json": {"user": "alice", "tags": ["a", "vip"]},
    }


def test_body_form_serializes_as_form_data():
    built = RequestBuilder.build(
        _env(),
        _case(method="POST", body_type="form", body={"k": "v"}),
    )
    assert built.body_kwargs == {"data": {"k": "v"}}


def test_body_raw_serializes_as_content_string():
    built = RequestBuilder.build(
        _env(),
        _case(method="POST", body_type="raw", body="raw payload"),
    )
    assert built.body_kwargs == {"content": "raw payload"}


def test_body_raw_substitutes_variables():
    built = RequestBuilder.build(
        _env(),
        _case(method="POST", body_type="raw", body="payload-${id}"),
        variables={"id": "42"},
    )
    assert built.body_kwargs == {"content": "payload-42"}


def test_body_unknown_type_falls_back_to_raw():
    """Schema validator already rejects unknown types; defensive fallback."""
    built = RequestBuilder.build(
        _env(),
        _case(method="POST", body_type="unknown", body="x"),
    )
    assert built.body_kwargs == {"content": "x"}


def test_body_non_string_top_level_passes_through_unchanged():
    """Non-string bodies (numbers, bools) for ``json`` pass through."""
    built = RequestBuilder.build(
        _env(),
        _case(method="POST", body_type="json", body={"n": 42, "b": True, "none": None}),
    )
    assert built.body_kwargs == {"json": {"n": 42, "b": True, "none": None}}


# === 5. Timeout + method normalisation ======================================


def test_timeout_uses_case_value():
    built = RequestBuilder.build(_env(), _case(timeout_seconds=60))
    assert built.timeout == 60.0


def test_method_uppercased():
    built = RequestBuilder.build(_env(), _case(method="get"))
    assert built.method == "GET"


def test_post_method_preserved():
    built = RequestBuilder.build(_env(), _case(method="post"))
    assert built.method == "POST"


# === 6. BuiltRequest dataclass ============================================


def test_built_request_defaults():
    """Empty ``BuiltRequest`` carries safe defaults."""
    req = BuiltRequest(method="GET", url="https://x.test/")
    assert req.headers == {}
    assert req.params == {}
    assert req.body_kwargs == {}
    assert req.timeout == 30.0


# === 7. Variables are applied to env headers too ===========================


def test_env_headers_get_variables_substituted():
    """Even when the case has no headers, env headers are substituted."""
    built = RequestBuilder.build(
        _env(headers={"X-Tenant": "${tenant}"}),
        _case(),
        variables={"tenant": "acme"},
    )
    assert built.headers["X-Tenant"] == "acme"