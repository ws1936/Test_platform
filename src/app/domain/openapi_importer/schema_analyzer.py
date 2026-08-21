"""F021 SchemaAnalyzer — F012 Operation → EndpointSchema.

See ``docs/01-product/F021_SPEC.md`` §5–§6 for the API surface and
§6 for the $ref / composite-schema normalisation rules.  Locked
decisions live in ``docs/04-rules/ADR.md`` ADR-008.
"""
from __future__ import annotations
import logging
from typing import Any, Optional

from app.domain.openapi_importer.exceptions import OpenApiParseError
from app.domain.openapi_importer.parser import Operation
from app.domain.openapi_importer.schema_model import (
    EndpointSchema,
    ParameterSchema,
    RequestSchema,
    ResponseSchema,
    SchemaModel,
    SecurityRequirement,
)


logger = logging.getLogger(__name__)


_CYCLE_MARKER = "__f021_cycle__"


class SchemaAnalyzer:
    """F021 入口：F012 ``Operation`` → ``EndpointSchema``。"""

    MAX_REF_DEPTH: int = 10  # ADR-008 决策 2

    # ---- 顶层入口 ----------------------------------------------------
    def analyze(
        self,
        operation: Operation,
        components_schemas: Optional[dict[str, Any]] = None,
        security_schemes: Optional[dict[str, Any]] = None,
        global_security: Optional[list[dict[str, list[str]]]] = None,
    ) -> EndpointSchema:
        """Build the deep ``EndpointSchema`` for a single operation."""
        components = components_schemas or {}

        parameters: list[ParameterSchema] = []
        if operation.raw_parameters:
            for raw_param in operation.raw_parameters:
                if isinstance(raw_param, dict):
                    parameters.append(
                        self.analyze_parameter(raw_param, components)
                    )

        request_body: Optional[RequestSchema] = None
        if operation.raw_request_body is not None:
            request_body = self.analyze_request_body(
                operation.raw_request_body, components
            )

        responses: list[ResponseSchema] = []
        if operation.raw_responses:
            for status_code, raw_resp in operation.raw_responses.items():
                if isinstance(raw_resp, dict):
                    responses.append(
                        self.analyze_response(
                            str(status_code), raw_resp, components
                        )
                    )

        op_security: list[SecurityRequirement] = []
        if global_security:
            for req in global_security:
                if isinstance(req, dict):
                    for scheme_name, scopes in req.items():
                        op_security.append(
                            SecurityRequirement(
                                name=str(scheme_name),
                                scopes=list(scopes or []),
                            )
                        )

        return EndpointSchema(
            operation_id=operation.operation_id,
            method=operation.method,
            path=operation.path,
            summary=operation.name,
            description=None,
            tags=list(operation.tags),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=op_security,
        )

    # ---- Schema 递归归一 --------------------------------------------
    def analyze_schema(
        self,
        raw: Any,
        components_schemas: dict[str, Any],
        *,
        depth: int = 0,
        _visited: Optional[set[int]] = None,
    ) -> SchemaModel:
        """Convert any JSON node to a ``SchemaModel``.

        * Non-dict values are returned as an empty ``SchemaModel``.
        * ``$ref`` is fully resolved (recursive) up to ``MAX_REF_DEPTH``.
        * Cycles in the ``$ref`` chain return a ``<cycle>`` placeholder
          without raising (per ADR-008 决策 3 / SPEC §11.1 T9).
        * Composite schemas are normalised per ADR-008 决策 3.
        """
        if _visited is None:
            _visited = set()

        if not isinstance(raw, dict):
            return SchemaModel()

        node_id = id(raw)
        if node_id in _visited:
            return SchemaModel(
                ref="<cycle>",
                description="recursive reference detected",
            )
        _visited.add(node_id)
        try:
            return self._analyze_schema_inner(
                raw, components_schemas, depth, _visited
            )
        finally:
            _visited.discard(node_id)

    def _analyze_schema_inner(
        self,
        raw: dict,
        components: dict,
        depth: int,
        visited: set[int],
    ) -> SchemaModel:
        if depth > self.MAX_REF_DEPTH:
            raise OpenApiParseError(
                "ref depth exceeded",
                details={"reason": "ref_depth", "depth": depth},
            )

        resolved = self._resolve_ref_chain(raw, components, depth)

        # Cycle detected by _resolve_ref_chain (chain revisits same name).
        if isinstance(resolved, dict) and resolved.get(_CYCLE_MARKER):
            return SchemaModel(
                ref="<cycle>",
                description="recursive reference detected",
            )

        branches = resolved.get("oneOf") or resolved.get("anyOf")
        if isinstance(branches, list) and branches:
            return self._unify_composite(resolved, branches, components, visited)

        if isinstance(resolved.get("allOf"), list) and resolved["allOf"]:
            return self._merge_all_of(resolved, components, visited)

        return self._build_schema_model(resolved, components, visited, depth)

    # ---- $ref 处理（完整递归） --------------------------------------
    def _resolve_ref_chain(
        self,
        raw: dict,
        components: dict,
        depth: int,
    ) -> dict:
        """Walk a ``$ref`` chain until we land on a non-ref dict.

        If the chain revisits a name we've already resolved (cycle),
        we return a sentinel dict flagged with ``__f021_cycle__`` so
        the caller can produce a ``<cycle>`` placeholder.  Per
        ADR-008 决策 3, cycles do **not** raise.
        """
        current = raw
        seen_in_chain: set[str] = set()
        while isinstance(current, dict) and "$ref" in current:
            if depth > self.MAX_REF_DEPTH:
                raise OpenApiParseError(
                    "ref depth exceeded",
                    details={"reason": "ref_depth", "depth": depth},
                )
            ref = current["$ref"]
            if not isinstance(ref, str):
                return current
            if not ref.startswith("#/components/schemas/"):
                return current
            name = ref.split("/")[-1]
            if name in seen_in_chain:
                # Cycle: signal back to caller via marker.
                return {_CYCLE_MARKER: True, "ref": name}
            seen_in_chain.add(name)
            target = components.get(name)
            if not isinstance(target, dict):
                return current
            siblings = {k: v for k, v in current.items() if k != "$ref"}
            current = {**target, **siblings}
            depth += 1
        return current

    # ---- oneOf / anyOf 归一（Q4） -----------------------------------
    def _unify_composite(
        self,
        raw: dict,
        branches: list[Any],
        components: dict,
        visited: set[int],
    ) -> SchemaModel:
        first = self.analyze_schema(branches[0], components, _visited=visited)
        unresolved: list[SchemaModel] = []
        for b in branches[1:]:
            unresolved.append(
                self.analyze_schema(b, components, _visited=visited)
            )

        first.unresolved_branches = unresolved
        if "oneOf" in raw:
            first.one_of = unresolved
        elif "anyOf" in raw:
            first.any_of = unresolved
        return first

    # ---- allOf 浅合并（Q5） -----------------------------------------
    def _merge_all_of(
        self,
        raw: dict,
        components: dict,
        visited: set[int],
    ) -> SchemaModel:
        merged = SchemaModel()
        for branch in raw.get("allOf") or []:
            sub = self.analyze_schema(branch, components, _visited=visited)
            if sub.type and merged.type and sub.type != merged.type:
                raise OpenApiParseError(
                    "allOf type conflict",
                    details={
                        "reason": "allof_type_conflict",
                        "existing": merged.type,
                        "incoming": sub.type,
                    },
                )
            if sub.type:
                merged.type = sub.type
            for prop_name, prop_sm in sub.properties.items():
                if prop_name not in merged.properties:
                    merged.properties[prop_name] = prop_sm
            for r in sub.required:
                if r not in merged.required:
                    merged.required.append(r)
            for f in (
                "format", "description", "example", "default", "enum",
                "min_length", "max_length", "pattern",
                "minimum", "maximum", "exclusive_minimum", "exclusive_maximum",
                "multiple_of", "min_items", "max_items", "unique_items",
                "nullable", "items", "additional_properties",
            ):
                v = getattr(sub, f)
                if v is not None and getattr(merged, f) is None:
                    setattr(merged, f, v)
        top_level_keys = {k: v for k, v in raw.items() if k != "allOf"}
        if top_level_keys:
            top_schema = self._build_schema_model(
                top_level_keys, components, visited, depth=0
            )
            merged = self._override(merged, top_schema)
        return merged

    def _override(self, base: SchemaModel, top: SchemaModel) -> SchemaModel:
        """``top`` wins on each non-default field."""
        out = base.model_copy(deep=True)
        for f in (
            "type", "format", "description", "example", "default", "enum",
            "const", "nullable",
            "minimum", "maximum", "exclusive_minimum", "exclusive_maximum",
            "multiple_of",
            "min_length", "max_length", "pattern",
            "min_items", "max_items", "unique_items",
            "items", "additional_properties",
            "ref",
        ):
            v = getattr(top, f)
            if v is not None and v != getattr(SchemaModel(), f):
                setattr(out, f, v)
        if top.properties:
            out.properties = {**out.properties, **top.properties}
        if top.required:
            out.required = top.required
        return out

    # ---- 普通 schema 构建 --------------------------------------------
    def _build_schema_model(
        self,
        raw: dict,
        components: dict,
        visited: set[int],
        depth: int,
    ) -> SchemaModel:
        inferred_type = raw.get("type")
        if inferred_type is None and isinstance(raw.get("properties"), dict):
            inferred_type = "object"
        if inferred_type is None and isinstance(raw.get("items"), dict):
            inferred_type = "array"

        sm = SchemaModel(
            type=inferred_type,
            format=raw.get("format"),
            description=raw.get("description"),
            example=raw.get("example"),
            default=raw.get("default"),
            enum=raw.get("enum"),
            const=raw.get("const"),
            nullable=bool(raw.get("nullable", False)),
            minimum=raw.get("minimum"),
            maximum=raw.get("maximum"),
            exclusive_minimum=raw.get("exclusiveMinimum"),
            exclusive_maximum=raw.get("exclusiveMaximum"),
            multiple_of=raw.get("multipleOf"),
            min_length=raw.get("minLength"),
            max_length=raw.get("maxLength"),
            pattern=raw.get("pattern"),
            min_items=raw.get("minItems"),
            max_items=raw.get("maxItems"),
            unique_items=bool(raw.get("uniqueItems", False)),
            additional_properties=raw.get("additionalProperties"),
        )

        if isinstance(raw.get("items"), dict):
            sm.items = self.analyze_schema(
                raw["items"], components, depth=depth + 1, _visited=visited
            )

        if isinstance(raw.get("properties"), dict):
            for prop_name, prop_raw in raw["properties"].items():
                sm.properties[prop_name] = self.analyze_schema(
                    prop_raw, components, depth=depth + 1, _visited=visited
                )

        if isinstance(raw.get("required"), list):
            sm.required = [
                str(x) for x in raw["required"] if isinstance(x, str)
            ]

        return sm

    # ---- 子节点：Parameter / RequestBody / Response ----------------
    def analyze_parameter(
        self,
        raw: dict,
        components: dict,
    ) -> ParameterSchema:
        schema = self.analyze_schema(raw.get("schema") or {}, components)
        return ParameterSchema(
            name=str(raw.get("name") or ""),
            **{"in": str(raw.get("in") or "query")},
            required=bool(raw.get("required", False)),
            schema=schema,
            description=raw.get("description"),
            example=raw.get("example"),
        )

    def analyze_request_body(
        self,
        raw: dict,
        components: dict,
    ) -> Optional[RequestSchema]:
        if not isinstance(raw, dict):
            return None
        content = raw.get("content") or {}
        if not content:
            return RequestSchema(
                content_type="",
                schema_model=None,
                required=bool(raw.get("required", False)),
            )
        content_type, media = next(iter(content.items()))
        if not isinstance(media, dict):
            return RequestSchema(
                content_type=str(content_type),
                schema_model=None,
                required=bool(raw.get("required", False)),
            )
        schema_raw = media.get("schema") or {}
        schema_model = (
            self.analyze_schema(schema_raw, components) if schema_raw else None
        )
        return RequestSchema(
            content_type=str(content_type),
            schema_model=schema_model,
            required=bool(raw.get("required", False)),
        )

    def analyze_response(
        self,
        status_code: str,
        raw: dict,
        components: dict,
    ) -> ResponseSchema:
        content = raw.get("content") or {}
        if not content:
            return ResponseSchema(
                status_code=status_code,
                content_type="",
                schema_model=None,
            )
        content_type, media = next(iter(content.items()))
        schema_raw = (
            media.get("schema") if isinstance(media, dict) else None
        ) or {}
        schema_model = (
            self.analyze_schema(schema_raw, components) if schema_raw else None
        )
        return ResponseSchema(
            status_code=status_code,
            content_type=str(content_type),
            schema_model=schema_model,
        )


__all__ = ["SchemaAnalyzer"]