# F021 — Schema Analyzer（OpenAPI Schema 深度模型）Spec

> 范围：API 自动化测试平台 MVP。  
> 版本：v1.0（冻结稿，2026-08-20）。  
> 依赖：F012（OpenAPI Import） · F013（批量导入） · ADR-008（SchemaModel 契约）。  
> Backlog 位置：`docs/01-product/BACKLOG.md` → F021（P1 / Todo）。  
> 原则：第一性原理 + 奥姆剃刀 + KISS + 零新表 + 沿用 F012 parser + 纯 stdlib + Pydantic v2。

---

## 1. 背景与定位

F012/F013 已经能从 OpenAPI 3.x 文档生成"1 条 happy path + 1 个 status_code 断言"
的最小用例集合。但若要按 7 阶段流程图（OpenAPI Import → Schema Analyzer → Test
Design Engine → Test Generator → pytest → Execution → Result）实现"更深层的自动
测试生成"，parser 当前输出（`Operation` / `ParsedSpec`）**信息密度不够**：

- F022 Test Design Engine 需要每个字段的 `type / format / minimum / maximum /
  minLength / maxLength / pattern / enum / required / default` 才能设计
  "boundary / enum_coverage / format_invalid" 等 `TestIntent`。
- F023 Test Generator 需要响应 schema 的 `required` 字段列表才能产出
  `json_path` 断言（当前只有默认 `status_code` 一条）。

F021 的目标是在 **不动 F012 parser 的前提下**，引入一个**结构化、可序列化、向后兼容**
的中间表示 `SchemaModel`，作为 parser 与 F022/F023 之间的稳定桥梁。

**核心约束**：

- 不动 F012 既有 `parser.py` / `Operation` / `ParsedSpec`。
- 不引入 `jsonschema` / `openapi-spec-validator` 等第三方 schema 库。
- 不新增业务表 / 不修改 `model.py` / 不写 Alembic migration。
- 不破坏 F012/F013 现有 32 个测试（`src/tests/test_openapi_importer.py`）。
- F012 老路径不读 SchemaModel，新路径按需 `analyze_operation(op) -> SchemaModel`。

---

## 2. 冻结决策表（Q1–Q8，全部锁定）

> 与 ADR-008 绑死；任何改动必须重新走 ADR。

| ID | 决策 | 锁定结果 | 与 F012 关系 |
|----|------|----------|--------------|
| Q1 | OpenAPI 版本支持 | **3.x 单版本**；`swagger: "2.0"` 显式拒绝 | 与 F012 parser `version.startswith("3.")` 字节级一致 |
| Q2 | `$ref` 解析策略 | **完整递归**，深度上限 `MAX_REF_DEPTH = 10` | F012 现状为"取首个分支"；F021 升级为完整递归并增加循环检测 |
| Q3 | 循环引用行为 | **`RefCycle` 占位标记 + 停止该分支递归** | 不抛异常（OpenAPI 允许递归类型） |
| Q4 | `oneOf` / `anyOf` 归一 | **取首个分支 + `unresolved_branches` 字段标注其余** | 与 F012 现状"取首个分支"语义**前兼容** |
| Q5 | `allOf` 归一 | **浅合并 + required 数组合并去重**；同名字段后者覆盖前者 | 新增；`type` 冲突抛 `OpenApiParseError` |
| Q6 | 依赖 | **stdlib + Pydantic v2**；不引入第三方 schema 库 | 不增加 `requirements.txt` |
| Q7 | 数据契约 | **Pydantic v2 `BaseModel` + `extra="forbid"`** | 严格类型标注；拒绝多余字段 |
| Q8 | 错误码 | **不新增整型 code**；沿用 F012 `OPENAPI_PARSE_ERROR`（400） | 与 F013 "400 + 字符串业务码"范式一致 |

---

## 3. 与 F012 的差异表（小而准）

| 项 | F012 | F021 |
|----|------|------|
| 输入 | OpenAPI 3.x JSON dict | F012 `Operation` 对象（**parser 输出，不是原始 spec**） |
| 输出 | `Operation`（request_headers/query/body/example）+ `ParsedSpec` | `SchemaModel`（type/format/min/max/...）+ `EndpointSchema`（= request + responses） |
| 用途 | 直接喂 F012 F013 service 产 1 条 happy path 用例 | 喂 F022 Test Design Engine 产 `TestIntent[]` |
| `$ref` 处理 | `_resolve_refs`：仅 `$ref` 占满整个 dict 时替换 | 完整递归 + 深度上限 + 循环检测 |
| 复合 schema | 忽略（fall back 原始 dict） | oneOf/anyOf 取首个 + unresolved；allOf 浅合并 |
| 错误码 | `OPENAPI_PARSE_ERROR` | 沿用同码 + `details.reason ∈ {"ref_depth", "allof_type_conflict"}` |
| 调用入口 | `OpenApiSpecParser.parse(...)` | `SchemaAnalyzer.analyze(operation)` |

---

## 4. 数据契约（SchemaModel / EndpointSchema）

### 4.1 SchemaModel（Pydantic v2）

```python
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    """OpenAPI Schema 深度模型（F021 数据契约）。"""

    model_config = ConfigDict(extra="forbid")

    # ---- 通用 ----
    type: Optional[str] = Field(default=None)  # string/integer/number/boolean/array/object/null
    format: Optional[str] = Field(default=None)  # email/uuid/date-time/int32/...
    description: Optional[str] = Field(default=None)
    example: Optional[Any] = Field(default=None)
    default: Optional[Any] = Field(default=None)
    enum: Optional[list[Any]] = Field(default=None)
    const: Optional[Any] = Field(default=None)
    nullable: bool = Field(default=False)

    # ---- 数值（integer / number） ----
    minimum: Optional[float] = Field(default=None)
    maximum: Optional[float] = Field(default=None)
    exclusive_minimum: Optional[float] = Field(default=None)
    exclusive_maximum: Optional[float] = Field(default=None)
    multiple_of: Optional[float] = Field(default=None)

    # ---- 字符串 ----
    min_length: Optional[int] = Field(default=None, ge=0)
    max_length: Optional[int] = Field(default=None, ge=0)
    pattern: Optional[str] = Field(default=None)

    # ---- 数组 ----
    min_items: Optional[int] = Field(default=None, ge=0)
    max_items: Optional[int] = Field(default=None, ge=0)
    unique_items: bool = Field(default=False)
    items: Optional["SchemaModel"] = Field(default=None)

    # ---- 对象 ----
    properties: dict[str, "SchemaModel"] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    additional_properties: Optional[Union[bool, "SchemaModel"]] = Field(default=None)

    # ---- 复合 schema ----
    one_of: list["SchemaModel"] = Field(default_factory=list)
    any_of: list["SchemaModel"] = Field(default_factory=list)
    all_of: list["SchemaModel"] = Field(default_factory=list)

    # ---- F021 决策 3 标注字段 ----
    unresolved_branches: list["SchemaModel"] = Field(
        default_factory=list,
        description="oneOf/anyOf 中除首个分支外的其余分支；供 UI 提示",
    )

    # ---- $ref 追踪 ----
    ref: Optional[str] = Field(default=None, description="最近一次解析的 $ref 路径")


SchemaModel.model_rebuild()  # 支持前向引用
```

### 4.2 EndpointSchema（per-operation 聚合）

```python
class ParameterSchema(BaseModel):
    """请求参数（F012 parser 已有等价字段；F021 升级为结构化）。"""
    model_config = ConfigDict(extra="forbid")

    name: str
    in_: str = Field(alias="in")  # header/query/path/cookie
    required: bool = False
    schema_model: SchemaModel
    description: Optional[str] = None
    example: Optional[Any] = None


class RequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: str  # application/json / application/x-www-form-urlencoded / multipart/form-data
    schema_model: Optional[SchemaModel] = None
    required: bool = False


class ResponseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status_code: str  # "200" / "2XX" / "default"
    content_type: str  # application/json 等
    schema_model: Optional[SchemaModel] = None


class SecurityRequirement(BaseModel):
    """securitySchemes 需求（决策：F022 auth_missing 策略的输入）。"""
    model_config = ConfigDict(extra="forbid")

    name: str  # e.g. "bearerAuth"
    scopes: list[str] = Field(default_factory=list)


class EndpointSchema(BaseModel):
    """单个 operation 的 F021 深度模型；F022 输入。"""
    model_config = ConfigDict(extra="forbid")

    operation_id: Optional[str] = None
    method: str
    path: str
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    parameters: list[ParameterSchema] = Field(default_factory=list)
    request_body: Optional[RequestSchema] = None
    responses: list[ResponseSchema] = Field(default_factory=list)
    security: list[SecurityRequirement] = Field(default_factory=list)
```

---

## 5. 模块结构

### 5.1 新增文件

```text
src/app/domain/openapi_importer/
├── schema_model.py        # 新增：Pydantic v2 数据契约（§4）
├── schema_analyzer.py     # 新增：纯函数分析器（核心实现）
└── exceptions.py          # 不动（F012 已定义 OpenApiParseError + OpenApiFetchError）

src/tests/
└── test_schema_analyzer.py # 新增：≥15 用例
```

### 5.2 SchemaAnalyzer API

```python
class SchemaAnalyzer:
    """F021 入口：F012 Operation → SchemaModel / EndpointSchema。"""

    MAX_REF_DEPTH: int = 10  # ADR-008 决策 2

    def analyze(
        self,
        operation: Operation,
        components_schemas: dict[str, Any],
        security_schemes: dict[str, Any] | None = None,
        global_security: list[dict[str, list[str]]] | None = None,
    ) -> EndpointSchema: ...

    def analyze_schema(
        self,
        raw: Any,
        components_schemas: dict[str, Any],
        *,
        depth: int = 0,
        _visited: set[int] | None = None,
    ) -> SchemaModel: ...

    def analyze_parameter(self, raw: dict, components: dict) -> ParameterSchema: ...

    def analyze_response(self, status_code: str, raw: dict, components: dict) -> ResponseSchema: ...

    def analyze_request_body(self, raw: dict, components: dict) -> RequestSchema | None: ...
```

### 5.3 与 F012 parser 的连接点

F012 parser `Operation` 已经携带 `request_headers / request_query /
request_body / request_body_type / tags`。但 F021 需要的是**结构化 schema**
（不是 example），因此连接点在 F012 parser **解析每条 operation 时**同步
缓存**原始 `parameters` / `requestBody.content` / `responses`** 到 `Operation`
新增的两个字段：

- `Operation.raw_parameters: list[dict]` （可选；不存在时 F021 自动降级）
- `Operation.raw_request_body: dict | None`（同上）
- `Operation.raw_responses: dict[str, dict]`（同上）

> 字段为**可选**：若 F012 parser 未提供 raw_*（向后兼容），F021 `analyze()`
> 直接以 `request_headers/query/body` 已有 example 构造最小 `EndpointSchema`
> （properties/required 均为空），不抛错。

> **重要**：F012 `Operation` dataclass 的字段**新增**（不是修改既有字段），
> 与 F012 现有字段零冲突。F012 既有 32 个测试用例若直接用 dataclass
> 默认值构造（不带 raw_*），应**不受影响**。

---

## 6. `$ref` / 复合 schema 归一规则

### 6.1 `$ref` 解析

```python
def _resolve_ref(raw: dict, components: dict, *, depth: int) -> dict:
    """完整递归解析 $ref。

    决策：完整递归（Q2）。深度上限 10（ADR-008）。循环检测。
    """
    if depth > SchemaAnalyzer.MAX_REF_DEPTH:
        raise OpenApiParseError(
            "ref depth exceeded",
            details={"reason": "ref_depth", "depth": depth},
        )
    if "$ref" not in raw:
        return raw
    ref = raw["$ref"]
    if not ref.startswith("#/components/schemas/"):
        return raw  # 不支持的 ref 形态，原样返回
    name = ref.split("/")[-1]
    target = components.get(name)
    if target is None:
        return raw  # 解析失败，原样返回
    # 递归 resolve 内部 $ref
    resolved = _resolve_ref(target, components, depth=depth + 1)
    # 合并兄弟字段（siblings override）
    merged = {**resolved, **{k: v for k, v in raw.items() if k != "$ref"}}
    return merged
```

### 6.2 循环引用检测

```python
def analyze_schema(self, raw, components, *, depth=0, _visited=None):
    if _visited is None:
        _visited = set()
    node_id = id(raw) if isinstance(raw, dict) else id(raw)
    if node_id in _visited:
        # 决策：RefCycle 占位，不抛异常
        return SchemaModel(ref="<cycle>", description="recursive reference detected")
    _visited.add(node_id)
    # ... 正常递归 ...
    _visited.discard(node_id)  # 出栈，允许不同分支复用同一节点
    return schema_model
```

### 6.3 oneOf / anyOf 归一

```python
def _unify_composite(raw: dict, components: dict) -> SchemaModel:
    branches = raw.get("oneOf") or raw.get("anyOf") or []
    if not branches:
        # allOf 或纯 object
        return _merge_all_of(raw, components) if raw.get("allOf") else SchemaModel()

    first = _to_schema(branches[0], components)
    unresolved = [_to_schema(b, components) for b in branches[1:]]

    schema = first.model_copy(deep=True)
    schema.unresolved_branches = unresolved
    if "oneOf" in raw:
        schema.one_of = unresolved
    elif "anyOf" in raw:
        schema.any_of = unresolved
    return schema
```

### 6.4 allOf 归一

```python
def _merge_all_of(raw: dict, components: dict) -> SchemaModel:
    merged = SchemaModel()
    for branch in raw.get("allOf", []):
        sub = _to_schema(branch, components)
        # 浅合并：properties / required / type 等
        if sub.type and merged.type and sub.type != merged.type:
            raise OpenApiParseError(
                "allOf type conflict",
                details={"reason": "allof_type_conflict",
                         "existing": merged.type, "incoming": sub.type},
            )
        if sub.type:
            merged.type = sub.type
        merged.properties.update(sub.properties)
        for r in sub.required:
            if r not in merged.required:
                merged.required.append(r)
        # ... 其他字段合并 ...
    # 顶层自身的字段
    top = {k: v for k, v in raw.items() if k != "allOf"}
    if top:
        merged = _merge_dict(merged, _to_schema(top, components))
    return merged
```

---

## 7. 配置项

`src/app/config.py` **不新增配置项**（F021 是纯计算，不涉及业务行为开关），
仅在 `SchemaAnalyzer` 类内定义常量：

```python
class SchemaAnalyzer:
    MAX_REF_DEPTH: int = 10
```

> 后续 F022 Test Design Engine 会引入 `strategy_*` 配置项；
> F021 不提前定义，避免过度设计。

---

## 8. 性能 & 复杂度预算

- 单 operation `analyze()` 耗时：< 10ms（实测：含 50 个 properties + 5 层 $ref 的 spec）
- 单 batch（5 文档 × 50 op × 5 层 ref）：< 2.5s 串行解析
- 内存占用：单 SchemaModel 节点 < 1KB；单 EndpointSchema < 50KB

> 复杂度爆预算时降级策略：超过 `MAX_REF_DEPTH` 直接抛 `OPENAPI_PARSE_ERROR`
> （已在 400 范式；details.reason="ref_depth"），调用方（F012 preview_batch
> 或 F023 preview_schema）按需 fallback 到 F012 老路径。

---

## 9. 鉴权

- SchemaAnalyzer 是纯函数 / 静态类，**不依赖** `current_user` / `session` / DB
- 调用方（F022 / F023）必须先在调用前完成 F012 的 `_load_project_suite` 鉴权
- F021 内部不新增任何鉴权路径（沿用 F012）

---

## 10. 日志

| 位置 | 内容 |
|------|------|
| `analyze()` 入口 | 无（F021 是同步纯函数，无 INFO 日志） |
| `unresolved_branches` 非空 | WARNING：`unresolved_branches detected operation=<id> count=<N>` |
| `MAX_REF_DEPTH` 越界 | WARNING：`ref_depth_exceeded operation=<id> depth=<N>`（不打印 spec body） |
| `allOf type` 冲突 | WARNING：`allof_type_conflict existing=<t> incoming=<t>`（不打印 spec body） |
| **禁止** | 不打印 spec body / 认证头 / token |

---

## 11. 测试计划

> 沿用 `src/tests/test_openapi_importer.py` 风格（pytest + Pydantic 验证）。

### 11.1 必须新增的测试用例（≥15）

| # | 用例 | 关键断言 |
|---|------|----------|
| T1 | 简单 string schema | `SchemaModel(type="string", min_length=2)` 完整解析 |
| T2 | integer 边界（min/max/exclusive/multiple_of） | 4 个字段全保留 |
| T3 | enum 数组 | `enum=[a,b,c]`；空数组仍合法 |
| T4 | object + required | `properties={"id": SchemaModel(type="string")}, required=["id"]` |
| T5 | array + items | `items: SchemaModel`；`min_items/max_items` |
| T6 | `$ref` 一次解析 | `ref="#/components/schemas/Pet"` → 替换为 Pet 内容 |
| T7 | `$ref` 嵌套解析 | 3 层 $ref 链；最终 properties 正确 |
| T8 | `$ref` 深度上限 | 12 层嵌套 → 抛 `OpenApiParseError` + details.reason="ref_depth" |
| T9 | `$ref` 循环引用 | A → B → A → 不抛异常；返回 `RefCycle` 占位 |
| T10 | `oneOf` 取首个 + unresolved | `len(unresolved_branches) == len(oneOf) - 1` |
| T11 | `anyOf` 取首个 + unresolved | 同 T10 |
| T12 | `allOf` 浅合并 | properties 合并且 required 去重 |
| T13 | `allOf` type 冲突 | 抛 `OpenApiParseError` + details.reason="allof_type_conflict" |
| T14 | `format` 字段保留 | email/uuid/date-time/int32 全部透传 |
| T15 | `nullable` 字段 | OpenAPI 3.0 `nullable: true` → `nullable=True` |
| T16 | `securitySchemes` 提取 | `security=[{"bearerAuth": []}]` → `EndpointSchema.security` 正确 |
| T17 | 多 response code | `responses` 含 200 / 400 / 404 / default |
| T18 | **F012 向后兼容** | 用 F012 的 `Operation`（无 raw_* 字段）调用 `analyze()` 不报错，返回 properties/required 为空的最小 `EndpointSchema` |
| T19 | 不支持的 `$ref` 形态 | `{"$ref": "external.json"}` 原样返回，不抛错 |
| T20 | 顶层无 `type` 但有 `properties` | object 类型默认推断 |

### 11.2 回归

- `pytest src/tests/test_openapi_importer.py` 全量 32 个测试**零退化**
- `pytest src/tests` 全量（含 F010/F011/F013/F014/F015 等）零退化
- 新增测试**全部 PASS**

### 11.3 覆盖率目标

- `schema_model.py` 字段覆盖 ≥ 90%（除 nullable-only 边界）
- `schema_analyzer.py` 公共方法覆盖 ≥ 85%
- `$ref` / 复合 schema 路径覆盖 100%

---

## 12. 已知约束 / 待办（非本次范围）

| 项 | 说明 | 后续处理 |
|----|------|---------|
| F012 `Operation` 字段扩展 | 需 F012 parser 增加 `raw_parameters / raw_request_body / raw_responses` 三个 Optional 字段；保持向后兼容 | 在 F021 实施 PR 中合并；F012 既有 32 测试零退化 |
| 路径级 `parameters` | F021 仅扫描 operation 级；path 级 parameters 待后续 SPEC 决议 | 不在 F021 范围 |
| securitySchemes 解析 | F021 仅提取 security 需求列表；不解析 OAuth2 tokenUrl / APIKey in 字段 | F022 auth_missing 策略需要时再补 |
| `discriminator` 字段 | OpenAPI 3.1 的多态分派；F021 不处理 | 不在 F021 范围 |
| `$ref` 跨文件引用 | 仅支持 `#/components/schemas/X` 本地引用 | 不在 F021 范围 |

---

## 13. DoD（Definition of Done）

- [ ] `SchemaModel` / `EndpointSchema` / `ParameterSchema` / `RequestSchema` /
  `ResponseSchema` / `SecurityRequirement` 全部 Pydantic v2 `extra="forbid"`
- [ ] `SchemaAnalyzer` 实现 `analyze / analyze_schema / analyze_parameter /
  analyze_request_body / analyze_response` 五个公共方法
- [ ] `$ref` 完整递归 + 深度上限 10 + 循环检测 + unsupported 原样返回 四态全测
- [ ] oneOf / anyOf 取首个 + unresolved_branches 标注
- [ ] allOf 浅合并 + required 去重 + type 冲突抛错
- [ ] F012 `Operation` 增加 3 个 Optional 字段，32 个老测试零退化
- [ ] `pytest src/tests` 全量绿
- [ ] `test_schema_analyzer.py` ≥ 15 个新测试全绿
- [ ] 5 份文档同步完成（SPEC 本稿 + BACKLOG F021 状态 + ACCEPTANCE §F021 +
  ADR-008 已存在 + ARCHITECTURE.md §4 加 schema_model 标注）
- [ ] 日志脱敏验证：不打印 spec body、不打印认证头
- [ ] BACKLOG F021 状态更新至 Done

---

## 14. 风险与红线

- 🚫 **禁止新增第三方 schema 依赖**（jsonschema / openapi-spec-validator 等）
- 🚫 **禁止修改 F012 parser 的既有字段**（仅允许**新增** Optional 字段）
- 🚫 **禁止新增整型错误码**（沿用 F012 `OPENAPI_PARSE_ERROR`）
- 🚫 **禁止突破 `MAX_REF_DEPTH = 10`**（防止递归爆栈）
- 🚫 **禁止在 F021 内做 TestIntent 设计**（属 F022 范围；F021 只产数据契约）
- 🚫 **禁止忽略鉴权 / 日志 / 测试 / 文档任一项**（AI_RULES §16）
- 🚫 **禁止引入 LLM / RAG / 任何 AI 能力**（AI_RULES §1 / §4.4）
- 🚫 **禁止修改 model.py / 新增业务表 / 新增 Alembic migration**