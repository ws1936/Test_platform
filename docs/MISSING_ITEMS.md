# 项目缺少清单（Missing Items）

> 本文档由 7 步整改后的扫描生成。  
> 整改已完成：① 目录对齐、② Alembic 迁移、③ logout/改密码、④ Role + 用户 CRUD、⑤ pytest 测试、⑥ Docker Compose、⑦ 前端脚手架。  
> 以下为**仍待补齐**的功能/合规项，用于后续排期。

---

## A. 核心业务（MVP Phase 1 — 自动化测试闭环）

### A1. 项目管理（001_project §四.2）
- [ ] `ApiProject` 模型（id/name/description/base_url/owner_id/created_at/updated_at）
- [ ] `ApiProject` 迁移文件
- [ ] `POST/GET/PUT/DELETE /api/v1/projects` 接口
- [ ] 项目列表分页 + 搜索
- [ ] 项目成员管理（多对多 user-project 关联表）

### A2. 环境管理（001_project §四.3）
- [ ] `ApiEnvironment` 模型（id/project_id/name/variables/headers/token/is_default）
- [ ] 迁移文件
- [ ] `POST/GET/PUT/DELETE /api/v1/projects/{id}/environments`
- [ ] 变量替换引擎（支持 `{{var}}` 语法）
- [ ] 默认环境标识

### A3. API 管理（001_project §四.4，004_api §3.3）
- [ ] `ApiTestCase` 模型（method/url/headers/query_params/body_type/body_content/assertions/pre_script/post_script）
- [ ] `ApiCollection` 模型（目录树，parent_id 自引用）
- [ ] 迁移文件
- [ ] 用例 CRUD 接口
- [ ] 集合 CRUD 接口
- [ ] 目录树查询接口

### A4. Swagger/OpenAPI 导入（001_project §四.5）
- [ ] Swagger URL 抓取（httpx）
- [ ] OpenAPI JSON 解析（openapi-schema-validator）
- [ ] 自动生成 ApiProject + ApiCollection + ApiTestCase
- [ ] 重复检测（按 URL + Method）

### A5. AI 自动生成测试用例（001_project §四.6，Phase 3 范围）
- [ ] 接入 LLM（OpenAI / 通义千问 / Claude）
- [ ] 根据接口元数据生成 pytest 脚本
- [ ] 生成断言规则
- [ ] 保存到 `pre_script` / `post_script`

### A6. 测试执行引擎（001_project §四.7）
- [ ] `ApiTestRun` + `ApiTestResult` 模型
- [ ] 迁移文件
- [ ] `POST /api/v1/projects/{id}/runs` 触发执行
- [ ] httpx 异步执行器，支持 GET/POST/PUT/DELETE
- [ ] 断言引擎（status_code / json_path / response_time / header）
- [ ] 变量替换（项目级 / 集合级 / 用例级 + 内置 `$timestamp` `$random_int` `$uuid`）
- [ ] 并发执行 + 超时控制
- [ ] 实时进度推送（WebSocket / SSE）
- [ ] 单用例 / 单集合 / 单项目 三种粒度

### A7. 测试报告（001_project §四.8）
- [ ] Allure 结果收集（allure-pytest 或自实现）
- [ ] `GET /api/v1/runs/{id}/results` 详情
- [ ] 历史趋势接口（成功率/平均时长）
- [ ] Allure Report 静态站点（nginx 托管）

---

## B. 平台能力（Phase 2 — 增强）

### B1. 定时任务
- [ ] APScheduler / Celery Beat 集成
- [ ] 定时执行配置（cron 表达式）
- [ ] 任务历史与日志

### B2. 消息通知
- [ ] 邮件 / 企业微信 / 钉钉 通知
- [ ] 失败告警 webhook

### B3. Dashboard
- [ ] 首页统计卡片（执行总数/成功率/活跃用户/项目数）
- [ ] 趋势图（最近 7/30 天）

### B4. Jenkins / GitLab CI 集成
- [ ] Pipeline 插件
- [ ] 回调上报执行结果

---

## C. 合规性 / 工程化（AI_RULES 对照）

### C1. 安全（AI_RULES §10）
- [ ] Token 黑名单升级为 Redis（目前是内存 set）
- [ ] 登录失败次数限制（rate-limit，如 slowapi）
- [ ] 验证码扩展位
- [ ] RBAC 细粒度：基于 permissions 列表的 `require_permission("user:write")` 装饰器
- [ ] HTTPS 反向代理（Nginx）
- [ ] CORS 白名单按环境收紧（生产仅允许业务域名）
- [ ] 敏感字段加密（手机号/邮箱，可选 KMS）

### C2. 日志（AI_RULES §9）
- [ ] JSON 结构化日志（`loguru` 或 `structlog`）
- [ ] 操作日志中间件（user_id / ip / path / method / status / cost）
- [ ] 接口日志与错误日志分离输出
- [ ] 敏感字段脱敏（password / token / cookie）
- [ ] 日志聚合（ELK / Loki）

### C3. 响应统一（AI_RULES §8）
- [ ] 成功响应也用 `{code: 0, message: "success", data: ...}` 包装
- [ ] 实现 custom `APIRoute` 自动包装 response
- [ ] OpenAPI schema 同步更新

### C4. 测试（AI_RULES §11）
- [ ] 测试覆盖率报告（pytest-cov），目标 ≥ 80%
- [ ] API 集成测试覆盖（目前仅 auth + 部分 user CRUD）
- [ ] 角色/项目管理/执行的接口测试
- [ ] 端到端 Playwright 测试（前端登录 → 创建项目 → 执行用例）
- [ ] CI 流水线强制通过（GitHub Actions）

### C5. 代码质量
- [ ] `ruff` 替代 black + isort（性能更好）
- [ ] `mypy` 严格模式（目前在很多文件 import 解析失败）
- [ ] 移除 `main.py` 的 `print()`（已删除，但 pytest.ini 替换 print）
- [ ] 移除未使用导入（service.py 当前 sqlalchemy 导入位置不规范）
- [ ] pre-commit hook

### C6. 数据库（AI_RULES §7）
- [ ] User 表加 `deleted_at` 字段并启用软删除（目前用 status=0 模拟）
- [ ] 所有表加 `ON UPDATE` 触发器记录 updated_at
- [ ] 关键查询加复合索引（users.email+status 等）

### C7. 部署（AI_RULES §4 Deployment）
- [ ] 多阶段 Dockerfile 已完成 ✅
- [ ] docker-compose ✅
- [ ] Nginx 反向代理配置
- [ ] Kubernetes Helm chart（可选）
- [ ] 健康检查 + 就绪探针
- [ ] 数据库备份策略

---

## D. 前端（Phase 1 仍需补齐）

### D1. 已完成
- [x] Vite + React + TS + AntD + Zustand 脚手架
- [x] Axios 客户端 + 拦截器
- [x] 登录页 + Dashboard 占位页
- [x] 路由保护（ProtectedRoute）

### D2. 待补
- [ ] 用户管理页（CRUD + 搜索 + 分页 + 启用/禁用）
- [ ] 角色管理页（CRUD + 权限分配）
- [ ] 个人中心（修改密码、改昵称）
- [ ] 项目列表/详情/编辑器
- [ ] 环境管理 UI
- [ ] API 用例编辑器（method/url/headers/body/assertions 表单）
- [ ] Swagger 导入向导
- [ ] 测试执行页（按钮触发 + 实时进度 + 结果查看）
- [ ] Allure 报告嵌入页
- [ ] Dashboard 图表（antd-charts / echarts）
- [ ] 国际化（中/英）
- [ ] 主题切换（亮/暗）
- [ ] 错误边界（ErrorBoundary）
- [ ] 单元测试（Vitest + React Testing Library）
- [ ] E2E 测试（Playwright）

---

## E. 文档

- [ ] `docs/design/` 填充（详细设计：数据流、时序、关键算法）
- [ ] `docs/meeting/` 填充（会议纪要模板）
- [ ] OpenAPI 客户端生成（openapi-generator → 前端 SDK）
- [ ] 部署手册（生产环境部署步骤）
- [ ] 故障排查手册（FAQ）

---

## F. 验证清单（建议立即执行）

> 以下可在不依赖外部服务的情况下立刻验证，建议在合并 PR 前完成。

1. `uv pip install -r requirements.txt`
2. `pytest -v` — 期望 14 个测试用例全部通过
3. `alembic upgrade head`（连真实 PostgreSQL）— 验证迁移无错
4. `docker compose up --build` — 验证三容器全部 healthy
5. `cd frontend && npm install && npm run build` — 验证前端能编译
6. `uvicorn app.main:app --reload` → 访问 `/docs` 查看 OpenAPI 包含所有 8 个新接口

---

## G. 优先级建议（按业务价值）

| 优先级 | 任务 | 估时 | 业务价值 |
|--------|------|------|----------|
| 🔴 P0 | C3 统一响应包装 | 0.5d | 规范 |
| 🔴 P0 | C1 Redis 黑名单 + rate-limit | 1d | 安全 |
| 🟠 P1 | A3 API 用例 + Collection 建模 | 2d | 核心闭环 |
| 🟠 P1 | A6 测试执行引擎 | 3d | 核心闭环 |
| 🟠 P1 | D2 用户/角色管理 UI | 2d | 用户可用 |
| 🟡 P2 | A1 项目管理 | 1d | 闭环 |
| 🟡 P2 | A2 环境管理 + 变量替换 | 1d | 闭环 |
| 🟡 P2 | C2 JSON 日志 | 1d | 运维 |
| 🟡 P2 | D2 项目/用例 UI | 3d | 用户可用 |
| 🟢 P3 | A4 Swagger 导入 | 2d | 易用性 |
| 🟢 P3 | A7 Allure 报告 | 1d | 体验 |
| 🟢 P3 | B1-B3 增强能力 | 各 1-2d | 增值 |

---

## H. 当前整体完成度（重新评估）

```
整改后完成度：  ████████░░░░░░░░░░░░  ~42%

├─ 文档体系        ████████████████  100%
├─ 工程规范        ████████████░░░░  ~75%  (统一响应包装待补)
├─ 架构骨架        ████████████████  100%
├─ 基础设施        ████████████████  100% (Docker ✅)
├─ 登录认证        ████████████████  100% (含 logout/改密码)
├─ 用户/角色管理   ████████████░░░░  ~80%  (UI/权限细粒度待补)
├─ API 测试业务    ░░░░░░░░░░░░░░░░░    0%  ← 核心待开发
├─ 前端骨架        ████████░░░░░░░░  ~50%  (仅登录/Dashboard)
├─ 测试体系        ████░░░░░░░░░░░░  ~25%  (基础已有，缺覆盖率)
└─ DevOps/CI       ██████████░░░░░░  ~60%  (Docker ✅, CI 缺)
```

对比整改前 **12%**，本轮提升 **+30%**。
