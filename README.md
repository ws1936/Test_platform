# API 自动化测试平台

一个面向测试团队的 API 自动化测试平台，用于统一管理接口测试项目、环境、用例、执行记录和测试报告。

> 当前阶段目标：**只做 API 自动化测试平台 MVP**。  
> 暂不做 UI 自动化、性能测试、AI Agent、RAG、分布式调度等复杂能力。

---

## 1. MVP 核心闭环

```text
登录
  ↓
创建项目
  ↓
配置环境
  ↓
维护 API 用例
  ↓
执行测试
  ↓
查看结果 / 报告
```

---

## 2. 文档结构

项目文档已按产品、设计、API、规则、测试五类重新整理：

```text
docs/
├── 01-product/
│   ├── PRD.md                  # 产品需求
│   ├── MVP.md                  # MVP 范围
│   ├── ROADMAP.md              # 版本规划
│   └── BACKLOG.md              # 功能待办列表
│
├── 02-design/
│   ├── ARCHITECTURE.md         # 系统架构
│   ├── DATABASE.md             # ER / 数据模型
│   ├── MODULE.md               # 模块设计
│   └── DEPLOYMENT.md           # 部署架构
│
├── 03-api/
│   ├── OPENAPI.yaml            # 接口契约
│   ├── API_GUIDE.md            # API 说明
│   └── ERROR_CODE.md           # 错误码规范
│
├── 04-rules/
│   ├── AI_RULES.md             # AI 编码规则（最重要）
│   ├── DIRECTORY.md            # 项目目录规范
│   ├── CODING_STYLE.md         # 编码规范
│   └── ADR.md                  # 架构决策记录
│
└── 05-test/
    ├── TEST_STRATEGY.md        # 测试策略
    ├── ACCEPTANCE.md           # 验收标准
    └── DoD.md                  # Definition of Done
```

建议阅读顺序：

1. `docs/04-rules/AI_RULES.md`
2. `docs/01-product/PRD.md`
3. `docs/01-product/MVP.md`
4. `docs/01-product/BACKLOG.md`
5. `docs/02-design/ARCHITECTURE.md`
6. `docs/02-design/MODULE.md`
7. `docs/03-api/API_GUIDE.md`
8. `docs/05-test/ACCEPTANCE.md`

---

## 3. 代码结构

```text
auto-test-platform/
├── docs/                       # 项目文档
├── src/                        # 后端代码
│   ├── app/
│   │   ├── common/             # 公共模块
│   │   ├── domain/             # 领域模块
│   │   ├── infrastructure/     # 基础设施
│   │   └── interfaces/         # HTTP 接口
│   └── tests/                  # 后端测试
├── frontend/                   # 前端工程
├── migrations/                 # Alembic 迁移
├── scripts/                    # 辅助脚本
└── README.md
```

---

## 4. 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| Python 3.12 | 编程语言 |
| FastAPI | Web 框架和 OpenAPI 文档 |
| Pydantic v2 | 请求/响应模型校验 |
| SQLAlchemy 2.x | ORM |
| Alembic | 数据库迁移 |
| PostgreSQL | 主数据库 |
| httpx | API 测试执行 HTTP 客户端 |
| pytest | 自动化测试 |

### 前端

| 技术 | 用途 |
|------|------|
| React | 管理页面 |
| TypeScript | 类型安全 |
| Vite | 构建工具 |
| Ant Design | UI 组件 |
| Zustand | 轻量状态管理 |
| Axios | 后端接口调用 |

---

## 5. 快速开始

### 5.1 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+
- uv

### 5.2 后端启动

```bash
uv sync
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --app-dir src
```

启动后访问：

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

### 5.3 前端启动

```bash
cd frontend
npm install
npm run dev
```

---

## 6. 测试

```bash
pytest src/tests
```

涉及前端时：

```bash
cd frontend
npm run build
```

---

## 7. 设计原则

- 第一性原理：先识别 API 测试闭环的本质数据和行为。
- 奥姆剃刀原则：当前阶段只保留必要功能，拒绝过度设计。
- KISS：优先清晰、直接、可维护的实现。
- 可测试：核心逻辑必须有单元测试或 API 测试覆盖。
