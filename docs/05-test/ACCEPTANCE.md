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
