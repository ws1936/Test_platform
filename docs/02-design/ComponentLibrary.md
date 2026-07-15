# API 自动化测试平台 · Component Library

> 版本：v1.0  
> 适用范围：API 自动化测试平台前端所有可复用组件  
> 配套：`DesignSystem.md`（视觉 Token）、`Layout.md`（骨架）、`NavigationUX.md`（导航规则）  
> 约束边界：**仅规范组件契约（职责 / Props / State / Events），不修改任何业务、不新增 API、不改动数据库**

---

## 0. 文档定位

本文档是平台的**组件字典**：每个被业务页面、列表页、详情页、Workspace、Drawer / Modal 复用的组件，都必须在这里有一份契约说明。约定：

| 概念 | 说明 |
|---|---|
| **职责** | 组件"做什么"与"不做什么" |
| **Props** | 组件接受的输入，包括数据 / 配置 / 回调 |
| **State** | 组件内部维护的状态（不应外泄到 Props） |
| **Events** | 组件通过回调向外通知用户行为 |
| **Variants** | 组件的主要形态变体 |
| **Used By** | 哪些页面 / 容器使用它 |

每个组件章节使用统一结构。新增组件时按同样结构追加。

---

## ① 组件分类总览

| 类别 | 数量 | 主要职责 |
|---|---:|---|
| **1. Layout & Navigation** | 8 | 页面骨架、路由壳、面包屑、菜单 |
| **2. Domain Cards** | 6 | 单个对象的卡片化呈现 |
| **3. Domain Tables** | 7 | 对象列表的表格化呈现 |
| **4. Status & Tags** | 9 | 状态徽标、Tag、Badge |
| **5. Forms** | 8 | 数据录入表单 |
| **6. Drawers & Modals** | 9 | 抽屉 / 模态框 |
| **7. States** | 4 | 空 / 加载 / 错误 / 骨架 |
| **8. Inputs** | 5 | 输入控件 |
| **9. Action Bars** | 3 | 操作栏 |
| **10. Reports** | 7 | 测试报告相关 |
| **11. Dashboard** | 7 | 工作台专用 |
| **12. Misc** | 3 | 其它工具型 |
| **总计** | **76** | — |

> 数量为初版登记数；后续随业务演进会增加。

---

## ② 全局约定

### 2.1 命名规范

| 类型 | 命名风格 | 示例 |
|---|---|---|
| 组件文件 | PascalCase | `ProjectCard.tsx` |
| Props 接口 | `ComponentNameProps` | `ProjectCardProps` |
| Event 回调 | `on[Subject][Verb]` | `onEdit`、`onDelete`、`onChange` |
| 受控值 | `value` + `onChange` | `value={x}` `onChange={setX}` |
| 内部状态 | 不暴露，不通过 Props 传入 | — |

### 2.2 通用 Props 约定

所有组件**必须**支持以下基础 Props（如适用）：

| Prop | 类型 | 说明 |
|---|---|---|
| `className` | `string` | 业务层追加 class |
| `style` | `CSSProperties` | 业务层内联样式 |
| `loading` | `boolean` | 加载态（默认 false） |
| `disabled` | `boolean` | 禁用态（默认 false） |
| `testId` | `string` | 测试 ID（QA 自动化用） |

### 2.3 状态约定

| 状态 | 触发条件 | 视觉 |
|---|---|---|
| `idle` | 默认 | 正常 |
| `loading` | 数据加载中 | Skeleton / Spin |
| `error` | 数据加载失败 | ErrorView |
| `empty` | 数据为空 | EmptyView |
| `disabled` | 不可交互 | 灰度 + cursor: not-allowed |
| `submitting` | 表单提交中 | 按钮 loading + 禁二次提交 |
| `success` | 操作成功 | Toast + 自动跳转 |

### 2.4 Event 约定

| Event | 触发时机 | 参数 |
|---|---|---|
| `onClick` | 主操作点击 | `event` |
| `onChange` | 受控值变化 | `value` |
| `onSubmit` | 表单提交 | `values` |
| `onCancel` | 取消 / 关闭 | — |
| `onConfirm` | 确认 | — |
| `onRetry` | 重试 | — |
| `onRefresh` | 刷新 | — |
| `onOpen` / `onClose` | 打开 / 关闭浮层 | — |

---

## ③ Layout & Navigation · 骨架与导航

### 3.1 `AppShell`

**职责**：L1 应用外壳。承载 Header / Sider / Content 三段，路由 Outlet 渲染受保护页面。

| Props | 类型 | 说明 |
|---|---|---|
| `children` | `ReactNode` | 路由 Outlet 内容（一般由路由系统传入） |

| State | 类型 | 说明 |
|---|---|---|
| `siderCollapsed` | `boolean` | Sider 折叠状态，持久化到 localStorage |
| `passwordModalOpen` | `boolean` | 修改密码 Modal 显隐 |
| `currentProjectId` | `string \| null` | 当前 Project（从 URL 解析） |

| Events | 参数 |
|---|---|
| `onLogout` | — |
| `onProjectSwitch` | `(nextProjectId: string) => void` |

**Variants**：仅 1 种（带 Sider + Header）。

**Used By**：所有已登录路由（`/dashboard`、`/projects`、`/admin/*`、`/projects/:id/**`）。

---

### 3.2 `ProjectWorkspaceLayout`

**职责**：L2 项目工作区外壳。提供 Project Context、并发加载项目元数据（项目 / 环境 / Suite / Case / Run），渲染 Workspace Header / Sider / Content / Context Panel。

| Props | 类型 | 说明 |
|---|---|---|
| `children` | `ReactNode` | 业务页面 Outlet |

| State | 类型 | 说明 |
|---|---|---|
| `project` | `Project \| null` | 当前 Project 详情 |
| `environments` | `Environment[]` | 环境列表 |
| `suites` | `Suite[]` | Suite 列表 |
| `caseTotal` | `number` | Case 总数 |
| `latestRun` | `TestRun \| null` | 最近 1 条 Run |
| `summary` | `ProjectRunSummary \| null` | 累计统计 |
| `readiness` | `Readiness` | 配置就绪度（环境 / Suite / Case 等） |
| `isLoading` | `boolean` | 是否初次加载 |
| `isError` | `boolean` | 是否加载失败 |

| Events | 参数 |
|---|---|
| `onRefresh` | `() => void` 刷新所有数据 |

**Used By**：`/projects/:projectId/workspace/**` 所有路由。

---

### 3.3 `PageHeader`

**职责**：每个业务页顶部统一头。承载面包屑 / 标题 / 副标题 / 主操作（Extra）。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `title` | `ReactNode` | ✅ | 页面标题（H2） |
| `description` | `ReactNode` | — | 副标题（Caption / Secondary） |
| `breadcrumbs` | `BreadcrumbItem[]` | — | 面包屑 |
| `extra` | `ReactNode` | — | 右侧主操作区 |
| `back` | `boolean` | — | 是否显示"返回"按钮（L3 详情页用） |

| State | — |

| Events | — |

**Variants**：

- **L2 模块页**：title = "模块名"，extra = "新建 / 主操作"
- **L3 详情页**：title = "对象名"，back = true，extra = "编辑 / 删除"
- **空 Dashboard**：title = "工作台"，extra 不显示

**Used By**：所有业务页。

---

### 3.4 `AppHeader`

**职责**：L1 顶栏。承载账号区（Avatar + 用户名 + Dropdown）。

| Props | 类型 | 说明 |
|---|---|---|
| `user` | `User` | 当前用户 |
| `onPasswordClick` | `() => void` | 点击修改密码 |
| `onLogout` | `() => void` | 点击退出登录 |

**Used By**：AppShell。

---

### 3.5 `AppMenu` / `WorkspaceMenu`

**职责**：L1 主菜单 / L2 工作区菜单。AntD Menu 封装。

| Props | 类型 | 说明 |
|---|---|---|
| `items` | `MenuItem[]` | 菜单项 |
| `selectedKeys` | `string[]` | 当前选中 |
| `defaultOpenKeys` | `string[]` | 默认展开 |
| `onClick` | `(key: string) => void` | 点击回调 |

**Used By**：AppShell、ProjectWorkspaceLayout。

---

### 3.6 `Breadcrumb`

**职责**：三级面包屑。依据 `INFORMATION_ARCHITECTURE.md` 的层级映射。

| Props | 类型 | 说明 |
|---|---|---|
| `items` | `BreadcrumbItem[]` | `{ title, href? }` |
| `separator` | `string` | 分隔符，默认 `/` |

**Used By**：PageHeader 内部。

---

### 3.7 `ProjectSwitcher`

**职责**：L1 Sider 顶部 Project 切换器。下拉 3 段：Recent / All / New。

| Props | 类型 | 说明 |
|---|---|---|
| `currentProjectId` | `string \| null` | 当前 Project ID |
| `recentProjects` | `Project[]` | 最近 5 个 Project |
| `allProjects` | `Project[]` | 全部 Project |
| `loading` | `boolean` | 加载态 |
| `error` | `unknown` | 错误态 |

| State | 类型 | 说明 |
|---|---|---|
| `searchKeyword` | `string` | 搜索关键字 |

| Events | 参数 |
|---|---|
| `onSwitch` | `(projectId: string) => void` |
| `onCreateNew` | `() => void` 跳新建 Project |

**Used By**：AppShell Sider。

---

### 3.8 `ProjectWorkspaceHeader`

**职责**：L2 项目头。展示项目名 / 描述 / 配置就绪度 / 最近 Run / 快速执行 / 刷新。

| Props | 类型 | 说明 |
|---|---|---|
| `project` | `Project` | 当前 Project |
| `latestRun` | `TestRun \| null` | 最近 Run |
| `defaultEnvironmentId` | `string \| null` | 默认环境 ID |
| `readiness` | `Readiness` | 配置就绪度 |

| Events | 参数 |
|---|---|
| `onQuickRun` | `() => void` 点击"快速执行" |
| `onOpenLatestRun` | `(runId: string) => void` 点击"最近执行" |
| `onRefresh` | `() => void` 点击"刷新" |
| `onTitleClick` | `() => void` 点击项目名跳概览 |

**Used By**：ProjectWorkspaceLayout。

---

## ④ Domain Cards · 领域卡片

### 4.1 `ProjectCard`

**职责**：项目卡片。展示单个 Project 的核心信息，支持点击进 Workspace。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `project` | `Project` | ✅ | Project 数据 |
| `caseCount` | `number` | — | 关联 Case 数 |
| `runCount` | `number` | — | 累计 Run 数 |
| `lastVisitedAt` | `string \| null` | — | 上次访问时间 |
| `hoverable` | `boolean` | — | 是否有 hover 抬起效果 |

| State | — |

| Events | 参数 |
|---|---|
| `onOpen` | `(projectId: string) => void` |
| `onEdit` | `(projectId: string) => void` |
| `onDelete` | `(projectId: string) => void` |

**Variants**：

- **default**：标准卡（白底 + 阴影）
- **compact**：紧凑卡（用于 Recent / Dashboard）

**Used By**：Projects 列表、Dashboard Recent Projects。

---

### 4.2 `SuiteCard`

**职责**：Suite 卡片。展示 Suite 基本信息 + 关联 Case 数 + 最近通过率。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `suite` | `Suite` | ✅ | Suite 数据 |
| `caseCount` | `number` | — | 关联 Case 数 |
| `lastRunPassRate` | `number \| null` | — | 最近通过率 |
| `lastRunAt` | `string \| null` | — | 最近执行时间 |

| Events | 参数 |
|---|---|
| `onOpen` | `(suiteId: string) => void` |
| `onEdit` | `(suiteId: string) => void` |
| `onRun` | `(suiteId: string) => void` |
| `onDelete` | `(suiteId: string) => void` |

**Used By**：Suites 列表、Dashboard Recent Suites。

---

### 4.3 `EnvironmentCard`

**职责**：环境卡片。展示 Base URL / Headers 数 / Variables 数 / 是否默认。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `environment` | `Environment` | ✅ | 环境数据 |
| `canDelete` | `boolean` | — | 是否可删除（非默认） |

| Events | 参数 |
|---|---|
| `onOpen` | `(envId: string) => void` |
| `onEdit` | `(envId: string) => void` |
| `onSetDefault` | `(envId: string) => void` |
| `onCopyBaseUrl` | `(url: string) => void` |
| `onDelete` | `(envId: string) => void` |

**Used By**：Environments 列表、Dashboard 环境摘要。

---

### 4.4 `CaseCard`

**职责**：用例卡片。单 Case 摘要，常用于 Suite 详情内。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `testCase` | `TestCase` | ✅ | Case 数据 |
| `draggable` | `boolean` | — | 是否可拖拽排序 |

| Events | 参数 |
|---|---|
| `onOpen` | `(caseId: string) => void` |
| `onRun` | `(caseId: string) => void` |
| `onRemove` | `(caseId: string) => void` 从 Suite 移除 |
| `onDragStart` | `(caseId: string) => void` |

**Used By**：Suite 详情。

---

### 4.5 `UserCard` / `RoleCard`

**职责**：用户 / 角色摘要卡。展示基本信息 + 角色 / 权限摘要。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `user` / `role` | `User` / `Role` | ✅ | 数据 |
| `roles` | `Role[]` | — | 角色列表（用于解析 roleId） |

| Events | 参数 |
|---|---|
| `onEdit` | `(id) => void` |
| `onDisable` | `(id) => void` |

**Used By**：User 管理、Role 管理。

---

## ⑤ Domain Tables · 领域表格

### 5.1 通用约定

所有 Table 组件：

| 维度 | 规范 |
|---|---|
| `rowKey` | 必须为唯一 ID（禁止 index） |
| `loading` | AntD Table `loading` prop |
| `empty` | 通过 `locale.emptyText` 接管 |
| `pagination` | `{ page, size, total, showSizeChanger, showTotal }` |
| 列宽 | 名称 ≥ 160 / 状态 100~140 / 数字 80~120 / 时间 160~200 / 操作 120~180 |
| 操作列 | `align: right`，使用 `Button type="link"` |

---

### 5.2 `ProjectTable`

| Props | 类型 | 说明 |
|---|---|---|
| `data` | `Project[]` | 数据 |
| `loading` | `boolean` | 加载态 |
| `pagination` | `PaginationConfig` | 分页 |
| `searchKeyword` | `string` | 搜索关键字 |
| `sortBy` | `string` | 排序 |

| 列 | 类型 | 渲染 |
|---|---|---|
| 名称 | `string` | `Link` + hover 色 |
| 描述 | `string` | `Typography` + ellipsis 2 行 |
| Owner | `string` | Tag |
| Case 数 | `number` | 数字 |
| 上次访问 | `string` | 相对时间 |
| 操作 | — | "进入 / 编辑 / 删除" |

---

### 5.3 `EnvironmentTable`

| 列 | 类型 | 渲染 |
|---|---|---|
| 名称 | `string` | Link |
| Base URL | `string` | `code-path` 字体 + 复制图标 |
| Headers | `number` | "N 项" |
| Variables | `number` | "N 项" |
| 是否默认 | `boolean` | "默认" Badge 或 "—" |
| 更新时间 | `string` | `formatDateTime` |
| 操作 | — | 编辑 / 设为默认 / 删除 |

**Events**：`onOpen / onEdit / onSetDefault / onCopyBaseUrl / onDelete`

---

### 5.4 `SuiteTable`

| 列 | 类型 | 渲染 |
|---|---|---|
| 名称 | `string` | Link |
| 描述 | `string` | ellipsis |
| Case 数 | `number` | 数字 |
| 最近通过率 | `number \| null` | Progress Bar + 百分比 |
| 更新时间 | `string` | format |
| 操作 | — | 详情 / 执行 / 编辑 / 删除 |

---

### 5.5 `CaseTable`

| 列 | 类型 | 渲染 |
|---|---|---|
| 启用 | `boolean` | Switch |
| Method | `HttpMethod` | `MethodTag` |
| 名称 | `string` | Link |
| Path | `string` | `code-path` |
| 所属 Suite | `string` | 多个以 Tag 列表呈现 |
| 超时 | `number` | "Ns" |
| 更新时间 | `string` | format |
| 操作 | — | 执行 / 编辑 / 删除 |

---

### 5.6 `RunTable`

| 列 | 类型 | 渲染 |
|---|---|---|
| Run ID | `string` | `#20260715-xxx` |
| 名称 | `string` | Link |
| 范围 | `RunScope` | `ScopeTag` |
| 状态 | `RunStatus` | `RunStatus` |
| 通过率 | `number` | Progress |
| 耗时 | `number` | "Xs" |
| 环境 | `string` | Tag |
| 触发人 | `string` | User ID 截断 |
| 开始时间 | `string` | format |
| 操作 | — | 详情 / 再次执行 |

---

### 5.7 `ResultTable`

| 列 | 类型 | 渲染 |
|---|---|---|
| 状态 | `ResultStatus` | `ResultStatus` |
| Method | `HttpMethod` | `MethodTag` |
| Path | `string` | Link |
| 状态码 | `number` | Status Code 彩色块 |
| 耗时 | `number` | "Xs" |
| 断言通过/失败 | `string` | "N/M" |
| 操作 | — | 详情 |

---

### 5.8 `UserTable` / `RoleTable`

| User 列 | Role 列 |
|---|---|
| 邮箱 | 名称 |
| 用户名 | 权限字符串数 |
| 昵称 | 用户数 |
| 角色 | 是否系统角色 |
| 状态（启用/禁用） | 描述 |
| superuser | 更新时间 |
| 操作：编辑 / 启停 / 重置密码 | 操作：编辑 / 删除 |

---

## ⑥ Status & Tags · 状态与标签

### 6.1 `RunStatus`

**职责**：渲染 Run 状态 Tag。根据 `pending / running / finished / failed / canceled` 映射不同 AntD 颜色。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `status` | `RunStatus` | ✅ | 状态枚举 |
| `size` | `'small' \| 'default'` | — | Tag 尺寸 |

| State | — |

| Events | — |

| 状态 | 颜色 | 文案 |
|---|---|---|
| `pending` | default | "等待中" |
| `running` | processing | "执行中" |
| `finished` | success | "已完成" |
| `failed` | error | "运行失败" |
| `canceled` | warning | "已取消" |

**Used By**：RunTable、RunStatusHeader、RunDetailHeader。

---

### 6.2 `ResultStatus`

**职责**：渲染 Result 状态 Tag。

| 状态 | 颜色 | 文案 |
|---|---|---|
| `passed` | success | "通过" |
| `failed` | error | "断言失败" |
| `skipped` | default | "已跳过" |
| `error` | volcano | "执行错误" |

**Used By**：ResultTable、ResultDetailHeader、FailureItem。

---

### 6.3 `MethodTag`

**职责**：HTTP Method 彩色 Tag。

| Method | 颜色 |
|---|---|
| GET | green |
| POST | blue |
| PUT | orange |
| PATCH | gold |
| DELETE | red |
| HEAD / OPTIONS | default |

**Used By**：CaseTable、ResultTable、CaseEditor、ResultDetail。

---

### 6.4 `ScopeTag`

**职责**：执行范围 Tag。

| Scope | 文案 |
|---|---|
| `case` | "单用例" |
| `collection` | "测试套件" |
| `project` | "整个项目" |

**Used By**：RunTable、RunExecutionDrawer、RunDetailHeader。

---

### 6.5 `DefaultBadge`

**职责**：默认标识 Badge。

| Props | 类型 | 说明 |
|---|---|---|
| `type` | `'environment' \| 'role' \| 'user'` | 类型 |
| `children` | `ReactNode` | 文案 |

**Used By**：EnvironmentTable、RoleTable。

---

### 6.6 `UserStatus`

**职责**：用户启用状态 Tag。

| 状态 | 颜色 |
|---|---|
| enabled | success |
| disabled | default |

---

### 6.7 `RoleTag` / `ProjectTag`

**职责**：渲染角色 / 项目的简洁 Tag。

---

### 6.8 `HttpStatusTag`

**职责**：HTTP 响应码彩色 Tag。

| 范围 | 颜色 |
|---|---|
| 1xx / 2xx | success |
| 3xx | warning |
| 4xx | error |
| 5xx | volcano |

---

## ⑦ Forms · 表单

### 7.1 通用约定

| 维度 | 规范 |
|---|---|
| 布局 | `layout="vertical"` |
| 必填标识 | `requiredMark="optional"`（不在 Label 上标 *） |
| 校验时机 | onSubmit + onBlur，不在 onChange |
| 错误展示 | `Form.Item validateStatus="error" + help="msg"` |
| dirty 检测 | `Form.useForm()[0].isFieldsTouched()` |
| 提交按钮 | 主操作 Primary，禁用直到必填通过 |

---

### 7.2 `ProjectForm`

| Props | 类型 | 说明 |
|---|---|---|
| `initialValues` | `Partial<Project>` | 编辑模式初始值 |
| `submitting` | `boolean` | 提交中 |
| `onSubmit` | `(values: ProjectFormValues) => void` | 提交 |
| `onCancel` | `() => void` | 取消 |

| Fields | 校验 |
|---|---|
| name（必填） | 1~50 字符 |
| description（可选） | ≤ 200 字符 |

---

### 7.3 `EnvironmentForm`

| Fields | 校验 |
|---|---|
| name（必填） | 1~50 字符 |
| base_url（必填） | URL 格式 |
| headers（数组） | 至少 0 项 |
| variables（数组） | JSON 合法 |
| is_default | 默认勾选 |

| Events | 参数 |
|---|---|
| `onSubmit` | `(values: EnvironmentFormValues) => void` |
| `onCancel` | — |
| `onHeadersChange` | `(rows: KeyValue[]) => void` |
| `onVariablesChange` | `(rows: KeyValue[]) => void` |

---

### 7.4 `SuiteForm`

| Fields | 校验 |
|---|---|
| name（必填） | 1~80 字符 |
| description（可选） | ≤ 500 字符 |

---

### 7.5 `CaseForm`

| Sections | Fields |
|---|---|
| **基本信息** | name（必填）/ enabled / timeout_ms |
| **请求配置** | method / path（必填）/ headers / query / body_type / body |
| **断言配置** | assertions 数组（每条：type / operator / expected / actual） |

| Events | 参数 |
|---|---|
| `onSubmit` | `(values: TestCasePayload) => void` |
| `onMethodChange` | `(method: HttpMethod) => void` 切换时联动 Body 字段 |
| `onAssertionAdd` | — |
| `onAssertionRemove` | `(index) => void` |

---

### 7.6 `UserForm`

| Fields | 校验 |
|---|---|
| email（必填） | 邮箱格式 |
| username（必填） | 1~50 |
| nickname（可选） | ≤ 50 |
| password（创建必填 / 编辑可选） | ≥ 8 位 |
| role_id（必填） | 单选 |
| is_active | bool |
| is_superuser | bool（仅 superuser 可改） |

---

### 7.7 `RoleForm`

| Fields | 校验 |
|---|---|
| name（必填） | 1~50 |
| description（可选） | ≤ 200 |
| permissions（必填） | 字符串数组 |

---

### 7.8 `ChangePasswordForm`

| Fields | 校验 |
|---|---|
| old_password（必填） | — |
| new_password（必填） | ≥ 8 位，且 ≠ old_password |
| confirm_password（必填） | === new_password |

---

### 7.9 `OpenApiImportForm`

| Sections | Fields |
|---|---|
| **来源** | source_type: URL / JSON；source_url 或 source_text |
| **过滤** | tags（多选）/ 关键词 |
| **冲突策略** | conflict_strategy: skip / overwrite |
| **命名** | name_prefix（可选） |

| Events | 参数 |
|---|---|
| `onPreview` | `(values) => void` 请求预览 |
| `onConfirm` | `(previewId) => void` 确认导入 |

---

## ⑧ Drawers & Modals · 抽屉与模态框

### 8.1 通用约定

| 维度 | 规范 |
|---|---|
| `destroyOnClose` | 必填（表单 Drawer / Modal） |
| `maskClosable` | 提交期间 `false` |
| `onClose` | 提交期间禁用 |
| 宽度 | 见 `DesignSystem.md` ⑨⑩ |

---

### 8.2 `RunExecutionDrawer`

**职责**：执行 Run 的统一入口 Drawer。承载 Suite / Case / Project 三种 scope。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `open` | `boolean` | ✅ | 显隐 |
| `source` | `RunExecutionSource` | ✅ | 来源（project / suite / case） |
| `projectId` | `string` | ✅ | 当前 Project |
| `environments` | `Environment[]` | ✅ | 环境列表 |
| `defaultEnvironmentId` | `string \| null` | — | 默认环境 |
| `enabledCaseCount` | `number` | — | 范围内启用 Case 数 |

| State | 类型 | 说明 |
|---|---|---|
| `phase` | `'configuring' \| 'submitting'` | 当前阶段 |
| `error` | `string \| null` | 错误文案 |

| Events | 参数 |
|---|---|
| `onSubmit` | `(values: RunExecutionValues) => void` |
| `onClose` | — |
| `onSuccess` | `(runId: string) => void` 成功后跳转 |

**Variants**：

- **Project scope**：默认，启用 Case 数 = 整个 Project
- **Suite scope**：预填 source.suiteId
- **Case scope**：预填 source.caseItem

**Used By**：SuiteDetail、CaseEditor、RunCenter、Workspace Header。

---

### 8.3 `ConfirmDialog`

**职责**：通用确认 Modal。危险操作二次确认。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `open` | `boolean` | ✅ | 显隐 |
| `title` | `string` | ✅ | 标题（"确认删除 XXX？"） |
| `description` | `ReactNode` | — | 详细说明 |
| `danger` | `boolean` | — | 是否危险（红色按钮） |
| `confirmText` | `string` | — | 确认按钮文案，默认"确认" |
| `cancelText` | `string` | — | 取消按钮文案，默认"取消" |
| `requireTextInput` | `string` | — | 需输入的字符串（如 Project 名），用于高危删除 |
| `loading` | `boolean` | — | 提交中 |

| Events | 参数 |
|---|---|
| `onConfirm` | `() => void` |
| `onCancel` | — |

**Variants**：

- **default**：普通确认
- **danger**：红色主按钮（删除）
- **danger + requireInput**：高危删除，需输入对象名

**Used By**：所有删除 / 危险操作。

---

### 8.4 `ProjectFormModal` / `EnvironmentFormModal` / `SuiteFormModal` / `UserFormModal` / `RoleFormModal` / `ChangePasswordModal`

**职责**：各自对应 Form 的 Modal 容器。统一封装 open / onClose / submit。

| 通用 Props | 说明 |
|---|---|
| `open` | 显隐 |
| `mode` | `'create' \| 'edit'` |
| `initialValues` | 编辑模式初始值 |
| `onClose` | — |
| `onSubmit` | — |

**Used By**：对应列表页。

---

### 8.5 `OpenApiPreviewModal`

**职责**：OpenAPI 导入预览 Modal。展示 operation 列表、冲突项、错误。

| Props | 类型 | 说明 |
|---|---|---|
| `open` | `boolean` | 显隐 |
| `preview` | `OpenApiPreview` | 预览数据 |
| `conflictStrategy` | `'skip' \| 'overwrite'` | 冲突策略 |
| `loading` | `boolean` | 预览加载中 |

| Events | 参数 |
|---|---|
| `onConfirm` | `(previewId: string) => void` |
| `onCancel` | — |
| `onStrategyChange` | `(strategy) => void` |

---

## ⑨ States · 状态视图

### 9.1 `EmptyView`

**职责**：空状态视图。图标 + 标题 + 描述 + 下一步动作。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `title` | `string` | ✅ | 标题 |
| `description` | `string` | — | 描述 |
| `action` | `ReactNode` | — | 下一步动作 |
| `icon` | `ReactNode` | — | 自定义图标 |
| `compact` | `boolean` | — | 紧凑模式（小卡片内） |

| State | — |

| Events | — |

**Variants**：

- **page**：大空态（独立区块，padding 48）
- **compact**：小空态（卡片内，padding 24）
- **inline**：行内空态（表格内）

**Used By**：所有列表 / 详情页。

---

### 9.2 `LoadingView`

**职责**：加载态视图。Spin + 占位 / 骨架屏。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `tip` | `string` | — | "加载中…" |
| `rows` | `number` | — | Skeleton 行数 |
| `fullPage` | `boolean` | — | 全屏模式 |
| `delay` | `number` | — | 延迟显示（避免闪烁） |

| Variants | 说明 |
|---|---|
| **spin** | 转圈 + 占位块 |
| **skeleton** | 骨架屏 |
| **skeleton-card** | 卡片内骨架 |

**Used By**：所有列表 / 详情页。

---

### 9.3 `ErrorView`

**职责**：错误态视图。Result 组件封装。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `error` | `unknown` | ✅ | 错误对象 |
| `onRetry` | `() => void` | — | 重试回调 |
| `title` | `string` | — | 自定义标题 |
| `compact` | `boolean` | — | 紧凑模式 |
| `status` | `'403' \| '404' \| 'error'` | — | 错误级别 |

| Events | 参数 |
|---|---|
| `onRetry` | — |
| `onBack` | `() => void` 返回上级 |

**Variants**：

- **full**：Result 大屏
- **compact**：行内

**Used By**：所有列表 / 详情页。

---

### 9.4 `SkeletonView`

**职责**：骨架屏。AntD Skeleton 封装。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `rows` | `number` | — | 行数（默认 4） |
| `title` | `boolean` | — | 是否含标题占位 |
| `avatar` | `boolean` | — | 是否含头像占位 |
| `card` | `boolean` | — | 是否卡片包裹 |

**Used By**：页面级初次加载。

---

## ⑩ Inputs · 输入控件

### 10.1 `SearchBar`

**职责**：搜索框。AntD Input.Search 封装。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `value` | `string` | — | 受控值 |
| `placeholder` | `string` | — | 占位 |
| `loading` | `boolean` | — | 搜索中 |
| `debounceMs` | `number` | — | 防抖（默认 300ms） |
| `size` | `'small' \| 'default' \| 'large'` | — | 尺寸 |

| Events | 参数 |
|---|---|
| `onChange` | `(value: string) => void` 输入 |
| `onSearch` | `(value: string) => void` 触发搜索 |
| `onClear` | `() => void` 清空 |

**Used By**：所有列表页 Toolbar。

---

### 10.2 `FilterBar`

**职责**：筛选条。组合多个 Filter 控件。

| Props | 类型 | 说明 |
|---|---|---|
| `filters` | `FilterConfig[]` | 筛选配置 |
| `value` | `Record<string, unknown>` | 当前值 |
| `loading` | `boolean` | 加载态 |

| Events | 参数 |
|---|---|
| `onChange` | `(next: Record<string, unknown>) => void` |
| `onReset` | `() => void` |

**Used By**：CaseTable（method / enabled）、RunTable（status）。

---

### 10.3 `EnvironmentSelect`

**职责**：环境选择器。封装默认环境标识。

| Props | 类型 | 说明 |
|---|---|---|
| `value` | `string` | 当前环境 ID |
| `environments` | `Environment[]` | 环境列表 |
| `showDefaultBadge` | `boolean` | 显示"默认"标识 |

**Used By**：RunExecutionDrawer。

---

### 10.4 `SuiteSelect` / `CaseSelect`

**职责**：Suite / Case 选择器。支持搜索。

| Props | 类型 | 说明 |
|---|---|---|
| `projectId` | `string` | 当前 Project |
| `value` | `string` | 当前 ID |
| `multiple` | `boolean` | 是否多选 |
| `excludeIds` | `string[]` | 排除的 ID |

---

### 10.5 `KeyValueEditor`

**职责**：键值对编辑器。用于 Headers / Variables / Query。

| Props | 类型 | 说明 |
|---|---|---|
| `value` | `KeyValue[]` | 数据 |
| `keyPlaceholder` | `string` | Key 占位 |
| `valuePlaceholder` | `string` | Value 占位 |
| `valueType` | `'text' \| 'json' \| 'secret'` | Value 类型（敏感值遮罩） |

| Events | 参数 |
|---|---|
| `onChange` | `(next: KeyValue[]) => void` |

**Used By**：EnvironmentForm（headers / variables）、CaseForm（headers / query）。

---

## ⑪ Action Bars · 操作栏

### 11.1 `ActionBar`

**职责**：页面级操作条。承载主要操作按钮组合。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `primary` | `ActionConfig` | — | 主操作（仅 1 个） |
| `secondary` | `ActionConfig[]` | — | 次操作 |
| `danger` | `ActionConfig[]` | — | 危险操作 |
| `extra` | `ReactNode` | — | 右侧附加 |

| ActionConfig | 类型 |
|---|---|
| `key` | `string` |
| `label` | `string` |
| `icon` | `ReactNode` |
| `disabled` | `boolean` |
| `loading` | `boolean` |
| `onClick` | `() => void` |

| Events | — |

**Variants**：

- **PageHeader ActionBar**：PageHeader extra 槽位
- **Drawer Footer ActionBar**：Drawer extra 槽位
- **Modal Footer ActionBar**：Modal footer 槽位
- **Toolbar ActionBar**：列表页上方

**Used By**：所有页面。

---

### 11.2 `Toolbar`

**职责**：列表页上方工具条。SearchBar + FilterBar + ActionBar 组合。

| Props | 类型 | 说明 |
|---|---|---|
| `search` | `SearchBarConfig` | 搜索 |
| `filters` | `FilterConfig[]` | 筛选 |
| `actions` | `ActionConfig[]` | 操作 |

**Used By**：所有列表页。

---

### 11.3 `ContextActions`

**职责**：上下文相关快捷操作集合。出现于 Workspace Context Panel / Detail Header。

| Props | 类型 | 说明 |
|---|---|---|
| `actions` | `ActionConfig[]` | 快捷操作 |

**Used By**：Workspace ContextPanel、Detail Header。

---

## ⑫ Reports · 报告组件

### 12.1 `ReportSummary`

**职责**：Run 报告摘要卡。展示 Run 关键 KPI。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `run` | `TestRun` | ✅ | Run 数据 |
| `summary` | `RunSummary` | ✅ | 累计统计 |
| `environment` | `Environment` | — | 环境 |
| `triggeredBy` | `User` | — | 触发人 |

| Sections | 内容 |
|---|---|
| 头部 | 名称 / 状态 / 通过率 |
| KPI | total / passed / failed / skipped / error |
| 元信息 | 范围 / 环境 / 触发人 / 开始 / 耗时 |

| Events | 参数 |
|---|---|
| `onRerun` | `() => void` |
| `onOpenReport` | `() => void` |

**Used By**：RunDetailHeader、Dashboard Recent Runs。

---

### 12.2 `ReportMetric`

**职责**：报告单指标卡。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `label` | `string` | ✅ | 指标名 |
| `value` | `string \| number` | ✅ | 指标值 |
| `hint` | `string` | — | 辅助说明 |
| `tone` | `'neutral' \| 'success' \| 'warning' \| 'danger'` | — | 配色 |

**Used By**：ReportSummary、Dashboard。

---

### 12.3 `FailureItem`

**职责**：单个失败项展开卡。展示断言对比。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `failure` | `TestResult` | ✅ | 失败 Result |
| `expanded` | `boolean` | — | 默认展开 |

| 内容 |
|---|
| 状态 / Method / Path |
| 错误码 / 错误信息 |
| 期望值 / 实际值对比 |
| 请求快照 |
| 响应快照 |

| Events | 参数 |
|---|---|
| `onOpenResult` | `(resultId) => void` |

**Used By**：RunDetail Failures Tab。

---

### 12.4 `AssertionDiff`

**职责**：断言对比视图。Allure 风格 expected / actual 对比。

| Props | 类型 | 说明 |
|---|---|---|
| `expected` | `unknown` | 期望值 |
| `actual` | `unknown` | 实际值 |
| `operator` | `'==' \| '!=' \| '>' \| '<' \| 'contains' \| 'regex'` | 操作符 |

**Used By**：FailureItem、ResultDetail Assertions Tab。

---

### 12.5 `RequestSnapshot` / `ResponseSnapshot`

**职责**：请求 / 响应快照。等宽字体 + 折叠展示。

| Props | 类型 | 说明 |
|---|---|---|
| `method` / `status` | `HttpMethod` / `number` | 请求 / 响应基本信息 |
| `url` / `headers` | `string` / `Record<string, string>` | URL / Headers |
| `body` | `unknown` | Body |
| `truncated` | `boolean` | Body 是否被截断 |

**Used By**：ResultDetail。

---

### 12.6 `JsonPreview`

**职责**：JSON 预览。等宽字体 + 语法高亮 + 复制按钮。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `data` | `unknown` | ✅ | JSON 数据 |
| `maxHeight` | `number` | — | 最大高度（默认 480） |
| `copyable` | `boolean` | — | 显示复制按钮 |

| Events | 参数 |
|---|---|
| `onCopy` | `() => void` |

**Used By**：ResultDetail、EnvironmentForm（variables）、OpenApiPreview。

---

## ⑬ Dashboard · 工作台专用

### 13.1 `DashboardMetricCard`

**职责**：Dashboard 指标卡。展示单个 KPI 数字。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `title` | `string` | ✅ | 指标名 |
| `value` | `string` | ✅ | 指标值 |
| `hint` | `string` | — | 辅助说明 |
| `percent` | `number \| null` | — | 进度条（0~1） |
| `loading` | `boolean` | — | 加载态 |
| `error` | `unknown` | — | 错误态 |
| `onRetry` | `() => void` | — | 重试 |
| `onClick` | `() => void` | — | 点击进详情 |
| `emptyTitle` | `string` | — | 空态标题 |

**Used By**：Dashboard KPI 区。

---

### 13.2 `RecentProjectsPanel`

**职责**：Recent Projects 卡片区。展示最近 5 个 Project。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `projects` | `Project[]` | ✅ | Recent Projects |
| `loading` | `boolean` | — | 加载态 |
| `maxItems` | `number` | — | 最大展示数（默认 5） |

| Events | 参数 |
|---|---|
| `onOpen` | `(projectId) => void` |
| `onCreateNew` | `() => void` |

**Used By**：Dashboard。

---

### 13.3 `RecentSuitesPanel` / `RecentRunsPanel` / `RecentReportsPanel`

**职责**：Recent Suites / Runs / Reports 列表。结构相似。

| Props | 类型 | 说明 |
|---|---|---|
| `items` | `RecentItem[]` | 数据 |
| `loading` | `boolean` | 加载态 |
| `limit` | `number` | 最多 5 条 |

| Events | 参数 |
|---|---|
| `onOpen` | `(id) => void` |
| `onViewAll` | `() => void` 查看全部 |

**Used By**：Dashboard、Workspace Overview。

---

### 13.4 `WelcomeBanner`

**职责**：Dashboard 顶部欢迎语。

| Props | 类型 | 说明 |
|---|---|---|
| `user` | `User` | 当前用户 |
| `greeting` | `string` | 问候语（"早上好" / "下午好"） |

**Used By**：Dashboard。

---

### 13.5 `WorkspaceReadinessIndicator`

**职责**：配置就绪度指示器。在 Workspace Header 中显示 4~5 项 Tag。

| Props | 类型 | 说明 |
|---|---|---|
| `readiness` | `Readiness` | 就绪度数据 |
| `defaultEnvironmentName` | `string \| null` | 默认环境名 |

**Used By**：ProjectWorkspaceHeader。

---

## ⑭ Workspace · 工作区专用

### 14.1 `ProjectWorkspaceSider`

**职责**：L2 内 Sider。工作区模块导航。

| Props | 类型 | 说明 |
|---|---|---|
| `projectId` | `string` | 当前 Project |
| `readiness` | `Readiness` | 就绪度（用于显示未就绪 · 标记） |

| State | — |

| Events | 参数 |
|---|---|
| `onSelect` | `(moduleKey: string) => void` |

**Used By**：ProjectWorkspaceLayout。

---

### 14.2 `ProjectWorkspaceContextPanel`

**职责**：L2 右栏 Context Panel。展示默认环境 / 最近 Run / 就绪度 / 快速操作。

| Props | 类型 | 说明 |
|---|---|---|
| `defaultEnvironmentId` | `string \| null` | 默认环境 |
| `defaultEnvironmentName` | `string \| null` | 默认环境名 |
| `defaultEnvironmentBaseUrl` | `string \| null` | Base URL |
| `latestRun` | `TestRun \| null` | 最近 Run |
| `readiness` | `Readiness` | 就绪度 |

| Events | 参数 |
|---|---|
| `onCopyBaseUrl` | `(url) => void` |
| `onOpenLatestRun` | `(runId) => void` |
| `onQuickCreate` | `(kind: 'env' \| 'suite' \| 'case') => void` |

**Used By**：ProjectWorkspaceLayout。

---

### 14.3 `WorkspaceQuickActions`

**职责**：Workspace Header 右侧快捷操作集合（最近执行 / 快速执行 / 刷新）。

| Props | 类型 | 说明 |
|---|---|---|
| `latestRun` | `TestRun \| null` | 最近 Run |
| `defaultEnvironmentId` | `string \| null` | 默认环境 |

| Events | 参数 |
|---|---|
| `onQuickRun` | — |
| `onOpenLatestRun` | — |
| `onRefresh` | — |

---

## ⑮ Misc · 杂项

### 15.1 `ErrorBoundary`

**职责**：React 错误边界。捕获子树未捕获异常，展示错误页。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `children` | `ReactNode` | ✅ | 子树 |

| State | 类型 | 说明 |
|---|---|---|
| `hasError` | `boolean` | 是否发生错误 |

| Events | — |

**Used By**：App 根、关键页面包裹。

---

### 15.2 `RouteGuard`

**职责**：路由守卫。校验登录态、权限、Project 归属。

| Props | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `requireAuth` | `boolean` | — | 是否需登录（默认 true） |
| `requireSuperuser` | `boolean` | — | 是否需 superuser |
| `requireProjectAccess` | `boolean` | — | 是否需 Project 归属校验 |
| `fallback` | `ReactNode` | — | 不通过时渲染 |

| Events | — |

**Used By**：路由表。

---

### 15.3 `StatusTags`（聚合组件）

**职责**：聚合 `RunStatus` / `ResultStatus` / `MethodTag` / `ScopeTag`，按需使用。

| Props | 类型 | 说明 |
|---|---|---|
| `type` | `'run' \| 'result' \| 'method' \| 'scope'` | 类型 |
| `value` | `string` | 值 |

---

## ⑯ 组件复用矩阵

| 组件 | 列表页 | 详情页 | Drawer / Modal | Workspace | Dashboard |
|---|:---:|:---:|:---:|:---:|:---:|
| `PageHeader` | ✅ | ✅ | — | ✅ | ✅ |
| `ActionBar` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `Toolbar` | ✅ | — | — | — | — |
| `SearchBar` | ✅ | — | — | — | ✅ |
| `EmptyView` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `LoadingView` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ErrorView` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ConfirmDialog` | — | — | ✅ | — | — |
| `KeyValueEditor` | — | — | ✅ | — | — |
| `JsonPreview` | — | ✅ | ✅ | — | — |
| `ReportSummary` | — | ✅ | — | ✅ | ✅ |
| `RunStatus` / `ResultStatus` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `MethodTag` | ✅ | ✅ | ✅ | — | — |
| `EnvironmentSelect` | — | — | ✅ | — | — |
| `ReadinessIndicator` | — | — | — | ✅ | — |

---

## ⑰ 组件创建守则

### 17.1 必须遵守

| # | 规则 |
|---:|---|
| 1 | 新组件**必须**先在本文件登记契约，再写实现 |
| 2 | Props 命名严格遵守 §2.1 命名规范 |
| 3 | 组件**不直接调用** API（数据由父组件传入） |
| 4 | 受控 / 非受控二选一，**不在同一组件混用** |
| 5 | 业务特定逻辑**不下沉**到通用组件（保持通用性） |
| 6 | 组件必须**支持** `className` / `style` / `loading` / `disabled` 基础 Props |
| 7 | 提供至少 1 个 **TypeScript 类型导出** |
| 8 | 内部状态**不暴露**到 Props（除非要外部受控） |

### 17.2 禁止

| # | 禁止 |
|---:|---|
| 1 | 禁止在组件内直接 `fetch` / `axios`（违反关注分离） |
| 2 | 禁止硬编码颜色 / 间距 / 字号（必须使用 DesignSystem Token） |
| 3 | 禁止组件耦合特定业务路由 / 业务字段 |
| 4 | 禁止在通用组件内引入业务图标（业务图标由调用方传入） |
| 5 | 禁止在 `forwardRef` 之外的组件上附加 ref |
| 6 | 禁止引入与组件职责无关的依赖 |

---

## ⑱ 组件版本演进

| 组件 | v1.0 状态 | 后续演进 |
|---|---|---|
| 所有 §3-§15 组件 | 初版登记 | 后续按业务需求扩充 Variants / Events |

---

## 附录 A · 组件命名一致性检查表

为避免同一概念有多个命名，建立以下检查表：

| 概念 | 统一命名 | 反例 |
|---|---|---|
| Project 卡片 | `ProjectCard` | ❌ `ProjectItem` |
| Suite 卡片 | `SuiteCard` | ❌ `CollectionCard` |
| Run 状态 | `RunStatus` | ❌ `RunStatusTag`（Tag 是实现细节） |
| Result 状态 | `ResultStatus` | ❌ `TestResultTag` |
| HTTP Method | `MethodTag` | ❌ `HttpMethodTag` |
| Scope | `ScopeTag` | ❌ `RunScopeTag` |
| 空状态 | `EmptyView` | ❌ `EmptyState` / `NoData` |
| 加载态 | `LoadingView` | ❌ `Loading` / `Spinner` |
| 错误态 | `ErrorView` | ❌ `ErrorState` / `ErrorPage` |
| 搜索框 | `SearchBar` | ❌ `SearchInput` / `SearchBox` |
| 操作栏 | `ActionBar` | ❌ `ButtonGroup` / `Actions` |
| 工具栏 | `Toolbar` | ❌ `FilterBar`（混合了多个职责） |
| 确认弹窗 | `ConfirmDialog` | ❌ `ConfirmModal` / `Popconfirm`（Popconfirm 是 AntD 内置组件） |
| 抽屉 | `Drawer` | ❌ `SidePanel` |
| 表单 | `XxxForm` | ❌ `XxxEditor`（Editor 指代码编辑器） |

---

## 附录 B · Props 设计模式

### B.1 受控 / 非受控双模式

```text
受控：父组件管理状态，通过 value / onChange 传入
非受控：组件内部维护状态，父组件通过 defaultValue 传入初值
```

| 模式 | 适用 |
|---|---|
| 受控 | 表单 / 列表筛选 / 任何需要外部持久化的状态 |
| 非受控 | 纯展示组件 / 一次性 UI 状态（如 Modal 内部 Tab） |

### B.2 复合组件模式

| 形态 | 示例 |
|---|---|
| **复合 Props** | `ActionBar` 接收 `ActionConfig[]` |
| **children 复合** | `Card` 接收 `title` / `extra` / children |
| **Slot 复合** | `Modal` 接收 `footer` prop |

### B.3 Render Props

适用于"行为注入型"组件，如：

- `Table` 的 `columns[].render`
- `FailureItem` 的 description 渲染

### B.4 Polymorphic 组件

仅在 `Button` / `Typography.Link` 等极少数场景使用，不鼓励新增。

---

## 附录 C · 测试契约

每个组件在交付时必须附带：

| 测试维度 | 说明 |
|---|---|
| **Snapshot** | 基础渲染快照 |
| **Props 必填** | 缺必填 Props 是否报错 |
| **Props 默认值** | 可选 Props 默认行为 |
| **Events 触发** | 用户操作后回调是否正确触发 + 参数正确 |
| **Variants** | 各 Variants 渲染差异 |
| **Loading / Empty / Error** | 三态视觉正确 |
| **Disabled** | 禁用态不可交互 |
| **a11y** | 键盘可达 / ARIA 标签 |

---

## 附录 D · 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-15 | 初版：登记 76 个组件，覆盖 Layout / Domain / Status / Form / Drawer / State / Input / Action / Report / Dashboard / Workspace / Misc 12 个分类 |

---

**约束再确认**

- ❌ 不修改任何业务逻辑
- ❌ 不新增任何 API
- ❌ 不修改数据库
- ✅ 仅规范组件契约（职责 / Props / State / Events），作为前端组件库的单一真相源