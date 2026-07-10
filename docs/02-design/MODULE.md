# 模块设计

> 本文描述 API 自动化测试平台 MVP 的模块边界、核心流程和关键算法。

---

## 1. 模块总览

| 模块 | 类型 | 说明 |
|------|------|------|
| Auth | 支撑 | 登录、Token、退出、当前用户 |
| User | 支撑 | 用户资料、状态、密码 |
| Role | 支撑 | 简单角色和权限边界 |
| Project | 核心 | API 测试项目 |
| Environment | 核心 | Base URL、Headers、Variables |
| Collection | 核心 | 用例分组 |
| TestCase | 核心 | 请求定义和断言规则 |
| TestRun | 核心 | 执行批次 |
| TestResult | 核心 | 单条结果 |
| TestEngine | 核心 | 变量替换、请求执行、断言 |

---

## 2. Auth 模块

职责：

- 用户登录。
- Access Token 生成和校验。
- Refresh Token 刷新。
- 退出登录。
- 当前用户获取。

边界：

- 不实现复杂单点登录。
- 不实现 OAuth2 第三方登录。

---

## 3. User / Role 模块

职责：

- 管理用户基础信息。
- 管理用户启用/禁用。
- 修改密码。
- 管理角色。
- 提供简单 RBAC。

MVP 角色：

- `admin`
- `tester`
- `viewer`

边界：

- 不做多角色绑定。
- 不做组织架构。
- 不做多租户数据权限。

---

## 4. Project 模块

职责：

- 管理 API 测试项目。
- 作为环境、集合、用例和执行记录的归属边界。

核心规则：

- 项目必须有 owner。
- 删除项目时需要明确处理其下环境、集合、用例和执行记录。
- MVP 可采用逻辑删除或限制已有执行记录的项目删除。

---

## 5. Environment 模块

职责：

- 管理项目下的执行环境。
- 提供 `base_url`、公共 `headers`、环境变量。

核心规则：

- 同一项目下环境名称唯一。
- 一个项目最多一个默认环境。
- 执行未指定环境时使用默认环境。

---

## 6. Collection 模块

职责：

- 对 API 用例进行分组。

MVP 规则：

- 只做一层集合。
- 不做拖拽排序和多级目录。

---

## 7. TestCase 模块

职责：

- 保存 API 请求定义。
- 保存断言配置。
- 控制用例启用/禁用。

核心字段：

- `method`
- `path`
- `headers`
- `query_params`
- `body_type`
- `body`
- `assertions`
- `timeout_seconds`

---

## 8. TestEngine 模块

### 8.1 执行步骤

```text
读取环境和用例
  ↓
构建变量上下文
  ↓
替换变量
  ↓
构造 HTTP 请求
  ↓
发送请求
  ↓
执行断言
  ↓
生成结果
```

### 8.2 变量替换

输入：字符串、数组或对象。  
输出：替换后的数据结构。

伪代码：

```python
def resolve(value, context):
    if isinstance(value, str):
        return replace_placeholders(value, context)
    if isinstance(value, list):
        return [resolve(item, context) for item in value]
    if isinstance(value, dict):
        return {key: resolve(item, context) for key, item in value.items()}
    return value
```

### 8.3 请求构造

| 数据 | 来源 |
|------|------|
| URL | `environment.base_url + test_case.path` |
| Headers | 环境 Headers + 用例 Headers，用例覆盖环境 |
| Query | 用例 Query Params |
| Body | 根据 body_type 生成 |
| Timeout | 用例超时或默认 30 秒 |

### 8.4 断言执行

规则：

- 每条断言都返回结果。
- 任一断言失败，用例结果为 `failed`。
- 配置错误、超时、连接异常，用例结果为 `error`。
- 所有断言通过，用例结果为 `passed`。

---

## 9. TestRun / TestResult 模块

### 9.1 TestRun

一次执行批次，负责记录：

- 执行范围。
- 使用环境。
- 触发人。
- 执行状态。
- 汇总统计。

### 9.2 TestResult

单条用例结果，负责记录：

- 实际请求。
- 实际响应。
- 断言结果。
- 错误信息。
- 耗时。

---

## 10. 状态流转

### 10.1 TestRun

```text
pending → running → finished
                   ↘ failed
                   ↘ canceled
```

### 10.2 TestResult

| 状态 | 说明 |
|------|------|
| `passed` | 全部断言通过 |
| `failed` | 请求完成但断言失败 |
| `error` | 请求异常、变量错误或断言配置错误 |
| `skipped` | 用例禁用或未执行 |

---

## 11. 安全边界

禁止：

- 执行用户自定义 Python / JavaScript 脚本。
- 记录 Token、Password、Cookie 到日志。
- 无超时访问被测 API。
- 未认证用户触发执行。
