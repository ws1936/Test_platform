"""RequestBuilder — merge ``ApiEnvironment`` + ``ApiTestCase`` into a built request.

F010's "构造 HTTP 请求" step (ARCHITECTURE.md §3.4 / §5). Pure
function: no I/O, no database, no httpx. The orchestrator hands the
output to :class:`ApiExecutor`.

Pipeline
--------
1. URL  = ``base_url.rstrip('/')`` + ``path`` (``path`` is already
   placeholder-substituted by the caller).
2. Headers = ``env.headers ∪ case.headers`` (case wins on conflict)
   — every value is substituted via F008.
3. Query  = ``case.query_params`` (every value substituted).
4. Body   = ``case.body`` serialized per ``case.body_type`` and
   walked through F008 substitution.
5. Timeout = ``case.timeout_seconds`` (PRD §5.7: 默认超时 30 秒).

Body type mapping (F007 §3.7 + PRD §5.4)
--------------------------------------
* ``"none"`` → no body kwargs
* ``"json"`` → ``httpx.Client.request(json=...)``
* ``"form"`` → ``httpx.Client.request(data=...)``
* ``"raw"``  → ``httpx.Client.request(content=...)`` (string body)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from app.domain.environment.model import ApiEnvironment
from app.domain.test_case.model import ApiTestCase
from app.services.variable_substitutor import substitute


@dataclass
class BuiltRequest:
    """A request ready to send via :class:`ApiExecutor`."""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    # ``body_kwargs`` is unpacked into ``httpx.Client.request(**kwargs)``.
    # Exactly one of "json" / "data" / "content" will be present (or none).
    body_kwargs: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0


class RequestBuilder:
    """Stateless builder — all methods are ``@staticmethod``."""

    @staticmethod
    def build(
        env: ApiEnvironment,
        case: ApiTestCase,
        variables: Optional[Mapping[str, Any]] = None,
    ) -> BuiltRequest:
        """Merge ``env`` + ``case`` + ``variables`` into a :class:`BuiltRequest`.

        The caller is responsible for having substituted ``case.path``
        / ``case.headers`` / ``case.query_params`` / ``case.body`` via
        F008 already — this function only re-substitutes ``env.headers``
        (which lives on the environment record) so a request built
        from scratch can still pick up environment-level placeholders.
        """
        variables = dict(variables or {})

        # 1. URL — base_url + path
        url = _join_url(env.base_url, case.path)

        # 2. Headers — env first, then case overrides (F008 substitute)
        env_headers = dict(env.headers or {})
        case_headers = dict(case.headers or {})
        merged_headers: dict[str, str] = {}
        for key, value in {**env_headers, **case_headers}.items():
            merged_headers[key] = (
                substitute(value, variables) if isinstance(value, str) else str(value)
            )

        # 3. Query — case only (env has no query layer in MVP)
        merged_params: dict[str, str] = {
            key: substitute(str(value), variables)
            for key, value in (case.query_params or {}).items()
        }

        # 4. Body — dispatched by body_type
        body_kwargs = _build_body(case.body_type, case.body, variables)

        # 5. Timeout — PRD default 30s; the column has ``default=30``
        # so callers that omit it still get a sane value
        timeout = float(case.timeout_seconds or 30)

        return BuiltRequest(
            method=case.method.upper(),
            url=url,
            headers=merged_headers,
            params=merged_params,
            body_kwargs=body_kwargs,
            timeout=timeout,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _join_url(base_url: str, path: str) -> str:
    """Join ``base_url`` and ``path`` with exactly one ``/`` between them.

    * Strips a trailing ``/`` from ``base_url`` (env may have one).
    * Forces ``path`` to start with ``/`` (F007's :class:`TestCaseBase`
      already validates this; we defend again here in case the
      fixture-built test cases in tests skip that validator).
    """
    base = (base_url or "").rstrip("/")
    if not path:
        return base or "/"
    if not path.startswith("/"):
        path = "/" + path
    return (base or "") + path


def _build_body(
    body_type: str,
    body: Any,
    variables: Mapping[str, Any],
) -> dict[str, Any]:
    """Translate ``(body_type, body, variables)`` into httpx kwargs."""
    if body is None or body_type == "none":
        return {}

    substituted = _substitute_recursive(body, variables)

    if body_type == "json":
        return {"json": substituted}
    if body_type == "form":
        return {"data": substituted}
    if body_type == "raw":
        # ``raw`` is a free-form string body. F007 allows any value
        # but ``content=`` only accepts bytes / str — coerce.
        return {"content": str(substituted)}

    # Unknown body_type — fall back to ``raw`` rather than fail the
    # entire run (the F007 schema validator already rejects unknown
    # types, so this branch is only hit on schema drift).
    return {"content": str(substituted)}


def _substitute_recursive(value: Any, variables: Mapping[str, Any]) -> Any:
    """Walk a JSON-compatible structure, substituting placeholder strings.

    Numbers / booleans / ``None`` pass through unchanged. Strings are
    run through F008. Lists / tuples / dicts are walked recursively.
    """
    if isinstance(value, str):
        return substitute(value, variables)
    if isinstance(value, list):
        return [_substitute_recursive(v, variables) for v in value]
    if isinstance(value, tuple):
        return tuple(_substitute_recursive(v, variables) for v in value)
    if isinstance(value, dict):
        return {k: _substitute_recursive(v, variables) for k, v in value.items()}
    return value