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

---

## 6. 技术选型

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
| React + Vite | 前端 | 管理界面 |

---

## 7. 当前不引入

| 能力 | 暂缓原因 |
|------|----------|
| 消息队列 | 当前手动触发和串行执行即可 |
| 分布式执行 | MVP 不需要横向扩容执行器 |
| AI / RAG | 不属于 API 测试最小闭环 |
| 定时任务 | 先完成手动执行闭环 |
| Allure 服务化 | 先做平台内置报告 |
