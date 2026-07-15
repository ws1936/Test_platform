# Report Center 设计

> 文档类型：页面与组件设计  
> 范围：Workspace → Report 模块，包括 Report 列表、Run 详情、Result 详情  
> 设计参考：GitHub Actions、Allure、Jenkins Blue Ocean 报告视觉  
> 实施约束：仅复用已有 API、不修改后端、不新增数据库、本阶段不写代码

---

## 1. 设计目标

- 把现有的 Run / Result / Failure 三个 API 端点组织成可读、易扫描的报告体验。
- 在不引入新后端接口的前提下提供 Pass / Fail / Duration / Recent Runs / Assertion Fail / Request / Response / Log 等维度。
- 沿用 Workspace Layout，在 Project 工作区内保持上下文。
- 视觉上参考 GitHub Actions / Blue Ocean / Allure：以状态色 + 摘要卡 + 详情 Tab 为骨架。

---

## 2. 已有数据能力（来自 `/runs/*`）

| 字段 | API 来源 | 用途 |
|---|---|---|
| `summary.total_runs / total_cases / total_passed / total_failed / total_error` | `GET /projects/{projectId}/runs/summary` | 顶部 KPI、最近 Run 摘要 |
| `run.overall_pass_rate / pass_rate / elapsed_seconds` | `GET /runs/{runId}` | 单 Run 通过率、耗时 |
| `run.recent_runs[]` | 同上 | 最近 Run 列表 |
| `run.failureList[]` | `GET /runs/{runId}/failures` | 失败原因 / 断言失败 |
| `result.request_snapshot / response_snapshot / assertions_snapshot / error_code / error_message` | `GET /results/{resultId}` | 请求 / 响应 / 断言 / 错误 |
| `result.body_truncated` | 同上 | 提示响应被截断 |
| `failureList.actual / expected / operator / assertion_type` | `failures` | 断言失败对比 |

> 现有 API 未提供“日志”端点（`GET /runs/{id}/log`）。设计中日志 Tab 将以 Result 列表 + 断言快照 + 错误信息为内容展示，对外注明“无后端日志端点，所见皆为后端返回快照”。

---

## 3. 页面与路由

```text
/projects/:projectId/workspace/report               Report List
/projects/:projectId/workspace/report/:runId        Run Detail
/projects/:projectId/workspace/report/:runId/result/:resultId   Result Detail
```

说明：

- 三级页面共用同一 React Query 缓存 key，复用现有 ProjectWorkspaceContext。
- 不需要新增抽屉 / Modal；所有内容直接在主区呈现。
- 返回路径：Result 详情 → Run 详情 → Report 列表。

---

## 4. Report List 页面

### 4.1 顶部 KPI 摘要

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Report                                                              │
│ Run 历史 / 报告分析                                                  │
├──────────┬──────────────┬──────────┬────────────┬──────────────────┤
│ 累计 Run │ 累计 Result │ 通过率 │ 失败 / 错误 │ 最近 Run 时间 │
│   18     │   240        │  92.5%  │  4 / 1      │  16:42          │
└──────────┴──────────────┴──────────┴────────────┴──────────────────┘
```

数据来源：`runs/summary`；视觉参考 Blue Ocean 顶部仪表盘：色块 + 数值 + 副标题。

### 4.2 Recent Runs 区

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Recent Runs                                            [查看全部 Report]│
├──────────────────────────────────────────────────────────────────────┤
│ ✓ 用户服务回归        92.5%   12.3s   suite  16:42 │
│ ✗ Case 列表加载失败   45.0%    6.1s   case   16:30 │
│ ✓ Order Service Run   98.0%   18.0s   project 16:15 │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 复用 `runs/summary.recent_runs`。
- 状态色：passed 绿、failed 红、running 蓝。
- 点击行进入 Run Detail。

### 4.3 Run 历史列表

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Run 历史  [状态: 全部 ▾]                              [搜索: _______] │
├──────────────────────────────────────────────────────────────────────┤
│ #   名称                范围   状态    通过率  耗时  时间        │
│ 18  user_smoke_v2      suite  ✓     92.5%  12.3s 16:42 │
│ 17  order_check        case   ✗     45.0%   6.1s 16:30 │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 复用 `runs/list?status=` 与 `runs/list?limit&offset`。
- 列表渲染：状态徽标 / ScopeTag / PassRate / ElapsedSeconds / StartedAt。
- 排序：服务端默认按 `created_at DESC`。
- 加载：初次 LoadingBlock；错误 ErrorState + 重试；空状态 EmptyState 引导去执行中心。

---

## 5. Run Detail 页面

### 5.1 顶部状态卡

```text
┌──────────────────────────────────────────────────────────────────────┐
│ user_smoke_v2                                ✓ finished  16:42 │
│ suite · 12 Case · 92.5% 通过率 · 12.3s                          │
│ 环境: staging                                                 │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 数据来源：`runs/{runId}`。
- 主要元素：名称（Title h2）、状态 RunStatusTag、ScopeTag、PassRate（环形或文字）、ElapsedSeconds、Environment。
- 主操作：[再次执行] / [打开 Suite 详情]。

### 5.2 Tabs

| Tab | 内容 | 数据来源 |
|---|---|---|
| 概览 | 总览 + 通过率 / 失败 / 错误 / 耗时 / 5 Case 摘要 | `runs/{runId}` + 计算 |
| 失败原因 | 失败断言表（Allure 风格） | `runs/{runId}/failures` |
| 全部 Result | 每条 Case 状态与耗时（点进 Result Detail） | `runs/{runId}/results` |
| 元信息 | Run ID、Project、环境、范围、触发人、时间 | `runs/{runId}` |

默认 Tab 取决于状态：有失败时默认“失败原因”，否则“概览”。

### 5.3 概览 Tab

```text
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Total 12     │ Passed 11   │ Failed 0    │ Error 1     │
│ Duration 12.3s            Pass Rate 91.6%             │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

实现：

- 5 个数字汇总：total / passed / failed / error / skipped。
- 通过率大号字 + 副标题 elapsed。
- 视觉：色块 + 标题 + 数字，副信息为 6 列表格。

### 5.4 失败原因 Tab（Allure 风格）

```text
┌──────────────────────────────────────────────────────────────────────┐
│ ✗ GET /api/users                 12.3s   assertion: status_code │
│     Expected: 200  Actual: 500  Operator: eq                 │
│     Response body (truncated):                                   │
│     ┌────────────────────────────┐                          │
│     │ {"error":"internal"}   │                          │
│     └────────────────────────────┘                          │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 数据来源：`runs/{runId}/failures`。
- 每条显示：Case 名称 / Method / Path / 耗时 / 断言类型 / 操作符 / Expected / Actual / 错误信息。
- 行级点击进入 Result Detail。
- 视觉：左侧状态色条 + 右侧断言对比（GitHub Action 风格）。

### 5.5 全部 Result Tab

```text
┌──────────────────────────────────────────────────────────────────────┐
│ #   状态   Method  名称                路径         耗时  错误 │
│ 1  ✓      GET    获取用户详情         /users/1     120ms  — │
│ 2  ✗      POST   登录                 /auth/login  200ms  status │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 数据来源：`runs/{runId}/results`。
- 点击行进入 Result Detail。
- 状态色：passed 绿、failed 红、error 橙、skipped 灰。

### 5.6 元信息 Tab

| 项 | 来源 |
|---|---|
| Run ID / Project / 环境 | `runs/{runId}` |
| 范围 / Scope ID | `runs/{runId}` |
| 触发人 | `triggered_by` |
| 开始 / 结束 | `started_at / finished_at` |
| 耗时 | `elapsed_seconds` |
| 创建时间 | `created_at` |

### 5.7 加载与错误

- Run 加载失败：整页 ErrorState + 重试。
- Result / Failure 加载失败：Tab 内 ErrorState + 单 Tab 重试。
- 空 Results 列表：EmptyState 引导重新执行。

---

## 6. Result Detail 页面

### 6.1 顶部元信息

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 获取用户详情                                ✓ passed  120ms  │
│ GET /api/users/1     Environment: staging                         │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 数据来源：`results/{resultId}`。
- 元素：Case 名称 / Method / Path / Status / MethodTag / Duration / Environment。
- 主操作：[跳到 Case 编辑器]（带 `?from=report&runId=&resultId=` 上下文）。

### 6.2 Tabs（GitHub Action 风格）

| Tab | 内容 | 数据 |
|---|---|---|
| 请求 | 实际请求 Method / URL / Headers / Body | `request_snapshot` |
| 响应 | Status / Headers / Body（截断提示） | `response_snapshot` |
| 断言 | 列表 + Passed/Failed + 期望 / 实际 / message | `assertions_snapshot` |
| 错误 | 错误代码 + 错误信息 | `error_code / error_message` |
| 概览 | 状态 + 耗时 + 时间 | `status / elapsed_ms / started_at / finished_at` |

默认 Tab：passed → “响应”；failed → “断言”；error → “错误”；status 缺失 → “请求”。

### 6.3 请求 Tab

```text
┌──────────────────────────────────────────────────────────────────────┐
│ GET /api/users/1                                                │
├──────────────────────────────────────────────────────────────────────┤
│ Headers                                                          │
│   Accept: application/json                                      │
│   Authorization: Bearer ******                                  │
├──────────────────────────────────────────────────────────────────────┤
│ Body                                                             │
│   (无)                                                            │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- Headers：列表 + 敏感 Header 自动脱敏（Authorization / Cookie 等）。后端已脱敏，UI 仅展示。
- Body：JSON 友好展示，超大时折叠 / 滚动。

### 6.4 响应 Tab

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 200 OK · 120ms                                                   │
├──────────────────────────────────────────────────────────────────────┤
│ Headers                                                          │
│   Content-Type: application/json                                 │
│   X-Request-Id: 5f1a7a8c                                        │
├──────────────────────────────────────────────────────────────────────┤
│ Body (128 字符 · 已截断)                                          │
│   {"id":1,"name":"Alice","email":"a@example.com"}             │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 状态码颜色：2xx 绿、3xx 蓝、4xx 黄、5xx 红。
- `body_truncated` 提示：UI 顶部 Alert 说明“响应超过 64 KiB 已被后端截断”。
- JSON 智能识别：尝试 `JSON.parse` 失败时按文本展示。

### 6.5 断言 Tab

```text
┌──────────────────────────────────────────────────────────────────────┐
│ #   状态   断言         操作符   期望     实际                  │
│ 1  ✓      status_code  eq      200      200                  │
│ 2  ✗      body_contains contains "id":1   ""                  │
└──────────────────────────────────────────────────────────────────────┘
```

实现：

- 数据来源：`assertions_snapshot`。
- 状态色与错误计数实时统计。

### 6.6 错误 Tab

- 错误代码 Tag（error_code）；未提供时显示 “无错误信息”。
- 错误信息 message 段落大号展示。
- 错误信息为空但状态为 error → 提示“后端仅返回错误码，无详细描述”。

### 6.7 状态与错误

- 加载：LoadingBlock / ErrorState。
- Result 不存在：整页错误。
- 请求 / 响应 / 断言快照为空：分别显示 EmptyState。
- 与 Suite / Case 编辑器跳转保留 from 上下文。

---

## 7. 组件树

```text
ReportListPage
├── ProjectWorkspaceHeader
├── ReportSummaryHeader
│   ├── MetricCard × 5
│   └── LastRunTime
├── RecentRunsPanel（GitHub Action 风格）
├── ReportTable
│   ├── StatusBadge
│   ├── PassRateText
│   └── RowAction
└── FilterBar（状态、搜索）

RunDetailPage
├── ProjectWorkspaceHeader
├── RunHeaderCard
│   ├── RunMeta
│   ├── StatusTag
│   ├── PassRateDial
│   └── DurationText
├── RunTabs
│   ├── RunOverviewTab
│   ├── FailureListTab（Allure 风格）
│   ├── RunResultListTab
│   └── RunMetaTab
└── RunAgainBar

ResultDetailPage
├── ResultHeaderCard
│   └── CaseMeta
├── ResultTabs
│   ├── RequestTab
│   ├── ResponseTab
│   ├── AssertionTab
│   ├── ErrorTab
│   └── OverviewTab
└── BackToRunBar
```

---

## 8. 视觉设计

### 8.1 颜色与排版

| 状态 | 颜色 | 用途 |
|---|---|---|
| passed | `#52c41a` | 状态徽标、行级首列背景 |
| failed | `#ff4d4f` | 状态徽标、断言失败 |
| error | `#fa8c16` | 状态徽标、执行错误 |
| skipped | `#bfbfbf` | 状态徽标、跳过 |
| running | `#1677ff` | 状态徽标（保留接口） |

字体：保留现有 Ant Design 默认，使用 `<Typography>` 系列；代码块使用等宽。

### 8.2 关键交互模式

- 列表行 hover：背景色 `#fafbff`；点击进入 Run Detail。
- Tab 切换：URL Hash 同步 `?tab=overview|failures|results|meta`。
- Run Detail 顶部“再次执行”按钮跳到 Execution Center（`?scope=&scopeId=`）。
- Result Detail 顶部的 [跳到 Case 编辑器] 保留 `?from=report&runId=&resultId=`。

---

## 9. 状态机

| 页面 | 状态 | 触发 | 表现 |
|---|---|---|---|
| Report List | loading | 首屏 | 全表 Skeleton |
| Report List | empty | 无 Run | EmptyState 引导去执行 |
| Report List | error | 列表失败 | 整页 ErrorState + 重试 |
| Run Detail | loading | 首屏 | Skeleton + Tab 骨架 |
| Run Detail | not_found | runId 不存在 | ErrorState 提示 Run 不存在 |
| Run Detail | tab_loading | 切 Tab | Tab 内 Skeleton |
| Run Detail | tab_error | 单 Tab 失败 | Tab 内 ErrorState |
| Result Detail | loading | 首屏 | Skeleton |
| Result Detail | not_found | resultId 不存在 | ErrorState |
| Result Detail | not_in_run | resultId 不属于当前 run | 顶部 ErrorState |
| Result Detail | snapshot_missing | 某 snapshot 为空 | 对应 Tab EmptyState |
| Result Detail | body_truncated | 后端标记截断 | 顶部 Alert 提示 |

---

## 10. 路由与上下文

- 列表：`/projects/:projectId/workspace/report`。
- Run Detail：`/projects/:projectId/workspace/report/:runId`。
- Result Detail：`/projects/:projectId/workspace/report/:runId/result/:resultId`。
- Query String：
  - `?status=passed|failed|error|...` 列表筛选。
  - `?search=...` 列表搜索。
  - `?tab=overview|failures|results|meta` Run Tab。
- 使用 `useProjectWorkspace().refresh()` 让 Header / ContextPanel 同步。

---

## 11. 验收标准

- [ ] 列表展示 KPI + Recent Runs + Run 历史，支持状态筛选与搜索。
- [ ] Run Detail 包含概览、失败原因、全部 Result、元信息四个 Tab。
- [ ] Result Detail 包含请求 / 响应 / 断言 / 错误 / 概览五个 Tab，且 body_truncated 有明确提示。
- [ ] 全部数据来自现有 API：`runs/summary`、`runs/{id}`、`runs/{id}/failures`、`runs/{id}/results`、`results/{id}`。
- [ ] 全部 Loading / Empty / Error / 截断 / 跳过 状态独立展示。
- [ ] 点击 Case 跳到 Case 编辑器，保留 `from=report&runId=&resultId=` 上下文。
- [ ] 不引入新接口；不修改后端、数据库或迁移。
- [ ] `npm run check` 通过；无 `any`、无重复块、无尾随空格。
- [ ] 边界检查：`git diff src/app migrations alembic.ini` 为空。

---

## 12. 与现有 IA 关系

- Report 模块的入口是左侧 Sider 的“报告”以及 Dashboard 的“最近 Run”。
- Result Detail 不会破坏 Case / Suite 上下文：通过 `from=report&...` 让 Case 编辑器的返回保留。
- Report 不属于 Project CRUD，因此仍然在 Project 工作区右侧 ContextPanel 提供“最近执行”快捷入口。
