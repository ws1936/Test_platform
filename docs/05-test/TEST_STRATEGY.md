# 测试策略

> 范围：API 自动化测试平台 MVP。  
> 目标：保证核心闭环可用、可重复、可回归。

---

## 1. 测试目标

必须验证以下闭环：

```text
登录 → 创建项目 → 配置环境 → 创建用例 → 执行测试 → 查询报告
```

重点保证：

- 认证和权限正确。
- 数据模型关系正确。
- 变量替换正确。
- 请求构造正确。
- 断言判断正确。
- 执行结果统计正确。

---

## 2. 测试分层

| 层级 | 目标 | 工具 |
|------|------|------|
| 单元测试 | 核心算法和 Service 逻辑 | pytest |
| API 测试 | HTTP 接口行为 | pytest + FastAPI TestClient / httpx |
| 集成测试 | 执行器与模拟被测 API | pytest + mock server |
| 前端测试 | MVP 后续页面交互 | Vitest / React Testing Library（后续） |

---

## 3. 单元测试范围

必须覆盖：

- 变量替换。
- 内置变量生成。
- 请求 URL 构造。
- Header 合并。
- Body 构造。
- 状态码断言。
- JSON Path 断言。
- Header 断言。
- 响应时间断言。
- 执行统计计算。

---

## 4. API 测试范围

必须覆盖：

- 注册/登录/刷新/退出。
- 当前用户信息。
- 修改密码。
- 用户管理。
- 角色管理。
- 项目 CRUD。
- 环境 CRUD。
- 集合 CRUD。
- 用例 CRUD。
- 单用例执行。
- 项目执行。
- 执行结果查询。

---

## 5. 集成测试策略

API 执行器测试不应依赖外部网络。

建议：

- 使用本地 mock API。
- 或使用 httpx MockTransport。
- 模拟成功、失败、超时、非 JSON 响应。

必须验证：

- 请求实际发送数据正确。
- 超时能被记录为 `error`。
- 断言失败能被记录为 `failed`。
- 执行完成能更新 TestRun 统计。

---

## 6. 测试数据原则

- 测试数据必须隔离。
- 每个测试可独立运行。
- 不依赖执行顺序。
- 不使用生产数据库。
- 不提交真实 Token、密码、Cookie。

---

## 7. 覆盖率目标

MVP 建议：

- 核心引擎模块覆盖率 ≥ 90%。
- Service 层覆盖率 ≥ 80%。
- 核心 API 至少有成功和失败路径测试。

---

## 8. 回归清单

每次合并前至少运行：

```bash
pytest src/tests
```

涉及前端时运行：

```bash
cd frontend
npm run build
```

### 8.1 CI 工作流（2026-09-23 起）

`.github/workflows/` 下两个 workflow 在 push / PR 到 `main` 时自动触发：

| Workflow | 触发条件 | 内容 |
|----------|----------|------|
| `backend-tests.yml` | `src/**` / `pyproject.toml` / `uv.lock` / `alembic.ini` / `migrations/**` 变更 | `pytest src/tests --cov=src/app --cov-fail-under=78` |
| `frontend-check.yml` | `frontend/**` / `package*.json` 变更 | `npm run check`（lint + typecheck + build） |

**覆盖率门槛演进路径**：

| 阶段 | 阈值 | 触发时间 |
|------|------|---------|
| 当前 baseline | 79% | 2026-09-23 实测（515 测试全绿） |
| 起步门槛 | 78% | 2026-09-23 留 1% 余量 |
| 目标线 1 | 80%（service 层最低要求，per §7） | 下个 Sprint |
| 目标线 2 | 90%（test_engine / test_design 关键路径） | F025 落地后 |

**红线**：

* 不上传 codecov / coveralls 等第三方服务（呼应 AI_RULES §4.4 + §15：未经 ADR 批准不引入新框架）。
* CI 失败必须修复或回滚；不允许 `-no-cov-on-fail` 等"绕过"提交。
* coverage.xml 仅作为 debug artifact 保留 7 天；不在 README 显示 badge（避免外部依赖）。
