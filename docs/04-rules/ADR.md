# ADR：架构决策记录

> ADR（Architecture Decision Record）用于记录关键技术和架构决策。  
> 新增核心技术、改变架构边界或扩大 MVP 范围时，必须补充 ADR。

---

## ADR-001：当前阶段只做 API 自动化测试平台

- 状态：Accepted
- 日期：2026-07-10

### 背景

原始设想包含 API 测试、UI 自动化、AI、RAG、CI/CD、分布式执行等能力，范围过大，容易导致 MVP 失焦。

### 决策

当前阶段只做 API 自动化测试平台 MVP，闭环为：

```text
认证登录 → 项目管理 → 环境管理 → API 用例管理 → 执行测试 → 查看报告
```

### 影响

- 暂不实现 UI 自动化、AI、RAG、分布式执行。
- 文档和代码优先围绕 API 测试闭环组织。
- 后续能力必须进入 Roadmap，不能直接塞入 MVP。

---

## ADR-002：采用单体 FastAPI 分层架构

- 状态：Accepted
- 日期：2026-07-10

### 背景

MVP 业务复杂度不高，核心是用例管理、执行和报告，不需要微服务或复杂网关。

### 决策

采用单体 FastAPI 后端，按以下分层：

```text
Router → Service → Repository → Database
```

### 影响

- 开发和部署简单。
- 业务边界仍通过模块目录保持清晰。
- 后续如需拆分执行器，可在 TestEngine 稳定后演进。

---

## ADR-003：MVP 使用进程内 API 执行器

- 状态：Accepted
- 日期：2026-07-10

### 背景

API 测试执行初期以手动触发、串行或有限并发为主，引入 Celery/MQ 会增加复杂度。

### 决策

MVP 中 API 执行器运行在 FastAPI 后端进程内，使用 httpx 发送请求。

### 影响

- 交付更快，依赖更少。
- 必须设置请求超时。
- 暂不支持大规模分布式执行。

---

## ADR-004：先做平台内置报告，不强依赖 Allure

- 状态：Accepted
- 日期：2026-07-10

### 背景

MVP 首要目标是保存和查看执行结果，不是建设复杂报告系统。

### 决策

执行结果保存到数据库，通过平台接口查询报告。

### 影响

- 报告数据更容易和业务模型关联。
- Allure 可作为后续导出能力，不作为当前强依赖。

---

## ADR-005：禁止用户自定义脚本执行

- 状态：Accepted
- 日期：2026-07-10

### 背景

前置/后置脚本会带来远程代码执行、安全沙箱和维护成本。

### 决策

MVP 不支持用户提交 Python/JavaScript 脚本执行，只支持变量替换和规则化断言。

### 影响

- 安全风险降低。
- MVP 能覆盖大部分 API 回归测试场景。
- 复杂逻辑后续必须经过安全设计再评估。

---

## ADR-006：F014 单 Run 内采用 asyncio + Semaphore 有限并发

- 状态：Accepted
- 日期：2026-08-04

### 背景

F010 的 `TestRunner` 串行执行所有用例。在一个含几十到上百条用例
的项目级 Run 上，回归耗时随用例数线性增长，用户体验差。
BACKLOG §3 F014 要求提升执行效率，但显式排除分布式执行。

### 决策

F014 选择 **`asyncio.Semaphore(N) + asyncio.gather`** 作为并发模型：

* 并发粒度 = **单个 TestRun 内的多条 TestCase**。不做跨 Run 调度、
  不做多进程 worker、不做 Celery / Redis / MQ。
* 默认并发度由 `settings.TEST_RUN_MAX_CONCURRENCY`（4）控制；调用方
  可通过 `?concurrency=N`（1 ≤ N ≤ 64）在单次 Run 上覆盖。
* 非法值（≤0、>64）由 Router 在 422 阶段拒绝；绕过 Router 直接调
  Service 时的非法值由 `TestRunner.__init__` 静默回落为 1，不抛异常。
* SQLAlchemy `AsyncSession` 非协程安全，因此 ORM 读写由一把
  `asyncio.Lock` 串行化；HTTP 请求本身在锁外，并行度不受影响。
* `_execute_single` 内部已捕获所有已知异常；外层 `except Exception`
  作为 defensive net，确保一个 case 崩溃不影响其他 case。

### 影响

- 零新依赖：复用现有 `httpx.AsyncClient`。
- 零 DB 改动：沿用 F011 的 `api_test_runs` / `api_test_results` 表。
- 性能：并发度 N 下，N 个慢 case 的总耗时接近 `ceil(T / N) * case_cost`，
  对项目级回归（≥ 10 条 case）通常带来 ≥ 50% 墙钟下降。
- DB 写入仍是隐式串行瓶颈：如未来需要突破，可演进为 per-task session
  + 显式事务边界，但**不在 F014 范围**。
- 文档同步：`docs/02-design/ARCHITECTURE.md` §5 标注；`docs/01-product/F014_SPEC.md`
  为设计稿；`docs/05-test/ACCEPTANCE.md` §4.5 为验收条目；`docs/03-api/OPENAPI.yaml`
  同步 `?concurrency=` 参数；`docs/01-product/BACKLOG.md` 状态 Todo → Doing → Done。

---

## ADR-007：F015 报告导出采用 JSON + 自带 HTML 模板（不引入 Allure / 模板引擎）

- 状态：Accepted
- 日期：2026-08-04

### 背景

F010 / F011 已落地：所有 Run + Result 写库后，详尽报告只能走 API 查询。
用户需要"下载一份报告传阅 / 存档 / 贴 CI artifact"，这是 P1 增强能力。
BACKLOG §3 F015 说明："JSON / HTML 导出，Allure 可作为后续方向"。

两个明确约束：
* PRD §7：当前阶段不做 "Allure 静态站点托管"。
* AI_RULES §4.4：暂缓技术中 "Allure 服务化：当前先做平台内置报告"。
* AI_RULES §15：未经 ADR 批准不得引入新框架。

### 决策

F015 选择 **JSON + 自带 HTML 模板**，不引入 Allure / jinja2 / mako / weasyprint：

* **JSON**：包含 Run 元信息 + 每条 Result 的 `request_snapshot` /
  `response_snapshot` / `assertions_snapshot`（后两者让用户离线复现
  请求/响应/断言，呼应 PRD §5.8 "结果详情"）。
* **HTML**：纯 Python f-string + 行内 CSS + `esc()` 转义；只展示摘要
  （状态 / 路径 / 耗时 / error_message），不塞 request/response 明文，
  避免 HTML 体积爆炸 + XSS 风险。
* 错误码不新增：format 校验在 Router 层 `pattern` 拦下为 422，
  Run 不存在复用 `TestRunNotFoundException`（404），非 owner 复用
  F011 的 鉴权路径。
* **脱敏**：F015 对 `response_snapshot.headers` 走与 F010
  `_sanitize_headers` 同一套黑名单二次脱敏；`request_snapshot.headers`
  信任 F010 在持久化时已脱敏。F015 不重复脱敏 request，避免意外变动业务字段。

### 影响

- 零新依赖（requirements.txt 不变），零 DB Migration，零 frontend 改动。
- 零新错误码，错误语义仍走 FastAPI 标准 422/404/403/401。
- 报告脱敏纵深防御：F010 防持久化层泄露，F015 防导出层泄露。
- 文档同步：`docs/01-product/F015_SPEC.md` 设计稿；`docs/05-test/ACCEPTANCE.md`
  §F015 验收条目；`docs/03-api/OPENAPI.yaml` `/runs/{run_id}/export` 端点。
- 后续 Allure 服务化（需独立 ADR）不在 F015 范围。

---

## ADR-008：F021 SchemaModel 数据契约 + 复合 schema 归一策略

- 状态：Accepted
- 日期：2026-08-20

### 背景

当前 F012 parser（`src/app/domain/openapi_importer/parser.py`）的输出
是 `Operation` + `ParsedSpec`，仅提取 `example` / `description` /
operation 级 `parameters` 与 `requestBody.content."application/json".example`。
这个最小信息量足以支撑 F012 的"1 条 happy path"用例生成，但**不足以**
驱动更深层的"自动测试生成"链路：

* F022 Test Design Engine 需要知道每个字段的 `type / format / minimum /
  maximum / minLength / maxLength / pattern / enum / required / default`，
  才能产出"边界值"、"enum 全覆盖"、"format 校验失败"等 `TestIntent`。
* F023 Test Generator 需要响应 schema 的 `required` 字段列表，才能产出
  `json_path` 断言（目前只有默认 `status_code` 一条）。
* F021 必须**向后兼容**现有 F012/F013 契约：F012 老路径产出 1 条 happy path
  + 1 个 status_code 断言必须**字节级一致**。

同时有两个不兼容增强必须决策：

1. **`$ref` 完整解析 vs 仅取首个分支**：
   F012 parser 当前实现的是"取首个分支"的简化版（`_resolve_refs` 仅
   处理 `$ref` 占满整个 dict 的形态，递归走 `components.schemas`）。当
   SchemaModel 需要 `type/format/enum/required` 完整信息时，"取首个分支"
   会丢失其他分支的语义；"完整递归解析"则会引入递归深度控制、循环引用
   检测等复杂度。
2. **oneOf / anyOf / allOf 归一策略**：
   OpenAPI 复合 schema 三种形态语义差异极大（`oneOf` 互斥、`anyOf` 至少
   一、`allOf` 全合并），parser 当前**直接忽略**（fall back 到原始 dict）。
   F021 必须给出明确归一规则。

### 决策

F021 引入 **`SchemaModel`** 数据契约，作为 parser 与下游 Test Design /
Generator 之间的稳定中间表示。三条核心决策如下：

**决策 1（OpenAPI 版本）：保持 3.x 单版本，不兼容 Swagger 2.0。**

* parser 现状 `version.startswith("3.")` 继续生效；Swagger 2.0（`swagger: "2.0"`）
  显式抛 `OpenApiParseError`。
* 后续若需 2.0 兼容，必须独立 ADR 决议；当前**不做**。

**决策 2（`$ref` 解析策略）：完整递归解析，递归深度上限 `MAX_REF_DEPTH = 10`，循环引用检测。**

* 解析顺序：先扁平化所有 `$ref`（resolve 链：`#/components/schemas/X` →
  `components.schemas["X"]` → 继续 resolve 内部 `$ref`），然后构造
  SchemaModel 节点。
* 深度上限：超过 `MAX_REF_DEPTH` 抛 `OpenApiParseError("ref depth exceeded")`。
* 循环检测：用 `id(node)` 集合，命中已访问节点 → 用占位 `RefCycle` 标记
  并停止该分支递归（**不抛异常**，因为 OpenAPI 规范允许循环结构用于递归类型）。
* 与 F012 的兼容性：F012 老路径**仅消费** SchemaModel 的
  `example / description / operation_id` 等"语义保持"字段，新字段缺失
  时降级为 `None / [] / {}`，确保 F012 happy path 行为**字节级不变**。

**决策 3（oneOf / anyOf / allOf 归一）：取首个分支 + `unresolved_branches` 字段标注。**

* `oneOf` / `anyOf`：取列表中**第一个** dict 作为归一目标；其余分支写入
  `unresolved_branches: list[SchemaModel]`，供下游 UI 提示"F021 未完整建模此复合类型"。
* `allOf`：把所有分支 **merge**（浅合并：同名字段后者覆盖前者；`type` 冲突
  抛 `OpenApiParseError`；`required` 数组合并去重）。
* 默认行为：**取首个分支**（与 F012 parser 现状"取首个分支"的简化语义
  **向前兼容**，不引入新错误码；仅在 `unresolved_branches` 非空时通过日志
  WARNING 告知）。
* 后续如需"完整分支展开"，必须独立 ADR 决议。

**决策 4（依赖）：不引入 jsonschema / openapi-spec-validator 等第三方库。**

* 解析、约束、归一全部走 stdlib + Pydantic v2 + 类型标注；
* 沿用 F012 的 `_resolve_refs` 风格扩展（纯函数递归）。
* 第三方 schema 库带来的学习成本 / 版本耦合 / 冗余字段**不值得**。

**决策 5（数据契约 SchemaModel）：Pydantic v2 `BaseModel`，`extra="forbid"`。**

* 顶层节点：`SchemaModel(type, format, enum, const, default, description, ref, ...)`
* 复合节点：`one_of: list[SchemaModel]` / `any_of: list[SchemaModel]` /
  `all_of: list[SchemaModel]` / `unresolved_branches: list[SchemaModel]`
* 数值节点：`minimum, maximum, exclusive_minimum, exclusive_maximum, multiple_of`
* 字符串节点：`min_length, max_length, pattern`
* 数组节点：`min_items, max_items, unique_items, items: SchemaModel`
* 对象节点：`properties: dict[str, SchemaModel]`, `required: list[str]`,
  `additional_properties: bool | SchemaModel`

### 影响

- **新增模块**：`src/app/domain/openapi_importer/schema_model.py`（数据契约）
  + `src/app/domain/openapi_importer/schema_analyzer.py`（分析器实现）；
  既有 `parser.py` **不动**。
- **向后兼容**：F012 parser 输出 `Operation` / `ParsedSpec` 字段保持；
  SchemaModel 是**增量可选消费**——老路径不读 SchemaModel，新路径按需
  `analyze_operation(op) -> SchemaModel` 调用。
- **零新依赖**：纯 stdlib + Pydantic v2（已是项目栈）。
- **零 DB Migration / 零 model.py 改动**。
- **零新错误码**：解析失败沿用 F012 的 `OPENAPI_PARSE_ERROR`（已在 400 范式）；
  仅在 `MAX_REF_DEPTH` 越界时复用同一错误码 + `details: {reason: "ref_depth"}`。
- **日志脱敏**：WARNING 日志只输出 `doc_index / source_tag / unresolved_branches count`，
  **不打印** spec body / 认证头（与 F012 parser 一致）。
- **文档同步**：`docs/01-product/F021_SPEC.md` 设计稿；
  `docs/05-test/ACCEPTANCE.md` §F021 验收条目；
  `docs/03-api/OPENAPI.yaml` 不变（SchemaModel 是内部数据契约，非 API 暴露）；
  `docs/01-product/BACKLOG.md` F021 状态 Todo → Doing → Done。
- **测试**：新增 `src/tests/test_schema_analyzer.py`（≥15 用例），覆盖
  $ref 深度 / 循环 / oneOf / anyOf / allOf / required / enum / boundary /
  format / 向后兼容 F012 等。
- **回归**：F012/F013 现有 32 个测试**字节级**不变。

### 备选方案（已否决）

* **方案 A（不引入 SchemaModel，直接在 Operation 上加字段）**：会污染
  F012 既有数据契约，破坏"零修改 parser"承诺。
* **方案 B（用 jsonschema 库做归一）**：依赖膨胀、版本耦合、对 OpenAPI
  复合 schema 语义无增强。
* **方案 C（完整展开 oneOf/anyOf/allOf 所有分支）**：复杂度爆炸（N 个
  oneOf 分支 × M 个 anyOf 分支），与 AI_RULES §2.3 KISS 冲突。

---

## ADR 模板

```text
## ADR-xxx：标题

- 状态：Proposed / Accepted / Deprecated
- 日期：YYYY-MM-DD

### 背景

为什么需要做这个决策？

### 决策

最终选择是什么？

### 影响

带来的收益、代价和后续影响。