# Execution Center 设计

> 文档类型：状态流 / 组件树 / 页面设计  
> 范围：Workspace → Run 模块的“Run Suite / Run Case / Run Project”执行流程  
> 实施约束：仅复用已有 API、不修改后端、不新增数据库、本阶段不写代码

---

## 1. 入口与触发

点击位置：

- Suite 详情顶部 [执行 Suite]。
- Suite 详情“批量添加”Modal 内的 [先创建 Case] 路径完成后回到 Suite。
- Workspace Header “快速执行”（Project 级）。
- Run 中心列表的“最近执行”行点击不再触发。
- Suite 列表行点击“名称”只跳详情，不直接执行。

每次进入执行前都需要再次打开 Execution Center，确认 Environment / Variables / Run 选项。

---

## 2. 状态流

Execution Center 的状态机设计为 `idle → configuring → running → success | error`，不依赖 polling：

```text
id
  ↓ [打开 Drawer]
configuring
  ├── 选择 environment（必填，默认选中 default）
  ├── 选择 scope（仅在 Run Center 出现，Suite 详情固定为 collection）
  ├── 选择 scope_target（与 scope 联动，加载对应列表）
  ├── 输入 run name（可空）
  ├── 输入 / 覆盖 variables（默认拉取所选环境的 variables，可改写）
  └── 提交按钮

[提交]
  ↓
submitting
  → useMutation：runsApi.create / runsApi.runCase
  → 成功：进入 running
  → 失败：回到 configuring，Toast + Drawer 错误提示

running
  ├── 进度显示（基于 elapsed 时间 + 占位状态）
  ├── 实时日志（GET /runs/{runId}/summary 间隔 1-2s 轮询）
  ├── 取消按钮（不可用：后端同步执行；改为提示）
  └── 后端 promise 完成 → 解析 run

success
  └── 自动跳转 /projects/:projectId/workspace/report/{runId}

error
  ├── Drawer 保留
  ├── 错误 Alert（来自 response.message）
  ├── 用户可继续编辑或取消
  └── 不自动关闭
```

说明：

- 同步执行：后端 `POST /runs/...` 返回结果即终态。
- 不引入 WebSocket / 轮询触发新接口；可使用 `runs/summary` 周期刷新，但 MVP 范围仅在“执行中”显示阶段性状态：Pending / Running / Finished。
- 真实进展：通过 `useMutation` 的 `onMutate` 切换 loading；详细进度（百分比）只展示相位文案。

---

## 3. 组件树

```text
RunExecutionDrawer（受控 Modal / Drawer）
├── DrawerHeader
│   ├── Title：执行 / 执行 Suite / 执行 Case
│   └── ScopeTag + TargetLabel
├── DrawerBody
│   ├── EnvironmentSelector（Select + 显示 base_url + 默认徽标）
│   ├── VariablesEditor
│   │   ├── SourcePreview（环境 variables 只读）
│   │   ├── OverrideList（可勾选覆盖）
│   │   └── JSONViewer / ErrorMessage
│   ├── RunNameInput
│   ├── ScopeSummary（case 数量 / Suite 名称 / 范围描述）
│   └── EmptyWarning（无环境 / 无默认 / 范围无启用 Case）
├── DrawerFooter
│   ├── Run Now（主操作）
│   ├── Cancel
│   └── LoadingInline（提交阶段展示）
└── RunStatusModal（执行中 / 完成阶段的弹层）
    ├── PhaseHeader（Pending / Running / Finished）
    ├── ProgressBlock
    │   ├── Progress / Spin
    │   └── 已完成 N / 共 M（若可估算）
    ├── LogStream
    │   └── 折叠显示 run 简要步骤 / 时间戳
    └── ResultFooter
        ├── 错误时显示 Retry / Close
        └── 成功时显示 “打开 Report” / Close
```

---

## 4. 页面骨架

```text
Drawer 720
  · 标题：执行 / 子标题（Suite 名 / Case 名 / Project）
  · 主体：
    - Environment（必选，含 Default 徽标 + Base URL）
    - Variables（默认显示环境 variables，可逐项覆盖）
    - Run Name（可选）
    - Scope Summary（case 数量 / Suite 名称）
  · Footer：
    - 取消（关闭 Drawer）
    - Run Now（loading 时显示“正在执行…”）

[提交成功]
  → Drawer 自动关闭
  → 立即跳到 /projects/{projectId}/workspace/report/{runId}
```

### 4.1 Suite 入口

来源：Suite 详情顶部 [执行 Suite]。

Drawer 默认配置：

- scope：collection
- scope_id：当前 Suite.id
- environment：默认选中 default
- run name：留空
- variables：默认从 environment 拉取

### 4.2 Case 入口

来源：Case 列表的 [执行] 按钮、Case 详情的 [执行] 按钮。

Drawer 默认配置：

- scope：case
- scope_id：当前 case.id
- environment：默认选中 default
- run name：留空
- variables：默认从 environment 拉取
- 若 case 不可执行（disabled / 缺默认环境），按钮 disabled + Tooltip 提示

### 4.3 Project 入口

来源：Workspace Header 快速执行按钮（带 `?scope=project`）；Run Center 默认页。

Drawer 配置：

- scope：project
- scope_id：当前 project.id
- environment：默认 default
- run name：可选
- variables：默认从 environment 拉取

---

## 5. Run 状态机与 UI 映射

| 状态 | 触发 | Drawer 显示 | 顶部状态徽标 |
|---|---|---|---|
| idle | 首次打开 | 表单 | “待执行” |
| configuring | 表单变更中 | 同上 | “待执行” |
| submitting | 点 Run Now 后 | 主按钮 loading；其它按钮 disabled | “正在同步执行” |
| running | `runsApi.create` promise pending | Drawer 关闭，弹出 RunStatusModal | “执行中” |
| success | `runsApi.create` 成功 | Drawer 关闭，跳 Report | “已完成” |
| error | `runsApi.create` 失败 | 错误 Alert；用户继续操作 | “失败” |

RunStatusModal 在 success / error 时可手动关闭；success 时提供“打开 Report”快捷按钮。

---

## 6. 变量覆盖

| 来源 | 行为 |
|---|---|
| `Environment.variables` | 展示在 SourcePreview；只读 |
| `OverrideList` | 用户可勾选 / 修改值；最终合并为运行 payload |
| `run name` | 直接拼接为 `name` 字段 |

最终 payload：

```text
{
  name?: string,
  environment_id: UUID,
  scope: case | collection | project,
  scope_id: UUID
}
```

注意：当前后端 `TestRunPayload` 不包含 variables 字段，因此变量覆盖仅在 UI 层面展示，不会传往后端；后端执行仍使用 environment 的 variables。这一限制在 UI 注明“变量仅作展示，实际执行仍按环境配置”进行说明，避免误导。

---

## 7. Loading / Progress / Logs

- `submitting`：主按钮 loading；Footer 显示 “正在执行…” 文字；Drawer 内部禁用所有控件。
- `running`：自动跳 Report 后，不再使用 RunStatusModal。MVP 范围内后端同步执行；如需进度展示，使用 `run.summarize` 信息中的 `total`、`passed`、`failed`、`error` 等字段（如果后端在 `POST /runs` 响应中携带）。当前后端在创建 Run 时返回完整 `TestRunResponse`，所以直接展示该数据。
- 日志：MVP 不拉取后端日志（不存在日志端点）。若后端后续提供 `GET /runs/{id}/summary` 实时端点，再扩展 Logs 组件。

---

## 8. 错误与边界状态

| 场景 | 表现 |
|---|---|
| 没有 default environment | Drawer 顶部红色 Alert：未设置默认环境。Run 按钮 disabled。提示用户到 Environment 模块配置。 |
| Project 无任何启用 Case | Scope Summary 提示 “当前 Project 没有启用的 Case”。Run 按钮 disabled。 |
| Case disabled | 入口按钮 disabled + Tooltip。 |
| Suite 无 Case | Suite 详情执行按钮点击后 Drawer 仍打开，但提示 Suite 无 Case，Run 按钮 disabled。 |
| 环境列表加载失败 | Drawer 内 Alert 提示环境加载失败；Run 按钮 disabled。 |
| 提交失败 | Drawer 保留；底部 Alert 显示后端 message；按钮恢复。 |
| 网络中断 | `useMutation` 抛错，呈现通用错误 Alert。 |

---

## 9. 路由与上下文

- 入口：
  - Suite 详情 → Drawer → 成功后跳 `/projects/{projectId}/workspace/report/{runId}`。
  - Project 头部 → Drawer → 成功后跳同上。
  - Case 入口 → Drawer → 成功后跳同上。
- 关闭 Drawer 不修改 URL。
- Run Center（`/projects/{projectId}/workspace/run`）：
  - 不弹 Drawer；展示表单 + 最近 Run 列表。
  - 表单提交后同样跳 Report。
- 上下文：
  - `useProjectWorkspace().refresh()` 不需要在 Drawer 中显式调用；跳 Report 后 Run 列表与统计由 Report 页面触发。

---

## 10. 验收标准

- [ ] Suite 入口、Case 入口、Project 入口三种场景均能正常打开 Drawer。
- [ ] Drawer 显示 Environment、Variables、Run name、Scope Summary。
- [ ] 默认环境选中后 Drawer 自动通过。
- [ ] 没有默认环境时 Run Now 不可点且有明确提示。
- [ ] 提交后自动跳 Report 详情，列表与 Dashboard 数据自动更新。
- [ ] 提交失败时 Drawer 保留，错误提示明确。
- [ ] 同步执行期间不显示进度条 / WebSocket，仅以提交 loading 表达。
- [ ] 任何修改都不引入后端新接口；仅复用现有 Run / RunSummary / Environment API。
- [ ] 与 Workspace 共享：Drawers 嵌套在 ProjectWorkspaceLayout 内，Header / ContextPanel 仍可访问。
- [ ] `npm run check` 通过；无 `any`、无重复块、无尾随空格。
- [ ] 边界检查：未修改后端、数据库或迁移。
