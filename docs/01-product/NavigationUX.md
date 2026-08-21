# API 自动化测试平台 · Project Workspace 导航 UX 优化

> 文档类型：Project Workspace 导航 UX 设计规范
> 适用范围：API 自动化测试平台前端 / Project Workspace 内部导航
> 设计阶段：先设计，不涉及代码实现
> 配套：`PRD.md`、`INFORMATION_ARCHITECTURE.md`、`PROJECT_WORKSPACE.md`、`NavigationUX.md`（既有全局导航规范）、`Journey.md`、`WorkflowReview.md`、`FirstRunGuide.md`、`EmptyState.md`
> **硬约束：不新增任何 API、不新增任何数据库表、不新增功能模块——仅复用已有 Project / Environment / Suite / Case / Run / Report / OpenAPI 7 类 API + 已有组件 + 前端路由 / URL Query / LocalStorage**

---

## 0. 设计目标

Project Workspace 内部导航体验从"能用"升级为"易用"。新增 / 优化 6 大导航能力：

| # | 能力 | 核心收益 | 数据源 |
|---:|---|---|---|
| 1 | **Recent Project** | 用户 1 步回到"上次干活的地方"，告别"Project 列表 → 搜索 → 选 → 概览"4 步 | LocalStorage `app.recentProjects` |
| 2 | **Back** | 任何页面 1 步回到上级，浏览器 Back 与页面"返回"按钮行为一致 | `history.back()` + URL Query |
| 3 | **Breadcrumb** | 用户随时知道"我在 Project X / 模块 Y / 对象 Z" | URL Path 解析 |
| 4 | **Quick Action** | Workspace Header 一键执行 / 切换环境 / 跳转最近 Report | 已有 React Query |
| 5 | **Recent Runs** | 当前 Project 最近 5 条 Run 一目了然，失败置顶 | `GET /runs?limit=5`（已有） |
| 6 | **Recent Reports** | 当前 Project 最近 5 条 Report（含通过率），跳转直达 | `runs/summary.recent_runs`（已有） |

**三大统一原则**：

1. **三层心智模型**：平台层（Dashboard / 项目列表 / 系统管理） → Project 层（Workspace 八大模块） → 详情层（Suite 详情 / Case 编辑 / Run 详情 / Result 详情）。
2. **永保留上下文**：Project / Suite / Case / Run 切换不丢失搜索 / Tab / 分页，全部进 URL Query。
3. **永保留返回路**：浏览器 Back / 页面返回按钮 / 面包屑"上一级"三者行为一致。

---

## 1. 当前架构现状（基于既有文档 / 代码）

### 1.1 已具备的组件

| 组件 | 位置 | 现状 |
|---|---|---|
| `ProjectWorkspaceLayout` | `frontend/src/components/workspace/` | 三段式布局：Header / Sider / Outlet |
| `ProjectWorkspaceHeader` | 同上 | 顶部信息条（Project 名 + Owner + 状态徽标） |
| `ProjectWorkspaceSider` | 同上 | 左侧模块导航（Overview / Environment / Suite / Case / Run / Report / Import / Information） |
| `ProjectWorkspaceContextPanel` | 同上 | 右侧上下文栏（默认环境 / 最近 Run / 快速创建） |
| `RecentProjectsPanel` | `frontend/src/components/dashboard/` | Dashboard 上"Recent Projects"卡片（**已存在但未启用 LocalStorage 持久化**） |
| `RecentRunsPanel` | 同上 | Dashboard / Overview 上"Recent Runs"卡片（已存在） |
| `RecentReportsPanel` | 同上 | Dashboard 上"Recent Reports"卡片（已存在） |
| `RecentSuitesPanel` | 同上 | Overview 上 Suite 摘要卡片 |
| `DashboardMetricCard` | 同上 | Dashboard KPI 卡 |
| `PageHeader` | `frontend/src/components/` | 通用页面标题 + 面包屑 + 主操作区 |

### 1.2 已具备的 API / 数据

| 数据 | API（已有） | 用途 |
|---|---|---|
| 用户全部 Project | `GET /projects` | Project Switcher 数据源 |
| 单 Project 详情 | `GET /projects/:projectId` | Header / Overview 项目摘要 |
| 当前 Project 最近 Run | `GET /projects/:projectId/runs/summary`（recent_runs） | Overview + Quick Action 数据源 |
| 当前 Project 最近 Report | `GET /projects/:projectId/runs?limit=5` | Recent Reports 数据源 |
| 单 Run 详情 | `GET /runs/:runId` | Recent Run 行点击跳转 |
| 当前 Project 默认环境 | `GET /projects/:projectId/environments` + `is_default=true` | Quick Action 切换环境 |
| 资产完整度 | `runs/summary.total_*` + `environments.total` + `suites.total` + `cases.total` | Header 状态徽标 |

### 1.3 当前痛点（来自 `UX_REVIEW.md` 与 `WorkflowReview.md`）

| ID | 痛点 | 引用 |
|---|---|---|
| **H1** | Project 切换上下文不重置（URL 中 runId / caseId 残留） | UX_REVIEW §1.16 / WorkflowReview §3.1 |
| **H2** | 三处执行入口不一致（Suite / Case / Header / Run Center） | UX_REVIEW §1.11 / WorkflowReview §2.7-H1 |
| **H3** | Report 列表与 Overview 区块完全重复 | UX_REVIEW §1.12 / WorkflowReview §2.8-H1 |
| **M1** | Overview 与 Run Detail 概览 Tab KPI 重复 | UX_REVIEW §1.13 |
| **M6** | Case 编辑返回丢失搜索状态 | UX_REVIEW §1.9 / WorkflowReview §2.5-H3 |
| **M10** | 缺全局搜索（依赖后端聚合接口，本期未提供） | UX_REVIEW §1.18 |

**本文档为每个痛点给出**前端可落地的修复策略，全部**不新增 API**。

---

# 2. Recent Project 设计

## 2.1 目标

用户从 Dashboard **1 次点击**直达最近操作的 Project，不必再走"Project 列表 → 搜索 → 选 → 概览"4 步冗余。

## 2.2 数据来源与持久化

| 来源 | 优先级 | 说明 |
|---|---|---|
| **最近 5 个 Project** | 最高 | 按 `lastVisitedAt` 倒序，**LocalStorage 持久化** |
| **拥有的全部 Project** | 中 | 当前用户 owner 的 Project，按 `updatedAt` 倒序（来自 `GET /projects`） |
| **收藏 Project** | （本期不做） | 未来扩展 |

**LocalStorage Schema**：

```typescript
// app.recentProjects
type RecentProject = {
  id: string;
  name: string;
  visitedAt: string;  // ISO 8601
};

// LocalStorage["app.recentProjects"]: RecentProject[]
// - 最多 5 项
// - 超出按 visitedAt 淘汰
// - 仅存 ID + 名称，不存任何 Project 内部数据
```

**写入时机**：
- 用户进入 `/projects/:projectId/**` 任意页面 → 写入当前时间到 LocalStorage
- 用户**切换 Project** 时，**保留** 5 个最近列表（不覆盖）
- 用户**主动删除 Project** 后 → 从 LocalStorage 清除该 ID

## 2.3 UI 呈现（Dashboard）

Dashboard 顶部 KPI 卡片下方放置 "Recent Projects" 区：

```text
┌─ Recent Projects ──────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 用户服务 API │  │ 订单中心 API │  │ 管理后台 API │              │
│  │ 👤 张三 · 3h │  │ 👤 张三 · 1d │  │ 👤 张三 · 3d │              │
│  │ ✓ 今日回归   │  │ ⚠ 待冒烟     │  │ — 7d 未访问   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                  [+ 新建]│
└─────────────────────────────────────────────────────────────────────┘
```

| 属性 | 规则 |
|---|---|
| 卡片数 | 5 个（不足则全部展示） |
| 排序 | `lastVisitedAt desc` |
| 信息 | Avatar（自动从 name 取首字）+ 名称 + 上次访问时间（如"3 小时前"）+ Owner 缩写 + 今日回归徽标 |
| 点击 | **直接进入该 Project 概览**（不再二次点击） |
| 空态 | "你还没有访问过 Project，去 [项目列表](#) 创建第一个" |
| 卡片右上角 | 今日是否已回归（基于 `runs/summary.last_run_at`） |

## 2.4 登录后默认落点（联动）

```text
[登录成功]
   ↓
[读取 LocalStorage.app.recentProjects]
   ↓
   ├─ 第一项 ≤ 7 天 → 直接跳该 Project 概览（节省 3 步）
   ├─ 第一项 > 7 天 → 落 Dashboard
   └─ 空 → 落 Dashboard
   ↓
[如有合法 returnTo URL → 优先跳 returnTo]
```

## 2.5 Project Switch 增强（联动）

`Project Switcher` 下拉改为 3 段：

```text
┌─ 切换 Project ──────────────────────┐
│ 🔍 搜索项目                         │
├─────────────────────────────────────┤
│ 最近                                │
│   👤 用户服务 API      · 3h 前      │
│   👤 订单中心 API      · 昨天       │
│   👤 管理后台 API      · 3 天前     │
├─────────────────────────────────────┤
│ 全部                                │
│   👤 用户服务 API                  │
│   👤 订单中心 API                  │
│   👤 管理后台 API                  │
│   👤 风控网关 API                  │
├─────────────────────────────────────┤
│ + 新建 Project                      │
└─────────────────────────────────────┘
```

**实现位置**：Sider 顶部 Project Switcher（已有）+ LocalStorage 读取。

## 2.6 退出 / 清除策略

| 场景 | 行为 |
|---|---|
| 用户主动删除 Project | 从 LocalStorage 移除该 ID（通过监听 `projects` query invalidate） |
| 用户切换账号 | LocalStorage 保留（不清空），因为 `id` 唯一；若 ID 在新账号下不存在，下次访问时 Query 失败，自动清除 |
| 用户清浏览器缓存 | LocalStorage 全清，按"无 Recent"处理 |
| 24h 内未访问任何 Project | Dashboard 顶部不显示 Recent 区，只显示"创建 Project"空态 |

---

# 3. Back 设计

## 3.1 Back 的两种来源

| 来源 | 行为 | 适用范围 |
|---|---|---|
| **浏览器 Back 键 / Backspace** | `history.back()` | 任何页面 |
| **页面"返回"按钮**（PageHeader 左侧） | 显式路由跳转 | 详情页 / Drawer / Modal |

**二者必须等价**（按浏览器 Back 等同于点页面"返回"按钮）。

## 3.2 Back 行为分级

| 当前页 | Back 目标 | 实现 |
|---|---|---|
| L3 详情页 | L3 列表页（带原 URL Query） | `navigate(-1)` 或读 `?returnTo=` |
| L3 详情页（从另一对象跳入） | 来源对象详情 | `navigate(returnTo)` |
| L2 模块页 | L2 概览页（Overview） | `navigate(/projects/:id/workspace/overview)` |
| L1 平台页 | Dashboard | `navigate(/dashboard)` |
| Project 概览 | Dashboard | `navigate(/dashboard)` |
| Drawer / Modal | 关闭浮层（**不**触发 `history.back`） | Drawer `onClose` |
| 全屏错误页 | 浏览器 Back 退出整个 App | `history.back()`（符合预期） |

## 3.3 "返回"按钮位置

| 页面类型 | 位置 | 文案 |
|---|---|---|
| L3 详情页 | `PageHeader` 标题**左侧**（H4 图标 + "返回"） | "返回" |
| Drawer | Header 左侧 | "关闭" / `CloseOutlined` |
| Modal | Header 右侧 | `CloseOutlined` |
| 全屏错误页 | 错误主体下方 | "返回 Dashboard" |

## 3.4 Drawer / Modal 的 Back 特殊处理

- **Drawer / Modal 打开不创建新 history 记录**（避免按 Back 直接关闭，反而绕过业务路径）。
- Drawer / Modal **关闭**使用浮层内部"取消 / 关闭"按钮，**不依赖**浏览器 Back。
- 浏览器 Back 键在 Drawer / Modal 打开期间被禁用（`maskClosable={false}` + 监听 `popstate` 拦截）。

## 3.5 Back 后必须恢复的状态

| 状态 | 是否恢复 |
|---|---|
| 滚动位置 | ✅ 恢复 |
| 搜索 / 筛选 | ✅ 恢复（来自 URL Query） |
| Tab | ✅ 恢复（来自 URL Query `?tab=`） |
| 分页 | ✅ 恢复（来自 URL Query `?page=`） |
| Drawer / Modal 打开状态 | ❌ 不恢复（Back 不应反向"打开"） |
| 表单未保存内容 | ⚠️ 弹离开确认（`beforeunload` 类） |

## 3.6 实现位置

- 全局 `RouteGuards.tsx` 增加 `usePopStateListener` Hook
- 各详情页 `PageHeader` 增加 `<Button onClick={handleBack} icon={<ArrowLeftOutlined />}>返回</Button>`

---

# 4. Breadcrumb 设计

## 4.1 三级 Breadcrumb

平台统一使用**三级面包屑**结构：

```text
[层级1：平台 / 项目] / [层级2：模块] / [层级3：对象]
```

| 用户所在 | Breadcrumb |
|---|---|
| Workspace Overview | `工作台 / 项目 / 用户服务 API` |
| Environment 列表 | `用户服务 API / 环境` |
| Environment 详情 | `用户服务 API / 环境 / 测试环境` |
| Suite 列表 | `用户服务 API / 测试套件` |
| Suite 详情 | `用户服务 API / 测试套件 / 冒烟回归` |
| Case 编辑器 | `用户服务 API / API 用例 / 获取用户详情` |
| Run 报告列表 | `用户服务 API / 测试报告` |
| Run 报告详情 | `用户服务 API / 测试报告 / Run #20260715` |
| Result 详情 | `用户服务 API / 测试报告 / Run #20260715 / Result #3` |

## 4.2 链接行为

| 段 | 行为 |
|---|---|
| **层级1（平台 / 项目）** | 永远可点击。点击 → 对应平台的规范入口（Dashboard / Project 列表 / 用户管理） |
| **层级2（模块）** | 永远可点击。点击 → 对应模块的**列表页**（保留 URL Query 如 `?search=&page=`） |
| **层级3（对象）** | 当前页时不可点击；其余对象页可点击，**跳转后保留原上下文** |

## 4.3 与 Workspace Header 的协同

- Workspace Header 已包含 Project 名 + 关键信息时，**面包屑的"层级1"允许省略**，避免与 Header 重复。
- Workspace Header 不吸顶（与内容一起滚动），面包屑始终在 `PageHeader` 顶部。

## 4.4 缺失场景

- Dashboard（首页） → 不显示面包屑
- 全屏空状态 / 全屏错误页 → 不显示面包屑
- 登录页 → 不显示面包屑

## 4.5 实现位置

`PageHeader` 组件已支持 `breadcrumbs?: { title: string; href?: string }[]`，各 Workspace 页面在 PageHeader 中传入。

---

# 5. Quick Action 设计

## 5.1 Workspace Header Quick Action

`ProjectWorkspaceHeader` 增加 4 个常驻快速操作按钮：

| 按钮 | 行为 | 数据源 |
|---|---|---|
| **▶️ 快速执行** | 打开 `RunExecutionDrawer`，scope 默认 project | `useProjectWorkspace().enabledCaseCount` |
| **🌐 切换环境** | 下拉切换默认环境，立即更新 | `GET /environments`（已有） |
| **📋 复制 Project ID** | 复制 ID 到剪贴板，Toast 提示 | `project.id`（已有） |
| **🔄 刷新** | 失效所有 Project 相关 Query | `queryClient.invalidateQueries` |

## 5.2 主操作按钮（按页面变化）

| 当前页面 | 主操作 | 次操作 |
|---|---|---|
| 项目概览 | 发起 Project 执行 | 复制 Project ID |
| 环境管理 | 新建环境 | 切换默认环境 |
| Suite 列表 | 新建 Suite | 导入 OpenAPI |
| Suite 详情 | 新建用例；次操作：导入 OpenAPI、执行 Suite | 编辑 Suite、删除 Suite |
| API Case 列表 | 新建用例（先选 Suite） | 导入 OpenAPI |
| API Case 详情 | 选择环境并执行 | 保存、删除 |
| 执行中心 | 发起执行 | 复制 Project ID |
| 测试报告 | （无写操作） | 跳转到执行中心 |
| 项目设置 | 保存更改 | 删除 Project |
| OpenAPI Import | 确认导入 | 取消 |

## 5.3 Quick Action 与 FirstRunGuide 联动

- 处于引导状态时，Quick Action 中"快速执行"按钮被引导覆盖，**点击仍打开 Drawer 但 drawer 标题显示"🎯 引导第 X 步"**。
- 引导 Step 2 时，Workspace Header 的"创建环境"按钮**自动 Pulse 红点动效**（3 秒后停止）。

## 5.4 实现位置

`ProjectWorkspaceHeader.tsx` 增加 `quickActions: QuickAction[]` 配置；各模块页面通过 `useProjectWorkspace()` 获取上下文数据。

---

# 6. Recent Runs 设计

## 6.1 数据源

```text
GET /projects/:projectId/runs/summary
  → summary.recent_runs: Run[]   // 最近 5 条 Run
```

## 6.2 出现位置

| 位置 | 数据 | 数量 |
|---|---|---|
| **Workspace Header 下拉** | 最近 5 条 Run，点击直达 Run 详情 | 5 |
| **Workspace Overview "最近执行"** | 最近 5 条 Run + "查看全部 →" | 5 |
| **Workspace Overview 缺省空态** | "▶️ 还没有执行记录" | 0 |

## 6.3 UI 呈现（Workspace Header 下拉）

```text
┌─ 最近执行 ──────────────────────────────────────────────┐
│ ✓ 用户服务回归    92.5%   12.3s   suite   16:42    › │
│ ✗ Case 列表加载失败  45.0%    6.1s   case    16:30    › │
│ ✓ Order Service Run  98.0%   18.0s   project 16:15    › │
├──────────────────────────────────────────────────────┤
│ [查看全部 Report →]                                       │
└──────────────────────────────────────────────────────┘
```

## 6.4 视觉规范

| 属性 | 规则 |
|---|---|
| 状态色 | passed 绿 / failed 红 / error 橙 / skipped 灰 |
| 行 hover | 背景 `#fafbff` |
| 点击 | 进入 Run 详情（直接，不经过 Report 列表） |
| 排序 | 按 `started_at desc` |
| 空态 | "▶️ 还没有执行记录，点击发起 Run" |

## 6.5 与 Report 列表去重

- Workspace Overview **"最近执行"区块**保留（Top 5），不与 Report 列表重复；
- Report 列表提供**完整列表**（含筛选 / 搜索 / 分页 / scope 筛选）；
- 二者用不同定位：Overview "最近 Run"是"概览"，Report 列表是"历史管理"。

## 6.6 失败置顶（智能排序）

- 当有 failed / error Run 时，Overview 与 Header 下拉的 Recent Runs **失败项置顶**（不强制但强烈推荐）。
- 通过前端对 `recent_runs` 排序：`failed / error` → `passed` → `running`，同状态按时间倒序。

## 6.7 实现位置

复用 `RecentRunsPanel.tsx`（已存在），增强"失败置顶"排序逻辑；在 `ProjectWorkspaceHeader.tsx` 增加下拉 Trigger。

---

# 7. Recent Reports 设计

## 7.1 数据源

```text
GET /projects/:projectId/runs?limit=5
  → items: Run[]   // 最近 5 条 Run（含完整 Report 信息）
```

## 7.2 出现位置

| 位置 | 数据 | 数量 |
|---|---|---|
| **Dashboard "Recent Reports" 区** | 最近 5 条 Report | 5 |
| **Workspace Header "最近 Report" 下拉**（与 Recent Runs 共享） | 最近 5 条 Report | 5 |

> **注意**：Recent Runs 与 Recent Reports 在 Header 下拉中**合并为一个下拉**（避免 2 个 Trigger 抢占 Header 空间），通过 Tab 切换"按时间 / 按状态"。

## 7.3 UI 呈现（Dashboard）

```text
┌─ Recent Reports ──────────────────────────────────────────────┐
│ Run #20260715-1  ✓ 92.5%  用户服务回归  suite  12.3s  16:42  › │
│ Run #20260715-2  ✗ 45.0%  Case 列表加载失败  case   6.1s 16:30 › │
│ Run #20260715-3  ✓ 98.0%  Order Service Run  project 18s 16:15 › │
├──────────────────────────────────────────────────────────┤
│ [查看全部 Report →]                                            │
└──────────────────────────────────────────────────────────┘
```

## 7.4 与 Recent Runs 的区别

| 维度 | Recent Runs | Recent Reports |
|---|---|---|
| 数据源 | `runs/summary.recent_runs` | `runs?limit=5` |
| 字段 | 摘要（不含 Result 数） | 完整（含通过率 / 耗时 / 范围） |
| 用途 | Header 快捷入口（看最新） | Dashboard 完整摘要（看趋势） |
| 排序 | 失败置顶 + 时间倒序 | 时间倒序 |

## 7.5 实现位置

复用 `RecentReportsPanel.tsx`（已存在），数据源从 `runs/summary.recent_runs` 切换为 `runs?limit=5`。

---

# 8. 各模块页面与 6 大能力的整合

## 8.1 Workspace Overview 整合

```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎯 引导横幅（FirstRunGuide，第 X / 6 步）  ← 仅引导状态显示         │
├──────────────────────────────────────────────────────────────────────┤
│  Workspace Header                                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 用户服务 API · 👤 张三 · ✓ 资产齐全 · [▶ 快速执行] [🌐 切换环境]│  │
│  │                                                       [🔄 刷新]│  │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  PageHeader                                                          │
│  Breadcrumb: 用户服务 API / 概览                                       │
│                                                                       │
├──────────────────────────────────────────────────────────────────────┤
│  Empty State / 资产缺失卡（按优先级）                                 │
│  ── 或 ──                                                            │
│  项目摘要 + 资产计数（环境 X / Suite X / Case X）                      │
│                                                                       │
├──────────────────────────────────────────────────────────────────────┤
│  Recent Runs (Top 5，失败置顶)                              [查看全部]│
│  ...                                                                  │
├──────────────────────────────────────────────────────────────────────┤
│  快速创建（ContextPanel）：环境 / Suite / Case                        │
└──────────────────────────────────────────────────────────────────────┘
```

## 8.2 Suite 详情整合

```text
┌──────────────────────────────────────────────────────────────────────┐
│  Workspace Header（Quick Action: ▶ 快速执行）                         │
├──────────────────────────────────────────────────────────────────────┤
│  PageHeader                                                          │
│  Breadcrumb: 用户服务 API / 测试套件 / 冒烟回归  ← Back 按钮在左侧    │
│  主操作: [执行 Suite] [OpenAPI 导入] [编辑] [删除]                    │
├──────────────────────────────────────────────────────────────────────┤
│  Suite 摘要（Case 数 / 已启用 / 末次 Run 通过率）                    │
├──────────────────────────────────────────────────────────────────────┤
│  Case 列表  ←  [批量添加] [新建 Case]                                 │
│  ...                                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

## 8.3 Case 编辑器整合

```text
┌──────────────────────────────────────────────────────────────────────┐
│  Workspace Header                                                    │
├──────────────────────────────────────────────────────────────────────┤
│  PageHeader                                                          │
│  [← 返回]  来自：[冒烟回归 Suite]                                    │
│  Breadcrumb: 用户服务 API / API 用例 / 获取用户详情                   │
│  主操作: [💾 保存] [💾 保存并执行] [▶ 选择环境并执行]                 │
├──────────────────────────────────────────────────────────────────────┤
│  基本信息 / 请求配置 / 断言配置  ← Tab 切换                            │
└──────────────────────────────────────────────────────────────────────┘
```

## 8.4 Run 详情整合

```text
┌──────────────────────────────────────────────────────────────────────┐
│  Workspace Header                                                    │
├──────────────────────────────────────────────────────────────────────┤
│  PageHeader                                                          │
│  [← 返回 Report 列表]                                                │
│  Breadcrumb: 用户服务 API / 测试报告 / Run #20260715                  │
│  主操作: [▶️ 再次执行]  ← 预填原 scope / env                          │
├──────────────────────────────────────────────────────────────────────┤
│  RunHeaderCard: ✓ finished · 92.5% · suite · 12 Case · 12.3s · staging│
├──────────────────────────────────────────────────────────────────────┤
│  Tabs: [概览] [失败原因 (3)] [全部 Result] [元信息]                    │
│  默认 Tab = 失败原因（若有）/ 概览（若无）                             │
└──────────────────────────────────────────────────────────────────────┘
```

---

# 9. URL Query 持久化规范（导航能力的基石）

## 9.1 全局 Query Key 命名

| Query Key | 用途 | 出现页 |
|---|---|---|
| `?search=` | 搜索关键字 | 列表页（Project / Suite / Case / Report / Run） |
| `?page=` | 分页 | 列表页 |
| `?size=` | 每页条数 | 列表页 |
| `?status=` | 状态筛选 | Run / Result 列表 |
| `?method=` | HTTP Method 筛选 | Case 列表 |
| `?tab=` | 当前 Tab | Run / Result 详情页 |
| `?returnTo=` | 编辑后回跳目标 | 编辑器 |
| `?scope=` | 执行范围 | Run Center / Drawer |
| `?scopeId=` | 执行范围 ID | Run Center / Drawer |
| `?from=` | 来源标识 | 跨模块跳转（dashboard / suite / report / firstRun） |
| `?runId=` | 来源 Run | Result → Case 编辑器 |
| `?resultId=` | 来源 Result | Result → Case 编辑器 |
| `?drawer=` | Drawer 状态 | Drawer 打开 / 关闭 |

## 9.2 通用 Hook

提供 `useUrlQueryState(key, defaultValue)` 统一读写 URL Query，所有 Workspace 列表 / 详情页使用。

**实现位置**：`frontend/src/hooks/useUrlQueryState.ts`（纯前端工具）。

## 9.3 Back / Forward / 分享支持

- 所有 Query **写入 URL**，浏览器 Back / Forward 可恢复。
- 任意 URL 复制粘贴后打开，**保持原状态**（搜索 / Tab / 分页 / Drawer 状态）。

---

# 10. 导航能力依赖矩阵

| 能力 | 依赖的已有数据 / API | 依赖的已有组件 |
|---|---|---|
| **Recent Project** | LocalStorage + `GET /projects` | `RecentProjectsPanel` |
| **Back** | URL Path + `history.back()` | `PageHeader` + `RouteGuards` |
| **Breadcrumb** | URL Path 解析 | `PageHeader.breadcrumbs` |
| **Quick Action** | `runs/summary` + `environments` | `ProjectWorkspaceHeader` |
| **Recent Runs** | `runs/summary.recent_runs` | `RecentRunsPanel` |
| **Recent Reports** | `runs?limit=5` | `RecentReportsPanel` |

**0 新增 API、0 新增 DB、0 新增功能模块**。

---

# 11. 实施优先级

| # | 任务 | 优先级 | 估时 | 价值 |
|---:|---|:-:|:-:|:-:|
| 1 | `useUrlQueryState` Hook + 全局 Query 持久化 | P0 | 1 天 | 高 |
| 2 | Recent Projects LocalStorage 持久化 + Dashboard 改造 | P0 | 1 天 | 高 |
| 3 | 登录后默认落点（Recent Project 判定） | P0 | 0.5 天 | 高 |
| 4 | PageHeader Back 按钮 + RouteGuards popstate | P0 | 1 天 | 高 |
| 5 | Project Switch 三层策略（A/B/C）+ 切换器 UI 改版 | P0 | 2 天 | 高 |
| 6 | Workspace Header Quick Actions（快速执行 / 切换环境 / 刷新） | P0 | 1 天 | 高 |
| 7 | Recent Runs / Recent Reports 失败置顶 + Header 下拉合并 | P0 | 1 天 | 高 |
| 8 | Breadcrumb 三级结构（PageHeader 已支持 breadcrumbs） | P1 | 0.5 天 | 中 |
| 9 | Drawer / Modal 的 Back 行为一致化 | P1 | 1 天 | 中 |
| 10 | Recent Reports 数据源切换（runs?limit=5） | P1 | 0.5 天 | 中 |
| 11 | Recent Project 空态 + 24h 失效逻辑 | P2 | 0.5 天 | 中 |
| 12 | 跨 Project 切换时的状态清理（drawer / scroll / form） | P2 | 1 天 | 中 |

---

# 12. 验收指标

| 指标 | 计算方式 | 当前 | 目标 |
|---|---|---|---|
| **主流程平均点击数** | 4 条 Journey 总点击数 / 4 | ~18 | ≤ 10 |
| **迷失事件率** | 用户 1 分钟内 Back / 面包屑 ≥ 3 次 | 高 | ≤ 5% |
| **Project 切换上下文错位率** | 切换后 URL 残留旧 Project entityId | 高 | **0%** |
| **Recent Project 使用率** | 从 Dashboard 进入 Project 经 Recent 卡片 | 低 | ≥ 60% |
| **登录后落点 Recent Project 命中率** | 老用户登录后直跳 Project 概览 | 0% | ≥ 60% |
| **执行完成自动跳转率** | Run 完成后自动跳 Report | — | 100% |
| **保存后自动回跳率** | 编辑器保存后自动回到来源页 | — | 100% |
| **Back 按钮点击率** | 详情页通过 Back 按钮 vs 浏览器 Back 的比例 | — | 50% / 50% |
| **URL Query 可恢复率** | 浏览器 Back 后搜索 / 筛选 / Tab 完整恢复 | 部分 | **100%** |
| **Drawers / Modals 误关闭率** | 用户在提交期间因误触关闭的比例 | — | ≤ 1% |

---

# 13. 与既有文档的对应关系

| 本文档 | 与既有文档的对应 |
|---|---|
| §2 Recent Project | `NavigationUX.md` §⑥ Recent Project（已有规范） + `WorkflowReview.md` §3.1 Project 切换 |
| §3 Back | `NavigationUX.md` §7 Back（已有规范） + `WorkflowReview.md` §2.5-H3 Case 编辑返回 |
| §4 Breadcrumb | `NavigationUX.md` §5 Breadcrumb（已有规范） + `WorkflowReview.md` §3.4 URL Query |
| §5 Quick Action | `NavigationUX.md` §⑨ 点击削减 + `FirstRunGuide.md` §3 Step 5 |
| §6 Recent Runs | `NavigationUX.md` §6 Recent Project + `WorkflowReview.md` §2.7-H2 Run Center |
| §7 Recent Reports | `WorkflowReview.md` §2.8-H1 Report 列表与 Overview 重复（解决） |
| §8 整合 | `PROJECT_WORKSPACE.md` 三大模块 + `FirstRunGuide.md` 6 步引导 |
| §9 URL Query | `NavigationUX.md` 附录 B + `WorkflowReview.md` §3.4 |

---

# 14. 文档约束再确认

- ✅ 不新增任何后端 API（复用 7 类已有 API + LocalStorage）
- ✅ 不新增任何数据库表 / 字段 / 迁移
- ✅ 不新增任何功能模块
- ✅ 所有导航能力通过**前端组件 + 路由 + URL Query + LocalStorage**实现
- ✅ 6 大能力全部复用已有 `RecentProjectsPanel` / `RecentRunsPanel` / `RecentReportsPanel` / `PageHeader` / `ProjectWorkspaceHeader` 组件

---

> **版本**：v1.0 · 2026-07-16
> **作者**：资深产品经理（测试平台方向）
> **范围**：MVP 阶段 Project Workspace 内部导航优化；定时 / CI / 通知 / 协作场景不在本期范围
> **配套使用**：`PRD.md`（产品定位）→ `Journey.md`（用户视角）→ `WorkflowReview.md`（问题视角）→ `FirstRunGuide.md`（引导实施）→ `EmptyState.md`（空态设计）→ `NavigationUX.md`（本文档：导航规范）