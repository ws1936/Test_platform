# API 设计文档

## 1. API 规范

### 1.1 基础规范
- 基础路径：`/api/v1`
- 数据格式：JSON
- 字符编码：UTF-8
- 认证方式：JWT Bearer Token

### 1.2 统一响应格式

**成功响应：**
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {}
}
```

**分页响应：**
```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "size": 20,
    "pages": 5
  }
}
```

**错误响应：**
```json
{
  "code": "ERROR_CODE",
  "message": "错误描述",
  "details": {}
}
```

### 1.3 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无内容） |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 数据验证失败 |
| 500 | 服务器内部错误 |

## 2. API 列表

### 2.1 认证模块 `/api/v1/auth`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /auth/register | 用户注册 | 否 |
| POST | /auth/login | 用户登录 | 否 |
| POST | /auth/refresh | 刷新Token | 否 |
| GET | /auth/me | 获取当前用户 | 是 |
| PUT | /me/password | 修改密码 | 是 |

### 2.2 用户管理 `/api/v1/users`

| 方法 | 路径 | 说明 | 认证 | 权限 |
|------|------|------|------|------|
| GET | /users | 用户列表 | 是 | admin/manager |
| GET | /users/{id} | 用户详情 | 是 | admin/manager |
| PUT | /users/{id} | 更新用户 | 是 | admin/manager |
| DELETE | /users/{id} | 删除用户 | 是 | admin |

### 2.3 API项目 `/api/v1/projects`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /projects | 创建项目 | 是 |
| GET | /projects | 项目列表 | 是 |
| GET | /projects/{id} | 项目详情 | 是 |
| PUT | /projects/{id} | 更新项目 | 是 |
| DELETE | /projects/{id} | 删除项目 | 是 |

### 2.4 测试集合 `/api/v1/collections`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /projects/{project_id}/collections | 创建集合 | 是 |
| GET | /projects/{project_id}/collections | 集合列表 | 是 |
| PUT | /collections/{id} | 更新集合 | 是 |
| DELETE | /collections/{id} | 删除集合 | 是 |

### 2.5 测试用例 `/api/v1/cases`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /collections/{collection_id}/cases | 创建用例 | 是 |
| GET | /collections/{collection_id}/cases | 用例列表 | 是 |
| GET | /cases/{id} | 用例详情 | 是 |
| PUT | /cases/{id} | 更新用例 | 是 |
| DELETE | /cases/{id} | 删除用例 | 是 |

### 2.6 测试执行 `/api/v1/runs`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /projects/{project_id}/runs | 创建执行 | 是 |
| GET | /projects/{project_id}/runs | 执行列表 | 是 |
| GET | /runs/{id} | 执行详情 | 是 |
| GET | /runs/{id}/results | 执行结果 | 是 |
| POST | /runs/{id}/stop | 停止执行 | 是 |

## 3. 详细接口设计

### 3.1 用户注册

**请求：**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "张三"
}
```

**响应 201：**
```json
{
  "code": "SUCCESS",
  "message": "注册成功",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "张三",
      "is_active": true,
      "is_superuser": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    },
    "token": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer",
      "expires_in": 1800
    }
  }
}
```

### 3.2 用户登录

**请求：**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应 200：**
```json
{
  "code": "SUCCESS",
  "message": "登录成功",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "张三",
      "is_active": true,
      "is_superuser": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    },
    "token": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer",
      "expires_in": 1800
    }
  }
}
```

### 3.3 创建API项目

**请求：**
```http
POST /api/v1/projects
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "用户服务API",
  "description": "用户服务的接口测试",
  "base_url": "https://api.example.com"
}
```

**响应 201：**
```json
{
  "code": "SUCCESS",
  "message": "创建成功",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "用户服务API",
    "description": "用户服务的接口测试",
    "base_url": "https://api.example.com",
    "owner_id": "550e8400-e29b-41d4-a716-446655440001",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### 3.4 创建测试用例

**请求：**
```http
POST /api/v1/collections/{collection_id}/cases
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "获取用户列表",
  "method": "GET",
  "url": "/api/users",
  "headers": {
    "Accept": "application/json"
  },
  "query_params": {
    "page": "1",
    "size": "20"
  },
  "assertions": [
    {
      "type": "status_code",
      "expected": 200,
      "operator": "eq"
    },
    {
      "type": "json_path",
      "path": "$.data.items",
      "operator": "exists"
    }
  ]
}
```

### 3.5 执行测试

**请求：**
```http
POST /api/v1/projects/{project_id}/runs
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "name": "回归测试 v1.0",
  "environment_id": "550e8400-e29b-41d4-a716-446655440002",
  "collection_ids": ["550e8400-e29b-41d4-a716-446655440003"]
}
```

**响应 201：**
```json
{
  "code": "SUCCESS",
  "message": "执行已创建",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440004",
    "name": "回归测试 v1.0",
    "status": "running",
    "total_count": 10,
    "passed_count": 0,
    "failed_count": 0,
    "skipped_count": 0,
    "started_at": "2024-01-01T00:00:00Z"
  }
}
```

## 4. 错误码定义

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| VALIDATION_ERROR | 422 | 数据验证失败 |
| UNAUTHORIZED | 401 | 未认证 |
| FORBIDDEN | 403 | 无权限 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| TOKEN_EXPIRED | 401 | Token已过期 |
| TOKEN_INVALID | 401 | Token无效 |
| USER_EXISTS | 409 | 用户已存在 |
| INVALID_CREDENTIALS | 401 | 凭证无效 |