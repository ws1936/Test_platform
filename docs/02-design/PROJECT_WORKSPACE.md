# API 自动化测试平台 Project Workspace 重设计

> 文档类型：信息架构与页面设计  
> 范围：进入 Project 后形成的工作空间  
> 实施约束：不新增接口、不修改已有 API、不新增数据库、本阶段不写代码

---

## 1. 设计结论

Project Workspace 是从“资源管理”升级为“任务闭环”的统一工作空间。

当用户点击 Project 或来自 Dashboard 的“项目”入口时，应进入 `/projects/{projectId}/workspace`，而不是 `/projects/{projectId}/overview` 这一概览占位页。Workspace 在不替代任何现有 API 的前提下，把 Project 维度的 Environment、Suite、Case、Run、Report、Import 集中到同一上下文：

- 保留完整的 Project 内导航（Environment / Suite / Case / Run / Report / Import）。
- 顶部保留全局信息条（项目信息、Owner、当前用户、最近操作入口）。
- 主区采用“三段式”结构：**侧边模块导航** + **Workspace 内容区** + **上下文侧栏**。
- 所有模块共享 Project 上下文，避免在每个页面重复选择 Project。
- URL 一致：所有 Workspace 内页面都以 `/projects/{projectId}/workspace/{module}` 形式存在；旧路由保持兼容并重定向到 Workspace。

最终结构：

```text
项目工作区 Project Workspace
├── 概览 Overview
├── 环境 Environment
├── 套件 Suite
├── 用例 Case
├── 执行 Run
├── 报告 Report
└── 导入 Import
```

旧概念中的“项目 CRUD”页面降级为 Workspace 内的“项目信息卡片 + 危险操作区”，不再作为独立一级页面。

---

## 2. 设计原则

### 2.1 工作空间而不是后台

- 顶部信息条：项目名、Owner、最近一次操作时间、当前登录用户、刷新入口。
- 左侧模块导航：六个固定模块（Overview、Environment、Suite、Case、Run、Report）+ Import。
- 主区：当前模块的工作台。
- 右侧上下文栏：当前 Project 的关键状态摘要，最近一次执行、最重要失败、默认环境等。

### 2.2 上下文共享而不是上下文重建

- 当前 Project 在整个 Workspace 内部共享，不在每个模块再次选择。
- Run 与 Case 联动：执行后自动跳 Report；Case 列表可“一键执行”，默认使用默认环境。
- Suite 与 Case 联动：在 Suite 中可创建/追加 Case。
- Import 与 Suite / Case 联动：导入是 Suite 内的一次性动作。

### 2.3 单个主任务流程闭环

- 配置 Environment → 配置 Suite → 创建或导入 Case → 发起 Run → 报告定位 → 修复并回归。
- 步骤顺序与信息架构保持一致。

### 2.4 状态共享而不是数据集中

- 服务端状态依然由 React Query 维护。
- 跨模块共享 Project 元信息缓存。
- 当前 Project ID 来自 URL Parameter。

### 2.5 旧的独立页面降级

- `/projects/{projectId}/overview` 继续存在，重定向到 `/projects/{projectId}/workspace/overview`。
- `/projects/{projectId}/settings` 保留在 Workspace 内作为 Information Tab。
- 不再将“项目 CRUD”作为独立一级页面，CRUD 操作在 Workspace Information Tab 完成。

---

## 3. 整体页面布局

### 3.1 三段式 24 栅格布局

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 顶部信息条：Project 名称 · Owner · 最近一次执行 · 状态徽标 · 刷新   │
├──────────────┬───────────────────────────────────┬───────────────────┤
│ 左侧模块导航  │  Workspace 内容区                  │ 右侧上下文栏     │
│  Overview    │                                    │  当前默认环境     │
│  Environment │  当前选中模块的工作台             │  最近一次执行     │
│  Suite       │                                    │  最近失败用例     │
│  Case        │                                    │  快速创建         │
│  Run         │                                    │                   │
│  Report      │                                    │                   │
│  Import      │                                    │                   │
│  ── 信息 ── │                                    │                   │
│  Information │                                    │                   │
└──────────────┴───────────────────────────────────┴───────────────────┘
```

### 3.2 栅格比例

| 区域 | 桌面端 | 平板端 | 移动端 |
|---|---:|---:|---:|
| 左侧模块导航 | 3 / 24 | 折叠为抽屉 | 抽屉 |
| Workspace 内容区 | 16 / 24 | 24 / 24 | 24 / 24 |
| 右侧上下文栏 | 5 / 24 | 隐藏 | 隐藏 |

### 3.3 桌面端布局细节

```text
┌──┬──────────────────────────────────────┬──────┐
│左│  顶部信息条（横跨三段）             │     │
│侧│  + 面包屑（Project 名称 / 模块名） │     │
│模├──────────────────────────────────────┤  右  │
│块│  当前模块的卡片化工作台              │  侧  │
│导│  · 模块主内容                        │  上  │
│航│  · 模块内状态提示 / 空状态 / 重试    │  下  │
│  │                                      │  文  │
│  │                                      │  栏  │
│  │  Information Tab（项目设置）         │     │
└──┴──────────────────────────────────────┴──────┘
```

### 3.4 移动端与平板

- 左侧模块导航折叠为顶栏 Drawer，触发按钮位于面包屑前。
- 右侧上下文栏隐藏，关键状态以紧凑徽标形式嵌入顶部信息条。
- 卡片宽度自动 100%。

---

# ① 页面布局

## 4. 顶部信息条

### 4.1 必填内容

| 元素 | 数据来源 | 行为 |
|---|---|---|
| Project 名称 | `GET /projects/{projectId}` | 展示并可点击跳到 Workspace Overview |
| 描述 | 同上 | 鼠标悬停展示完整描述 |
| Owner | 同上 | 复制 Owner ID 方便协作 |
| 最近一次执行 | `GET /projects/{projectId}/runs?limit=1` | 点击进入 Report 详情 |
| 默认环境 | `GET /projects/{projectId}/environments` | 点击进入 Environment 列表 |
| 快速执行 | Run | 跳到执行中心并预填 scope=project |
| 刷新 | 全部 | 触发当前 Project 相关 Query 失效 |

### 4.2 状态徽标

- 资产配置完整度徽标：环境 / Suite / Case 是否齐全。
- 执行健康度徽标：最近一次 Run 是否成功。
- 健康度规则：使用 `runs/summary` 的 `overall_pass_rate`，徽标颜色与 `0.8` / `0.5` 阈值对齐。

### 4.3 重要约束

- 不展示全平台、跨用户、跨 Project 的统计。
- 不展示任何后续能力，徽标只是当前 Project 的轻摘要。

---

## 5. 左侧模块导航

### 5.1 导航项

| 序号 | 模块 | URL 子路径 | 主要职责 |
|---:|---|---|---|
| 1 | Overview | `overview` | Project 摘要 + 最近活动 + 质量摘要 |
| 2 | Environment | `environment` | 维护默认环境、其他环境 |
| 3 | Suite | `suite` | 维护测试套件 |
| 4 | Case | `case` | 维护 API 用例 |
| 5 | Run | `run` | 发起执行与查看最近执行 |
| 6 | Report | `report` | 报告历史与详情 |
| 7 | Import | `import` | OpenAPI 导入到指定 Suite |
| 8 | Information | `information` | 项目信息、危险操作区 |

### 5.2 交互规则

- 选中项高亮 + 面包屑同步。
- 鼠标悬停展示简短说明。
- 未启用模块（如尚无 Suite 时的 Import 之外）保留入口，但通过右侧上下文栏显示“前置条件缺失”。
- 折叠态：仅显示图标，鼠标悬停显示文字。

### 5.3 模块默认排序

按完整闭环排列：Overview → Environment → Suite → Case → Run → Report → Import → Information。Information 排在最后，因为它对应低频危险操作。

---

## 6. Workspace 内容区

### 6.1 Overview 模块

主要目标：让用户一眼看到当前 Project 的资产与执行质量。

| 区块 | 数据来源 | 行为 |
|---|---|---|
| 项目摘要 | `GET /projects/{projectId}` | 名称、描述、Owner、创建/更新时间 |
| 资产计数 | `environments` / `suites` / `cases` 的 `total` | 任意区域缺失时显示引导 |
| 质量摘要 | `GET /projects/{projectId}/runs/summary` | 通过率、错误率、最近一次时间 |
| 最近执行 | `GET /projects/{projectId}/runs?limit=5` | 跳转 Report |
| 最近失败 | `runs/summary` 间接 | 跳转 Report 的失败原因 Tab |
| 资产配置引导 | 上述四个统计的完整性 | 缺失时显示对应引导卡片 |

### 6.2 Environment 模块

等同于现有 `/projects/{projectId}/environments`，主要差别：

- 顶部信息条和左侧导航保留。
- 卡片使用 Workspace 风格的元数据头（项目名 + 当前模块名）。
- 列表行为保持：搜索、设为默认、新建、编辑、删除（默认环境不可删）。
- 名称 + 默认徽标 + Headers / Variables 数量 + Base URL + 更新时间。

### 6.3 Suite 模块

- 列表页：搜索、新建 Suite、进入 Suite 详情、删除 Suite。
- 详情页：进入 `Suite` 详情后显示已关联用例，可创建、调整顺序、移除关联、OpenAPI 导入、执行 Suite。
- 包含两个子模块：
  - `SuiteCase` 列表：作为 Suite 详情的内容区，调用 `GET /collections/{suiteId}/cases`。
  - `Import` 模块的 Suite 选择器：默认使用 URL 中 `?suiteId` 指定 Suite。
- 详情 URL：`/projects/{projectId}/workspace/suite/{suiteId}`。
- 导入 URL：`/projects/{projectId}/workspace/import/{suiteId}`。

### 6.4 Case 模块

- 列表页：搜索、Method 筛选、启用筛选；进入 Case 编辑；执行单用例；删除。
- 编辑器：单页（基本 / 请求 / 断言）继续使用 React Hook Form + Ant Design。
- 状态联动：从 Suite 详情进入编辑器时保留 `?suiteId`；执行时跳 Run 模块并预填 `scope=case&scopeId=...`。

### 6.5 Run 模块

- 发起执行：选择 Case、Suite、Project 三种 scope；默认环境自动选中。
- 最近执行：当前 Project 最近 5 条 Run，状态、范围、耗时、通过率、错误。
- 跳到 Report：点击 Run 行直接进入 Report 详情。
- 与 Report 模块的差异：Run 强调“发起 + 最近”，Report 强调“历史 + 详情”。

### 6.6 Report 模块

- 入口：`/projects/{projectId}/workspace/report`。
- 子页面：
  - 列表：当前 Project 的全部 Run 历史。
  - 详情：`/projects/{projectId}/workspace/report/{runId}`。
  - 结果详情：`/projects/{projectId}/workspace/report/{runId}/result/{resultId}`。
- 提供筛选：按 Run 状态过滤；按失败原因展开。
- 跳到 Case：失败时跳到对应 Case 编辑器并保留 `?from=report&runId=...&resultId=...`。

### 6.7 Import 模块

- 入口：`/projects/{projectId}/workspace/import/{suiteId}`。
- 选择来源（URL 或 JSON）。
- 选择标签、冲突策略、名称前缀。
- 预览后必须显示 `preview_id` 才允许确认；否则明确说明无确认能力。
- 导入后回到 Suite 详情。

### 6.8 Information 模块

- 项目名称与描述编辑。
- 项目 ID、Owner、创建/更新时间。
- 危险操作区：
  - 删除项目（输入名称确认）。
  - 离开项目（可后续能力）。

---

## 7. 右侧上下文栏

### 7.1 信息块

| 区块 | 数据来源 | 行为 |
|---|---|---|
| 当前默认环境 | `GET /projects/{projectId}/environments` | 显示 Base URL；点击跳到环境详情 |
| 最近一次执行 | `runs/summary.last_run_at` | 点击进入 Report |
| 失败概览 | `runs/summary.total_failed + total_error` | 数字 > 0 时显示失败数 |
| 快速创建 | — | 链接到 Environment / Suite / Case |
| 资产完整度 | 四个统计 | 缺失时显示引导 |

### 7.2 隐藏规则

- 平板端隐藏。
- 移动端折叠。
- 内容稳定：右栏数据是“Project 摘要”，与顶部信息条不重复。

### 7.3 数据来源

- 仅依赖 Project 维度已有 API。
- 不聚合跨 Project 数据。

---

# ② 页面切换

## 8. 模块间跳转关系

```text
进入 Project（任意入口）
  │
  ▼
Workspace Overview
  │
  ├── 跳到 Environment（顶部信息条默认环境、右侧上下文栏）
  │     │
  │     ├── 创建环境 → 留在 Environment 模块
  │     ├── 设为默认 → 仍留在 Environment 模块
  │     └── 编辑环境 → 留在 Environment 模块
  │
  ├── 跳到 Suite（左侧模块、Overview 资产计数、快速创建）
  │     │
  │     ├── 新建 Suite → 留在 Suite 列表
  │     ├── 进入 Suite 详情 → Suite 详情
  │     │     ├── 添加已关联 Case → 留在 Suite 详情
  │     │     ├── 调整顺序 → 留在 Suite 详情
  │     │     ├── 创建 Case → 跳到 Case 编辑器（保留 suiteId）
  │     │     ├── 导入 OpenAPI → 跳到 Import（保留 suiteId）
  │     │     └── 执行 Suite → 跳到 Run 模块（scope=collection&scopeId=...）
  │     └── 删除 Suite → 留在 Suite 列表
  │
  ├── 跳到 Case
  │     │
  │     ├── 编辑 Case → Case 编辑器（保留 suiteId）
  │     ├── 执行单用例 → 跳到 Run（scope=case&scopeId=...）
  │     └── 删除 Case → 留在 Case 列表
  │
  ├── 跳到 Run
  │     │
  │     ├── 发起执行 → 同步执行 → 跳到 Report 详情
  │     └── 查看最近执行 → 跳到 Report 列表
  │
  ├── 跳到 Report
  │     │
  │     ├── 点击 Run 行 → Report 详情
  │     │     ├── 失败项 → 跳到 Result 详情
  │     │     │     └── 查看当前 Case 定义 → 跳到 Case 编辑器（保留 from=report&runId&resultId）
  │     │     └── 再次执行 → 跳到 Run（scope 复用）
  │     └── 筛选 Run 状态 → 留在 Report 列表
  │
  └── 跳到 Import
        ├── 预览 → 留在 Import
        ├── 确认 → 跳到 Suite 详情
        └── 重新配置 → 留在 Import
```

## 9. 页面切换原则

- 模块内部切换：在该模块内完成，不破坏 Project 上下文。
- 跨模块切换：保留 `?from=...&...` 参数以支持返回。
- 高风险动作（删除、覆盖导入）必须有二次确认。
- 后台失效：创建/更新/删除后，Project 范围相关 Query 全部失效。

## 10. 返回行为

- Case 编辑器返回：保留 Suite 上下文。
- Suite 详情返回：回到 Suite 列表。
- Report 详情返回：回到 Report 列表。
- Result 详情返回：回到 Run 详情。
- OpenAPI Import 返回：回到 Suite 详情。
- 全部在 Workspace 内，不退回全局 Project 列表。

---

# ③ 状态共享

## 11. 状态分类

| 类别 | 工具 | 范围 | 持久化 |
|---|---|---|---|
| 服务端状态 | React Query | 全局 | 服务端 |
| 认证状态 | Zustand | 全局 | localStorage |
| 当前 Project | URL Parameter | 路由 | URL |
| 当前模块 | URL 子路径 | 路由 | URL |
| 跨模块共享 UI | React Context | 整个 Workspace | 组件树 |
| 模块内部 UI | useState | 组件 | 组件树 |
| 危险确认 | Ant Design Modal | 组件 | 组件树 |

## 12. 跨模块共享 Project 上下文

### 12.1 单一真实源

URL 中 `/projects/{projectId}/workspace/{module}` 决定 Project ID，所有模块统一通过 `useParams().projectId` 获取。

### 12.2 Project 元信息缓存

使用 React Query 维护 Project 详情，各模块共享：

```text
["projects", projectId, "project"]
```

页面初始渲染从 Workspace Provider 注入 Project 名称、Owner、创建时间等，避免每个模块重新请求。

### 12.3 跨模块事件

- 在 Suite 中创建 Case → 失效 `["projects", projectId, "suites"]` 和 `["projects", projectId, "cases"]`。
- 在 Import 中确认导入 → 失效对应 Suite 的用例和项目用例。
- 在 Run 中发起执行 → 失效 `["projects", projectId, "runs"]`。
- 在 Report 中进入 Case 编辑器 → 保留 `from=report&runId&resultId`。

## 13. Workspace Provider 设计

Workspace Provider 在 `AppShell` 的 `Outlet` 内部、Workspace 路由组外层，提供：

- Project 元信息（名称、Owner、创建/更新时间）。
- Project 资产计数（环境、Suite、Case）以便顶部信息条不重复请求。
- 资产完整度标记：是否缺失环境、是否缺失 Suite、是否缺失 Case。
- 模块级回调：刷新、跳转、错误恢复。

不重复各模块自己的 Query，而是在 Provider 内提供共享 Selector。

## 14. URL 状态

所有 URL 均包含 `projectId` 和 `module`：

```text
/projects/{projectId}/workspace
/projects/{projectId}/workspace/overview
/projects/{projectId}/workspace/environment
/projects/{projectId}/workspace/suite
/projects/{projectId}/workspace/suite/{suiteId}
/projects/{projectId}/workspace/case
/projects/{projectId}/workspace/case/new?suiteId=...
/projects/{projectId}/workspace/case/{caseId}
/projects/{projectId}/workspace/run
/projects/{projectId}/workspace/report
/projects/{projectId}/workspace/report/{runId}
/projects/{projectId}/workspace/report/{runId}/result/{resultId}
/projects/{projectId}/workspace/import/{suiteId}
/projects/{projectId}/workspace/information
```

模块外信息通过 Query：

```text
?from=suite&suiteId=...
?from=report&runId=...&resultId=...
?scope=case|collection|project&scopeId=...
```

URL 是状态的真实源，浏览器后退、刷新、分享全部能恢复。

## 15. 页面本地状态

仅以下短生命周期 UI 状态：

- 侧栏 Drawer 是否展开。
- 列表搜索、筛选、分页。
- 表单 dirty / submitting。
- 模态可见性。

不使用 LocalStorage 保存 Workspace 状态。

---

# ④ URL 路由

## 16. 完整路由表

| 路径 | 页面 | 组件 |
|---|---|---|
| `/projects/:projectId` | 重定向到 Workspace Overview | `<Navigate>` |
| `/projects/:projectId/overview` | 重定向到 Workspace Overview | `<Navigate>` |
| `/projects/:projectId/workspace` | Workspace Overview | `<ProjectWorkspaceLayout><WorkspaceOverview /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/overview` | Workspace Overview | 同上 |
| `/projects/:projectId/workspace/environment` | Workspace Environment | `<ProjectWorkspaceLayout><WorkspaceEnvironment /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/suite` | Workspace Suite 列表 | `<ProjectWorkspaceLayout><WorkspaceSuiteList /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/suite/:suiteId` | Workspace Suite 详情 | `<ProjectWorkspaceLayout><WorkspaceSuiteDetail suiteId /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/case` | Workspace Case 列表 | `<ProjectWorkspaceLayout><WorkspaceCaseList /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/case/new` | Workspace Case 新建 | `<ProjectWorkspaceLayout><WorkspaceCaseEditor /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/case/:caseId` | Workspace Case 编辑 | `<ProjectWorkspaceLayout><WorkspaceCaseEditor /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/run` | Workspace Run | `<ProjectWorkspaceLayout><WorkspaceRun /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/report` | Workspace Report 列表 | `<ProjectWorkspaceLayout><WorkspaceReportList /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/report/:runId` | Workspace Report 详情 | `<ProjectWorkspaceLayout><WorkspaceReportDetail /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/report/:runId/result/:resultId` | Workspace Result 详情 | `<ProjectWorkspaceLayout><WorkspaceResultDetail /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/import/:suiteId` | Workspace Import | `<ProjectWorkspaceLayout><WorkspaceImport /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/workspace/information` | Workspace Information | `<ProjectWorkspaceLayout><WorkspaceInformation /></ProjectWorkspaceLayout>` |
| `/projects/:projectId/settings` | 旧 Settings 路由 | 重定向到 Workspace Information |

## 17. 路由兼容性

所有现有路由保留，重定向到 Workspace：

| 旧路径 | 新路径 |
|---|---|
| `/projects/:projectId/overview` | `/projects/:projectId/workspace/overview` |
| `/projects/:projectId/environments` | `/projects/:projectId/workspace/environment` |
| `/projects/:projectId/suites` | `/projects/:projectId/workspace/suite` |
| `/projects/:projectId/suites/:suiteId` | `/projects/:projectId/workspace/suite/:suiteId` |
| `/projects/:projectId/suites/:suiteId/import/openapi` | `/projects/:projectId/workspace/import/:suiteId` |
| `/projects/:projectId/cases` | `/projects/:projectId/workspace/case` |
| `/projects/:projectId/cases/new` | `/projects/:projectId/workspace/case/new` |
| `/projects/:projectId/cases/:caseId` | `/projects/:projectId/workspace/case/:caseId` |
| `/projects/:projectId/runs` | `/projects/:projectId/workspace/run` |
| `/projects/:projectId/reports` | `/projects/:projectId/workspace/report` |
| `/projects/:projectId/reports/:runId` | `/projects/:projectId/workspace/report/:runId` |
| `/projects/:projectId/reports/:runId/results/:resultId` | `/projects/:projectId/workspace/report/:runId/result/:resultId` |
| `/projects/:projectId/settings` | `/projects/:projectId/workspace/information` |

新增 `Workspace` 父路由组件包裹所有模块，实现统一壳与状态。

## 18. URL 状态规则

- 模块名出现在路径，不出现在 Query。
- 列表搜索、分页、过滤出现在 Query。
- 跨模块上下文（`?from=suite&suiteId=...`、`?scope=case&scopeId=...`）在 Query。
- URL 切换 Project 时 Module 上下文继承。

---

# ⑤ 组件拆分

## 19. 组件树

```text
AppShell
└── WorkspaceRoute
    └── ProjectWorkspaceLayout
        ├── ProjectWorkspaceHeader（顶部信息条）
        │   ├── ProjectIdentity
        │   ├── ProjectHealthBadge
        │   ├── ProjectQuickActions
        │   └── ProjectRefreshControl
        ├── ProjectWorkspaceSider（左侧模块导航）
        │   └── ProjectModuleMenu
        ├── ProjectWorkspaceContextPanel（右侧上下文栏）
        │   ├── ProjectContextEnvironment
        │   ├── ProjectContextLatestRun
        │   ├── ProjectContextQuickCreate
        │   └── ProjectContextReadiness
        ├── Outlet（Workspace 内容区）
        │   ├── WorkspaceOverview
        │   ├── WorkspaceEnvironment
        │   ├── WorkspaceSuiteList
        │   ├── WorkspaceSuiteDetail
        │   ├── WorkspaceCaseList
        │   ├── WorkspaceCaseEditor
        │   ├── WorkspaceRun
        │   ├── WorkspaceReportList
        │   ├── WorkspaceReportDetail
        │   ├── WorkspaceResultDetail
        │   ├── WorkspaceImport
        │   └── WorkspaceInformation
        └── ProjectWorkspaceFooter（低优先级提示）
```

## 20. 组件职责

| 组件 | 单一职责 | 主要输入 | 主要行为 |
|---|---|---|---|
| `ProjectWorkspaceLayout` | 包裹 Project 上下文，统一布局 | `projectId` | 注入 Provider、渲染三段式 |
| `ProjectWorkspaceHeader` | Project 摘要、状态徽标、刷新 | Project、Summary | 跳转、刷新、状态徽标 |
| `ProjectWorkspaceSider` | 模块导航 | 当前模块 | 切换模块、状态标记 |
| `ProjectWorkspaceContextPanel` | Project 上下文侧栏 | Project + 资产 | 显示默认环境、最近执行、完整度 |
| `WorkspaceOverview` | Workspace 入口页 | projectId | 摘要 + 最近活动 |
| `WorkspaceEnvironment` | 环境管理 | projectId | 列表 + 表单 |
| `WorkspaceSuiteList` | Suite 列表 | projectId | 列表 + 新建 |
| `WorkspaceSuiteDetail` | Suite 详情 | projectId, suiteId | 用例关联、Import、执行 |
| `WorkspaceCaseList` | Case 列表 | projectId | 列表 + 过滤 + 执行入口 |
| `WorkspaceCaseEditor` | Case 编辑器 | projectId, caseId | 表单 + 保存 + 执行 |
| `WorkspaceRun` | 发起 + 最近 Run | projectId | 同步执行、最近 5 条 |
| `WorkspaceReportList` | Report 列表 | projectId | 列表 + 过滤 |
| `WorkspaceReportDetail` | Report 详情 | runId | 概览 + 失败 + 全部结果 |
| `WorkspaceResultDetail` | Result 详情 | resultId | 请求/响应/断言/错误 |
| `WorkspaceImport` | OpenAPI 导入 | suiteId | 预览 + 确认 |
| `WorkspaceInformation` | 项目信息 | projectId | 编辑 + 删除项目 |
| `ProjectHealthBadge` | 项目健康度徽标 | Summary | 显示颜色和数值 |
| `ProjectModuleMenu` | 模块导航菜单 | 当前模块、完整度 | 切换模块 |
| `ProjectContextEnvironment` | 默认环境信息 | Environments | 点击跳到详情 |
| `ProjectContextLatestRun` | 最近执行 | Summary、Latest Run | 点击跳到 Report |
| `ProjectContextQuickCreate` | 快速创建 | — | 跳到对应模块的创建表单 |
| `ProjectContextReadiness` | 资产完整度 | Project、Suites、Cases、Environments | 标记缺失并引导 |

## 21. 组件边界原则

- Layout 组件不渲染模块内容，只承担三段式结构、Provider 与状态徽标。
- Workspace Provider 注入共享状态，但本身不调用业务 API。
- 模块组件不直接使用全局导航状态；通过 Layout 提供的回调进行跳转。
- 跨模块跳转 URL 始终带 `from=...`，返回行为可恢复。
- Ant Design 组件只用于表现，不嵌入业务规则。

## 22. 复用与新增

| 现有组件 | 在 Workspace 中的用途 |
|---|---|
| `PageHeader` | Overview、Environment 等模块内容区标题 |
| `EmptyState / ErrorState / LoadingBlock` | 各模块 Loading / Empty / Error 状态 |
| `StatusTags` | Run / Result / Suite 状态显示 |
| `ProjectFormModal` | 仍用于全局 Project 列表的创建；Workspace 内不重复 |
| `EnvironmentFormModal / SuiteFormModal` | Workspace 模块的创建 / 编辑表单 |
| `RecentRunsPanel / RecentProjectsPanel` | Overview 模块复用 |

无现有能力可复用的部分：Workspace 顶部信息条、模块导航、右侧上下文栏需新增为独立组件。

## 23. 加载与状态管理原则

- 每个模块独立 Loading / Empty / Error。
- Provider 加载慢时仅阻塞 Layout 骨架，不阻塞模块。
- 模块切换不重新加载整个 Workspace。
- URL 切换 Project 时清空旧 Project 缓存。

---

## 24. 数据流概览

```text
URL: /projects/{projectId}/workspace/{module}
  │
  ▼
ProjectWorkspaceLayout
  │
  ├── useProjectWorkspaceData(projectId)
  │     ├── project
  │     ├── environments（供 Environment 模块与上下文栏）
  │     ├── suites（供 Suite 列表与上下文栏）
  │     ├── cases total
  │     ├── runs/summary
  │     └── latestRun
  │
  ├── ProjectContext.Provider
  │     ├── projectMeta
  │     ├── readiness
  │     └── refresh()
  │
  ├── Header
  ├── Sider
  ├── ContextPanel
  └── Outlet → Workspace{module}
```

模块组件不再独立请求 Project 详情，统一从 Context 读取，仅请求各自业务数据。

---

## 25. 跳转关系总表

| 来源 | 目标 | URL 模式 |
|---|---|---|
| Dashboard 卡片 | Workspace Overview | `/projects/{projectId}/workspace/overview` |
| Dashboard 发起执行按钮 | Workspace Run（prefill scope=project） | `/projects/{projectId}/workspace/run?scope=project` |
| Dashboard 最近 Run | Workspace Report 详情 | `/projects/{projectId}/workspace/report/{runId}` |
| Header Project 名 | Workspace Overview | `/projects/{projectId}/workspace/overview` |
| Header 默认环境 | Workspace Environment 模块 | `/projects/{projectId}/workspace/environment` |
| Header 快速执行 | Workspace Run（prefill scope=project） | 同上 |
| Sider 切换 | Workspace {module} | `/projects/{projectId}/workspace/{module}` |
| ContextPanel 默认环境 | Workspace Environment | 同上 |
| ContextPanel 最近 Run | Workspace Report 详情 | `/projects/{projectId}/workspace/report/{runId}` |
| ContextPanel 快速创建 | 对应模块新建表单 | `/projects/{projectId}/workspace/{module}/new` |
| Run 模块发起完成 | Workspace Report 详情 | `/projects/{projectId}/workspace/report/{runId}` |
| Report 列表点击 Run | Workspace Report 详情 | 同上 |
| Report 详情 Result 跳 Case | Workspace Case 编辑器 | `/projects/{projectId}/workspace/case/{caseId}?from=report&runId=&resultId=` |
| Import 完成 | Workspace Suite 详情 | `/projects/{projectId}/workspace/suite/{suiteId}` |
| Information 删除项目 | Project 列表 | `/projects` |

---

## 26. 验收标准

### 入口与导航

- [ ] 点击 Dashboard Project 卡片直接进入 Workspace。
- [ ] 点击 Header Project 名回到 Workspace Overview。
- [ ] 旧 Project 路由全部重定向到 Workspace，不出现 404。
- [ ] 顶部信息条、左侧模块导航、右侧上下文栏在所有 Workspace 内页面保持稳定。

### 信息架构

- [ ] Workspace 仅包含现有能力的 Project 内工作区，不出现全平台、跨 Project 汇总。
- [ ] Overview、Environment、Suite、Case、Run、Report、Import、Information 八大模块均已实现。
- [ ] 每个模块保留现有 CRUD、列表、详情、编辑能力。
- [ ] 旧的“Project CRUD”页面被降级为 Information Tab，CRUD 行为完整保留。

### 状态共享

- [ ] 切换模块不重新请求 Project 元信息。
- [ ] 切换模块时，原 Project 的最近执行、默认环境、资产计数保持显示。
- [ ] 模块间跳转 URL 携带 `from=` 和 `?suiteId=...` 等上下文。

### 响应式

- [ ] 桌面端、平板端、移动端布局合理。
- [ ] 平板端隐藏右侧上下文栏。
- [ ] 移动端将左侧模块导航折叠为 Drawer。

### 性能与构建

- [ ] Workspace 路由下页面均通过懒加载，关闭后不阻塞其他模块。
- [ ] Provider 内部查询使用 `staleTime`，避免每次切换都重新拉取。
- [ ] ESLint、TypeScript 严格模式、生产构建通过。
- [ ] 没有新增接口、修改后端、修改数据库或迁移。

### 视觉

- [ ] 顶部信息条稳定显示 Project、Owner、最近执行、健康度。
- [ ] 右侧上下文栏仅在桌面端显示。
- [ ] 所有 Loading / Empty / Error 状态有明确文案和动作。

---

## 27. 最终推荐方案摘要

```text
Project Workspace
├── Header：Project 元信息 + 状态徽标 + 快速执行
├── Sider：Overview / Environment / Suite / Case / Run / Report / Import / Information
├── ContextPanel：默认环境 + 最近 Run + 快速创建 + 资产完整度
└── Outlet
    ├── Overview
    ├── Environment
    ├── Suite (List / Detail)
    ├── Case (List / Editor)
    ├── Run
    ├── Report (List / Detail / Result)
    ├── Import
    └── Information
```

该方案在不修改任何后端 API、不增加数据库的前提下，把 Project 内的工作流从“分页面”重构为“工作空间”，形成清晰的资产维护与执行闭环，并通过 Provider 共享 Project 上下文与状态。
