# F013 — 批量生成基础用例（Spec）

> 范围：API 自动化测试平台 MVP。  
> 版本：v1.0（冻结稿，2026-07-22）。  
> 依赖：F012（OpenAPI 导入） · F007（用例 CRUD） · F006（集合/批量入库/owner 鉴权基线）。  
> Backlog 位置：`docs/01-product/BACKLOG.md` → F013（P1 / Doing）。  
> 原则：第一性原理 + 奥姆剃刀 + KISS + 零新表 + 沿用 F012 契约。

---

## 1. 背景与定位

F012 已经能从单份 OpenAPI 文档生成基础 API 用例草稿（一站式 `POST /import/openapi` + `?dry_run` + `on_conflict`）。  
但实际项目里测试资产往往按 **多个上游服务的 OpenAPI 文档** 分散维护，逐份调用费时、容易遗漏。

F013 把 F012 升级为 **多文档批量**：一次提交 N 份 OpenAPI 文档，生成 N 组基础用例，落到同一个 Suite，全部沿用 F012 的"是否覆盖"语义。

**核心约束**：
- 不重复造轮子：解析器、唯一键、落入 Suite 的路径、two-phase dry_run、`on_conflict` 全部沿用 F012。
- 不动数据模型、不写 Alembic migration。
- 不引入新框架、不引入新中间件。
- 不破坏 F012 现有契约（单文档入口仍可用）。

---

## 2. 冻结决策表（Q1–Q10，全部锁定）

> 与下方"实现要求"绑死；任何改动必须重新走一轮 Backlog + ADR。

| ID | 决策 | 锁定结果 | 与 F012 关系 |
|----|------|----------|--------------|
| Q1 | "批量"含义 | **多 OpenAPI 文档一次提交**（URL / 文本 JSON 二选一逐文档） | 在 F012 现有 `source_url/source_content` 二选一模式上扩为数组 |
| Q2 | 每 operation 草稿条数 | **1 条 happy path** | 完全沿用 F012 |
| Q3 | "草稿"如何表达 | **沿用 `TestCaseService.create_test_case` 默认 status，不强制 disabled** | 不干预 model.py / 不新增枚举 |
| Q4 | 落入哪个 Suite | **suite_id 走路径参数（强制显式传）** | 沿用 F012 端点结构 |
| Q5 | 用例唯一键 + 行为 | **(project_id, method, path)；冲突时 `on_conflict` ∈ `skip / overwrite`** | 沿用 F012 的 `Literal["skip","overwrite"]` |
| Q6 | 幂等策略 | **不做文档级幂等**：逐 operation 按唯一键处理；同名 → skip 或 overwrite 由请求方决定 | 不存 content hash |
| Q7 | 失败回滚 | **单文档失败 → 该文档失败明细累积，不影响其它文档** | 沿用 F012 `errors[]` 累计风格 |
| Q8 | dry_run | **沿用 F012 two-phase**：first call → preview + `preview_id`；second call with `?batch=true&preview_id=...` → 真创建 | 不发明新机制 |
| Q9 | 配额 | **N = 5 文档 / M = 50 operation/文档** → `OPENAPI_BATCH_MAX_DOCS`、`OPENAPI_BATCH_MAX_OPS_PER_DOC` 走 `app/config.py`，禁硬编码 | **新增**配置项 |
| Q10 | 错误码 | **不新增整型 code**，沿用 F012 的"400 + 字符串业务码"模式；**仅新增 1 个业务码** `OPENAPI_BATCH_LIMIT_EXCEEDED` | 不复用 33001–33004（该段不存在） |

---

## 3. 与 F012 的差异表（小而准）

| 项 | F012（单文档） | F013（批量） |
|----|----------------|---------------|
| 端点 | `POST /projects/{pid}/suites/{sid}/import/openapi` | 同 URL，加 `?batch=true` 启用批量模式 |
| 请求体 | 单 `source_url` XOR `source_content` + `tags` + `on_conflict` + `name_prefix` + `dry_run` | 出现 `documents[]` 时**忽略**单文档字段（互斥，模型层 `model_validator` 保证） |
| 响应体 | `ImportPreviewResponse` / `ImportResponse`（所有 operation 揉在一起） | 新增 `documents: list[DocumentSummary]` 字段，每个 doc 一份聚合（preview/complete 两种形态） |
| 限流 | 无（单文档够用） | 文档数 ≤ N（默认 5）；单文档 operation ≤ M（默认 50） |
| 错误码 | `OPENAPI_PARSE_ERROR` / `OPENAPI_FETCH_ERROR` / `OPENAPI_IMPORT_CONFLICT` | 全部沿用 + `OPENAPI_BATCH_LIMIT_EXCEEDED` |

---

## 4. API 形状（沿用 F012，等价于"已实现能力的批量升级"）

### 4.1 URL & Query

```text
POST /api/v1/projects/{project_id}/suites/{suite_id}/import/openapi?batch=true|false
```

| Query | 默认 | 说明 |
|-------|------|------|
| `batch` | `false` | `false`/缺失 → 走 F012 单文档语义；`true` → 启用 F013 批量 |
| `dry_run` | `true` | 沿用 F012 |
| `preview_id` | `null` | 沿用 F012 |
| `on_conflict` | `skip` | 沿用 F012 |
| `name_prefix` | `null`（批量时仅作默认前缀，单文档可逐个覆盖） | 沿用 F012 |

> **`batch=false` 的请求/响应完全 = F012 现状**，不引入任何 breaking change。  
> `batch=true` 时请求体按 §4.2；响应体按 §4.3。

### 4.2 请求 Schema（`batch=true`）

在 `OpenApiImportRequest` 上加可选字段：

```python
class OpenApiImportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_url: Optional[str] = None          # 二选一
    source_content: Optional[dict[str, Any]] = None  # 二选一
    tags: Optional[list[str]] = None
    name_prefix: Optional[str] = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _check_source(self) -> "OpenApiImportDocument":
        if (self.source_url is None) == (self.source_content is None):
            raise ValueError("exactly one of source_url/source_content required")
        if self.source_url is not None:
            url = self.source_url.lower()
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("source_url must start with http:// or https://")
        return self


class OpenApiImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 单文档字段（向后兼容，保持原状）
    source_url: Optional[str] = Field(default=None)
    source_content: Optional[dict[str, Any]] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)
    on_conflict: ImportConflictStrategy = Field(default="skip")
    dry_run: bool = Field(default=True)
    name_prefix: Optional[str] = Field(default=None, max_length=80)

    # F013 批量字段（与上面互斥）
    documents: Optional[list[OpenApiImportDocument]] = None

    @model_validator(mode="after")
    def _check_source(self) -> "OpenApiImportRequest":
        # 单文档路径不变（与 F012 行为一致）
        if self.documents is None:
            if (self.source_url is None) == (self.source_content is None):
                raise ValueError(
                    "exactly one of source_url/source_content required"
                )
            if self.source_url is not None:
                url = self.source_url.lower()
                if not (
                    url.startswith("http://")
                    or url.startswith("https://")
                ):
                    raise ValueError(
                        "source_url must start with http:// or https://"
                    )
            return self
        # 批量路径
        if not (1 <= len(self.documents) <= settings.OPENAPI_BATCH_MAX_DOCS):
            raise ValueError(
                f"documents size must be in [1, "
                f"{settings.OPENAPI_BATCH_MAX_DOCS}]"
            )
        if (
            self.source_url is not None
            or self.source_content is not None
            or self.tags is not None
            or self.name_prefix is not None
        ):
            raise ValueError(
                "documents[] is mutually exclusive with single-doc fields"
            )
        return self
```

> 单文档字段被复用，`model_validator` 必须保证 422 行为在 F012 测试用例下不退化。

### 4.3 响应 Schema（`batch=true`）

#### 4.3.1 Preview（`?dry_run=true`）

```python
class DocumentPreviewSummary(BaseModel):
    doc_index: int                # 入参 documents[] 中的下标
    source: str                   # "url:https://..." | "content:<sha256_前8位>"
    spec_version: str
    base_path: str
    total: int
    new_count: int
    existing_count: int
    skipped_count: int
    operations: list[OperationPreview]
    errors: list[str]            # 仅归属于本文档


class BatchImportPreviewResponse(BaseModel):
    suite_id: UUID
    suite_name: str
    total_documents: int
    total_operations: int
    documents: list[DocumentPreviewSummary]
    errors: list[str]             # 跨文档汇总（例如任一文档超 M）
```

#### 4.3.2 Commit（`?dry_run=false&preview_id=...&batch=true`）

```python
class DocumentImportSummary(BaseModel):
    doc_index: int
    source: str
    created: list[str]
    skipped: list[str]
    overwritten: list[str]
    errors: list[str]


class BatchImportResponse(BaseModel):
    total_documents: int
    total_attempted: int
    total_succeeded: int
    documents: list[DocumentImportSummary]
    errors: list[str]
```

**关键不变量**：
- `created` / `skipped` / `overwritten` / `errors` 全部"按文档拆开"放在 `documents[i]` 下，跨文档汇总到顶层（仅 `errors`）便于一眼判断是否有失败。
- 单文档失败 → 仅该 `documents[i].errors` 增加项，其它 `documents[j]` 正常落库，不回滚。

### 4.4 错误响应（沿用 F012 的"400 + 业务码字符串"）

新增唯一一个业务码 `OPENAPI_BATCH_LIMIT_EXCEEDED`，其它沿用：

| HTTP | 业务 code | 说明 |
|------|-----------|------|
| 400 | `OPENAPI_PARSE_ERROR` | 文档无效 / 版本不支持（沿用） |
| 400 | `OPENAPI_FETCH_ERROR` | URL 抓取失败（沿用） |
| 400 | `OPENAPI_IMPORT_CONFLICT` | preview_id 失效 / 缓存丢失（沿用） |
| 400 | `VALIDATION_ERROR` | 请求体不合法（沿用） |
| **400** | **`OPENAPI_BATCH_LIMIT_EXCEEDED`** | **文档数 > N 或 单文档 operation > M**（新） |

> **不再新增整型错误码**。本规范彻底撤销早期规划里"33001–33004"的设想——F012 已确立"400 + 字符串业务码"范式，F013 沿用。

---

## 5. Service 层编排（最小增量）

### 5.1 复用清单（禁止重复造）

| 既有组件 | 用途 |
|----------|------|
| `OpenApiSpecParser` | 解析每份文档（**0 改动**） |
| `Operation` / `ParsedSpec` | 解析结果（**0 改动**） |
| `TestCaseService.create_test_case` | 用例落库（**0 改动**） |
| `TestCaseService.delete_test_case` | `overwrite` 时删除旧用例（**0 改动**） |
| `SuiteService.get_suite` / `ProjectService.get_project` | 鉴权 / 取资源（**0 改动**） |
| `OpenApiImportService._find_existing_cases` | 唯一键查询（**0 改动**，行 186–198） |

### 5.2 新增方法（仅在 service 层增量）

```text
OpenApiImportService
  ├── preview(...)           # 已有，F013 batch=true 时路由到下面
  ├── import_from_preview(...)  # 已有，F013 batch=true 时路由到下面
  │
  ├── preview_batch(...)     # 新增
  │     输入：documents: list[OpenApiImportDocument]
  │     行为：
  │       1. 对每个 doc 调用 parser 解析（try/except 捕获为 errors）
  │       2. 检查任一 doc.operation 数 > M → 抛 OPENAPI_BATCH_LIMIT_EXCEEDED
  │       3. 为整批生成 1 个 preview_id，写进 _preview_cache
  │          （缓存值为 list[(doc_index, ParsedSpec)]）
  │       4. 对每个 doc 调用现有 _find_existing_cases → 同一份缓存里归并
  │       5. 返回 BatchImportPreviewResponse
  │
  └── import_batch_from_preview(...)  # 新增
        输入：preview_id, on_conflict, name_prefix
        行为：
          1. 取缓存；缺失 → OPENAPI_IMPORT_CONFLICT
          2. 对每个 doc 循环现有 import_from_preview 的核心循环
             （按 on_conflict 走 skip / overwrite）
          3. 失败单 op 进对应 documents[i].errors，不影响其它 doc
          4. 返回 BatchImportResponse
```

### 5.3 Router 入口（增量分支）

```text
openapi_importer_router.preview_or_import_openapi  (已有)
  入参增加: batch: bool = Query(default=False)
  分支:
    if not batch:
        # 完全沿用 F012 路径（保证 back-compat）
        ...
    else:
        if dry_run or preview_id is None:
            return await service.preview_batch(...)
        return await service.import_batch_from_preview(...)
```

### 5.4 配置项

`src/app/config.py` 新增：

```python
# F013 OpenAPI batch import limits
OPENAPI_BATCH_MAX_DOCS: int = 5
OPENAPI_BATCH_MAX_OPS_PER_DOC: int = 50
```

> 一律走配置，不硬编码。常量值由 `app/config.py` 单点维护。

---

## 6. 数据层承诺

- 0 新表。
- 0 Alembic migration。
- 0 `model.py` 字段新增。
- 用例落库走 F007 `test_case_service.create_test_case`，状态由该 Service 决定（F013 不干预）。
- 覆盖（`on_conflict=overwrite`）时旧用例历史 `TestResult` **不级联删除**，保留可追溯（AI_RULES §6 / §16）。

---

## 7. 鉴权

| 维度 | 要求 |
|------|------|
| JWT | 必须登录（沿用 `get_current_user`） |
| 项目 owner | 必须当前用户是 `project.owner_id` 或 `is_superuser`（沿用 F012 `_load_project_suite`） |
| Suite 归属 | `suite.project_id == path.project_id`（沿用） |

跨用户 / 跨项目 / 跨 suite 的负向用例直接复用 F012 测试 `test_openapi_preview_403_for_non_owner` / `test_openapi_preview_404_for_missing_project`。

---

## 8. 日志

| 位置 | 内容 |
|------|------|
| Service 入口 | INFO：`batch_import_preview` / `batch_import_commit`，带 `documents_count`、项目/套件 ID |
| 文档解析失败 | WARNING：`OPENAPI_PARSE_ERROR doc_index=N source=...`（不打印 body） |
| 数量越界 | WARNING：`OPENAPI_BATCH_LIMIT_EXCEEDED docs=N/N_max ops=M/M_max` |
| 退出 | INFO：成功/失败汇总（`total_succeeded / total_attempted`） |
| **禁止** | 不打印 spec body、不打印 token / cookie |

---

## 9. 测试计划

> 沿用 `src/tests/test_openapi_importer.py` 风格（in-process `client` + `_create_project_and_suite` helper）。

### 9.1 必须新增的测试用例

| # | 用例 | 关键断言 |
|---|------|----------|
| T1 | `preview_batch=true` 多文档（如 2 份） | 200，`documents` 长度 == 入参，每个 doc 各自 `new_count`、`operations[]` |
| T2 | `commit batch=true&preview_id=...` 真创建 | 200，`documents[i].created` 聚合等于 `project_test_cases` 新增数量 |
| T3 | `batch=true` 单文档与单文档端点结果一致 | 两个路径在 `documents=[d]` 与 `?batch=true` 下产出相同 case 数 |
| T4 | `documents=[]` （空数组） | 422（`docs size must be in [1, N]`） |
| T5 | `documents` 数 > N（默认 5） | 422 `OPENAPI_BATCH_LIMIT_EXCEEDED` |
| T6 | 单文档 operation > M（默认 50） | 400 `OPENAPI_BATCH_LIMIT_EXCEEDED` |
| T7 | 部分文档失败 + 部分成功 | 成功文档全部落库；失败文档仅在 `documents[i].errors` 里 |
| T8 | `batch=true` 与单文档字段同传 | 422（互斥） |
| T9 | `batch=true&dry_run=true` 不落库 | DB `api_test_case` 不增加 |
| T10 | `batch=true&on_conflict=overwrite` 重复提交 | 旧用例被删 + 新用例落库，**TestResult 历史保留** |
| T11 | `batch=true&on_conflict=skip` 重复提交 | 全部 `skipped[]`，零 `created` |
| T12 | 跨用户调用：非 owner | 403 |
| T13 | 跨项目调用：`suite.project_id != project_id` | 404 |

### 9.2 回归

- 跑一次 `pytest src/tests/test_openapi_importer.py` 全量。
- 跑一次 `pytest src/tests` 全量，确保 F007 / F006 / F010 / F011 无回归。

---

## 10. 已知约束 / 待办（非本次范围）

| 项 | 说明 | 后续处理 |
|----|------|----------|
| `_preview_cache` 进程内 dict | 服务重启或多 worker 下缓存丢失 → 必须重新 `?dry_run=true` | 与 F012 一同处理；不在 F013 范围 |
| 单次最多 `5 × 50 = 250` operation | 越界 → 422 | 后续如需更大配额，调 `app/config.py` 即可（不需代码改动） |
| URL 抓取 5s 超时 | 沿用 `OpenApiSpecParser.HTTP_TIMEOUT` | 同上 |
| `documents[]` 与单文档字段互斥 | 模型层强制 | 文档需明确告知调用方 |

---

## 11. 文档同步清单（实施时一并交付）

| 文档 | 内容 | 状态 |
|------|------|------|
| `docs/01-product/BACKLOG.md` | F013 状态 Todo → Doing；实现完成后 → Done | 待执行 |
| `docs/03-api/OPENAPI.yaml` | 在 F012 端点上补 `?batch=true`、`documents[]`、批量响应 schema | 待执行 |
| `docs/03-api/API_GUIDE.md` | §3.8 下加 F013 子节 | 待执行 |
| `docs/03-api/ERROR_CODE.md` | §5.1 新增 `OPENAPI_BATCH_LIMIT_EXCEEDED` 一行 | 待执行 |
| `docs/05-test/ACCEPTANCE.md` | 登记 F013 验收条目（覆盖 T1–T13 子集） | 待执行 |

---

## 12. DoD（Definition of Done）

- [ ] `OpenApiImportRequest` / `OpenApiImportDocument` / `BatchImportPreviewResponse` / `BatchImportResponse` 全部带 `extra="forbid"` 与类型标注
- [ ] `app/config.py` 新增 `OPENAPI_BATCH_MAX_DOCS=5`、`OPENAPI_BATCH_MAX_OPS_PER_DOC=50`
- [ ] Service / Router 增量分支可用，`batch=false` 与 F012 行为字节级一致
- [ ] `pytest src/tests` 全量绿
- [ ] 5 份文档同步完成
- [ ] BACKLOG 状态更新至 Done
- [ ] 日志脱敏验证：不打印 spec body、不打印认证头

---

## 13. 风险与红线

- 🚫 **禁止新增整型错误码**（F012 范式不可破）
- 🚫 **禁止 hardcode** N/M，必须走 `app/config.py`
- 🚫 **禁止回滚已成功落库的用例**（Q7：单文档失败不影响其它文档）
- 🚫 **禁止覆盖时级联删除 TestResult**（AI_RULES §6 可追溯）
- 🚫 **禁止修改 model.py**（零 schema 改动）
- 🚫 **禁止引入新框架**
- 🚫 **禁止忽略鉴权 / 日志 / 测试 / 文档任一项**（AI_RULES §16）
