# 项目前后端代码审查清单（2026-07-27）

> 审查范围：产品文档、前端路由/页面/API、后端 Router/Service/Repository/Engine、自动化测试与构建。
> 基线闭环：登录 → 项目 → 环境 → Suite/Case → 执行 → 报告。
> 说明：仓库近期已补齐旧评估中标为“占位”的 5 个 Workspace 页面，因此本清单以当前源码为准，而非沿用 `PROJECT_EVALUATION.md`（2026-07-20）的旧结论。

## 一、审查结论

- 前端核心页面已存在：登录、Dashboard、项目、环境、Suite、Case、执行中心、报告、OpenAPI 导入、项目设置、用户与角色管理。
- 后端 F001–F015 的主体代码已出现；F014 并发和 F015 导出实际上已实现，但 Backlog 仍写 Todo。
- 当前没有“整块核心页面缺失”，但存在多处会阻断真实业务闭环的契约错误，优先级最高的是：
  1. 单文档 OpenAPI 导入无法从预览进入提交；
  2. 大多数业务路由未校验 `token_version/is_active`，禁用用户或改密后的旧 Token 仍可访问；
  3. Case 编辑保存逻辑要求一个并不存在的 suiteId；
  4. Suite 执行会把禁用 Case 一并执行；
  5. 报告“再次执行”传入 Run ID，而不是原 scope ID。
- 验证结果：
  - 前端 `npm run check`：通过（lint、typecheck、build 均通过），但主包约 1.49 MB，存在分包告警。
  - 后端全量测试：收集阶段失败，`src/tests/test_test_run_export.py:140` 有 Python 语法错误。
  - 忽略该文件后：395 项测试全部通过，说明既有覆盖范围稳定，但导出模块未进入有效回归。

---

## 本轮处理进展（2026-07-27）

- [x] 统一受保护业务路由的 Token 版本与账号状态校验，并新增跨模块安全回归测试。
- [x] Role 创建、更新、删除改为仅超级管理员可调用；同时修复 SQLite 下 permissions JSON 存储。
- [x] 修复单文档 OpenAPI 预览不返回 `preview_id`，前端已消费真实 ID。
- [x] 修复 Case 编辑模式错误要求 Suite ID，以及错误的 Suite 缓存失效键。
- [x] Suite Run 过滤禁用 Case，并在无启用 Case 时明确拒绝执行。
- [x] TestRun 新增并持久化 `scope_id`（migration `0008_test_run_scope_id`），报告重跑使用原目标。
- [x] 修复 F015 导出测试语法和 HTML 实体转义实现。
- [x] 验证：后端 `411 passed`；前端 lint/typecheck/build 全通过。

## 二、P0：阻断主业务闭环 / 安全边界

### P0-01 单文档 OpenAPI 两段式导入无法提交

- [x] 后端 `ImportPreviewResponse` 增加并返回真实 `preview_id`。
- [x] 前端删除 `data.preview_id ?? "auto"` 的伪 fallback，消费真实 ID。
- [x] 单文档 Preview/Commit 与 OpenAPI 回归测试通过。
- 证据：
  - `src/app/domain/openapi_importer/schema.py:122-132` 无 `preview_id`；
  - `service.py:85-86` 生成并缓存 ID，但 `103-114` 未返回；
  - `frontend/src/pages/workspace/WorkspaceImport.tsx:132-135` 使用字符串 `auto`；
  - Commit 会在 `service.py:127-131` 因找不到缓存键而报冲突。
- 影响：当前 OpenAPI 单文档页面能预览但不能真正创建 Case。

### P0-02 认证撤销只在项目路由生效，大多数业务接口仍接受旧 Token

- [x] `get_current_user` 统一校验 token version 与账号状态，覆盖所有使用该依赖的业务路由。
- [x] 新增 Suite/Role 跨模块撤销与禁用账号回归测试，既有项目安全测试继续通过。
- [ ] `change_password` 后续可进一步改为强依赖完整用户校验（当前不阻断资产接口安全修复）。
- 证据：
  - `common/dependencies.py:132-139` 的 `get_current_user` 不检查 `token_version` 和 `is_active`；
  - Environment/Suite/TestCase/TestRun/OpenAPI/Role 共 44 处使用该弱依赖；
  - 只有项目路由显式使用 `get_current_user_with_version`；
  - `user_router.py:55` 修改密码仅依赖 `get_current_user_id`。
- 影响：管理员禁用用户或用户改密后，旧 access token 仍可继续读写大量测试资产，违反验收标准。

### P0-03 Case 编辑模式无法保存

- [ ] 后端明确“Case 是否单归属 Suite”模型；当前 Case 实体只有 `project_id`，Suite 是关联表，需统一产品语义。
- [x] 编辑 Case 不再要求 `initialSuiteId`；更新用例本身无需 Suite ID。
- [ ] 若支持变更归属 Suite，应新增/复用 Suite 关联 API，并在 UI 单独处理。
- [x] 修正错误的缓存键，不再把 Case ID 当作 Suite ID。
- 证据：`WorkspaceCaseEditor.tsx:153-156` 编辑时取 `initialSuiteId ?? ""`；从列表进入编辑 URL 不带 suiteId，因此必抛“请选择 Suite”。
- 影响：Case 创建可用，但从 Case 列表进入编辑后无法保存。

### P0-04 Suite 执行未过滤禁用 Case

- [x] 后端 collection scope 在解析 Suite 关联后，仅保留 `status == 1` 的 Case。
- [x] 若过滤后为空，返回明确的“Suite has no enabled test cases”错误。
- [x] 前端预览已按 enabled 过滤，与后端一致。
- 证据：`TestRunService._resolve_case_ids()` 的 project/case scope 检查 enabled，但 collection 分支 `190-201` 直接返回全部关联 ID。
- 影响：被禁用的 Case 仍可能在 Suite Run 中执行，违背 MVP 定义。

### P0-05 报告“再次执行”传错 scopeId

- [x] TestRun 持久化并返回原始 `scope_id`，新增 Alembic 0008 migration。
- [x] “再次执行”传原 Case ID / Suite ID / Project ID，而不是 `run.id`。
- [ ] 后续引入前端测试框架后增加三类重跑导航组件测试。
- 证据：`WorkspaceReportDetail.tsx:131` 使用 `scopeId=${run.id}`。
- 影响：project scope 因后端忽略 scopeId 尚可运行；case/suite scope 会预选失败或无法提交。

### P0-06 角色管理后端缺少管理员权限保护

- [x] Role 的创建、更新、删除使用 `get_current_superuser`。
- [x] 列表/详情保留给已登录用户读取，写操作仅管理员。
- [x] 增加非管理员创建/更新/删除 403 测试。
- 证据：`role_router.py` 所有端点依赖 `get_current_user`，而前端虽有 `AdminRoute`，API 可被直接调用。
- 影响：普通用户可绕过 UI 修改角色与权限字符串。

---

## 三、P1：功能已出现但契约/页面未完整闭环

### P1-01 报告导出后端已实现，前端入口和 API 封装缺失

- [ ] `frontend/src/api/runs.ts` 增加 blob 下载方法。
- [ ] Report Detail 增加 JSON / HTML 导出按钮并处理文件名。
- [ ] 修复导出测试语法错误并纳入全量回归。
- 证据：后端有 `GET /runs/{run_id}/export` 与 exporter；前端全局没有 `/export`、下载或导出调用。

### P1-02 F013 批量 OpenAPI 导入没有前端页面

- [ ] 前端 API 类型补充 `documents[]`、Batch Preview、Batch Commit。
- [ ] 导入页支持 1–5 份文档、逐文档状态和失败隔离结果。
- [ ] 页面明确单文档与批量模式，并保持两段式确认。
- 证据：后端 F013 已实现；`openApiImport.ts` 和 `WorkspaceImport.tsx` 仅实现单文档。

### P1-03 执行时“未指定环境使用默认环境”未实现

- [ ] 决定是否严格兑现验收标准：若是，`environment_id` 改可选并由 Service 查询默认环境。
- [ ] 无默认环境时返回明确业务错误。
- [ ] 单 Case 快捷执行也保持同一语义。
- 证据：`TestRunCreateRequest.environment_id` 为必填；前端也强制选择。与 `ACCEPTANCE.md §5` 的“未指定环境时使用默认环境”不一致。

### P1-04 缺失变量没有明确失败，仍会把占位符发给目标服务

- [ ] 替换器返回 unresolved variables，RequestBuilder 在发送前抛明确业务错误。
- [ ] Result 保存 `VARIABLE_NOT_FOUND`，而不是依赖目标服务偶然返回错误。
- [ ] 覆盖 path/header/query/body/assertion expected 的缺失变量。
- 证据：`variable_substitutor.py:153-161` 仅 warning 并保留原字符串；与 MVP“变量缺失要给出明确错误”不一致。

### P1-05 内置变量只实现 timestamp，且语法与 PRD/MVP 不一致

- [ ] 冻结一种公开语法并同步 PRD、MVP、UI 提示、API Guide 与代码。
- [ ] 若按 MVP，实现 timestamp、uuid、random_int 全部内置变量。
- [ ] 提供兼容迁移策略（如同时支持 `${name}` 与 `{{name}}` 一段时间）。
- 证据：代码仅支持 `${timestamp}`；文档要求 `{{$timestamp}}`、`{{$uuid}}`、`{{$random_int}}` 或 `{{token}}`。

### P1-06 TestRun 未保存 scope_id，历史无法准确重放

- [ ] 数据模型新增 `scope_id`（需 migration），创建 Run 时持久化。
- [ ] Response、导出、报告详情都返回该字段。
- [ ] 用于“再次执行”和审计定位原执行范围。
- 影响：当前 Run 只知道 scope 类型，不知道具体 Case/Suite。

### P1-07 OpenAPI overwrite 不是原子更新，存在丢 Case 风险

- [ ] overwrite 改为更新现有 Case，或对“删除旧 Case + 创建新 Case”使用 savepoint/事务补偿。
- [ ] 创建失败时确保旧 Case 仍存在。
- [ ] 校验 TestResult 历史保留策略与 FK 行为。
- 证据：`OpenApiImportService` 先删除提交，再尝试创建；创建异常只记录 errors。

### P1-08 项目更新缺少名称冲突转换

- [ ] update 前做 owner+name 重复检查并捕获 `IntegrityError`。
- [ ] 返回与 create 一致的 409 业务码。
- 证据：`ProjectService.update_project:193-200` 直接 commit，没有冲突转换。

### P1-09 用户角色更新无法清空 role_id

- [ ] 使用 `model_fields_set` 或显式 sentinel 区分“未传”与“传 null”。
- [ ] 补充清空角色的 API 与前端回归测试。
- 证据：`UserService.update_user:325-326` 仅在 `role_id is not None` 时赋值；前端允许传 null。

### P1-10 前端 Legacy 路由存在错误重定向

- [ ] 修复 `/projects/:projectId/suites/:suiteId` 中硬编码 `PLACEHOLDER`。
- [ ] 修复旧 report/result/import 路由，使用参数构建绝对新地址。
- [ ] 修复 AppShell 选中菜单与项目切换：当前 Workspace URL 不在旧 modules 匹配表中。
- 证据：`App.tsx:62` 明确出现 `/projects/PLACEHOLDER/...`；多处 `<Navigate to="../...">` 会丢失参数或落到错误层级。

### P1-11 OpenAPI Preview 的冲突状态展示不准确

- [ ] 后端根据 `on_conflict` 返回 `overwrite` / `skip` 的可执行状态，或前端根据 existing + strategy 推导。
- [ ] `skipped_count` 应反映 skip 策略下的已存在数量。
- [ ] Suite 名称应正确返回；当前单文档预览写死空字符串。
- 证据：单文档 Service 永远返回 `new/exists`、`skipped_count=0`、`suite_name=""`；前端却统计 `overwrite` 状态。

### P1-12 前端没有自动化页面测试

- [ ] 引入 Vitest + React Testing Library。
- [ ] 至少覆盖登录刷新、Case 创建/编辑、Run 三 scope、Import 两段式、Report 重跑/导出、权限路由。
- [ ] CI 执行 `npm run check` + 前端测试。
- 影响：当前 TypeScript 可构建，但业务契约类错误无法由静态检查发现。

---

## 四、P2：一致性、性能与可维护性

- [ ] **清理重复执行 UI**：`RunExecutionDrawer.tsx` 未被任何页面引用，与 `WorkspaceRun` 功能重复；删除或统一复用。
- [ ] **前端分包**：主 chunk 约 1.49 MB，按 antd/vendor/workspace/report 分割，更多 Workspace 页面改 lazy。
- [ ] **列表分页**：Case、Suite、Environment 前端均偏向一次取全；数据量增大后补服务端分页。
- [ ] **并发执行架构复核**：F014 已实现，但共享单个 `AsyncSession` + 锁 + 每 Case commit，吞吐与事务语义需压测。
- [ ] **Preview Cache 外置/限时清理**：当前类级 dict 无 TTL，重启丢失，多 worker 不共享，长期运行会积累未消费缓存。
- [ ] **Token blacklist / rate limit 外置**：多实例前迁移 Redis。
- [ ] **项目删除改软删除或归档**：当前硬删并级联 Run/Result，和“结果可追溯”目标冲突。
- [ ] **删除确认增强**：高风险项目删除建议输入项目名确认，而非单次 Popconfirm。
- [ ] **API 错误结构统一**：角色权限使用 FastAPI `HTTPException.detail`，其它业务使用 `code/message/details`。
- [ ] **依赖与源码一致**：代码直接 import `bcrypt`、执行器依赖 httpx；确认生产 dependencies 明确声明，不只依赖间接包或 dev extra。
- [ ] **消除 PytestCollectionWarning**：导入的 `TestRunner` / `TestCaseRepository` 使用别名，避免 pytest 误判测试类。
- [ ] **升级 python-jose 或封装兼容**：测试产生大量 `datetime.utcnow()` 弃用警告。
- [ ] **文档状态同步**：Backlog 的 F014/F015 仍为 Todo，F016 仍称前端页面 Todo，与当前代码不符。
- [ ] **旧评估文档更新**：`PROJECT_EVALUATION.md` 仍称 5 个 Workspace 页面是占位页，已明显过期。
- [ ] **OpenAPI 文档校正**：`batch` 默认值应与后端 `False` 一致；补 F015 export 契约。

---

## 五、已实现模块盘点

| 模块 | 后端 | 前端 | 当前判断 |
|---|---|---|---|
| 登录/刷新/退出/当前用户/改密 | 已实现 | 已实现 | 主流程可用；撤销校验覆盖不一致 |
| 用户管理 | 已实现 | 已实现 | 可用；role_id 清空存在问题 |
| 角色管理 | CRUD 已实现 | CRUD 已实现 | 后端写接口权限缺失 |
| 项目管理 | CRUD 已实现 | 列表、创建、编辑、删除、设置页 | 可用；更新冲突/硬删除需处理 |
| 环境管理 | CRUD、默认环境 | 完整页面 | 可用 |
| Suite 管理 | CRUD、关联、排序 | 列表与详情 | 可用；Suite Run enabled 过滤错误 |
| Case 管理 | CRUD | 列表与结构化编辑器 | 创建可用；编辑保存阻断 |
| 变量替换 | 引擎已实现 | 编辑器提示 | 语法/内置变量/缺失变量与需求不一致 |
| 断言引擎 | 5 类型、12 操作符 | 结构化编辑器 | 基本对齐；文档操作符命名需统一 |
| 执行 | Case/Suite/Project、有限并发 | 执行中心和单 Case 入口 | 可用但有 scope 与 enabled 缺陷 |
| 报告 | 列表、详情、Failure、Result | 完整页面 | 查看可用；重跑错误、导出入口缺失 |
| OpenAPI 单文档 | Preview/Commit 代码存在 | 导入向导存在 | Preview 可用，Commit 被 preview_id 阻断 |
| OpenAPI 批量 | 后端已实现 | 未实现 | 缺前端页面/契约 |
| 报告导出 | JSON/HTML 后端已实现 | 未实现 | 测试文件还存在语法错误 |

---

## 六、建议处理顺序

1. **安全先行**：P0-02、P0-06。
2. **恢复核心写入闭环**：P0-01、P0-03、P0-04、P0-05。
3. **补齐已实现后端能力的 UI**：P1-01、P1-02、P1-06。
4. **收敛需求契约**：变量语法/缺失策略、默认环境、OpenAPI Preview 状态。
5. **建立回归门禁**：修导出测试 → 后端全量绿 → 前端业务测试 → CI。
6. **最后处理性能、软删除、多实例和文档治理等 P2 项。**
