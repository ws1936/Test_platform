# 功能待办列表 Backlog

> 范围：API 自动化测试平台 MVP 及后续演进。  
> 用途：统一记录功能项、优先级和当前状态，作为开发排期入口。

---

## 1. 状态说明

| 状态 | 说明 |
|------|------|
| Todo | 待开发 |
| Doing | 开发中 |
| Done | 已完成 |
| Blocked | 阻塞 |
| Later | 后续再做 |

---

## 2. 优先级说明

| 优先级 | 说明 |
|--------|------|
| P0 | MVP 必须完成，影响 API 测试闭环 |
| P1 | MVP 后增强能力，提升效率或体验 |
| P2 | 中长期能力，当前不进入 MVP |

---

## 3. 功能 Backlog

| ID | Feature | 优先级 | 状态 | 说明 |
|----|---------|--------|------|------|
| F001 | 用户登录 | P0 | Done | 已具备登录、JWT 鉴权能力 |
| F002 | 用户管理 | P0 | Done | 已具备基础用户 CRUD、禁用、改密码能力 |
| F003 | 角色管理 | P0 | Done | 已具备基础角色 CRUD，后续可完善细粒度权限 |
| F004 | 项目管理 | P0 | Done | API 测试项目 CRUD + owner/superuser 鉴权 + 跨用户隔离 |
| F005 | 环境管理 | P0 | Done | Base URL、Headers、Variables、默认环境（单项目唯一 + 默认互斥 + 默认不可删除） |
| F006 | 集合管理 | P0 | Done | Suite CRUD + 批量添加用例（事务 + 幂等 + 默认排序 + 项目内唯一 + owner 鉴权） |
| F007 | API 用例管理 | P0 | Done | 用例 CRUD + 启用/禁用 + 套件/项目双维度列表 + owner 鉴权 + suite_cases 级联清理 |
| F008 | 变量替换 | P0 | Done | `${var}` 占位符替换 + `${timestamp}` 内置变量 + 缺失变量保留占位符并 WARNING + 调用方控制合并优先级（无 Router/DB） |
| F009 | 断言引擎 | P0 | Done | 5 种断言 × 12 个操作符规则化引擎 + 集成 F008 变量替换 + 手写 json_path + RFC7230 header 大小写不敏感 + 错误码 31003/31004/31005（无 Router/DB） |
| F010 | pytest / API 执行 | P0 | Done | httpx 同步执行 + RequestBuilder/ApiExecutor/TestRunner 引擎 + 6 个 HTTP 端点 + 错误码 32001/32002/32003 + 敏感头脱敏 + 64KB body 截断 + 复用 F008/F009（无 Celery/Redis） |
| F011 | 测试报告 | P0 | Done | 3 个聚合端点（单 run 概览 / 项目级概览 / 失败原因列表）+ TestRunResponse 新增 pass_rate/elapsed_seconds 计算字段 + list_project_runs 加 status 过滤 + 无新表（复用 F010 表） |
| F012 | Swagger / OpenAPI 导入 | P1 | Done | 从 OpenAPI 3.x 文档生成基础 API 用例 + stdlib 解析 + 1 个 POST 端点（?dry_run=true） + 复用 F006/F007 零新表 |
| F013 | 批量生成基础用例 | P1 | Todo | 基于导入接口批量生成用例草稿 |
| F014 | 有限并发执行 | P1 | Todo | 提升执行效率，但不做分布式执行 |
| F015 | 报告导出 | P1 | Todo | JSON / HTML 导出，Allure 可作为后续方向 |
| F016 | 前端 API 测试页面 | P1 | Todo | 项目、环境、用例、执行、报告管理页面 |
| F017 | 定时执行 | P2 | Later | 当前不进入 MVP，待执行闭环稳定后评估 |
| F018 | 消息通知 | P2 | Later | 企业微信、钉钉、邮件等通知能力 |
| F019 | CI/CD Webhook | P2 | Later | 与流水线集成触发或回传结果 |
| F020 | AI 生成 Case | P2 | Later | 基于接口定义生成测试用例，需安全和数据治理评估 |

---

## 4. 当前 MVP 开发顺序建议

```text
F004 项目管理
  ↓
F005 环境管理
  ↓
F006 集合管理
  ↓
F007 API 用例管理
  ↓
F008 变量替换
  ↓
F009 断言引擎
  ↓
F010 pytest / API 执行
  ↓
F011 测试报告
```

---

## 5. 维护规则

1. 新增功能必须先进入 Backlog。
2. P0 功能必须能支撑 API 测试最小闭环。
3. P1/P2 功能不得抢占 P0 开发顺序。
4. 状态变化需要同步更新本文件。
5. 扩大 MVP 范围必须补充 `docs/04-rules/ADR.md`。
