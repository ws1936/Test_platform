# API 使用说明

> 范围：API 自动化测试平台 MVP。  
> 所有接口统一使用 `/api/v1` 前缀。

---

## 1. 基础规范

| 项 | 约定 |
|----|------|
| 基础路径 | `/api/v1` |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| 认证方式 | `Authorization: Bearer <access_token>` |
| 时间格式 | ISO 8601 |
| ID 类型 | UUID |

---

## 2. 统一响应

### 2.1 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 2.2 分页响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "size": 20
  }
}
```

### 2.3 错误响应

```json
{
  "code": 10001,
  "message": "Project Not Found",
  "data": null
}
```

---

## 3. API 列表

### 3.1 认证

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/auth/register` | 注册。首个用户自动成为超级管理员；后续注册需超级管理员 Token | 否/是* |
| POST | `/auth/login` | 登录（邮箱 + 密码） | 否 |
| POST | `/auth/refresh` | 刷新 Token | 否 |
| POST | `/auth/logout` | 退出登录 | 是 |
| GET | `/auth/me` | 当前用户信息 | 是 |

*`/auth/register` 在系统中无任何用户时公开（首个用户为超级管理员）；其余情况需超级管理员 Token。

### 3.2 用户

| 方法 | 路径 | 说明 | 认证 | 权限 |
|------|------|------|------|------|
| GET | `/users` | 用户列表 | 是 | admin |
| GET | `/users/{user_id}` | 用户详情 | 是 | admin |
| PUT | `/users/{user_id}` | 更新用户 | 是 | admin |
| DELETE | `/users/{user_id}` | 禁用用户 | 是 | admin |
| PUT | `/users/me/password` | 修改当前用户密码 | 是 | 登录用户 |

### 3.3 角色

| 方法 | 路径 | 说明 | 认证 | 权限 |
|------|------|------|------|------|
| GET | `/roles` | 角色列表 | 是 | admin |
| POST | `/roles` | 创建角色 | 是 | admin |
| GET | `/roles/{role_id}` | 角色详情 | 是 | admin |
| PUT | `/roles/{role_id}` | 更新角色 | 是 | admin |
| DELETE | `/roles/{role_id}` | 删除角色 | 是 | admin |

### 3.4 项目

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/projects` | 创建项目 | 是 |
| GET | `/projects` | 项目列表 | 是 |
| GET | `/projects/{project_id}` | 项目详情 | 是 |
| PUT | `/projects/{project_id}` | 更新项目 | 是 |
| DELETE | `/projects/{project_id}` | 删除项目 | 是 |

### 3.5 环境

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/projects/{project_id}/environments` | 创建环境 | 是 |
| GET | `/projects/{project_id}/environments` | 环境列表 | 是 |
| GET | `/environments/{environment_id}` | 环境详情 | 是 |
| PUT | `/environments/{environment_id}` | 更新环境 | 是 |
| DELETE | `/environments/{environment_id}` | 删除环境 | 是 |

### 3.6 集合

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/projects/{project_id}/collections` | 创建集合 | 是 |
| GET | `/projects/{project_id}/collections` | 集合列表 | 是 |
| GET | `/collections/{collection_id}` | 集合详情 | 是 |
| PUT | `/collections/{collection_id}` | 更新集合 | 是 |
| DELETE | `/collections/{collection_id}` | 删除集合 | 是 |

### 3.7 用例（F007 已实现）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/collections/{suite_id}/cases` | 创建用例（同时关联到指定 suite） | 是 |
| GET | `/collections/{suite_id}/cases` | 列出该 suite 下的用例 | 是 |
| GET | `/projects/{project_id}/test-cases` | 列出项目下全部用例（含未归属 suite 的） | 是 |
| GET | `/test-cases/{case_id}` | 用例详情 | 是 |
| PUT | `/test-cases/{case_id}` | 更新用例 | 是 |
| DELETE | `/test-cases/{case_id}` | 删除用例（级联清理 suite 关联） | 是 |
| POST | `/test-cases/{case_id}/run` | 执行单用例（F010） | 是 |

说明：
- ``collection`` 在 API 上是历史命名，实际指向 F006 的 ``suite``。
- 创建用例时其 ``project_id`` 从 URL 中的 ``suite_id`` 推导，不接受请求体中的 ``project_id``。
- ``status``（int 0/1）在传输层暴露为 ``enabled``（bool）。
- ``POST /test-cases/{case_id}/run`` 需传入 ``environment_id`` 查询参数；返回结构与下面 `POST /projects/{project_id}/runs` 相同。

### 3.8 执行与报告（F010 已实现）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/projects/{project_id}/runs` | 创建并同步执行批次（scope: case/collection/project） | 是 |
| GET | `/projects/{project_id}/runs` | 执行历史（按创建时间倒序） | 是 |
| GET | `/runs/{run_id}` | 执行详情 | 是 |
| GET | `/runs/{run_id}/results` | 执行结果列表 | 是 |
| GET | `/results/{result_id}` | 单条结果详情 | 是 |

说明：
- ``POST /projects/{project_id}/runs`` 请求体：
  ```json
  {
    "name": "可选，未传则自动生成 'Run @ {ISO timestamp}'",
    "environment_id": "环境 UUID",
    "scope": "case | collection | project",
    "scope_id": "按 scope 解释为 case_id / suite_id / project_id"
  }
  ```
  返回结构是同步执行后的最终 run 状态（``status=finished``）。
- 同步执行是 MVP 行为：F014（有限并发）会改为后台任务 + 轮询状态。
- 每个 result 包含 ``request_snapshot`` / ``response_snapshot`` /
  ``assertions_snapshot``；响应体超过 64 KiB 会截断，并设置
  ``response_snapshot.body_truncated=true``。
- 敏感头（``Authorization`` / ``Cookie`` / ``Set-Cookie`` / ``X-Auth-Token``
  / ``X-API-Key`` / ``X-CSRF-Token``）在快照中被脱敏。
- 执行错误以单条 ``status="error"`` 结果行落库；``error_code`` 字段
  取值 ``API_EXECUTION_TIMEOUT`` (32002) / ``API_CONNECTION_ERROR`` (32003)
  / ``API_EXECUTION_ERROR`` (32001)，运行本身不报错。
- F011 报告会复用 ``TestRun`` / ``TestResult`` 表，因此 §3.8 暂不
  单独提供报告端点。

---

## 4. 关键请求示例

### 4.1 登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "password123"
}
```


### 4.2 创建环境

```http
POST /api/v1/projects/{project_id}/environments
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "test",
  "base_url": "https://api-test.example.com",
  "headers": {
    "Accept": "application/json"
  },
  "variables": {
    "token": "test-token",
    "user_id": "10001"
  },
  "is_default": true
}
```

### 4.3 创建用例

```http
POST /api/v1/collections/{collection_id}/cases
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "获取用户详情",
  "method": "GET",
  "path": "/api/users/{{user_id}}",
  "headers": {
    "Authorization": "Bearer {{token}}"
  },
  "query_params": {},
  "body_type": "none",
  "body": null,
  "timeout_seconds": 30,
  "assertions": [
    {
      "type": "status_code",
      "operator": "eq",
      "expected": 200
    }
  ]
}
```

### 4.4 执行项目

```http
POST /api/v1/projects/{project_id}/runs
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "用户服务回归测试",
  "environment_id": "environment-uuid",
  "scope": "project"
}
```

---

## 5. 枚举

| 枚举 | 值 |
|------|----|
| HTTP 方法 | GET, POST, PUT, PATCH, DELETE |
| Body 类型 | none, json, form, raw |
| 执行范围 | case, collection, project |
| 执行状态 | pending, running, finished, failed, canceled |
| 结果状态 | passed, failed, skipped, error |
