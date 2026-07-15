# Environment 页面组件设计

> 文档类型：组件设计与交互规格  
> 范围：Workspace → Environment 模块的页面、表单、Drawer、Dialog、状态  
> 实施约束：仅复用已有 API、不修改后端、不新增数据库、本阶段不写代码

---

## 1. 设计目标

在 Workspace → Environment 模块下完整支持环境的 CRUD、默认环境切换、Variables / Headers / Base URL 编辑。所有交互必须符合现有后端契约，不引入新的端点。

| 操作 | 后端 API | 触发位置 |
|---|---|---|
| 列表 | `GET /projects/{projectId}/environments?search=` | 页面初始化 |
| 新建 | `POST /projects/{projectId}/environments` | 新建 Drawer 提交 |
| 编辑 | `GET /environments/{environmentId}` + `PUT /environments/{environmentId}` | 编辑 Drawer |
| 删除 | `DELETE /environments/{environmentId}` | 列表行内删除 |
| 设默认 | `POST /environments/{environmentId}/set-default` | 列表行内切换 |

---

## 2. 页面骨架

```text
PageHeader：环境
  · 面包屑：项目 / 模块
  · 描述：环境是 Run 的执行上下文
  · 主操作：[+ 新建环境]

Toolbar
  · 搜索（按 name）
  · 计数：共 N 个环境，其中 M 个默认

DataTable（列表）
  · 名称（含默认徽标）
  · Base URL
  · Headers 数量
  · Variables 数量
  · 更新时间
  · 操作：设为默认 / 编辑 / 删除

EnvironmentDetailDrawer（侧拉）
  · 标题：环境名
  · Tabs：
    - 基本（名称、Base URL、是否默认）
    - Headers（JSON 编辑）
    - Variables（JSON 编辑）
  · 操作：保存 / 取消

DeleteConfirmModal（删除确认）
  · 高危 Modal，含项目名二次确认

State Components
  · LoadingBlock / ErrorState / EmptyState 复用
```

---

## 3. 组件树

```text
WorkspaceEnvironmentPage
├── PageHeader
├── EnvironmentToolbar
│   ├── EnvironmentSearchInput
│   └── EnvironmentCountSummary
├── EnvironmentTable
│   ├── EnvironmentRowActions
│   └── EnvironmentDefaultTag
├── EnvironmentDrawer
│   ├── EnvironmentBasicForm
│   ├── EnvironmentHeadersEditor
│   ├── EnvironmentVariablesEditor
│   └── EnvironmentDrawerFooter
├── EnvironmentDeleteModal
└── Workspace shared state
    ├── WorkspaceContext（默认环境/ready 状态）
    └── WorkspaceLayout
```

---

## 4. 列表 Table 设计

### 4.1 列

| 列 | 数据 | 行为 |
|---|---|---|
| 名称 | `env.name` | 默认环境显示“默认”徽标 |
| Base URL | `env.base_url` | 悬停展示完整 URL |
| Headers | 计数 | 点击进入 Drawer Headers Tab |
| Variables | 计数 | 点击进入 Drawer Variables Tab |
| 更新时间 | `env.updated_at` | 标准时间格式 |
| 操作 | 行内操作 | 设为默认 / 编辑 / 删除 |

### 4.2 加载与错误

- 初次加载：全表 Skeleton。
- 错误：行内 ErrorState + 整页重试。
- 空：EmptyState 引导“新建第一个环境”。

### 4.3 搜索

- 服务端搜索：`?search=`，由 `EnvironmentListQuery.search` 处理。
- 名称模糊匹配（大小写不敏感）。
- 搜索时清空 URL 之外的本地筛选状态。

### 4.4 排序

- 默认按 `updated_at DESC`。
- 未来可扩展为列排序，但当前无服务端 sort 参数。

---

## 5. Drawer 表单设计

Drawer 使用 Ant Design `Drawer` 组件，从右侧拉出，宽度 720。

### 5.1 Tabs

| Tab | 字段 | 必填 | 校验 |
|---|---|---|---|
| 基本 | name、base_url、is_default | name / base_url | 名称 1-50；base_url http(s) |
| Headers | JSON 对象 | 否 | 合法 JSON，键值均为字符串 |
| Variables | JSON 对象 | 否 | 合法 JSON，键值均为字符串 |

### 5.2 字段组件

- 名称：Input + maxLength=50。
- Base URL：Input + 前缀提示 `https://`，失焦校验。
- 默认：Switch + Tooltip 解释。
- Headers：JsonEditor（CodeMirror 风格等宽字体 + 行号）。
- Variables：JsonEditor（与 Headers 同组件，标签不同）。
- 保存：禁用直到所有必填通过；保存期间显示 loading。

### 5.3 校验与提示

- JSON 编辑器右上角提供“格式校验”按钮。
- 格式错误时显示错误高亮，保存按钮自动禁用。
- 切换到 Variables Tab 时，如果 Basic 有未保存改动，提示先保存。

### 5.4 保存流程

```text
提交表单
  │
  ├── POST /environments  (新增)
  │   └── 成功后：关闭 Drawer + 刷新列表
  │
  └── PUT /environments/{id}  (编辑)
      └── 成功后：保留在 Drawer 但标记为已保存；再按 × 关闭
```

设置 / 取消默认环境：

- 用户在表单中切换 is_default，提交时一并保存。
- 提交中按钮 disabled=true。

---

## 6. 设为默认流程

```text
列表行内 [设为默认]
  │
  ├── 调 POST /environments/{id}/set-default
  ├── 乐观更新表格默认徽标
  ├── 失败：回滚 + Toast
  └── 失效 query：让列表与上下文自动刷新
```

设默认时不需要打开 Drawer。

---

## 7. 删除流程

```text
列表行内 [删除]
  │
  ├── 弹 DeleteConfirmModal
  │     · 默认环境：禁删，按钮 disabled + 提示
  │     · 普通环境：要求输入项目名确认
  │
  └── 调 DELETE /environments/{id}
        └── 失败：保留 Modal + 重试
```

注意：现有 API 对默认环境的删除返回 409 冲突；前端需要基于响应码或后端报错提示更友好的文案。

---

## 8. 状态管理

| 类别 | 工具 | 范围 |
|---|---|---|
| 服务端状态 | React Query | 列表 / 详情 / 删除 / 设默认 |
| 表单状态 | React Hook Form | Drawer 内部 |
| 全局 Workspace 状态 | ProjectWorkspaceContext | 默认环境 ID、刷新回调 |
| 本地状态 | useState | Drawer 开关、Tab、JSON 校验 |
| 弹窗 | Ant Design Modal | 删除确认 |

使用 `useProjectWorkspace().refresh()` 失效 Workspace 共享缓存，让 ContextPanel 立即看到新的默认环境。

---

## 9. Loading / Empty / Error 全状态规格

| 状态 | 触发 | 展示 |
|---|---|---|
| Loading | 首次加载 | 全表 Skeleton |
| Error | 列表请求失败 | 行级 ErrorState，含重试 |
| Empty | 列表为空 | EmptyState 引导“新建环境” |
| Searching Empty | 搜索无结果 | EmptyState 提示“清空搜索” |
| Save Loading | 提交 Drawer | 主按钮 loading |
| Save Error | 后端拒绝 | Drawer 内 Alert + 主按钮恢复 |
| Set Default Loading | 行内操作 | 按钮 loading |
| Delete Loading | 删除确认 | 确认按钮 loading |

---

## 10. 路由与上下文

- 页面 URL：`/projects/:projectId/workspace/environment`。
- 列表数据 key：`["projects", projectId, "environments", search]`。
- Drawer 不影响 URL，关闭即销毁。
- 切换默认环境后，调用 `useProjectWorkspace().refresh()` 让 Header / ContextPanel 立即反映。

---

## 11. 校验规则

- name：1-50 字符，项目内唯一（由后端 409 返回）。
- base_url：必须以 `http://` 或 `https://` 开头。
- Headers：合法 JSON 对象（可空 `{}`）。
- Variables：合法 JSON 对象（可空 `{}`）。
- is_default：布尔；切换为 true 提交时由后端将其他 is_default 设为 false。

---

## 12. 与 Workspace 共享

- Drawer 关闭时若默认环境变化，调用 `refresh()` 让 ContextPanel 重新拉取 environments 与 readiness。
- Drawer 打开时，使用 Workspace 的默认环境 ID 作为当前上下文。
- 行内“设为默认”成功后，立即更新 ContextPanel 内的默认环境卡片。

---

## 13. 验收标准

- [ ] 新建、编辑、删除、设默认、查看 JSON 内容均成功。
- [ ] 默认环境无法删除，弹窗正确显示原因。
- [ ] 切默认后 Workspace ContextPanel 立即更新。
- [ ] JSON 编辑器支持格式校验与一键格式化。
- [ ] Drawer、Modal、Table、Toolbar 状态切换符合 Loading / Error / Empty 规范。
- [ ] 全部交互使用已有 API；不新增端点、不修改后端。
- [ ] `npm run check` 通过，无 `any`、无重复块、无尾随空格。
- [ ] 边界检查：未修改后端、数据库或迁移。
