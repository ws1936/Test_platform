# AI_RULES.md

> Version: v1.1  
> Scope: API Automation Testing Platform MVP  
> Purpose: Define the mandatory engineering rules that every AI Coding Agent must follow in this project.

---

## 1. Mission（当前使命）

当前阶段只构建一套 **API 自动化测试平台**。

平台的最小业务闭环是：

```text
认证登录 → 项目管理 → 环境管理 → API 用例管理 → 执行测试 → 查看报告
```

当前阶段不实现：

- UI 自动化测试。
- 性能测试、压力测试、安全测试。
- AI Agent。
- RAG 知识库。
- 分布式任务调度。
- CI/CD 深度集成。
- 多租户和复杂组织架构。

后续能力必须在 MVP 稳定后，通过需求评审或 ADR 再进入实现范围。

---

## 2. Engineering Principles（工程原则）

所有 AI 必须遵循以下原则。

### 2.1 第一性原理（First Principles）

任何 Feature 必须先回答：

- 为什么存在？
- 它解决什么问题？
- 核心数据是什么？
- 核心行为是什么？
- 边界和不做什么是什么？

禁止收到需求后直接开始编码。

### 2.2 奥姆剃刀原则（Occam's Razor）

优先采用：

- 最简单。
- 最稳定。
- 最成熟。
- 最容易维护。

的实现方案。

禁止为了展示能力引入复杂设计。

### 2.3 KISS 原则

Keep It Simple.

避免：

- 过度抽象。
- 过度设计。
- 多层包装。
- 无意义封装。

### 2.4 DRY 原则

重复逻辑必须抽取公共模块，但不要为了“消除表面重复”制造难理解的抽象。

### 2.5 SOLID 原则

优先遵循：

- 单一职责。
- 开闭原则。
- 依赖倒置。

---

## 3. Development Workflow（开发流程）

AI 必须严格遵循以下顺序：

```text
理解需求
  ↓
分析业务
  ↓
阅读已有代码和文档
  ↓
设计方案
  ↓
评估影响范围
  ↓
实现代码
  ↓
编写或更新测试
  ↓
运行检查
  ↓
输出结果
```

---

## 4. Project Technology Stack（当前统一技术栈）

未经 ADR 批准，不得擅自引入新的核心技术栈。

### 4.1 Backend

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Pydantic v2
- PostgreSQL
- Alembic
- httpx
- pytest

### 4.2 Frontend

- React
- TypeScript
- Vite
- Ant Design
- Zustand
- Axios

### 4.3 Deployment

- Docker
- Docker Compose
- Nginx（生产反向代理，后续完善）

### 4.4 暂缓技术

以下技术当前不应主动引入：

- Redis：仅在 Token 黑名单或缓存确有必要时引入。
- Celery / MQ：当前使用进程内执行器。
- Kubernetes / Helm：当前 Docker Compose 足够。
- Allure 服务化：当前先做平台内置报告。
- Playwright：当前不做 UI 自动化。
- LLM / RAG：当前不做 AI 能力。

---

## 5. Architecture Rules（架构规范）

统一采用：

```text
Router / Controller
  ↓
Service
  ↓
Repository
  ↓
Database
```

必须遵守：

- Router 只处理 HTTP 请求、参数和响应。
- Service 承载业务规则和流程编排。
- Repository 封装数据库读写。
- Controller 禁止直接操作数据库。
- API 测试执行逻辑应进入 Service 或独立 Engine，不得写在 Router 中。

---

## 6. API Test Domain Rules（API 测试领域规则）

当前核心领域对象：

- `ApiProject`
- `ApiEnvironment`
- `ApiCollection`
- `ApiTestCase`
- `ApiTestRun`
- `ApiTestResult`

执行链路必须保持清晰：

```text
加载环境和用例
  ↓
变量替换
  ↓
构造 HTTP 请求
  ↓
发送请求
  ↓
执行断言
  ↓
保存结果
  ↓
汇总报告
```

当前禁止：

- 执行用户自定义 Python / JavaScript 脚本。
- 无超时访问外部接口。
- 将被测 API 的敏感响应写入日志。
- 在未认证情况下触发执行。

---

## 7. Coding Rules（编码规范）

所有代码必须：

- 类型标注完整。
- 方法职责单一。
- 变量命名清晰。
- 保持高可读性。

Python：

- `snake_case` for functions and variables。
- `PascalCase` for classes。
- `UPPER_CASE` for constants。

TypeScript：

- `camelCase` for variables and functions。
- `PascalCase` for components and types。

禁止：

- Magic Number。
- `print()`。
- 冗余代码。
- 超长函数。
- 超长类。

---

## 8. Database Rules（数据库规范）

每张业务表必须包含：

- `id`
- `created_at`
- `updated_at`

推荐按业务需要增加：

- `status`：启用/禁用。
- `deleted_at`：软删除。

Migration：

- 统一使用 Alembic。
- 禁止直接手工修改生产数据库结构。

API 测试结果必须保存请求、响应和断言快照，保证历史可追溯。

---

## 9. API Rules（接口规范）

统一使用 RESTful API。

统一前缀：

```text
/api/v1
```

统一成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

统一错误响应：

```json
{
  "code": 10001,
  "message": "Project Not Found",
  "data": null
}
```

所有接口必须能自动生成 OpenAPI 文档。

---

## 10. Logging Rules（日志规范）

必须记录：

- 操作日志。
- 接口日志。
- 错误日志。
- API 测试执行摘要。

日志要求：

- 可追踪。
- 可搜索。
- 生产环境优先 JSON 格式。

禁止输出敏感数据：

- Token。
- Password。
- Secret。
- Cookie。

---

## 11. Security Rules（安全规范）

必须：

- JWT Authentication。
- 简单 RBAC 权限控制。
- 参数校验。
- SQL 注入防护。
- 密码哈希存储。
- API 执行超时控制。

禁止：

- 明文密码。
- 硬编码密钥。
- 执行用户提交的任意代码。
- 日志记录认证凭据。

---

## 12. Testing Rules（测试规范）

新增后端功能必须至少包含：

- 单元测试，覆盖核心算法和 Service 逻辑。
- API 测试，覆盖主要 HTTP 接口。

API 测试平台核心逻辑必须重点测试：

- 变量替换。
- 请求构造。
- 断言引擎。
- 执行结果统计。
- 权限校验。

建议测试覆盖率 ≥ 80%。

---

## 13. Git Rules（Git 规范）

Commit Message 使用：

```text
feat:
fix:
refactor:
docs:
test:
chore:
```

每个 PR 应：

- 关联 Feature 或任务。
- 通过测试。
- 完成 Code Review。

---

## 14. AI Behavior Rules（AI 行为规范）

AI 必须：

### 14.1 先阅读已有代码和文档

优先修改已有实现，禁止重复实现相同功能。

### 14.2 保持一致性

必须遵循：

- 当前目录结构。
- 当前编码风格。
- 当前设计模式。
- 当前 API 自动化测试平台的范围边界。

### 14.3 控制影响范围

每次修改应尽量局部，不得影响无关模块。

### 14.4 输出必须解释

生成代码或文档时必须说明：

- 修改原因。
- 修改位置。
- 影响范围。
- 风险分析。

---

## 15. Forbidden Rules（禁止事项）

禁止：

- 未经确认扩大 MVP 范围。
- 删除已有可用功能。
- 修改数据库结构但不提供 Migration。
- 引入未经批准的新框架。
- 修改公共接口但不更新文档和测试。
- 重复造轮子。
- 忽略异常处理。
- 忽略日志。
- 忽略测试。
- 提交不可运行代码。
- 留下 TODO/FIXME 后直接结束任务。

---

## 16. Definition of Done（完成标准）

AI 完成任务前必须确认：

- 功能或文档目标完成。
- 与当前 API 测试平台 MVP 范围一致。
- 代码可运行或文档自洽。
- 测试已补充或说明未运行原因。
- OpenAPI 文档同步更新（如涉及接口）。
- Migration 完成（如涉及数据库）。
- 日志和权限校验考虑完整。
- 无明显重复代码。
- 无安全隐患。
- 与本文档规则保持一致。

---

## 17. Core Philosophy（核心理念）

> 正确优先于速度。  
> 简单优先于复杂。  
> 一致性优先于个性化。  
> 可维护性优先于技巧。  
> 测试优先于交付。  
> 长期演进优先于短期实现。

AI 的职责不是“写代码”，而是持续交付符合工程标准、可维护、可扩展、可验证的软件。
