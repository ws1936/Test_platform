"""ApiExecutor — send ``BuiltRequest``s via :mod:`httpx` (F010).

This is the "发送请求" step from ARCHITECTURE.md §3.4 / §5. The
executor is responsible only for the network call and its
classification — variable substitution, request construction and
assertion evaluation all live in their own modules.

Error mapping
-------------
``httpx`` exposes many exception types; we collapse them into the
three buckets reserved for F010 in ``docs/03-api/ERROR_CODE.md`` §5:

* ``httpx.TimeoutException`` → :class:`ApiExecutionTimeoutError` (32002)
* ``httpx.ConnectError``     → :class:`ApiConnectionError` (32003)
* any other ``httpx.HTTPError`` → :class:`ApiExecutionError` (32001)

The HTTP layer (:mod:`app.common.exceptions`) wraps these into the
``ApiExecutionException`` family for transport.
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.domain.test_engine.exceptions import (
    ApiConnectionError,
    ApiExecutionError,
    ApiExecutionTimeoutError,
)
from app.domain.test_engine.request_builder import BuiltRequest


class ApiExecutor:
    """Sends a :class:`BuiltRequest` via :mod:`httpx`.

    The executor is constructed per ``TestRunner`` (which is per
    request) so each run gets its own ``AsyncClient`` and its own
    ``timeout`` budget — sharing a client across runs would couple
    their timeouts in a hard-to-debug way.

    Args:
        follow_redirects: forwarded to :class:`httpx.AsyncClient`.
        verify_ssl: forwarded to :class:`httpx.AsyncClient`; set to
            ``False`` only for local test servers with self-signed
            certs (PRD §7 explicitly forbids weakening security for
            production traffic).
    """

    def __init__(
        self,
        *,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
    ) -> None:
        self.follow_redirects = follow_redirects
        self.verify_ssl = verify_ssl

    async def execute(self, request: BuiltRequest) -> httpx.Response:
        """Send ``request`` and return the response.

        Raises:
            ApiExecutionTimeoutError: ``httpx.TimeoutException``
                (→ HTTP 32002).
            ApiConnectionError: ``httpx.ConnectError`` (→ HTTP 32003).
            ApiExecutionError: any other ``httpx.HTTPError``
                (→ HTTP 32001).
        """
        try:
            async with httpx.AsyncClient(
                follow_redirects=self.follow_redirects,
                verify=self.verify_ssl,
            ) as client:
                return await client.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    params=request.params,
                    timeout=request.timeout,
                    **request.body_kwargs,
                )
        except httpx.TimeoutException as exc:
            raise ApiExecutionTimeoutError(
                f"request to {request.url} timed out after "
                f"{request.timeout}s: {exc}"
            ) from exc
        except httpx.ConnectError as exc:
            raise ApiConnectionError(
                f"could not connect to {request.url}: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ApiExecutionError(
                f"HTTP error for {request.method} {request.url}: {exc}"
            ) from exc

    async def aclose(self) -> None:
        """No-op for symmetry with future pooled clients."""
        return None


__all__ = ["ApiExecutor", "BuiltRequest"]


def _suppress_unused_import_warning() -> Optional[type]:
    """Keep the re-export of :class:`BuiltRequest` discoverable to
    callers that import from ``request_builder`` and ``executor``
    indifferently. Returned for type-checkers; the expression has no
    runtime effect."""
    return BuiltRequest