# API 自动化测试平台信息架构（IA）重设计

> 文档类型：产品信息架构设计  
> 适用范围：现有 API 自动化测试平台前端  
> 设计阶段：先设计，不涉及代码实现  
> 约束：不新增后端接口、不新增数据库、不修改已有 API

---

## 0. 结论摘要

本次 IA 的核心决策是：**以 Project 作为测试工作的唯一上下文边界**。

- `Dashboard`、`Project`、`用户管理`、`角色管理` 属于平台级能力。
- `Environment`、`Suite`、`API Case`、`Run`、`Report` 全部归入 Project 工作区。
- `OpenAPI Import` 不是独立业务对象，而是“向指定 Suite 导入 API Case”的上下文动作，因此放在 Suite / API Case 页面中，不占用全局一级菜单。
- `Run` 与 `Report` 明确分工：Run 负责“配置并发起执行”，Report 负责“查询、分析和定位结果”。
- 登录后的默认落点为 Dashboard；进入 Project 后，用户始终保留清晰的项目上下文，不需要在每个模块重复选择 Project。

目标结构：

```text
平台级
├── Dashboard
├── Project 列表
└── 系统管理（仅超级管理员）
    ├── 用户管理
    └── 角色管理

Project 工作区
├── 项目概览
├── 环境管理
├── 测试资产
│   ├── 测试套件 Suite
│   └── API 用例 API Case
├── 执行中心 Run
├── 测试报告 Report
└── 项目设置

上下文动作
└── OpenAPI Import（目标必须是某个 Suite）
```

---

## 1. 设计前提与能力边界

### 1.1 已有能力

| 领域 | 当前可用能力 |
|---|---|
| 认证 | 登录、Token 刷新、退出、当前用户信息、修改密码 |
| 用户 | 用户列表、详情、更新、启用/禁用、管理员创建账号 |
| 角色 | 角色列表、创建、详情、更新、删除，角色包含权限字符串 |
| Project | 创建、分页列表、名称搜索、详情、更新、删除 |
| Environment | 项目内创建、列表、名称搜索、详情、更新、删除、设置默认环境 |
| Suite | 项目内创建、列表、搜索、详情、更新、删除、批量添加用例、移除用例、用例排序 |
| API Case | Suite 内创建、Suite 维度列表、Project 维度列表、搜索、详情、更新、删除、启用/禁用 |
| Run | 单用例、Suite、Project 三种范围；选择环境；同步执行；执行历史 |
| Report | Project 聚合概览、Run 概览、结果列表、失败原因、单结果请求/响应/断言快照 |
| OpenAPI Import | OpenAPI 3.x 来源解析、标签过滤、冲突预览、跳过/覆盖策略、导入至指定 Suite |

### 1.2 必须遵守的业务事实

1. Environment、Suite、API Case、Run、Report 都从属于 Project。
2. API Case 创建时必须指定 Suite；Project 级用例列表也可能包含已从所有 Suite 移除的“未归套件用例”。
3. 一个 API Case 可以通过关联关系出现在 Suite 中，Suite 内用例支持排序。
4. Run 必须提交环境 ID；前端可以自动选中默认环境，但仍需向现有接口传入该 ID。
5. 执行为同步执行；当前没有任务队列、后台轮询、取消执行接口。
6. Report 是已有 Run / Result 数据的只读视图，不创建新的“报告实体”。
7. Project 列表当前只返回当前用户拥有的项目；不能设计“全平台项目库”或“共享给我的项目”。
8. Project 资产的后端访问边界是 Project owner 或 superuser；当前没有项目成员、项目协作者或多租户模型。

### 1.3 本次不设计的能力

以下内容没有现有能力支撑，不进入菜单、页面主路径或交互承诺：

- 项目成员与协作空间
- 多租户、组织架构、团队空间
- 定时执行、任务编排、消息通知
- CI/CD Webhook
- 批量并发或分布式执行
- 执行取消、暂停、队列进度
- 报告导出、分享链接、公开链接
- 高级趋势分析、自定义看板
- 用例复制、批量编辑、标签体系
- 多级 Suite 目录
- 自定义 Python / JavaScript 前后置脚本
- UI、性能、安全或 AI 测试

---

## 2. IA 设计原则

### 2.1 平台与 Project 两级作用域

- 平台级页面解决“我能进入哪里”和“平台由谁管理”。
- Project 级页面解决“在当前项目中配置、维护、执行和分析什么”。
- Project 级资源不进入全局一级菜单，避免用户每进入一个模块都重新选择项目。

### 2.2 先配置、再建资产、后执行、最后分析

Project 内导航按真实任务顺序组织：

```text
项目概览
  → 环境管理
  → Suite / API Case
  → 执行中心
  → 测试报告
```

### 2.3 对象与动作分离

- Project、Environment、Suite、API Case、Run、Report 是用户持续访问的信息对象或任务空间。
- OpenAPI Import 是一次性动作，必须依附目标 Suite，不作为一级菜单。
- “新建”“导入”“执行”“设置默认”等动作放在对应对象页面的主操作区。

### 2.4 单一主入口

- 一个对象只设一个规范详情入口。
- Run 执行完成后统一进入 Report 详情，不再创建一套重复的“Run 详情”和“Report 详情”。
- Suite 中点击用例与 API Case 列表中点击用例，最终都进入同一 API Case 详情页。

### 2.5 保留上下文

每个 Project 页面始终展示：

- 当前 Project 名称
- 当前模块
- 面包屑
- Project 切换入口
- 与当前任务相关的主操作

---

# ① 左侧菜单结构

## 3. 全局左侧菜单

### 3.1 未进入 Project 时

```text
[产品标识]

工作台
└── Dashboard

项目
└── Project 列表

系统管理                         仅 superuser 可见
├── 用户管理
└── 角色管理

[底部]
├── 当前用户摘要
└── 收起侧栏
```

### 3.2 进入 Project 后

左侧菜单在“项目”下增加动态的“当前 Project”分组；不再增加第二条永久侧栏。

```text
[产品标识]

工作台
└── Dashboard

项目
├── Project 列表
└── 当前 Project：用户服务 API      可切换 / 可折叠
    ├── 项目概览
    ├── 环境管理
    ├── 测试资产
    │   ├── 测试套件
    │   └── API 用例
    ├── 执行中心
    ├── 测试报告
    └── 项目设置

系统管理                           仅 superuser 可见
├── 用户管理
└── 角色管理

[底部]
├── 当前用户摘要
└── 收起侧栏
```

### 3.3 顶部账号区，不占左侧菜单

账号相关操作放在右上角用户菜单：

- 当前用户信息：读取现有 `/auth/me`
- 修改密码
- 退出登录

不设置“个人资料编辑”，因为当前只支持管理员更新用户资料，普通用户只有修改自己密码的能力。

### 3.4 菜单显隐规则

| 菜单 | 未登录 | 普通登录用户 | Project owner | superuser |
|---|---:|---:|---:|---:|
| Dashboard | 否 | 是 | 是 | 是 |
| Project 列表 | 否 | 是 | 是 | 是 |
| 当前 Project 导航 | 否 | 有权访问 Project 时 | 是 | 有权访问具体 Project 时 |
| 用户管理 | 否 | 否 | 否 | 是 |
| 角色管理 | 否 | 否 | 否 | 是 |
| 修改密码 / 退出 | 否 | 是 | 是 | 是 |

### 3.5 不采用的菜单结构

不建议采用以下扁平菜单：

```text
Dashboard / Project / Environment / Suite / API Case / Run / Report / OpenAPI Import
```

原因：

1. Environment 等对象没有脱离 Project 的独立意义。
2. 扁平结构会要求用户在每个页面重复选择 Project。
3. OpenAPI Import 必须先知道目标 Suite，独立入口会增加无效步骤。
4. Run 与 Report 会因缺少项目上下文形成大量重复筛选。
5. 页面 URL、面包屑和返回路径容易丢失 Project 归属。

---

# ② 页面层级

## 4. 页面树

```text
L0 认证层
└── 登录

L1 平台层
├── Dashboard
├── Project
│   ├── Project 列表
│   └── 新建 Project（弹窗或抽屉）
├── 系统管理
│   ├── 用户管理
│   │   ├── 用户列表
│   │   ├── 新建用户（弹窗或抽屉）
│   │   └── 用户详情 / 编辑（抽屉）
│   └── 角色管理
│       ├── 角色列表
│       ├── 新建角色（弹窗或抽屉）
│       └── 角色详情 / 编辑（抽屉）
└── 账号
    └── 修改密码（弹窗）

L2 Project 工作区
├── 项目概览
├── 环境管理
│   ├── 环境列表
│   ├── 新建环境
│   └── 环境详情 / 编辑
├── 测试资产
│   ├── 测试套件
│   │   ├── Suite 列表
│   │   ├── 新建 Suite
│   │   └── Suite 详情
│   │       ├── 已关联用例
│   │       ├── 添加已有用例
│   │       ├── 调整顺序
│   │       ├── 新建 API Case
│   │       └── OpenAPI Import
│   └── API 用例
│       ├── Project 全部用例列表
│       ├── 新建用例（必须先选 Suite）
│       └── 用例详情 / 编辑
│           ├── 基本信息
│           ├── 请求配置
│           └── 断言配置
├── 执行中心
│   ├── 发起执行
│   └── 最近执行
├── 测试报告
│   ├── Project 报告概览
│   ├── 执行历史
│   └── Run 报告详情
│       ├── 执行概览
│       ├── 失败原因
│       ├── 全部结果
│       └── 单条结果详情
└── 项目设置
    ├── 基本信息
    └── 删除 Project
```

## 5. 建议前端路由层级

> 以下是前端信息层级与可分享 URL 设计，不代表新增或修改后端 API。

| 页面 | 建议前端路由 |
|---|---|
| 登录 | `/login` |
| Dashboard | `/dashboard` |
| Project 列表 | `/projects` |
| Project 根路径 | `/projects/:projectId`，重定向到概览 |
| 项目概览 | `/projects/:projectId/overview` |
| 环境列表 | `/projects/:projectId/environments` |
| 环境详情 / 编辑 | `/projects/:projectId/environments/:environmentId` |
| Suite 列表 | `/projects/:projectId/suites` |
| Suite 详情 | `/projects/:projectId/suites/:suiteId` |
| OpenAPI Import | `/projects/:projectId/suites/:suiteId/import/openapi` |
| API Case 列表 | `/projects/:projectId/cases` |
| 新建 API Case | `/projects/:projectId/cases/new?suiteId=:suiteId` |
| API Case 详情 / 编辑 | `/projects/:projectId/cases/:caseId` |
| 执行中心 | `/projects/:projectId/runs` |
| 测试报告 | `/projects/:projectId/reports` |
| Run 报告详情 | `/projects/:projectId/reports/:runId` |
| 单条结果详情 | `/projects/:projectId/reports/:runId/results/:resultId` |
| 项目设置 | `/projects/:projectId/settings` |
| 用户管理 | `/admin/users` |
| 角色管理 | `/admin/roles` |

## 6. 各页面职责

### 6.1 登录

**目标：** 完成身份认证，不承载注册、产品宣传或复杂配置。

主要内容：

- 邮箱
- 密码
- 登录按钮
- 登录失败、账号禁用、请求过多等反馈

成功后：

- 有合法的站内返回地址时回到原目标页。
- 否则进入 Dashboard。

### 6.2 Dashboard

**目标：** 帮助用户快速进入自己的 Project，而不是伪造一个全平台数据大盘。

可展示：

- 当前用户欢迎信息
- 当前用户拥有的 Project 总数
- Project 快速列表
- 创建 Project 入口
- “继续配置环境 / 创建 Suite / 发起执行”等静态任务引导
- superuser 的用户管理、角色管理快捷入口

不展示：

- 全平台 Project 数量
- 全平台最近执行
- 跨 Project 通过率
- 跨用户失败趋势

原因是当前没有对应的全局聚合接口。

### 6.3 Project 列表

**目标：** 选择和管理当前用户拥有的 Project。

主要能力：

- 名称搜索
- 分页
- 新建 Project
- 进入 Project 概览
- 编辑或删除 Project 的入口

每个 Project 卡片 / 行只使用已有字段：名称、描述、owner、创建时间、更新时间。不要虚构成员数、用例数或通过率；这些数据在进入 Project 后再读取。

### 6.4 项目概览

**目标：** 提供一个 Project 内的工作起点和质量摘要。

页面区块：

1. Project 基本信息：名称、描述、owner、更新时间。
2. 资产摘要：环境数、Suite 数、API Case 数。
3. 执行摘要：总执行次数、累计结果数、通过/失败/错误数、总体通过率、最近执行时间。
4. 最近 Run：最近 N 次执行。
5. 配置完整性提示：
   - 无环境：引导“创建环境”。
   - 无默认环境：引导“设置默认环境”。
   - 无 Suite：引导“创建 Suite”。
   - 无 API Case：引导“创建或导入用例”。
6. 主操作：“发起 Project 执行”。

以上均可由现有 Project、Environment、Suite、API Case 列表和 Project Run Summary 组合得到。

### 6.5 环境管理

**目标：** 维护 Project 执行所需的环境上下文。

列表字段：

- 环境名称
- Base URL
- 是否默认
- Headers 数量
- Variables 数量
- 更新时间
- 操作

主要动作：

- 新建环境
- 编辑名称、Base URL、Headers、Variables
- 设置为默认环境
- 删除非默认环境

交互约束：

- 默认环境明确显示唯一徽标。
- 默认环境不可直接删除；先引导用户将另一个环境设为默认。
- 运行选择器默认选中默认环境，但用户仍可更换。
- Headers / Variables 在界面中按键值形式组织；疑似敏感值默认遮罩显示，但不改变后端数据结构。

### 6.6 Suite 列表与详情

**目标：** 以业务场景或回归范围组织 API Case。

Suite 列表：

- 名称搜索
- 新建 Suite
- 名称、描述、排序、更新时间
- 进入详情、编辑、删除

Suite 详情：

- Suite 基本信息
- 已关联 API Case 的有序列表
- 添加 Project 内已有 API Case
- 创建新 API Case
- 移除关联，但不删除 API Case 本体
- 调整 Suite 内用例顺序
- OpenAPI Import
- 执行当前 Suite

关键语义：

- “从 Suite 移除”与“删除 API Case”必须使用不同文案和二次确认。
- Suite 只做一层，不展示树形目录或子 Suite。
- UI 统一称为“测试套件（Suite）”；已有 API 中的 `collection` 只作为技术兼容命名，不暴露给用户。

### 6.7 API Case 列表与编辑

**目标：** 统一维护当前 Project 的 API 请求与断言定义。

列表字段：

- 启用状态
- HTTP Method
- 用例名称
- Path
- 超时时间
- 更新时间
- 操作

已有能力允许的筛选：

- 按名称搜索：服务端已有能力。
- 按 Method、启用状态：可对当前已加载列表进行前端筛选。
- 按 Suite 查看：跳转到对应 Suite 详情或调用已有 Suite 用例列表，不设计新的组合查询接口。

创建规则：

- 从 Suite 详情创建时，自动带入该 Suite。
- 从 Project 全部用例页创建时，先选择一个 Suite，再进入编辑器。
- 不提供“直接创建未归套件用例”，因为现有创建接口要求 Suite。

编辑器信息分组：

1. **基本信息**：名称、启用状态、超时时间。
2. **请求配置**：Method、Path、Headers、Query Params、Body Type、Body。
3. **断言配置**：规则化断言列表。

页面主操作：

- 保存
- 保存后返回
- 选择环境并执行当前用例
- 删除用例

不提供脚本编辑器、前置脚本、后置脚本或自定义代码执行入口。

### 6.8 OpenAPI Import

**定位：** Suite 详情和 API Case 页中的上下文动作，不是一级导航页面。

建议流程：

```text
选择目标 Suite
  → 选择来源（URL 或 JSON 内容）
  → 可选标签过滤
  → 选择冲突策略（默认 skip）
  → 预览 operation
  → 确认导入
  → 查看导入结果
  → 返回 Suite 详情或 API Case 列表
```

预览信息：

- OpenAPI 版本
- Base Path
- operation 总数
- 新增数
- 已存在数
- Method、Path、名称、冲突状态
- 解析错误

确认信息：

- 冲突策略：`skip` 或 `overwrite`
- 可选名称前缀
- 覆盖策略必须进行明显风险提示

边界：

- 仅 OpenAPI 3.0 / 3.1。
- Swagger 2.0 不进入可导入状态。
- 导入结果仍然是普通 API Case，不产生新的资产类型。

### 6.9 执行中心 Run

**目标：** 完成“选择范围 + 选择环境 + 发起执行”，而不是承担深度结果分析。

页面结构：

1. 执行名称，可选。
2. 执行范围：
   - 单 API Case
   - Suite
   - 整个 Project
3. 范围目标：根据范围选择 Case 或 Suite；Project 范围无需再次选择。
4. 执行环境：必选，默认选中 Project 默认环境。
5. 范围摘要：将执行什么、在哪个环境执行。
6. 发起执行按钮。
7. 最近执行：只展示少量记录，并提供“查看全部报告”。

同步执行交互：

- 提交后按钮进入不可重复提交状态。
- 明确提示“正在同步执行，请勿重复提交”。
- 不展示队列位置、后台任务 ID、取消按钮或虚构的实时百分比。
- 请求完成后直接跳转对应 Run 报告详情。
- 请求异常时保留用户已选择的范围和环境，便于修正后重试。

前置校验：

- 无环境：引导去环境管理。
- Suite 没有用例：引导去 Suite 详情添加用例。
- Project 没有启用用例：引导去 API Case 列表。
- 单用例已禁用：不允许发起，提供启用入口。

### 6.10 测试报告 Report

**目标：** 查询历史、判断质量、定位失败。

#### Project 报告页

- 总 Run 数
- 累计结果数
- 通过、失败、错误数
- 总体通过率
- 最近执行时间
- 最近 N 次 Run
- 执行历史列表
- 按 Run 状态过滤

#### Run 报告详情

固定分为三个视图：

1. **执行概览**
   - 名称、范围、环境、状态、触发人
   - 开始/结束时间、耗时
   - total、passed、failed、skipped、error、通过率
2. **失败原因**
   - 用例、Method、Path
   - 断言类型、操作符、expected、actual、message
   - 超时、连接或执行错误信息
3. **全部结果**
   - 每条用例的状态、耗时、Method、Path
   - 点击进入单条结果详情

#### 单条结果详情

- 用例快照信息
- 实际请求快照
- 实际响应快照
- 断言结果
- 错误代码与错误信息
- 响应 Body 是否被截断
- 返回 Run 报告
- 跳转当前 API Case 定义

历史报告展示的是执行时快照；跳到 API Case 后看到的是当前定义。页面需明确提示两者可能不同。

不提供报告导出、分享、删除或修改功能。

### 6.11 项目设置

**目标：** 集中承载低频、风险较高的 Project 管理动作。

- 修改 Project 名称与描述
- 展示 Project ID、owner、创建/更新时间
- 删除 Project

删除放在“危险操作区”，要求输入 Project 名称或再次确认。删除后返回 Project 列表，并清理前端当前 Project 上下文。

### 6.12 用户管理

仅 superuser 在导航中可见。

- 用户分页列表
- 邮箱 / 用户名 / 昵称搜索
- 新建用户
- 查看详情
- 修改昵称、手机号、角色、状态、superuser 标记
- 启用 / 禁用用户

禁用用户使用明确的状态文案，不将后端软禁用表现成“永久物理删除”。

### 6.13 角色管理

仅 superuser 在导航中可见。

- 角色列表
- 新建角色
- 查看角色详情
- 编辑名称、描述、权限字符串
- 删除非系统角色
- 系统角色展示“系统角色”标识并禁用不可执行动作

当前没有权限字典接口，前端只能围绕现有权限字符串进行展示与编辑，不设计权限资源树或动态权限点管理中心。

---

# ③ Project 内部导航

## 7. Project 工作区结构

### 7.1 导航顺序

| 顺序 | 导航项 | 用户问题 | 主任务 |
|---:|---|---|---|
| 1 | 项目概览 | 当前项目是否可测试、质量如何？ | 查看摘要、继续下一步 |
| 2 | 环境管理 | 请求发到哪里、使用哪些变量？ | 配置 Base URL、Headers、Variables |
| 3 | 测试套件 | 用哪些业务范围组织回归？ | 组织和排序用例 |
| 4 | API 用例 | 具体请求和断言是什么？ | 创建、维护、启停用例 |
| 5 | 执行中心 | 现在要执行什么？ | 选择范围、环境并运行 |
| 6 | 测试报告 | 执行结果如何、为什么失败？ | 查看历史、分析结果 |
| 7 | 项目设置 | 如何修改或删除项目？ | 维护 Project 元数据 |

### 7.2 Project Header

Project 页面顶部固定展示：

```text
[Project 名称]  [owner 信息]
[可选描述]
[主操作：根据当前页面变化]
```

主操作规则：

| 当前页面 | 主操作 |
|---|---|
| 项目概览 | 发起 Project 执行 |
| 环境管理 | 新建环境 |
| Suite 列表 | 新建 Suite |
| Suite 详情 | 新建用例；次操作为导入 OpenAPI、执行 Suite |
| API Case 列表 | 新建用例；次操作为导入 OpenAPI |
| API Case 详情 | 选择环境并执行 |
| 执行中心 | 发起执行 |
| 测试报告 | 无写操作；可跳转执行中心 |
| 项目设置 | 保存更改 |

### 7.3 Project 切换规则

- 切换器的数据来自现有 Project 列表，只显示当前用户列表接口可发现的 Project。
- 在模块列表页切换 Project 时，保留模块语义：例如环境列表切换后进入新 Project 的环境列表。
- 在实体详情页切换 Project 时，不尝试保留实体 ID，回到新 Project 对应模块的列表页。
- 有未保存编辑内容时，切换 Project 前进行离开确认。
- 不提供“最近 Project”“收藏 Project”或“共享 Project”，避免引入无后端数据来源的状态。

### 7.4 面包屑规则

示例：

```text
Project / 用户服务 API / 测试套件 / 冒烟回归
Project / 用户服务 API / API 用例 / 获取用户详情
Project / 用户服务 API / 测试报告 / Run #20260715 / 获取用户详情
系统管理 / 用户管理 / user@example.com
```

面包屑中的 Project 名称、Suite、Case、Run、Result 均可点击返回其规范页面。

---

# ④ 页面之间跳转关系

## 8. 全局跳转图

```text
登录
  └── Dashboard
       ├── Project 列表
       │    ├── 新建 Project ──→ Project 概览
       │    └── 选择 Project ──→ Project 概览
       ├── 用户管理（superuser）
       └── 角色管理（superuser）

Project 概览
  ├── 环境摘要 ──→ 环境管理
  ├── Suite 摘要 ──→ Suite 列表
  ├── Case 摘要 ──→ API Case 列表
  ├── 最近 Run ──→ Run 报告详情
  ├── 发起执行 ──→ 执行中心
  └── 质量摘要 ──→ 测试报告

环境管理
  └── 执行入口 ──→ 执行中心（预选环境）

Suite 列表
  └── Suite 详情
       ├── API Case 详情
       ├── 新建 API Case
       ├── 添加已有 API Case
       ├── OpenAPI Import ──→ 导入结果 ──→ Suite 详情
       └── 执行 Suite ──→ 执行完成 ──→ Run 报告详情

API Case 列表
  ├── API Case 详情 / 编辑
  ├── 新建 API Case（先选 Suite）
  ├── OpenAPI Import（先选 Suite）
  └── 执行单用例 ──→ 执行完成 ──→ Run 报告详情

执行中心
  └── 执行完成 ──→ Run 报告详情

测试报告
  └── Run 报告详情
       ├── 失败项 ──→ 单条结果详情
       ├── 结果项 ──→ 单条结果详情
       ├── 当前用例 ──→ API Case 详情
       └── 再次执行 ──→ 执行中心（仅预填现有可确定字段）
```

## 9. 关键跳转关系表

| 来源 | 用户动作 | 目标 | 需要保留的上下文 |
|---|---|---|---|
| 登录 | 登录成功 | 原合法目标或 Dashboard | 原目标 URL |
| Dashboard | 点击 Project | Project 概览 | projectId |
| Project 列表 | 创建成功 | 新 Project 概览 | projectId |
| Project 概览 | 点击“创建环境” | 环境新建 | projectId |
| Project 概览 | 点击“创建 Suite” | Suite 新建 | projectId |
| Project 概览 | 点击“创建用例” | 先选 Suite，再进入用例新建 | projectId、suiteId |
| Suite 列表 | 点击 Suite | Suite 详情 | projectId、suiteId、列表查询条件 |
| Suite 详情 | 点击用例 | API Case 详情 | projectId、caseId、returnTo=suite |
| Suite 详情 | 新建用例 | API Case 新建 | projectId、suiteId |
| Suite 详情 | OpenAPI Import | 导入页 | projectId、suiteId |
| Suite 详情 | 执行 | 执行中心或环境选择层 | projectId、scope=collection、suiteId |
| API Case 列表 | 新建 | Suite 选择后进入新建 | projectId、suiteId |
| API Case 列表 | 执行 | 环境选择层 | projectId、scope=case、caseId |
| API Case 详情 | 执行 | 环境选择层 | projectId、caseId |
| 环境列表 | 在某环境下执行 | 执行中心 | projectId、environmentId |
| 执行中心 | 执行成功 | Run 报告详情 | projectId、runId |
| Project 概览 | 点击最近 Run | Run 报告详情 | projectId、runId |
| 测试报告 | 点击历史 Run | Run 报告详情 | projectId、runId、历史筛选条件 |
| Run 报告 | 点击失败项 | Result 详情 | projectId、runId、resultId |
| Result 详情 | 查看当前定义 | API Case 详情 | projectId、caseId、returnTo=report |
| 项目设置 | 删除成功 | Project 列表 | 清空已删除 projectId |
| 用户详情 | 点击角色 | 角色详情 | roleId |
| 任意受保护页 | Token 失效且刷新失败 | 登录 | 安全保存原目标 URL |

## 10. 返回行为

1. 从 Suite 进入 API Case，返回时回到原 Suite，而不是固定回到全部用例列表。
2. 从 Report Result 进入 API Case，返回时回到原 Result / Run Report。
3. 搜索词、分页、状态过滤放入 URL Query，浏览器返回后可恢复。
4. 创建、编辑成功后优先回到发起动作的上下文页面。
5. 403 进入“无权限”状态页；404 进入“资源不存在”状态页；两者不自动跳到 Dashboard 以掩盖问题。
6. 实体 URL 中包含 Project 上下文；即使后端详情接口使用扁平资源 ID，前端仍校验响应中的 Project 归属。

---

# ⑤ 用户完整操作路径

## 11. 主路径：从零建立 API 回归测试

适用角色：Project owner / 测试工程师。

```text
1. 登录
2. 进入 Dashboard
3. 新建 Project
4. 自动进入 Project 概览
5. 根据空状态提示进入环境管理
6. 创建环境，填写 Base URL / Headers / Variables，并设为默认环境
7. 创建 Suite
8. 选择以下任一方式建立 API Case：
   8.1 手工创建：配置 Method、Path、Headers、Query、Body、断言、超时
   8.2 OpenAPI Import：选择来源、预览、确认导入到当前 Suite
9. 检查并启用要执行的 API Case
10. 进入执行中心
11. 选择执行范围：Case / Suite / Project
12. 确认默认环境或切换环境
13. 发起同步执行
14. 执行完成后自动进入 Run 报告
15. 查看通过率、失败项和错误项
16. 进入单条 Result 查看请求、响应、断言和错误
17. 跳转当前 API Case 修正配置
18. 返回执行中心，重新选择范围并执行
19. 在测试报告中查看新的 Run 结果
```

闭环：

```text
环境配置 → 资产维护 → 执行 → 报告定位 → 修复用例 → 再执行
```

## 12. OpenAPI 导入路径

```text
登录
  → Project 列表
  → Project 概览
  → Suite 列表
  → 选择或创建目标 Suite
  → OpenAPI Import
  → 选择 URL 或 JSON 内容
  → 可选标签过滤
  → 选择 skip / overwrite
  → 查看预览和冲突
  → 确认导入
  → 查看 created / skipped / overwritten / errors
  → 返回 Suite 详情
  → 检查导入的 API Case 与默认断言
  → 进入执行中心
  → 选择环境执行 Suite
  → 查看 Report
```

## 13. 单用例调试路径

```text
Project
  → API Case 列表
  → 搜索用例
  → API Case 详情
  → 检查请求和断言
  → 选择环境并执行
  → Run 报告
  → Result 详情
  → 回到 API Case 修正
  → 再次执行
```

注意：平台没有“只发送请求但不保存 Run”的独立调试接口，因此单用例调试仍会生成正式 Run / Result 记录。

## 14. Suite 回归路径

```text
Project
  → Suite 列表
  → Suite 详情
  → 检查用例顺序、启用状态
  → 执行当前 Suite
  → 选择环境
  → 同步执行
  → Run 报告
  → 失败原因
  → Result 详情
  → API Case 修正
  → 返回执行中心重新选择该 Suite 执行
```

## 15. Project 全量回归路径

```text
Project 概览
  → 发起 Project 执行
  → 默认 scope=project
  → 选择环境
  → 确认当前 Project 的全部启用用例范围
  → 执行
  → Run 报告
  → 按失败 / 错误定位
  → 修复用例
  → 重新发起 Project 执行
```

## 16. 失败定位路径

```text
测试报告
  → 筛选或选择目标 Run
  → 失败原因
  → 选择失败断言 / 执行错误
  → Result 详情
  → 检查实际请求
  → 检查实际响应
  → 对比 expected / actual
  → 查看 error_code / error_message
  → 跳转当前 API Case
  → 修正请求、变量引用、超时或断言
  → 进入执行中心重新执行
```

判断顺序建议：

1. 先看 `error`：超时、连接或执行错误。
2. 再看 `failed`：请求完成但断言未通过。
3. 检查环境与变量是否符合目标环境。
4. 检查请求快照是否与预期一致。
5. 检查响应与断言的 expected / actual。

## 17. 环境切换与维护路径

```text
Project
  → 环境管理
  → 新建或编辑环境
  → 设置默认环境
  → 执行中心
  → 默认自动选中新默认环境
  → 执行 Case / Suite / Project
  → 报告中确认 environmentId
```

删除默认环境：

```text
环境管理
  → 选择另一个环境
  → 设置为默认
  → 返回原环境
  → 删除
```

## 18. 管理员路径

### 18.1 用户管理

```text
登录
  → 系统管理 / 用户管理
  → 搜索或新建用户
  → 选择角色
  → 设置启用状态 / superuser 标记
  → 保存
  → 后续可进入用户详情调整角色或禁用账号
```

### 18.2 角色管理

```text
登录
  → 系统管理 / 角色管理
  → 新建角色
  → 填写名称、描述、已有权限字符串
  → 保存
  → 用户管理
  → 将角色分配给用户
```

系统角色不可删除时，前端直接禁用删除操作并解释原因。

## 19. 只读用户路径

产品层面的 Viewer 建议路径：

```text
登录
  → Dashboard
  → 可访问的 Project
  → 查看环境 / Suite / API Case
  → 查看测试报告
  → 查看 Result 请求、响应与断言快照
```

创建、编辑、删除、导入和执行入口在只读模式下隐藏或禁用。

但必须注意：当前后端的主要 Project 授权模型是 owner / superuser，且没有 Project 成员共享关系；前端“只读模式”不能替代后端安全控制。详见第 22 节。

---

## 20. 页面状态设计

### 20.1 空状态

| 页面 | 空状态主文案 | 主操作 |
|---|---|---|
| Dashboard / Project | 尚未创建 Project | 新建 Project |
| 环境管理 | 尚未配置执行环境 | 新建环境 |
| Suite | 尚未创建测试套件 | 新建 Suite |
| API Case | 尚未创建 API 用例 | 选择 Suite 后新建 / 导入 OpenAPI |
| Suite 详情 | 当前 Suite 尚无用例 | 新建用例 / 添加已有用例 / OpenAPI Import |
| 执行中心 | 当前范围不可执行 | 按原因去环境、Suite 或 Case 页面修复 |
| 测试报告 | 尚无执行记录 | 前往执行中心 |
| Run 失败原因 | 本次执行无失败项 | 查看全部结果 |
| 用户管理 | 尚无匹配用户 | 清除搜索 / 新建用户 |
| 角色管理 | 尚无匹配角色 | 新建角色 |

### 20.2 加载与错误状态

- 列表加载、页面加载和提交加载分开表达。
- 同步 Run 使用页面级执行状态，防止重复提交。
- Token 过期先使用已有 Refresh 能力；刷新失败再回登录。
- 403、404、409、422 展示业务可行动建议。
- 删除和覆盖属于高风险动作，必须二次确认。
- 网络失败不应清空未提交表单。

### 20.3 命名规范

| 技术名 | 用户界面名称 | 说明 |
|---|---|---|
| Project | 项目 | 所有测试资产的归属边界 |
| Environment | 环境 | Base URL、Headers、Variables |
| Suite / collection | 测试套件 | UI 统一使用 Suite，不展示历史 `collection` 命名 |
| Test Case | API 用例 | 请求定义与断言规则 |
| Run | 执行 | 一次 Case / Suite / Project 执行批次 |
| Result | 用例结果 | Run 中某条用例的执行结果 |
| Report | 测试报告 | 对 Run / Result 的只读分析视图 |
| OpenAPI Import | OpenAPI 导入 | 向指定 Suite 生成 API Case 的动作 |

---

## 21. 现有 API 与页面映射

该映射用于证明本 IA 不依赖新增后端能力。

| 前端页面 / 动作 | 复用的现有 API 能力 |
|---|---|
| 登录 | `POST /auth/login` |
| Token 续期 | `POST /auth/refresh` |
| 当前用户 | `GET /auth/me` |
| 退出 | `POST /auth/logout` |
| 修改密码 | `PUT /users/me/password` |
| Dashboard 的 Project 总数与列表 | `GET /projects` |
| Project 创建 / 详情 / 编辑 / 删除 | `POST /projects`、`GET/PUT/DELETE /projects/{project_id}` |
| Project 概览资产数 | Project 下 Environment、Suite、Test Case 列表响应中的 `total` |
| Project 概览执行摘要 | `GET /projects/{project_id}/runs/summary` |
| 环境管理 | Project 环境列表及 Environment 详情、创建、更新、删除、设默认接口 |
| Suite 管理 | Project Suite CRUD、详情、用例关联、批量添加、排序、移除接口 |
| API Case 管理 | Suite 用例创建/列表、Project 用例列表、Test Case 详情/更新/删除接口 |
| OpenAPI Import | `POST /projects/{project_id}/suites/{suite_id}/import/openapi` |
| 发起 Case 执行 | `POST /test-cases/{case_id}/run` |
| 发起 Suite / Project 执行 | `POST /projects/{project_id}/runs` |
| 最近执行 / 历史列表 | `GET /projects/{project_id}/runs` |
| Project 报告概览 | `GET /projects/{project_id}/runs/summary` |
| Run 概览 | `GET /runs/{run_id}` 或 `/runs/{run_id}/summary` |
| Run 全部结果 | `GET /runs/{run_id}/results` |
| Run 失败原因 | `GET /runs/{run_id}/failures` |
| Result 详情 | `GET /results/{result_id}` |
| 用户管理 | `/users`、`/users/{user_id}`，创建复用受管理员保护的 `/auth/register` |
| 角色管理 | `/roles`、`/roles/{role_id}` |

---

## 22. 权限与现有契约风险说明

本节不是新增后端需求，而是为了避免前端 IA 对现有能力作出错误承诺。

### 22.1 当前可依赖的后端边界

| 范围 | 当前实际边界 |
|---|---|
| 用户管理 | superuser |
| Project 列表 | 当前用户拥有的 Project |
| Project 详情及资产 | Project owner 或 superuser |
| 执行与报告 | Project owner 或 superuser |
| OpenAPI Import | Project owner 或 superuser |
| Project 成员 / 共享 | 不存在 |

因此：

- 不设计“我参与的项目”“共享给我的项目”“项目成员管理”。
- superuser 的 Project 列表也不能被描述为“全部项目”，因为现有列表仍按当前 owner 过滤。
- 若 superuser 通过合法深链访问其他 Project，可使用详情能力，但 IA 不提供无法由列表发现的“全局项目管理”入口。

### 22.2 Role 与 Viewer 的限制

虽然角色数据包含 `permissions`，产品文档也定义了 admin / tester / viewer，但当前 Project 资产的主要后端授权仍是 owner / superuser，并非完整权限点校验。

因此前端可以：

- 根据 superuser 隐藏系统管理菜单。
- 根据已取得的角色信息做操作显隐与只读体验。

但前端不应：

- 宣称 Viewer 只读已经形成可靠安全边界。
- 允许用户因前端权限字符串而访问后端未授权的其他 Project。
- 将菜单隐藏当作鉴权替代品。

### 22.3 OpenAPI Import 契约一致性

现有文档描述的确认导入流程依赖 `preview_id`，但当前已审阅的 `ImportPreviewResponse` 字段中未声明该值；同时确认导入必须通过该值消费预览。

在“不修改已有 API”的约束下：

1. 前端实施前必须以实际运行响应确认 `preview_id` 是否可取得。
2. 若现有响应无法取得该值，前端只能可靠提供“OpenAPI 预览”，不得伪造“导入成功”。
3. IA 仍将该入口放在 Suite 上下文中；这是导航归属，不代表绕过现有契约限制。

### 22.4 同步 Run 限制

- 不设计后台运行、轮询、取消和实时进度。
- 执行返回后进入报告。
- “再次执行”跳回执行中心；由于 Run 响应没有完整保存并返回所有原始范围选择信息，不能承诺所有 Case / Suite Run 都可一键原样重放。

---

## 23. IA 验收标准

### 23.1 导航验收

- [ ] 登录后默认进入 Dashboard。
- [ ] 全局一级菜单只包含 Dashboard、Project、系统管理。
- [ ] 系统管理仅对 superuser 展示。
- [ ] 进入 Project 后可看到完整 Project 内导航。
- [ ] Environment、Suite、API Case、Run、Report 不脱离 Project 上下文。
- [ ] OpenAPI Import 不作为全局一级菜单。

### 23.2 层级验收

- [ ] 任一 Project 资源页均展示当前 Project。
- [ ] 任一实体详情均有清晰面包屑和返回路径。
- [ ] Suite 与 API Case 关系表达准确。
- [ ] Run 与 Report 没有重复详情页。
- [ ] Report Result 可跳转到当前 API Case 定义，并提示快照差异。

### 23.3 闭环验收

- [ ] 用户可完成“Project → Environment → Suite → API Case → Run → Report”完整路径。
- [ ] 用户可从失败 Result 返回 API Case 修复，并重新执行。
- [ ] 用户可从 Suite 发起 OpenAPI 导入预览，并在现有契约允许时完成导入。
- [ ] 无环境、无 Suite、无用例、无报告时均有正确下一步。

### 23.4 约束验收

- [ ] 所有页面数据都能映射到已有 API。
- [ ] 没有新增数据库实体或前端虚构业务对象。
- [ ] 没有承诺项目成员、任务调度、消息通知、执行取消、报告导出等未有能力。
- [ ] 不以菜单显隐替代后端鉴权。
- [ ] 不修改已有 API 命名或契约；UI 层只做统一术语与上下文组织。

---

## 24. 最终 IA 一览

```text
登录
└── Dashboard
    ├── 我的 Project
    │   └── Project 工作区
    │       ├── 项目概览
    │       ├── 环境管理
    │       ├── 测试资产
    │       │   ├── Suite
    │       │   │   ├── Suite 用例管理
    │       │   │   └── OpenAPI Import
    │       │   └── API Case
    │       │       └── 请求与断言编辑
    │       ├── 执行中心
    │       │   └── Case / Suite / Project Run
    │       ├── 测试报告
    │       │   ├── Project 质量概览
    │       │   ├── Run 报告
    │       │   └── Result 详情
    │       └── 项目设置
    └── 系统管理（superuser）
        ├── 用户管理
        └── 角色管理
```

该结构在不改变后端和数据库的前提下，将现有模块组织为清晰的企业级任务闭环：

```text
进入平台 → 选择 Project → 配置环境 → 维护测试资产 → 发起执行 → 分析报告 → 修复并回归
```
