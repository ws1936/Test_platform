# F022 实施前 Precheck 建议（3 项）

> 范围：F022 Test Design Engine 开干前的三项规划建议。  
> 目的：在 F022 SPEC 撰写前对齐 ADR / config / test fixture 三个层面的关键决策。  
> 原则：第一性原理 + 奥姆剃刀 + KISS + 沿用 F012/F013/F021 契约 + 不破坏向后兼容。

---

## 1. ADR-009 必要性评估

### 1.1 结论

**需要 ADR-009，但应该挂在 F023 而非 F022**。

### 1.2 分析

| Feature | HTTP 暴露？ | 用户可见错误？ | 是否需要 ADR |
|---|---|---|---|
| F021 Schema Analyzer | ❌ 纯函数 | ❌ 无 | ❌（已用 ADR-008） |
| **F022 Test Design Engine** | ❌ 纯函数 / service | ❌ 无（错误仅 Python 异常） | ❌ |
| **F023 Test Generator** | ✅ `?design=schema` query | ✅ 用户可触发 | ✅ **ADR-009** |

**理由**：
- F022 是**纯内存策略引擎**，输出 `TestIntent` 列表。
- F022 内部错误（如 `StrategyNotEnabledError`）是 Python 异常，由调用方（F023 service）捕获并转译为业务错误码，**不直接面向用户**。
- F023 通过 `?design=schema` 暴露给用户，是**用户可见错误码真正产生的地方**。

### 1.3 ADR-009 应锁定的话题（F023 开工时决议）

| 话题 | 当前草案 | 待 ADR 决议 |
|---|---|---|
| 用户启用被关闭的策略时如何响应 | BACKLOG F022 未提及 | 三选一：(a) 静默 drop intent / (b) 422 VALIDATION_ERROR / (c) 400 + 新业务码 `STRATEGY_NOT_ENABLED` |
| 单 operation 超出 `GENERATOR_MAX_INTENTS_PER_OPERATION` | 422 `GENERATOR_INTENT_LIMIT_EXCEEDED`（BACKLOG F023） | 是否新增整型 code？字符串业务码 vs 整型 code 范式（呼应 F012 "400 + 字符串业务码"） |
| `?design=schema` 启用时是否要求至少 1 个策略开启 | 未提及 | 推荐：必须 ≥ 1，否则 422 |
| `?design=simple` 与 `?design=schema` 互斥语义 | 未提及 | 推荐：`design` 互斥 + 默认 `simple`（F012 行为）；`schema` 模式下忽略 strategy 配置为全部 False → 422 |
| `?batch=true&?design=schema` 组合时跨 operation 配额 | 未提及 | 推荐：与单 op 配额一致；不做跨 op 聚合限制 |

### 1.4 建议执行节奏

```text
本周
  ↓ 写完本文档（F022_PRECHECK.md）作为前置规划
  ↓
第 1 周：F022 SPEC + ADR-009
  - F022_SPEC.md 描述策略引擎 + TestIntent 数据契约
  - ADR-009 锁定 §1.3 表中 5 项决策
  ↓
第 2 周：F022 实施
  - src/app/domain/test_design/strategies/*.py
  - src/tests/test_test_design.py
  ↓
第 3 周：F023 SPEC（基于已稳定的 F022）
  - 此时 ADR-009 决策已就位
  ↓
第 4 周：F023 实施
```

> **反对"先写 ADR-009 再写 F022"的方案**：F022 是纯函数层，不涉及 HTTP，ADR 没必要；强行写 ADR-009 会让"配置项默认值"等纯配置决策与 HTTP 错误码耦合，混淆关注点。

---

## 2. `strategy_*` 配置项默认值与边界

### 2.1 推荐默认值（写进 `app/config.py`）

| 配置项 | 默认 | 取值范围 | 备注 |
|---|---|---|---|
| `strategy_happy_path` | `True` | `bool` | **永远 True**：F012 向后兼容的字节级保证 |
| `strategy_required_field_missing` | `False` | `bool` | 保守默认；用户显式开启 |
| `strategy_enum_coverage` | `False` | `bool` | 同上 |
| `strategy_boundary_min_max` | `False` | `bool` | 同上 |
| `strategy_format_invalid` | `False` | `bool` | 同上 |
| `strategy_auth_missing` | `False` | `bool` | 同上 |
| `generator_max_intents_per_operation` | `20` | `1 ≤ N ≤ 100` | 硬上限；越界返 422 |
| `strategy_required_field_missing_max_per_op` | `5` | `1 ≤ N ≤ 20` | 单 op 内该策略产出数上限 |
| `strategy_enum_coverage_max_per_op` | `10` | `1 ≤ N ≤ 20` | 同上 |
| `strategy_boundary_min_max_max_per_op` | `10` | `1 ≤ N ≤ 20` | 同上 |
| `strategy_format_invalid_max_per_op` | `5` | `1 ≤ N ≤ 20` | 同上 |
| `strategy_auth_missing_max_per_op` | `1` | `1 ≤ N ≤ 1` | 单 op 仅 1 条 auth_missing 用例 |

### 2.2 边界 & 校验规则

#### 规则 1：策略开关默认 False
除 `happy_path` 外全部默认关闭。**默认 F022 行为字节级 = F012**（满足 BACKLOG §5.4 红线"不得破坏 F012/F013 现有契约"）。

#### 规则 2：每个策略配额 ≤ 总配额
启动时校验：`strategy_*_max_per_op ≤ generator_max_intents_per_operation`；否则 `ValueError`（启动失败，避免运行时静默截断）。

#### 规则 3：配额硬上限 = 100
`generator_max_intents_per_operation` 上限 100（API 层 422 拒绝超过）。单 op 100 个用例足以覆盖边界/必填/枚举/格式的极限组合，且不会让 `api_test_case` 表爆量。

#### 规则 4：截断策略 = "前 N 个 + WARNING 日志"
当某策略产出超过该策略配额时，**截断为前 N 个**，WARNING 日志输出 `strategy=<name> truncated=<K> operation=<id>`，**不抛异常**。理由：测试设计是 best-effort，宁少勿错。

#### 规则 5：`happy_path` 永远 1 条
无论配置如何，`happy_path` 策略产出**永远恰好 1 条**（与 F012 一致）；不被配额限制影响。

#### 规则 6：`required_field_missing` 数量受 required 字段数限制
若 `len(required) ≤ N`，产出 `len(required)` 条；否则产出 `N` 条 + WARNING（截断）。

### 2.3 配额举例

假设某 operation 有 8 个 required 字段，2 个 enum 属性（分别 5 / 10 个值），3 个 numeric 字段（带 min/max）：

| 策略 | 默认产出数 | 配额上限 | 实际产出 |
|---|---|---|---|
| happy_path | 1 | 1（不限） | 1 |
| required_field_missing | 8 | 5 | **5**（截断 + WARNING） |
| enum_coverage | 15 | 10 | **10**（截断 + WARNING） |
| boundary_min_max | 18 | 10 | **10**（截断 + WARNING） |
| format_invalid | 0 | 5 | 0 |
| auth_missing | 0（无 security） | 1 | 0 |
| **总计** | | **20** | **26 → 截到 20**（最后一条 WARNING 触发 hard cap） |

> 最终硬上限 `GENERATOR_MAX_INTENTS_PER_OPERATION=20` 是**最后一道关**：所有策略截断后求和若仍 > 20，按策略优先级 `happy_path > required > enum > boundary > format > auth` 取前 20 个。

### 2.4 启动校验伪代码

```python
# app/config.py
def _validate_strategy_caps() -> None:
    per_strategy_caps = [
        settings.strategy_required_field_missing_max_per_op,
        settings.strategy_enum_coverage_max_per_op,
        settings.strategy_boundary_min_max_max_per_op,
        settings.strategy_format_invalid_max_per_op,
        settings.strategy_auth_missing_max_per_op,
    ]
    for cap in per_strategy_caps:
        if cap > settings.generator_max_intents_per_operation:
            raise ValueError(
                f"strategy_*_max_per_op ({cap}) must be <= "
                f"generator_max_intents_per_operation ({settings.generator_max_intents_per_operation})"
            )
```

---

## 3. 测试夹具复用（EndpointSchema builder）

### 3.1 现状痛点

`src/tests/test_schema_analyzer.py` 共 33 个测试，每个测试都手工构造 `SchemaModel` / `EndpointSchema`。F022/F023 落地后，测试数量预估 100+，手工构造将：
- 重复样板代码
- 让测试意图被构造细节淹没
- 难以在多测试间共享"边界用例样本"（如"含 5 个 enum 值的 string 字段"）

### 3.2 建议：新建 `src/tests/openapi_factories.py`

**理由**：
- 项目已有 `src/tests/conftest.py`（`client` / `db_session`），但**不适合放 OpenAPI 工厂**（conftest 是 fixture，不是工厂）
- 新建独立模块 `openapi_factories.py`，与既有 `test_assertion_engine.py` / `test_request_builder.py` 等**领域工厂**模式一致

### 3.3 推荐 API 形状

```python
# src/tests/openapi_factories.py
"""F022/F023 test factories — build SchemaModel / EndpointSchema with minimal boilerplate.

Usage::

    from tests.openapi_factories import (
        make_schema, make_endpoint_schema,
        make_endpoint_with_enum_property, make_endpoint_with_required_fields,
    )

    sm = make_schema(type="string", min_length=2, max_length=32)
    ep = make_endpoint_with_required_fields(["id", "name", "email"])
"""
from typing import Any
from app.domain.openapi_importer.schema_model import (
    EndpointSchema, SchemaModel, RequestSchema,
)


def make_schema(**overrides: Any) -> SchemaModel:
    """Build a SchemaModel with sensible defaults (type=string, format=None)."""
    defaults: dict[str, Any] = {}
    defaults.update(overrides)
    return SchemaModel(**defaults)


def make_object_schema(
    properties: dict[str, dict[str, Any]],
    required: list[str] | None = None,
) -> SchemaModel:
    """Convenience: object schema with nested SchemaModel properties."""
    return SchemaModel(
        type="object",
        properties={
            name: make_schema(**props)
            for name, props in properties.items()
        },
        required=required or [],
    )


def make_endpoint_schema(**overrides: Any) -> EndpointSchema:
    """Build an EndpointSchema with sensible defaults."""
    defaults: dict[str, Any] = {
        "method": "GET",
        "path": "/test",
        "summary": "Test operation",
    }
    defaults.update(overrides)
    return EndpointSchema(**defaults)


# ---- Strategy-specific presets (F022 测试用) -----------------------------

def make_endpoint_with_required_fields(field_names: list[str]) -> EndpointSchema:
    """request_body 含 N 个 required 字段；用于 required_field_missing 策略测试。"""
    props = {name: {"type": "string"} for name in field_names}
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(props, required=field_names),
            required=True,
        ),
    )


def make_endpoint_with_enum_property(
    enum_values: list[Any],
    field_name: str = "status",
) -> EndpointSchema:
    """request_body 含 1 个 enum 属性；用于 enum_coverage 策略测试。"""
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {field_name: {"type": "string", "enum": enum_values}},
                required=[field_name],
            ),
        ),
    )


def make_endpoint_with_numeric_boundary(
    min_val: float | int,
    max_val: float | int,
    field_name: str = "age",
) -> EndpointSchema:
    """request_body 含 1 个 numeric 字段带 min/max；用于 boundary_min_max 策略测试。"""
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {field_name: {"type": "integer", "minimum": min_val, "maximum": max_val}},
                required=[field_name],
            ),
        ),
    )


def make_endpoint_with_email_format() -> EndpointSchema:
    """request_body 含 1 个 format=email 字段；用于 format_invalid 策略测试。"""
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {"email": {"type": "string", "format": "email"}},
                required=["email"],
            ),
        ),
    )


def make_endpoint_with_security(
    scheme_name: str = "bearerAuth",
    scopes: list[str] | None = None,
) -> EndpointSchema:
    """带 security 需求；用于 auth_missing 策略测试。"""
    from app.domain.openapi_importer.schema_model import SecurityRequirement
    return make_endpoint_schema(
        security=[SecurityRequirement(name=scheme_name, scopes=scopes or [])],
    )
```

### 3.4 落地建议

| 步骤 | 范围 | 时机 |
|---|---|---|
| 1 | 新建 `src/tests/openapi_factories.py`（上面 8 个工厂函数） | **F022 SPEC 撰写时同步**（避免测试时手忙脚乱） |
| 2 | F022 测试文件 `test_test_design.py` 全部使用工厂 | F022 实施 PR |
| 3 | （可选）重构 `test_schema_analyzer.py` 使用工厂 | 单独 PR，不阻塞 F022 |
| 4 | F023 测试文件 `test_test_generator.py` 复用同一工厂 | F023 实施 PR |

### 3.5 为什么不放 `conftest.py`？

| 维度 | `conftest.py` | 独立 `openapi_factories.py` |
|---|---|---|
| Fixture 生命周期 | pytest 自动注入 | 显式 import |
| 适合内容 | `client` / `db_session` / `mock_user` | 纯数据构造 |
| 可被生产代码 import | ❌（fixture scope） | ✅（普通模块） |
| 测试间共享 | ✅ 自动 | ✅ 显式 |

→ 数据构造工厂放独立模块更清晰，与 fixture 区分。

---

## 4. 综合建议

按以下顺序推进：

1. **本周**：本文档落地（`docs/01-product/F022_PRECHECK.md`）作为前置规划 ✅
2. **第 1 周（并行）**：
   - F022 SPEC.md 撰写（含 `TestIntent` 数据契约 + 策略接口规范 + 配额截断规则）
   - **新建 `src/tests/openapi_factories.py`**（独立 PR，8 个工厂函数）
3. **第 2 周**：F022 实施
   - `src/app/domain/test_design/__init__.py`
   - `src/app/domain/test_design/strategies/__init__.py`
   - `src/app/domain/test_design/strategies/happy_path.py` / `required_field_missing.py` / `enum_coverage.py` / `boundary_min_max.py` / `format_invalid.py` / `auth_missing.py`
   - `src/app/domain/test_design/engine.py`（策略编排 + 配额截断）
   - `src/app/domain/test_design/schema.py`（TestIntent 数据契约）
   - `src/tests/test_test_design.py`（≥15 个策略用例 + 边界 + 配额）
4. **第 3 周**：F023 SPEC + **ADR-009**（锁定错误码 / 配置项默认值 / `?design=schema` 语义）
5. **第 4 周**：F023 实施

---

## 5. 红线（再次强调）

- ❌ F022 不得引入 LLM / RAG / 第三方 schema 库
- ❌ F022 默认行为必须字节级 = F012（除 `?design=schema` 显式启用外）
- ❌ F022 不得新增业务表 / model.py 改动
- ❌ F022 不得新增整型错误码（HTTP 层错误码是 F023 ADR-009 的事）
- ✅ F022 可新增 `strategy_*` 配置项（`app/config.py`） + Pydantic Schema（`TestIntent`）+ 模块文件
- ✅ 启动时校验 `strategy_*_max_per_op ≤ generator_max_intents_per_operation`

---

## 6. 等待确认

请就以下几点给结论后即可启动 F022 SPEC：

1. ✅ 同意 ADR-009 挂在 F023 而非 F022？
2. ✅ 同意 §2.1 配置项默认值表（含 6 个策略开关 + 7 个配额项）？
3. ✅ 同意 §2.2 规则 1–6（含"截断 + WARNING 不抛错"）？
4. ✅ 同意 §3.3 工厂函数 API 形状（8 个工厂）？
5. ⚠️ `generator_max_intents_per_operation` 上限 **100** 是否合理？（替代默认 20）