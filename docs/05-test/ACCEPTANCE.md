# 验收标准

> 范围：API 自动化测试平台 MVP。  
> 验收目标：确认平台完成 API 测试最小闭环。

---

## 1. 总体验收标准

MVP 完成时必须满足：

- 用户可以登录系统。
- 管理员可以管理用户和角色。
- 测试工程师可以创建 API 项目。
- 测试工程师可以配置环境。
- 测试工程师可以创建集合和 API 用例。
- 用例可以引用变量。
- 用例可以配置断言。
- 平台可以执行单用例、集合、项目。
- 平台可以保存执行结果。
- 报告可以展示请求、响应、断言和失败原因。

---

## 2. 认证验收

- [ ] 正确账号密码可以登录。
- [ ] 错误账号密码返回 401。
- [ ] 登录成功返回 Access Token 和 Refresh Token。
- [ ] Access Token 可以访问受保护接口。
- [ ] Refresh Token 可以刷新 Access Token。
- [ ] 退出登录后当前 Token 失效。
- [ ] 禁用用户不能登录。
- [ ] 修改密码后旧密码不能登录。

---

## 3. 用户与角色验收

- [ ] 管理员可以查看用户列表。
- [ ] 管理员可以查看用户详情。
- [ ] 管理员可以更新用户状态和角色。
- [ ] 管理员可以管理角色。
- [ ] 非管理员不能执行管理操作。
- [ ] 接口响应不返回 `hashed_password`。

---

## 4. API 测试资产验收

### 4.1 项目

- [ ] 可以创建项目。
- [ ] 可以查询项目列表和详情。
- [ ] 可以更新项目。
- [ ] 可以删除项目或禁用项目。

### 4.2 环境

- [ ] 可以创建环境。
- [ ] 环境包含 `base_url`、`headers`、`variables`。
- [ ] 同一项目下环境名称不可重复。
- [ ] 可以设置默认环境。

### 4.3 集合与用例

- [ ] 可以创建集合。
- [ ] 可以创建 API 用例。
- [ ] 用例支持 GET、POST、PUT、PATCH、DELETE。
- [ ] 用例支持 headers、query、body。
- [ ] 用例支持断言配置。
- [ ] 用例支持启用/禁用。

### 4.4 OpenAPI 导入与批量生成（F012 + F013）

- [ ] 可以从 OpenAPI 3.x 文档（URL 或 JSON 内容）预览生成基础 API 用例（F012 `dry_run=true`）。
- [ ] 可以消费 `preview_id` 真创建用例，默认 `on_conflict=skip`，可选 `overwrite`。
- [ ] 可以一次提交多份 OpenAPI 文档（F013 `?batch=true&documents[]`）并生成全部基础用例。
- [ ] 单文档失败不影响其它文档正常落库（F013 失败隔离）。
- [ ] 越过 `OPENAPI_BATCH_MAX_DOCS`（默认 5）或 `OPENAPI_BATCH_MAX_OPS_PER_DOC`（默认 50）返回业务码 `OPENAPI_BATCH_LIMIT_EXCEEDED`。
- [ ] `documents[]` 与单文档字段同传返回 422，互斥校验在请求模型层生效。
- [ ] 覆盖（`on_conflict=overwrite`）时旧用例历史 `TestResult` 保留可追溯，不级联删除。
- [ ] 非项目 owner / admin 调用 → 403；项目/套件不存在 → 404；缺 token → 401。
- [ ] 敏感头（`Authorization` / `Cookie` 等）在解析/落库过程中不被写入日志。
- [ ] 零 DB 改动、零 Alembic migration、不动 model.py。

### 4.5 有限并发执行（F014）

- [ ] 单 Run 内多条 TestCase 在 `TestRunner` 进程内以 `asyncio.Semaphore` 限流并发执行；默认 `settings.TEST_RUN_MAX_CONCURRENCY=4`。
- [ ] `?concurrency=N` 传入合法范围 `1 ≤ N ≤ 64` 时，`TestRunner` 收到的 `max_concurrency` 等于 N。
- [ ] `?concurrency=0` / `?concurrency=200` 在 Router 层返回 422，runner 不被调用。
- [ ] 不传 `?concurrency=` 时，Service 透传 `None`，runner 读 settings 默认值。
- [ ] `max_concurrency=1` 退化为串行（峰值并发 = 1）。
- [ ] `max_concurrency=N` 时实测峰值并发 ≤ N 且 ≥ 2（验证限流真生效）。
- [ ] 非法 `max_concurrency`（0 / 负数）回落为 1，不抛异常。
- [ ] 并发下 `passed + failed + error + skipped == total` 恒成立。
- [ ] `_execute_single` 抛未预期 `RuntimeError` 不中断 `gather`，其他 case 仍完成。
- [ ] 单 case 列表（size=1）的并发逻辑退化为普通执行。
- [ ] `POST /test-cases/{case_id}/run?concurrency=N` 接受对称参数（1 case 无并行语义，仅透传）。
- [ ] 零 DB Migration、零 Alembic 改动、零新依赖（requirements.txt 不变）。
- [ ] 敏感 header（`Authorization` / `Cookie` 等）和 response body 不写日志。
- [ ] 全量回归：`pytest src/tests/` 通过，0 回归。

### 4.6 报告导出（F015）

- [ ] `GET /runs/{run_id}/export?format=json` 返回 `application/json; charset=utf-8` + `Content-Disposition: attachment; filename="run-<时间戳>-<uuid>.json"`。
- [ ] `GET /runs/{run_id}/export?format=html` 返回 `text/html; charset=utf-8` + 同样 `attachment` 头；HTML 为自包含（行内 CSS，不依赖外链）。
- [ ] `format` 越界（如 `xml`）由 FastAPI `pattern` 校验返回 422。
- [ ] JSON 中 `run` 包含：id / name / scope / scope_id / status / total / passed / failed / error / skipped / started_at / finished_at / environment_id / project_id / triggered_by / pass_rate / elapsed_seconds。
- [ ] JSON 中 `results[]` 每条包含 request_snapshot / response_snapshot / assertions_snapshot 三个完整快照（脱敏后）。
- [ ] `response_snapshot.headers` 被 `_sanitize_headers` 二次脱敏：`Authorization` / `Cookie` / `Set-Cookie` / `x-api-key` 等不出现在导出中。
- [ ] `request_snapshot.headers` 保留 F010 在持久化时已脱敏的产物，F015 不再二次处理。
- [ ] HTML 表格不展示 request/response/assertion 明文，仅 case_name / case_method / case_path / elapsed_ms / error_message。
- [ ] HTML 中所有用户控制字段经 `esc()` 转义（XSS 防护）：`<` / `>` / `&` / `"` 分别转义为对应的 HTML entity。
- [ ] 端点鉴权：未登录 401；非 owner 非 admin 403；run 不存在 404。
- [ ] 不新增业务错误码（沿用 FastAPI 标准 422/404/403/401）。
- [ ] 零 DB Migration、零 Alembic 改动、零新依赖（requirements.txt 不变）。
- [ ] 全量回归：`pytest src/tests/` 通过，0 回归。

### 4.7 前端 API 测试页面（F016）

**注**：F016 不引入前端自动化测试（KISS + 零基础设施）。验收以"页面 / 路由 / 操作"清单为准，配合 `npm run check` 编译闸门。

**路由 / 页面**
- [ ] `/login` 登录页 + token 持久化 + 401 自动 refresh
- [ ] `/dashboard` 含 4 个 Recent*Panel + 指标卡
- [ ] `/projects` 项目列表 + 创建 / 编辑模态框
- [ ] `/projects/:projectId/workspace/overview` 项目概览
- [ ] `/projects/:projectId/workspace/environment` 环境 CRUD + 默认环境切换
- [ ] `/projects/:projectId/workspace/suite` + `/:suiteId` 集合 CRUD + 顺序调整
- [ ] `/projects/:projectId/workspace/case` + `/new` + `/:caseId` 用例 CRUD + 启用 / 禁用
- [ ] `/projects/:projectId/workspace/run` 执行中心（包含 F014 并发度 Slider）
- [ ] `/projects/:projectId/workspace/report` + `/:runId` + `result/:resultId` 报告详情
- [ ] `/projects/:projectId/workspace/import` + `/:suiteId` OpenAPI 导入（F012/F013）
- [ ] `/projects/:projectId/workspace/information` 项目信息
- [ ] `/admin/users` + `/admin/roles` 管理员页（AdminRoute 守卫）
- [ ] `/403` / `*`（catch-all 404）系统错误页

**P1 集成点**
- [ ] F014：执行中心 `Slider + InputNumber` 选择并发度（1-64），透传到 `POST /projects/{pid}/runs?concurrency=N`，后端校验 422 与乱值兜底
- [ ] F015：报告详情「导出报告」Dropdown 选 JSON / HTML，axios blob 下载，不在 URL 里塞 token

**鉴权**
- [ ] 未登录访问受保护路由 → 跳 `/login`
- [ ] 非 admin 访问 `/admin/*` → 跳 `/403`
- [ ] 命中不存在的 URL → 跳 `/404`

**状态管理 / 工具**
- [ ] TanStack Query 覆盖所有 server state（projects / environments / suites / cases / runs / reports / users / roles）
- [ ] Zustand 仅 `store/auth.ts` 管 token + user
- [ ] queryKeys factory 统一管理 cache key；mutation 后 `invalidateQueries` 相关 key

**编译闸门**
- [ ] `npm run lint` 0 errors / 0 warnings（`--max-warnings 0`）
- [ ] `npm run typecheck` 0 errors
- [ ] `npm run build` 成功生成 `dist/`

**文档**
- [ ] `frontend/README.md` 含启动 / 目录 / 状态管理分工 / 鉴权约定 / P1 集成点

**边界（明确不做）**
- [ ] 零前端自动化测试（Cypress / Playwright / Vitest+RTL）
- [ ] 零 i18n 国际化
- [ ] 零暗色模式
- [ ] 零 WebSocket 实时推送
- [ ] 零 PWA / 离线
- [ ] 零新 UI 库（已锁 Ant Design）
- [ ] 零 Redux / MobX（已选 Zustand）
- [ ] 后端 `pytest src/tests/` 仍 424/424 全绿（F016 改动仅前端）

---

## 5. 执行验收

- [ ] 可以执行单用例。
- [ ] 可以执行集合。
- [ ] 可以执行项目。
- [ ] 执行时可以指定环境。
- [ ] 未指定环境时使用默认环境。
- [ ] 变量能正确替换。
- [ ] 请求超时记录为 `error`。
- [ ] 断言失败记录为 `failed`。
- [ ] 断言通过记录为 `passed`。

---

## 6. 报告验收

- [ ] 可以查看执行批次列表。
- [ ] 可以查看执行批次详情。
- [ ] 可以查看执行结果列表。
- [ ] 可以查看单条结果详情。
- [ ] 报告包含总数、通过数、失败数、跳过数、耗时。
- [ ] 失败结果包含断言失败原因。
- [ ] 异常结果包含错误信息。

---

## 7. 文档验收

- [ ] PRD、MVP、ROADMAP 已更新。
- [ ] ARCHITECTURE、DATABASE、MODULE、DEPLOYMENT 已更新。
- [ ] OPENAPI、API_GUIDE、ERROR_CODE 已更新。
- [ ] AI_RULES、DIRECTORY、CODING_STYLE、ADR 已更新。
- [ ] TEST_STRATEGY、ACCEPTANCE、DoD 已更新。

---

## 8. 不验收内容

以下内容不属于 MVP 验收范围：

- UI 自动化。
- 性能测试。
- AI 生成用例。
- 定时任务。
- 分布式执行。
- 多租户。
- Allure 静态站点。
