# 项目目录规范

> 目标：让代码和文档结构稳定、可查找、可维护。  
> 当前项目聚焦 API 自动化测试平台 MVP。

---

## 1. 文档目录规范

```text
docs/
├── 01-product/
│   ├── PRD.md
│   ├── MVP.md
│   ├── ROADMAP.md
│   └── BACKLOG.md
├── 02-design/
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── MODULE.md
│   └── DEPLOYMENT.md
├── 03-api/
│   ├── OPENAPI.yaml
│   ├── API_GUIDE.md
│   └── ERROR_CODE.md
├── 04-rules/
│   ├── AI_RULES.md
│   ├── DIRECTORY.md
│   ├── CODING_STYLE.md
│   └── ADR.md
└── 05-test/
    ├── TEST_STRATEGY.md
    ├── ACCEPTANCE.md
    └── DoD.md
```

### 1.1 编号规则

- `01-product`：产品目标、范围、路线图、功能待办。
- `02-design`：架构、数据库、模块、部署。
- `03-api`：接口契约、接口说明、错误码。
- `04-rules`：AI、目录、编码、ADR 规则。
- `05-test`：测试策略、验收标准、完成定义。

### 1.2 文档维护规则

- 需求变化先更新 `01-product`。
- 架构或数据模型变化必须更新 `02-design`。
- 接口变化必须更新 `03-api/OPENAPI.yaml` 和 `03-api/API_GUIDE.md`。
- 工程约束变化必须更新 `04-rules`。
- 测试范围变化必须更新 `05-test`。

---

## 2. 后端目录规范

```text
src/
└── app/
    ├── main.py
    ├── config.py
    ├── common/
    │   ├── dependencies.py
    │   ├── exceptions.py
    │   ├── responses.py
    │   └── security.py
    ├── domain/
    │   ├── user/
    │   ├── role/
    │   └── api_test/
    ├── infrastructure/
    │   └── database/
    └── interfaces/
        └── http/
```

### 2.1 分层规则

- `interfaces/http`：只放 HTTP Router。
- `domain/*/service.py`：业务逻辑和流程编排。
- `domain/*/repository.py`：数据库访问。
- `domain/*/model.py`：SQLAlchemy 模型。
- `domain/*/schema.py`：Pydantic Schema。
- `common`：通用异常、响应、安全、依赖。
- `infrastructure`：数据库和外部技术实现。

### 2.2 API 测试模块建议结构

```text
src/app/domain/api_test/
├── model.py
├── schema.py
├── repository.py
├── service.py
└── engine/
    ├── variables.py
    ├── request_builder.py
    ├── executor.py
    └── assertions.py
```

---

## 3. 前端目录规范

```text
frontend/src/
├── api/
├── pages/
├── store/
├── components/
└── main.tsx
```

规则：

- API 请求封装放在 `api/`。
- 页面级组件放在 `pages/`。
- 全局状态放在 `store/`。
- 可复用组件放在 `components/`。

---

## 4. 测试目录规范

```text
src/tests/
├── conftest.py
├── test_auth.py
├── test_user_crud.py
└── test_api_test_*.py
```

规则：

- 新增后端接口必须补 API 测试。
- 变量替换、断言引擎必须补单元测试。
- 测试文件命名使用 `test_*.py`。

---

## 5. 禁止事项

- 禁止在 Router 中直接访问数据库。
- 禁止将业务逻辑写入迁移脚本。
- 禁止把临时脚本散落在项目根目录。
- 禁止新增未归档的 Markdown 文档。
- 禁止文档与代码长期不一致。
