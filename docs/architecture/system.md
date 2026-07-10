# 系统架构设计文档

## 1. 架构概述

### 1.1 架构风格
采用领域驱动设计（DDD）+ 分层架构

### 1.2 系统架构图
```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│                    (React + TypeScript)                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                           │
│              (Nginx / Traefik / CloudFlare)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Interface Layer                             │
│          (FastAPI Routers + Middleware + DTOs)                   │
├─────────────────────────────────────────────────────────────────┤
│                       Domain Layer                               │
│    (Entities + Value Objects + Domain Services + Repositories)   │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                          │
│      (Database + External APIs + Message Queue + Cache)          │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 分层说明

### 2.1 接口层 (Interface Layer)
**职责：** 处理HTTP请求和响应

| 组件 | 说明 |
|------|------|
| Routers | API路由定义 |
| Middleware | 请求/响应拦截器 |
| DTOs | 数据传输对象（Pydantic） |
| Dependencies | 依赖注入 |

### 2.2 领域层 (Domain Layer)
**职责：** 核心业务逻辑

| 组件 | 说明 |
|------|------|
| Entities | 领域实体（User, Project等） |
| Value Objects | 值对象（Email, Password等） |
| Domain Services | 领域服务 |
| Repository Interfaces | 仓储接口定义 |
| Domain Events | 领域事件 |

### 2.3 基础设施层 (Infrastructure Layer)
**职责：** 技术实现细节

| 组件 | 说明 |
|------|------|
| Database | SQLAlchemy ORM |
| External APIs | HTTP客户端 |
| Cache | Redis缓存 |
| Message Queue | 消息队列 |

## 3. 目录结构

> 说明：实际代码位于仓库 `src/` 目录下（与 README 一致）。为便于切换，本节两种写法等价。

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI入口
│   ├── config.py               # 配置管理
│   │
│   ├── common/                 # 公共模块
│   │   ├── dependencies.py     # 依赖注入
│   │   ├── exceptions.py       # 自定义异常
│   │   └── security.py         # 安全工具
│   │
│   ├── domain/                 # 领域层
│   │   ├── user/               # 用户领域
│   │   │   ├── model.py        # 实体模型
│   │   │   ├── schema.py       # DTO
│   │   │   ├── repository.py   # 仓储实现
│   │   │   └── service.py      # 领域服务
│   │   ├── role/               # 角色领域
│   │   └── api_test/           # API测试领域
│   │       ├── model.py
│   │       ├── schema.py
│   │       ├── repository.py
│   │       └── service.py
│   │
│   ├── infrastructure/         # 基础设施层
│   │   └── database/
│   │       └── session.py      # 数据库连接
│   │
│   └── interfaces/             # 接口层
│       └── http/
│           ├── auth_router.py  # 认证路由
│           ├── user_router.py  # 用户路由
│           └── api_router.py   # API测试路由
│
├── migrations/                 # 数据库迁移
├── tests/                      # 测试代码
├── alembic.ini
└── requirements.txt
```

## 4. 技术选型

### 4.1 后端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.115+ | Web框架 |
| SQLAlchemy | 2.0+ | ORM |
| Pydantic | 2.9+ | 数据验证 |
| Alembic | 1.13+ | 数据库迁移 |
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存 |

### 4.2 前端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI框架 |
| TypeScript | 5+ | 类型安全 |
| Ant Design | 5+ | UI组件 |
| React Query | 5+ | 数据请求 |
| React Router | 6+ | 路由管理 |

## 5. 部署架构

### 5.1 开发环境
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│ PostgreSQL  │
│  localhost  │     │  localhost  │     │  localhost  │
│   :3000     │     │   :8000     │     │   :5432     │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 5.2 生产环境
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CDN     │───▶│  Nginx   │───▶│  App     │───▶│Database  │
│(CloudFlare)│   │(Reverse  │    │(Docker)  │    │(Managed  │
│          │    │  Proxy)  │    │          │    │ Postgres)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

## 6. 安全设计

### 6.1 认证机制
- JWT Token 认证
- Access Token + Refresh Token 双Token机制
- Token 黑名单（Redis）

### 6.2 授权机制
- RBAC（基于角色的访问控制）
- 细粒度权限控制

### 6.3 数据安全
- 密码 bcrypt 加密
- 敏感数据加密存储
- SQL注入防护（ORM）
- XSS防护

## 7. 扩展性设计

### 7.1 水平扩展
- 无状态API设计
- 分布式Session（Redis）
- 数据库读写分离

### 7.2 垂直扩展
- 模块化解耦
- 异步任务队列
- 缓存策略