# 系统架构设计

> 范围：API 自动化测试平台 MVP。  
> 原则：单体优先、分层清晰、结果可追溯，不为未来能力提前引入复杂组件。

---

## 1. 架构目标

当前系统只需要支撑一个核心闭环：

```text
管理 API 测试资产 → 执行 HTTP 请求 → 执行断言 → 保存结果 → 查看报告
```

架构目标：

- 简单：MVP 不引入消息队列、分布式调度、AI Agent。
- 稳定：核心数据持久化到 PostgreSQL。
- 可维护：遵循 Router → Service → Repository → Database。
- 可测试：变量替换、断言、执行统计可单独测试。
- 可追溯：每次执行保存请求、响应和断言快照。

---

## 2. 总体架构

```text
┌──────────────────────────────────────────────┐
│                  User / Browser              │
│       React UI 或 FastAPI Swagger UI          │
└───────────────────────┬──────────────────────┘
                        │ HTTP JSON / JWT
                        ▼
┌──────────────────────────────────────────────┐
│                 FastAPI Backend              │
│                                              │
│  Router / Controller                         │
│        ↓                                     │
│  Service                                     │
│        ↓                                     │
│  Repository                                  │
│        ↓                                     │
│  SQLAlchemy ORM                              │
│                                              │
│  API Test Engine                             │
│   ├─ Variable Resolver                       │
│   ├─ Request Builder                         │
│   ├─ HTTP Executor (httpx) ───▶ Target APIs   │
│   └─ Assertion Engine                        │
└───────────────────────┬──────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│                 PostgreSQL                   │
│ users / roles / projects / cases / runs      │
└──────────────────────────────────────────────┘
```

---

## 3. 分层职责

### 3.1 Router / Controller

职责：

- 定义 REST API。
- 接收请求和参数校验。
- 获取当前用户上下文。
- 调用 Service。
- 返回统一响应。

禁止：

- 直接操作数据库。
- 编写 API 测试执行逻辑。
- 编写复杂业务判断。

### 3.2 Service

职责：

- 承载业务规则。
- 校验权限和资源归属。
- 编排 Repository、执行器、断言引擎。
- 处理业务异常。

典型 Service：

- `AuthService`
- `UserService`
- `RoleService`
- `ProjectService`
- `EnvironmentService`
- `CollectionService`
- `TestCaseService`
- `TestRunService`

### 3.3 Repository

职责：

- 封装数据库查询。
- 隔离 SQLAlchemy 细节。
- 提供面向业务的读写方法。

### 3.4 API Test Engine

| 组件 | 职责 |
|------|------|
| `VariableResolver` | 替换 `{{variable}}` 和内置变量 |
| `RequestBuilder` | 合并环境和用例，构造请求 |
| `ApiExecutor` | 使用 httpx 发送 HTTP 请求 |
| `AssertionEngine` | 执行规则化断言 |
| `ResultRecorder` | 保存结果并更新统计 |
| `ReportExporter` | F015：报告导出（`app/domain/test_run/exporter.py`）。输出 JSON / HTML；复用 F010 `_sanitize_headers` 对 response_snapshot.headers 二次脱敏 |

---

## 4. 模块边界

### 4.1 支撑模块

| 模块 | 说明 |
|------|------|
| Auth | 登录、刷新 Token、退出、当前用户 |
| User | 用户信息、状态、修改密码 |
| Role | 简单 RBAC |

### 4.2 核心模块

| 模块 | 说明 |
|------|------|
| Project | API 测试资源边界 |
| Environment | Base URL、Headers、Variables |
| Collection | 用例分组 |
| TestCase | 请求定义和断言配置 |
| TestRun | 一次执行批次 |
| TestResult | 单条用例执行结果 |

---

## 5. 核心执行流程

```text
用户触发执行
  ↓
校验项目、环境、用例和权限
  ↓
创建 TestRun，状态 running
  ↓
查询待执行 TestCase
  ↓
逐条执行：
  1. 合并变量上下文
  2. 替换变量
  3. 构造 HTTP 请求
  4. 发送请求并记录耗时
  5. 执行断言
  6. 保存 TestResult
  ↓
汇总统计
  ↓
更新 TestRun 状态
  ↓
返回执行报告
```

> **F014 有限并发**：从 F014 开始，`逐条执行` 改为 `受控并发执行`——`TestRunner` 使用 `asyncio.Semaphore(N)` + `asyncio.gather` 在进程内限流，默认 `N=settings.TEST_RUN_MAX_CONCURRENCY`（4）。SQLAlchemy `AsyncSession` 读写由一把 `asyncio.Lock` 串行化保证 ORM 安全，HTTP 请求本身在锁外真正并行。调用方可过 `POST /projects/{pid}/runs?concurrency=N`（1≤N≤64）覆盖默认值。详见 `docs/01-product/F014_SPEC.md` 与 `docs/04-rules/ADR.md` ADR-006。
>
> **F015 报告导出**：从 F015 开始，用户可过 `GET /runs/{run_id}/export?format=json|html` 下载报告。`ReportExporter` (`app/domain/test_run/exporter.py`) 输出 JSON（含 request/response/assertions 三件套，response.headers 二次脱敏）与自包含 HTML（行内 CSS + `esc()` XSS 防护）。**不引入 Allure / jinja2 / mako / weasyprint**（呼应 PRD §7 + AI_RULES §4.4 / §15）。详见 `docs/01-product/F015_SPEC.md` 与 `docs/04-rules/ADR.md` ADR-007。

---

## 6. 前端工作区（F016）

**选型**（已锁定，呼应 AI_RULES §4.4）：

| 层 | 库 | 职责 |
|----|----|------|
| UI 框架 | React 18 + Vite 5 + TypeScript 5.5 | SPA + HMR |
| 路由 | React Router 6 | 14 个路由（含 6 个 legacy 重定向） |
| UI 库 | Ant Design 5 + Ant Design Icons | 组件库（Form / Table / Drawer / Modal / Tabs） |
| 服务端状态 | TanStack Query 5 | 列表 / 详情 / mutation；`queryKeys` factory 统一管理 |
| 客户端状态 | Zustand 4 | 仅 `store/auth.ts`（token + user） |
| HTTP | Axios 1.7 | 拦截器：401 自动 refresh + Bearer 注入 |
| 表单 | React Hook Form 7 | 5 个 FormModal + CaseEditor |

**路由架构**：

```text
/login                                                    公开
/dashboard                                                ProtectedRoute
/projects                                                 ProtectedRoute
/projects/:projectId/workspace/                           ProtectedRoute (ProjectWorkspaceLayout)
├── overview                                              项目概览
├── environment                                           环境 CRUD
├── suite / suite/:suiteId                                集合 CRUD + 顺序
├── case / case/new / case/:caseId                        用例 CRUD + 启用/禁用
├── run                                                   执行中心（含 F014 concurrency）
├── report / report/:runId / result/:resultId             报告详情 + F015 导出
├── import / import/:suiteId                              OpenAPI 导入（F012/F013）
└── information                                           项目信息
/admin/users, /admin/roles                                AdminRoute 守卫
/403, * (catch-all)                                      系统错误页
```

**鉴权**：
* `ProtectedRoute` 包裹 `<AppShell>` 拦截未登录 → `/login`
* `AdminRoute` 包裹 admin 页 → 非 admin 跳 `/403`
* Axios 拦截器：401 自动用 refresh token 续签；续签失败跳 `/login`
* Token 存 `localStorage`（`access_token` / `refresh_token`）

**P1 集成点**：

| Feature | 前端入口 | 后端 API |
|---------|---------|---------|
| F012 OpenAPI 导入 | `WorkspaceImportIndex` / `WorkspaceImport` | `POST /projects/{pid}/suites/{sid}/import/openapi?dry_run=true` |
| F013 批量导入 | 同上 + `?batch=true` + `documents[]` | 同上 |
| F014 并发度 | `WorkspaceRun` Slider + InputNumber（1-64） | `POST /projects/{pid}/runs?concurrency=N` |
| F015 报告导出 | `WorkspaceReportDetail` 「导出报告」Dropdown | `GET /runs/{run_id}/export?format=json\|html`（axios blob 下载） |

**不做**：
* 不引入前端自动化测试（Cypress / Playwright / Vitest+RTL）—— KISS
* 不引入 i18n / 暗色模式 / WebSocket / PWA / 离线
* 不切 UI 库（已锁 Ant Design）；不引入 Redux / MobX（已选 Zustand）

详见 `frontend/README.md`。

---

## 7. 技术选型

| 技术 | 用途 | 说明 |
|------|------|------|
| Python 3.12 | 后端语言 | 与项目规则一致 |
| FastAPI | Web 框架 | 自动 OpenAPI，类型友好 |
| Pydantic v2 | 数据校验 | 请求/响应 Schema |
| SQLAlchemy 2.x | ORM | 数据访问 |
| Alembic | 迁移 | 数据库版本管理 |
| PostgreSQL | 主数据库 | 持久化和 JSON 支持 |
| httpx | HTTP 客户端 | 执行被测 API |
| pytest | 测试 | 单元测试和 API 测试 |
| React 18 + Vite 5 | 前端 | 管理界面（F016） |
| Ant Design 5 | 前端 UI 库 | 组件库（F016） |
| TanStack Query 5 | 前端 server state | 列表 / 详情 / mutation（F016） |
| Zustand 4 | 前端 client state | 仅 `store/auth.ts`（F016） |

---

## 8. 当前不引入

| 能力 | 暂缓原因 |
|------|----------|
| 消息队列 | 当前手动触发和串行执行即可 |
| 分布式执行 | MVP 不需要横向扩容执行器 |
| AI / RAG | 不属于 API 测试最小闭环 |
| 定时任务 | 先完成手动执行闭环 |
| Allure 服务化 | 先做平台内置报告 |
| 前端自动化测试 | KISS：项目不引入 vitest+RTL / Cypress / Playwright |
