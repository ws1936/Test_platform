# API 自动化测试平台 · Quick Action 设计规范

> 文档类型：Quick Action（快速操作）设计规范
> 适用范围：API 自动化测试平台所有页面
> 设计阶段：先设计，不涉及代码实现
> 配套：`PRD.md`、`INFORMATION_ARCHITECTURE.md`、`PROJECT_WORKSPACE.md`、`NavigationUX.md`、`Journey.md`、`WorkflowReview.md`、`FirstRunGuide.md`、`EmptyState.md`
> **硬约束：不新增任何 API、不新增任何数据库表、不新增功能模块——仅复用已有 Project / Environment / Suite / Case / Run / Report / OpenAPI 7 类 API + 已有组件 + 前端路由 / URL Query / LocalStorage**

---

## 0. 设计目标

让用户**用最少的点击**完成高频任务。**核心指标**：主流程点击数从 ~18 降至 ≤ 10。

**三大原则**：

1. **1 次点击直达**：每个 Quick Action **1 次点击打开目标 Drawer / 跳转目标页面**，不允许"先点按钮 → 再选弹窗 → 再确认"的多步操作。
2. **智能默认值**：所有需要参数的 Quick Action 全部**预填最佳值**（默认环境 / 默认 Suite / 上次 scope），用户**直接 Run Now** 即可。
3. **上下文感知**：Quick Action 根据当前用户状态（Project 数 / Suite 数 / 上次 Run / LocalStorage Recent）**自动调整显示**，而非固定展示。

---

## 1. Quick Action 全景图

### 1.1 按出现位置分类

| 位置 | 数量 | 典型动作 |
|---|:-:|---|
| **Dashboard** | 5 个 | 创建 Project / 浏览 Project / 打开 Recent Project / 查看 Recent Report / 切换到上次 Project |
| **Workspace Header** | 4 个 | 快速执行 / 切换环境 / 最近 Run / 刷新 |
| **Suite 详情 PageHeader** | 4 个 | 执行 Suite / OpenAPI 导入 / 编辑 Suite / 删除 Suite |
| **Case 编辑器 PageHeader** | 3 个 | 保存 / 保存并执行 / 执行 Case |
| **Run 详情 PageHeader** | 2 个 | 再次执行 / 修复第一条失败 |
| **Report 列表 PageHeader** | 2 个 | 快速执行 / 复制 Project ID |
| **Context Panel（右侧栏）** | 3 个 | 快速创建 / 最近执行 / 资产完整度 |

### 1.2 点击次数削减目标

| 场景 | 当前 | 目标 | 节省 |
|---|---:|---:|:-:|
| Dashboard → 创建 Project | 3 | **1** | -67% |
| Dashboard → 进入最近 Project | 3 | **1** | -67% |
| Dashboard → 查看最近 Report | 4 | **2** | -50% |
| Suite 详情 → 执行 Suite | 2 | **1** | -50% |
| Case 编辑器 → 执行 Case | 3 | **1** | -67% |
| Run 详情 → 再次执行 | 4 | **1** | -75% |
| Run 详情 → 修复第一条失败 | 5 | **2** | -60% |
| **主流程总点击数** | **~18** | **≤ 10** | **-44%** |

---

# 2. Dashboard Quick Actions（用户首要入口）

> Dashboard 是用户登录后的第一站，Quick Actions 必须**基于用户当前状态**动态显示。

## 2.1 Quick Action 列表

| # | Quick Action | 显示条件 | 1 次点击行为 | 数据源 / API |
|:-:|---|---|---|---|
| **QA-D1** | **📁 创建 Project** | 永远显示（主操作） | 打开 `ProjectFormModal` | 无 |
| **QA-D2** | **📋 浏览 Project 列表** | 永远显示 | 跳转 `/projects` | 无 |
| **QA-D3** | **▶️ 进入最近 Project** | LocalStorage `app.recentProjects.length > 0` | 跳该 Project 概览 | LocalStorage |
| **QA-D4** | **📊 查看最近 Report** | 至少 1 个 Project 有 Run | 跳转最近 Report 详情 | `runs/summary.recent_runs[0]` |
| **QA-D5** | **🔄 重新执行最后一次 Run** | 至少 1 个 Project 有 Run | 打开 Drawer，预填上次 scope / env | `runs?limit=1` |

## 2.2 Dashboard Quick Action Bar（顶部固定区）

```text
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  👋 你好，张三 · 今天有 3 个 Project 待处理                          │
│                                                                       │
│  [+📁 创建 Project]  [📋 浏览列表]  [▶️ 上次 Project]  [📊 最近 Report]│
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**按钮显示规则**：

| 状态 | QA-D1 | QA-D2 | QA-D3 | QA-D4 | QA-D5 |
|---|:-:|:-:|:-:|:-:|:-:|
| 0 Project | ✅ 主操作 | ✅ | ❌ | ❌ | ❌ |
| ≥1 Project 无 Recent | ✅ | ✅ | ❌ | ✅ | ❌ |
| ≥1 Project 有 Recent + 有 Run | ✅ | ✅ | ✅ | ✅ | ✅ |
| ≥1 Project 有 Recent 无 Run | ✅ | ✅ | ✅ | ❌ | ❌ |

## 2.3 Recent Project Quick Cards（中部卡片区）

```text
┌─ Recent Projects ──────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 👤 用户服务  │  │ 👤 订单中心  │  │ 👤 管理后台  │              │
│  │ ✓ 今日回归  │  │ ⚠ 待冒烟    │  │ — 7d 未访问  │              │
│  │ [▶️ Run]    │  │ [▶️ Run]    │  │ [▶️ Run]    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                  [+ 新建]│
└──────────────────────────────────────────────────────────────────────┘
```

**每个卡片 1 个 Quick Action**：

- 卡片**整体可点击** → 进入 Project 概览（默认）
- 卡片右下角 **[▶️ Run] 按钮** → **1 次点击** 打开 `RunExecutionDrawer`，scope 自动 = 该 Project（默认 project，预填默认环境）
- 卡片右上角 **"今日已回归 ✓" 徽标**（基于 `runs/summary.last_run_at`）

**节省**：从 Dashboard "Run 一次" 的 5 次点击（Dashboard → Project 列表 → 选 Project → Project 概览 → Run 模块 → Drawer）降至 **2 次**（Dashboard 卡片 → Drawer）。

## 2.4 Recent Report Quick Cards（中部卡片区）

```text
┌─ Recent Reports ─────────────────────────────────────────────────┐
│  ✓ Run #20260715-1   92.5%  用户服务回归  suite   12.3s    16:42 │
│  ✗ Run #20260715-2   45.0%  订单冒烟     suite    6.1s    16:30 │
│  ✓ Run #20260715-3   98.0%  全量回归    project 18.0s    16:15 │
│                                                                  [+ 查看全部]│
└──────────────────────────────────────────────────────────────────────┘
```

**每行 2 个 Quick Action**：

- 行**整体可点击** → 进入 Run 详情
- 行右侧 **[修复失败]** 按钮（仅 failed / error 时显示）→ 跳 Result 详情 → 失败项 Tab
- 行右侧 **[再次执行]** 按钮 → 1 次点击打开 Drawer，预填原 scope / env

**节省**：从 Dashboard "查看最近 Report" 的 4 次点击（Dashboard → Report 列表 → 选 Run → Run 详情）降至 **1 次**。

## 2.5 实现位置

- 复用 `RecentProjectsPanel.tsx` / `RecentRunsPanel.tsx` / `RecentReportsPanel.tsx`（已存在）
- Dashboard 顶部新增 `DashboardQuickActions.tsx` 组件（纯 UI 组件）
- 按钮点击行为通过已有 Drawer / 路由实现，0 新增 API

---

# 3. Workspace Header Quick Actions（Project 内最高频入口）

> Workspace Header 在 Project 所有页面顶部常驻，是用户操作 Project 的"控制台"。

## 3.1 Quick Action 列表

| # | Quick Action | 1 次点击行为 | 数据源 / API |
|:-:|---|---|---|
| **QA-H1** | **▶️ 快速执行** | 打开 `RunExecutionDrawer`，scope 默认 project | `useProjectWorkspace().enabledCaseCount` |
| **QA-H2** | **🌐 切换环境** | 下拉切换默认环境，立即 `set-default` | `environments` + `set-default` API |
| **QA-H3** | **📋 复制 Project ID** | 复制到剪贴板，Toast 提示 | `project.id` |
| **QA-H4** | **🔄 刷新** | 失效所有 Project 相关 Query | `queryClient.invalidateQueries` |

## 3.2 UI 呈现

```text
┌──────────────────────────────────────────────────────────────────────┐
│  用户服务 API · 👤 张三 · ✓ 资产齐全                                  │
│                                                                       │
│  [▶️ 快速执行]  [🌐 测试环境 ▾]  [📋 复制 ID]  [🔄]               │
│                                                                       │
│  最近：✓ 用户服务回归 92.5% (16:42)  ✗ 订单冒烟 45.0% (16:30)      │
└──────────────────────────────────────────────────────────────────────┘
```

## 3.3 "▶️ 快速执行" 智能判定

根据 Project 状态，Quick Action 自动调整文案 / 行为：

| Project 状态 | 按钮文案 | 1 次点击行为 |
|---|---|---|
| **0 启用 Case** | ▶️ 快速执行（disabled） | Tooltip 提示"暂无可执行 Case" |
| **0 默认环境** | ⚠️ 设置默认环境 | 跳转 Environment 模块 |
| **正常** | ▶️ 快速执行（Project） | 打开 Drawer，scope=project，预填默认环境 |
| **运行中** | ▶️ 快速执行（disabled） | Tooltip 提示"上次 Run 进行中"（前端记录开始时间） |

## 3.4 "🌐 切换环境" 下拉

```text
[🌐 测试环境 ▾]
   ├─ ✓ 测试环境     (默认)
   ├─   预发环境
   ├─   开发环境
   ├─ ─────────────
   └─ ⚙️ 管理环境...
```

**行为**：
- 点击环境名 → 立即调 `POST .../set-default` + 失效 Header / ContextPanel 数据
- 点击"管理环境" → 跳转 Environment 模块
- 当前环境有 **✓** 标识

## 3.5 与 FirstRunGuide 联动

- 处于引导状态时，Header Quick Action 仍可用，但**按钮文案后追加 🎯**（如 `▶️ 快速执行 🎯`）
- 引导 Step 2 时，"创建环境"按钮**自动 Pulse 红点动效**（3 秒）

## 3.6 实现位置

`ProjectWorkspaceHeader.tsx` 增加 `quickActions: QuickAction[]` 配置 + `useProjectWorkspace()` 提供 enabledCaseCount / defaultEnvironmentId。

---

# 4. Suite 详情 Quick Actions

> Suite 详情是"组织用例 + 执行"的关键页面。

## 4.1 Quick Action 列表

| # | Quick Action | 1 次点击行为 | 数据源 / API |
|:-:|---|---|---|
| **QA-S1** | **▶️ 执行 Suite** | 打开 `RunExecutionDrawer`，scope=suite+suiteId | `runs?suiteId=...` |
| **QA-S2** | **📥 OpenAPI 导入** | 跳转 `/workspace/import/:suiteId` | 已有路由 |
| **QA-S3** | **➕ 新建 Case** | 跳 Case Editor，`?suiteId=` 自动带入 | 已有路由 |
| **QA-S4** | **🔍 批量添加 Case** | 打开 `SuiteAddCasesModal` | 已有 Modal |

## 4.2 UI 呈现（PageHeader）

```text
┌──────────────────────────────────────────────────────────────────────┐
│  [← 返回 Suite 列表]                                                  │
│  Breadcrumb: 用户服务 API / 测试套件 / 冒烟回归                       │
│                                                                       │
│  [▶️ 执行 Suite]  [📥 OpenAPI 导入]  [➕ 新建 Case]  [⚙️]            │
└──────────────────────────────────────────────────────────────────────┘
```

**主操作 = ▶️ 执行 Suite**（最高频）

## 4.3 "▶️ 执行 Suite" 智能判定

| Suite 状态 | 按钮状态 | 1 次点击行为 |
|---|---|---|
| **0 Case** | disabled + Tooltip "请先添加 Case" | 无 |
| **全部 Case 被禁用** | disabled + Tooltip "请先启用至少 1 个 Case" | 无 |
| **Project 无默认环境** | ⚠️ 设置默认环境 | 跳转 Environment 模块 |
| **正常** | ▶️ 执行 Suite | 打开 Drawer，scope=collection+suiteId，预填默认环境 |

## 4.4 实现位置

`WorkspaceSuiteDetail.tsx` PageHeader 主操作按钮（已有结构），调整 Drawer 触发逻辑。

---

# 5. Case 编辑器 Quick Actions

> Case 编辑器是配置单个 API 测试用例的核心页面。

## 5.1 Quick Action 列表

| # | Quick Action | 1 次点击行为 | 数据源 / API |
|:-:|---|---|---|
| **QA-C1** | **💾 保存** | `PUT /test-cases/:id`，Toast 提示 | 已有 API |
| **QA-C2** | **💾 保存并执行** | 先保存，再打开 Drawer 预填 scope=case | 已有 API + Drawer |
| **QA-C3** | **▶️ 执行 Case**（未保存修改时禁用） | 打开 Drawer，scope=case+caseId | 已有 Drawer |

## 5.2 UI 呈现（PageHeader）

```text
┌──────────────────────────────────────────────────────────────────────┐
│  [← 返回 Suite 详情]    来自：冒烟回归 Suite                          │
│  Breadcrumb: 用户服务 API / API 用例 / 获取用户详情                   │
│                                                                       │
│  [💾 保存]  [💾 保存并执行]  [▶️ 执行 Case]                          │
└──────────────────────────────────────────────────────────────────────┘
```

**主操作优先级**：`💾 保存并执行` > `💾 保存`（用户高频需求"调通即跑"）

## 5.3 "💾 保存并执行" 流程

```text
[用户点击 保存并执行]
   ↓
[1. PUT /test-cases/:id]（保存当前修改）
   ↓
[2. 打开 RunExecutionDrawer]
   ├─ source = { kind: 'case', caseItem: {...} }
   ├─ scope = 'case'
   ├─ scope_id = case.id
   ├─ environment_id = defaultEnvironmentId
   └─ run name = "Case 调通测试 - [时间戳]"
   ↓
[3. 用户可选改环境 / 改 Run Name]
   ↓
[4. 点击 "Run Now"]
   ↓
[5. POST /runs/runCase]
   ↓
[6. 同步执行完成 → 自动跳 /workspace/report/:runId]
```

**节省**：原来 5 步（保存 → 关闭 → 回到 Suite → 点执行 → Drawer）降至 **2 步**（保存并执行 → Run Now）。

## 5.4 智能判定

| Case 状态 | 💾 保存 | 💾 保存并执行 | ▶️ 执行 Case |
|---|:-:|:-:|:-:|
| **未修改**（无 dirty） | disabled | enabled | enabled |
| **已修改**（dirty） | enabled | enabled | disabled（提示"请先保存"） |
| **Case disabled** | enabled | disabled + Tooltip "Case 已禁用" | disabled + Tooltip |
| **无默认环境** | enabled | ⚠️ 提示"将跳转设置环境" | ⚠️ 提示 |

## 5.5 实现位置

`WorkspaceCaseEditor.tsx` PageHeader 增加"保存并执行"按钮（已有"保存"按钮旁）。

---

# 6. Run 详情 Quick Actions

> Run 详情是用户查看测试结果的核心页面，也是"修复再跑"的起点。

## 6.1 Quick Action 列表

| # | Quick Action | 1 次点击行为 | 数据源 / API |
|:-:|---|---|---|
| **QA-R1** | **▶️ 再次执行** | 打开 Drawer，预填原 scope / env | `runs?limit=1` |
| **QA-R2** | **🔧 修复第一条失败** | 跳 Result 详情 → 失败项 Tab → 跳 Case 编辑器 | `run.failures[0].resultId` |

## 6.2 UI 呈现

```text
┌──────────────────────────────────────────────────────────────────────┐
│  [← 返回 Report 列表]                                                │
│  Breadcrumb: 用户服务 API / 测试报告 / Run #20260715                  │
│                                                                       │
│  ✓ finished · 92.5% · 12 Case · 12.3s · 测试环境                     │
│                                                                       │
│  [▶️ 再次执行]  [🔧 修复 3 条失败]                                  │
└──────────────────────────────────────────────────────────────────────┘
```

## 6.3 "▶️ 再次执行" 智能预填

| 上次 Run scope | Drawer 预填 |
|---|---|
| `project` | scope=project, env=defaultEnv |
| `collection` | scope=collection, scopeId=suiteId, env=defaultEnv |
| `case` | scope=case, scopeId=caseId, env=defaultEnv |

**1 次点击**：Drawer 直接打开，全部预填，用户**直接 Run Now**。

**节省**：原来 4 步（返回 Report 列表 → 去 Run 模块 → 选 scope → Drawer）降至 **2 步**（再次执行 → Run Now）。

## 6.4 "🔧 修复第一条失败" 流程

```text
[用户点击 修复第一条失败]
   ↓
[1. 读取 run.failures[0]]
   ↓
[2. 跳 /workspace/report/:runId/result/:resultId]
   ↓
[3. Result 详情顶部按钮 "修改并再执行" 1 步完成]
   ↓
[4. 跳 /workspace/case/:caseId?from=report&runId=&resultId=]
   ↓
[5. Case 编辑器 + 失败断言定位]
   ↓
[6. 保存 → "保存并执行" → Drawer → 新 Run 报告]
```

**节省**：原来 6 步（Run 详情 → 失败 Tab → 选失败项 → Result 详情 → 跳 Case → 编辑）降至 **2 步**（修复按钮 → 修改并再执行）。

## 6.5 智能判定

| Run 状态 | ▶️ 再次执行 | 🔧 修复第一条失败 |
|---|:-:|:-:|
| **全部通过** | ✅ | ❌（隐藏） |
| **有 failed/error** | ✅ | ✅（显示数字徽标"修复 3 条"） |
| **Run 进行中** | disabled | ❌ |

## 6.6 实现位置

`WorkspaceReportDetail.tsx` PageHeader 增加"再次执行"和"修复第一条失败"按钮（已有结构）。

---

# 7. 其他页面的 Quick Action 速查

## 7.1 Environment 模块

| # | Quick Action | 1 次点击行为 |
|:-:|---|---|
| QA-E1 | 🌐 新建环境 | 打开 `EnvironmentFormModal`，is_default 默认勾选 |
| QA-E2 | 📋 复制 Base URL | 行右侧图标按钮，复制到剪贴板 |

## 7.2 Suite 列表

| # | Quick Action | 1 次点击行为 |
|:-:|---|---|
| QA-SL1 | 📦 新建 Suite | 打开 `SuiteFormModal` |
| QA-SL2 | ▶️ 执行 Suite（行内） | 1 次点击打开 Drawer，预填 scope=collection+suiteId |

## 7.3 Case 列表

| # | Quick Action | 1 次点击行为 |
|:-:|---|---|
| QA-CL1 | ➕ 新建 Case | 跳 Case Editor，先选 Suite |
| QA-CL2 | ▶️ 执行 Case（行内） | 1 次点击打开 Drawer，预填 scope=case+caseId |
| QA-CL3 | 📋 复制 Case Path | 行右侧图标按钮，复制到剪贴板 |

## 7.4 Report 列表

| # | Quick Action | 1 次点击行为 |
|:-:|---|---|
| QA-RL1 | ▶️ 快速执行 | 打开 Drawer，scope=project |
| QA-RL2 | 🔍 失败优先筛选 | 一键 Tab 切到"仅失败" |

## 7.5 Project 列表

| # | Quick Action | 1 次点击行为 |
|:-:|---|---|
| QA-PL1 | 📁 新建 Project | 打开 `ProjectFormModal` |

## 7.6 Context Panel（右侧栏）

| # | Quick Action | 1 次点击行为 |
|:-:|---|---|
| QA-CP1 | 🌐 跳到默认环境详情 | 跳转 Environment 模块 |
| QA-CP2 | ▶️ 跳到最近 Run | 跳转 Run 详情 |
| QA-CP3 | ➕ 快速创建环境/Suite/Case | 直接打开对应 Drawer |

---

# 8. Quick Action 数据流

## 8.1 通用数据结构

```typescript
interface QuickAction {
  id: string;                      // 唯一标识
  label: string;                   // 按钮文案
  icon: React.ReactNode;           // 图标
  variant: 'primary' | 'default' | 'link' | 'text';  // 按钮样式
  disabled?: boolean;              // 是否禁用
  disabledReason?: string;         // 禁用原因（Tooltip）
  preCondition?: () => boolean;    // 显示条件
  onClick: () => void;             // 点击行为（1 次点击直达）
  shortcut?: string;               // 可选：快捷键
  badge?: number | string;         // 可选：徽标（数字 / 文字）
}
```

## 8.2 Quick Action 渲染流程

```text
[页面挂载 / 状态变化]
   ↓
[读取当前页面上下文] → useProjectWorkspace() / useUrlQueryState() / LocalStorage
   ↓
[计算 QuickAction[] 列表]
   ├─ 过滤：preCondition() === false 的不显示
   ├─ 排序：variant=primary 排最前
   └─ 注入 disabled / badge / tooltip
   ↓
[渲染到 PageHeader / Header / Panel]
   ↓
[用户点击] → onClick() → 打开 Drawer / 跳转 / 触发 mutation
```

## 8.3 智能判定中心：`useQuickActions` Hook

**位置**：`frontend/src/hooks/useQuickActions.ts`（纯前端，0 新增 API）

**职责**：
- 接受当前页面上下文（projectId / suiteId / caseId / runId）
- 返回该页面的 `QuickAction[]` 列表
- 每个 Action 自带 preCondition / onClick / disabledReason

---

# 9. Quick Action 与现有组件的复用清单

| Quick Action | 复用已有组件 / API |
|---|---|
| 📁 创建 Project | `ProjectFormModal` + `POST /projects` |
| 🌐 创建环境 | `EnvironmentFormModal` + `POST /environments` |
| 📦 创建 Suite | `SuiteFormModal` + `POST /suites` |
| ➕ 新建 Case | 跳 Case Editor + `POST /test-cases` |
| 📥 OpenAPI 导入 | 跳 Import 页 + `POST /openapi/import` |
| ▶️ 快速执行 / 执行 Suite / 执行 Case | `RunExecutionDrawer` + `POST /runs` |
| ▶️ 再次执行 | `RunExecutionDrawer`（预填 scope）+ `POST /runs` |
| 🔧 修复失败 | 跳 Case Editor（带 from=report）+ `PUT /test-cases` |
| 🔄 切换环境 | `POST .../set-default` |
| 📋 复制 ID / URL / Path | `navigator.clipboard.writeText`（浏览器 API） |
| 🔄 刷新 | `queryClient.invalidateQueries` |

**全部 Quick Action 通过已有 API + 已有组件实现，0 新增 API，0 新增 DB，0 新增功能模块。**

---

# 10. 验收指标

| 指标 | 计算方式 | 当前 | 目标 |
|---|---|---|---|
| **主流程平均点击数** | 4 条 Journey 总点击数 / 4 | ~18 | **≤ 10** |
| **Dashboard → 执行最近 Project 的 Run** | 点击数 | 5 | **2** |
| **Suite 详情 → 执行 Suite** | 点击数 | 2 | **1** |
| **Case 编辑器 → 保存并执行** | 点击数 | 5 | **2** |
| **Run 详情 → 修复第一条失败** | 点击数 | 6 | **2** |
| **Quick Action 命中率** | 用户实际点击 Quick Action 占所有操作的比例 | 低 | **≥ 60%** |
| **Quick Action 启用率** | Dashboard Quick Action 中 ≥ 1 个被点击的比例 | — | **≥ 80%** |
| **从 Dashboard 到 Run 报告的平均点击** | — | 4 | **≤ 2** |

---

# 11. 实施优先级

| # | 任务 | 优先级 | 估时 | 价值 |
|---:|---|:-:|:-:|:-:|
| 1 | Dashboard Quick Action Bar（QA-D1~D5） | P0 | 1 天 | 高 |
| 2 | Recent Project 卡片 [▶️ Run] 按钮 | P0 | 0.5 天 | 高 |
| 3 | Recent Report 行 [再次执行] / [修复失败] 按钮 | P0 | 0.5 天 | 高 |
| 4 | Workspace Header Quick Actions（QA-H1~H4） | P0 | 1 天 | 高 |
| 5 | Suite 详情 [▶️ 执行 Suite] 直开 Drawer | P0 | 0.5 天 | 高 |
| 6 | Case 编辑器 [💾 保存并执行] | P0 | 0.5 天 | 高 |
| 7 | Run 详情 [▶️ 再次执行] / [🔧 修复失败] | P0 | 1 天 | 高 |
| 8 | `useQuickActions` Hook | P0 | 1 天 | 高 |
| 9 | Suite 列表行内 [▶️ 执行 Suite] | P1 | 0.5 天 | 中 |
| 10 | Case 列表行内 [▶️ 执行 Case] | P1 | 0.5 天 | 中 |
| 11 | Environment 列表行内 [📋 复制 Base URL] | P1 | 0.5 天 | 中 |
| 12 | Context Panel Quick Actions 整合 | P1 | 1 天 | 中 |
| 13 | Quick Action 智能判定（disabled 提示 / 失败徽标） | P1 | 0.5 天 | 中 |
| 14 | Quick Action 与 FirstRunGuide 联动 | P2 | 0.5 天 | 中 |

---

# 12. 不在范围（防止范围蔓延）

- ❌ 全局快捷键（依赖前端事件监听，本期不实现）
- ❌ Quick Action 自定义配置（用户无法自定义按钮）
- ❌ Quick Action AI 推荐（依赖 ML）
- ❌ Quick Action 拖拽排序（保持固定顺序）
- ❌ 浮动 Quick Action 工具栏（悬浮按钮）
- ❌ Quick Action 使用统计埋点（除非后端提供接口）

---

# 13. 文档约束再确认

- ✅ 不新增任何后端 API
- ✅ 不新增任何数据库表 / 字段 / 迁移
- ✅ 不新增任何功能模块
- ✅ 所有 Quick Action 通过**已有 Drawer / 路由 / API / 前端 Hook**实现
- ✅ 智能判定全部基于前端已有数据（React Query / LocalStorage / URL Query）

---

> **版本**：v1.0 · 2026-07-16
> **作者**：资深产品经理（测试平台方向）
> **范围**：MVP 阶段所有页面 Quick Action；定时 / 通知 / AI 推荐场景不在本期范围
> **配套使用**：`PRD.md`（产品定位）→ `Journey.md`（用户视角）→ `WorkflowReview.md`（问题视角）→ `FirstRunGuide.md`（引导实施）→ `EmptyState.md`（空态设计）→ `NavigationUX.md`（导航规范）→ `QuickAction.md`（本文档：快速操作）