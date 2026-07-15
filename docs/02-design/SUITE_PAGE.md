# Suite 管理页面设计

> 文档类型：Workspace → Suite / Case 模块的完整页面设计  
> 范围：Suite 列表、Suite 详情（Case 列表、增删、排序）  
> 实施约束：仅复用已有 API、不修改后端、不新增数据库、本阶段不写代码

---

## 1. 设计目标

在 Workspace → Suite / Case 模块下完整支持：

- Suite 列表：创建 Suite、编辑 Suite、删除 Suite、按名称搜索。
- Suite 详情：浏览已关联 Case、添加已存在 Case、移除 Case 关联、调整 Case 顺序、运行 Suite、OpenAPI 导入。
- Case 排序：基于现有 `order` 字段的拖拽 / 上移下移。

所有交互必须符合现有后端契约，不引入新端点。

| 操作 | 后端 API |
|---|---|
| Suite 列表 | `GET /projects/{projectId}/suites?search=` |
| 创建 Suite | `POST /projects/{projectId}/suites` |
| 编辑 Suite | `GET /suites/{suiteId}` + `PUT /projects/{projectId}/suites/{suiteId}` |
| 删除 Suite | `DELETE /projects/{projectId}/suites/{suiteId}` |
| Suite 关联 Case | `GET /collections/{suiteId}/cases` |
| 批量追加 Case | `POST /projects/{projectId}/suites/{suiteId}/cases` body `{test_case_ids:[]}` |
| 调整 Case 顺序 | `PUT /projects/{projectId}/suites/{suiteId}/cases/order` body `{test_case_ids:[]}` |
| 移除 Case 关联 | `DELETE /projects/{projectId}/suites/{suiteId}/cases/{caseId}` |
| 可追加的 Case 池 | `GET /projects/{projectId}/test-cases?search=` |
| 套件运行 | 复用 Run 模块，URL `?scope=collection&scopeId=...` |
| OpenAPI 导入 | `/projects/{projectId}/workspace/import/{suiteId}` |

---

## 2. 页面结构

### 2.1 顶层结构

Suite 页面分为两个层级：

- `Workspace Suite List Page`：路径 `/projects/:projectId/workspace/suite`。
- `Workspace Suite Detail Page`：路径 `/projects/:projectId/workspace/suite/:suiteId`。

两个页面共享同一组 React Query 缓存 key，但通过 `enabled` 区分数据加载。

### 2.2 Suite List 页面骨架

```text
PageHeader
  · 标题：Suite
  · 面包屑：项目 / Suite
  · 主操作：[+ 新建 Suite]

Toolbar
  · 搜索（按 suite 名称）
  · 计数：共 N 个 Suite

DataTable
  · 名称
  · 描述
  · 排序
  · 更新时间
  · 已关联 Case 数量
  · 操作：进入 / 编辑 / 删除
```

### 2.3 Suite Detail 页面骨架

```text
PageHeader
  · 标题：Suite 名称
  · 面包屑：项目 / Suite / Suite 名称
  · 描述：Suite 描述
  · 主操作：运行 Suite、OpenAPI 导入
  · 次操作：编辑 Suite、删除 Suite

SuiteStats 摘要
  · Case 数量
  · 已启用 / 全部
  · 末次运行（来自 Project Run Summary，跳过）

Tabs
  · 已关联 Case（默认 Tab）
  · Suite 信息

关联 Case 列表
  · 序号（拖拽 / 上移下移）
  · Method
  · Case 名称
  · Path
  · 启用状态（不可改）
  · 操作：移除 / 跳到 Case 编辑
  · 顶部：搜索（按 Case 名称 / Path）+ [批量添加]

Empty 状态
  · 当前 Suite 尚无 Case → 引导创建或导入
```

---

## 3. 组件树

```text
WorkspaceSuiteListPage
├── PageHeader
├── SuiteToolbar
│   ├── SuiteSearchInput
│   └── SuiteCountSummary
├── SuiteTable
│   ├── SuiteRowActions
│   └── SuiteFormDrawer（共用）
└── SuiteAddCasesModal（共用）

WorkspaceSuiteDetailPage
├── PageHeader
├── SuiteStats
├── SuiteDetailTabs
│   ├── SuiteCaseList
│   │   ├── SuiteCaseRowActions
│   │   ├── SuiteCaseOrderControl
│   │   ├── SuiteCaseEmpty
│   │   └── SuiteCaseMoveButtons
│   └── SuiteInfoTab
│       └── SuiteMetaTable
├── SuiteFormDrawer
├── SuiteAddCasesModal
├── SuiteDeleteConfirmModal
├── SuiteCaseRemoveConfirmModal
└── RunSuiteButton
```

---

## 4. Suite 列表 Table 设计

| 列 | 数据 | 行为 |
|---|---|---|
| 名称 | `suite.name` | 点击进入 Suite 详情 |
| 描述 | `suite.description` | 截断 + 悬停完整 |
| 排序 | `suite.sort_order` | 用于 Suite 排序（当前无后端 sort 参数，UI 只展示） |
| 更新时间 | `suite.updated_at` | 标准时间格式 |
| 已关联 Case 数量 | `suite.cases?.length` 或独立请求 | 入口 “查看 Case” 按钮 |
| 操作 | Suite 行的操作 | 进入 / 编辑 / 删除 |

- 初次加载：全表 Skeleton。
- 错误：行级 ErrorState + 整页重试。
- 空：EmptyState 引导 “新建 Suite”。
- 搜索：服务端 `?search=`，防抖触发。
- 排序：默认 `sort_order asc, created_at asc`，与后端默认行为一致；前段不引入新排序请求。

---

## 5. Suite 创建 / 编辑 Drawer

Drawer 宽 720，单 Tab 表单：

| 字段 | 必填 | 校验 |
|---|---|---|
| 名称 | 是 | 1-100 字符 |
| 描述 | 否 | 0-500 字符 |
| 排序 | 否 | 0-9999（默认 0，仅展示用） |

操作：

- 新建：保存成功后刷新列表，关闭 Drawer。
- 编辑：保存成功后保留在 Drawer 状态，但刷新列表。

> 现有 `EnvironmentFormModal` 已实现创建 / 编辑；可以保持“Modal 形态”以减小代码量，或者按 Suite 升级为 Drawer。两种形态均可接受，本设计使用 Drawer 以便与 Case 操作共享宽度。

---

## 6. Suite 删除流程

- 列表行内 [删除] 弹出 `Popconfirm` 二次确认。
- 描述文案包括 Suite 名称与风险（“Suite 删除后，关联的 Case 不会被删除”）。
- 确认后调用 `DELETE /projects/{projectId}/suites/{suiteId}`。
- 失败时保留 Popconfirm（不自动关闭），由 Toast 提示。
- Suite Detail 顶部的 [删除 Suite] 与列表中行为一致。

---

## 7. Suite 详情：Case 关联列表

### 7.1 数据来源

`GET /collections/{suiteId}/cases` 返回的 Case 列表是当前 Suite 关联的 Case。

字段映射：

- `id`（SuiteCaseLink.id）→ 行 key
- `test_case_id` → Case ID
- `order` → 当前顺序
- Case 详情（name、path、method、enabled）：由 `GET /projects/{projectId}/test-cases` 一次性加载，Map 缓存。

### 7.2 列表

| 列 | 数据 | 行为 |
|---|---|---|
| 序号 | 当前 `order` | 上下移 / 拖拽手柄（待后续实现） |
| Method | `case.method` | Ant Design `MethodTag` |
| Case 名称 | `case.name` | 点击进入 Case 编辑器 |
| Path | `case.path` | 灰色等宽字体 |
| 启用 | `case.enabled` | 不可切换的 Switch |
| 操作 | 行内 | 上移 / 下移 / 跳到 Case / 移除 |

### 7.3 排序

排序策略：前段不引入新后端请求；采用现有 `PUT /projects/{projectId}/suites/{suiteId}/cases/order` 接口。

- 行内上下移按钮：
  - 上移：交换本行与上一行的位置。
  - 下移：交换本行与下一行的位置。
  - 计算新的 `test_case_ids` 顺序并调用 `reorderCases`。
- 全局拖拽（待扩展）：可后续通过 dnd-kit 启用。
- 排序请求失败：保留原顺序，Toast 提示。

### 7.4 添加已存在 Case

点击 [批量添加] 打开 Modal：

- 内容：Modal `title` 包含 Suite 名称。
- 表单：可搜索的 `Select multiple` 数据源为 `GET /projects/{projectId}/test-cases`：
  - 默认仅显示“未在本 Suite 的 Case”（前端过滤已关联的 case_id）。
  - 支持按名称 / Path 搜索（antd `filterOption`）。
  - 限制：服务端约束 ≤ 200 / 次。
- 提交：调用 `POST /projects/{projectId}/suites/{suiteId}/cases` body `{test_case_ids:[]}`。
- 成功：刷新 Suite 关联 Case 列表 + Project 级 `case-cases` 与 `suite-cases` 失效。
- 错误：保留选择，提示错误。

### 7.5 移除 Case 关联

行内 [移除] 调用 `Popconfirm` 二次确认：

- 描述：“从 Suite 移除，不会删除 Case 本身。”
- 确认后调用 `DELETE /projects/{projectId}/suites/{suiteId}/cases/{caseId}`。
- 成功：刷新 Suite 关联 Case 列表。
- 失败：保留 Popconfirm。

### 7.6 Empty 状态

Suite 详情 Empty 状态包含 3 个动作：

- 新建 Case：跳转 `case/new?suiteId=...`。
- 添加已有 Case：直接打开 “批量添加” Modal。
- OpenAPI 导入：跳转 `import/{suiteId}`。

### 7.7 加载与错误

- 初次加载：Suite 详情先 Skeleton；Case 列表显示行级 Skeleton。
- Suite 不存在：跳到 404。
- Case 关联查询失败：行级 ErrorState + 整页重试。
- 排序 / 添加 / 移除失败：保留原状态，Toast 错误。

---

## 8. Suite 信息 Tab

只读元信息表：

- Suite ID、Project ID、创建时间、更新时间、当前 Case 数量。
- 操作：编辑、删除。
- 用于 Suite 详情顶部信息条简单摘要。

---

## 9. 路由与上下文

- Suite 列表：`/projects/:projectId/workspace/suite`。
- Suite 详情：`/projects/:projectId/workspace/suite/:suiteId`。
- 共享 React Query key：
  - `["projects", projectId, "suites", search]`。
  - `["projects", projectId, "cases", search]`。
  - `["suites", suiteId, "cases"]`。
- 与 ProjectWorkspaceContext 交互：
  - 切默认环境后调用 `useProjectWorkspace().refresh()` 让顶部信息条 / ContextPanel 同步。
  - 任何 Suite / Case 变更都通过失效对应 query 触发全局刷新。

---

## 10. 状态管理

| 类别 | 工具 | 范围 |
|---|---|---|
| 服务端状态 | React Query | Suite 列表 / Suite 详情 / Case 关联 / Cases 池 / Project Cases |
| 表单状态 | Ant Design Form | Suite Drawer |
| 弹窗 | Ant Design Modal | 添加 Case、删除 Suite、移除 Case 关联 |
| 本地状态 | useState | Drawer / Modal 开关、排序锁定 |
| 全局 Workspace | useProjectWorkspace | refresh、默认环境 |
| 排序操作 | 行内乐观更新 | 仅当前 Suite 关联列表 |

---

## 11. Loading / Empty / Error 全状态

| 状态 | 触发 | 展示 |
|---|---|---|
| Loading | Suite 列表首次加载 | 全表 Skeleton |
| Empty Suite | 列表为空 | EmptyState 引导新建 Suite |
| Empty Case | Suite 详情无 Case | EmptyState 引导新建 / 导入 |
| Error Suite | 列表查询失败 | 行级 ErrorState + 重试 |
| Error Detail | 详情查询失败 | 整页 ErrorState + 返回列表 |
| Add Loading | 批量添加提交 | 确认按钮 loading |
| Remove Loading | 移除 Case 关联 | 行内 loading |
| Reorder Loading | 排序请求 | 整页 loading；排序按钮 disabled |
| Delete Loading | 删除 Suite | 确认按钮 loading |

---

## 12. 跳转到其他模块

- Suite 列表 → Suite 详情。
- Suite 详情 → Case 编辑（带 `?suiteId=` 上下文）。
- Suite 详情 → 导入（OpenAPI Import）。
- Suite 详情 → Run（`?scope=collection&scopeId=...`）。
- Suite 详情 → Workspace Information Tab（通过 Information 内的“项目信息”入口）。

---

## 13. 验收标准

- [ ] 列表 / 创建 / 编辑 / 删除 / 搜索 Suite 全部成功。
- [ ] Suite 详情展示已关联 Case，支持搜索 / 上移 / 下移 / 移除。
- [ ] 添加 Case Modal 仅显示未在本 Suite 的 Case。
- [ ] 排序请求成功后页面顺序与后端一致；失败保持原状。
- [ ] 移除 Case 仅解除关联，不删除 Case 本体。
- [ ] Suite 删除后，Project Cases 仍保留。
- [ ] Empty / Error / Loading 全部独立且一致。
- [ ] 与 Workspace Layout 共享状态：默认环境、Refresh、ProjectHeader 全部能立即响应。
- [ ] `npm run check` 通过；无 `any`、无重复块、无尾随空格。
- [ ] 边界检查：未修改后端、数据库或迁移。
