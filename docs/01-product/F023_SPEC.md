# F023 — Test Generator（消费 Intent 生成用例）Spec

> **状态**：Draft v1（基于 ADR-009 Accepted 2026-09-23；实施时按本稿）。
> **作者**：QA（基于 BACKLOG F023 行 + F022_SPEC §4 TestIntent 契约 + F013_SPEC 模式推导）。
> **范围**：API 自动化测试平台 MVP。
> **依赖**：F012（OpenAPI Import） · F013（批量导入） · F021（SchemaModel） · F022（TestDesignEngine + TestIntent） · ADR-009（**Accepted 2026-09-23**）。
> **Backlog 位置**：`docs/01-product/BACKLOG.md` → F023（P1 / **Doing** 2026-09-23）。
> **原则**：第一性原理 + 奥姆剃刀 + KISS + 零新表 + 沿用 F022 TestIntent + 复用 F012/F013 端点 + 规则化（不引入 AI）。

---

## 1. 背景与定位

F021（SchemaModel）+ F022（TestDesignEngine）已经把"接口契约 → 声明式用例意图（`TestIntent[]`）"打通。  
F023 是这条链路的最后一步：**把 `TestIntent[]` 变成可落库的 `TestCaseCreateRequest[]`**，并把生成能力**挂到现有 F012/F013 端点上**，让"策略驱动生成"通过 `?design=schema` 一个 Query 启用，**不引入新端点**。

**F023 不做**：
- ❌ 不重新设计 OpenAPI 解析（沿用 F012）
- ❌ 不新增用例存储（沿用 F007 `api_test_case`）
- ❌ 不重新设计鉴权（沿用 F012 `_load_project_suite`）
- ❌ 不重新设计 batch（沿用 F013 端点 + `?batch=true`）

**F023 做**：
- ✅ 新增纯函数 `TestGenerator`：`TestIntent + EndpointSchema(base_meta) -> TestCaseCreateRequest`
- ✅ 自动生成多类型断言：`status_code` / `json_path`（响应 schema required）/ `header`（content-type）
- ✅ Router `preview_or_import_openapi` 新增 `?design=` Query
- ✅ Service `preview` / `import_from_preview` / `preview_batch` / `import_batch_from_preview` 新增 `design` 参数
- ✅ 新增业务错误码 `GENERATOR_INTENT_LIMIT_EXCEEDED`
- ✅ 复用 F022 `generator_max_intents_per_operation`（**配置项唯一性**——见 ADR-009 §决策 1）

---

## 2. 冻结决策表（Q1–Q10 — 依据 ADR-009 Accepted 2026-09-23）

| ID | 决策 | 锁定结果 | 备注 |
|----|------|----------|------|
| Q1 | 配置项归属 | **复用** F022 `generator_max_intents_per_operation`（默认 20） | 单一配置源；F022 §7 已存在 |
| Q2 | `?design=` 字面量集合 | `Literal["simple", "schema"]` | `"simple"` = F012 字节级；`"schema"` = 策略驱动 |
| Q3 | `?design=` 默认值 | **`"simple"`**（即 `?design=` 省略时与 F012 等价） | 保证向后兼容 + 字节级承诺 |
| Q4 | HTTP 错误码范式 | **400 + 字符串业务码**（沿用 F012 §5.1 范式） | BACKLOG 原文写 "422"——**需 ADR 钉死**；当前 ERROR_CODE §5.1 全部用 400 |
| Q5 | 单 operation intent 超限 | **整批 abort**，抛 `GENERATOR_INTENT_LIMIT_EXCEEDED` | 不是数据错误，是配额保护 |
| Q6 | Batch 模式 + `design=schema` | 同 Q5 整批 abort（不沿用 F013 "per-doc 失败隔离"） | F013 的失败是 spec 解析失败；intent 超限是平台保护 |
| Q7 | json_path 断言输入 | F021 `ResponseSchema.schema_model.properties[*].required` | `EndpointSchema.responses` 中 status_code="200" 的 schema |
| Q8 | json_path 缺失时 | **静默跳过**（不警告），退化到 `status_code` only | 与 F022 "best-effort" 一致 |
| Q9 | 鉴权 | 沿用 F012 `_load_project_suite`（owner / superuser） | 零改动 |
| Q10 | 公共 API 出口 | `app.domain.test_generator.generator.TestGenerator` | 纯函数；service 持有实例 |

> Q4 是**最关键**的未决项。BACKLOG F023 行写"越界返回 422"，但现有 ERROR_CODE.md §5.1 范式是"400 + 字符串业务码"。两种范式各有先例（F009/F010 错误码用 400/500 数字，F012 用 400 字符串）。**强烈建议 Q4 = 400 字符串**——保持 F012/F013 已确立的"OpenAPI 导入类错误"范式一致性。

---

## 3. 数据契约

### 3.1 `TestGenerator`（纯函数）

```python
# src/app/domain/test_generator/generator.py
from typing import Optional

from app.domain.openapi_importer.schema_model import EndpointSchema
from app.domain.test_case.schema import TestCaseCreateRequest
from app.domain.test_design.schema import TestIntent


class TestGenerator:
    """F023 纯函数：TestIntent → TestCaseCreateRequest。

    设计原则：
    * 无状态（无 __init__ 字段，无 DB / session 依赖）
    * 接受 base_meta（happy_path intent 提供）用于相对覆盖
    * 多类型断言自动合并：status_code + json_path + header
    """

    def intent_to_request(
        self,
        intent: TestIntent,
        base_meta: EndpointSchema,
    ) -> TestCaseCreateRequest:
        """单条 Intent → 单条 TestCaseCreateRequest。

        步骤：
        1. 派生 headers / query_params / body：先取 happy_path 默认，再按 intent.*_override 覆盖
        2. 自动断言：status_code（from intent） + json_path（from response schema required）
                  + header（content-type 等）
        3. name 截断到 200 字符
        4. timeout_seconds 默认 30
        """
        ...

    def intents_to_requests(
        self,
        intents: list[TestIntent],
        base_meta: EndpointSchema,
    ) -> list[TestCaseCreateRequest]:
        """批量入口；intents[0] 应为 happy_path（作为 base_meta 的派生依据）。"""
        return [self.intent_to_request(i, base_meta) for i in intents]

    def _auto_json_path_assertions(
        self, base_meta: EndpointSchema
    ) -> list[dict[str, Any]]:
        """扫描 EndpointSchema.responses[status='200'].schema_model.properties 中
        required 字段，产出 json_path 断言 [{"type":"json_path","operator":"exists",
        "expected":"$.<field>"}]。
        """

    def _auto_header_assertions(
        self, base_meta: EndpointSchema
    ) -> list[dict[str, Any]]:
        """扫描 responses[status='200'].content_type → 断言 Content-Type header 存在。"""
```

### 3.2 自动断言规则（详细）

| 来源 | 触发条件 | 断言格式 |
|------|----------|----------|
| **status_code**（每条 intent 必有） | 总是 | `{"type":"status_code","operator":"in","expected":[200,201,202,204]}` 或 400/422/401 |
| **json_path**（happy_path 必带） | `responses[200].schema_model.properties` 有 `required` 字段 | `{"type":"json_path","operator":"exists","expected":"$.<field>"}` per field |
| **header**（happy_path 必带） | `responses[200].content_type` 存在 | `{"type":"header","operator":"exists","expected":"Content-Type"}` + **不强校验 value**（响应侧 content-type 协商由网关/反代决定） |
| **required_field_missing** | 来自 intent 自身 | `{"type":"status_code","operator":"in","expected":[400,422]}` |
| **enum_coverage / boundary / format / auth_missing** | 来自 intent 自身 | 沿用各 intent 期望 status_code |

**关键不变量**：所有 intent 的 `assertions` 列表 = `intent.assertions` ∪ `auto_assertions`（按上述规则），去重。

---

## 4. URL & Query（沿用 F012 + F013 端点）

### 4.1 单文档入口

```text
POST /api/v1/projects/{project_id}/suites/{suite_id}/import/openapi
```

新增 Query：

| Query | 默认 | 说明 |
|----|----|----|
| `design` | `"simple"` | `simple` → 沿用 F012 字节级（1 happy path / op）；`schema` → 启用 F022 TestDesignEngine + F023 TestGenerator |
| 其它 (`batch`, `dry_run`, `preview_id`, `on_conflict`, `name_prefix`) | 同 F012/F013 | 0 改动 |

### 4.2 批量入口

```text
POST /api/v1/projects/{project_id}/suites/{suite_id}/import/openapi?batch=true
```

`design` Query 同步生效；`documents[]` 中各 operation 独立跑 TestDesignEngine。

### 4.3 响应 Schema

| Mode | 现有（F012/F013） | F023 新增 |
|------|-------------------|-----------|
| `?design=simple&dry_run=true` | `ImportPreviewResponse` | **0 改动**（byte-for-byte） |
| `?design=simple&dry_run=false` | `ImportResponse` | **0 改动** |
| `?design=schema&dry_run=true` | `ImportPreviewResponse` | **新增字段** `total_intents: int`；每条 `operations[i].name` 改为"operation name + ': strategy'" |
| `?design=schema&dry_run=false` | `ImportResponse` | **新增字段** `total_created: int`；`created[]` 含 strategy 后缀 |
| `?design=schema&batch=true&dry_run=true` | `BatchImportPreviewResponse` | 每个 `documents[i].operations[j]` 多一条 `strategy: str` |
| `?design=schema&batch=true&dry_run=false` | `BatchImportResponse` | 每个 `documents[i].created[j]` 多一条 `strategy: str` |

> **关键不变量**：`?design=simple` 与"无 design 参数"在响应模型上**字节级一致**——前端可直接忽略 design 字段。

---

## 5. Service 层编排（最小增量）

### 5.1 复用清单

| 既有组件 | 用途 |
|----------|------|
| `OpenApiSpecParser` | F012（0 改动） |
| `SchemaAnalyzer` | F021（0 改动，输入 `Operation` → `EndpointSchema`） |
| `TestDesignEngine.design(endpoint)` | F022（0 改动，输入 `EndpointSchema` → `TestIntent[]`） |
| `TestCaseService.create_test_case` | F007（0 改动，落库 `TestCaseCreateRequest`） |
| `_load_project_suite` / `_find_existing_cases` | F012（0 改动） |
| `OpenApiImportService._preview_cache` | F012/F013（0 改动，缓存结构扩展 `[TestIntent[], ...]`） |

### 5.2 新增/修改方法

```text
OpenApiImportService
  ├── preview(..., design="simple|schema" = "simple")  # 改：新增 design 参数
  │     design="simple"  → F012 老路径（0 行为变化）
  │     design="schema"  → 对每个 operation：
  │                        1. analyze_operation → EndpointSchema
  │                        2. TestDesignEngine.design(endpoint) → TestIntent[]
  │                        3. TestGenerator.intents_to_requests(intents, endpoint)
  │                        4. 累加 total_intents；超 generator_max_intents_per_operation → 抛 GENERATOR_INTENT_LIMIT_EXCEEDED
  │
  ├── import_from_preview(..., design="simple|schema" = "simple")  # 改
  │     design="simple"  → F012 老路径
  │     design="schema"  → 从 _preview_cache 取出 TestIntent[] → TestGenerator → create_test_case * N
  │
  ├── preview_batch(..., design="simple|schema" = "simple")  # 改
  │     同 preview，但每 operation 独立算；任一超限 → 整批 abort（同 F022 风格）
  │
  └── import_batch_from_preview(..., design="simple|schema" = "simple")  # 改
```

### 5.3 Router 层

```python
# src/app/interfaces/http/openapi_importer_router.py
from typing import Literal

DesignMode = Literal["simple", "schema"]

@import_router.post("...")
async def preview_or_import_openapi(
    ...,
    design: DesignMode = Query(default="simple"),
    ...,
):
    if batch:
        if dry_run or preview_id is None:
            return await service.preview_batch(..., design=design)
        return await service.import_batch_from_preview(..., design=design)
    if dry_run or preview_id is None:
        return await service.preview(..., design=design)
    return await service.import_from_preview(..., design=design)
```

---

## 6. 配置项

**0 新配置**（F022 §7 已定义，F023 复用）：

| 配置 | 来源 | 默认 | F023 用法 |
|------|------|------|-----------|
| `generator_max_intents_per_operation` | F022 §7 | 20 | 超限抛 `GENERATOR_INTENT_LIMIT_EXCEEDED` |
| `strategy_*_max_per_op` | F022 §7 | 1–10 | 间接限制单 op intent 上限 |
| `strategy_*` (6 布尔) | F022 §7 | True / False | 决定启用哪些策略 |

**启动期校验**（沿用 F022 `_validate_strategy_caps`）：
- 单 `strategy_*_max_per_op ≤ generator_max_intents_per_operation`（F022 已校验）

---

## 7. 错误响应（**待 ADR-009 Q4 钉死**）

**推荐方案**（与 F012/F013 同范式）：

| HTTP | 业务 code | 说明 |
|------|-----------|------|
| **400** | `GENERATOR_INTENT_LIMIT_EXCEEDED` | 单 operation intent 数 > `generator_max_intents_per_operation` |
| 422 | `VALIDATION_ERROR` | `?design=BOGUS` 非法字面量（FastAPI Literal 校验自动） |

> BACKLOG F023 行写 "422 `GENERATOR_INTENT_LIMIT_EXCEEDED`"。**强烈建议改为 400**（与 F012 §5.1 / F013 §5.1 范式一致）；如保留 422，需在 ADR-009 中给出明确理由。

---

## 8. 鉴权

完全沿用 F012 `_load_project_suite`：
- 必须登录（`get_current_user`）
- 必须当前用户是 `project.owner_id` 或 `is_superuser`
- `suite.project_id == path.project_id`

跨用户 / 跨项目 / 跨 suite 的负向用例**直接复用** `test_openapi_importer.py` 既有鉴权测试，新增 `?design=schema` 的等价变体。

---

## 9. 日志

| 位置 | 等级 | 内容 |
|------|------|------|
| `preview(design="schema")` 入口 | INFO | `generator_preview project=... suite=... design=schema ops=N` |
| `import_from_preview(design="schema")` 入口 | INFO | `generator_commit project=... suite=... design=schema intents=K` |
| intent 超限 | WARNING | `GENERATOR_INTENT_LIMIT_EXCEEDED operation=<method> <path> produced=K cap=M` |
| **禁止** | — | 不打印 spec body / 认证头 / token（沿用 F012 §8 红线） |

---

## 10. 测试计划

> 测试层划分与用例编号见 **§10.1–§10.4**。完整用例集 T1–T_N 在 `src/tests/TEST_PLAN_F023.md` 单独维护（待落地）。

### 10.1 单元层 — `src/tests/test_test_generator.py`（**新文件**）

| ID | 用例 | 关键断言 |
|----|------|----------|
| FT-U01 | `intent_to_request(happy_path)` 字节级等价 F012 旧分支 | 断言 = `[{"type":"status_code","operator":"in","expected":[200,201,202,204]}]` |
| FT-U02 | `intent_to_request(required_field_missing)` body_override 应用 | body 字段置 None；assertions 含 status_code in [400,422] |
| FT-U03 | `intent_to_request(enum_coverage)` body 单字段替换 | 仅替换目标字段，其它字段不变 |
| FT-U04 | `intent_to_request(boundary_min_max)` body 单数值替换 | min-1/min/min+1/max-1/max/max+1 各自一条 |
| FT-U05 | `intent_to_request(format_invalid)` body 字段填非法值 | email→"not-a-valid-email" |
| FT-U06 | `intent_to_request(auth_missing)` Authorization 移除 | headers 中不包含 Authorization；assertions 期望 401 |
| FT-U07 | `name` 长度截断 | `len(name) == 200` |
| FT-U08 | `body_type_override` 切换 json/none/form/raw | body_type 正确传递 |
| FT-U09 | `assertion` 合并去重 | intent.assertions ∪ auto_assertions 去重 |
| FT-U10 | json_path 自动生成（响应 schema required） | 响应 schema required = ["id","name"] → 断言含 json_path $.id exists / $.name exists |
| FT-U11 | json_path 不生成（响应 schema 缺失） | 0 条 json_path；仅 status_code |
| FT-U12 | header 自动生成（content-type） | header Content-Type exists |
| FT-U13 | 多 intent 顺序保留 | 1 happy + N required → 顺序符合 F022 优先级 |

### 10.2 Service 层 — `test_openapi_importer.py` 增量

| ID | 用例 | 关键断言 |
|----|------|----------|
| FT-S01 | `preview(design="simple")` 字节级 = F012 | 默认行为无变化 |
| FT-S02 | `preview(design="schema")` 开启全部策略 | 每 op → 1+N preview |
| FT-S03 | `preview(design="schema")` 仅 happy_path=True | 字节级 = FT-S01 |
| FT-S04 | `preview(design="schema")` 单 op 超 20 | 抛 `GENERATOR_INTENT_LIMIT_EXCEEDED` |
| FT-S05 | `import_from_preview(design="schema")` 真落库 | 落库 case 数 = intent 总数；assertions 正确持久化 |
| FT-S06 | `import_from_preview(design="schema")` + `on_conflict=skip` 重复 | 旧 case 全部 skipped；新 intent 全 created |
| FT-S07 | `preview_batch(design="schema")` 多文档策略驱动 | 每文档独立算；任一超限 → 整批 abort |
| FT-S08 | `import_batch_from_preview(design="schema")` 真落库 | DB 行数 = ∑intents |
| FT-S09 | `preview(design="BOGUS")` | 422 `VALIDATION_ERROR` |

### 10.3 Router 层 — `test_openapi_importer.py` 增量（与 §10.2 同文件）

| ID | 用例 | 关键断言 |
|----|------|----------|
| FT-R01 | `?design=schema&dry_run=true` | 200；preview 含 `total_intents` |
| FT-R02 | `?design=schema&dry_run=false&preview_id=...` | 200；DB api_test_case 新增 = intents.length |
| FT-R03 | `?design=simple`（默认省略）字节级 = FT-R01 默认 | 与 F012 老路径字节级一致 |
| FT-R04 | `?design=schema` intent 超 20 | 400 `GENERATOR_INTENT_LIMIT_EXCEEDED` |
| FT-R05 | `?design=schema` 无 auth | 401 |
| FT-R06 | `?design=schema` 非 owner | 403 |
| FT-R07 | `?design=schema` cross-project | 404 |
| FT-R08 | `?design=schema&batch=true` 多文档 | 复用 F013 batch 语义，每条 case 落库带正确 assertions |
| FT-R09 | `?design=BOGUS` | 422 `VALIDATION_ERROR` |
| FT-R10 | `?design=schema` + 同一 spec 二次 preview | preview_id → import 字节级 = 一次 |

### 10.4 鉴权 + 回归 — `test_authz_regressions.py` 增量

| ID | 用例 |
|----|------|
| FT-A01 | `?design=schema` 非 owner → 403 |
| FT-A02 | `?design=schema` cross-project → 404 |
| FT-A03 | `?design=schema` 无 token → 401 |

### 10.5 回归（全量）

- F012 既有 13 个测试**零修改**通过
- F013 既有 13 个测试**零修改**通过
- F022 既有 23 个测试通过
- F021 既有 33 个测试通过
- 全量 `pytest src/tests -v` ≥ 480 全绿（F022 baseline）

---

## 11. 可复用 fixture（前置基建）

> 由 QA 团队**在 F023 测试代码落地前**抽到 `src/tests/conftest.py`（详见 §11.1–§11.6）。

```python
# 新增 fixture（不破坏既有）

@pytest.fixture
def auth_headers(token: str) -> dict[str, str]:
    """`{"Authorization": f"Bearer {token}"}` —— 消除 18 个 router 文件的重复样板。"""
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def admin_user(client, user_payload):
    """= 现行 registered_user 的语义清晰版；不破坏既有调用。"""
    resp = await client.post("/api/v1/auth/register", json=user_payload)
    assert resp.status_code == 201
    body = resp.json()
    return {
        "user": body["user"],
        "access_token": body["token"]["access_token"],
        "refresh_token": body["token"]["refresh_token"],
        "headers": {"Authorization": f"Bearer {body['token']['access_token']}"},
    }

@pytest_asyncio.fixture
async def member_user(client, admin_user, auth_headers):
    """第二位用户（受 admin 限权，is_superuser=False），用于鉴权回归。"""
    second_payload = {
        **user_payload,  # 由调用方 fixture 参数注入
        "username": "member",
        "email": "member@example.com",
    }
    resp = await client.post(
        "/api/v1/auth/register",
        json=second_payload,
        headers=admin_user["headers"],
    )
    assert resp.status_code == 201
    body = resp.json()
    return {
        "user": body["user"],
        "access_token": body["token"]["access_token"],
        "headers": {"Authorization": f"Bearer {body['token']['access_token']}"},
    }

@pytest_asyncio.fixture
async def make_project(client, auth_headers):
    """Factory fixture：POST /api/v1/projects → 返回 project dict（含 id）。"""
    async def _create(name: str = "Test Project", description: str = ""):
        resp = await client.post(
            "/api/v1/projects",
            json={"name": name, "description": description},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()
    return _create

@pytest_asyncio.fixture
async def make_environment(client, auth_headers, make_project):
    """Factory fixture：POST /api/v1/projects/{pid}/environments → 返回 env dict。"""
    async def _create(
        project_id: UUID,
        base_url: str = "https://api.test",
        name: str = "default",
        headers: dict | None = None,
        variables: dict | None = None,
        is_default: bool = False,
    ):
        payload = {
            "name": name,
            "base_url": base_url,
            "is_default": is_default,
        }
        if headers is not None:
            payload["headers"] = headers
        if variables is not None:
            payload["variables"] = variables
        resp = await client.post(
            f"/api/v1/projects/{project_id}/environments",
            json=payload,
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()
    return _create

@pytest_asyncio.fixture
async def make_suite(client, auth_headers):
    """Factory fixture：POST /api/v1/projects/{pid}/suites → 返回 suite dict。"""
    async def _create(project_id: UUID, name: str = "Test Suite", description: str = ""):
        resp = await client.post(
            f"/api/v1/projects/{project_id}/suites",
            json={"name": name, "description": description},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()
    return _create
```

### 11.7 验证步骤

```bash
pytest src/tests -v --tb=short
# 期望：≥ 480 测试全绿（与 F022 baseline 持平）
```

---

## 12. 文档同步清单（实施时一并交付）

| 文档 | 内容 |
|------|------|
| `docs/01-product/BACKLOG.md` | F023 状态 Todo → Doing → Done |
| `docs/04-rules/ADR.md` | 已完成 ADR-009（**Accepted 2026-09-23**，本 SPEC §2 Q1–Q10 + §7 错误码范式） |
| `docs/03-api/ERROR_CODE.md` §5.1 | 新增 `GENERATOR_INTENT_LIMIT_EXCEEDED` 行（HTTP 码待 ADR 钉死） |
| `docs/03-api/OPENAPI.yaml` | `preview_or_import_openapi` 加 `?design` Query；响应模型加可选 `total_intents` |
| `docs/03-api/API_GUIDE.md` §3 | 加 F023 子节（与 F012/F013 同级） |
| `docs/05-test/ACCEPTANCE.md` | 登记 F023 验收条目（覆盖 §10 用例） |
| `src/tests/TEST_PLAN_F023.md` | QA 维护：FT-U/S/R/A 全部用例到函数名 1:1 映射（本 SPEC §10 落地后产出） |

---

## 13. DoD（Definition of Done）

- [ ] ADR-009 写完并被产品/架构 Accepted（§2 Q1–Q10 + §7 钉死）
- [ ] `TestGenerator` 纯函数实现 + 13 个单测（§10.1）
- [ ] Service 层 4 个方法均接受 `design` 参数；`design="simple"` 与 F012 字节级一致
- [ ] Router `preview_or_import_openapi` 新增 `?design=` Query；`Literal` 校验
- [ ] 配置项 **0 新增**（复用 F022 `generator_max_intents_per_operation`）
- [ ] 业务错误码 `GENERATOR_INTENT_LIMIT_EXCEEDED` 在 ERROR_CODE.md §5.1 登记
- [ ] §11 fixture 6 个新增并跑通 baseline
- [ ] §10 全部测试用例（≈ 36 个）全绿
- [ ] F012/F013/F022/F021 既有 80+ 测试**零退化**
- [ ] 全量回归 `pytest src/tests -v` ≥ 480 全绿
- [ ] 文档 5 份同步（§12）
- [ ] 日志脱敏验证：不打印 spec body / 认证头
- [ ] BACKLOG F023 状态更新至 Done

---

## 14. 风险与红线

- 🚫 **禁止引入 LLM / RAG / 第三方 schema 库**
- 🚫 **禁止修改 F012/F013/F021/F022 既有契约**
- 🚫 **禁止新增数据库表 / 修改 model.py**
- 🚫 **禁止新增配置项**（复用 F022）
- 🚫 **禁止修改 happy_path 默认行为**（`?design=simple` 默认必须字节级 = F012）
- 🚫 **禁止硬编码** 任何 intent 配额常量
- 🚫 **禁止忽略鉴权 / 日志 / 测试 / 文档任一项**（AI_RULES §16）
- 🚫 **禁止在 F023 内做策略执行 / 设计**（属 F022）
- 🚫 **禁止回滚已成功落库的用例**（沿用 F012 红线）
- 🚫 **禁止覆盖时级联删除 TestResult**（沿用 F012/F013 红线）

---

## 15. ADR-009 决策落地状态

| 项 | ADR-009 决策 | 实施要求 |
|----|--------------|----------|
| HTTP 错误码（Q4） | **400 字符串**（与 F012/F013 一致） | `OpenApiImportService` 抛 `OpenApiIntentLimitExceededError`（HTTP 400，code=`GENERATOR_INTENT_LIMIT_EXCEEDED`） |
| Batch 模式超限行为（Q6） | **整批 abort** | 抛同款异常，整批 preview/commit 失败 |
| json_path 缺失时行为（Q8） | **静默跳过** | `TestGenerator._auto_json_path_assertions` 在 `EndpointSchema.responses` 无 2xx schema 时返回 `[]` |
| `?design=` 字面量集合（Q2） | `Literal["simple", "schema"]` | Router `?design=Query(...)`；FastAPI `Literal` 校验自动 422 on `BOGUS` |
| 测试层用例分配 | 单元 13 / Service 9 / Router 10 / 鉴权 3 = **35 个**（不含 §10.5 回归） | `src/tests/test_test_generator.py`（新）+ `test_openapi_importer.py` 增量 + `test_authz_regressions.py` 增量 |
| 配置项归属（Q1） | **复用** F022 `generator_max_intents_per_operation` | **0 新增**配置项；启动校验沿用 F022 `_validate_strategy_caps` |
| 鉴权 | 沿用 F012 `_load_project_suite` | 0 改动；测试复用 `test_authz_regressions.py` 矩阵 |