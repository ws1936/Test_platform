# 用户管理模块需求文档

## 1. 功能概述

### 1.1 模块名称
用户管理模块

### 1.2 功能描述
提供用户信息管理、角色权限管理等功能。

## 2. 用户故事

### US-101 查看用户列表
**作为** 管理员
**我希望** 能够查看所有用户列表
**以便** 管理平台用户

**验收标准：**
- 支持分页查询
- 支持按邮箱、姓名搜索
- 显示用户基本信息和状态

### US-102 编辑用户信息
**作为** 管理员
**我希望** 能够编辑用户信息
**以便** 维护用户数据

**验收标准：**
- 可修改用户姓名
- 可修改用户状态（启用/禁用）
- 可修改用户角色

### US-103 删除用户
**作为** 管理员
**我希望** 能够删除用户
**以便** 清理无效账号

**验收标准：**
- 软删除机制（标记删除）
- 删除后用户无法登录
- 数据保留用于审计

### US-104 修改个人信息
**作为** 普通用户
**我希望** 能够修改我的个人信息
**以便** 更新我的资料

**验收标准：**
- 可修改姓名
- 可修改密码
- 不可修改邮箱（需特殊流程）

## 3. 数据模型

### 3.1 User 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| email | VARCHAR(255) | 邮箱（唯一） |
| hashed_password | VARCHAR(255) | 加密密码 |
| full_name | VARCHAR(100) | 姓名 |
| is_active | BOOLEAN | 是否启用 |
| is_superuser | BOOLEAN | 是否管理员 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| deleted_at | TIMESTAMP | 删除时间（软删除） |

### 3.2 Role 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(50) | 角色名称 |
| description | VARCHAR(255) | 角色描述 |
| permissions | JSON | 权限列表 |
| created_at | TIMESTAMP | 创建时间 |

### 3.3 UserRole 关联表
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | UUID | 用户ID |
| role_id | UUID | 角色ID |

## 4. 接口设计

### 4.1 获取用户列表
```
GET /api/v1/users
Query:
  - page: 页码（默认1）
  - size: 每页数量（默认20）
  - search: 搜索关键词
Headers:
  Authorization: Bearer xxx
Response:
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20
}
```

### 4.2 获取用户详情
```
GET /api/v1/users/{user_id}
Headers:
  Authorization: Bearer xxx
Response:
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "张三",
  "is_active": true,
  "is_superuser": false,
  "roles": [...],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### 4.3 更新用户
```
PUT /api/v1/users/{user_id}
Request:
{
  "full_name": "新名字",
  "is_active": true,
  "role_ids": ["uuid1", "uuid2"]
}
```

### 4.4 删除用户
```
DELETE /api/v1/users/{user_id}
```

### 4.5 修改密码
```
PUT /api/v1/users/me/password
Request:
{
  "old_password": "old123",
  "new_password": "new12345"
}
```

## 5. 权限设计

### 5.1 角色定义
| 角色 | 说明 | 权限 |
|------|------|------|
| admin | 管理员 | 所有权限 |
| manager | 经理 | 用户管理、测试管理 |
| tester | 测试员 | 测试执行、报告查看 |
| viewer | 观察者 | 仅查看权限 |

### 5.2 权限矩阵
| 功能 | admin | manager | tester | viewer |
|------|-------|---------|--------|--------|
| 查看用户 | ✓ | ✓ | ✗ | ✗ |
| 编辑用户 | ✓ | ✓ | ✗ | ✗ |
| 删除用户 | ✓ | ✗ | ✗ | ✗ |
| 查看测试 | ✓ | ✓ | ✓ | ✓ |
| 执行测试 | ✓ | ✓ | ✓ | ✗ |
| 查看报告 | ✓ | ✓ | ✓ | ✓ |

## 6. 测试要点

### 6.1 功能测试
- [ ] 用户列表查询
- [ ] 用户详情查询
- [ ] 用户信息修改
- [ ] 用户删除
- [ ] 密码修改

### 6.2 权限测试
- [ ] 管理员权限验证
- [ ] 普通用户权限验证
- [ ] 越权操作拦截

### 6.3 数据测试
- [ ] 分页正确性
- [ ] 搜索准确性
- [ ] 软删除验证