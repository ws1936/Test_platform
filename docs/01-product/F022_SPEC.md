# F022 — Test Design Engine（策略化用例设计）Spec

> 范围：API 自动化测试平台 MVP。  
> 版本：v1.0（冻结稿，2026-08-20）。  
> 依赖：F012（OpenAPI Import） · F013（批量导入） · F021（Schema Analyzer / EndpointSchema） · `docs/01-product/F022_PRECHECK.md`（前置规划）。  
> Backlog 位置：`docs/01-product/BACKLOG.md` → F022（P1 / Todo）。  
> 原则：第一性原理 + 奥姆剃刀 + KISS + 零新表 + 沿用 F021 SchemaModel + 纯 stdlib + Pydantic v2 + 规则化（不引入 AI）。

---

## 1. 背景与定位

F012/F013 已经能从 OpenAPI 3.x 文档生成"1 条 happy path + 1 个 status_code 断言"的最小用例集合。F021 引入了 `EndpointSchema` 作为结构化中间表示。

F022 在两者之上架设**策略化用例设计引擎**：给定一个 `EndpointSchema`，根据用户配置的策略集合，产出 0..N 条**声明式用例意图**（`TestIntent`）。

- F022 **不**生成 `TestCaseCreateRequest`（属 F023 Test Generator 范围）
- F022 **不**做 HTTP 执行（属 F010 TestRunner 范围）
- F022 **不**新增数据库表（沿用 F007 TestCase）

F022 是**纯内存规则化引擎**，输出 `TestIntent[]`，由 F023 消费后转成具体用例落库。

**核心约束**：

- 不动 F012/F013/F021 既有契约
- 默认行为字节级 = F012（除用户显式开启策略外）
- 纯 stdlib + Pydantic v2，零新依赖
- 零新业务表 / 零 model.py 改动
- 零新错误码（HTTP 层错误码属 F023 ADR-009 范围）

---

## 2. 冻结决策表（Q1–Q12，全部锁定）

> 与 F022_PRECHECK.md §1.3 / §2.1 / §2.2 绑死；任何改动必须重新走 Backlog + ADR。

| ID | 决策 | 锁定结果 | 备注 |
|----|------|----------|------|
| Q1 | 输入契约 | **`EndpointSchema`**（F021 输出） | 单一入口；不接受原始 dict |
| Q2 | 输出契约 | **`TestIntent[]`**（Pydantic v2 `extra="forbid"`） | 声明式，**不含** TestCase 字段 |
| Q3 | 策略集合 | `happy_path` / `required_field_missing` / `enum_coverage` / `boundary_min_max` / `format_invalid` / `auth_missing` | 6 个；可独立开关 |
| Q4 | 默认开关 | `happy_path=True` 其余 `False` | 默认 F022 行为字节级 = F012 |
| Q5 | 单 op 硬上限 | `generator_max_intents_per_operation=20`（范围 1–100） | 启动校验；API 层 422 在 F023 实施 |
| Q6 | 单策略配额 | `strategy_*_max_per_op`（5/10/10/5/1） | ≤ `generator_max_intents_per_operation` |
| Q7 | 截断行为 | **前 N 个 + WARNING 日志，不抛错** | best-effort；与 F021 日志脱敏一致 |
| Q8 | `happy_path` 配额 | 永远 1 条，不被策略配额影响 | F012 向后兼容字节级保证 |
| Q9 | 策略优先级 | `happy_path > required > enum > boundary > format > auth` | 硬截时按此序取前 N 个 |
| Q10 | 错误处理 | F022 内部抛 Python 异常（`StrategyError` 等），由 F023 转译为业务码 | **F022 不新增业务错误码** |
| Q11 | 依赖 | stdlib + Pydantic v2（已是项目栈） | 不引入新第三方库 |
| Q12 | 测试夹具 | 复用 `src/tests/openapi_factories.py`（F022 同步创建） | 与 F022_PRECHECK §3 锁定一致 |

---

## 3. 与 F012 / F013 / F021 的差异表

| 项 | F012/F013 | F021 | F022 |
|----|-----------|------|------|
| 输入 | OpenAPI 3.x JSON dict | F012 `Operation` | F021 `EndpointSchema` |
| 输出 | `Operation` + 1 条 happy path 用例 | `SchemaModel` / `EndpointSchema` | `TestIntent[]` |
| 主要职责 | 解析 spec | 归一 schema | 设计用例意图 |
| HTTP 暴露 | ✅ | ❌ | ❌ |
| 默认产物数 | 1（每 operation） | 1（每 schema 节点） | 1..N（每 operation；可配） |
| 错误码 | 400 + 字符串业务码 | 沿用 F012 同码 | ❌ 不新增 |
| 配置项 | F012/F013 各 1 个 (`OPENAPI_BATCH_MAX_*`) | 0 个 | 13 个 (`strategy_*` + `generator_*`) |

---

## 4. 数据契约（TestIntent）

### 4.1 TestIntent（Pydantic v2）

```python
from typing import Any, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


class TestIntent(BaseModel):
    """F022 输出：单条声明式用例意图。

    F023 消费 TestIntent → TestCaseCreateRequest。
    F022 不落库；F023 才落 api_test_case 表。
    """

    model_config = ConfigDict(extra="forbid")

    # ---- 标识 ----
    intent_id: str = Field(description="uuid4().hex；F022 内唯一")
    strategy: Literal[
        "happy_path",
        "required_field_missing",
        "enum_coverage",
        "boundary_min_max",
        "format_invalid",
        "auth_missing",
    ]
    operation_id: str  # 来自 EndpointSchema.method + path 的稳定 hash
    method: str
    path: str

    # ---- 用例字段（声明式；F023 据此生成 TestCaseCreateRequest）----
    name: str = Field(max_length=200)
    description: Optional[str] = None

    # 请求覆盖（相对 happy_path 的增量；None 表示沿用 happy_path）
    headers_override: Optional[dict[str, str]] = None
    query_override: Optional[dict[str, Any]] = None
    body_override: Optional[Any] = None
    body_type_override: Optional[Literal["none", "json", "form", "raw"]] = None

    # ---- 断言（声明式；F023 据此生成 AssertionRule 列表）----
    assertions: list[dict[str, Any]] = Field(default_factory=list)

    # ---- 期望响应（status_code 期望 + 期望 body 字段）----
    expected_status_codes: list[int] = Field(default_factory=list)
    expected_status_mode: Literal["any_of", "not_in"] = "any_of"
```

### 4.2 OperationKey（用于去重 / 配额键）

```python
class OperationKey:
    """单 operation 的稳定标识，用于配额与排序。

    F022 不引入新数据类；用 (method, path) tuple 替代。
    """
```

---

## 5. 策略接口规范

### 5.1 抽象基类（基线实现可放在 `engine.py`）

```python
from typing import Protocol


class Strategy(Protocol):
    """F022 策略协议。

    每个策略实现 4 个属性 + 1 个方法：
    - name: 策略标识（与配置 strategy_<name> 对应）
    - default_enabled: 启动默认开关
    - max_per_op: 单 op 产出配额（来自配置）
    - generate(endpoint): 产 TestIntent 列表
    """

    name: str
    default_enabled: bool
    max_per_op: int

    def generate(self, endpoint: EndpointSchema) -> list[TestIntent]: ...
```

### 5.2 六个策略实现规范

#### 5.2.1 `happy_path`（永远 enabled，产出永远 1 条）

- **输入**：`EndpointSchema`
- **产出**：1 条 TestIntent，`expected_status_codes=[200, 201, 202, 204]`
- **body**：沿用 schema 的 `example` 字段（与 F012 parser 兼容）
- **assertions**：`[{"type": "status_code", "operator": "in", "expected": [200, 201, 202, 204]}]`
- **name**：`f"{summary or method_path}: happy path"[:200]`
- **不受任何配额限制**

#### 5.2.2 `required_field_missing`

- **输入**：`EndpointSchema.request_body.schema_model.properties` 中 `required` 列表
- **产出**：N 条 TestIntent（N = `min(len(required), strategy_required_field_missing_max_per_op)`）
- **每条**：
  - `body_override`：深拷贝 happy_path body，将 1 个 required 字段移除/置 None
  - `expected_status_codes=[400, 422]`
  - `assertions=[{"type": "status_code", "operator": "in", "expected": [400, 422]}]`
  - `name=f"{base_name}: missing required field '<field_name>'"[:200]`
- **截断**：超过配额时取前 N 个 + WARNING
- **空 required**：不产出

#### 5.2.3 `enum_coverage`

- **输入**：扫描 `properties` 中每个 `enum: list[Any]` 字段
- **产出**：每个 enum 字段产出 `min(len(enum), strategy_enum_coverage_max_per_op)` 条
- **每条**：固定其它字段，**逐个** 替换 enum 字段为该 enum 中的一个值
- **expected_status_codes**：`[200, 201]`（happy path 期望）
- **name**：`f"{base_name}: enum '{field_name}' = '<value>'"[:200]`
- **截断**：超过该策略配额时取前 N 个 + WARNING

#### 5.2.4 `boundary_min_max`

- **输入**：扫描 numeric 类型（integer / number）字段 + 带 `minimum/maximum` 的字段
- **产出**：每字段产出 6 条候选（`min-1 / min / min+1 / max-1 / max / max+1`），按 `strategy_boundary_min_max_max_per_op` 配额截断
- **每条**：body 仅该字段值变化；期望 200 或 400（越界值期望 400）
- **name**：`f"{base_name}: boundary {field_name}={value}"[:200]`

#### 5.2.5 `format_invalid`

- **输入**：扫描 `format ∈ {"email", "uuid", "date-time", "uri", "ipv4", "ipv6"}` 的 string 字段
- **产出**：每字段产出 1 条 TestIntent（`format_invalid` 配额按字段数限制）
- **每条**：body 该字段填 `"not-a-valid-{format}"` 之类的明显非法值；期望 400/422
- **name**：`f"{base_name}: invalid format on {field_name}"[:200]`

#### 5.2.6 `auth_missing`

- **输入**：`EndpointSchema.security` 非空时启用
- **产出**：1 条 TestIntent
- **每条**：从 headers 中**移除**所有匹配 security scheme 名的 header（最简：直接置 `Authorization=None`），期望 401
- **name**：`f"{base_name}: missing auth"[:200]`
- **配额永远 1 条**（`strategy_auth_missing_max_per_op=1`）
- **无 security 需求时**：策略跳过

---

## 6. 引擎编排（`engine.py`）

### 6.1 入口

```python
class TestDesignEngine:
    """F022 策略编排引擎。"""

    def __init__(self, settings: Settings) -> None:
        self.strategies: dict[str, Strategy] = {
            "happy_path": HappyPathStrategy(),
            "required_field_missing": RequiredFieldMissingStrategy(
                max_per_op=settings.strategy_required_field_missing_max_per_op,
            ),
            "enum_coverage": EnumCoverageStrategy(
                max_per_op=settings.strategy_enum_coverage_max_per_op,
            ),
            "boundary_min_max": BoundaryMinMaxStrategy(
                max_per_op=settings.strategy_boundary_min_max_max_per_op,
            ),
            "format_invalid": FormatInvalidStrategy(
                max_per_op=settings.strategy_format_invalid_max_per_op,
            ),
            "auth_missing": AuthMissingStrategy(
                max_per_op=settings.strategy_auth_missing_max_per_op,
            ),
        }
        self.enabled: dict[str, bool] = {
            "happy_path": settings.strategy_happy_path,  # 默认 True
            "required_field_missing": settings.strategy_required_field_missing,
            "enum_coverage": settings.strategy_enum_coverage,
            "boundary_min_max": settings.strategy_boundary_min_max,
            "format_invalid": settings.strategy_format_invalid,
            "auth_missing": settings.strategy_auth_missing,
        }
        self.max_intents_per_op: int = settings.generator_max_intents_per_operation
        self._validate_caps()  # 启动校验

    def _validate_caps(self) -> None:
        """strategy_*_max_per_op ≤ generator_max_intents_per_operation"""
        for name, strat in self.strategies.items():
            if strat.max_per_op > self.max_intents_per_op:
                raise StrategyCapError(
                    f"strategy '{name}' max_per_op={strat.max_per_op} "
                    f"exceeds generator_max_intents_per_operation={self.max_intents_per_op}"
                )

    def design(self, endpoint: EndpointSchema) -> list[TestIntent]:
        """Per-operation 设计入口（F023 主调用）。

        流程：
        1. 按策略优先级顺序收集 intent（happy_path 永远最先）
        2. 每个策略内部 max_per_op 截断 + WARNING
        3. 总数 > generator_max_intents_per_operation 时按优先级硬截
        4. 返回 TestIntent[]
        """
        intents: list[TestIntent] = []
        strategy_order = [
            "happy_path",
            "required_field_missing",
            "enum_coverage",
            "boundary_min_max",
            "format_invalid",
            "auth_missing",
        ]
        for name in strategy_order:
            if not self.enabled.get(name, False):
                continue
            strat = self.strategies[name]
            produced = strat.generate(endpoint)
            if len(produced) > strat.max_per_op:
                logger.warning(
                    "F022 strategy truncated: strategy=%s produced=%d cap=%d "
                    "operation=%s %s",
                    name, len(produced), strat.max_per_op,
                    endpoint.method, endpoint.path,
                )
                produced = produced[:strat.max_per_op]
            intents.extend(produced)
        # 硬截（按策略优先级取前 N）
        if len(intents) > self.max_intents_per_op:
            logger.warning(
                "F022 hard cap hit: produced=%d cap=%d operation=%s %s",
                len(intents), self.max_intents_per_op,
                endpoint.method, endpoint.path,
            )
            intents = intents[:self.max_intents_per_op]
        return intents

    def design_batch(
        self, endpoints: list[EndpointSchema]
    ) -> dict[str, list[TestIntent]]:
        """批量入口（按 (method, path) 作 key 返回）。"""
        return {
            f"{ep.method} {ep.path}": self.design(ep)
            for ep in endpoints
        }
```

### 6.2 错误类型（仅 Python 异常，非业务错误码）

```python
class StrategyError(Exception):
    """F022 基线策略异常。"""

class StrategyCapError(StrategyError):
    """strategy_*_max_per_op > generator_max_intents_per_operation。启动期抛。"""

class StrategyDisabledError(StrategyError):
    """F023 调用 design() 时若启用了一个未 enabled 的策略（理论上不会发生，留防御）。"""
```

---

## 7. 配置项（`app/config.py` 增量）

> 与 F022_PRECHECK §2.1 锁定一致。

```python
# app/config.py —— F022 增量
class Settings(BaseSettings):
    # ... 既有 F010/F013/F014/F015 配置项 ...

    # ---- F022 Test Design Engine ----
    strategy_happy_path: bool = True  # F012 向后兼容字节级保证
    strategy_required_field_missing: bool = False
    strategy_enum_coverage: bool = False
    strategy_boundary_min_max: bool = False
    strategy_format_invalid: bool = False
    strategy_auth_missing: bool = False

    generator_max_intents_per_operation: int = 20  # 范围 1-100

    strategy_required_field_missing_max_per_op: int = 5  # 1-20
    strategy_enum_coverage_max_per_op: int = 10  # 1-20
    strategy_boundary_min_max_max_per_op: int = 10  # 1-20
    strategy_format_invalid_max_per_op: int = 5  # 1-20
    strategy_auth_missing_max_per_op: int = 1  # 固定 1
```

启动期 `_validate_strategy_caps()` 校验所有 `strategy_*_max_per_op ≤ generator_max_intents_per_operation`。

---

## 8. 鉴权

- F022 是**纯内存**引擎，**不**接收 `current_user` / `session` / DB
- 调用方（F023 OpenApiImportService）必须在调用 `design()` 前完成 F012 的 `_load_project_suite` 鉴权
- F022 内部不引入任何鉴权路径

---

## 9. 日志

| 位置 | 等级 | 内容 |
|------|------|------|
| `engine._validate_caps()` 失败 | ERROR（启动失败） | `strategy_cap_violation strategy=<name> max=<N> generator_cap=<M>` |
| `engine.design()` 单策略截断 | WARNING | `F022 strategy truncated strategy=<name> produced=<K> cap=<N> operation=<method> <path>` |
| `engine.design()` 硬截 | WARNING | `F022 hard cap hit produced=<K> cap=<N> operation=<method> <path>` |
| 策略 `generate()` 内部边界 | DEBUG | 仅开发模式；生产默认 INFO 及以上 |
| **禁止** | — | 不打印 spec body / endpoint 完整请求体 / 认证头 / token |

---

## 10. 模块结构

### 10.1 新增文件

```text
src/app/domain/test_design/
├── __init__.py
├── schema.py              # TestIntent（Pydantic v2）
├── engine.py              # TestDesignEngine 编排 + 配额 + 截断
├── exceptions.py          # StrategyError / StrategyCapError / StrategyDisabledError
└── strategies/
    ├── __init__.py
    ├── happy_path.py
    ├── required_field_missing.py
    ├── enum_coverage.py
    ├── boundary_min_max.py
    ├── format_invalid.py
    └── auth_missing.py

src/app/config.py          # 增量 13 个 strategy_* / generator_* 配置项

src/tests/
├── openapi_factories.py   # F022 同步创建（详见 F022_PRECHECK §3.3）
└── test_test_design.py    # ≥15 用例
```

### 10.2 公共 API 出口

```python
# src/app/domain/test_design/__init__.py
from .engine import TestDesignEngine
from .schema import TestIntent
from .exceptions import StrategyError, StrategyCapError, StrategyDisabledError
```

---

## 11. 测试计划（≥15 用例）

> 全部使用 `src/tests/openapi_factories.py`（F022 同步创建）。

| # | 用例 | 关键断言 |
|---|------|----------|
| T1 | happy_path 单 endpoint | `len(intents) == 1`；`strategy == "happy_path"`；断言 = 默认 status_code in |
| T2 | happy_path 不被配额影响 | `max_per_op=0`（构造极端）；仍产 1 条 |
| T3 | required_field_missing = 3 fields, default cap | 产出 3 条；name 包含 "missing required field '<name>'" |
| T4 | required_field_missing = 8 fields, cap=5 | 产出 5 条 + WARNING 日志 |
| T5 | required_field_missing = 0 required fields | 产出 0 条 |
| T6 | enum_coverage 单字段 5 values | 产出 5 条；body 中该字段值遍历 enum |
| T7 | enum_coverage 多个字段 | 字段 1 (5 values) + 字段 2 (10 values) = 15 条 → 截到 10 |
| T8 | boundary_min_max 3 numeric fields | 每字段 6 条候选 = 18 → 截到 10 |
| T9 | boundary_min_max 边界值正确 | min-1, min, min+1, max-1, max, max+1 六值全部出现 |
| T10 | format_invalid email | 1 条；body.email = "not-a-valid-email"；期望 400/422 |
| T11 | format_invalid uuid | 1 条；body.uuid = "not-a-uuid"；期望 400/422 |
| T12 | auth_missing 带 security | 1 条；Authorization=None；期望 401 |
| T13 | auth_missing 无 security | 产出 0 条 |
| T14 | 多策略 enabled 联合（happy + required + enum） | 总数 1 + 3 + 5 = 9；happy 在最前 |
| T15 | 硬截（所有策略产出总和 > 20） | 按优先级截到 20；WARNING 命中 |
| T16 | 启动校验 `strategy_*_max > generator_max` | 抛 `StrategyCapError` |
| T17 | 默认 `enabled` 字节级 = F012 | 仅 happy_path=True 时，1 条 intent 与 F012 happy path 等价 |
| T18 | batch design 入口 | `design_batch(endpoints)` 返回 dict；key 为 `method path` |
| T19 | strategy 接口协议 | 6 个策略类都实现 `Strategy` Protocol（运行时检查） |
| T20 | TestIntent Pydantic v2 extra=forbid | 传额外字段抛 ValidationError |

---

## 12. 已知约束 / 待办（非本次范围）

| 项 | 说明 | 后续处理 |
|----|------|---------|
| happy_path 不复用 F012 的 Operation 数据 | F022 的 happy_path 是 F021 EndpointSchema 上的重新构建；不复用 `parser.py` 的 example 抽取 | F023 可选择是否对齐 |
| `auth_missing` 仅移除 `Authorization` header | 不处理 OAuth2 tokenUrl / APIKey in=query/cookie | F022+1 子项 |
| `boundary_min_max` 不支持 `exclusiveMinimum/exclusiveMaximum` | 当前仅用 `minimum/maximum` | F022+1 子项 |
| `enum_coverage` 不区分 `nullable=true` 的 enum | 视为普通 enum | 同上 |
| `format_invalid` 仅 6 种 format（email/uuid/date-time/uri/ipv4/ipv6） | 不覆盖全部 OpenAPI format 枚举 | 同上 |
| 跨 operation 配额（total ≤ X） | 不做；仅 per-operation 配额 | F023 评估 |
| 策略之间的"互斥"语义 | 当前独立产出；可能同一字段多个策略产出近似 intent | 不在 F022 范围 |

---

## 13. DoD（Definition of Done）

- [ ] `TestIntent` Pydantic v2 `extra="forbid"`，字段标注完整
- [ ] `TestDesignEngine.design()` + `design_batch()` 实现
- [ ] 6 个策略文件全部实现并被引擎加载
- [ ] 启动校验 `_validate_strategy_caps()` 在 `Settings` 初始化时跑通
- [ ] `app/config.py` 增量 13 个配置项 + 文档注释
- [ ] `src/tests/openapi_factories.py` 创建（含 8 个工厂函数）
- [ ] `src/tests/test_test_design.py` ≥ 20 个测试全绿（含 T1–T20 + 边界）
- [ ] F012/F013 现有 32 个测试零退化
- [ ] F021 现有 33 个测试零退化
- [ ] 全量回归 ≥ 457 测试全绿
- [ ] 5 份文档同步完成（SPEC 本稿 + BACKLOG F022 状态 + ACCEPTANCE §F022 +
  openapi_factories.py 引用 + ARCHITECTURE.md §4 加 test_design 标注）
- [ ] 日志脱敏验证：不打印 spec body、不打印认证头
- [ ] BACKLOG F022 状态更新至 Done
- [ ] **不**触发 ADR-009（属 F023 范围）

---

## 14. 风险与红线

- 🚫 **禁止引入 LLM / RAG / 第三方 schema 库**
- 🚫 **禁止修改 F012/F013/F021 既有契约**
- 🚫 **禁止新增业务表 / 修改 model.py**
- 🚫 **禁止新增整型错误码 / 业务码字符串**（HTTP 层错误码属 F023 ADR-009）
- 🚫 **禁止修改 happy_path 默认行为**（默认必须字节级 = F012）
- 🚫 **禁止硬编码** 任何 `strategy_*` / `generator_*` 常量；必须走 `app/config.py`
- 🚫 **禁止忽略鉴权 / 日志 / 测试 / 文档任一项**（AI_RULES §16）
- 🚫 **禁止在 F022 内做 TestCaseCreateRequest 转换**（属 F023）
- 🚫 **禁止引入 asyncio / 多进程**（F022 是同步纯函数）
