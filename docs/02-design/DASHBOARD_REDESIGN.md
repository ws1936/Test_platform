# API 自动化测试平台 Dashboard 重设计

> 文档类型：Dashboard 页面设计  
> 设计范围：页面布局、组件设计、API 调用关系、状态管理  
> 实施约束：不新增接口、不修改已有 API、不新增数据库、本阶段不写代码

---

## 1. 设计结论

Dashboard 定位为**进入 Project 前的工作入口与轻量执行驾驶舱**，不伪装成全平台 BI 大盘。

由于当前后端没有跨 Project 的 Run、Suite、Report 聚合接口，推荐在 Dashboard 顶部增加“数据范围 Project”选择器：

- “最近项目”保持平台级展示。
- 最近执行、最近 Suite、最近 Report、Run Success Rate、今日执行次数均展示**当前所选 Project**的数据。
- 不通过对所有 Project 发起 N+1 请求来伪造全局统计。
- 若没有 Project、没有选择 Project 或现有数据无法形成准确指标，展示明确占位组件，不显示误导性的 `0`。

最终页面包含用户要求的六类信息：

1. 最近执行
2. 最近项目
3. 最近 Suite
4. 最近 Report
5. Run Success Rate
6. 今日执行次数

---

## 2. 数据口径

### 2.1 Dashboard 数据范围

Dashboard Header 中固定显示：

```text
数据范围：[Project 选择器]
```

规则：

- 默认选中 Project 列表中的第一项。
- 现有 Project 列表按 `created_at DESC` 返回，因此默认项是最近创建的 Project，不是最近访问的 Project。
- 当前 Project ID 写入前端 URL Query：`/dashboard?project={projectId}`。
- 刷新页面、复制链接或浏览器返回时，可以恢复同一 Project 范围。
- URL 中 Project 无权访问或不存在时，回退到列表第一项并展示提示。
- 当前没有“全部 Project”统计选项，因为后端没有安全且高效的全局聚合接口。

### 2.2 六类数据的准确口径

| 展示项 | 推荐口径 | 数据范围 | 支持状态 |
|---|---|---|---|
| 最近执行 | 按 `created_at DESC` 的最近 5 条 Run | 当前 Project | 已有 API 完整支持 |
| 最近项目 | 最近创建的 5 个 Project | 当前用户拥有的 Project | 已有 API 完整支持；不是最近访问 |
| 最近 Suite | Suite 列表按 `updated_at DESC` 前端排序后取 5 条 | 当前 Project | 已有 API + 前端派生 |
| 最近 Report | 最近可查看报告的 5 条终态 Run | 当前 Project | 复用 Run；Report 不是独立实体 |
| Run Success Rate | 最近最多 200 条已完成 Run 中，无 `failed`、无 `error` 的 Run 占比 | 当前 Project | 已有 API + 前端派生 |
| 今日执行次数 | 按浏览器本地时区统计今日创建的 Run | 当前 Project | 已有 API + 前端派生；超过 200 条时可能显示下限 |

### 2.3 Run Success Rate 定义

成功 Run：

```text
status = finished
AND failed = 0
AND error = 0
```

计算：

```text
Run Success Rate = 成功 Run 数 / 已完成 Run 数
```

补充规则：

- `pending`、`running`、`canceled` 不进入分母。
- 如果没有已完成 Run，显示 `—`，而不是 `0%`。
- 当前 Run 列表单次最多读取 200 条，因此标题或 Tooltip 必须写明“最近 N 次已完成 Run”。
- 不用 Project Summary 的 `overall_pass_rate` 冒充 Run Success Rate，因为该字段实际是 `passed result / total result`，语义是用例结果通过率。

### 2.4 今日执行次数定义

基于 `GET /projects/{project_id}/runs?limit=200&offset=0` 返回的 Run：

1. 使用浏览器本地时区确定今日 `00:00:00`。
2. 对 `created_at` 在今日范围内的 Run 计数。
3. 当 `total <= 200` 时，数值准确。
4. 当 `total > 200`，但第 200 条 Run 已早于今日零点时，今日数值仍然准确。
5. 当 `total > 200` 且返回的 200 条全部发生在今日时，显示 `200+`，不可显示错误的精确值。
6. Tooltip 标注“按当前浏览器时区统计”。

如果产品要求“全平台今日执行次数”或“跨 Project 今日执行次数”，当前无对应接口，应改为能力占位，不进行全 Project 并发聚合。

### 2.5 最近 Report 定义

当前没有独立 Report 表或 Report 列表接口。Report 是 Run / Result 的只读展示，因此：

- 最近 Report 复用 Run 列表。
- 只显示终态 Run：`finished`、`failed`。
- 卡片强调通过率、失败数、错误数和耗时。
- 点击后进入 `/projects/{projectId}/reports/{runId}`。
- 不重复请求不存在的 Report 资源。

---

# ① 页面布局

## 3. 桌面端布局

采用 12 栅格布局。

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 你好，{用户}                          数据范围：[Project ▼] [刷新] │
│ 查看当前项目的最近执行与测试质量                                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐  ┌──────────────────────────────┐
│ Run Success Rate             │  │ 今日执行次数                 │
│ 92.5%                        │  │ 18                           │
│ 最近 40 次已完成 Run         │  │ 当前 Project · 本地时区      │
└──────────────────────────────┘  └──────────────────────────────┘

┌──────────────────────────────────────────────┐  ┌────────────────────┐
│ 最近执行                                     │  │ 最近 Report        │
│ Status / 名称 / Scope / 通过率 / 时间        │  │ 通过率 / 失败 / 时间│
│ …                                            │  │ …                  │
│ [查看全部执行]                               │  │ [查看全部报告]     │
└──────────────────────────────────────────────┘  └────────────────────┘

┌─────────────────────────────────┐  ┌─────────────────────────────┐
│ 最近项目                        │  │ 最近 Suite                  │
│ 名称 / 描述 / 创建时间          │  │ 名称 / 描述 / 更新时间      │
│ …                               │  │ …                           │
│ [查看全部项目]                  │  │ [查看全部 Suite]            │
└─────────────────────────────────┘  └─────────────────────────────┘
```

### 3.1 栅格比例

| 区域 | 桌面端宽度 |
|---|---:|
| Run Success Rate | 6 / 12 |
| 今日执行次数 | 6 / 12 |
| 最近执行 | 8 / 12 |
| 最近 Report | 4 / 12 |
| 最近项目 | 6 / 12 |
| 最近 Suite | 6 / 12 |

### 3.2 页面首屏优先级

从上到下：

1. 当前数据范围，避免用户误认为是全平台数据。
2. 两个质量 KPI：Run Success Rate、今日执行次数。
3. 最近执行与最近 Report，支撑回归与失败定位。
4. 最近项目与最近 Suite，支撑快速进入工作空间。

### 3.3 响应式布局

| 断点 | 布局 |
|---|---|
| `≥ 1440px` | 12 栅格，按上述 2 列布局 |
| `1024px–1439px` | KPI 保持 2 列；四个列表区域均为整行 |
| `< 1024px` | 所有区域单列；表格切换为紧凑列表 |
| `< 768px` | Project 选择器独占一行；隐藏次要列，只保留状态、名称、时间 |

---

## 4. 各区域内容

### 4.1 Dashboard Header

展示：

- 当前用户昵称或用户名。
- 一句任务导向文案。
- Project 数据范围选择器。
- 手动刷新按钮。
- 可选主操作“发起执行”，进入当前 Project 执行中心。

不展示：

- 全平台 Project 数。
- 全平台通过率。
- superuser 的跨用户统计。

### 4.2 Run Success Rate Card

展示：

- 百分比或环形进度。
- 成功 Run 数 / 已完成 Run 数。
- 数据窗口：“最近 N 次已完成 Run”。
- 点击进入当前 Project 测试报告页。

状态：

- 无已完成 Run：显示 `—` 和“暂无已完成执行”。
- Run 请求失败：卡片内独立错误与重试。
- 正在重新拉取：保留旧数据，显示局部刷新状态。

### 4.3 今日执行次数 Card

展示：

- 今日次数。
- 当前 Project 名称。
- “按浏览器本地时区统计”说明。
- 数据不完整时显示 `200+` 或 `—`，不显示虚假精确值。

点击后进入当前 Project 测试报告页。当前没有日期过滤 API，因此不承诺跳转后自动只显示今日 Run。

### 4.4 最近执行 Panel

建议字段：

| 字段 | 说明 |
|---|---|
| 状态 | pending / running / finished / failed / canceled |
| 执行名称 | Run 名称 |
| Scope | case / collection / project |
| 结果 | passed / total；同时展示 failed、error |
| 通过率 | Run 的 `pass_rate` |
| 时间 | `created_at` 或 `started_at` |

行为：

- 点击行进入对应 Run Report。
- “查看全部执行”进入当前 Project 的执行中心或测试报告页。
- 最多展示 5 条。

### 4.5 最近 Report Panel

建议使用紧凑列表，不再复制完整 Run 表格。

每项展示：

- Report / Run 名称。
- 通过率。
- 失败数与错误数。
- 总耗时。
- 完成时间。

行为：

- 点击进入 Run Report。
- 仅展示 `finished`、`failed` Run。
- 无终态 Run 时展示“暂无可查看报告”。

### 4.6 最近项目 Panel

当前接口按创建时间倒序，因此卡片副标题必须明确：

```text
按创建时间排序
```

每项展示：

- Project 名称。
- 两行以内描述。
- 创建时间。
- 更新时间可作为辅助信息，但不参与排序。

行为：

- 点击进入 Project Overview。
- “查看全部项目”进入 `/projects`。
- 无项目时展示创建 Project 主操作。

不使用“最近访问”文案，因为当前没有访问历史接口。

### 4.7 最近 Suite Panel

每项展示：

- Suite 名称。
- 所属 Project 名称（当前都相同，可弱化）。
- 描述。
- 更新时间。

数据处理：

- 调用当前 Project Suite 列表。
- 前端按 `updated_at DESC` 排序。
- 取前 5 条。

行为：

- 点击进入 Suite 详情。
- “查看全部 Suite”进入当前 Project Suite 列表。
- 无 Suite 时引导创建 Suite。

---

# ② 组件设计

## 5. 组件树

```text
DashboardPage
├── DashboardHeader
│   ├── UserGreeting
│   ├── ProjectScopeSelector
│   ├── DashboardRefreshButton
│   └── RunPrimaryAction
├── DashboardMetricGrid
│   ├── RunSuccessRateCard
│   └── TodayRunsCard
├── DashboardActivityGrid
│   ├── RecentRunsPanel
│   │   └── RecentRunTable / RecentRunList
│   └── RecentReportsPanel
│       └── RecentReportList
└── DashboardAssetGrid
    ├── RecentProjectsPanel
    │   └── RecentProjectList
    └── RecentSuitesPanel
        └── RecentSuiteList
```

## 6. 组件职责

| 组件 | 单一职责 | 主要输入 | 主要输出 / 行为 |
|---|---|---|---|
| `DashboardPage` | 编排查询与页面布局 | 当前用户、URL Project ID | 组合各展示组件 |
| `DashboardHeader` | 展示标题和范围操作 | 用户、Project、刷新状态 | 选择 Project、刷新、去执行 |
| `ProjectScopeSelector` | 选择 Dashboard 数据范围 | Project 列表、selected ID | 更新 URL Query |
| `RunSuccessRateCard` | 展示派生 Run 成功率 | completed runs、loading、error | 跳转报告 |
| `TodayRunsCard` | 展示今日执行次数 | runs、total、时区 | 跳转报告 |
| `RecentRunsPanel` | 展示最近 5 条 Run | runs、Project ID | 进入 Run Report |
| `RecentReportsPanel` | 展示最近终态 Run 的报告入口 | terminal runs、Project ID | 进入 Report |
| `RecentProjectsPanel` | 展示最近创建 Project | projects | 进入 Project Overview |
| `RecentSuitesPanel` | 展示最近更新 Suite | suites、Project ID | 进入 Suite 详情 |
| `DashboardPanel` | 统一面板标题、操作与容器样式 | title、extra、children | 保持布局一致 |
| `MetricCard` | 统一 KPI 显示 | label、value、hint、status | 可点击 KPI |
| `CapabilityPlaceholder` | 明确无接口或数据不完整 | title、reason、next action | 不伪造数值 |
| `PanelSkeleton` | 局部 Loading | panel 类型 | 保持页面骨架稳定 |
| `PanelError` | 局部 Error 与重试 | error、retry | 单面板重试 |
| `PanelEmpty` | 区分“请求成功但无数据” | title、action | 引导下一步 |

## 7. 组件边界原则

- 页面组件不直接渲染复杂表格单元格，列表内容下沉到 Panel。
- API 调用集中在现有 `src/api` 封装，不在展示组件内拼接 URL。
- 派生统计放在 Dashboard selector / hook 层，不散落在多个组件中重复计算。
- `RecentRunsPanel` 与 `RecentReportsPanel` 可以共享 Run 数据，但展示职责不同。
- Loading、Empty、Error 必须是三种独立状态，不能都用空白卡片代替。

---

# ③ API 调用关系

## 8. 页面调用流程

```text
进入 /dashboard
  │
  ├── 复用认证缓存：GET /auth/me
  │
  └── GET /projects?page=1&size=20
       │
       ├── 渲染最近项目：items.slice(0, 5)
       ├── 恢复 URL 中合法 projectId
       └── 若无 URL projectId，选择 items[0].id
             │
             ├── GET /projects/{projectId}/runs?limit=200&offset=0
             │    ├── 最近执行：前 5 条
             │    ├── 最近 Report：终态 Run 前 5 条
             │    ├── Run Success Rate：前端计算
             │    └── 今日执行次数：前端计算
             │
             └── GET /projects/{projectId}/suites
                  └── 按 updated_at DESC，取前 5 条
```

三个 Dashboard 业务请求的依赖关系：

- Project 列表为第一阶段请求。
- Run 与 Suite 请求依赖有效 `selectedProjectId`，第二阶段并行执行。
- 不调用全量 Project 的 Run / Suite 接口。
- 不调用用户管理、角色管理或 Project Summary 来拼凑 Dashboard。

## 9. API 映射

| UI 数据 | 已有接口 | 请求参数 | 前端处理 |
|---|---|---|---|
| 当前用户 | `GET /auth/me` | 无 | 复用认证缓存，不重复请求 |
| 最近项目 | `GET /projects` | `page=1&size=20` | 前 5 条；按接口的创建时间倒序 |
| Project 选择器 | `GET /projects` | `page=1&size=20` | 当前页可选；更多项目进入项目列表 |
| 最近执行 | `GET /projects/{projectId}/runs` | `limit=200&offset=0` | 取前 5 条 |
| 最近 Report | 同上 | 同上 | 过滤终态并取前 5 条 |
| Run Success Rate | 同上 | 同上 | 基于 finished Run 前端计算 |
| 今日执行次数 | 同上 | 同上 | 按本地日期过滤；必要时显示下限 |
| 最近 Suite | `GET /projects/{projectId}/suites` | 无搜索词 | 按 `updated_at` 前端排序，取 5 条 |

## 10. 不调用的能力

- 不对每个 Project 调用 `/runs` 和 `/suites`。
- 不读取 `/users` 拼接触发人名称；普通用户也无该权限。
- 不把 `/projects/{projectId}/runs/summary` 的 `overall_pass_rate` 当作 Run Success Rate。
- 不新增 `/dashboard`、`/recent`、`/statistics/today` 等接口。
- 不新增前端 mock 请求。

## 11. 页面跳转关系

| 来源组件 | 点击目标 |
|---|---|
| 最近项目 | `/projects/{projectId}/overview` |
| 最近 Suite | `/projects/{projectId}/suites/{suiteId}` |
| 最近执行 | `/projects/{projectId}/reports/{runId}` |
| 最近 Report | `/projects/{projectId}/reports/{runId}` |
| Run Success Rate | `/projects/{projectId}/reports` |
| 今日执行次数 | `/projects/{projectId}/reports` |
| 发起执行 | `/projects/{projectId}/runs` |
| 查看全部项目 | `/projects` |
| 查看全部 Suite | `/projects/{projectId}/suites` |
| 查看全部报告 | `/projects/{projectId}/reports` |

---

# ④ 状态管理方案

## 12. 状态分类

### 12.1 服务端状态：React Query

全部远程数据使用 React Query，不复制到 Zustand。

建议 Query Keys：

```text
["dashboard", "projects", { page: 1, size: 20 }]
["dashboard", projectId, "runs", { limit: 200 }]
["dashboard", projectId, "suites"]
```

也可复用项目内现有 Query Keys，但必须保证：

- Dashboard Run 查询与报告页 Run 查询能共享或精确失效。
- Dashboard Suite 查询与 Suite 管理页能共享或精确失效。
- 新建 Project、Suite 或 Run 后，对应 Dashboard Query 会被失效。

建议缓存策略：

| Query | `staleTime` | 说明 |
|---|---:|---|
| 当前用户 | 5 分钟 | 复用认证层缓存 |
| Project 列表 | 60 秒 | 变化频率较低 |
| Suite 列表 | 60 秒 | 变化频率中等 |
| Run 列表 | 15 秒 | 执行数据变化更频繁 |

其他策略：

- 首次进入显示 Panel Skeleton。
- 手动刷新调用三个 Dashboard Query 的 `refetch`。
- 后台刷新时保留上次数据，不让整个页面闪空。
- 一个 Panel 失败不阻塞其他 Panel。
- 403 / 404 不自动重试。
- 网络错误最多按全局 Query 策略有限重试。

### 12.2 认证状态：Zustand

Zustand 仅保存已有认证状态：

- `access_token`
- `refresh_token`
- 当前用户

Dashboard 不把 Project、Run、Suite 数据写入 Zustand。

### 12.3 URL 状态

当前 Dashboard 数据范围写入 URL：

```text
/dashboard?project={projectId}
```

URL 状态负责：

- Project 选择恢复。
- 页面分享。
- 浏览器前进 / 后退。
- Project 切换后的查询联动。

### 12.4 页面本地状态

仅保存短生命周期 UI 状态：

- Project 选择器是否展开。
- 手动刷新按钮状态。
- 移动端 Panel 折叠状态（如需要）。

不使用 Local Storage 保存“最近访问 Project”，因为这会改变“最近项目”的数据语义，并形成跨设备不一致。

## 13. 派生状态

由 Run 与 Suite Query 通过纯计算派生，必要时使用 memoized selector：

```text
recentRuns
terminalRuns
recentReports
completedRuns
successfulRuns
runSuccessRate
todayRuns
todayRunsDisplayValue
recentSuites
```

派生原则：

- 不修改 React Query Cache 原数据。
- 日期比较统一使用同一时区策略。
- 分母为 0 时返回 `null`，由组件显示 `—`。
- 数量超过接口窗口时返回带完整性标记的结构，而不是只返回数字。

推荐派生结果结构：

```text
{
  value: number | null,
  displayValue: string,
  isExact: boolean,
  sampleSize: number,
  reason?: string
}
```

---

## 14. Loading / Empty / Error / Placeholder

| 状态 | 展示规则 |
|---|---|
| Loading | 每个 Panel 独立 Skeleton，不阻塞 Dashboard Header |
| Empty Projects | 页面级空状态，主操作“新建 Project” |
| Empty Runs | KPI 显示 `—`；最近执行和 Report 展示首次执行引导 |
| Empty Suites | 最近 Suite Panel 展示“创建 Suite” |
| Error Projects | Project 依赖区域进入错误状态；保留 Header 与重试 |
| Error Runs | 两个 KPI、最近执行、最近 Report 显示同源错误提示；一次重试同一 Query |
| Error Suites | 只影响最近 Suite Panel |
| Capability Missing | 使用能力占位，不显示 `0` 或 mock 数据 |
| Background Refresh | 保留旧数据，Panel 标题区显示轻量刷新状态 |

### 14.1 能力占位组件文案

如果未来要求切换到“全部 Project”范围，当前应展示：

```text
标题：全局统计暂不可用
说明：当前平台仅提供 Project 维度的执行与报告查询，无法准确计算跨 Project 数据。
操作：请选择一个 Project 查看。
```

不要展示：

- 随机 mock 数字。
- 前端硬编码成功率。
- 将空数据误写为 `0%`。
- 对全部 Project 发起不受控的并发请求。

---

## 15. 验收标准

### 页面布局

- [ ] 六类指定信息均有明确区域。
- [ ] 当前 Project 数据范围在首屏可见。
- [ ] 桌面、平板、移动端层级清晰。
- [ ] 最近执行与最近 Report 不使用完全相同的视觉组件。

### 数据准确性

- [ ] 最近项目明确是按创建时间，而不是最近访问。
- [ ] 最近 Suite 明确由 `updated_at` 前端排序。
- [ ] Report 明确是 Run 的只读投影视图。
- [ ] Run Success Rate 不误用 Result Pass Rate。
- [ ] 今日执行次数注明时区与 200 条窗口限制。
- [ ] 无准确数据时显示 `—`、`200+` 或占位，不显示虚假精确值。

### API 约束

- [ ] 只调用现有 Project、Suite、Run、Auth API。
- [ ] 不新增 Dashboard API。
- [ ] 不新增数据库或 Report 实体。
- [ ] 不进行全 Project N+1 聚合请求。

### 状态管理

- [ ] 远程数据仅由 React Query 管理。
- [ ] Zustand 只保存认证状态。
- [ ] 当前 Project 由 URL Query 管理。
- [ ] Loading、Empty、Error、Placeholder 状态互相区分。
- [ ] Project / Suite / Run 变更后可以精确刷新相关 Dashboard 数据。

---

## 16. 最终推荐方案摘要

```text
Dashboard
├── Header：用户问候 + Project 数据范围 + 刷新 + 发起执行
├── KPI
│   ├── Run Success Rate（当前 Project，最近最多 200 条）
│   └── 今日执行次数（当前 Project，本地时区）
├── Activity
│   ├── 最近执行（最近 5 条 Run）
│   └── 最近 Report（最近 5 条终态 Run 投影）
└── Assets
    ├── 最近项目（最近创建 5 个）
    └── 最近 Suite（当前 Project 最近更新 5 个）
```

该方案完整覆盖目标内容，同时只复用已有 API、避免全局 N+1 请求，并通过 Project 范围、准确口径和能力占位保证企业级 Dashboard 不产生误导数据。
