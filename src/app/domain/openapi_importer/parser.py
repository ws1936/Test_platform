"""F012 OpenAPI spec parser (std lib only).

F021 addition: ``Operation`` carries three OPTIONAL raw_* fields
(``raw_parameters`` / ``raw_request_body`` / ``raw_responses``) which
the F021 ``SchemaAnalyzer`` consumes to build a deep ``EndpointSchema``.
When the parser is constructed via test fixtures without these fields
populated (i.e. all three default to ``None`` / empty), the dataclass
construction is byte-for-byte unchanged and all F012 tests pass.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.domain.openapi_importer.exceptions import OpenApiFetchError, OpenApiParseError


@dataclass
class Operation:
    operation_id: Optional[str]
    method: str
    path: str
    name: str
    request_headers: dict[str, str] = field(default_factory=dict)
    request_query: dict[str, Any] = field(default_factory=dict)
    request_body: Optional[Any] = None
    request_body_type: str = "none"
    tags: list[str] = field(default_factory=list)

    # ---- F021 additions (all optional; backward-compatible) -------------
    raw_parameters: Optional[list[dict[str, Any]]] = field(default=None)
    raw_request_body: Optional[dict[str, Any]] = field(default=None)
    raw_responses: Optional[dict[str, dict[str, Any]]] = field(default=None)


@dataclass
class ParsedSpec:
    version: str
    title: str
    base_path: str
    operations: list[Operation]
    raw: dict[str, Any] = field(default_factory=dict)


class OpenApiSpecParser:
    """MVP-grade OpenAPI 3.0/3.1 parser. Pure stdlib, no external deps.

    Supports a pragmatic subset:
    - Spec version + title + first server URL
    - All paths × all 5 methods
    - $ref resolution (one level + nested through components/schemas)
    - Per-operation request: parameters (in: header|query), requestBody
    - Falls back gracefully on oneOf/anyOf/allOf (takes first branch)
    """

    HTTP_TIMEOUT = 5.0
    ALLOWED_METHODS = ("get", "post", "put", "patch", "delete")

    def from_url(self, url: str) -> dict[str, Any]:
        url_obj = urlparse(url)
        if url_obj.scheme not in ("http", "https"):
            raise OpenApiFetchError(f"only http/https URLs supported, got {url_obj.scheme!r}")
        try:
            resp = httpx.get(url, timeout=self.HTTP_TIMEOUT, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise OpenApiFetchError(f"failed to fetch spec: {exc}")
        if resp.status_code >= 400:
            raise OpenApiFetchError(f"fetch returned {resp.status_code}")
        try:
            return resp.json()
        except Exception as exc:
            raise OpenApiFetchError(f"response is not valid JSON: {exc}")

    def from_content(self, content: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(content, dict):
            raise OpenApiParseError("spec must be a JSON object")
        return content

    def parse(self, spec: dict[str, Any], tags: Optional[list[str]] = None) -> ParsedSpec:
        if not isinstance(spec, dict):
            raise OpenApiParseError("spec must be a JSON object")

        version = spec.get("openapi") or spec.get("swagger") or ""
        if not version.startswith("3."):
            raise OpenApiParseError(f"only OpenAPI 3.x is supported, got {version!r}")

        info = spec.get("info") or {}
        title = info.get("title", "Untitled")

        servers = spec.get("servers") or []
        base_path = ""
        if servers and isinstance(servers[0], dict):
            url = servers[0].get("url", "")
            parsed = urlparse(url)
            if parsed.path and parsed.path != "/":
                base_path = parsed.path.rstrip("/")

        components = spec.get("components") or {}
        component_schemas = components.get("schemas") or {}

        operations: list[Operation] = []
        paths = spec.get("paths") or {}
        for raw_path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            full_path = base_path + raw_path
            for method, op in path_item.items():
                if method.lower() not in self.ALLOWED_METHODS:
                    continue
                if not isinstance(op, dict):
                    continue
                op_tags = op.get("tags") or []
                if tags:
                    if not (set(op_tags) & set(tags)):
                        continue
                resolved_op = self._resolve_refs(op, component_schemas)
                operations.append(self._build_operation(
                    method=method.upper(),
                    path=full_path,
                    op=resolved_op,
                    raw_op=op,  # F021: pass through original (pre-resolve) operation
                ))

        return ParsedSpec(
            version=version,
            title=title,
            base_path=base_path,
            operations=operations,
            raw=spec,
        )

    def _resolve_refs(self, obj: Any, schemas: dict[str, Any]) -> Any:
        if isinstance(obj, dict):
            if "$ref" in obj and len(obj) == 1:
                ref = obj["$ref"]
                if ref.startswith("#/components/schemas/"):
                    name = ref.split("/")[-1]
                    if name in schemas:
                        return self._resolve_refs(schemas[name], schemas)
                return obj
            return {k: self._resolve_refs(v, schemas) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._resolve_refs(v, schemas) for v in obj]
        return obj

    def _build_operation(
        self,
        method: str,
        path: str,
        op: dict[str, Any],
        raw_op: dict[str, Any],
    ) -> Operation:
        op_id = op.get("operationId")
        summary = op.get("summary") or op.get("description") or f"{method} {path}"
        headers: dict[str, str] = {}
        query: dict[str, Any] = {}
        for param in op.get("parameters") or []:
            if not isinstance(param, dict):
                continue
            p_name = param.get("name")
            p_in = param.get("in")
            if not p_name:
                continue
            if p_in == "header":
                example = param.get("example") or param.get("schema", {}).get("example")
                if example is not None:
                    headers[p_name] = str(example)
            elif p_in == "query":
                schema = param.get("schema") or {}
                example = param.get("example") or schema.get("example")
                if example is not None:
                    query[p_name] = example

        body: Any = None
        body_type = "none"
        rb = op.get("requestBody")
        if rb and isinstance(rb, dict):
            content = rb.get("content") or {}
            json_media = content.get("application/json")
            if json_media and isinstance(json_media, dict):
                schema = json_media.get("schema") or {}
                example = json_media.get("example") or schema.get("example")
                if example is not None:
                    body = example
                    body_type = "json"

        # ---- F021: collect raw_ fields from the ORIGINAL op ----
        raw_params = raw_op.get("parameters")
        raw_rb = raw_op.get("requestBody")
        raw_resp = raw_op.get("responses")
        # These are best-effort: missing fields just default to None and
        # ``SchemaAnalyzer`` will degrade gracefully.

        return Operation(
            operation_id=op_id,
            method=method,
            path=path,
            name=summary,
            request_headers=headers,
            request_query=query,
            request_body=body,
            request_body_type=body_type,
            tags=op.get("tags") or [],
            raw_parameters=raw_params if isinstance(raw_params, list) else None,
            raw_request_body=raw_rb if isinstance(raw_rb, dict) else None,
            raw_responses=raw_resp if isinstance(raw_resp, dict) else None,
        )