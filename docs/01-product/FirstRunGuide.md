# API 自动化测试平台 · 首次使用引导（First Run Guide）

> 文档类型：首次使用引导（First Run Guide）产品方案
> 适用范围：新建账号 / 平台零资产的测试工程师
> 设计阶段：先设计，不涉及代码实现
> 配套：`PRD.md`、`INFORMATION_ARCHITECTURE.md`、`PROJECT_WORKSPACE.md`、`NavigationUX.md`、`Journey.md`、`WorkflowReview.md`
> **硬约束：不新增任何业务能力、不新增任何 API、不新增任何数据库表——仅复用已有 Project / Environment / Suite / OpenAPI / Run / Report 6 类 API + 已有 Drawer / 组件 / 前端路由 / URL Query / LocalStorage**

---

## 0. 设计目标

让**第一次使用平台的测试工程师**，在 **0 菜单导航**、**0 自我探索** 的前提下，**自动被引导**完成 `创建 Project → 创建 Environment → Import OpenAPI → 创建 Suite → Run → 查看 Report` 全流程 6 步，最终**看到第一条 Run 报告**。

**核心原则**：

1. **页面不替身**：不新增"引导页 / Wizard 页"，不打断 Workspace 既有结构；引导叠加在 Workspace 既有 UI 上。
2. **下一步永远自动出现**：完成当前步骤后，系统**自动判断**下一步该做什么，**自动打开 Drawer / 跳转页面 / 弹出下一步卡片**，用户不必去 Sider 找模块。
3. **可退出 / 可重入**：用户可随时关闭引导；关闭后任何步骤缺失会再次提示"继续引导"。
4. **零新功能**：所有动作（建 Project / 建 Environment / Import / 建 Suite / Run / 看 Report）调用**已存在 API**，引导仅控制时序与默认参数。

---

## 1. 引导触发与状态判定

### 1.1 触发条件（任一即触发）

| 触发点 | 判定逻辑 | 数据来源 |
|---|---|---|
| 用户登录成功 | LocalStorage `app.firstRun` 不存在 | LocalStorage |
| 进入 Dashboard | 用户的 Project 列表总数 === 0 | `GET /projects?limit=1`（已有） |
| 进入 Workspace Overview | 当前 Project 资产（Environment + Suite + Case）全部为 0 | `runs/summary` + `environments` + `suites` + `cases`（已有） |

### 1.2 引导状态机

```text
[未触发 idle]
   │ 登录 / 进入 0 资产 Workspace
   ▼
[已触发，引导启动 active]
   │ Step 1 (Project) → Step 2 (Environment) → Step 3 (Import) → Step 4 (Suite) → Step 5 (Run) → Step 6 (Report)
   │
   ├─ [用户主动关闭] → [最小化 minimized]
   │     │ 检测到资产缺失 / 点击"继续引导" → 回到 active
   │
   └─ [全部 6 步完成] → [已完成 completed]
         │ 写入 LocalStorage `app.firstRun.completed = true`
         │ Dashboard 显示"首次跑通"庆祝条
```

### 1.3 引导状态持久化

| Key | 类型 | 含义 |
|---|---|---|
| `app.firstRun.completed` | boolean | 用户是否完成过首次引导 |
| `app.firstRun.currentStep` | number（1~6） | 当前进行到第几步 |
| `app.firstRun.projectId` | string | 引导创建的 Project ID（用于恢复上下文） |
| `app.firstRun.environmentId` | string | 默认环境 ID |
| `app.firstRun.suiteId` | string | Step 3 自动创建的 Suite ID |
| `app.firstRun.dismissedAt` | ISO 时间 | 最近一次关闭时间，用于 24h 内不再自动弹出 |

**全部使用 LocalStorage，不修改任何后端字段。**

---

## 2. 引导 UI 形态

### 2.1 三种 UI 元素（同时存在，按场景切换）

#### A. 引导横幅（Top Banner）

位置：Workspace Header 下方 / PageHeader 上方。

```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎯 首次使用引导    Step 3 / 6 · 导入 OpenAPI    [跳过] [关闭引导]  │
└──────────────────────────────────────────────────────────────────────┘
```

行为：

- 始终可见（步骤进行中）
- 显示当前 Step 编号 + 标题 + 主操作按钮
- "跳过"跳到下一步但不执行当前步（仅用于高级用户）
- "关闭引导" 写入 `dismissedAt`，切换为**最小化态**

#### B. 引导卡片（Context Card）

位置：每个 Workspace 模块页内容区**顶部**（叠加在 Overview / Environment / Suite / Case / Run / Report 模块内）。

```text
┌──────────────────────────────────────────────────────────────────────┐
│  ⏵ 首次使用引导 · 第 3 步（共 6 步）                              │
│  目标：导入 OpenAPI 文档，自动生成 API 用例                        │
│  系统已为你创建 Suite「API 导入」，下面开始导入 ↓                  │
│  [导入 OpenAPI] [查看已创建 Suite]                                  │
└──────────────────────────────────────────────────────────────────────┘
```

行为：

- 提供当前步骤的**主操作按钮**（点击直接打开对应 Drawer 或跳转对应模块）
- 提供"上一步 / 下一步"（仅在状态机允许时启用）
- 完成后**自动切换**到下一步卡片（不刷新页面）

#### C. Drawer / 模态预填

位置：所有引导触发的 Drawer（Project / Environment / Suite / Import）**自动打开**。

行为：

- Drawer 打开时标题旁显示"🎯 引导第 X 步"
- Drawer 表单**预填最佳默认值**：例如 Environment Drawer 自动勾选"设为默认"
- Drawer 保存成功后**自动关闭 + 自动进入下一步**（不弹"已保存 Toast"后等用户操作）

### 2.2 引导元素出现规则

| 当前步骤 | Banner | Context Card | Drawer / Page |
|---:|:-:|:-:|---|
| **Step 1 · Project** | 显示 | 显示 | 自动打开 **ProjectFormModal** |
| **Step 2 · Environment** | 显示 | 显示（Workspace Overview） | 自动跳 Environment 模块 + 打开 **EnvironmentFormModal** |
| **Step 3 · Import OpenAPI** | 显示 | 显示（Suite 详情） | 自动跳 Suite 详情 + 打开 **Import Drawer** |
| **Step 4 · Suite** | 显示 | 显示（Suite 列表） | 自动打开 **SuiteFormModal** |
| **Step 5 · Run** | 显示 | 显示（Run 模块） | 自动打开 **RunExecutionDrawer** |
| **Step 6 · Report** | 显示 | 隐藏 | 自动跳 Run 报告详情 |

---

## 3. 逐步设计（6 步）

> 每步给出：**用户目标 / 当前页面 / 系统自动行为 / 用户操作 / 完成判定 / 兜底路径**。

---

## Step 1 · 创建 Project

### 用户目标

"我要为我的服务建一个测试 Project。"

### 当前页面

`/login` → `/dashboard`（刚登录，无 Project）

### 系统自动行为

1. 登录成功后检测 `app.firstRun.completed !== true` + `GET /projects?limit=1` 返回 0 条 → 触发引导。
2. 跳转 `/dashboard`（不直跳 Project 列表，便于用户在 Dashboard 看到引导卡）。
3. Dashboard 中央显示**引导卡片 A**（取代原本的"推荐工作路径"教学卡）：

```text
┌──────────────────────────────────────────────────────────────────────┐
│  👋 欢迎使用 API 自动化测试平台                                      │
│  下面 6 步带您跑通第一条测试用例                                      │
│  Step 1 / 6：创建你的第一个 Project                                  │
│  [📁 创建 Project]                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

4. 点击按钮 → **自动打开 ProjectFormModal**（已有）：

- 标题旁显示"🎯 引导第 1 步"
- "名称"输入框聚焦
- 描述字段默认收起 + 占位文案
- `owner` 字段隐藏（自动 = 当前用户）
- "创建并继续"为主按钮

### 用户操作

1. 输入 Project 名称（如"用户服务 API"）
2. 点击"创建并继续"

### 系统后续行为

1. `POST /projects`（已有）
2. 成功后：
   - 关闭 Drawer
   - **自动跳转** `/projects/:projectId/workspace/overview`
   - **LocalStorage 写入** `app.firstRun.currentStep = 2`、`app.firstRun.projectId = ...`
   - Workspace Overview 顶部**引导卡片 B** 自动出现："第 2 步：创建环境"

### 完成判定

`app.firstRun.projectId` 已设置 + Project 存在。

### 兜底

- 用户中途关闭 Drawer → 引导保持 Step 1，Dashboard 引导卡仍显示"创建 Project"。
- 用户跳过 Step 1（手动在 Sider 创建） → 检测到 Project 数量 ≥ 1，自动跳 Step 2。

---

## Step 2 · 创建 Environment

### 用户目标

"我要配置这个 Project 的测试环境地址。"

### 当前页面

`/projects/:projectId/workspace/overview`

### 系统自动行为

1. Workspace Overview 加载时检测：
   - `app.firstRun.projectId === :projectId` 且 `currentStep === 2`
   - Project `environments` 列表为空（`GET /projects/:projectId/environments` 返回 0 条）
   → 触发引导。
2. Overview 顶部显示**引导卡片 B**：

```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎯 Step 2 / 6 · 创建环境                                           │
│  下一步：填写 Base URL / Headers / Variables                          │
│  [🌐 创建环境]                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

3. Workspace Header **"创建环境"按钮自动高亮**（红点 / Pulse 动效，3 秒）。
4. 点击按钮 → **自动打开 EnvironmentFormModal**（已有）：

- 标题旁显示"🎯 引导第 2 步"
- "Base URL"输入框聚焦
- "设为默认环境" **Switch 默认开启**（最佳实践）
- 提示文字"第一个环境将自动成为默认环境"
- "Headers / Variables" **键值表模式**（已有 JSON 模式 + 表模式切换）
- 主按钮文案"保存并继续 →"

### 用户操作

1. 输入名称（如"测试环境"）
2. 输入 Base URL（如`https://api.test.example.com`）
3. （可选）点击 Headers / Variables 添加键值
4. 点击"保存并继续 →"

### 系统后续行为

1. `POST /projects/:projectId/environments`（已有）
2. 成功后：
   - 关闭 Drawer
   - 自动调用 `set-default` 接口（已有，因 is_default=true）
   - **不跳转页面**，仍在 Workspace Overview
   - **Overview 顶部引导卡片切换为 Step 3**："导入 OpenAPI"
   - **LocalStorage 写入** `currentStep = 3`、`environmentId = ...`

### 完成判定

Project 至少 1 个环境，且 defaultEnvironmentId 已设置。

### 兜底

- 用户关 Drawer 后未保存 → 检测到 Environment 数仍为 0，引导卡显示"创建环境"再次出现。
- 用户跳过（手动建环境） → 检测到 defaultEnvironmentId 存在，自动跳 Step 3。

---

## Step 3 · Import OpenAPI

### 用户目标

"我把 OpenAPI 文档导入，自动生成 API 用例。"

### 当前页面

`/projects/:projectId/workspace/overview`

### 系统自动行为

1. 检测 `currentStep === 3` 且 Project 无 Suite / Case。
2. **系统自动创建一个名为"导入的用例"的 Suite**（作为 Import 目标），避免 Import 无家可归：

- 调用 `POST /projects/:projectId/suites` body `{name: "导入的用例", description: "首次引导自动创建"}`（已有 API）
- 写入 `app.firstRun.suiteId = ...`

> **说明**：用户原 6 步顺序是"Import → Suite"，但 Import URL 必须带 suiteId。本设计在 Step 3 自动创建一个空 Suite 作为容器；用户可在 Step 4 自行新建更多业务 Suite。这是对用户流程的最小调整，不新增任何 API。

3. Overview 顶部引导卡片切换为 Step 3：

```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎯 Step 3 / 6 · 导入 OpenAPI                                        │
│  系统已为你创建 Suite「导入的用例」，下面开始导入 ↓                  │
│  [📥 导入 OpenAPI] [查看 Suite]                                      │
└──────────────────────────────────────────────────────────────────────┘
```

4. 点击"导入 OpenAPI"按钮 → **自动跳转到** `/projects/:projectId/workspace/import/:suiteId`（已有路由）。
5. Import 页面顶部显示引导横幅：

```text
🎯 Step 3 / 6 · 导入 OpenAPI（目标 Suite：导入的用例）
```

6. Import Drawer / 页面默认值（已有 + 引导增强）：

- **冲突策略默认 skip**（避免误覆盖）
- 名称前缀默认空
- 标签过滤默认"全部"
- "导入并继续 →" 为主按钮

### 用户操作

1. 选择来源（URL 或粘贴 JSON）
2. （可选）点击"预览"查看
3. 点击"导入并继续 →"

### 系统后续行为

1. 调用 OpenAPI Import 接口（已有 `POST /projects/:projectId/openapi/import`）
2. 成功后：
   - 展示导入摘要（created / skipped / overwritten / errors，已有）
   - **自动跳转** `/projects/:projectId/workspace/suite/:suiteId`（Suite 详情）
   - **LocalStorage 写入** `currentStep = 4`
   - Suite 详情顶部显示引导卡片 Step 4

### 完成判定

Suite 内 Case 数 ≥ 1。

### 兜底

- 用户关 Import 页未导入 → 检测到目标 Suite 仍为空，引导卡显示"导入 OpenAPI"再次出现。
- 用户跳过（手动建 Case） → 检测到 Case 数 ≥ 1，自动跳 Step 4。

---

## Step 4 · 创建 Suite（可选）

### 用户目标

"我创建更多业务 Suite（如冒烟 / 回归）来组织用例。"

### 当前页面

`/projects/:projectId/workspace/suite/:suiteId`（Step 3 导入完成后的页面）

### 系统自动行为

1. 检测 `currentStep === 4` 且 Step 3 已完成。
2. 顶部引导卡片显示 Step 4：

```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎯 Step 4 / 6 · 创建更多 Suite（可选）                              │
│  你已完成导入。还可以按业务场景创建更多 Suite 来组织用例              │
│  [📦 新建 Suite] [跳过，进入 Run]                                   │
└──────────────────────────────────────────────────────────────────────┐
```

> **说明**：Step 3 已自动创建了"导入的用例"Suite 作为导入容器；Step 4 是**可选的扩展步骤**，用户可继续创建业务 Suite，或直接跳到 Run。本步骤不强求创建。

3. 若用户点击"新建 Suite" → 自动跳 `/projects/:projectId/workspace/suite` + **自动打开 SuiteFormModal**：

- 标题旁显示"🎯 引导第 4 步"
- 名称输入框聚焦
- 描述字段占位文案"如：用户登录冒烟 / 订单核心回归"
- "创建并继续 →" 为主按钮
- 提供"再建一个"副按钮（保存后留在 Drawer）

4. 用户点击"跳过" → 直接进入 Step 5。

### 用户操作

**路径 A**（创建 Suite）：

1. 输入 Suite 名称
2. 点击"创建并继续 →"

**路径 B**（跳过）：

1. 点击"跳过，进入 Run"

### 系统后续行为

**路径 A**：

1. `POST /projects/:projectId/suites`（已有）
2. 成功后关闭 Drawer，**回到 Suite 列表**，引导卡片仍显示 Step 4（可再建或跳到 Run）。

**路径 B / 或路径 A 完成后点击"进入 Run"**：

1. **LocalStorage 写入** `currentStep = 5`
2. **自动跳转** `/projects/:projectId/workspace/run?scope=collection&scopeId=...`
3. **自动打开 RunExecutionDrawer**（已有组件，scope=collection 锁定为 Step 3 创建的 Suite）

### 完成判定

用户点击"跳过"或已新建 ≥ 1 个 Suite。

### 兜底

- 用户在 Suite 列表手动操作 → 引导卡仍显示"进入 Run"，点击进入 Step 5。

---

## Step 5 · Run

### 用户目标

"跑一下这个 Suite，看测试结果。"

### 当前页面

`/projects/:projectId/workspace/run`（自动跳转）

### 系统自动行为

1. 检测 `currentStep === 5`。
2. Run 模块顶部显示引导卡片：

```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎯 Step 5 / 6 · 执行测试                                            │
│  范围：导入的用例（X 条启用）                                         │
│  环境：测试环境（默认）                                               │
│  [▶ Run Now] [改环境]                                                │
└──────────────────────────────────────────────────────────────────────┘
```

3. **自动打开 RunExecutionDrawer**（已有）：

- title 显示"🎯 引导第 5 步"
- scope 锁定为 `collection` + `scopeId = app.firstRun.suiteId`（不可改）
- environment 预填默认环境
- Run Name 自动填"首次引导 Run"
- Variables 自动展示只读（来自环境）
- "Run Now" 为主按钮

### 用户操作

1. （可选）改 Environment
2. 点击"Run Now"

### 系统后续行为

1. `POST /runs` scope=collection（已有）
2. 同步执行完成后：
   - **自动跳转** `/projects/:projectId/workspace/report/:runId?from=firstRun`
   - **LocalStorage 写入** `currentStep = 6`

### 完成判定

Run 报告已生成（`runId` 存在）。

### 兜底

- 用户关 Drawer 未执行 → Run 模块引导卡仍显示"Run Now"。
- 用户手动执行 → 检测到最近 Run 存在，自动跳 Step 6。

---

## Step 6 · 查看 Report

### 用户目标

"我看一下测试结果，是不是都通过了。"

### 当前页面

`/projects/:projectId/workspace/report/:runId?from=firstRun`（自动跳转）

### 系统自动行为

1. 检测 `currentStep === 6` 且 URL 含 `?from=firstRun`。
2. Run 详情顶部显示引导横幅（**最终庆祝条**）：

```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎉 恭喜！你已跑通第一条 API 测试                                    │
│  Step 6 / 6 · 查看 Report                                             │
│                                                                       │
│  通过率：100%（或"还有 N 条失败待修复"）                              │
│                                                                       │
│  下一步建议：                                                          │
│  · 点击"失败项"查看原因                                              │
│  · 返回 Suite 详情查看用例                                            │
│  · 进入 Report 列表看历史                                              │
│  [查看失败原因] [返回 Suite] [完成引导 →]                            │
└──────────────────────────────────────────────────────────────────────┘
```

3. Run 详情默认 Tab 规则：
   - 有 failed/error → **失败原因**（已实现）
   - 全部通过 → **概览**
4. 用户点击"完成引导 →"：

- 写入 `app.firstRun.completed = true`
- Dashboard 跳转后显示"🎉 首次跑通"庆祝条
- 引导横幅消失

### 用户操作

1. 浏览 Run 报告
2. （可选）点击"失败项" → Result 详情 → Case 编辑器
3. 点击"完成引导 →"

### 系统后续行为

1. **LocalStorage 写入** `app.firstRun.completed = true`
2. **清空** `app.firstRun.currentStep / projectId / environmentId / suiteId`（保留 `completed` 标记即可）
3. 跳转 `/dashboard`，显示"🎉 首次跑通"庆祝条 + "查看 Run 详情"按钮

### 完成判定

`app.firstRun.completed === true` + 跳 Dashboard。

### 兜底

- 用户在 Run 详情手动操作 → 点击 PageHeader 的"完成引导"按钮（次操作）即可结束。
- 用户关闭引导卡 → 24h 内不再显示，24h 后再次进入 Workspace Overview 仍显示"完成引导"提示。

---

## 4. 引导控制器设计（前端 Hook）

### 4.1 `useFirstRun` Hook

**位置**：新增 `frontend/src/hooks/useFirstRun.ts`（仅前端，不新增 API）

**职责**：

```typescript
interface FirstRunState {
  active: boolean;          // 是否在引导中
  currentStep: 1 | 2 | 3 | 4 | 5 | 6;
  projectId?: string;
  environmentId?: string;
  suiteId?: string;
  runId?: string;
  dismissedAt?: string;
}

interface FirstRunActions {
  start: () => void;                       // 触发引导（首次登录 / 0 资产）
  advance: () => void;                      // 进入下一步
  back: () => void;                         // 上一步
  skip: () => void;                         // 跳过当前步骤
  dismiss: () => void;                      // 关闭引导（最小化）
  complete: () => void;                     // 完成引导
  reset: () => void;                        // 重置引导（用于演示 / 测试）
}

useFirstRun(): { state, actions, isFirstRunActive }
```

**数据流**：

```text
LocalStorage `app.firstRun`  ⇄  useFirstRun Hook  ⇄  组件（Banner / Card / Drawer 自动行为）
                                  │
                                  └─→ 监听资产状态变化：
                                       · projects 数 === 0 → 自动触发 start
                                       · environments 数 === 0 且 currentStep === 2 → 重新打开 Drawer
                                       · cases 数 ≥ 1 且 currentStep === 3 → 自动 advance
                                       · runs 数 ≥ 1 且 currentStep === 5 → 自动 advance
```

### 4.2 `FirstRunProvider` Provider

**位置**：包裹在 `AppShell` 内、`ProtectedRoute` 外。

**职责**：

- 初始化时读 LocalStorage，注入到 React Context
- 监听路由变化，**根据当前路由判断是否触发引导动作**
- 在 Workspace 各模块挂载时检查资产完整度，自动推进状态机

**不修改任何后端接口**。

---

## 5. 各步汇总表

| Step | 用户目标 | 触发页面 | 系统自动动作 | 用户操作 | 系统跳转 | API 调用（全部已有） |
|:-:|---|---|---|---|---|---|
| **1 Project** | 建第一个 Project | `/dashboard` | 显示引导卡 + 自动打开 ProjectFormModal | 输入名称 → 创建 | 跳 Workspace Overview | `POST /projects` |
| **2 Environment** | 配置测试环境 | `/workspace/overview` | 显示引导卡 + 自动打开 EnvironmentFormModal（is_default=on） | 填 Base URL → 保存 | 不跳页（保留 Overview） | `POST /environments` + `POST .../set-default` |
| **3 Import** | 导入 OpenAPI | `/workspace/overview` | 自动建 Suite "导入的用例" + 跳 Import 页 | 选来源 → 预览 → 导入 | 跳 Suite 详情 | `POST /suites` + `POST /openapi/import` |
| **4 Suite** | 建更多 Suite（可选） | `/workspace/suite/:id` | 显示引导卡 + 打开 SuiteFormModal 或"跳过"按钮 | 填名称 → 保存 / 跳过 | 跳 Run 模块 | `POST /suites` |
| **5 Run** | 跑测试 | `/workspace/run` | 显示引导卡 + 自动打开 RunExecutionDrawer（scope=collection） | 选环境 → Run Now | 跳 Run 详情 | `POST /runs` |
| **6 Report** | 看结果 | `/workspace/report/:runId` | 显示引导横幅 + 跳转 Dashboard 庆祝条 | 浏览 → 完成引导 | 跳 Dashboard | 无（只读） |

---

## 6. 引导与已有组件的复用清单

| 引导需要的元素 | 复用已有组件 | 调用 |
|---|---|---|
| Project 新建 | `ProjectFormModal` | 已有 |
| Environment 新建 | `EnvironmentFormModal` | 已有 |
| Suite 新建（Step 3 自动建） | `SuiteFormModal` | 已有 |
| Suite 新建（Step 4 用户建） | `SuiteFormModal` | 已有 |
| OpenAPI Import | `WorkspaceImport` | 已有 |
| Run 发起 | `RunExecutionDrawer` | 已有 |
| Report 查看 | `WorkspaceReportDetail` | 已有 |
| 引导横幅 | 新增 `FirstRunBanner`（仅 UI 组件，不含业务） | 新增（不涉及 API） |
| 引导卡片 | 新增 `FirstRunContextCard`（仅 UI 组件，不含业务） | 新增（不涉及 API） |
| 引导状态机 | 新增 `useFirstRun` Hook + Provider | 新增（仅前端） |
| LocalStorage 持久化 | `app.firstRun.*` 5 个 key | 新增（仅前端） |

**全部"新增"都是纯前端 UI / Hook / LocalStorage，不涉及后端任何字段或接口。**

---

## 7. 与 WorkflowReview / Journey 的关系

| 既有文档 | 本文档的对应设计 |
|---|---|
| `WorkflowReview.md` 2.2-M2（Overview 引导步骤跳转过多） | **本设计**通过引导卡片 + 自动打开 Drawer 解决：用户**不跳转** Sider / PageHeader |
| `WorkflowReview.md` 2.3-M3（设默认环境 Header 不刷新） | 引导 Step 2 Drawer 保存成功后调用 `refresh()` 解决 |
| `WorkflowReview.md` 2.5-H1（Suite 详情跳 Run Center） | 引导 Step 5 直接打开 `RunExecutionDrawer`，不跳 Run Center |
| `WorkflowReview.md` 2.5-H3（Case 编辑器返回丢上下文） | 引导 Step 6 完成跳转 Dashboard，不经 Case 编辑器 |
| `WorkflowReview.md` 2.7-H1（四处执行入口不一致） | 引导 Step 5 统一为 Drawer 入口 |
| `WorkflowReview.md` 2.8-H1（Report 列表与 Overview 重复） | 引导流程**不经过 Report 列表**，直接跳 Run 详情，避免重复 |
| `Journey.md` ① 新用户 Journey Step 1~10 | **本设计 = Journey 的实施版**：每一步的"系统自动动作"对应 Journey 的"优化建议" |

---

## 8. 验收指标

| 指标 | 计算方式 | 当前 | 目标 |
|---|---|---|---|
| **首次跑通完成率** | 注册后 7 天内完成 6 步引导的用户占比 | — | ≥ 70% |
| **首次跑通总点击数** | Step 1~6 总点击数 | ~22（无引导） | **≤ 10** |
| **首次跑通总耗时** | 登录 → Step 6 完成 | ~30 分钟 | **≤ 8 分钟** |
| **引导中断率** | Step 1~5 任一步关闭引导卡的比例 | — | ≤ 20% |
| **菜单导航次数** | 引导过程中用户主动点击 Sider 切换模块的次数 | — | **0**（除非用户主动跳过） |
| **引导完成后 Dashboard 庆祝条点击率** | 点击"查看 Run 详情"按钮的比例 | — | ≥ 50% |
| **环境 / Suite 重复创建率** | 引导过程中重复创建同一资产的比例 | — | **0%** |

---

## 9. 不在范围（防止范围蔓延）

- ❌ 引导过程中视频 / 动画演示（避免引入新资源）
- ❌ 引导进度云端同步（仅 LocalStorage）
- ❌ 引导任务奖励 / 积分（避免引入新业务）
- ❌ 多语言引导文案（保持简体中文）
- ❌ 引导过程中"邀请同事"功能（避免引入协作场景）
- ❌ 引导跳过后的"必须完成"强制（保持可关闭）

---

## 10. 实施优先级

| # | 任务 | 优先级 | 估时 | 价值 |
|---:|---|:-:|:-:|:-:|
| 1 | `useFirstRun` Hook + FirstRunProvider | P0 | 1 天 | 高 |
| 2 | `FirstRunBanner` + `FirstRunContextCard` UI 组件 | P0 | 1 天 | 高 |
| 3 | Step 1 / 2 / 3 / 5 自动 Drawer 触发 | P0 | 2 天 | 高 |
| 4 | Step 3 自动创建"导入的用例"Suite | P0 | 0.5 天 | 高 |
| 5 | Step 6 庆祝条 + 完成状态写入 | P0 | 0.5 天 | 高 |
| 6 | 引导状态与 React Query 资产监听联动 | P1 | 1 天 | 高 |
| 7 | 引导跳过 / 关闭 / 重入机制 | P1 | 0.5 天 | 中 |
| 8 | Dashboard "首次跑通" 庆祝条 | P1 | 0.5 天 | 中 |
| 9 | 引导完成后的"提示关闭"二次确认 | P2 | 0.5 天 | 低 |
| 10 | 引导完成后的"再次体验"入口（用于演示 / 培训） | P2 | 0.5 天 | 低 |

---

# 11. 文档约束再确认

- ✅ 不新增任何后端 API（全部使用 Project / Environment / Suite / OpenAPI / Run / Report 6 类已有接口）
- ✅ 不新增任何数据库表 / 字段 / 迁移
- ✅ 不新增任何业务能力（不引入"任务奖励 / 引导视频 / 云端进度同步"等）
- ✅ 所有"新增"均为前端 Hook / Provider / UI 组件 / LocalStorage Key
- ✅ 引导叠加在 Workspace 既有 UI 上，不替换 / 不打断任何页面

---

> **版本**：v1.0 · 2026-07-16
> **作者**：资深产品经理（测试平台方向）
> **范围**：MVP 阶段首次使用引导 6 步；定时 / CI / 通知 / 协作场景不在本期范围
> **配套使用**：`PRD.md`（产品定位）→ `Journey.md`（用户视角）→ `WorkflowReview.md`（问题视角）→ `FirstRunGuide.md`（引导实施）→ `NavigationUX.md`（导航规范）