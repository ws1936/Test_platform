# 功能待办列表 Backlog

> 范围：API 自动化测试平台 MVP 及后续演进。  
> 用途：统一记录功能项、优先级和当前状态，作为开发排期入口。

---

## 1. 状态说明

| 状态 | 说明 |
|------|------|
| Todo | 待开发 |
| Doing | 开发中 |
| Done | 已完成 |
| Blocked | 阻塞 |
| Later | 后续再做 |

---

## 2. 优先级说明

| 优先级 | 说明 |
|--------|------|
| P0 | MVP 必须完成，影响 API 测试闭环 |
| P1 | MVP 后增强能力，提升效率或体验 |
| P2 | 中长期能力，当前不进入 MVP |

---

## 3. 功能 Backlog

| ID | Feature | 优先级 | 状态 | 说明 |
|----|---------|--------|------|------|
| F001 | 用户登录 | P0 | Done | 已具备登录、JWT 鉴权能力 |
| F002 | 用户管理 | P0 | Done | 已具备基础用户 CRUD、禁用、改密码能力 |
| F003 | 角色管理 | P0 | Done | 已具备基础角色 CRUD，后续可完善细粒度权限 |
| F004 | 项目管理 | P0 | Done | API 测试项目 CRUD + owner/superuser 鉴权 + 跨用户隔离 |
| F005 | 环境管理 | P0 | Done | Base URL、Headers、Variables、默认环境（单项目唯一 + 默认互斥 + 默认不可删除） |
| F006 | 集合管理 | P0 | Done | Suite CRUD + 批量添加用例（事务 + 幂等 + 默认排序 + 项目内唯一 + owner 鉴权） |
| F007 | API 用例管理 | P0 | Done | 用例 CRUD + 启用/禁用 + 套件/项目双维度列表 + owner 鉴权 + suite_cases 级联清理 |
| F008 | 变量替换 | P0 | Done | `${var}` 占位符替换 + `${timestamp}` 内置变量 + 缺失变量保留占位 + WARNING + 调用方控制合并优先级（无 Router/DB） |
| F009 | 断言引擎 | P0 | Done | 5 种断言 × 12 个操作符规则化引擎 + 集成 F008 变量替换 + 手写 json_path + RFC7230 header 大小写不敏感 + 错误码 31003/31004/31005（无 Router/DB） |
| F010 | pytest / API 执行 | P0 | Done | httpx 同步执行 + RequestBuilder/ApiExecutor/TestRunner 引擎 + 6 个 HTTP 端点 + 错误码 32001/32002/32003 + 敏感头脱敏 + 64KB body 截断 + 复用 F008/F009（无 Celery/Redis） |
| F011 | 测试报告 | P0 | Done | 3 个聚合端点（单 run 概览 / 项目级概览 / 失败原因列表）+ TestRunResponse 新增 pass_rate/elapsed_seconds 计算字段 + list_project_runs 加 status 过滤 + 无新表（复用 F010 表） |
| F012 | Swagger / OpenAPI 导入 | P1 | Done | 从 OpenAPI 3.x 文档生成基础 API 用例 + stdlib 解析 + 1 个 POST 端点（?dry_run=true） + 复用 F006/F007 零新表 |
| F013 | 批量生成基础用例 | P1 | Done | 已具备基于 F012 的批量：多 OpenAPI 文档一次提交 + `?batch=true`/两段式 `?dry_run` 流转 + `on_conflict`（skip / overwrite）+ 每文档独立错误隔离 + N=5 文档 / M=50 operation 配置上限 + 1 个新错误码 `OPENAPI_BATCH_LIMIT_EXCEEDED`。跨请求进程内 preview_cache 共享（修复 F012 latent）。零新表、零 Alembic migration、不动 model.py。设计稿 `docs/01-product/F013_SPEC.md`，验收条目 `docs/05-test/ACCEPTANCE.md §4.4`，测试覆盖 T1–T13（32 个 openapi_importer 测试全绿） |
| F014 | 有限并发执行 | P1 | Done | `TestRunner` 进程内 `asyncio.Semaphore` 限流 + Router `?concurrency=` 可选入参（1≤N≤64，默认 `settings.TEST_RUN_MAX_CONCURRENCY=4`）；并发下计数器一致、异常隔离、`_execute_single` 未异常覆盖其他 case；零 DB Migration、零新依赖。设计稿 `docs/01-product/F014_SPEC.md`，ADR `docs/04-rules/ADR.md` ADR-006，验收条目 `docs/05-test/ACCEPTANCE.md` §4.5，测试 `test_runner_concurrency.py`(8) + `test_test_run_concurrency_param.py`(9) 全绿 |
| F015 | 报告导出 | P1 | Done | `GET /runs/{run_id}/export?format=json|html` 端点 + `exporter.py` 独立模块：JSON 含 Run 元信息 + 每条 Result 的 request/response/assertions 完整快照（response.headers 走 F010 `_sanitize_headers` 二次脱敏）；HTML 自包含模板（f-string + 行内 CSS + `esc()` XSS 防护）。**不做 Allure / jinja2 / mako / weasyprint**（呼应 PRD §7 + AI_RULES §4.4 / §15）。设计稿 `docs/01-product/F015_SPEC.md`，ADR `docs/04-rules/ADR.md` ADR-007，验收条目 `docs/05-test/ACCEPTANCE.md` §F015，测试 `test_test_run_export.py` 17/17 全绿（含 4 个新增脱敏 + 完整快照测试），全量 424/424 0 回归 |
| F016 | 前端 API 测试页面 | P1 | Done | 完整前端（React 18 + Vite + Ant Design + TanStack Query + Zustand + React Hook Form）：14 个路由 / 12 个 workspace 页面 / 9 个 API 客户端 / Zustand auth store / TanStack Query 全覆盖 / `ProtectedRoute` + `AdminRoute` 鉴权守卫。本次加固：F014 `?concurrency=` 在 `WorkspaceRun` 暴露（Slider + InputNumber 1-64）；F015 报告导出在 `WorkspaceReportDetail` 暴露（Dropdown + `runsApi.exportReport` axios blob 下载）；修复 1 处 lint warning（`useMemo` 包裹 `linked`）。`npm run check`（lint + typecheck + build）全绿，零前端自动化测试（KISS）。前端 `frontend/README.md` 已建；验收条目 `docs/05-test/ACCEPTANCE.md` §F016；架构标注 `docs/02-design/ARCHITECTURE.md` §8 前端工作区。零 DB Migration、零新依赖、零后端改动 |
| F017 | 定时执行 | P2 | Later | 当前不进入 MVP，待执行闭环稳定后评估 |
| F018 | 消息通知 | P2 | Later | 企业微信、钉钉、邮件等通知能力 |
| F019 | CI/CD Webhook | P2 | Later | 与流水线集成触发或回传结果 |
| F020 | AI 生成 Case | P2 | Later | 基于接口定义生成测试用例，需安全和数据治理评估。Phase 4 候选，受 AI_RULES §1 / §4.4 约束 |
| F021 | Schema Analyzer（OpenAPI Schema 深度模型） | P1 | Done | 7 阶段流程图第 2 步：SchemaModel 数据契约（Pydantic v2 + extra="forbid"）覆盖 type/format/minimum/maximum/minLength/maxLength/pattern/enum/required/default + oneOf/anyOf/allOf 归一 + `$ref` 完整递归解析（深度上限 10）+ 循环检测（RefCycle 占位）。`SchemaAnalyzer` 5 个公共方法 + `Operation` 新增 3 个 Optional 字段（向后兼容）。新增 `src/app/domain/openapi_importer/schema_model.py` + `schema_analyzer.py`，新增 `src/tests/test_schema_analyzer.py`（33 个测试全绿）。F012/F013 现有 32 个测试零退化，全量 457/ 0 回归。设计稿 `docs/01-product/F021_SPEC.md`，ADR `docs/04-rules/ADR.md` ADR-008，零新表、零 model.py 改动、零新依赖、零新错误码 |
| F022 | Test Design Engine（策略化用例设计） | P1 | Done | 7 阶段流程图第 3 步：`TestDesignEngine` 编排 6 个策略（happy_path / required_field_missing / enum_coverage / boundary_min_max / format_invalid / auth_missing），输入 `EndpointSchema`，输出 `TestIntent[]`（Pydantic v2 extra="forbid"）。默认行为字节级 = F012（仅 happy_path=True）；其他策略默认关闭。启动校验 `strategy_*_max_per_op ≤ generator_max_intents_per_operation`。单策略截断 + WARNING + 硬截（按 happy_path > required > enum > boundary > format > auth 优先级）。`app/config.py` 增量 13 配置项 + `validate_strategy_caps()`。新增 `src/app/domain/test_design/`（10 个文件）+ `src/tests/openapi_factories.py`（8 工厂函数）+ `src/tests/test_test_design.py`（23 个测试 T1–T20 + extras）。F012/F013/F021 现有 65 个测试零退化，全量 480/ 0 回归。设计稿 `docs/01-product/F022_SPEC.md` + 前置规划 `docs/01-product/F022_PRECHECK.md`，零新表、零 model.py 改动、零新依赖、零新错误码（HTTP 错误码属 F023 ADR-009） |
| F023 | Test Generator（消费 Intent 生成用例） | P1 | Todo | 7 阶段流程图第 4 步：把 TestIntent 转为 `TestCaseCreateRequest`。扩展 F012/F013 的 service 层：增加 `?design=schema`（策略驱动）/ `?design=simple`（沿用 F012 happy path）切换；自动生成多类型断言：status_code / json_path（基于 response schema required 字段）/ header（content-type 等）。配置项 `GENERATOR_MAX_INTENTS_PER_OPERATION=20`，越界返回 422 `GENERATOR_INTENT_LIMIT_EXCEEDED`。复用 F012/F013 端点 + 协议。**开始前需先写 ADR-009**（错误码 / 配置项 / `?design=schema` 语义） |
| F024 | 导入向导 v2（前端子子集 + 预览增强） | P1 | Todo | 7 阶段流程图 4 步配套 UI：`WorkspaceImport.tsx` 增加策略多选（Checkboxes：happy_path / required_field_missing / enum_coverage / boundary / format / auth）+ Preview 面板显示每条 intent 的 name/description（不再是仅 method+path），允许单条勾选/取消后再 commit。前端 `frontend/src/api/openApiImport.ts` 增加 `previewSchema` / `commitSchema` 两个方法。零后端改动在 F024 内仅前端 |
| F025 | 报告断言回放 + 失败智能归因 | P2 | Later | 7 阶段流程图最后两步增强：基于 schema_diff 对比"本次响应 vs 上一次通过响应"定位可疑字段；仍属规则化（F009 断言引擎扩展），不属于 AI。Phase 4 后再评估与 F020 的关系 |

---

## 4. 当前 MVP 开发顺序建议

```text
F004 项目管理
  ↓
F005 环境管理
  ↓
F006 集合管理
  ↓
F007 API 用例管理
  ↓
F008 变量替换
  ↓
F009 断言引擎
  ↓
F010 pytest / API 执行
  ↓
F011 测试报告
```

---

## 5. 「OpenAPI → 自动测试生成」流程拆解（F021 + F022 已 Done）

> 把当前 F012/F013 的"OpenAPI 文档 → 1 条 happy path 用例"升级为 7 阶段闭环（基于 AI_RULES §1 / §4.4 暂缓 AI 的前提下，全部 spec 驱动）。

### 5.1 阶段映射

| 阶段 | 现状 | 升级项 |
|------|------|--------|
| 1 OpenAPI Import | ✅ F012 + F013 已完成 | 不动 |
| 2 Schema Analyzer | ✅ F021 已完成 | 不动 |
| 3 Test Design Engine | ✅ F022 已完成 | 不动 |
| 4 Test Generator | ❌ 不存在 | F023：消费 Intent，输出多条 + 多类型断言 |
| 5 pytest | ✅ F010 | 不动 |
| 6 Execution | ✅ F010（同步/F014 并发） | 不动 |
| 7 Result | ✅ F011 + F015 | 不动 |

### 5.2 依赖关系

```text
F021 Schema Analyzer   [Done 2026-08-20]
   ↓
F022 Test Design Engine   [Done 2026-08-20]
   ↓
F023 Test Generator   [Todo]
   ↓
F024 导入向导 v2   [Todo]
```

> F021–F024 是 **P1 串行依赖链**：后一步依赖前一步的输出。F025 是 P2 Later，独立分支。

### 5.3 ADR 要求

- ✅ **ADR-008**（2026-08-20）：F021 SchemaModel 契约 + `$ref`/复合 schema 归一策略
- ⏳ **ADR-009**（F023 实施前）：F023 配置 `GENERATOR_MAX_INTENTS_PER_OPERATION` 默认值、错误码 `GENERATOR_INTENT_LIMIT_EXCEEDED` 是否新增
- F022 策略开关：已走 `app/config.py` 配置项，不必 ADR

### 5.4 红线（来自 AI_RULES）

- ❌ F021–F024 **不得引入 LLM / RAG / 第三方 schema 库**（纯 stdlib + Pydantic v2）
- ❌ F021–F024 **不得新增业务表 / 修改 model.py**
- ❌ F021–F024 **不得破坏 F012/F013 现有契约**（`?design=simple` 必须字节级 = F012 行为）
- ✅ 可新增 Pydantic Schema、配置项、模块文件、独立测试

### 5.5 验收标准（每个 Feature 必须）

- 单元测试覆盖核心策略与边界
- API 测试覆盖主要 happy / 422 / 403 / 401 / 404 路径
- 与 F012/F013 的全量测试（32 个）无回归
- 文档同步：`Fxxx_SPEC.md` + `ACCEPTANCE.md §Fxxx` + `OPENAPI.yaml` + `BACKLOG.md` 状态更新
- ADR（按需）
- 日志脱敏：禁止打印 spec body / 认证头

---

## 6. 维护规则

1. 新增功能必须先进入 Backlog。
2. P0 功能必须能支撑 API 测试最小闭环。
3. P1/P2 功能不得抢占 P0 开发顺序。
4. 状态变化需要同步更新本文件。
5. 扩大 MVP 范围必须补充 `docs/04-rules/ADR.md`。