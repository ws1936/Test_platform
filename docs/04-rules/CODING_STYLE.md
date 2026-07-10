# 编码规范

> 范围：API 自动化测试平台 MVP。  
> 原则：清晰优先、类型明确、职责单一、可测试。

---

## 1. 通用原则

- 命名必须表达业务含义。
- 函数只做一件事。
- 避免过度抽象。
- 避免魔法数字。
- 避免重复代码。
- 错误必须显式处理。
- 敏感信息不得进入日志。

---

## 2. Python 规范

### 2.1 命名

| 对象 | 规范 | 示例 |
|------|------|------|
| 变量/函数 | snake_case | `create_test_run` |
| 类 | PascalCase | `TestRunService` |
| 常量 | UPPER_CASE | `DEFAULT_TIMEOUT_SECONDS` |
| 私有方法 | `_snake_case` | `_build_request` |

### 2.2 类型标注

必须为函数参数和返回值添加类型标注：

```python
def get_case(case_id: UUID) -> ApiTestCase:
    ...
```

### 2.3 分层约束

- Router 不直接操作数据库。
- Service 不依赖 FastAPI Request 对象。
- Repository 不写业务决策。
- Model 不包含复杂业务流程。

### 2.4 异常处理

- 业务异常转换为统一错误响应。
- 不吞掉异常。
- 外部请求异常必须记录摘要。
- 日志必须脱敏。

---

## 3. FastAPI 规范

- Router 使用清晰的 prefix 和 tags。
- 请求体使用 Pydantic Schema。
- 响应体使用 Pydantic Schema。
- 受保护接口必须依赖当前用户。
- 接口必须能生成 OpenAPI 文档。

---

## 4. SQLAlchemy 规范

- 每张业务表包含 `id`、`created_at`、`updated_at`。
- 数据库结构变化必须使用 Alembic。
- 查询逻辑放 Repository。
- 不在业务代码中拼接原始 SQL，除非有明确理由。

---

## 5. API 测试引擎规范

- 变量替换逻辑必须独立可测。
- 断言逻辑必须独立可测。
- HTTP 执行必须设置超时。
- 执行结果必须保存请求、响应、断言快照。
- 禁止执行用户提交的任意脚本。

---

## 6. TypeScript / React 规范

- 组件使用 PascalCase。
- hooks 使用 `useXxx` 命名。
- API 请求集中封装在 `src/api`。
- 登录态放在 Zustand store。
- 表单字段与后端 Schema 尽量保持一致。

---

## 7. 禁止事项

- 禁止 `print()` 调试后提交。
- 禁止硬编码密钥。
- 禁止日志输出 Token、Password、Cookie。
- 禁止超长函数和超长类。
- 禁止复制粘贴大段重复逻辑。
- 禁止引入未经 ADR 批准的新核心框架。
