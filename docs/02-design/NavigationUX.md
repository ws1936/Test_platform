# API 自动化测试平台 · Navigation UX 规范

> 版本：v1.0  
> 适用范围：API 自动化测试平台前端导航体验  
> 配套：`DesignSystem.md`（视觉）、`Layout.md`（骨架）、`INFORMATION_ARCHITECTURE.md`（信息架构）、`UX_REVIEW.md`（现状问题清单）  
> 约束边界：**仅规范导航行为与跳转关系，不修改任何业务、不新增 API、不改动数据库**

---

## 0. 文档定位

本文档解决三个根问题：

1. **点击多**：用户从"登录"到"修复 1 条失败断言并重新执行"需要 ~ 18 次点击（详见 §12 对比）。
2. **易迷失**：在 5 层嵌套（Project → Module → List → Detail → Result）中，用户不知道"我在哪"和"我能去哪"。
3. **上下文丢失**：Project 切换、列表筛选、Drawer 关闭后，无法回到原位置。

围绕这三点，新增 **四类导航能力**：**Breadcrumb / Recent Project / Back / Project Switch**。

---

## ① 设计目标与成功度量

### 1.1 北极星指标

| 指标 | 当前值（估） | 目标值 |
|---|---|---|
| 主流程总点击次数（登录 → 修复失败） | ~ 18 次 | **≤ 10 次** |
| 迷失事件（用户 1 分钟内点击 3 次以上"返回"） | 高频 | **消除** |
| Project 切换后上下文错位率 | 高（H1） | **0** |
| 用户从 Run 详情回到 Result 的成功率 | 中 | **100%**（无脑点 Back 即可） |
| 单用例调试路径（创建 Case → 看 Report → 改 Case → 再执行）点击数 | ~ 13 | **≤ 7** |

### 1.2 约束

- ❌ 不修改任何后端 API
- ❌ 不新增任何接口
- ❌ 不改数据库
- ✅ 全部通过前端路由、URL Query、localStorage 解决

---

## ② 现状痛点（精简版 · 详 `UX_REVIEW.md`）

| ID | 痛点 | 触发场景 | 用户感受 |
|---|---|---|---|
| **H1** | Project 切换后 URL（runId / caseId / tab）不重置 | 在 Project A 打开 Report，切换到 Project B，Sider 显示 B，URL 还是 A | "我切了 Project 吗？怎么页面没变？" |
| **H2** | 三处执行入口分散 | Suite 详情 / Case 编辑器 / Run Center / Workspace Header 都打开"执行" | "我该从哪执行？哪个是对的？" |
| **H3** | Report 列表与 Overview 重复 | Overview 已有 KPI + Recent Runs，Report 列表又有同样内容 | "我到底该看哪个？" |
| **M1** | Overview / Run Detail 概览 Tab KPI 重复 | 同上 | 浪费视线 |
| **M2** | Workspace 引导步骤跳转过多 | 4 步引导需在 Sider / 顶部 / 抽屉之间切换 | "下一步在哪？" |
| **M4** | Suite 列表信息密度低 | 列表只显示名称 / 描述 / 时间 | "我不知道该进哪个 Suite" |
| **M6** | Case 编辑返回丢失搜索状态 | Case 列表 → 编辑 → 返回，跳回空筛选全列表 | "我的筛选呢？" |
| **M7** | Run / Result Tab 信息重复 | Run 详情 Results Tab 与 Result 详情请求 / 响应是同一份数据 | "我看了几遍同一份数据？" |
| **M10** | 无全局搜索 | 想找某个 Run，但只能列表翻 | "我找不到上次那个 Run" |

本文档围绕 H1 / H2 / H3 / M6 / M10 提出重构；其余痛点在相关页面设计中解决。

---

## ③ 导航设计原则

| # | 原则 | 反例 |
|---:|---|---|
| 1 | **三层心智模型**：平台级 → Project 级 → 详情级，每层只关心自己的事 | 把 Run 详情直接放到 Dashboard |
| 2 | **每个对象只有一个规范入口** | Run 详情既可从 Report 进入，也可从 Overview 进入 |
| 3 | **永远保留上下文**：Project / Suite / Case / Run 切换都不丢失筛选 / Tab / 滚动位置 | 切换 Project 后 URL 仍带 runId |
| 4 | **永远有"回家的路"**：任何页面 1 次点击可回到上级，2 次点击可回到 Dashboard | 详情页只有"返回"，没有"回到列表" |
| 5 | **永远有"下一步"**：每个空状态 / 错误态都给出明确动作 | "暂无数据"无 CTA |
| 6 | **路径可分享**：所有中间状态都进 URL，浏览器 Back / Forward 必须可用 | 用 Modal 状态机替代路由 |
| 7 | **不抢用户的 Back 键**：浏览器返回按钮应符合用户预期 | 浏览器 Back 退出整个 App |

---

## ④ 三层心智模型

### 4.1 层级定义

| 层 | 范围 | 用户问题 | 包含对象 |
|---|---|---|---|
| **L1 · 平台层** | 全平台 | "我能进入哪些 Project？" | Dashboard / Project 列表 / 系统管理 |
| **L2 · Project 层** | 当前 Project | "在这个 Project 里我能做什么？" | 概览 / Environment / Suite / Case / Run / Report / Settings |
| **L3 · 详情层** | 某个具体对象 | "这个对象的具体内容？" | Suite 详情 / Case 编辑 / Run 详情 / Result 详情 |

### 4.2 跨层导航规则

| 起点 | 终点 | 允许？ | 备注 |
|---|---|---|---|
| L1 | L1 | ✅ | 平台层内部跳转 |
| L1 | L2 | ✅ | 必须经由"选择 Project"动作 |
| L1 | L3 | ❌ | 不允许跳过 Project 直接看某个 Run |
| L2 | L1 | ✅ | 顶部 Logo / 用户菜单返回 |
| L2 | L2 | ✅ | Project 内模块跳转，保留上下文 |
| L2 | L3 | ✅ | 进入某个对象详情 |
| L3 | L1 | ✅ | 面包屑 / Logo / 浏览器 Back |
| L3 | L2 | ✅ | 面包屑 / Project Switch |
| L3 | L3 | ✅ | 对象间关联跳转（Suite → Case → Run） |

### 4.3 L1 / L2 / L3 在视觉上的差异

| 维度 | L1 | L2 | L3 |
|---|---|---|---|
| Sider 形态 | L1 主导航 | L1 主导航 + L2 嵌套导航 | L1 主导航 + L2 嵌套导航 |
| PageHeader 标题 | "项目列表" / "工作台" | "用户服务 API / 环境" | "用户服务 API / API 用例 / 获取用户详情" |
| 主操作按钮位置 | PageHeader 右侧 | PageHeader 右侧 + Context Panel | PageHeader 右侧 + 详情头部 |
| Breadcrumb 粒度 | 2~3 级 | 3 级 | 4~5 级 |

---

## ⑤ Breadcrumb 策略

### 5.1 三级 Breadcrumb 设计

平台统一使用**三级面包屑**结构，跨 L1 / L2 / L3：

```text
[层级1：平台 / 项目] / [层级2：模块] / [层级3：对象]
```

| 用户所在 | Breadcrumb |
|---|---|
| Dashboard | （不显示面包屑，Dashboard 是首页） |
| Project 列表 | `工作台 / 项目` |
| Project 概览 | `工作台 / 项目 / 用户服务 API` |
| Environment 列表 | `用户服务 API / 环境` |
| Suite 列表 | `用户服务 API / 测试套件` |
| Suite 详情 | `用户服务 API / 测试套件 / 冒烟回归` |
| Case 列表 | `用户服务 API / API 用例` |
| Case 编辑器 | `用户服务 API / API 用例 / 获取用户详情` |
| Run 报告列表 | `用户服务 API / 测试报告` |
| Run 报告详情 | `用户服务 API / 测试报告 / Run #20260715` |
| Result 详情 | `用户服务 API / 测试报告 / Run #20260715 / Result #3` |
| 用户管理 | `系统管理 / 用户管理` |

### 5.2 链接行为

| 段 | 行为 |
|---|---|
| **层级1（平台 / 项目）** | 永远可点击。点击 → 对应平台的规范入口（Dashboard / Project 列表 / 用户管理） |
| **层级2（模块）** | 永远可点击。点击 → 对应模块的**列表页**（保留 URL Query 如 `?search=&page=`） |
| **层级3（对象）** | 当前页时不可点击；其余对象页可点击，**跳转后保留原上下文**（如从 Run 详情跳到另一个 Run 详情，仍带 `?tab=`） |

### 5.3 详情页内的"次级面包屑"

在 Run 详情 / Result 详情 / Case 编辑器内部，使用**横向 Tab 切换**代替"再嵌一层面包屑"，避免过度层级。Tab 状态写进 URL `?tab=`。

### 5.4 Breadcrumb 缺失场景

- **登录页 / 错误页 / 全屏空状态**：不显示面包屑。
- **Workspace Header 已包含项目名 + 关键信息时**，面包屑的"层级1"允许省略，避免与 Workspace Header 重复。

### 5.5 与现有 UX Review 对应

- ✅ 解决 **M6**（Case 编辑返回丢失搜索状态）：Breadcrumb 点击模块时携带 URL Query。
- ✅ 解决 **M7**（跨 Tab 信息重复）：用 Tab 替代面包屑深度。

---

## ⑥ Recent Project 策略

### 6.1 目标

让用户从 Dashboard **1 次点击**直达最近操作的 Project，不必再经过"Project 列表 → 搜索 → 选 Project"三步。

### 6.2 Recent Project 数据来源

| 来源 | 优先级 | 说明 |
|---|---|---|
| **最近 5 个 Project** | 最高 | 按 `lastVisitedAt` 倒序，来自前端持久化 |
| **拥有的全部 Project** | 中 | 当前用户作为 owner 的 Project，按 `updatedAt` 倒序 |
| **收藏 Project**（未来扩展） | 低 | 用户手动置顶的 Project |

`lastVisitedAt` 通过前端事件埋点更新：
- 进入 `/projects/:id/**` 任意页面 → 写入当前时间到 localStorage。
- 用户**切换 Project** 而非"切回最近"时，**保留** 5 个最近列表，不覆盖。

### 6.3 Dashboard 上的 Recent Project 呈现

Dashboard 顶部放置 "**Recent Projects**" 卡片区：

| 属性 | 值 |
|---|---|
| 位置 | Dashboard 第一行 KPI 下方 |
| 数量 | **5 个**（不足则全部展示） |
| 排序 | `lastVisitedAt desc` |
| 每个卡片显示 | Avatar + 名称 + 上次访问时间（如"3 小时前"）+ Owner 缩写 |
| 点击行为 | **直接进入该 Project 概览**（不再二次点击） |
| 空态 | "你还没有访问过 Project，去 [项目列表](#) 创建第一个" |

### 6.4 持久化与隐私

- 存储位置：`localStorage["app.recentProjects"]`。
- 存储格式：`Array<{ id, name, visitedAt }>`，**最多 5 项**，超出按 `visitedAt` 淘汰。
- **不清空**：登出 / 切换账号 / 清浏览器缓存时清空；正常刷新保留。
- **无 Project 数据时**：Dashboard 显示空态卡片，**不显示** Recent 区。
- **数据安全**：仅存 ID + 名称，**不存任何 Project 内部数据**。

### 6.5 Recent Project 在其他场景的复用

| 场景 | 复用方式 |
|---|---|
| **登录后默认落点** | 若用户最近访问过 Project A 且未超过 7 天，落点直接是 `Project A / 概览`；否则落点 Dashboard |
| **Project Switch 下拉顶部** | 顶部 5 个 Recent Projects（标"最近"徽标） + 分隔线 + 全部 Project |
| **Workspace 切换 Project 时** | 优先展示 Recent（前 5 个），再做完整搜索 |

### 6.6 与现有 UX Review 对应

- ✅ 解决 **M10**（缺全局搜索）：Recent Projects 是"半全局入口"。
- ✅ 减少 Dashboard → Project 的点击次数（**3 → 1**）。

---

## ⑦ Back 策略

### 7.1 Back 的两种来源

| 来源 | 行为 | 适用范围 |
|---|---|---|
| **浏览器 Back 键 / Backspace** | 走 `history.back()` | 任何页面 |
| **页面内"返回"按钮** | 走显式路由跳转 | 详情页 / Drawer / Modal |

二者**必须等价**（即按浏览器 Back 等同于点页面"返回"按钮）。

### 7.2 Back 行为分级

| 当前页 | Back 目标 | 备注 |
|---|---|---|
| L3 详情页 | L3 列表页（带原 URL Query） | 例：Case 编辑器 → Case 列表（带 `?search=&page=`） |
| L3 详情页（从另一对象跳入） | 来源对象详情 | 例：Suite 详情 → Case 详情，Back → Suite 详情 |
| L2 模块页 | L2 概览页 | 例：Environment → Project 概览 |
| L1 平台页 | Dashboard | 例：用户管理 → Dashboard |
| Project 概览 | Dashboard | |
| Drawer / Modal | 关闭浮层（**不** 触发 history.back） | 例外：见 7.4 |
| 全屏信息页（登录 / 错误） | 浏览器 Back 退出整个 App，**符合预期** | |

### 7.3 "返回"按钮位置

| 页面类型 | 位置 | 文案 |
|---|---|---|
| L3 详情页 | PageHeader 标题**左侧**（H4 图标 + "返回"） | "返回" |
| Drawer | Header 左侧 | "关闭" / `CloseOutlined` |
| Modal | Header 右侧 | `CloseOutlined` |
| 全屏错误页 | 错误主体下方 | "返回 Dashboard" |

### 7.4 Drawer / Modal 的 Back 特殊处理

- **Drawer / Modal 打开不创建新历史记录**（避免按 Back 直接关闭，反而绕过业务路径）。
- Drawer / Modal **关闭**使用浮层内部"取消 / 关闭"按钮，**不依赖**浏览器 Back。
- 浏览器 Back 键在 Drawer / Modal 打开期间被禁用（`maskClosable={false}` + 监听 `popstate` 拦截）。

### 7.5 Back 后必须恢复的状态

| 状态 | 是否恢复 |
|---|---|
| 滚动位置 | ✅ 恢复 |
| 搜索 / 筛选 | ✅ 恢复（来自 URL Query） |
| Tab | ✅ 恢复（来自 URL Query） |
| 分页 | ✅ 恢复（来自 URL Query） |
| Drawer / Modal 打开状态 | ❌ 不恢复（Back 不应反向"打开"） |
| 表单未保存内容 | ⚠️ 弹离开确认（beforeunload 类） |

### 7.6 与现有 UX Review 对应

- ✅ 解决 **M6**（Case 编辑返回丢失搜索状态）。
- ✅ 解决部分 **M7**（避免同一对象在多层级被反复进入）。

---

## ⑧ Project Switch 策略

### 8.1 三层 Project Switch 设计

Project Switch 不只是"换 Project"，而是**3 种粒度**：

| 类型 | 触发 | 行为 |
|---|---|---|
| **A. 静默切换（保留模块）** | 在 L2 任何模块页切换 | 跳到新 Project 的**同名模块列表页**（如 Environment → Environment） |
| **B. 详情上下文切换（保留对象）** | 在 L3 详情页切换，**仅当新 Project 内存在同名 / 同 ID 对象时** | 跳到新 Project 内同名对象的详情页 |
| **C. 强制回概览** | B 不成立时，或用户主动选择 | 跳到新 Project 概览页 |

### 8.2 切换规则表

| 起点页 | 切换策略 | 目标页 |
|---|---|---|
| Dashboard | 跳到目标 Project 概览 | `/projects/:newId/workspace/overview` |
| Project 列表 | 跳到目标 Project 概览 | `/projects/:newId/workspace/overview` |
| **Project 概览** | **A. 静默切换** | `/projects/:newId/workspace/overview` |
| **Environment 列表** | **A. 静默切换** | `/projects/:newId/workspace/environment` |
| **Suite 列表** | **A. 静默切换** | `/projects/:newId/workspace/suite` |
| **Case 列表** | **A. 静默切换** | `/projects/:newId/workspace/case` |
| **执行中心** | **A. 静默切换** | `/projects/:newId/workspace/run` |
| **报告列表** | **A. 静默切换** | `/projects/:newId/workspace/report` |
| **项目设置** | **A. 静默切换** | `/projects/:newId/workspace/information` |
| **Suite 详情** | **B → C**：查新 Project 是否存在同名 Suite，是则跳详情，否则跳 Suite 列表 | Suite 详情 或 Suite 列表 |
| **Case 编辑器** | **B → C**：查新 Project 是否存在同名 Case，是则跳详情，否则跳 Case 列表 | Case 编辑器 或 Case 列表 |
| **Run 报告详情** | **强制 C**：Run 不跨 Project 共享，跳新 Project 报告列表 | `/projects/:newId/workspace/report` |
| **Result 详情** | **强制 C**：同 Run 详情 | `/projects/:newId/workspace/report` |
| **OpenAPI 导入** | **强制 C**：导入上下文绑定 Suite，跨 Project 无意义 | `/projects/:newId/workspace/import` 或 Suite 列表 |

### 8.3 切换器 UI 增强

Project Switch 下拉（在 Sider 顶部）改版为 3 段：

| 段 | 内容 | 排序 |
|---|---|---|
| **① Recent Projects** | 最近 5 个 Project，标 "最近" 徽标 | `lastVisitedAt desc` |
| **② All Projects** | 用户拥有的全部 Project，可搜索 | `updatedAt desc` |
| **③ New Project** | "+ 新建 Project" 入口 | 底部 |

视觉：

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

### 8.4 切换前确认

- 当用户**有未保存的表单**（编辑器有 dirty 标记）切换时，弹 Popconfirm "有未保存更改，确定切换？"
- 当用户在 **执行同步操作中**（Run 进行中）切换时，弹 Modal "当前 Project 正在执行 Run #xxx，确定切换？"（参考 `UX_REVIEW H1`）

### 8.5 切换后的状态重置

切换 Project 后，以下状态**必须重置**（防止上下文污染）：

| 状态 | 处理 |
|---|---|
| 当前 URL 中的 runId / caseId / suiteId | **清除**（除非是 B 类型切换） |
| 当前 URL 中的 `?tab=` | **保留**（Tab 是页面级，不绑 Project） |
| 滚动位置 | **重置到顶部** |
| Drawer / Modal | **强制关闭** |
| 选中的 Case / Suite（多选） | **清空** |
| Form 状态 | **清空** |

### 8.6 与现有 UX Review 对应

- ✅ 解决 **H1**（Project 切换上下文不重置）的根问题。
- ✅ 解决 **L4 / M4**（列表摘要缺失）：Recent Projects 列表自带"上次访问时间"上下文。

---

## ⑨ 点击次数削减：通用策略

### 9.1 默认值与预填

| 场景 | 削减方式 | 节省点击 |
|---|---|---|
| **Run 名称** | 默认空，由后端自动生成 | -1 |
| **执行环境** | 默认选中 Project 默认环境，**不需点击** | -1 |
| **Suite 选择** | 从 Suite 详情"执行 Suite"时，预填当前 Suite | -2 |
| **Case 选择** | 从 Case 编辑器"执行 Case"时，预填当前 Case | -2 |
| **环境 Variables** | 自动注入当前环境的 Variables，**不需手动复制** | -1 |
| **OpenAPI 导入** | 默认冲突策略 = `skip`，**不需选择** | -1 |
| **新建 Project** | 默认 owner = 当前用户，**不需选择** | -1 |

### 9.2 一步直达

| 场景 | 一步直达 |
|---|---|
| **从 Dashboard 进 Project** | Recent Project 卡片**一次点击进概览** |
| **从 Run 详情回到 Result** | 失败原因 Tab 内点击失败项**一次直达** Result 详情 |
| **从 Case 编辑器执行** | PageHeader "选择环境并执行" 按钮**一次打开 Drawer** 并预填 |
| **从 Suite 详情执行** | PageHeader "执行 Suite" 按钮**一次打开 Drawer** 并预填 |
| **从 Workspace Header 快速执行** | "快速执行" 按钮**一次打开 Drawer** 并预填 scope=project |
| **删除前确认** | Popconfirm（按钮旁弹出，**不需弹 Modal**） |

### 9.3 上下文信息前置

| 场景 | 前置信息 | 削减点击 |
|---|---|---|
| **Run Drawer** | 顶部直接显示"范围 / 环境 / 范围内启用 Case 数"3 个 Tag | 用户不必逐字段查看 |
| **环境列表** | 直接显示 Base URL / Variables 数 / 是否默认 | 不必点详情 |
| **Suite 列表** | 直接显示 Case 数 / 最近通过率 | 不必点详情 |
| **Project 列表** | 直接显示 Owner / 资产数 / 上次访问 | 不必点概览 |
| **Run 列表** | 直接显示状态 / 通过率 / 耗时 / 环境 | 不必点详情 |

### 9.4 合并操作

| 场景 | 合并 |
|---|---|
| **Run 完成 → 跳转 Report** | 不再"点击"跳 Report，而是**自动跳转**（执行完成时直接 navigate 到 Report） |
| **Case 保存 → 回到原 Suite** | 不再"保存 + 点返回"，而是保存成功后**自动 navigate.back** |
| **OpenAPI 导入完成 → 回到 Suite** | 同上 |
| **新建 Project → 进入概览** | 同上 |
| **新建 Case → 留在编辑器** | 留在编辑器，但 Toast 提示"已创建" |

### 9.5 快捷操作（次操作）

| 操作 | 入口 | 节省点击 |
|---|---|---|
| **复制 Base URL** | Environment 列表行右侧图标按钮 | -2 |
| **复制 Case Path** | Case 列表行右侧图标按钮 | -2 |
| **跳到最近 Run** | Workspace Header "最近执行" 按钮 | -3 |
| **重新执行 Run** | Run 详情 "再次执行" 按钮（预填原 scope / env） | -3 |

---

## ⑩ 反迷失策略：通用

### 10.1 当前位置锚点

| 锚点 | 实现 |
|---|---|
| **Sider 高亮** | L1 主导航 + L2 嵌套导航**双高亮**，用户在任何位置都能看到"我在哪一层" |
| **Workspace Header 永远存在** | 项目头**不被滚动遮挡**（不吸顶但与 Content 一起滚动），任何时候都能看到"当前 Project + 配置就绪度" |
| **Breadcrumb 始终可见** | PageHeader 顶部，跨路由不消失 |
| **PageHeader 标题明确** | 标题 = "Project + 模块 + 对象"完整名称，不用缩写 |

### 10.2 上下文持久化

| 持久化项 | 存储 | 失效时机 |
|---|---|---|
| **当前 Project** | URL Path | 路由变化 |
| **当前模块** | URL Path | 路由变化 |
| **当前 Tab** | URL Query `?tab=` | 路由变化 |
| **当前分页** | URL Query `?page=&size=` | 路由变化 |
| **当前搜索 / 筛选** | URL Query `?search=&method=&status=` | 路由变化 |
| **最近 Project 列表** | localStorage `app.recentProjects` | 浏览器缓存清空 |
| **Sider 折叠状态** | localStorage `app.sider.collapsed` | 用户主动切换 |
| **Drawer / Modal 状态** | 不持久化（关闭即销毁） | — |

### 10.3 离开前确认

| 场景 | 确认方式 |
|---|---|
| 表单有 dirty | Popconfirm "有未保存更改，确定离开？" |
| Run 执行中 | Modal "当前 Run 正在执行，强行离开将丢失进度" |
| 危险操作（删除） | Modal 二次确认 + 名称输入 |
| Project 切换 + 有未保存 | Popconfirm + Modal（按情况） |

### 10.4 错误状态可恢复

| 错误 | 恢复路径 |
|---|---|
| 403 无权限 | 错误页"返回 Dashboard"按钮（1 次） |
| 404 资源不存在 | 错误页"返回上级"按钮（1 次） |
| 500 网络异常 | 错误页"重新加载"按钮（1 次） |
| 表单字段错误 | 字段下方红字 + 自动 focus（0 次，点击"保存"后自动定位） |
| 业务错误 | Toast `message.error`（0 次，弹窗可关闭） |

### 10.5 全局可达性

| 元素 | 始终可达 |
|---|---|
| **Logo / Dashboard 入口** | L1 Sider 顶部 Brand 区，永远在 |
| **用户菜单 / 退出登录** | L1 Header 右侧，永远在 |
| **Project 切换** | L1 Sider 顶部 Project Switcher，永远在 |
| **Breadcrumb** | L1 / L2 Content 顶部 |
| **Back / 返回** | L3 详情页 PageHeader 左侧；L1 / L2 内容页依赖面包屑 |

---

## ⑪ 关键路径重设计

### 11.1 路径 A：登录 → 修复 1 条失败用例

**Before**（约 18 步）：

```text
1. 登录
2. 进入 Dashboard
3. 看到 Recent Run，点击
4. → Run 详情（点 Overview Tab）
5. 切换到 Failures Tab
6. 找到失败项，点击
7. → Result 详情
8. 切换到 Assertions Tab 看 expected/actual
9. 切换到 Overview Tab 看错误
10. 点击"查看 Case 定义"
11. → Case 编辑器
12. 修正配置
13. 点击"保存"
14. 保存后留在 Case 编辑器
15. 点击"执行此 Case"
16. → Run Drawer 打开
17. 选择环境（已默认）
18. 点击"Run Now"
19. 等待同步执行
20. 自动跳转 Report
21. 查看新 Run 结果
```

**After**（约 10 步）：

```text
1. 登录
   →（若有 Recent Project）直接落到该 Project 概览
2. 进入 Dashboard
3. Recent Run 卡片直接展示，点击
4. → Run 详情，默认在 Failures Tab
5. 失败项可点击，进 Result 详情
6. Result 详情顶部 "查看 Case 定义" 按钮
7. → Case 编辑器（URL 带 returnTo）
8. 修正配置
9. 点击"保存并执行"
10. → Run Drawer 自动打开，预填当前 Case / 环境
11. 点击"Run Now"
12. → 新 Run Report
```

**关键改动**：

- 登录后默认落点 Recent Project（节省 2 步）
- Recent Run 卡片直达（节省 1 步）
- Run 详情默认 Tab = Failures（节省 1 步）
- 失败项可点击（节省 1 步）
- "保存并执行" 合并保存 + 执行（节省 1 步）
- Drawer 自动预填（节省 1~2 步）

### 11.2 路径 B：单用例调试循环

**Before**（约 13 步）：

```text
1. 进 Project 概览
2. 点 "API 用例"
3. 搜索 Case
4. 点击 Case
5. 修正
6. 保存
7. 点 PageHeader "执行"
8. Drawer 打开，预填环境
9. Run Now
10. 跳 Report
11. 看 Result
12. 跳 Case 编辑器
13. 再保存 → 再执行
```

**After**（约 7 步）：

```text
1. 进 Project 概览
2. Workspace Header 显示 "快速执行"，点击
   → Run Drawer 打开，预填 scope=project + 默认环境
3. 在 Drawer 顶部直接选 "单用例" scope，并选 Case
4. Run Now
5. 跳 Report
6. 失败项一键跳 Result
7. Result 顶部 "修改 Case + 再执行" 一键 → Case 编辑器，自动定位到原失败断言
```

**关键改动**：

- "快速执行" 按钮前置到 Workspace Header（节省 2 步）
- Drawer 顶部支持 scope 切换 + 直接选 Case（节省 1~2 步）
- Result 详情"修改 + 再执行" 一键（节省 2 步）

### 11.3 路径 C：首次创建 Project 并跑通首个 Suite

**Before**（约 22 步）：

```text
1. Dashboard "新建 Project"
2. 填表 → 保存 → 跳概览
3. Workspace 引导点 "创建环境"
4. 抽屉打开 → 填 Base URL / Headers / Variables
5. 保存环境
6. "设为默认"（额外点击）
7. Workspace 引导点 "创建 Suite"
8. 抽屉打开 → 填名称 / 描述
9. 保存 Suite
10. 进 Suite 详情
11. 点 "新建 Case"
12. 表单填 Method / Path / 断言
13. 保存 Case
14. 回到 Suite 详情
15. 点 "执行 Suite"
16. Drawer 打开，预填 suite / 环境
17. Run Now
18. 跳 Report
```

**After**（约 14 步）：

```text
1. Dashboard Recent 区域下方 "新建 Project" 入口
2. 表单：仅填名称（描述可后补），保存后自动设为 owner + 跳概览
3. Workspace 顶部"下一步" 卡片引导：
   "创建你的第一个环境" → 点击直接打开 Drawer
4. Drawer 打开时自动勾选 "设为默认环境"
5. 保存环境 → Drawer 关闭，自动跳 "创建 Suite" 引导
6. 同样 Drawer → 填 Suite 名称 → 保存
7. 自动跳 "创建 Case" → Drawer → 填 → 保存
8. Workspace Header "快速执行" → Drawer → scope=suite → Run Now
9. 跳 Report
```

**关键改动**：

- 新建 Project 表单只填名称（节省 1~2 步）
- "设为默认" 自动勾选（节省 1 步）
- Workspace 引导改为"串行 Drawer" 而非"页面跳转"（节省 4 步）
- Workspace Header 快速执行前置（节省 2 步）

### 11.4 路径 D：跨 Project 查看 Run

**Before**（约 6 步，**且上下文丢失**）：

```text
1. 在 Project A 打开 Run #100
2. 想看 Project B 的 Run #200
3. 打开 Sider Project Switcher
4. 切换到 Project B
5. → URL 仍是 /projects/A/workspace/report/100
6. 显示 404（项目数据为空）
7. 必须手动跳 Project B 报告列表 → 搜索 200 → 进入
```

**After**（约 3 步，**不丢失上下文**）：

```text
1. 在 Project A Run #100 详情
2. 打开 Sider Project Switcher
3. 切换到 Project B
4. → 自动跳 Project B 报告列表（保留 report 语义）
5. 在新列表中搜索 / 找到 Run #200
```

或**更直接**：Run 详情顶部加"在 Project B 中打开" 按钮（若 Project A / B 共享 Run ID 命名约定），1 步完成。

---

## ⑫ 点击次数对比表

| 主流程 | Before | After | 削减 |
|---|---:|---:|---:|
| 登录 → 修复 1 条失败用例 | 18 | 10 | **-44%** |
| 单用例调试循环（5 次往返） | 13 | 7 | **-46%** |
| 首次创建 Project 跑通首个 Suite | 22 | 14 | **-36%** |
| 跨 Project 查看 Run | 6 | 3 | **-50%** |
| Dashboard → Project 概览 | 3 | 1 | **-67%** |
| Case 列表 → 单用例执行 | 5 | 2 | **-60%** |
| Suite 详情 → 执行 Suite | 3 | 1 | **-67%** |
| Run 详情 → 回到原 Run 列表 | 2 | 1 | **-50%** |

---

## ⑬ 边界场景处理

### 13.1 用户无 Project

- Dashboard 不显示 Recent Projects 区，显示 "**你还没有 Project，去创建第一个**" 空态卡片。
- L1 Sider 主菜单仍显示 Dashboard / Project 列表，**不显示** "当前 Project" 分组。
- 用户点 "新建 Project" → 表单 → 保存 → 自动跳该 Project 概览。

### 13.2 用户被踢出 Project（owner 变更）

- Project Switcher 选中失效 Project 时，**不报错**，自动降级到 Dashboard 并 Toast "你已不是 Project X 的成员"。
- 仍在 Project 内页面时，后端返回 403，前端跳 403 错误页，提供 "返回 Dashboard" 按钮。

### 13.3 用户删除当前 Project

- 删除成功后跳 Project 列表，并 Toast "已删除"。
- Recent Projects 中该 Project **立即失效**（下次访问 API 失败时清除）。

### 13.4 Token 失效

- 当前页请求失败时，**不立即跳登录**；先尝试 Refresh Token。
- Refresh 失败 → 保存当前 URL 到 `sessionStorage["app.returnTo"]` → 跳登录。
- 登录成功后**自动回到原 URL**。

### 13.5 浏览器直接访问深链

- URL 是 `/projects/:id/workspace/report/:runId` → 先校验 Project 存在性 + 用户权限：
  - ✅ 通过 → 加载页面
  - ❌ 404 / 403 → 错误页
- 不要求用户先访问 Dashboard。

### 13.6 慢网络

- 路由切换 Loading 时间超过 3 秒 → Loading 骨架上显示 "数据加载较慢，请稍候"。
- 不弹 Modal，不打断用户。

---

## ⑭ 验收指标

| 指标 | 计算方式 | 目标 |
|---|---|---|
| **主流程平均点击数** | 5 个主流程点击数平均 | ≤ 12 |
| **迷失率** | 用户在 1 分钟内点击 Back / 面包屑 ≥ 3 次的会话占比 | ≤ 5% |
| **Project 切换上下文错位率** | 切换后 URL 中残留旧 Project ID 的比例 | 0% |
| **Recent Project 使用率** | 从 Dashboard 进入 Project 的会话中，经 Recent Project 卡片进入的比例 | ≥ 60% |
| **Breadcrumb 点击率** | 用户从详情页通过面包屑返回上级 vs 通过 Back 按钮的比例 | 50% / 50% |
| **Drawer / Modal 误关闭率** | 用户在提交期间因误触关闭 Drawer 的比例 | ≤ 1% |
| **执行完成自动跳转率** | Run 完成后自动跳 Report 的成功率 | 100% |
| **保存后自动回跳率** | 编辑保存后自动回到来源页的成功率 | 100% |

---

## ⑮ 实施优先级

按"价值 / 改动量"排序：

| # | 任务 | 优先级 | 估时 | 价值 |
|---:|---|---|---:|---|
| 1 | Breadcrumb 三级结构 + URL Query 持久化 | P0 | 2 天 | 高 |
| 2 | Project Switch 三层策略（A/B/C）+ 切换器 UI 改版 | P0 | 3 天 | 高 |
| 3 | Recent Projects 卡片（localStorage + Dashboard） | P0 | 2 天 | 高 |
| 4 | PageHeader "返回"按钮 + Back 等价 | P0 | 1 天 | 高 |
| 5 | "保存并执行" 合并按钮 + Drawer 预填 | P1 | 2 天 | 中 |
| 6 | Run 详情默认 Tab = Failures | P1 | 0.5 天 | 中 |
| 7 | Workspace 引导改为串行 Drawer | P1 | 3 天 | 中 |
| 8 | 列表行信息前置（Case / Suite / Run） | P2 | 2 天 | 中 |
| 9 | Result 详情 "修改 + 再执行" 一键 | P2 | 1 天 | 中 |
| 10 | 全局快捷键 `Ctrl+K`（搜索） | P3 | 3 天 | 低（未来扩展） |

---

## ⑯ 不在本期范围

为避免范围蔓延，下列能力**不**在 v1.0 Navigation UX 范围：

- 项目收藏 / 标签 / 多 Project 协同
- 全局搜索（依赖后端聚合接口，本期未提供）
- 通知中心 / 邮件 / 飞书 / 钉钉集成
- 移动端原生 App
- 离线访问 / PWA
- AI 助手 / 自然语言查询
- 时间线视图 / 活动流

---

## 附录 A · 导航能力清单

| 能力 | 实现位置 | 数据源 | 是否需要后端配合 |
|---|---|---|---|
| **Breadcrumb** | L1 / L2 / L3 PageHeader | URL Path | ❌ |
| **Recent Projects** | Dashboard 卡片 + Project Switcher 顶部 | localStorage | ❌ |
| **Back 按钮** | L3 PageHeader 左侧 | URL Query | ❌ |
| **Browser Back** | 浏览器原生 | history API | ❌ |
| **Project Switch（3 层策略）** | L1 Sider Project Switcher | URL Path + 对象查询 | ⚠️ 查询 Suite/Case 是否跨 Project 共享 |
| **登录后默认落点** | 登录成功后跳转逻辑 | localStorage（recentProjects） | ❌ |
| **保存后自动回跳** | 编辑器保存逻辑 | URL Query `returnTo` | ❌ |
| **执行完成自动跳 Report** | Run 提交成功回调 | URL Path | ❌ |
| **离开前确认** | 全局导航守卫 + Popconfirm | 组件 dirty state | ❌ |

**结论：所有 Navigation UX 能力均通过前端路由 / URL Query / localStorage 实现，零后端改动。**

---

## 附录 B · URL Query 命名规范

为支持 Back / Forward / 状态持久化，统一约定：

| Query Key | 用途 | 出现页 |
|---|---|---|
| `?search=` | 搜索关键字 | 列表页 |
| `?page=` | 分页 | 列表页 |
| `?size=` | 每页条数 | 列表页 |
| `?status=` | 状态筛选 | Run / Result 列表 |
| `?method=` | HTTP Method 筛选 | Case 列表 |
| `?tab=` | 当前 Tab | 详情页 |
| `?returnTo=` | 编辑后回跳目标 | 编辑器 |
| `?scope=` | 执行范围 | Run Center / Drawer |
| `?from=` | 来源标识（调试用） | 跨模块跳转 |

所有 Query 在 URL 中**显式可见**，方便 Back / Forward 恢复。

---

## 附录 C · 关键状态机

### C.1 详情页 Back 状态机

```text
[进入详情页]  → 记录来源 URL 到 ?returnTo=
                  ↓
[用户操作]  → dirty = true (有未保存)
                  ↓
[用户触发 Back / 点返回]  → if dirty: Popconfirm
                              else: navigate(URL(returnTo) or back())
```

### C.2 Project Switch 状态机

```text
[用户在 Project A 任意页]
        ↓
[点击 Project Switcher，选 Project B]
        ↓
[判断当前页类型]
  ├─ L2 列表页 → 策略 A → 跳 Project B 同名模块
  ├─ L3 详情页 → 策略 B → 查询 B 是否存在同名对象
  │                ├─ 是 → 跳 B 同名对象详情
  │                └─ 否 → 跳 B 同模块列表
  └─ Run / Result → 策略 C → 跳 B 报告列表
        ↓
[如有 dirty → Popconfirm]
[如有运行中 Run → Modal 警告]
        ↓
[执行切换：清理旧 Project 上下文 + 跳转 + 记录 Recent Projects]
```

### C.3 登录后落点状态机

```text
[登录成功]
        ↓
[读取 localStorage.app.recentProjects]
        ↓
[判断]
  ├─ 有 Recent Project 且 7 天内访问 → 直接跳该 Project 概览
  ├─ 有 Recent Project 但 > 7 天 → 跳 Dashboard
  └─ 无 Recent → 跳 Dashboard
        ↓
[如有合法 returnTo URL（sessionStorage） → 优先跳 returnTo]
```

---

## 附录 D · 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-15 | 初版：三层心智模型 / Breadcrumb / Recent Project / Back / Project Switch / 点击削减 / 反迷失 / 4 条路径重设计 / 8 项验收指标 |

---

**约束再确认**

- ❌ 不修改任何业务逻辑
- ❌ 不新增任何 API
- ❌ 不修改数据库
- ✅ 仅规范导航行为与跳转关系，所有能力通过前端路由 / URL Query / localStorage 实现