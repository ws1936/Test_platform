# AI_RULES.md

> Version: v1.0
> Scope: Enterprise Automation Testing Platform
> Purpose: Define the mandatory engineering rules that every AI Coding Agent must follow.

---

# 1. Mission（项目使命）

本项目旨在构建一套企业级自动化测试平台。

平台目标包括：

* API 自动化测试
* UI 自动化测试
* 测试任务调度
* 测试数据管理
* 测试报告管理
* AI Agent 辅助测试
* RAG 知识库
* 企业级权限管理

所有设计与实现均以：

**可维护、可扩展、可测试、可持续迭代** 为最高原则。

---

# 2. Engineering Principles（工程原则）

所有 AI 必须遵循以下原则：

## 第一性原理（First Principles）

任何 Feature 必须先分析：

* 为什么存在？
* 它解决什么问题？
* 数据是什么？
* 行为是什么？
* 边界是什么？

不得直接开始编码。

---

## 奥姆剃刀原则（Occam's Razor）

优先采用：

* 最简单
* 最稳定
* 最成熟
* 最容易维护

的实现方案。

禁止为了展示能力而引入复杂设计。

---

## KISS 原则

Keep It Simple.

避免：

* 过度抽象
* 过度设计
* 多层包装
* 无意义封装

---

## DRY 原则

Don't Repeat Yourself.

重复逻辑必须抽取公共模块。

---

## SOLID 原则

优先遵循：

* 单一职责
* 开闭原则
* 依赖倒置

---

# 3. Development Workflow（开发流程）

AI 必须严格遵循以下顺序：

```
理解需求
↓

分析业务

↓

阅读已有代码

↓

设计方案

↓

评估影响范围

↓

实现代码

↓

编写测试

↓

运行检查

↓

输出结果
```

禁止：

收到需求立即输出代码。

---

# 4. Project Technology Stack（统一技术栈）

## Backend

* Python 3.12
* FastAPI
* SQLAlchemy 2.x
* Pydantic v2
* PostgreSQL
* Redis
* Alembic

---

## Frontend

* React
* TypeScript
* Vite
* Ant Design
* Zustand
* Axios

---

## Testing

* pytest
* Playwright
* Allure
* Faker

---

## Deployment

* Docker
* Docker Compose
* Nginx
* GitHub Actions

未经 ADR 批准，不得擅自引入新的核心技术栈。

---

# 5. Project Architecture Rules（架构规范）

统一采用：

```
Controller

↓

Service

↓

Repository

↓

Database
```

禁止：

Controller

直接操作数据库。

所有业务逻辑必须进入 Service。

---

# 6. Coding Rules（编码规范）

所有代码必须：

* 类型标注完整
* 方法职责单一
* 变量命名清晰
* 保持高可读性

Python：

* snake_case
* PascalCase(Class)
* UPPER_CASE(Constant)

TypeScript：

* camelCase
* PascalCase(Component)

禁止：

* Magic Number
* print()
* 冗余代码
* 超长函数
* 超长类

---

# 7. Database Rules（数据库规范）

统一：

每张表必须包含：

* id
* created_at
* updated_at

推荐：

* deleted_at（软删除）

Migration：

统一 Alembic。

禁止：

直接修改数据库。

禁止：

生产环境手工改表。

---

# 8. API Rules（接口规范）

统一：

RESTful API。

统一前缀：

```
/api/v1
```

统一响应：

```json
{
    "code":0,
    "message":"success",
    "data":{}
}
```

错误统一：

```json
{
    "code":10001,
    "message":"Project Not Found"
}
```

所有接口：

自动生成 OpenAPI。

---

# 9. Logging Rules（日志规范）

必须记录：

* 操作日志
* 接口日志
* 错误日志

日志要求：

* JSON 格式
* 可追踪
* 可搜索

禁止：

输出敏感数据：

* Token
* Password
* Secret
* Cookie

---

# 10. Security Rules（安全规范）

必须：

* JWT Authentication
* RBAC 权限
* HTTPS
* 参数校验
* SQL 注入防护
* XSS 防护

禁止：

明文密码。

禁止：

硬编码密钥。

---

# 11. Testing Rules（测试规范）

新增功能必须：

至少包含：

* 单元测试
* API 测试

涉及页面：

必须：

Playwright 自动化。

CI 必须全部通过。

建议：

测试覆盖率 ≥ 80%。

---

# 12. Git Rules（Git 规范）

Commit Message：

```
feat:
fix:
refactor:
docs:
test:
chore:
```

每个 PR：

必须：

* 关联 Feature
* 通过 CI
* 完成 Code Review

---

# 13. AI Behavior Rules（AI 行为规范）

AI 必须：

### 先阅读已有代码

优先修改已有实现。

禁止重复实现相同功能。

---

### 保持一致性

必须遵循：

* 当前目录结构
* 当前编码风格
* 当前设计模式

不得擅自重构整个项目。

---

### 控制影响范围

每次修改：

尽量局部。

不得影响无关模块。

---

### 输出必须解释

生成代码时：

必须说明：

* 修改原因
* 修改位置
* 影响范围
* 风险分析

---

# 14. Forbidden Rules（禁止事项）

禁止：

* 删除已有功能
* 修改数据库结构（未经 Migration）
* 引入未经批准的新框架
* 修改公共接口
* 重复造轮子
* 忽略异常处理
* 忽略日志
* 忽略测试
* 提交不可运行代码
* 留下 TODO/FIXME 后直接结束任务

---

# 15. Definition of Done（完成标准）

AI 完成任务前必须确认：

* 功能完成
* 编译通过
* 测试通过
* OpenAPI 更新
* Migration 完成（如涉及数据库）
* 日志完整
* 权限校验完成
* 无明显重复代码
* 无安全隐患
* 与 AI_RULES 保持一致

全部满足后，任务才视为完成。

---

# 16. Core Philosophy（核心理念）

所有 AI 必须始终遵循以下价值观：

> 正确优先于速度。

> 简单优先于复杂。

> 一致性优先于个性化。

> 可维护性优先于技巧。

> 测试优先于交付。

> 长期演进优先于短期实现。

AI 的职责不是“写代码”，而是持续交付符合企业工程标准、可维护、可扩展、可验证的软件。
