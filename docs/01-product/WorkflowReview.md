# API 自动化测试平台 · 全流程 Workflow Review

> 文档类型：Workflow 走查与问题清单（资深 PM 视角）
> 走查路径：`登录 → Project → Environment → Import → Suite → Run → Report`
> 评估维度：**重复点击 / 重复跳转 / 重复确认 / 重复输入 / 迷路 / 上下文丢失**
> 严重等级：**High（阻塞主流程，导致用户迷失或放弃）/ Medium（影响效率或清晰度）/ Low（细节优化）**
> 约束：**不新增 API、不新增数据库、不新增功能模块**——所有建议必须落在已存在的 API / 字段 / 组件 / 前端路由 / URL Query / LocalStorage 上
> 配套：`PRD.md`、`INFORMATION_ARCHITECTURE.md`、`NavigationUX.md`、`PROJECT_WORKSPACE.md`、`UX_REVIEW.md`、`Journey.md`

---

## 0. 评估方法

### 0.1 六维度定义

| 维度 | 定义 | 典型信号 |
|---|---|---|
| **重复点击** | 用户为达成一个目标需点击同一语义按钮 ≥ 2 次 | "再次执行"按钮、"保存"按钮 |
| **重复跳转** | 用户为读一个完整信息需在 ≥ 2 个页面 / 路由间往返 | "概览 → Report 列表 → Report 详情" |
| **重复确认** | 用户为完成一个动作需点 ≥ 2 次确认（Modal / Popconfirm / 警告） | "删除 → 输入项目名 → 再次确认" |
| **重复输入** | 用户为同一字段在 ≥ 2 个页面输入相同内容 | Project 描述 / 环境 Variables |
| **迷路** | 用户在 1 分钟内 ≥ 3 次点击 Back / 面包屑 / 切换模块 | "我刚才在哪？现在在做什么？" |
| **上下文丢失** | 用户从 A 跳到 B 后，A 的搜索 / Tab / 实体 ID 未保留或被错误继承 | "Case 编辑器返回丢失搜索词" |

### 0.2 等级定义

| 等级 | 定义 | 处理优先级 |
|---|---|---|
| **High** | 阻塞主流程、产生数据错乱（404/污染）、用户在 ≥ 30% 场景下迷失 | P0，必须修复 |
| **Medium** | 影响效率 ≥ 2 次点击 / 1 次跳转，但流程可完成 | P1，建议修复 |
| **Low** | 细节可优化，不阻塞流程 | P2，体验打磨 |

---

## 1. 走查总览（先看结论）

### 1.1 按等级汇总

| 等级 | 数量 | 主要问题 |
|---|---:|---|
| **High** | **6 个** | H1 Project 切换 URL 不重置 · H2 三处执行入口不一致 · H3 Report 列表与 Overview 区块完全重复 · H4 Suite 详情"执行 Suite"跳 Run Center（与 Drawer 入口分裂）· H5 Case 编辑器返回丢失 Suite 上下文与搜索状态 · H6 行内"从 Suite 移除"与"删除 Case"语义混淆 |
| **Medium** | **12 个** | 见 §3 各页详述 |
| **Low** | **8 个** | 见 §3 各页详述 |

### 1.2 按页面汇总（问题密度）

| 页面 | High | Medium | Low | 主要症结 |
|---|---:|---:|---:|---|
| 登录 | 0 | 0 | 2 | 落点单一、错误文案泛化 |
| Project 列表 | 0 | 2 | 2 | 摘要不前置 / 新建后无下一步引导 |
| Environment | 0 | 3 | 1 | 列表缺引用提示 / Header 不实时刷新 / Variables 编辑门槛高 |
| Import | 0 | 3 | 0 | 入口分散 / 默认策略非最佳 / 错误提示不清 |
| Suite | 2 | 3 | 1 | 执行入口分裂 / Case 编辑返回丢上下文 / 行内操作语义混淆 |
| Run | 1 | 2 | 1 | 三入口不一致 / 最近 Run 重复 / Run Center 表单重复 |
| Report | 1 | 3 | 1 | Report 列表与 Overview 重复 / Result 详情→Case→返回上下文丢失 |
| 跨页面（上下文）| 2 | 1 | 0 | Project 切换 URL 不重置 / Result→Case 返回路径错乱 |

### 1.3 走查流程图（标注问题位置）

```text
[登录] Low:落点单一
  ↓
[Dashboard] Low:教学卡长期存在
  ↓
[Project列表] Low:摘要不全  |  Medium:进入Workspace无过渡
  ↓
[Project工作区 Overview]
  ├─→ Medium: 引导步骤需 Sider/PageHeader/Drawer 多次切换（迷路）
  ├─→ High: "最近 Run" 区块与 Report 列表完全重复
  └─→ Medium: 缺资产完整度徽标 + 主操作按钮
  ↓
[Environment 模块]
  ├─→ Medium: Headers/Variables JSON 模式门槛高（重复输入风险）
  ├─→ Medium: 删除无引用提示（迷路到"为何失败"）
  └─→ Medium: 设默认后 Workspace Header 不实时刷新（上下文不一致）
  ↓
[OpenAPI Import]
  ├─→ Medium: 入口分散在 Overview/Suite/Case（迷路）
  ├─→ Medium: 冲突策略非默认 skip（重复选择）
  └─→ Medium: 错误提示"预览功能不可用"不清（迷路）
  ↓
[Suite]
  ├─→ High: Suite 详情"执行 Suite"按钮跳 Run Center（重复跳转，与 Drawer 入口分裂）
  ├─→ Medium: Suite 列表缺 Case 数 / 通过率（迷路到详情才能判断）
  └─→ High: 行内"从 Suite 移除" vs "删除 Case" 语义混淆（重复确认）
  ↓
[Case 编辑器]
  ├─→ High: 返回丢失 Suite 上下文与搜索状态（上下文丢失）
  └─→ Low: Body 字段缺 JSON 校验（重复输入风险）
  ↓
[Run]
  ├─→ High: Run Center / Suite 详情 / Case 编辑器 / Header 四入口不一致（重复跳转 + 重复点击）
  ├─→ Medium: "最近 5 Run" 与 Overview / Report 列表重复（重复跳转）
  └─→ Medium: 默认 scope / env 不全预填（重复输入）
  ↓
[Report]
  ├─→ High: Report 列表 KPI + Recent Runs 与 Overview 完全重复（重复跳转 + 重复输入）
  ├─→ High: Result 详情 → Case 编辑器 → 返回可能回到 Run 列表（上下文丢失）
  ├─→ Medium: Run 详情 Tab 信息与 Result 详情 Tab 重复（重复跳转）
  └─→ Medium: 失败原因 Tab 折叠 expected/actual（重复点击才能看全）
```

---

# 2. 逐页面详述

> 每个问题标注：`类别 / 等级 / 触发场景 / 现象 / 根因 / 建议`，所有建议严格落在已有能力范围。

---

## 2.1 登录页 `/login`

### 走查路径

```text
Dashboard / 任意深链 / 链接  →  /login  →  登录成功  →  Dashboard
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复点击 | — | — | — | — |
| 重复跳转 | Low | 登录成功后总跳 Dashboard，老用户还要 Dashboard → Project 列表 → 概览，3 步冗余 | 落点判定逻辑只有"index → /dashboard" | 登录后判断 LocalStorage `app.recentProjects`：第一项 ≤ 7 天 → 直跳该 Project 概览；否则 Dashboard。已有 Recent Projects 持久化能力（见 NavigationUX §⑥） |
| 重复确认 | — | — | — | — |
| 重复输入 | — | — | — | — |
| 迷路 | Low | 登录失败 / 账号禁用 / 密码错误均只显示后端 message，用户不知该做什么 | 错误码未分类 | 登录失败时区分"账号不存在或密码错误 / 账号已禁用 / 请求过于频繁（429）"三种文案，对应引导"联系管理员开通 / 修改密码" |
| 上下文丢失 | Low | 用户从 `/projects/xxx/reports/yyy` 深链被踢回 `/login` 后，登录成功跳 Dashboard，不再回到原 URL | 当前未持久化 returnTo | Token 失效时把原 URL 写入 `sessionStorage["app.returnTo"]`，登录成功后优先跳回。已有 sessionStorage 持久化能力（详见 NavigationUX §13.4） |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.1-L1 | Low | 重复跳转 | 登录落点单一，未识别 Recent Project |
| 2.1-L2 | Low | 迷路 / 上下文 | 登录失败文案未分类；深链 returnTo 未持久化 |

---

## 2.2 Project 列表 `/projects` + Project 工作区 Overview

### 走查路径

```text
Dashboard → Project 列表 → 选择/新建 Project → Workspace Overview
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复点击 | — | — | — | — |
| 重复跳转 | Medium | Overview 上"最近 Run"区块与 Report 列表是同一份数据（同一 React Query key），用户从 Overview → Run 详情 → 返回 → 想看更多 → 再跳 Report 列表，2 次跳转才到全量列表 | Overview 内嵌了 `RecentRunsPanel`，与 `/workspace/report` 列表同源同视图 | Overview 的"最近 Run"区块**保留但限定为 Top 5 + "查看全部 →"按钮**，完整列表走 `/workspace/report`；明确两个页面的边界（详见 NavigationUX §⑪ 路径 A） |
| 重复跳转 | Medium | 新建 Project 后跳 Workspace Overview，但列表与 Workspace 之间无明确过渡，列表中找不到新建的 Project | 列表 query 可能在新建后未立即 invalidate | 新建 Project Drawer onSuccess 中同时 invalidate `["projects", "", "list"]`，列表在用户 Back 时已刷新；Overview 提供"返回项目列表"按钮 |
| 重复确认 | — | — | — | — |
| 重复输入 | — | — | — | — |
| 迷路 | Medium | Overview 引导步骤 1~4（默认环境 / Suite / Case / Run）每步都需在 Sider、PageHeader、Drawer 之间切换；用户难以定位"下一步在哪" | 引导卡片仅文案 + 跳转链接，无 drawer 直达 | Overview 顶部**"下一步"主操作按钮**，按缺失优先级自动选："创建环境 / 创建 Suite / 导入或创建 Case"，点击直接打开对应 Drawer，**不跳转页面** |
| 迷路 | Low | 资产计数（环境 / Suite / Case）为 0 时无视觉强调，用户不知"还差什么" | Overview 卡片只有数字 0 | 缺失任一项时显示红点徽标 + 文字"缺失"；已有 `runs/summary` 等接口可读 total |
| 上下文丢失 | — | — | — | — |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.2-M1 | High | 重复跳转 | Overview "最近 Run" 区块与 Report 列表数据完全重复 |
| 2.2-M2 | Medium | 迷路 | Overview 引导步骤需在 Sider/PageHeader/Drawer 多次切换 |
| 2.2-M3 | Medium | 重复跳转 | 新建 Project 后列表可能未立即刷新 |
| 2.2-L1 | Low | 迷路 | 资产计数为 0 时无视觉强调 |

---

## 2.3 Environment 模块 `/workspace/environment`

### 走查路径

```text
Overview 引导 → Environment 列表 → 新建 / 编辑 / 设默认 / 删除 / 切默认
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复点击 | Medium | Headers / Variables 需在 JSON 模式下编辑，新手需反复切换到 JSON 视图 / 输入键值 / 校验 | Environment Drawer 用 `JsonEditor` 文本框 | Drawer 默认**键值表模式**（Key / Value 两列 + "+"新增行 + "切换为 JSON"按钮）；高级用户保留 JSON 模式 |
| 重复输入 | Medium | 用户在 Run Drawer 中需要确认 Variables 是否正确，但 Run Drawer 只展示只读 Variables；要修改必须：关 Run Drawer → 切到 Environment → 编辑 → 保存 → 重新打开 Run Drawer，**Variables 不能跨 Drawer 预填** | Environment Drawer 与 Run Drawer 不联动 | Run Drawer 顶部"环境 Tag"展示 Base URL，**点击展开**显示 Variables 摘要（只读）；明确标注"修改请到 Environment 模块"（已有此限制，UI 应明示） |
| 重复跳转 | Medium | Overview "1. 设置默认环境"引导跳到 Environment 列表；Run Drawer 也提示"前往 Environment"；用户可能两边都被引到 Environment | 引导重复 | Environment 列表顶部在 "未设置默认" 时显示顶部红条 + "立即设为默认"按钮，**避免 Overview / Run Drawer / Environment 三处引导分散** |
| 重复确认 | Medium | 删除非默认环境时只显示 Popconfirm，**未告知"此环境已被 X 个 Run 引用 / 将影响历史 Report"**；用户删除后才在 Run 详情发现 environmentName 异常 | 后端 DELETE 接口不返回引用计数 | 前端在 Popconfirm 描述中加"该环境已被历史 Run 引用 N 次，删除不会影响 Run 报告，但后续 Run 将无法再使用此环境"（基于前端已有 Run 列表接口做前端过滤计数，**不新增 API**） |
| 迷路 | Medium | 设默认环境后，Workspace Header 的默认环境徽标**未实时刷新**，用户以为没生效 | `useProjectWorkspace().refresh()` 未在"设默认"成功后调用 | 列表行"设为默认"成功后调用 `refresh()`，Header 立即更新；Environment Drawer 保存成功后同样调用 refresh() |
| 上下文丢失 | Low | Environment Drawer 关闭不修改 URL，但若用户从 Overview 引导点击"创建环境"，Drawer 关闭后回到 Overview，缺失引导已满足的状态会保留显示 | Overview "下一步"卡片未在 Drawer 保存后自动消失 | Overview "下一步"卡片在 Environment Drawer onSuccess 时通过 `useProjectWorkspace().refresh()` 失效 `["projects", projectId, "environments"]` + 检查 `defaultEnvironmentId`，缺失标记自动消失 |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.3-M1 | Medium | 重复点击 | Headers/Variables JSON 模式编辑门槛高 |
| 2.3-M2 | Medium | 重复输入 | Run Drawer Variables 只读，修改需跨页面 |
| 2.3-M3 | Medium | 迷路 | 设默认环境后 Header 徽标不实时刷新 |
| 2.3-M4 | Medium | 重复确认 | 删除环境无引用次数提示 |
| 2.3-L1 | Low | 上下文丢失 | Overview 引导完成后"下一步"卡不自动消失 |

---

## 2.4 OpenAPI Import `/workspace/import/:suiteId`

### 走查路径

```text
Suite 详情 / Case 列表 → OpenAPI Import → 选择来源 → 预览 → 确认 → Suite 详情
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复点击 | Medium | 用户必须手动选择"冲突策略（skip / overwrite）" + "名称前缀" + "标签过滤"，每次导入都要重新填 | Drawer 默认值非最佳实践 | 冲突策略**默认 skip**（避免误覆盖），名称前缀默认空，标签过滤默认"全部"；**高级设置折叠**，普通用户不必触碰 |
| 重复跳转 | Medium | 导入完成后停留在 Import 页，用户必须手动点"返回 Suite"或浏览器 Back；导入出错重试时也需手动 | 成功后无自动跳转 | Import Drawer `onSuccess` 中自动 `navigate(/projects/:projectId/workspace/suite/:suiteId)`；错误时停留在 Drawer 显示详细错误 |
| 重复输入 | — | — | — | — |
| 重复确认 | Medium | 冲突策略选 "overwrite" 时**风险极高**（会覆盖已有同名 Case），但当前 Drawer 仅靠用户主动选，无明显风险提示 | 当前无警告 UI | 选 `overwrite` 时**弹出 Modal 二次确认**："将覆盖 N 条已有 Case，Case 名 / Path / 断言将被替换，是否继续？"；`skip` 不弹 |
| 迷路 | Medium | `preview_id` 不可用时，确认按钮 disabled 但提示"预览功能不可用"含糊，企业用户误以为是系统故障 | 错误文案未细化 | 错误信息分三档：① "后端未返回 preview_id（已尝试 N 次），请联系管理员"；② "OpenAPI 文档无 operation，已跳过"；③ "OpenAPI 版本不支持，仅支持 3.0 / 3.1" |
| 上下文丢失 | — | — | — | — |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.4-M1 | Medium | 重复点击 | 冲突策略 / 名称前缀每次都需重选 |
| 2.4-M2 | Medium | 重复跳转 | 导入完成需手动返回 Suite |
| 2.4-M3 | Medium | 重复确认 | `overwrite` 策略无二次确认，风险极高 |
| 2.4-M4 | Medium | 迷路 | `preview_id` 不可用时错误文案不清 |

---

## 2.5 Suite 列表 + Suite 详情

### 走查路径

```text
Suite 列表 → Suite 详情 → 浏览 Case / 添加 / 排序 / 移除 / 执行 / 导入 / 编辑 / 删除
  → Case 编辑器（行点击） → 返回
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复点击 | Medium | Suite 列表行点击"名称"才能进入详情，决策成本高（不知 Case 数 / 通过率） | 列表仅展示名称 / 描述 / 时间 | 列表行新增列："关联 Case 数 / 已启用数 / 最近通过率 / 最近执行时间"，点击即跳详情 |
| 重复跳转 | **High** | Suite 详情"执行 Suite"按钮**跳到 Run Center（`/workspace/run?scope=collection&scopeId=...`）**，Run Center 又打开 Run Drawer；同一执行动作**两次跳转**才到 Drawer | 当前实现是 navigate 到 Run Center，再由 Run Center 渲染 Drawer | Suite 详情"执行 Suite"按钮**直接打开 RunExecutionDrawer**（传入 `source.kind='suite'`），不跳转 Run Center；与 Header 快速执行共享同一 Drawer（详见 EXECUTION_CENTER.md §4.1） |
| 重复跳转 | Medium | Suite 详情行点击 Case 名 → Case 编辑器 → 保存 → 跳"返回 Suite 详情"或浏览器 Back，URL 仍带 `caseId`，**但 Case 列表 / 搜索状态已丢**（URL 不持久化列表查询条件） | Case 列表 URL 未带 `?search=&page=&method=` | Suite 详情进入 Case 编辑器时 URL 加 `?returnTo=suite&suiteId=...&from=case&caseId=...`；编辑器返回时回 Suite 详情，**保留原 Suite 列表查询条件**（Suite 列表查询条件入 URL Query） |
| 重复确认 | **High** | Suite 详情行内"**移除**"按钮 + Suite 详情"**删除 Suite**"按钮 + Case 列表行内"**删除 Case**"按钮，三者语义混淆：用户误以为"移除"即删除 Case | 行内按钮文案都是"删除"类危险词 | ① Suite 详情行内按钮文案改为 **"从 Suite 移除"**（不带"删除"字样），颜色为 link；**不显示**"删除 Case"按钮（删除需到 Case 列表）；② Case 列表行的"删除 Case"必须二次输入 Case 名确认；③ Suite 详情顶部"删除 Suite"保留 Popconfirm（已有） |
| 重复输入 | — | — | — | — |
| 迷路 | Medium | Suite 详情行内"上移 / 下移"每点一次都触发整页 loading，**Case 列表消失**，用户以为操作失败 | `reorderMutation.isPending` 让 Table 全表 loading | 行内 loading 仅锁定"上 / 下移"按钮（已实现），但 Table `loading={loading}` 让骨架闪烁 → 改为**不传 Table loading**，让按钮独立显示 loading 状态 |
| 上下文丢失 | **High** | Case 编辑器返回时，URL 中的 `?search=&method=&status=` **全部丢失**，返回的是 Case 列表空筛选全列表 | Case 列表 URL Query 未持久化 | Case 列表所有筛选 / 搜索 / 分页入 URL Query `?search=&method=&status=&page=&size=`；Case 详情带 `?from=case&caseId=...`；浏览器 Back 时从 URL 恢复 |
| 上下文丢失 | Medium | Suite 详情→Case 编辑器→保存→Case 列表（**跳错列表**），不是回到 Suite 详情 | 编辑器 onSuccess 跳默认 `/workspace/case` | 编辑器 onSuccess 读取 URL 的 `returnTo`，存在则跳回；不存在跳 Suite 详情（若 URL 含 suiteId）或 Case 列表 |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.5-H1 | **High** | 重复跳转 | Suite 详情"执行 Suite"跳 Run Center，两次跳转才到 Drawer |
| 2.5-H2 | **High** | 重复确认 | 行内"移除" vs "删除 Case" 语义混淆 |
| 2.5-H3 | **High** | 上下文丢失 | Case 编辑器返回丢失 Suite 上下文 + Case 列表搜索/筛选/分页 |
| 2.5-M1 | Medium | 重复点击 | Suite 列表缺 Case 数 / 通过率 / 最近执行时间 |
| 2.5-M2 | Medium | 重复跳转 | Case 编辑器保存后跳默认列表而非 Suite 详情 |
| 2.5-M3 | Medium | 迷路 | 排序时整页 loading，Case 列表闪烁 |

---

## 2.6 Case 编辑器 `/workspace/case/:caseId`

### 走查路径

```text
Case 列表 / Suite 详情 → Case 编辑器 → 编辑 / 保存 / 执行
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复点击 | Low | "保存"按钮 + "执行"按钮各一次；从 Suite 详情跳编辑器后想"再加一条"得手动"返回 → 新建 Case" | 保存后停留在编辑器 | 保存后 Toast 提示"已保存"，附"继续新建"按钮，点击带当前 Suite 的 `?suiteId=` 跳新建 Case |
| 重复跳转 | — | — | — | — |
| 重复确认 | — | — | — | — |
| 重复输入 | Low | Body 字段全为 textarea，无 JSON 校验 / 格式化按钮；写错的 JSON 在 Run 失败时才暴露 | 编辑器无 JSON 校验 | Body 编辑器右上角加"格式化 / 校验"按钮 + 错误高亮；切换 Body Type 时不清空已有内容 |
| 迷路 | Medium | 编辑器顶部只有"返回"按钮（回到 Case 列表默认页），从 Suite 详情跳入的用户必须记住"我从 Suite X 来的" | URL 无来源上下文 | PageHeader 标题旁显示"来自：[Suite 名]"，点击回 Suite 详情 |
| 上下文丢失 | **High** | 见 §2.5-H3（Case 列表 → 编辑器 → 返回丢失所有 URL Query） | 同 2.5-H3 | 同 2.5-H3 修复 |
| 上下文丢失 | Medium | 编辑器修改未保存时点 "执行"按钮 → 跳 Run Drawer → 未保存的修改**丢失** | "执行"按钮不触发保存 | "执行"按钮文案改为 **"保存并执行"**，点击先保存（已有 mutation）再开 Run Drawer；保留"保存"为主按钮，"保存并执行"为副按钮 |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.6-H1 | **High** | 上下文丢失 | Case 编辑器返回丢失列表搜索 / 筛选 / 分页（同 2.5-H3） |
| 2.6-M1 | Medium | 上下文丢失 | "执行"按钮丢失未保存的修改 |
| 2.6-M2 | Medium | 迷路 | 编辑器顶部无"来自 Suite"上下文提示 |
| 2.6-L1 | Low | 重复点击 | 保存后无"继续新建"快捷按钮 |
| 2.6-L2 | Low | 重复输入 | Body 字段缺 JSON 校验 |

---

## 2.7 Run Center `/workspace/run` + Run Drawer

### 走查路径

```text
Suite 详情"执行 Suite" / Case 编辑器"执行 Case" / Workspace Header"快速执行" / Run Center 入口
  → Run Drawer → 同步执行 → 自动跳 Report 详情
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复点击 | **High** | **四处执行入口**：① Suite 详情"执行 Suite"（跳 Run Center）；② Case 编辑器"执行 Case"（跳 Run Center）；③ Workspace Header "快速执行"（打开 Drawer）；④ Run Center 顶部表单（提交跳 Report）。**同一动作四种入口，参数路径不一致** | Suite/Case 编辑器按钮 navigate 到 Run Center，Header 直接打开 Drawer | **统一为 Drawer 入口**：① Suite 详情直接 `setRunDrawerSource({kind:'suite'})`；② Case 编辑器保存后直接 `setRunDrawerSource({kind:'case'})`；③ Header 直接 `setRunDrawerSource({kind:'project'})`；④ Run Center 顶部表单**移除**，仅保留"快速执行"按钮 + "最近 5 Run" |
| 重复跳转 | **High** | 见 2.7-H1（Suite/Case 入口跳 Run Center 是两次跳转） | 同上 | 同上 |
| 重复跳转 | Medium | Run Center "最近 5 Run" 区块与 Overview "最近 Run" + Report 列表完全重复 | 同一数据源三处展示 | Run Center 移除"最近 Run"区块，**只保留"快速执行"入口**；历史查询走 Report 列表 |
| 重复确认 | — | — | — | — |
| 重复输入 | Medium | Run Drawer 中 Environment 选择默认 Project 默认环境，但**用户必须手动点 Environment 下拉才能换**；同样 Variables 是只读，要改必须去 Environment 模块 | 默认值已是 defaultEnvironmentId，无明显标识 | Drawer 顶部"环境 Tag"显示当前选中环境 + Base URL，**点击展开**Variables 摘要；切换 Environment 下拉后顶部 Tag 实时更新 |
| 迷路 | Medium | Run Center 仍保留旧版表单，**与 Execution Drawer 并存**，新用户不知该用哪个 | Run Center 表单未删除 | 同 2.7-H1：Run Center 仅保留"快速执行"按钮 + "最近 5 Run" → 再简化为仅保留按钮，移除整个表单页 |
| 上下文丢失 | Medium | Run Drawer 提交成功跳 Report 详情，但 URL 中不携带 scope / environment / suite 上下文（虽然 Report 详情自带 runId，但用户从 Report 详情想"再跑一次"时丢失原 scope） | Drawer onSuccess 仅 navigate 到 reportId | Drawer onSuccess 跳 `/projects/:projectId/workspace/report/:runId?from=run&scope=&scopeId=&envId=`；Run 详情"再次执行"按钮读取 URL Query 预填 Drawer |
| 上下文丢失 | Medium | Run Drawer 打开不创建新 history 记录（`destroyOnClose`），但用户按浏览器 Back 时**Drawer 已关闭，但 history 也无变化**，出现"按 Back 无反应" | Drawer 是 Portal 渲染 | Drawer 关闭时同步 push 一条空 history，使 Back 键"关闭 Drawer"语义成立；或在 Route 层监听 ESC/Back 关闭 Drawer |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.7-H1 | **High** | 重复点击 + 重复跳转 | Run Center / Suite 详情 / Case 编辑器 / Header 四处执行入口不一致 |
| 2.7-H2 | **High** | 重复跳转 | Run Center 表单与 Execution Drawer 并存 |
| 2.7-M1 | Medium | 重复跳转 | Run Center "最近 5 Run" 与 Overview / Report 列表重复 |
| 2.7-M2 | Medium | 重复输入 | Run Drawer 环境切换后 Variables 不直观 |
| 2.7-M3 | Medium | 上下文丢失 | Drawer 关闭不创建 history，Back 键行为不一致 |
| 2.7-M4 | Medium | 上下文丢失 | Drawer 提交成功后未保留 scope/env 给 Report 详情 |

---

## 2.8 Report 模块 `/workspace/report` + Run 详情 + Result 详情

### 走查路径

```text
执行完成 / Workspace Header 最近 Run / Report 列表 → Run 详情（默认 Tab = 概览 / 失败原因）
  → Result 详情 → 失败项跳 Case 编辑器 → 返回
```

### 维度分析

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| 重复跳转 | **High** | **Report 列表与 Workspace Overview 的"最近 Run"区块完全重复**（同一 React Query `runs/summary` + 同一 RecentRunsPanel）：用户从 Overview → Run 详情 → 想看更多 → 再跳 Report 列表；Overview 顶部"最近 Run"和 Report 列表都展示 KPI + 5 条 Run | Overview 嵌入了 RecentRunsPanel | Overview "最近 Run"区块保留**仅 Top 3 + "查看全部 Report →"按钮**，完整列表（含筛选 / 搜索 / 分页）只在 Report 列表；明确职责划分（详见 NavigationUX §⑨ 9.3） |
| 重复跳转 | Medium | Run 详情"全部 Result Tab"显示 Case 状态表，点击进入 Result 详情，Result 详情"请求/响应/断言"Tab 内容**与 Run 详情 Tab 内联展示数据是同一份** | `results/{id}` API 返回 snapshot 同时被两个页面使用 | Run 详情"全部 Result Tab"精简为 Case 状态 + 耗时 + 错误摘要（不再内联 Request/Response），用户要看请求/响应细节必须点进 Result 详情；避免同数据两处展示 |
| 重复跳转 | Medium | Run 详情"概览 Tab"展示 KPI（总数 / 通过 / 失败 / 错误 / 通过率），**与 Report 列表顶部 KPI + Overview 顶部 KPI 三处展示同一份数据** | KPI 计算逻辑都基于 runs/summary | 移除 Run 详情顶部 KPI 卡（保留顶部 StatusBadge + 名称 + 环境），KPI 数据由 Report 列表 / Overview 单一权威展示 |
| 重复确认 | — | — | — | — |
| 重复输入 | — | — | — | — |
| 迷路 | Medium | 失败原因 Tab 列表行只显示 Case 名称 / Method / Path / 耗时；**expected / actual 折叠**，用户必须点进 Result 详情才能看断言细节 | `runs/{id}/failures` API 返回断言对比，UI 默认折叠 | 失败原因 Tab 行**默认展开** expected / actual（前 80 字符），企业用户一眼判断 |
| 迷路 | Medium | Run 详情 Tab 切换（概览 / 失败原因 / 全部 Result / 元信息）共 4 个 Tab，新用户不知从哪个开始 | 默认 Tab 已有规则但 UI 未强调 | Tab 默认值规则：存在 failed/error → "失败原因"；否则"概览"；**Tab 旁加"建议从此开始"小角标** |
| 上下文丢失 | **High** | Result 详情顶部"跳到 Case 编辑器"按钮跳 `/workspace/case/:caseId?from=report&runId=&resultId=`，**Case 编辑器 onSuccess 跳默认 `/workspace/case`（Case 列表）**，URL 中的 from / runId / resultId 全部丢失；用户回到 Result 详情需手动翻 Run 详情找 | Case 编辑器 onSuccess 跳固定 URL，不读 returnTo | Case 编辑器 onSuccess 优先读 URL Query 的 `returnTo`：存在则跳回该 URL；不存在按当前来源跳（从 Suite 跳则回 Suite，从 Case 列表跳则回列表并保留筛选） |
| 上下文丢失 | Medium | Result 详情 5 个 Tab（请求 / 响应 / 断言 / 错误 / 概览）状态存 URL Query `?tab=`；但**Result 详情从 Run 详情"全部 Result Tab"点击进入时丢失 Run 详情当前 Tab 状态**（如用户在 Run 详情"全部 Result Tab"看一半，点 Result 看完返回时 Run 详情切到"概览"） | Run 详情 Tab 状态写入 URL Query，但点进 Result 时可能因 React Query 重新挂载重置 | Result 详情 Back 时 `history.back()` 应恢复 Run 详情 Tab 状态；可借助 `sessionStorage["runDetailTab"]` 暂存 |

### 本页问题汇总

| ID | 等级 | 维度 | 摘要 |
|---|:-:|---|---|
| 2.8-H1 | **High** | 重复跳转 | Report 列表与 Overview "最近 Run" 区块完全重复 |
| 2.8-H2 | **High** | 上下文丢失 | Result 详情 → Case 编辑器 → 返回跳错页面，丢失 from 上下文 |
| 2.8-M1 | Medium | 重复跳转 | Run 详情"全部 Result Tab"与 Result 详情请求/响应 Tab 重复 |
| 2.8-M2 | Medium | 重复跳转 | Run 详情 KPI 与 Report 列表 / Overview KPI 三处重复 |
| 2.8-M3 | Medium | 迷路 | 失败原因 Tab 折叠 expected / actual |
| 2.8-M4 | Medium | 迷路 | Run 详情 4 个 Tab 无默认引导 |
| 2.8-M5 | Medium | 上下文丢失 | Result 详情返回时 Run 详情 Tab 状态丢失 |

---

# 3. 跨页面上下文问题

> 以下问题跨多个页面，单独成节。

### 3.1 H-Project 切换上下文不重置（**High**）

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| **上下文丢失** | **High** | 用户在 Project A 打开 Run 详情（URL `/projects/A/workspace/report/123`），切换到 Project B，**URL 仍含 A 的 runId**，Sider 显示 Project B 但页面是 Project A 的资源；用户看到错误内容或 404 | Project Switcher 仅切换 Sider 当前 Project，**未清理 URL 中的 runId / caseId / suiteId** | 实施 **NavigationUX §⑧ 三层策略**：① L2 列表页（Environment / Suite / Case 列表等）静默切换；② L3 详情页（Suite 详情 / Case 编辑）查询新 Project 是否存在同名对象，是则跳新对象详情，否则回列表；③ Run / Result 详情强制回新 Project 的 Report 列表。切换后**清理 URL 中残留的 entityId**，保留 `?tab=`（Tab 是页面级） |
| **迷路** | **High** | Project 切换后用户看不到明确反馈，不知"切了没" | Sider 高亮 + URL 变更不可见 | 切换 Project 时**显示 Loading 状态 + Toast**"已切换到 Project B" |

### 3.2 Case 编辑器返回路径不一致（**High**）

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| **上下文丢失** | **High** | 见 §2.6-H1 | 同上 | 同上 |

### 3.3 Drawer / Modal 的 Back 行为不一致（Medium）

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| **迷路** | Medium | Drawer 打开后**不创建新 history 记录**（destroyOnClose）；用户按浏览器 Back，Drawer 仍开着，但 history 已退回上一页，导致 Drawer 与页面内容**状态错位** | Drawer 是 Portal，React Router 监听不到 | Drawer 关闭时 push 一条 `?drawer=closed` 或在 Route 层监听 ESC/Back 关闭 Drawer；详见 NavigationUX §7.4 |

### 3.4 跳转时 URL Query 持久化不完整（Medium）

| 维度 | 等级 | 现象 | 根因 | 建议 |
|---|:-:|---|---|---|
| **上下文丢失** | Medium | Suite 列表 / Case 列表 / Report 列表的搜索 / 筛选 / 分页**部分入 URL Query，部分丢失**；Case 编辑器 / Suite 详情 / Run 详情 / Result 详情 之间的 from / suiteId / runId / resultId 传递不一致 | 各组件自行实现 URL 同步 | 全局统一规范（详见 NavigationUX §⑨ 与附录 B）：`?search=&page=&size=&method=&status=&tab=&scope=&scopeId=&from=&runId=&resultId=&returnTo=&drawer=`；提供 `useUrlQueryState` hook 统一读写 |

---

# 4. 修复优先级与工作量

## 4.1 P0 · High（必须修复）

| # | 问题 | 等级 | 涉及页面 | 改动量 | 实现位置 |
|---:|---|:-:|---|:-:|---|
| 1 | **H-Project 切换上下文不重置**（§3.1） | High | 全局 | 3 天 | `RouteGuards.tsx` + Sider Switcher + 各列表页 URL 清理 |
| 2 | **H-四处执行入口统一为 Drawer**（§2.7-H1） | High | Suite / Case / Run Center / Header | 2 天 | `RunExecutionDrawer` + Suite 详情按钮 + Case 编辑器按钮 + Workspace Header |
| 3 | **H-Report 列表与 Overview 重复**（§2.8-H1） | High | Overview / Report | 1 天 | Overview `RecentRunsPanel` 改为 Top 3 + "查看全部 →"按钮 |
| 4 | **H-Suite 详情"执行 Suite"直开 Drawer**（§2.5-H1） | High | Suite 详情 | 0.5 天 | `WorkspaceSuiteDetail.tsx` 替换 navigate 为 setDrawerSource |
| 5 | **H-Case 编辑器 returnTo 上下文**（§2.6-H1 / §2.8-H2） | High | Case 编辑器 | 1 天 | `WorkspaceCaseEditor.tsx` onSuccess 读取 returnTo |
| 6 | **H-行内"移除" vs "删除 Case" 文案分离**（§2.5-H2） | High | Suite 详情 / Case 列表 | 0.5 天 | `WorkspaceSuiteDetail.tsx` 行内按钮文案 / Case 列表二次确认 |

## 4.2 P1 · Medium（建议修复）

| # | 问题 | 等级 | 涉及页面 | 改动量 |
|---:|---|:-:|---|:-:|
| 7 | **M-Overview 引导动作化**（§2.2-M2） | Medium | Overview | 1 天 |
| 8 | **M-Environment Headers/Variables 键值表模式**（§2.3-M1） | Medium | Environment Drawer | 1 天 |
| 9 | **M-Environment 设默认后 Header 实时刷新**（§2.3-M3） | Medium | Environment 列表 / Header | 0.5 天 |
| 10 | **M-Environment 删除引用次数提示**（§2.3-M4） | Medium | Environment Drawer | 0.5 天 |
| 11 | **M-Import 冲突策略默认 skip + overwrite 二次确认**（§2.4-M1/M3） | Medium | Import Drawer | 0.5 天 |
| 12 | **M-Import 完成后自动回 Suite**（§2.4-M2） | Medium | Import Drawer | 0.5 天 |
| 13 | **M-Import 错误提示分档**（§2.4-M4） | Medium | Import Drawer | 0.5 天 |
| 14 | **M-Suite 列表加 Case 数 / 通过率**（§2.5-M1） | Medium | Suite 列表 | 0.5 天 |
| 15 | **M-Case 编辑器"保存并执行"**（§2.6-M1） | Medium | Case 编辑器 | 0.5 天 |
| 16 | **M-Case 编辑器"来自 Suite"提示**（§2.6-M2） | Medium | Case 编辑器 | 0.5 天 |
| 17 | **M-Run Drawer 切换环境时 Variables 摘要展开**（§2.7-M2） | Medium | Run Drawer | 1 天 |
| 18 | **M-Drawer / Back 行为一致**（§3.3） | Medium | 全局 Drawer | 1 天 |
| 19 | **M-URL Query 持久化全局规范**（§3.4） | Medium | 全局 | 1 天 |
| 20 | **M-Run 详情 Tab 精简 / KPI 合并**（§2.8-M1/M2） | Medium | Run 详情 | 1 天 |
| 21 | **M-失败原因 Tab 默认展开**（§2.8-M3） | Medium | Run 详情 | 0.5 天 |
| 22 | **M-Run 详情 Tab 默认值引导**（§2.8-M4） | Medium | Run 详情 | 0.5 天 |
| 23 | **M-Run Drawer 提交后 URL 携带 scope**（§2.7-M4） | Medium | Run Drawer / Run 详情 | 0.5 天 |
| 24 | **M-Overview 与 Run Center "最近 Run" 区块移除**（§2.2-M1 / §2.7-M1） | Medium | Overview / Run Center | 1 天 |
| 25 | **M-Suite 详情排序时 Table loading 收窄**（§2.5-M3） | Medium | Suite 详情 | 0.5 天 |

## 4.3 P2 · Low（体验打磨）

| # | 问题 | 等级 | 涉及页面 | 改动量 |
|---:|---|:-:|---|:-:|
| 26 | **L-登录落点判定 Recent Project**（§2.1-L1） | Low | Login | 0.5 天 |
| 27 | **L-登录失败文案分类**（§2.1-L2） | Low | Login | 0.5 天 |
| 28 | **L-Token 失效 returnTo 持久化**（§2.1-L2） | Low | 全局 RouteGuard | 0.5 天 |
| 29 | **L-Overview 资产计数徽标**（§2.2-L1） | Low | Overview | 0.5 天 |
| 30 | **L-Overview 引导完成后"下一步"自动消失**（§2.3-L1） | Low | Overview | 0.5 天 |
| 31 | **L-Case 编辑器"继续新建"**（§2.6-L1） | Low | Case 编辑器 | 0.5 天 |
| 32 | **L-Case 编辑器 Body JSON 校验**（§2.6-L2） | Low | Case 编辑器 | 1 天 |
| 33 | **L-Run Center 完全简化为入口按钮**（§2.7） | Low | Run Center | 0.5 天 |

---

# 5. 验收指标

> 修复后用以下指标验证改善程度。

| 指标 | 计算方式 | 当前 | 目标 |
|---|---|---|---|
| **主流程平均点击数** | 4 条 Journey 总点击数 / 4 | ~18 | ≤ 10 |
| **迷路事件率** | 用户 1 分钟内 Back / 面包屑 ≥ 3 次的会话占比 | 高 | ≤ 5% |
| **Project 切换上下文错位率** | 切换后 URL 残留旧 Project entityId 的比例 | 高 | **0%** |
| **Case 编辑器返回路径正确率** | 返回后停留在来源页的比例 | 低 | **100%** |
| **执行入口一致性** | Suite / Case / Project / Header 四个入口打开 Drawer 的行为一致 | 不一致 | **100%** |
| **Report 列表去重** | Overview / Report 列表 / Run Center "最近 Run" 三处去重 | 三处重复 | **一处权威** |
| **误删除率** | 用户误把"从 Suite 移除"当"删除 Case"的比例 | 中 | ≤ 1% |
| **Drawer Back 一致性** | Drawer 打开时 Back 键能关闭 Drawer | 不一致 | **100%** |
| **登录落点 Recent Project 命中率** | 老用户登录后直跳 Project 概览的比例 | 0% | ≥ 60% |
| **URL Query 可恢复率** | 浏览器 Back 后搜索 / 筛选 / Tab 完整恢复 | 部分 | **100%** |

---

# 6. 与既有文档的关联

| 既有文档 | 本 Review 中的引用 |
|---|---|
| `UX_REVIEW.md` H1-H3 / M1-M10 / L1-L7 | §2.5-H3 / §3.1（Project 切换 URL）；§2.7-H1（执行入口）；§2.8-H1（Report 列表与 Overview 重复） |
| `NavigationUX.md` §⑧ Project Switch | §3.1 修复策略 |
| `NavigationUX.md` §7.4 Drawer / Modal Back | §3.3 修复策略 |
| `NavigationUX.md` 附录 B URL Query 命名 | §3.4 修复策略 |
| `NavigationUX.md` §⑬ Token 失效 returnTo | §2.1-L2 修复策略 |
| `EXECUTION_CENTER.md` §4 入口与触发 | §2.7-H1 修复策略（统一 Drawer） |
| `REPORT_CENTER.md` §5-6 Tabs | §2.8 修复策略（精简重复 Tab） |
| `Journey.md` 4 条 Journey 步骤分析 | 与本 Review 互为表里：Journey 写"做什么"，Review 写"哪里卡" |

---

# 7. 约束再确认

- ✅ 不新增任何后端 API
- ✅ 不新增任何数据库表 / 字段 / 迁移
- ✅ 不新增任何功能模块
- ✅ 所有建议**仅优化已有流程**：① 默认值 / 预填；② Drawer / 按钮 / Tab 的入口合并；③ URL Query 持久化（已有 NavigationUX 附录 B 规范）；④ LocalStorage Recent Project；⑤ 文案与反馈优化；⑥ 二次确认策略优化

---

> **版本**：v1.0 · 2026-07-16
> **作者**：资深产品经理（测试平台方向）
> **范围**：MVP 阶段全流程；定时 / CI / 通知 / 协作场景不在本期范围
> **配套使用**：先读 `Journey.md`（看用户视角），再读本 `WorkflowReview.md`（看问题视角），最后读 `NavigationUX.md`（看修复策略）