# API 自动化测试平台 · User Journey 优化方案

> 文档类型：产品 Journey 设计（产品经理视角）
> 适用范围：现有 API 自动化测试平台 MVP
> 设计阶段：先设计，不涉及代码实现
> 配套：`PRD.md`（产品定位）、`INFORMATION_ARCHITECTURE.md`（信息架构）、`NavigationUX.md`（导航规范）、`PROJECT_WORKSPACE.md`（工作空间）
> **硬约束：不新增任何 API、不新增任何数据库表、不新增功能模块，仅优化已有流程的组织方式、默认行为、跳转关系与上下文复用**

---

## 0. 设计原则（贯穿 4 条 Journey）

1. **三层心智模型**：平台层（Dashboard / 项目列表 / 系统管理） → 项目层（Workspace 八大模块） → 详情层（Suite / Case / Run / Result）。每条 Journey 必须明确用户当前在哪一层。
2. **目标唯一性**：每个 Journey 仅对应一种"用户角色 × 场景"，避免混线。
3. **每一步五要素**：**用户目标 / 当前页面 / 下一步 / 阻碍 / 优化建议**，缺一不可。
4. **闭环可验证**：每条 Journey 结尾必须有"完成判定"，用于产品验收。
5. **拒绝"虚功能"**：所有优化建议必须落在已存在的 API、字段、组件或前端路由 / Query / LocalStorage 上。
6. **上下文不丢**：Project / Suite / Case / Run / Tab / 搜索 / 分页全部进 URL Query；Recent Project 进 LocalStorage。
7. **下一步永远可达**：每一步都给出"下一步"和"卡住时的兜底路径"，不出现"用户不知道去哪"的死局。

---

## 1. 用户角色与场景矩阵

| 用户 | 场景 | 对应 Journey |
|---|---|---|
| 新用户 | 从零搭建第一个 Project 并跑通首个 Suite | **① 新用户 Journey** |
| 老用户 | 已有 Project / Suite / Case 资产，需维护并迭代 | **② 老用户 Journey** |
| 测试工程师 | 上线前 / 每日对全量用例做回归 | **③ 日常 Regression Journey** |
| 测试工程师 | 上线前 / 改动核心接口后做关键路径冒烟 | **④ Smoke Test Journey** |

---

# ① 新用户 Journey

> **角色**：新注册用户 / 第一次使用平台的测试工程师
> **终点**：跑通第一条 Suite，生成第一条 Run 并看到 Report
> **预设**：账号已由管理员开通，密码已修改，平台已有 ≥ 1 个 Project（已由 Admin 预先建好或由用户本人在 Dashboard 新建）

## 1.1 Journey 主路径

```text
登录 → Dashboard（Recent Project 区） → Project 概览（Workspace Overview）
  → 环境管理（创建 + 设默认） → Suite 列表（创建 Suite） → Suite 详情
  → OpenAPI Import 或 新建 Case → Workspace Header "快速执行"
  → Run Drawer（预填 Suite / 默认环境） → Run 报告详情
  → 失败原因 → 单条 Result → 跳 Case 编辑器 → 保存并执行 → 新 Run 报告
```

## 1.2 每一步分析

### 步骤 1 · 登录

| 要素 | 内容 |
|---|---|
| **用户目标** | 进入平台，看到自己"该做什么" |
| **当前页面** | `/login`（登录页） |
| **下一步** | 输入邮箱 + 密码 → 登录成功 → 进入 Dashboard（或 Recent Project 概览） |
| **阻碍** | ① 没有"忘记密码"路径（超纲，不优化）；② 登录成功后落点是 Dashboard，新用户对下一步无感；③ 不知道"我的第一个 Project 在哪里" |
| **优化建议** | ① 登录成功后的落点判定：若 LocalStorage `app.recentProjects` 为空 → 直接落 Dashboard，并展示**首登引导卡**"欢迎使用 API 自动化平台，下面 3 步跑通第一条测试：① 进入 Project ② 创建环境 ③ 执行 Suite"，每一步给"去创建"按钮；② 登录失败时区分"账号禁用 / 密码错误 / 请求过多"三种文案，不只说"登录失败" |

---

### 步骤 2 · 进入 Dashboard

| 要素 | 内容 |
|---|---|
| **用户目标** | 找到目标 Project，开始配置 |
| **当前页面** | `/dashboard`（Dashboard） |
| **下一步** | 点击 Recent Project 卡片 / 进入项目列表 → Project 概览 |
| **阻碍** | ① 新用户无 Recent Project，Dashboard 显示空态；② 项目列表无关键词搜索提示；③ 新用户不知道"先建环境还是先建 Suite" |
| **优化建议** | ① Recent Project 空态替换为**首登引导卡**（与步骤 1 联动），文案"去创建你的第一个 Project"，按钮直达 Project 新建 Drawer；② 项目列表顶部展示提示条"搜索 Project 名 / 描述"，引导用户使用搜索；③ 当 Recent Project 为空时，Dashboard 隐藏"最近 Run / 最近 Report"两个区，避免空态干扰 |

---

### 步骤 3 · 新建 / 选择 Project

| 要素 | 内容 |
|---|---|
| **用户目标** | 进入一个 Project 上下文 |
| **当前页面** | Dashboard 或 `/projects`（项目列表） |
| **下一步** | 新建 Project → 自动跳 Workspace Overview；或选择已有 Project → Workspace Overview |
| **阻碍** | ① 新建表单字段过多（名称 + 描述），新用户不知道描述写什么；② 新建成功后未立即提供"下一步"引导 |
| **优化建议** | ① Project 新建 Drawer **默认收起描述字段**，鼠标悬停"?"图标给出占位文案"如：用户中心对外 API"；② 新建成功后自动进入 Workspace Overview，并在 Overview 顶部展示"下一步"卡片："你的项目还没有环境，去创建 →"，点击直接打开 Environment Drawer；③ 项目列表行直接展示 Owner + 创建时间 + 上次访问时间（如有 Recent），不必进入概览也能判断 |

---

### 步骤 4 · 进入 Workspace Overview

| 要素 | 内容 |
|---|---|
| **用户目标** | 看到当前 Project 的"健康度 + 下一步" |
| **当前页面** | `/projects/:projectId/workspace/overview` |
| **下一步** | 点击 Overview 上的"创建环境"引导卡 → Workspace Environment 模块 |
| **阻碍** | ① Overview 资产计数（环境/Suite/Case 数量）为 0 时没有视觉强调；② Overview 没有"主操作"按钮，用户不知该做什么 |
| **优化建议** | ① Overview 顶部加"资产配置完整度"徽标，缺失任一项时显示红点；② 缺失环境时，Overview 顶部主操作按钮显示 **"创建环境"**；缺失 Suite 时显示 **"创建 Suite"**；缺失 Case 时显示 **"导入或创建 Case"**；按钮直接打开对应 Drawer，无需跳转；③ 右侧 Context Panel 显示"快速创建"区块，与顶部主操作一致 |

---

### 步骤 5 · 创建环境

| 要素 | 内容 |
|---|---|
| **用户目标** | 配置 Base URL、Headers、Variables，并把它设为默认 |
| **当前页面** | `/projects/:projectId/workspace/environment` |
| **下一步** | 打开 Environment Drawer → 填表 → 保存 → 自动跳"创建 Suite"引导 |
| **阻碍** | ① Headers / Variables 在 JSON 模式下编辑，新用户不友好；② "设为默认环境"是**额外一次点击**，且默认环境不可见后果不直观；③ 环境列表无示例 |
| **优化建议** | ① Environment Drawer 中 Headers / Variables 默认**键值表模式**（key / value 两列，"+"按钮新增行），保留"切换为 JSON"按钮供高级用户；② 新建环境 Drawer **默认勾选"设为默认环境"**，并加灰色提示"第一个环境将自动成为默认环境"；③ 切换 Project 时若当前 Project 无默认环境，Workspace Header 红点提醒 + Drawer 引导"指定一个环境作为默认" |

---

### 步骤 6 · 创建 Suite

| 要素 | 内容 |
|---|---|
| **用户目标** | 创建一个分组，准备放用例 |
| **当前页面** | Workspace Environment → Workspace Suite 列表 |
| **下一步** | 打开 Suite Drawer → 填名称 / 描述 → 保存 → 跳 Suite 详情 |
| **阻碍** | ① 新用户不知道 Suite 是"业务场景"还是"回归范围"；② 名称填好后无即时引导"接下来做什么" |
| **优化建议** | ① Suite Drawer 描述字段占位文案给出示例："如：用户登录冒烟 / 订单核心回归"；② 保存成功后**不弹 Toast**，而是直接跳 Suite 详情，并在 Suite 详情顶部展示空态卡"这个 Suite 还没有用例，从 OpenAPI 导入 或 新建 Case 开始" |

---

### 步骤 7 · 准备 API Case（Import 或 新建）

| 要素 | 内容 |
|---|---|
| **用户目标** | 给 Suite 添加用例 |
| **当前页面** | `/projects/:projectId/workspace/suite/:suiteId` |
| **下一步** | 选 **Import OpenAPI** 或 **新建 Case** |
| **阻碍** | ① OpenAPI Import 是"上下文动作"，没有放在一级菜单，新用户找不到；② 新建 Case 时必须指定 Suite，从 Project 维度进入时无 Suite 上下文 |
| **优化建议** | ① Suite 详情空态卡上明确两个按钮："导入 OpenAPI"（主操作）/ "新建 Case"（次操作），按钮各自带说明 tooltip；② OpenAPI Import Drawer 流程**默认冲突策略 = skip**（不必用户选），名称前缀可空；导入完成后**自动跳回 Suite 详情**，不必手动返回；③ 新建 Case Drawer 中 "Method / Path / 断言模板" 给出最常见示例（GET /users、POST /login），降低首次编写门槛 |

---

### 步骤 8 · 发起执行

| 要素 | 内容 |
|---|---|
| **用户目标** | 把当前 Suite 跑起来 |
| **当前页面** | Suite 详情 / Workspace Header / Run 模块 |
| **下一步** | 点击 **Workspace Header 的"快速执行"** 按钮 → Run Drawer 打开 |
| **阻碍** | ① 执行入口分散：Suite 详情、Case 编辑器、Run 模块、Header 都有，新用户不知道哪个"对"；② Run Drawer 默认值不清晰，用户可能错选环境 |
| **优化建议** | ① Workspace Header 的"快速执行"按钮是**默认主入口**：点击后 Drawer 顶部展示 **范围 Tag + 环境 Tag + 范围内启用 Case 数 Tag**，用户一眼看清"将要执行什么 / 在哪执行 / 多少条"；② Drawer 默认 **scope=project**，从 Suite 详情发起时自动改为 **scope=collection + suiteId**；环境自动选 Project 默认环境；③ 发起前必做前置校验：无默认环境 → Drawer 顶部红条 + 跳转按钮；Suite 为空 → Drawer 顶部红条 + "去添加 Case" 按钮 |

---

### 步骤 9 · 同步执行与跳转 Report

| 要素 | 内容 |
|---|---|
| **用户目标** | 看到执行结果 |
| **当前页面** | Run Drawer → Loading → Report 详情 |
| **下一步** | Run 详情默认 Tab = **概览**（看通过率）→ 切换到 **失败原因** Tab |
| **阻碍** | ① 同步执行时按钮文案不明确，用户可能误以为卡死；② 执行成功跳转 Report 详情后默认 Tab = 概览，但用户更关心"哪里失败" |
| **优化建议** | ① Run Drawer 提交后按钮文案变为"执行中…（请勿重复提交）"并禁用；② Run 详情 **默认 Tab = 失败原因**（当存在 failed / error 时），否则默认 Tab = 概览；③ Run 详情顶部展示一个**KPI 条**：总数 / 通过 / 失败 / 错误 / 通过率 / 耗时，颜色与 StatusTags 一致 |

---

### 步骤 10 · 查看失败 / 修正 / 再执行

| 要素 | 内容 |
|---|---|
| **用户目标** | 定位失败原因，修正后立即再跑 |
| **当前页面** | Run 详情 → Result 详情 → Case 编辑器 |
| **下一步** | 失败项一键跳 Result 详情 → "查看 Case 定义并修改" → 保存 → "保存并执行" → 新 Run |
| **阻碍** | ① Result 详情与 Case 编辑器间需手动复制参数；② 修改保存后还要回到 Suite 详情 / 再点执行，步骤多 |
| **优化建议** | ① Result 详情顶部按钮 **"修改并再执行"**：一键跳 Case 编辑器（URL 带 `?from=report&runId=&resultId=`），并把失败断言定位到编辑器锚点；② Case 编辑器保存按钮旁加 **"保存并执行"** 副按钮（主按钮仍是"保存"），点击后 Drawer 预填 scope=case + 当前 caseId + 默认环境；③ 新 Run 完成后**自动跳转新 Run 详情**，实现"修 → 跑 → 看结果" 1 步闭环 |

---

### 步骤 11 · 完成判定

| 要素 | 内容 |
|---|---|
| **用户目标** | 知道"完成"了 |
| **当前页面** | 新 Run 报告详情 |
| **下一步** | 看到通过率 100%（或失败已定位），关闭 Journey |
| **阻碍** | 没有"完成反馈"，用户不知道"接下来该做什么" |
| **优化建议** | ① 通过率 = 100% 时，Run 详情顶部展示绿色 Banner"全部通过 ✓"，并给"返回 Suite 详情 / 返回 Dashboard"两个按钮；② 通过率 < 100% 时，失败原因 Tab 顶部展示红条"+N 条失败待修复"，点击直达第一条失败项 |

---

# ② 老用户 Journey

> **角色**：已在平台维护多个 Project 的测试工程师
> **典型动作**：① 日常维护资产（新增 / 修改 / 删除 Case、调整 Suite 顺序、修改环境）；② 修复某个失败用例；③ 在 Project 间切换
> **预设**：账号 ≥ 1 个 Project、≥ 1 个 Suite、≥ 1 个已启用 Case

## 2.1 Journey 主路径

```text
登录 → Dashboard（Recent Project） → 目标 Project 概览
  → （场景 A：新增 Case）Suite 详情 → 新建 Case → 保存 → 留在 Case 编辑器
  → （场景 B：修复失败）测试报告 → Run 详情 → 失败项 → Result → 修改 Case
  → （场景 C：调整 Suite）Suite 详情 → 调整顺序 / 启用禁用 / 移除关联
  → （场景 D：切 Project）Workspace Header Project Switcher → 新 Project 同模块
```

## 2.2 每一步分析

### 步骤 1 · 登录与默认落点

| 要素 | 内容 |
|---|---|
| **用户目标** | 快速回到"上次干活的地方" |
| **当前页面** | `/login` |
| **下一步** | 登录成功 → 直接落 **最近 Project 概览**（≤ 7 天内） 或 Dashboard |
| **阻碍** | 老用户每次都要 Dashboard → Project 列表 → 选 Project → 概览，4 步冗余 |
| **优化建议** | ① 登录成功判断：LocalStorage `app.recentProjects` 第一项 ≤ 7 天 → 直接跳该 Project 概览；② 若 5 个 Recent Project 中有 **今日未访问过** 的 Project，Dashboard 顶部加 Banner"你最近 5 个 Project 中有 X 个今天还没看过"；③ Token 失效时优先尝试 Refresh Token，刷新失败再跳登录并通过 sessionStorage 保存 returnTo |

---

### 步骤 2 · Dashboard 的"今日待办"

| 要素 | 内容 |
|---|---|
| **用户目标** | 看到"今天哪些 Project 有失败 / 待处理" |
| **当前页面** | `/dashboard` |
| **下一步** | 点击 Recent Project 卡片 / 查看 Recent Runs 中失败项 |
| **阻碍** | ① Dashboard 上"Recent Runs / Recent Reports"是按时间排，老用户看不出"哪些失败需要我修"；② 无 Project 维度的"上次访问时间"，老用户不确定"哪些 Project 我该回头看" |
| **优化建议** | ① Dashboard Recent Runs **按 status 优先排序**：failed / error 置顶，passed 折叠；② Recent Project 卡片**右侧加"上次访问时间"**（如"3 小时前"），并对 **超过 7 天未访问** 的 Project 加灰底标记；③ 若用户超 24 小时未访问某 Project，Recent 卡片上加"⚠ 待跟进"徽标（基于 Summary 接口的 last_run_at） |

---

### 步骤 3 · 场景 A · 新增 Case

| 要素 | 内容 |
|---|---|
| **用户目标** | 在已有 Suite 中加 1 条用例 |
| **当前页面** | Suite 详情 或 Case 列表 |
| **下一步** | 新建 Case Drawer → 保存 → 留在 Case 编辑器 → 可选"保存并执行" |
| **阻碍** | ① Case 列表的"新建"按钮不强制选 Suite，老用户可能漏选；② 保存后默认停留在编辑器，老用户想"再加一条"得手动点"新建" |
| **优化建议** | ① Suite 详情点"新建 Case" → Drawer **自动带入 suiteId**，不必用户再选；② 从 Case 列表点"新建" → Drawer 顶部 Suite 选择器**优先列出当前用户最近用过的 5 个 Suite**（基于前端埋点）；③ 保存后 Toast 提示"已创建 [Case 名]"，并附"继续新建"按钮，1 步再建一条 |

---

### 步骤 4 · 场景 B · 修复失败用例

| 要素 | 内容 |
|---|---|
| **用户目标** | 找到最近失败 → 定位原因 → 修正 → 再跑 |
| **当前页面** | 测试报告 → Run 详情 |
| **下一步** | 失败项 → Result 详情 → "修改并再执行" → Case 编辑器 → 保存并执行 → 新 Run |
| **阻碍** | ① Run 列表筛选只有状态过滤，老用户要在"全部 Run"里挑出"今天失败的"；② 修改 Case 后还得回到执行中心再选 scope=case，老用户重复操作 |
| **优化建议** | ① Run 列表增加**快捷筛选**："今日 / 本周 / 仅失败"3 个 Tab，写入 URL Query `?range=today`；② Result 详情"修改并再执行"按钮**直接打开 Run Drawer**（不跳到 Run 中心），预填 scope=case + 当前 caseId + 当前 environmentId，节省 2 步；③ 新 Run 完成后**自动跳新 Run 详情**（与新用户 Journey 一致） |

---

### 步骤 5 · 场景 C · 调整 Suite（顺序 / 启用 / 移除关联）

| 要素 | 内容 |
|---|---|
| **用户目标** | 整理 Suite 内用例顺序，禁用 / 启用部分 |
| **当前页面** | Suite 详情 |
| **下一步** | 拖拽排序 / 切换启用状态 / 移除关联 / 添加已有 Case |
| **阻碍** | ① "从 Suite 移除"与"删除 Case"在列表行同区域，老用户易误点；② 拖拽排序后未自动失效 Suite 列表缓存 |
| **优化建议** | ① Suite 详情行操作分两区：**左侧主操作**（"在 Suite 中移除"，文案不带"删除"字样）+ **右侧次操作**（"查看 Case 定义 / 执行此 Case"），**完全不显示**"删除 Case"按钮（删除需在 Case 列表完成）；② 任何 Suite 内写操作（排序 / 启用 / 移除 / 添加）后，**自动失效** `["projects", projectId, "suites"]` 和 `["projects", projectId, "runs", "summary"]` 缓存，确保下次 Run 摘要即时更新；③ 拖拽排序**保存即生效**（PATCH 现有顺序接口），不弹"保存"按钮 |

---

### 步骤 6 · 场景 D · 切换 Project

| 要素 | 内容 |
|---|---|
| **用户目标** | 从 Project A 切到 Project B，**保留模块语义** |
| **当前页面** | Project A 任意页面 |
| **下一步** | 点击 Workspace Header Project Switcher → 选 Project B |
| **阻碍** | ① 当前实现切 Project 后 URL 中 runId / caseId 不清理，老用户被带到 404；② 表单有未保存内容时直接切走，老用户丢内容 |
| **优化建议** | ① 实施 **NavigationUX §⑧ 三层策略**：L2 列表页静默切换（保留模块）、L3 详情页查询同名对象后切换或不成功则回概览、Run / Result 强制回 Project B 报告列表；② 切换前若表单 dirty → Popconfirm；若 Run 执行中 → Modal 警告；③ 切换完成后立即清理 URL 中的 runId / caseId / suiteId，滚动位置重置，Drawer / Modal 强制关闭（详见 NavigationUX §8.5） |

---

### 步骤 7 · Workspace 内"我的最近操作"

| 要素 | 内容 |
|---|---|
| **用户目标** | 不离开当前 Project 就能回到"昨天 / 上次执行" |
| **当前页面** | 任意 Workspace 模块 |
| **下一步** | 顶部 Header "最近执行"按钮 → Run 详情 |
| **阻碍** | ① 老用户常需要"对比上次 vs 这次"，但只能在 Report 列表翻；② 没有"最近失败的 Case"快捷入口 |
| **优化建议** | ① Workspace Header 增加 **"最近执行"** 按钮，下拉展示 Project 最近 5 条 Run（来自 `runs?limit=5`），点击直达 Run 详情；② 右侧 Context Panel 增加 **"最近失败"** 区块，展示最近 1 次 Run 的失败项 Top 3，点击直达 Result 详情；③ 在 Suite 详情 Case 列表上方增加 **"上次执行"** 标签，显示该 Suite 最近 1 次 Run 的通过率（来自 `runs?limit=1` 过滤该 scope） |

---

### 步骤 8 · 环境切换 / 维护

| 要素 | 内容 |
|---|---|
| **用户目标** | 切到测试环境 / 预发环境执行 |
| **当前页面** | Environment 模块 / Run Drawer |
| **下一步** | Run Drawer 切换 environmentId → 发起执行 |
| **阻碍** | ① 切换环境不会同步刷新 Variables 缓存，老用户误以为"切完就生效"；② 默认环境被其他用户改后，本地缓存仍是旧值 |
| **优化建议** | ① Run Drawer 顶部"环境 Tag"显示当前选中环境的 Base URL，**点击展开**该环境的 Headers / Variables 摘要（只读，前端从已有列表接口拉取），让用户确认变量；② Run Drawer 切换环境时**主动 invalidate** `["projects", projectId, "environments"]` 缓存，确保 Variables 最新；③ Workspace Header 的默认环境徽标**实时刷新**：环境管理中"设为默认"成功后，Header 立即更新 |

---

### 步骤 9 · 跨 Project 资产复用

| 要素 | 内容 |
|---|---|
| **用户目标** | 把 Project A 的某个 Suite / Case 复制到 Project B |
| **当前页面** | Project A Suite / Case 详情 |
| **下一步** | ❌ 平台无"复制 Case"功能 |
| **阻碍** | 当前 API 不支持跨 Project 复制，老用户必须手工新建 |
| **优化建议** | ⚠️ **不新增功能**，仅在 UI 上**明确告知**当前限制：在 Case 详情 / Suite 详情"复制"按钮位置放 **"暂不支持复制，请到目标 Project 手工新建"** 的 Popover，**不显示虚假的复制按钮**（避免假功能产生不信任）；Project Switch 行为遵循 NavigationUX §8.2 策略 B → C |

---

### 步骤 10 · 完成判定

| 要素 | 内容 |
|---|---|
| **用户目标** | 知道"今天该做的做完了" |
| **当前页面** | Dashboard |
| **下一步** | 看到 Recent Runs 全绿，关闭 Journey |
| **阻碍** | Dashboard 没有"今日完成 / 今日待办"统计，老用户要逐个 Project 看 |
| **优化建议** | ① Dashboard 顶部 KPI 加 **"今日失败"**（汇总自 5 个 Recent Project 的 last_run_at = 今日且 status ∈ {failed, error} 的 Run 数）；② 5 个 Recent Project 全部通过时 Dashboard 顶部显示**庆祝条**"今日全部 Project 通过 ✓" |

---

# ③ 日常 Regression Journey

> **角色**：测试工程师，每日上线前 / 提测前跑全量回归
> **频率**：1 次 / 日
> **终点**：得到一份 Project 维度的回归 Run，并通过率、失败定位、修复闭环
> **预设**：每个 Project 至少有 1 个 Suite（通常是"全量回归"Suite），默认环境已配置

## 3.1 Journey 主路径

```text
登录 → Dashboard → Recent Project / Project 列表 → Project 概览
  → Workspace Header "快速执行"（scope=project，预填默认环境）
  → Run Drawer（确认范围 / 环境） → 同步执行 → 自动跳 Run 报告详情
  → 概览 Tab（看通过率） → 失败原因 Tab（按 status 过滤）
  → 失败项 → Result 详情 → 修改 Case → 保存并执行 → 新 Run
  → 全部通过 / 仍有失败 → 测试报告列表（看历史趋势）
```

## 3.2 每一步分析

### 步骤 1 · 进入 Dashboard

| 要素 | 内容 |
|---|---|
| **用户目标** | 1 步进入"今天要回归的 Project" |
| **当前页面** | `/dashboard` |
| **下一步** | 点击 Recent Project 卡片 |
| **阻碍** | ① 老用户有 5+ 个 Project，"今天要回归的"不一定排第一；② Dashboard 没有"上次回归时间"概念 |
| **优化建议** | ① Recent Project 卡片**附带"上次回归时间"**（基于 Summary 接口 last_run_at，若 ≤ 24h 加"今日已回归 ✓"标记）；② 用户在 Workspace Header Project Switcher 中，可对每个 Project 标记**"今日已回归"**（前端 LocalStorage，仅自己可见），Dashboard 优先展示"今日未回归"的 Recent Project |

---

### 步骤 2 · 发起 Project 全量回归

| 要素 | 内容 |
|---|---|
| **用户目标** | 把整个 Project 的启用用例全部跑一遍 |
| **当前页面** | Project 概览 / Workspace Header |
| **下一步** | 点击 **"快速执行"** → Run Drawer 打开 |
| **阻碍** | ① "全量回归"Suite 不一定存在，老用户每次都要确认范围；② Run Drawer 的 scope 选项让老用户犹豫（Case / Suite / Project） |
| **优化建议** | ① 鼓励 Project 内维护一个名为 **"全量回归"** 的 Suite（命名约定，**不强制**）：Run Drawer scope = suite 时**自动优先**列出名为"全量回归 / Regression / All"的 Suite；② Run Drawer 顶部展示 **3 个 scope Tab**："单 Case / Suite / Project"，每个 Tab 给出简短说明（如"Project：执行当前 Project 全部启用用例"），减少选择成本；③ Workspace Header "快速执行"按钮的 **默认 scope = project**（与 NavigationUX §11 一致），老用户每日回归不必选 |

---

### 步骤 3 · 选择环境

| 要素 | 内容 |
|---|---|
| **用户目标** | 在"测试环境"而非"开发环境"跑 |
| **当前页面** | Run Drawer |
| **下一步** | 选择 environmentId（默认 = Project 默认环境） |
| **阻碍** | ① 默认环境是"测试"还是"预发"由环境管理决定，老用户执行前要核对；② 环境 Variables 不会自动注入预览，老用户不知道请求会带什么变量 |
| **优化建议** | ① Run Drawer 顶部"环境 Tag"展示 **Base URL**，点击展开 Headers / Variables 摘要（只读，不修改）；② 切换环境时**主动拉取**最新 Variables 缓存；③ 环境列表行**显示 Base URL + 最近一次使用时间**，老用户凭直觉判断"哪个是测试环境" |

---

### 步骤 4 · 执行与等待

| 要素 | 内容 |
|---|---|
| **用户目标** | 同步执行所有 Case |
| **当前页面** | Run Drawer（Loading） |
| **下一步** | 等待接口返回 → 自动跳 Run 报告详情 |
| **阻碍** | ① 同步执行时无任何反馈，老用户以为卡死；② 长链路 Suite（100+ Case）执行时间长，老用户无法打断 |
| **优化建议** | ① Run Drawer 提交后按钮变"执行中…（请勿重复提交）"，并显示**已完成 X / 总数 N**（前端通过 PATCH 现有 status 接口或 SSE 不在范围内，**仅前端拉取 result 进度条不可行**，故**只显示"执行中"文案**，不伪造进度）；② 执行失败 / 超时时 Drawer 顶部红条 + 错误码 + "重试"按钮；③ 若执行时间超过 60 秒，Drawer 自动展示提示"用例较多，请耐心等待" |

---

### 步骤 5 · 进入 Run 报告

| 要素 | 内容 |
|---|---|
| **用户目标** | 1 秒看到"通过率 / 失败数" |
| **当前页面** | `/projects/:projectId/workspace/report/:runId` |
| **下一步** | 默认 Tab = 概览 → 失败原因 |
| **阻碍** | ① Run 报告 KPI 与 Overview / Report 列表 KPI 重复，老用户信息冗余；② 通过率计算逻辑不直观 |
| **优化建议** | ① Run 详情顶部 KPI 条：总数 / 通过 / 失败 / 错误 / 跳过 / 通过率 / 耗时，**与 StatusTags 颜色一致**；② 默认 Tab 规则：存在 failed / error → **失败原因**；否则 → **概览**；③ 通过率分子定义在 KPI 旁 tooltip：`passed / (total - skipped)`，避免歧义 |

---

### 步骤 6 · 失败原因定位

| 要素 | 内容 |
|---|---|
| **用户目标** | 找到"哪条用例、哪个断言"失败 |
| **当前页面** | Run 详情 → 失败原因 Tab |
| **下一步** | 失败行可点击 → Result 详情 |
| **阻碍** | ① 失败行字段少，老用户必须点进 Result 才能看到断言；② 多条失败时无法按"失败类型"分组（断言 / 超时 / 连接错误） |
| **优化建议** | ① 失败原因 Tab 列表行**内联显示**断言类型 / expected / actual（折叠态显示前 80 字符），不必点进 Result；② 失败原因 Tab 顶部 **3 个二级 Tab**："断言失败 / 执行错误 / 超时"，点击过滤；③ 失败项展示 error_code，老用户判断是网络问题还是断言问题 |

---

### 步骤 7 · 修复失败用例

| 要素 | 内容 |
|---|---|
| **用户目标** | 修正配置后立即再跑 |
| **当前页面** | Result 详情 |
| **下一步** | "修改并再执行"按钮 → Case 编辑器 → 保存并执行 |
| **阻碍** | ① Result 详情 → Case 编辑器间上下文易丢；② 修复后要重选 scope，老用户易漏 |
| **优化建议** | ① Result 详情"修改并再执行"按钮 1 步完成"跳编辑器 + 预填执行"，URL 带 `?from=report&runId=&resultId=`；② 编辑器保存后**保留来源 URL**（`?returnTo=`），返回时回到原 Result；③ Case 编辑器右侧增加 **"原失败断言"** 折叠区（来自 URL Query 的 resultId），老用户对照修正 |

---

### 步骤 8 · 历史趋势对比

| 要素 | 内容 |
|---|---|
| **用户目标** | 看"今天 vs 昨天"的通过率变化 |
| **当前页面** | `/projects/:projectId/workspace/report`（Report 列表） |
| **下一步** | 看列表中近 5 次 Run 的通过率与耗时 |
| **阻碍** | ① 报告列表只展示状态 / 通过率，不展示"环比昨日"；② 跨 Suite / 跨 scope 的 Run 在同一列表，老用户难以定位"Project 全量"的 Run |
| **优化建议** | ① Report 列表行增加 **"上次通过率"** 列（基于列表中相邻上一条 Run），并显示 ↑/↓ 箭头；② Report 列表顶部增加 scope 筛选 Tab："全部 / Case / Suite / Project"，避免老用户被淹没；③ 不引入图表（避免新增功能），但 KPI 数字旁可加 ↑/↓ 文字标记 |

---

### 步骤 9 · 回归结束确认

| 要素 | 内容 |
|---|---|
| **用户目标** | 知道"今日回归完成" |
| **当前页面** | Run 详情 / Report 列表 |
| **下一步** | 看到全部通过或记录剩余失败 |
| **阻碍** | 无明确"今日回归"状态标记 |
| **优化建议** | ① 通过率 = 100% 时，Run 详情顶部绿 Banner"今日回归全部通过 ✓"，按钮"返回 Dashboard / 查看 Report 列表"；② 仍有失败时，红 Banner"+N 条失败待修复"，按钮"查看失败原因 Tab" / "修复第一条" |

---

### 步骤 10 · 完成判定

| 要素 | 内容 |
|---|---|
| **用户目标** | 今日回归完成 |
| **当前页面** | Dashboard |
| **下一步** | 看到 Recent Projects 全部标"今日已回归 ✓" |
| **阻碍** | 无 Project 维度的"今日是否回归"标记 |
| **优化建议** | ① Dashboard Recent Project 卡片根据 `runs/summary.last_run_at` 显示徽标：今日 → ✓ 绿；昨日 → ○ 灰；更早 → ⚠ 黄；② 5 个 Recent Project 全部今日已回归 → Dashboard 顶部庆祝条（与老用户 Journey 一致） |

---

# ④ Smoke Test Journey

> **角色**：测试工程师，**改动核心接口后**或**上线前**做关键路径冒烟
> **频率**：每次发版 / 每次核心接口改动
> **终点**：在 ≤ 5 分钟内确认核心 5~15 条用例通过
> **预设**：Project 维护了若干业务场景 Suite（登录 / 下单 / 支付 / 查询等），存在一个名为 **"冒烟"** 或 **"Smoke"** 的 Suite（命名约定）

## 4.1 Journey 主路径

```text
登录 → Dashboard / Workspace Header → 目标 Project 概览
  → Suite 列表 → 选择"冒烟"Suite → Suite 详情（仅启用 Case）
  → 点击 "执行 Suite" → Run Drawer（预填 scope=collection + suiteId + 默认环境）
  → 同步执行 → 自动跳 Run 报告详情
  → 概览 Tab（看通过率） → 失败项 → Result → 修改 → 保存并执行 → 新 Run
  → 全部通过 → 返回 Suite 详情 / Dashboard
```

## 4.2 每一步分析

### 步骤 1 · 进入 Project

| 要素 | 内容 |
|---|---|
| **用户目标** | 1 步进入"今天要冒烟的 Project" |
| **当前页面** | Dashboard |
| **下一步** | Recent Project 卡片点击 → Project 概览 |
| **阻碍** | 同新用户 Journey 步骤 2 |
| **优化建议** | ① Recent Project 卡片附带"最近冒烟时间"（基于 Scope = 该 Suite 的 Run 的 last_run_at），老用户凭直觉判断"是不是该再冒一次"；② 距上次冒烟 > 24h 时 Recent Project 卡片加 "⚠ 待冒烟" 徽标 |

---

### 步骤 2 · 找到"冒烟"Suite

| 要素 | 内容 |
|---|---|
| **用户目标** | 1 步找到冒烟 Suite |
| **当前页面** | Project 概览 / Suite 列表 |
| **下一步** | 在 Suite 列表搜索"冒烟" / "Smoke" |
| **阻碍** | ① Suite 列表无"冒烟"快捷筛选；② 不同人命名不同（冒烟 / Smoke / Sanity / Critical），搜索时需逐一尝试 |
| **优化建议** | ① Suite 列表顶部加 **"快捷 Suite"** 快捷筛选按钮（识别名称包含"冒烟 / Smoke / Sanity / Critical / 核心"的 Suite），点击直接进入对应 Suite 详情；② 不新增 API，仅前端对 `GET /projects/:projectId/suites` 返回的列表做前端过滤；③ Suite 列表行展示"上次执行时间 + 通过率"，老用户凭直觉判断"是不是这个 Suite" |

---

### 步骤 3 · 检查 Suite 内容（启用 / 顺序）

| 要素 | 内容 |
|---|---|
| **用户目标** | 确认冒烟 Suite 用例齐了 |
| **当前页面** | Suite 详情 |
| **下一步** | 浏览 Case 列表，确认启用状态 |
| **阻碍** | ① Suite 详情列表无"上次执行结果"内联，老用户不知道"上次是不是通过的"；② 大量 Case 时找"是否包含最新改动接口"困难 |
| **优化建议** | ① Suite 详情 Case 行展示 **"上次 Run 状态徽标"**（来自 Suite 维度的最近 Run 摘要，前端缓存），老用户凭颜色判断"上次过没过"；② Suite 详情顶部若存在"近期修改过 Case"（基于 Case 列表 `updatedAt`），加 Banner"以下 X 条 Case 在过去 24h 被修改过"（来自 `updatedAt` 排序的前 5 条） |

---

### 步骤 4 · 一键执行 Suite

| 要素 | 内容 |
|---|---|
| **用户目标** | 跑冒烟 Suite |
| **当前页面** | Suite 详情 |
| **下一步** | Suite 详情 **"执行 Suite"** 按钮 → Run Drawer |
| **阻碍** | ① "执行 Suite"按钮位置不明显；② Run Drawer 打开后需要选 scope，老用户易选错 |
| **优化建议** | ① Suite 详情 PageHeader 主操作按钮 **"执行 Suite"**（唯一入口），点击 Drawer 顶部 scope 自动 = `suite + suiteId`，**不可改**（节省用户思考）；② Drawer 顶部 3 个 Tag 明确："范围：冒烟回归 Suite（X 条启用） / 环境：测试环境 / Base URL：xxx" |

---

### 步骤 5 · 等待同步执行

| 要素 | 内容 |
|---|---|
| **用户目标** | 在 ≤ 30 秒看到结果 |
| **当前页面** | Run Drawer（Loading） |
| **下一步** | 自动跳 Run 报告详情 |
| **阻碍** | 同日常 Regression Journey 步骤 4 |
| **优化建议** | ① 冒烟 Suite 用例少（≤ 15 条），执行应 < 30 秒，按钮文案"执行中…预计 < 30 秒"；② 超时 60 秒 Drawer 顶部红条提示"用例较少但耗时较长，请检查网络" |

---

### 步骤 6 · 看通过率

| 要素 | 内容 |
|---|---|
| **用户目标** | 1 秒判断"通过 / 失败" |
| **当前页面** | Run 详情 |
| **下一步** | KPI 条 → 通过率 |
| **阻碍** | ① 全部通过 / 失败时 UI 无明显颜色提示，老用户需看数字；② 通过率 = 100% 与 ≥ 80% 视觉无差别 |
| **优化建议** | ① KPI 条通过率**按阈值染色**：100% 绿、≥ 80% 黄、< 80% 红；② 全部通过时顶部绿 Banner"冒烟测试通过 ✓"；③ 仍有失败时顶部红 Banner"+N 条失败，建议立即修复" |

---

### 步骤 7 · 失败快速定位

| 要素 | 内容 |
|---|---|
| **用户目标** | 1 步跳到失败项 |
| **当前页面** | Run 详情 → 失败原因 Tab |
| **下一步** | 失败行点击 → Result 详情 |
| **阻碍** | ① 冒烟 Suite 一般 5~15 条，失败数量少，老用户希望"1 屏看完"；② 失败原因 Tab 默认折叠 |
| **优化建议** | ① 失败原因 Tab 默认**展开**（不折叠）所有失败项，老用户一眼看完整；② 失败行**内联 expected / actual**（与日常 Regression 一致），不必点进 Result |

---

### 步骤 8 · 修复与重跑

| 要素 | 内容 |
|---|---|
| **用户目标** | 修改 → 再跑 → 通过 |
| **当前页面** | Result 详情 → Case 编辑器 |
| **下一步** | 修改 → 保存并执行 → 新 Run |
| **阻碍** | ① 冒烟场景时间敏感，老用户希望 1 步搞定"改完再跑"；② 多条失败时改完第一条，跳回列表才能改第二条 |
| **优化建议** | ① Case 编辑器"保存并执行"按钮**默认主操作**（冒烟场景下），不再隐藏在次操作；② Result 详情增加 **"下一条失败"** 按钮（按 Run 内失败顺序排序），老用户串行修复不需回到列表；③ 新 Run 完成后**自动跳转**并对比"vs 上次 Run"（KPI 旁 ↑/↓ 标记） |

---

### 步骤 9 · 完成判定

| 要素 | 内容 |
|---|---|
| **用户目标** | 冒烟通过 |
| **当前页面** | Run 详情 |
| **下一步** | 看到全部通过，回到 Suite 详情 / Dashboard |
| **阻碍** | 无 |
| **优化建议** | ① 全部通过 → Banner "冒烟测试通过 ✓" + 按钮"返回 Suite 详情" / "查看完整 Report"；② 通过率 < 100% → Banner 列出失败项链接，便于回溯 |

---

# ⑤ 跨 Journey 共性优化建议汇总

> 以下是 4 条 Journey 中**反复出现**的优化点，汇总为通用规则，便于实施时统一处理。

## 5.1 跳转与上下文

| # | 优化点 | 适用 Journey | 实现位置 |
|---:|---|---|---|
| 1 | Workspace Header 永远显示 Project Switcher | ①②③④ | `ProjectWorkspaceHeader.tsx` |
| 2 | 详情页 → 上级时**保留原 URL Query**（搜索 / 分页 / Tab） | ①②③④ | 路由层 + 各列表组件 |
| 3 | 编辑器 / Drawer 保存后**自动回跳**来源页（URL `returnTo`） | ①②③④ | 路由层 |
| 4 | Run 执行完成后**自动跳 Run 详情**，不需用户再点 | ①③④ | `RunExecutionDrawer.tsx` |
| 5 | Result 详情"修改并再执行"1 步完成"跳编辑器 + 预填执行" | ①③④ | `WorkspaceResultDetail.tsx` |

## 5.2 默认值与预填

| # | 优化点 | 适用 Journey | 实现位置 |
|---:|---|---|---|
| 6 | 新建环境 Drawer **默认勾选"设为默认"** | ① | `EnvironmentFormModal.tsx` |
| 7 | OpenAPI Import Drawer **默认冲突策略 = skip** | ① | `WorkspaceImport.tsx` |
| 8 | Project 新建 Drawer **owner = 当前用户**（不必选） | ① | `ProjectFormModal.tsx` |
| 9 | Run Drawer **默认 scope = project**（从 Workspace Header 触发时） | ①③ | `RunExecutionDrawer.tsx` |
| 10 | Suite 详情"执行 Suite" → Drawer **scope = suite + suiteId 锁定** | ④ | `RunExecutionDrawer.tsx` |

## 5.3 信息前置

| # | 优化点 | 适用 Journey | 实现位置 |
|---:|---|---|---|
| 11 | Run Drawer 顶部展示 **3 个 Tag**（范围 / 环境 / 范围内 Case 数） | ①③④ | `RunExecutionDrawer.tsx` |
| 12 | Run 详情 KPI 条**颜色按阈值染色** | ③④ | `WorkspaceReportDetail.tsx` |
| 13 | Run 详情默认 Tab **存在 failed/error → 失败原因**；否则 → 概览 | ①③④ | `WorkspaceReportDetail.tsx` |
| 14 | Suite 列表行展示"上次执行时间 + 通过率" | ①②③④ | `WorkspaceSuiteList.tsx` |
| 15 | Environment 列表行展示 Base URL + Variables 数 + 是否默认 | ①② | `WorkspaceEnvironment.tsx` |
| 16 | Recent Project 卡片附带"上次访问时间 + 上次回归时间" | ①②③④ | `RecentProjectsPanel.tsx` |

## 5.4 错误兜底

| # | 优化点 | 适用 Journey | 实现位置 |
|---:|---|---|---|
| 17 | 无默认环境时 **Run Drawer 顶部红条 + 跳转按钮** | ①③ | `RunExecutionDrawer.tsx` |
| 18 | Suite 为空时 Run Drawer 红条 + "去添加 Case" 按钮 | ① | `RunExecutionDrawer.tsx` |
| 19 | 切换 Project 时若有未保存表单 / Run 执行中 → Popconfirm / Modal | ①② | 全局 `RouteGuards.tsx` |
| 20 | 登录失败区分"账号禁用 / 密码错误 / 请求过多" | ①②③④ | `Login.tsx` |

## 5.5 不在范围（防止范围蔓延）

下列建议**不进入本期**（避免新增功能 / API / DB）：

- ❌ 跨 Project 复制 Case / Suite
- ❌ 全局搜索（依赖后端聚合接口）
- ❌ 通知中心 / 邮件 / IM 集成
- ❌ 定时执行 / CI 集成
- ❌ 报告导出 / 分享链接
- ❌ 性能图表 / 趋势图
- ❌ AI 助手
- ❌ 项目成员 / 协作空间

---

# ⑥ 验收指标（4 条 Journey 通用）

| 指标 | 计算方式 | 目标 |
|---|---|---|
| **新用户首次跑通 Suite 点击数** | 步骤 1~10 点击总数 | ≤ 14 次（现状 ~22） |
| **老用户日常回归点击数** | Dashboard → Run 报告 → 修复 → 再跑 | ≤ 10 次 |
| **冒烟测试完成时间** | 进入 Suite 详情 → 全部通过 | ≤ 5 分钟（含修复 1 条失败） |
| **迷失事件** | 用户在 1 分钟内点击 Back / 面包屑 ≥ 3 次 | ≤ 5% |
| **Recent Project 使用率** | 从 Dashboard 进入 Project 的会话中，经 Recent 卡片进入 | ≥ 60% |
| **执行完成自动跳转率** | Run 完成后自动跳 Report | 100% |
| **保存后自动回跳率** | 编辑器保存后自动回到来源页 | 100% |
| **误删除率** | 用户误把"从 Suite 移除"当"删除 Case"的次数 | ≤ 1% |

---

# ⑦ 实施优先级

按"价值 / 改动量"排序（与 NavigationUX §⑮ 协同）：

| # | 任务 | 优先级 | 估时 | 价值 |
|---:|---|:-:|:-:|:-:|
| 1 | Workspace Header "快速执行" 按钮（预填 scope=project） | P0 | 1 天 | 高 |
| 2 | Run Drawer 顶部 3 个 Tag + 默认 scope / 环境 | P0 | 1 天 | 高 |
| 3 | Run 详情默认 Tab + KPI 染色 + 自动跳 Report | P0 | 1 天 | 高 |
| 4 | Result 详情"修改并再执行" 1 步按钮 | P0 | 1 天 | 高 |
| 5 | Recent Project 卡片 + 登录后落点（NavigationUX §⑥） | P0 | 2 天 | 高 |
| 6 | Breadcrumb 三级结构 + URL Query 持久化（NavigationUX §⑤） | P0 | 2 天 | 高 |
| 7 | Project Switch 三层策略 + 切换器改版（NavigationUX §⑧） | P0 | 3 天 | 高 |
| 8 | Overview 资产完整度徽标 + "下一步" 引导卡 | P1 | 1 天 | 中 |
| 9 | Suite 列表"上次执行时间 + 通过率" 信息前置 | P1 | 0.5 天 | 中 |
| 10 | Case 编辑器"保存并执行" 副按钮 | P1 | 0.5 天 | 中 |
| 11 | Report 列表 scope 筛选 Tab + "上次通过率"列 | P1 | 1 天 | 中 |
| 12 | OpenAPI Import Drawer 默认 skip + 自动回跳 | P1 | 0.5 天 | 中 |
| 13 | Run Drawer 切换环境时 invalidate 缓存 | P2 | 0.5 天 | 中 |
| 14 | 登录失败区分错误类型文案 | P2 | 0.5 天 | 低 |
| 15 | 切换 Project 兜底确认（Popconfirm / Modal） | P2 | 1 天 | 中 |

---

# ⑧ 文档约束再确认

- ✅ 不新增任何后端 API
- ✅ 不新增任何数据库表 / 字段 / 迁移
- ✅ 不新增功能模块（无复制 / 无定时 / 无通知 / 无图表 / 无 AI）
- ✅ 仅优化已有流程的组织方式、默认行为、跳转关系、上下文复用
- ✅ 所有能力通过前端路由 / URL Query / LocalStorage / 已有 Drawer 预填实现

---

**附录**：本 Journey 文档与既有设计文档的对应关系

| 既有文档 | 本 Journey 中引用的优化点 |
|---|---|
| `INFORMATION_ARCHITECTURE.md` §11 主路径 | ① 新用户 Journey 主路径 |
| `INFORMATION_ARCHITECTURE.md` §13 单用例调试路径 | ① 新用户 Journey 步骤 10 |
| `INFORMATION_ARCHITECTURE.md` §14 Suite 回归路径 | ④ Smoke Test Journey |
| `INFORMATION_ARCHITECTURE.md` §15 Project 全量回归路径 | ③ 日常 Regression Journey |
| `INFORMATION_ARCHITECTURE.md` §16 失败定位路径 | ②③④ 失败修复步骤 |
| `INFORMATION_ARCHITECTURE.md` §17 环境切换与维护路径 | ② 老用户 Journey 步骤 8 |
| `NavigationUX.md` §11 路径 A 登录→修复失败 | ①③ 失败定位步骤 |
| `NavigationUX.md` §11 路径 B 单用例调试循环 | ②③ 单条调试步骤 |
| `NavigationUX.md` §11 路径 C 首次创建 Project 跑通首个 Suite | ① 新用户 Journey 全部 |
| `NavigationUX.md` §11 路径 D 跨 Project 查看 Run | ② 老用户 Journey 步骤 6 |
| `PROJECT_WORKSPACE.md` §4 顶部信息条 | 全部 Journey Header 体验 |
| `PROJECT_WORKSPACE.md` §7 右侧上下文栏 | ② 老用户 Journey 步骤 7 |

---

> **版本**：v1.0 · 2026-07-16
> **作者**：产品经理（测试平台方向）
> **范围**：仅 MVP 阶段 4 条核心 Journey；定时 / CI / 通知 / 协作场景不在本期范围