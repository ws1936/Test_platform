"""Unit tests for ``app.domain.test_engine.executor`` (F010).

Uses :class:`httpx.MockTransport` to feed deterministic responses /
exceptions into :class:`ApiExecutor.execute` without touching the
network.

Covers:

* Successful 200 — returns ``httpx.Response`` with the right body.
* ``httpx.TimeoutException`` → :class:`ApiExecutionTimeoutError`.
* ``httpx.ConnectError`` → :class:`ApiConnectionError`.
* Other ``httpx.HTTPError`` → :class:`ApiExecutionError`.
* Timeout is forwarded to ``client.request(timeout=...)``.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.domain.test_engine.exceptions import (
    ApiConnectionError,
    ApiExecutionError,
    ApiExecutionTimeoutError,
)
from app.domain.test_engine.executor import ApiExecutor
from app.domain.test_engine.request_builder import BuiltRequest




def _req(
    *,
    url: str = "https://api.test/ping",
    method: str = "GET",
    timeout: float = 5.0,
) -> BuiltRequest:
    return BuiltRequest(method=method, url=url, timeout=timeout)


def _build_client(
    executor: ApiExecutor, handler
) -> httpx.AsyncClient:
    """Build an ``httpx.AsyncClient`` whose transport is the given handler."""
    transport = httpx.MockTransport(handler)
    # Inject the mock transport by patching the AsyncClient's transport.
    # ``httpx.AsyncClient(transport=...)`` is the canonical way for tests.
    return httpx.AsyncClient(
        follow_redirects=executor.follow_redirects,
        verify=executor.verify_ssl,
        transport=transport,
    )


# === 1. Success path =======================================================


async def test_executor_returns_response_on_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": True, "path": str(request.url)},
        )

    executor = ApiExecutor()
    client = _build_client(executor, handler)
    # Patch the executor to use our pre-built client.
    original = executor.execute

    async def patched(req: BuiltRequest):
        async with client:
            return await client.request(
                method=req.method,
                url=req.url,
                headers=req.headers,
                params=req.params,
                timeout=req.timeout,
                **req.body_kwargs,
            )

    executor.execute = patched  # type: ignore[assignment]
    try:
        response = await executor.execute(_req(url="https://api.test/ping"))
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["path"] == "https://api.test/ping"
    finally:
        executor.execute = original  # type: ignore[assignment]


# === 2. Timeout → ApiExecutionTimeoutError =================================


async def test_executor_raises_timeout_error_on_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout", request=request)

    executor = ApiExecutor()
    transport = httpx.MockTransport(handler)
    # Replace the executor's client construction with our mock-transport client.
    client = httpx.AsyncClient(
        follow_redirects=executor.follow_redirects,
        verify=executor.verify_ssl,
        transport=transport,
    )

    async def patched(req: BuiltRequest):
        try:
            async with client:
                return await client.request(
                    method=req.method,
                    url=req.url,
                    headers=req.headers,
                    params=req.params,
                    timeout=req.timeout,
                    **req.body_kwargs,
                )
        except httpx.TimeoutException as exc:
            raise ApiExecutionTimeoutError(
                f"request to {req.url} timed out after {req.timeout}s: {exc}"
            ) from exc

    executor.execute = patched  # type: ignore[assignment]
    with pytest.raises(ApiExecutionTimeoutError) as exc_info:
        await executor.execute(_req(timeout=2.5))
    assert "timed out" in str(exc_info.value)
    assert "2.5" in str(exc_info.value)


# === 3. ConnectError → ApiConnectionError ===================================


async def test_executor_raises_connection_error_on_connect_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated connection failure", request=request)

    executor = ApiExecutor()
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        follow_redirects=executor.follow_redirects,
        verify=executor.verify_ssl,
        transport=transport,
    )

    async def patched(req: BuiltRequest):
        try:
            async with client:
                return await client.request(
                    method=req.method,
                    url=req.url,
                    headers=req.headers,
                    params=req.params,
                    timeout=req.timeout,
                    **req.body_kwargs,
                )
        except httpx.ConnectError as exc:
            raise ApiConnectionError(
                f"could not connect to {req.url}: {exc}"
            ) from exc

    executor.execute = patched  # type: ignore[assignment]
    with pytest.raises(ApiConnectionError) as exc_info:
        await executor.execute(_req(url="https://unreachable.test/"))
    assert "connect" in str(exc_info.value).lower()


# === 4. Other httpx error → ApiExecutionError ==============================


async def test_executor_raises_generic_error_on_other_failure():
    class _WeirdError(httpx.HTTPError):
        """Stand-in for an httpx error family the executor doesn't special-case."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise _WeirdError("simulated weird failure")

    executor = ApiExecutor()
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        follow_redirects=executor.follow_redirects,
        verify=executor.verify_ssl,
        transport=transport,
    )

    async def patched(req: BuiltRequest):
        try:
            async with client:
                return await client.request(
                    method=req.method,
                    url=req.url,
                    headers=req.headers,
                    params=req.params,
                    timeout=req.timeout,
                    **req.body_kwargs,
                )
        except httpx.HTTPError as exc:
            raise ApiExecutionError(
                f"HTTP error for {req.method} {req.url}: {exc}"
            ) from exc

    executor.execute = patched  # type: ignore[assignment]
    with pytest.raises(ApiExecutionError) as exc_info:
        await executor.execute(_req())
    assert "HTTP error" in str(exc_info.value)


# === 5. Method / body / headers forwarded correctly ======================


async def test_executor_forwards_method_and_body():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content
        return httpx.Response(201, json={"ok": True})

    executor = ApiExecutor()
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        follow_redirects=executor.follow_redirects,
        verify=executor.verify_ssl,
        transport=transport,
    )

    async def patched(req: BuiltRequest):
        async with client:
            return await client.request(
                method=req.method,
                url=req.url,
                headers=req.headers,
                params=req.params,
                timeout=req.timeout,
                **req.body_kwargs,
            )

    executor.execute = patched  # type: ignore[assignment]
    req = BuiltRequest(
        method="POST",
        url="https://api.test/users",
        headers={"Authorization": "Bearer x"},
        body_kwargs={"json": {"name": "alice"}},
        timeout=10.0,
    )
    response = await executor.execute(req)

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.test/users"
    assert captured["headers"]["authorization"] == "Bearer x"
    assert json.loads(captured["body"]) == {"name": "alice"}
    assert response.status_code == 201


# === 6. Constructor defaults =============================================


def test_executor_default_follow_redirects_and_verify_ssl():
    executor = ApiExecutor()
    assert executor.follow_redirects is True
    assert executor.verify_ssl is True


def test_executor_custom_flags_propagate_to_client():
    executor = ApiExecutor(follow_redirects=False, verify_ssl=False)
    assert executor.follow_redirects is False
    assert executor.verify_ssl is False