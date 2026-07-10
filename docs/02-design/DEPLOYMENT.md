# 部署架构

> 范围：API 自动化测试平台 MVP。  
> 原则：开发简单、生产稳定，不提前引入 Kubernetes 和复杂运维体系。

---

## 1. 部署目标

- 后端 FastAPI 可稳定运行。
- PostgreSQL 数据可持久化。
- 前端可访问后端 API。
- 生产环境支持 Nginx 反向代理和 HTTPS。
- 使用 Docker Compose 满足 MVP 部署。

---

## 2. 开发环境

```text
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ React / Vite │ ───▶  │   FastAPI    │ ───▶  │  PostgreSQL  │
│ localhost    │       │ localhost    │       │ localhost    │
│ :5173        │       │ :8000        │       │ :5432        │
└──────────────┘       └──────────────┘       └──────────────┘
```

启动方式：

```bash
uv sync
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --app-dir src
```

前端：

```bash
cd frontend
npm install
npm run dev
```

---

## 3. Docker Compose 环境

```text
┌──────────────┐       ┌──────────────┐
│ app          │ ───▶  │ postgres     │
│ FastAPI      │       │ database     │
└──────────────┘       └──────────────┘
```

适用场景：

- 本地集成验证。
- 测试环境部署。
- MVP 小规模生产部署。

---

## 4. MVP 生产架构

```text
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    Nginx     │ ───▶  │ FastAPI App  │ ───▶  │  PostgreSQL  │
│ HTTPS/Proxy  │       │ Container    │       │  Managed/VM  │
└──────────────┘       └──────────────┘       └──────────────┘
```

职责：

| 组件 | 职责 |
|------|------|
| Nginx | HTTPS、反向代理、静态资源托管 |
| FastAPI App | API 服务和测试执行器 |
| PostgreSQL | 持久化项目、用例、执行、结果 |

---

## 5. 配置项

必须通过环境变量配置：

- 数据库连接。
- JWT Secret。
- Token 过期时间。
- CORS 白名单。
- 日志级别。
- API 执行默认超时时间。

禁止：

- 硬编码密钥。
- 将生产密钥提交到 Git。

---

## 6. 数据库迁移

统一使用 Alembic：

```bash
alembic upgrade head
```

规则：

- 修改数据库结构必须提交迁移文件。
- 禁止生产环境手工改表。
- 迁移前必须备份生产数据库。

---

## 7. 日志与排错

MVP 至少记录：

- 服务启动日志。
- 接口访问错误。
- 认证失败。
- API 测试执行摘要。
- 执行异常和超时。

禁止记录：

- 密码。
- Token。
- Cookie。
- Secret。

---

## 8. 后续扩展

只有当 MVP 稳定后再考虑：

- Redis Token 黑名单和缓存。
- 定时任务调度。
- 独立执行 Worker。
- CI/CD Webhook。
- Kubernetes / Helm。
- 日志聚合和监控告警。
