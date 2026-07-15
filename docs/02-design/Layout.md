# API 自动化测试平台 · Layout 规范

> 版本：v1.0  
> 适用范围：API 自动化测试平台前端（React 18 + Ant Design 5.x）  
> 配套：`DesignSystem.md`（视觉 Token）、`INFORMATION_ARCHITECTURE.md`（导航结构）  
> 约束边界：**仅规范布局结构与交互行为，不修改任何业务、不新增 API、不改动数据库**

---

## 0. 文档定位

本文件定义平台**统一的页面骨架**：所有受保护页面（除登录页外）共享同一套外壳（Shell），所有 Project 内页面在 Shell 之内再叠加一套**项目工作区骨架**（Workspace）。任何新增页面必须按本规范"对号入座"，不得自创外壳。

设计骨架分两层：

| 层级 | 名称 | 出现页面 |
|---|---|---|
| **L1 · 应用外壳（App Shell）** | 顶栏 + 左侧主导航 + 内容区 | 全部已登录页面 |
| **L2 · 项目工作区（Project Workspace）** | 项目头 + 工作区左侧导航 + 内容区 + 右侧上下文面板 | 进入某个 Project 后的所有页面 |

---

## ① 布局总览

### 1.1 信息层级

```text
┌──────────────────────────────────────────────────────────────────┐
│  L1 应用外壳 (App Shell)                                           │
│  ┌────────┬─────────────────────────────────────────────────────┐ │
│  │        │  Header（顶栏 · 64px 高 · 全局）                       │ │
│  │        ├─────────────────────────────────────────────────────┤ │
│  │ Sider  │                                                     │ │
│  │ 主导航 │  Content（内容区 · 全宽，最大 1600px 居中）              │ │
│  │ 248/72 │  ┌────────────────────────────────────────────────┐  │ │
│  │        │  │  L2 项目工作区（仅 Project 内页面才有）           │  │ │
│  │        │  │  ┌──────────────────────────────────────────┐  │  │ │
│  │        │  │  │ Workspace Header（项目头 · 居中）         │  │  │ │
│  │        │  │  ├──────┬───────────────────────┬─────────┤  │  │ │
│  │        │  │  │ 内Sider│ Workspace Content     │ 右侧   │  │  │ │
│  │        │  │  │ 240   │  （各业务页面）          │ 上下文 │  │  │ │
│  │        │  │  │      │                       │ 280    │  │  │ │
│  │        │  │  └──────┴───────────────────────┴─────────┘  │  │ │
│  │        │  └────────────────────────────────────────────────┘  │ │
│  └────────┴─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 路由与布局对应关系

| 路由形态 | 布局 |
|---|---|
| `/login` | **无外壳**，全屏单页布局（独立于 App Shell） |
| `/dashboard`、`/projects`、`/admin/*` | **L1 App Shell** |
| `/projects/:projectId/workspace/**` | **L1 App Shell + L2 Workspace** |
| 受保护路由在数据未就绪前 | **L1 App Shell + 全屏 Loading 骨架** |

---

## ② Header（顶栏）

### 2.1 位置与尺寸

| 属性 | 值 |
|---|---|
| 位置 | 顶部，固定吸顶（`position: sticky; top: 0`） |
| 高度 | **64 px**（所有断点统一） |
| 水平 padding | 左右各 **28 px**（≥ 1100px 视窗）；**18 px**（< 820px 视窗） |
| 背景 | `--bg-surface` + 92% 不透明 + `backdrop-filter: blur(12px)` |
| 下边线 | `1px solid var(--border-default)` |
| Z-Index | **15**（在 Sider 之下，避免遮挡 Sider 顶角） |

### 2.2 内容分区

Header 沿水平方向分三段：

| 区段 | 位置 | 内容 |
|---|---|---|
| **左** | 左对齐 | **预留**（不放置 Logo，Logo 在 Sider 顶部）。可在桌面端放置"面包屑"备选 |
| **中** | 居中 | **空白**，用于未来扩展（搜索、通知）；当前保持空 |
| **右** | 右对齐 | 用户账号区（Avatar + 用户名）→ Dropdown（修改密码 / 退出登录） |

### 2.3 用户账号区

- **Avatar** 尺寸 28 px，圆形；图标兜底 `UserOutlined`。
- **用户名** 最大宽度 160 px，超出 `text-overflow: ellipsis`。
- **Dropdown 触发**：点击按钮展开，不使用 Hover（避免误触）。
- **Dropdown 项**：当前账号（禁用）/ 修改密码 / 分隔线 / 退出登录（danger）。

### 2.4 行为

- 滚动时 Header 不收起、不变窄。
- 不承载任何"创建 / 编辑"等业务操作入口。
- 不展示当前 Project 名称（Project 切换器在 Sider 顶部，不进入 Header）。

---

## ③ Sidebar（左侧主导航 · L1）

### 3.1 位置与尺寸

| 属性 | 值 |
|---|---|
| 位置 | 左侧，固定（`position: sticky; top: 0; height: 100vh`） |
| 宽度（展开） | **248 px** |
| 宽度（折叠） | **72 px** |
| 折叠切换 | **底部"折叠 / 展开"按钮**，不是 hover 自动折叠 |
| 背景 | `--bg-surface` |
| 右侧阴影 | `--shadow-sider`（轻量描边阴影） |
| 内部滚动 | `overflow: hidden auto`，仅菜单区域可滚动，Logo / Switcher / 折叠按钮吸顶 / 吸底 |

### 3.2 垂直分区

自上而下分为四段：

| 段 | 内容 | 高度 |
|---|---|---|
| ① Brand 区 | Logo + 产品名 | 64 px |
| ② Project 切换器 | 当前 Project 下拉（仅当已进入 Project 时显示） | 自适应，约 64 px |
| ③ 主菜单区 | 菜单（Dashboard / Project / 当前 Project / 系统管理） | `flex: 1`，独立滚动 |
| ④ 折叠按钮 | 吸底 | 自适应 |

### 3.3 Brand 区

- 全宽按钮（`width: 100%`），点击跳转 `/dashboard`。
- **Logo Mark**（32×32 px）：圆角 9 px，品牌渐变背景，`ApiOutlined` 图标。
- **产品名** "API Test Hub"（17 / 700 / letter-spacing -0.2 px）：折叠时隐藏。
- 不承载 Project 切换；切换在下一段。

### 3.4 Project 切换器

- **位置**：Brand 区正下方，仅当 URL 包含 `/projects/:id` 时渲染。
- **行为**：
  - 切换时保留当前模块（Environment / Suite / Case / Run / Report / Settings），回到对应模块的列表页（解决 UX H1：上下文不重置）。
  - 不重新加载整页，仅路由跳转。
  - 切换过程不关闭已打开的 Drawer / Modal（如有，先拦截）。
- **搜索**：内置 `showSearch`，按名称过滤。
- **空数据**：`status="error"` 显示错误态，正常态显示 "加载中…"。**不在切换器内显示 "无 Project" 字样**，引导通过 Dashboard 创建。

### 3.5 主菜单

| 分组 | 项 | 图标 | 显隐 |
|---|---|---|---|
| 工作台 | Dashboard | `DashboardOutlined` | 始终 |
| 项目 | Project 列表 | `ProjectOutlined` | 始终 |
| 当前 Project（仅已选 Project） | 分组标题（折叠时隐藏文字） | — | Project 已选 |
| └ | 项目概览 | `AppstoreOutlined` | Project 已选 |
| └ | 环境管理 | `DatabaseOutlined` | Project 已选 |
| └ | 测试资产 › 测试套件 | `FolderOpenOutlined` | Project 已选 |
| └ | 测试资产 › API 用例 | `ApiOutlined` | Project 已选 |
| └ | 执行中心 | `PlayCircleOutlined` | Project 已选 |
| └ | 测试报告 | `FileSearchOutlined` | Project 已选 |
| └ | 项目设置 | `SettingOutlined` | Project 已选 |
| 系统管理 | 用户管理 | `TeamOutlined` | 仅 superuser |
| 系统管理 | 角色管理 | `SafetyCertificateOutlined` | 仅 superuser |

- 默认展开分组：`测试资产`（一次进入 Project 后始终展开）。
- 折叠态：图标 + Tooltip，不显示文字（避免折行）。
- 选中态：背景 `--bg-muted`，左侧 3 px 主色高亮条（由 AntD Menu 内置）。
- 折叠切换按钮 Tooltip 文案动态切换："收起菜单" / "展开菜单"。

### 3.6 折叠按钮

- 吸底，绝对定位 `bottom: 16px`，左右各缩进 12 px。
- 高度 32 px，宽度 `calc(100% - 24px)`，文字按钮（`type="text"`）。
- 图标：`MenuFoldOutlined` / `MenuUnfoldOutlined`。

---

## ④ Breadcrumb（面包屑）

### 4.1 位置

- **位置 1**：L1 Content 顶部，位于 PageHeader 上方，距离 12 px。
- **位置 2**（仅 Project 内）：可同时在 Workspace Header 内以"次级面包屑"形式存在（`项目 / 测试套件 / 冒烟回归`）。

### 4.2 分隔符

- 默认 `/`，中文环境允许替换为 `›`（AntD `<Breadcrumb separator>`）。
- 字号 Caption Small（12 / 18）。

### 4.3 内容层级

| 场景 | 面包屑链 |
|---|---|
| Dashboard | （无面包屑） |
| Project 列表 | `工作台 / 项目` |
| Project 概览 | `工作台 / 项目 / 用户服务 API / 概览` |
| Suite 详情 | `项目 / 用户服务 API / 测试套件 / 冒烟回归` |
| Run 报告详情 | `项目 / 用户服务 API / 测试报告 / Run #20260715` |
| Result 详情 | `项目 / 用户服务 API / 测试报告 / Run #20260715 / Result #3` |
| 用户管理 | `系统管理 / 用户管理 / user@example.com` |

### 4.4 行为

- **最后一项不可点击**（当前页）。
- 中间项点击跳转对应"规范列表 / 概览"页面（详见 `INFORMATION_ARCHITECTURE.md`）。
- URL 中 `tab / page / search` 等查询参数变化**不改变**面包屑。
- 当面包屑超过 5 级时，**首段省略为 "…"**，避免横向溢出。

---

## ⑤ Content（内容区）

### 5.1 容器

| 属性 | 值 |
|---|---|
| 宽度 | **最大 1600 px 居中**，左右自动外边距 |
| 高度 | `min-height: calc(100vh - 64px)`，确保页脚不浮空 |
| 水平 padding | **28 px / 32 px**（≥ 1100px）；**22 px / 18 px**（< 820px） |
| 底部 padding | **48 px**（确保最后一块内容不贴底） |

### 5.2 内部结构

每个内容页统一由三段堆叠：

| 段 | 说明 |
|---|---|
| **PageHeader** | 面包屑 + 标题 + 副标题 + Extra（主操作）。`margin-bottom: 22 px` |
| **Toolbar**（可选） | 搜索 / 筛选 / 次操作，与下一段间距 16 px |
| **Body** | 业务内容（Card / Table / Form）。卡片间距 24 px |

### 5.3 页面空白

- 内容不足一屏时，Body 区域保持自然高度；不要强制拉伸。
- 不出现"全屏空白 + 居中 Logo"假加载。
- 内容超过一屏时启用 **Content 滚动**（见 ⑩）。

---

## ⑥ Footer（页脚）

### 6.1 位置

- **位于 L1 Content 内部底部**，不进入全局吸底吸底条。
- 仅在"全屏信息页"（如 Dashboard 空态、错误页）出现。
- 业务页（Project 内、列表页）**不显示** Footer，避免噪声。

### 6.2 内容

| 列 | 内容 |
|---|---|
| 左 | 产品名 + 版本号（`API Test Hub · v0.1.0`） |
| 中 | 文档 / 帮助 / 问题反馈链接（未来扩展） |
| 右 | 版权 + 当前年份 |

### 6.3 规格

- 高度 56 px，背景 `--bg-muted`，上边线 `1px solid var(--border-default)`。
- 字号 Caption Small（12 / 18），颜色 `--text-secondary`。
- 不承担任何业务操作。

---

## ⑦ Project Workspace（L2 · 项目工作区）

> 仅在 `/projects/:projectId/workspace/**` 路由下生效；与 L1 App Shell 嵌套，不替换 L1。

### 7.1 整体容器

- **外层卡片** `.workspace-shell`：`display: flex; flex-direction: column; gap: 18 px`。
- 距 L1 Content 边缘自然对齐；Workspace 自身**没有自己的滚动条**，滚动由 L1 Content 接管。

### 7.2 Workspace Header（项目头）

| 属性 | 值 |
|---|---|
| 高度 | 自适应，约 **96~112 px**（带摘要时可更高） |
| 背景 | `--bg-surface` + 92% 透明 + `backdrop-filter: blur(12px)` |
| 边框 | `1px solid var(--border-default)` |
| 圆角 | `--radius-xl` (14 px) |
| 阴影 | `--shadow-md` |
| 内边距 | `18 px 24 px` |
| 位置 | L2 顶部，**不吸顶**（被 L1 Header 自然遮挡） |

### 7.3 Workspace Header 内容

水平三段：

| 段 | 内容 |
|---|---|
| **左** | Avatar（48×48 圆角方形 + 品牌渐变 + 项目名首字母） + 项目名（H3）+ Tag "Project" + 描述 / Owner / 更新时间（次级信息） |
| **中** | 配置就绪度 Tag 列表：环境 / 默认环境 / Suite / Case；通过 / 未就绪用不同 Tag 色 |
| **右** | "最近执行"按钮（仅当存在 Run 时显示）+ "快速执行"（Primary）+ "刷新" |

### 7.4 Workspace Body（项目主体）

采用 **三列 Grid**：

| 列 | 宽度 | 内容 |
|---|---|---|
| **左 · 内 Sider** | 240 px | 工作区模块导航（见 7.5） |
| **中 · Workspace Content** | `minmax(0, 1fr)` | 业务页面（Outlet） |
| **右 · Context Panel** | 280 px | 项目上下文（环境 / 最近 Run / 配置就绪度） |

**响应式降级**：

| 断点 | 布局变化 |
|---|---|
| ≥ 1280 px | 完整三列 |
| 960~1280 px | 右侧 Context Panel 移至底部，与左侧 Sider 同行（两列） |
| < 960 px | Sider 与 Context Panel 均**塌缩为顶部抽屉 / Accordion** |

### 7.5 内 Sider（Workspace Sider）

| 属性 | 值 |
|---|---|
| 位置 | Workspace Body 左列 |
| 宽度 | 240 px |
| 背景 | `--bg-surface` |
| 圆角 | `--radius-xl` |
| 边框 | `1px solid var(--border-default)` |
| 内边距 | `16 px 0` |
| 位置（sticky） | `top: 84 px`（L1 Header 64 + 间距 20） |

**菜单项**：

| 顺序 | 模块 | 图标 | 显隐 |
|---:|---|---|---|
| 1 | 概览 | `AppstoreOutlined` | 始终 |
| 2 | 环境 | `DatabaseOutlined` | 已配置环境（未配置显示 · 标记） |
| 3 | 套件 | `FolderOpenOutlined` | 已存在 Suite |
| 4 | 用例 | `ApiOutlined` | 已存在 Case |
| 5 | 执行 | `PlayCircleOutlined` | 已配置环境 |
| 6 | 报告 | `FileSearchOutlined` | 已存在 Run |
| 7 | 导入 | `ImportOutlined` | 已存在 Suite |
| 8 | 信息 | `SettingOutlined` | 始终 |

- 顶部 "项目工作区" 分组标题（12 / 600 / All-Caps / `--text-secondary`）。
- 未就绪模块右侧以 `·` 角标（`workspace-sider-flag`，`--color-warning`）。
- 不折叠（与 L1 Sider 不同：L2 空间宝贵，菜单不可压缩到图标态）。

### 7.6 Workspace Content（业务主区）

| 属性 | 值 |
|---|---|
| 背景 | `--bg-surface` |
| 圆角 | `--radius-xl` |
| 边框 | `1px solid var(--border-default)` |
| 内边距 | **24 px** |
| 最小高度 | **480 px**（保证下方不显空洞） |
| 滚动 | 由 L1 Content 整体接管；Workspace Content **自身不滚动** |

### 7.7 Context Panel（右侧上下文面板）

| 属性 | 值 |
|---|---|
| 宽度 | 280 px |
| 位置 | sticky（与 Sider 同步），`top: 84 px` |
| 圆角 | `--radius-xl` |
| 边框 / 阴影 | 与 Workspace Content 一致 |
| 内边距 | `16 px` |
| 子 Card 间距 | 18 px |

**子模块**：

1. **默认环境卡**：环境名 + Base URL + 复制按钮 + "未设置"占位。
2. **最近执行卡**：最近 1 条 Run + 状态 + 通过率 + 跳转按钮。
3. **配置就绪度卡**：环境 / 默认环境 / Suite / Case / Run 5 项打勾。
4. **快速操作卡**：新建环境 / 新建 Suite / 新建 Case 三个快捷入口（按就绪度动态显隐）。

### 7.8 Soft Alert

- 位置：L2 最底部，与 Content 之间间距 16 px。
- 触发：未设置默认环境时显示一条 warning。
- 行为：可关闭（关闭后本次会话内不再出现，刷新页面恢复）。

---

## ⑧ Responsive（响应式）

### 8.1 断点

| 名称 | 视窗宽度 | 说明 |
|---|---|---|
| `xs` | < 480 px | 手机（次要场景，主要优化对象是桌面） |
| `sm` | 480~820 px | 平板竖屏 |
| `md` | 820~1100 px | 平板横屏 / 小笔记本 |
| `lg` | 1100~1280 px | 标准笔记本 |
| `xl` | ≥ 1280 px | 桌面 / 大屏 |

### 8.2 各断点下的布局行为

| 断点 | L1 Sider | L1 Content | L2 Sider | L2 Content | Context Panel |
|---|---|---|---|---|---|
| **xs / sm** | **自动折叠为 0**（通过汉堡按钮打开抽屉式） | 占满 | 不显示（折叠到下拉菜单） | 占满 | 不显示（折叠到顶部折叠区） |
| **md** | 自动折叠为 72 px（图标态） | padding 18 px | 220 px | 1fr | 移到下方 |
| **lg** | 248 px（默认展开） | padding 22 px | 240 px | 1fr | 280 px |
| **xl** | 248 px（默认展开） | padding 28 px / 32 px | 240 px | 1fr | 280 px |

### 8.3 响应式规则

1. **断点切换发生在不破坏状态**：表格分页 / 筛选 / Drawer 不因断点变化而清空。
2. **不支持的设备**（如 < 480 px）：不强行优化，仅保证**不报错**；提示"建议在桌面浏览器使用"。
3. **横屏 / 竖屏切换**：以视窗宽度为准，竖屏视为窄屏。
4. **打印**：不做特殊样式（产品场景不需要）。
5. **键盘 / 鼠标拖拽改变窗口大小**：实时响应，不做节流。

### 8.4 移动端策略

- 不投入大量精力优化 < 820 px 的体验。
- < 820 px 时**默认进入"桌面建议"占位页**，引导用户在桌面浏览器打开。
- 关键操作（查看最近 Run / 切 Project）通过顶部 Hamburger Menu 提供。

---

## ⑨ 折叠菜单（Collapse Menu）

### 9.1 触发

| 触发方式 | 行为 |
|---|---|
| 点击 Sider 底部"折叠 / 展开"按钮 | 立即折叠 / 展开，状态写入 localStorage |
| 自动折叠 | 仅在响应式断点切换时（< 1100 px 自动折叠为 72 px；< 820 px 自动折叠为 0） |
| 手动折叠状态 | 优先级高于自动折叠；用户偏好在视窗变化时仍生效 |

### 9.2 折叠状态规格

| 状态 | 宽度 | 显示内容 |
|---|---|---|
| **展开** | 248 px | Brand（Logo + 文字）+ Project Switcher + 菜单文字 |
| **图标态** | 72 px | Brand（仅 Logo）+ Project Switcher 折叠为图标按钮 + 菜单图标 + Tooltip |
| **隐藏态** | 0 | 完全隐藏，Top Header 出现汉堡按钮触发 Drawer |

### 9.3 状态持久化

- 折叠 / 展开状态保存到 `localStorage`（key：`app.sider.collapsed`）。
- 用户偏好与视窗宽度取**较窄值**：例如用户手动展开到 248，但视窗缩小到 md，则按 72 图标态展示；下次视窗恢复，记忆展开。
- 登出 / 切换账号时不重置偏好。

### 9.4 折叠态菜单交互

- 折叠态下菜单项仅显示图标，**Hover 显示 Tooltip** 完整文字。
- 分组标题（如 "当前 Project"、"系统管理"）折叠时不显示，依赖图标 + 间距自然分组。
- 折叠态不允许**展开子菜单到侧边浮层**（保持简洁，依赖 Tooltip）。

---

## ⑩ 页面宽度

### 10.1 内容区最大宽度

| 区域 | 最大宽度 | 居中策略 |
|---|---:|---|
| **L1 Content** | **1600 px** | `margin: 0 auto` |
| **L2 Workspace** | **1400 px** | `margin: 0 auto`（含 Header + Body） |
| **表单页** | **760 px**（如 Run 表单）或 **640 px**（如新建 Suite） | `margin: 0 auto` 或贴左 |
| **登录页** | 100% | 双栏 1.1 : 0.9 网格 |

### 10.2 卡片 / 表格宽度策略

| 场景 | 策略 |
|---|---|
| **Dashboard 指标卡** | Grid 12 栏，按内容跨度 span-3 / 4 / 6 / 8 |
| **列表表格** | 占满 Content；列宽固定，行高 56 px |
| **详情页** | 双列 Grid，左 8 栏主内容 + 右 4 栏元数据 |
| **报告页** | 占满 Content；内部按模块分块 |
| **窄屏（< 820 px）** | 所有 Grid 强制 span-12 |

### 10.3 宽度使用守则

1. **不强制最小宽度导致横向滚动**（除非 Table 数据本身需要）。
2. **页面宽度变化时，Content 宽度等比例变化**，但卡片内边距不变。
3. **表格不出现"列无限挤压"**：当视窗窄于阈值，表格启用横向滚动（容器 `overflow-x: auto`）。
4. **登录页宽度例外**：保持桌面布局，不响应式塌缩。

---

## ⑪ 滚动策略

### 11.1 滚动容器分层

平台滚动分为**三层**，互不嵌套：

| 层 | 滚动容器 | 滚动谁 |
|---|---|---|
| **文档滚动** | `<html>` / `<body>` | L1 Content 之外的全部内容 |
| **L1 Content 滚动** | `.app-content` 内部 | 内容区 |
| **局部滚动** | 单个组件（Drawer Body / Table 容器 / JsonPreview / Modal Body） | 局部内容 |

### 11.2 各区域滚动策略

| 区域 | 是否滚动 | 行为 |
|---|---|---|
| L1 Sider | **自身滚动**（仅菜单） | `overflow: hidden auto`；Brand / Switcher / 折叠按钮吸顶 / 吸底 |
| L1 Header | 否 | 固定吸顶 |
| L1 Content | 否（由文档滚动接管） | 自然高度，不嵌套滚动条 |
| L2 Sider | 否 | 与 Workspace Content 一起被文档滚动；Context Panel sticky |
| L2 Context Panel | 否 | sticky 跟随 |
| Workspace Content | 否 | 与 L1 一致 |
| Workspace Header | 否 | 跟随文档滚动，**不吸顶** |
| Table 容器 | **横向滚动**（窄屏时启用） | 仅当列总宽 > 容器宽 |
| Drawer / Modal Body | **自身滚动** | `overflow: auto`，Header / Footer 固定 |
| JsonPreview | **自身滚动** | `overflow: auto`，等宽字体 |

### 11.3 滚动条样式

- **Webkit**：`::-webkit-scrollbar { width: 8 px; height: 8 px; }`。
- **颜色**：轨道透明，滑块 `rgba(31, 45, 80, 0.18)`；Hover `rgba(31, 45, 80, 0.30)`。
- **不抢占布局**：滚动条宽度不计入内容（避免切换滚动 / 不滚动时布局抖动）。
- **移动端**：保留原生滚动条样式，不做自定义。

### 11.4 滚动行为

- **锚点跳转**：使用 `scroll-behavior: smooth`（仅锚点，**禁止**给整个文档开启）。
- **路由切换**：新页面的滚动位置回到顶部（**不保留旧页面滚动位置**，避免上下文混乱）。
- **Drawer / Modal 打开**：底层文档滚动锁定（`overflow: hidden`）。
- **保存滚动位置**：列表筛选 / 搜索变化时**保留**滚动位置；切换路由时**不保留**。
- **键盘滚动**：支持 `↑ / ↓ / Page Up / Page Down / Home / End`。

### 11.5 禁止事项

- ❌ 同一页面嵌套多层滚动条（"页面滚动 + Content 滚动 + Table 滚动"）。
- ❌ 使用 JS 控制 `scrollTop` 实现"自动滚动到某元素"，**必须用锚点 + `scrollIntoView`**。
- ❌ 关闭页面级滚动条后用 JS 模拟滚动行为。
- ❌ Drawer 内部再出现 Drawer 滚动嵌套。

---

## ⑫ Z-Index / 层叠模型

为避免覆盖冲突，全局 Z-Index 阶梯固定：

| 层级 | 值 | 内容 |
|---|---:|---|
| 基础内容 | `0` | 文档流、Card、Table |
| 浮动 Tag / 徽标 | `2` | 表格右上角 Tag、状态徽标 |
| **L1 Sider** | **20** | 固定吸顶侧栏 |
| **L1 Header** | **15** | 顶栏（在 Sider 之下，避免遮挡侧栏角落） |
| Dropdown / Tooltip | `1050` | AntD 默认 |
| **Backdrop（Drawer / Modal 遮罩）** | `1000` | AntD 默认 |
| **Drawer Panel** | `1010` | AntD 默认 |
| **Modal Panel** | `1050` | AntD 默认 |
| **Message / Notification** | `1100` | AntD 默认（永远在最上） |
| 全局 Loading Mask | `1200` | 全屏加载遮罩，遮挡 Modal |
| Dev Tools / Debug | `9999` | 仅开发态 |

新增浮层组件必须按上表选择层级；不得使用 `9999` 抢覆盖。

---

## ⑬ 无障碍 / 键盘

### 13.1 焦点

- **Tab 顺序**：从左到右、从上到下，符合视觉顺序。
- **Sider / Header / Content** 视为独立焦点区，**不跨区**回跳。
- **Modal / Drawer 打开**：焦点自动落到主操作按钮；关闭后回到触发元素。
- **可见的焦点环**：所有可聚焦元素必须有 `outline: 2px solid var(--color-primary); outline-offset: 2px`。

### 13.2 快捷键

| 快捷键 | 行为 |
|---|---|
| `Ctrl/Cmd + K` | （未来）全局搜索 |
| `Esc` | 关闭顶层 Modal / Drawer / Dropdown |
| `← / →` | Breadcrumb 切换（仅当焦点在面包屑时） |
| `↑ / ↓` | 同级菜单项切换 |

### 13.3 Skip Link

- 提供 "跳到主内容" 隐藏链接，键盘 `Tab` 第一次聚焦时显示。
- 链接跳转到 `.app-content` 区域，并设置焦点。

---

## ⑭ Loading / 状态遮罩

### 14.1 全屏 Loading

- **触发**：路由 Suspense fallback、App Shell 内 React Query 初次加载且无缓存。
- **位置**：L1 Content 内部，**不覆盖 Sider / Header**。
- **样式**：骨架屏（Skeleton）或 Spin + 占位块（`min-height: 220 px`）。
- **持续超过 3 秒**：附加文案 "数据加载较慢，请稍候"。

### 14.2 区块 Loading

- **触发**：Tab 切换、Drawer 内表单加载。
- **样式**：Card 内部 `<Skeleton active paragraph={{ rows: 4 }}>`。

### 14.3 行级 Loading

- **触发**：表格初次加载。
- **样式**：`<Table loading>` 自动渲染骨架行。

### 14.4 提交 Loading

- **触发**：任何"保存 / 执行 / 删除"按钮点击。
- **样式**：按钮变 `loading`，**禁用二次点击**；Drawer / Modal 在提交期间禁用关闭。

### 14.5 路由切换 Loading

- 切换路由时**保持旧页面**，直到新页面数据就绪再切换（避免 Loading 闪烁）。
- 切换失败时显示 `<ErrorState>` 而非空白。

---

## ⑮ 布局守则（Do / Don't）

### 15.1 必须遵守

| # | 规则 |
|---:|---|
| 1 | 所有受保护页面**必须**在 L1 App Shell 之内；不允许新建独立 Layout |
| 2 | 所有 Project 内页面**必须**在 L2 Workspace 之内；不允许脱离 Project 上下文 |
| 3 | Content 内每个页面必须按 **PageHeader → Toolbar → Body** 三段组织 |
| 4 | Sider 折叠状态必须持久化，不允许每次刷新回到默认 |
| 5 | Drawer / Modal 提交期间**必须**禁用关闭 |
| 6 | Workspace 切换 Project 时**必须**保留模块语义，不允许在详情页直接切换 |
| 7 | 任何浮层组件**必须**使用约定的 Z-Index 阶梯 |
| 8 | 滚动策略**必须**遵守三层模型，禁止嵌套滚动 |

### 15.2 禁止行为

| # | 禁止 |
|---:|---|
| 1 | 禁止在 Header 中放置业务操作入口 |
| 2 | 禁止在 L1 Sider 之外另建侧栏 |
| 3 | 禁止在 Workspace 内再嵌入一个独立的 Layout |
| 4 | 禁止 Content 内部嵌套自己的滚动容器 |
| 5 | 禁止 Modal 内出现 Table / 长列表 |
| 6 | 禁止 Drawer 内出现 Modal |
| 7 | 禁止使用 `position: fixed` 自建顶栏 / 侧栏 |
| 8 | 禁止自定义滚动条样式（除 11.3 规定的颜色） |
| 9 | 禁止在 L1 / L2 之外另建"主导航" |
| 10 | 禁止修改 Document（`<html>` / `<body>`）的滚动行为 |

---

## 附录 A · 布局 Token 速查

| Token | 值 | 来源 |
|---|---|---|
| `--header-height` | 64 px | 顶栏 |
| `--sider-width` | 248 px | L1 Sider 展开 |
| `--sider-collapsed-width` | 72 px | L1 Sider 折叠 |
| `--sider-hidden-width` | 0 px | L1 Sider 隐藏（移动态） |
| `--content-max-width` | 1600 px | L1 Content 最大宽度 |
| `--workspace-max-width` | 1400 px | L2 Workspace 最大宽度 |
| `--workspace-sider-width` | 240 px | L2 Sider 宽度 |
| `--workspace-context-width` | 280 px | L2 Context Panel 宽度 |
| `--workspace-content-min-height` | 480 px | L2 Content 最小高度 |
| `--breadcrumb-gap` | 12 px | 面包屑与 PageHeader 间距 |
| `--z-header` | 15 | Header 层 |
| `--z-sider` | 20 | Sider 层 |
| `--z-drawer-mask` | 1000 | Drawer 遮罩 |
| `--z-modal` | 1050 | Modal |
| `--z-message` | 1100 | 消息提示 |
| `--z-global-loading` | 1200 | 全屏 Loading |

---

## 附录 B · 布局断点速查

| 名称 | 范围 | L1 Sider | L1 Content Padding | L2 Body 列数 |
|---|---|---|---|---|
| `xs` | < 480 px | hidden + 汉堡 | 16 px / 12 px | 1 |
| `sm` | 480~820 px | hidden + 汉堡 | 18 px / 16 px | 1 |
| `md` | 820~1100 px | 72 px | 22 px / 18 px | 2（Sider + Content） |
| `lg` | 1100~1280 px | 248 px | 24 px / 24 px | 3 |
| `xl` | ≥ 1280 px | 248 px | 28 px / 32 px | 3 |

---

## 附录 C · 滚动 Token 速查

| Token | 值 |
|---|---|
| `--scrollbar-size` | 8 px |
| `--scrollbar-thumb` | `rgba(31, 45, 80, 0.18)` |
| `--scrollbar-thumb-hover` | `rgba(31, 45, 80, 0.30)` |
| `--scrollbar-track` | `transparent` |
| `--scroll-behavior-anchor` | `smooth` |
| `--scroll-restoration` | `manual`（路由切换回顶，列表筛选保留） |

---

## 附录 D · 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-15 | 初版：Header / Sidebar / Breadcrumb / Content / Footer / Project Workspace / Responsive / Collapse / Width / Scroll / Z-Index / A11y 全部落地 |

---

**约束再确认**

- ❌ 不修改任何业务逻辑
- ❌ 不新增任何 API
- ❌ 不修改数据库
- ✅ 仅规范布局结构与交互行为，作为前端骨架的单一真相源