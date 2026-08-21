# API 自动化测试平台 · 反馈（Feedback）统一规范

> 文档类型：Feedback 统一设计规范
> 适用范围：API 自动化测试平台所有页面的 Loading / Submitting / Running / Importing / Deleting / Toast / Notification / Retry / Progress
> 设计阶段：先设计，不涉及代码实现
> 配套：`PRD.md`、`INFORMATION_ARCHITECTURE.md`、`PROJECT_WORKSPACE.md`、`NavigationUX.md`、`Journey.md`、`WorkflowReview.md`、`FirstRunGuide.md`、`EmptyState.md`、`QuickAction.md`
> **硬约束：不新增任何 API、不新增任何数据库表、不新增功能模块——仅复用已有 Ant Design 组件（Spin / Skeleton / Alert / Modal / Drawer / message）+ React Query 状态 + 已有前端交互**

---

## 0. 设计目标

统一全平台**所有用户可见的反馈**（视觉、文案、按钮、出现 / 消失时机），让用户**清楚知道"系统在做什么"和"我下一步该做什么"**。

**三大原则**：

1. **永远有反馈**：用户任何操作（点按钮 / 提交 / 删除 / 执行）**必须有视觉反馈**，不允许"点了没反应"。
2. **反馈有时限**：所有反馈必须有**明确的出现 / 消失时机**，不允许"loading 转圈无终点"。
3. **反馈可恢复**：失败状态必须提供**重试入口**，不允许"错误弹窗只有 OK"。

---

## 1. 反馈类型分类

| # | 类型 | 用户感知 | 主要组件 |
|:-:|---|---|---|
| 1 | **Loading** | "数据在加载" | Spin / Skeleton / LoadingBlock |
| 2 | **Submitting** | "我刚提交的请求在处理" | 按钮 loading 状态 / Drawer loading |
| 3 | **Running** | "测试在执行" | Spin + Alert（带预估时长文案） |
| 4 | **Importing** | "OpenAPI 在导入" | Spin + 进度文案（无真实进度条） |
| 5 | **Deleting** | "删除中" | Popconfirm loading / Modal loading |
| 6 | **Toast** | "操作结果通知"（成功 / 失败 / 警告） | Ant Design `message` |
| 7 | **Notification** | "需要用户关注的重要通知" | Ant Design `notification` |
| 8 | **Retry** | "失败后可重试" | Button（带重试图标）/ 错误状态行 |
| 9 | **Progress** | "长时间任务的进度" | Progress / Steps（仅前端展示，无真实进度） |

---

# 2. Loading 加载反馈

## 2.1 触发时机

| 触发点 | 数据请求 | UI 表现 |
|---|---|---|
| 列表页首次加载 | `isLoading === true` | **全表 Skeleton** |
| 列表页翻页 / 搜索 | `isFetching === true`（旧数据仍显示） | **表格顶部 Spin**（不替换数据） |
| 详情页首次加载 | `isLoading === true` | **整页 Skeleton**（行级骨架） |
| 详情页切换 Tab | `isFetching === true` | **Tab 内 Skeleton**（不替换其他 Tab） |
| Drawer 打开（拉取远程数据） | `isLoading === true` | **Drawer 内 Spin**（居中） |

## 2.2 持续时间

| 情况 | 反馈策略 |
|---|---|
| < 300ms | 不显示 Loading（避免闪烁） |
| 300ms ~ 3s | 显示 Skeleton / Spin |
| > 3s | 显示 Skeleton + **文案** "数据加载较慢，请稍候"（避免用户以为卡死） |
| > 30s | **Toast 警告** + 后台继续加载（用户可继续操作） |

## 2.3 文案模板

| 场景 | 文案 |
|---|---|
| 列表加载 | （无文案，仅 Skeleton） |
| 详情加载 | （无文案，仅 Skeleton） |
| 慢加载 | "数据加载较慢，请稍候..." |
| 超时提示 | "请求耗时较长，已转后台加载" |

## 2.4 颜色 / 视觉

| 元素 | 颜色 |
|---|---|
| Skeleton | 灰色 `#f0f0f0`（Ant Design 默认） |
| Spin 圆圈 | 主色 `#1677ff`（Ant Design 默认） |
| Spin 背景 | 透明 / 浅灰 `#fafafa` |
| 慢加载文案 | 次要色 `#8c8c8c` |

## 2.5 按钮

无按钮（用户等待即可）。

## 2.6 反例

- ❌ 列表加载时显示"暂无数据"（实际还在加载）
- ❌ Loading 时间无上限，用户以为卡死
- ❌ Skeleton 闪烁（应使用稳定的占位骨架）

## 2.7 实现位置

复用 `frontend/src/components/AsyncState.tsx` 中的 `<LoadingBlock rows={N} />`。

---

# 3. Submitting 提交反馈

## 3.1 触发时机

| 触发点 | 反馈位置 |
|---|---|
| Drawer 表单提交 | Drawer 内主按钮 loading + 副按钮 disabled + 字段 disabled |
| Popconfirm 确认 | Popconfirm 确认按钮 loading + 取消按钮 disabled |
| Modal 表单提交 | Modal 主按钮 loading + 关闭按钮 disabled |
| 行内操作（如"切换默认"） | 行内图标按钮 loading + 其他行操作 disabled |
| 列表批量操作 | 工具栏批量按钮 loading + 表格 disabled |

## 3.2 持续时间

| 情况 | 反馈策略 |
|---|---|
| 提交中 | 按钮 loading 转圈 + 字段 disabled |
| 成功 | Toast 成功 + Drawer 自动关闭 + 列表自动刷新 |
| 失败 | Drawer / Modal **保留** + 错误 Alert 显示 + 按钮恢复 |
| 超时（> 30s） | 按钮 loading 保留 + Toast 警告"提交较慢" |

## 3.3 文案模板

| 场景 | 按钮文案 |
|---|---|
| 默认 | "保存" / "确认" / "Run Now" |
| Submitting 中 | "保存中..." / "确认中..." / "提交中..." |
| Submitting 完成（自动恢复） | （恢复默认文案） |

**禁止文案**："请稍候" / "Loading..." / "处理中"（用户不懂）。

**推荐文案**：

| 动作 | Submitting 文案 |
|---|---|
| 保存 Project | "保存中..." |
| 保存 Environment | "保存中..." |
| 保存 Suite | "保存中..." |
| 保存 Case | "保存中..." |
| 删除 Project | "删除中..." |
| 删除 Environment | "删除中..." |
| 删除 Suite | "删除中..." |
| 删除 Case | "删除中..." |
| 设默认环境 | "设置中..." |
| 设置排序 | "排序中..." |
| 批量添加 Case | "添加中..." |
| 修改密码 | "修改中..." |

## 3.4 颜色 / 视觉

| 元素 | 颜色 |
|---|---|
| Loading 转圈 | 主按钮背景色（蓝色 `#1677ff`）+ 白圈 |
| Disabled 按钮 | 灰底 `#f5f5f5` + 灰字 `#bfbfbf` |
| 错误 Alert | 红 `#ff4d4f` 边框 + 浅红 `#fff2f0` 背景 |

## 3.5 按钮

| 按钮 | 状态 |
|---|---|
| 主操作按钮 | loading + 文案变化 |
| 副操作按钮 | disabled |
| 取消按钮 | disabled（避免误触） |
| 关闭按钮（×） | disabled（避免误触） |

## 3.6 实现位置

每个 Modal / Drawer / Popconfirm 的 `confirmLoading={mutation.isPending}`（已有模式）。

---

# 4. Running 执行反馈（同步执行）

## 4.1 触发时机

`Run Now` / `执行 Suite` / `执行 Case` / `执行 Project` 点击后，进入 `phase === 'submitting'`（参见 `RunExecutionDrawer.tsx`）。

## 4.2 持续时间

| 情况 | 反馈策略 |
|---|---|
| < 5s（小 Suite / 单 Case） | RunExecutionDrawer 按钮 loading + "执行中..." |
| 5s ~ 30s（中 Suite） | Drawer 内 Alert："正在同步执行，预计 < 30 秒" |
| > 30s（大 Suite） | Drawer 内 Alert："用例较多，请耐心等待"+ 后台继续 |
| > 60s | Toast 警告"执行时间较长" |
| 完成 | Drawer 自动关闭 → **自动跳转** Run 详情 |
| 失败 | Drawer **保留** + 错误 Alert + 按钮恢复 |

## 4.3 文案模板

| 阶段 | 文案 |
|---|---|
| Run Drawer Submitting | "正在同步执行" / "执行中...（请勿重复提交）" |
| Drawer Footer 提示 | "同步执行中，完成后会自动跳 Report" |
| Drawer 内 Alert | "后端为同步执行；请勿关闭或重复提交" |
| 超时（> 60s） | Toast: "执行时间较长，已在后台运行；完成后会通知" |
| 成功 Toast | "执行完成，正在打开报告" |
| 失败 Alert | "执行失败：[后端 message]" |

## 4.4 颜色 / 视觉

| 元素 | 颜色 |
|---|---|
| Submitting 按钮 | 主色蓝 + 白 loading 圈 |
| Alert 信息 | 蓝 `#1677ff`（info 主题） |
| 超时 Toast | 黄 `#faad14`（warning 主题） |
| 成功 Toast | 绿 `#52c41a`（success 主题） |
| 失败 Alert | 红 `#ff4d4f`（error 主题） |

## 4.5 按钮

| 按钮 | Running 中状态 |
|---|---|
| Run Now（主） | loading + 文案"执行中..." |
| 取消（副） | disabled |
| Drawer 关闭（×） | disabled |
| Drawer 内其他控件（环境选择 / Run Name） | disabled |

## 4.6 反例

- ❌ 显示"已完成 X / 共 Y"进度条（前端无法估算，无真实进度）
- ❌ 用户可点"取消"（后端同步执行，无取消接口）
- ❌ Drawer 关闭后丢失错误信息

## 4.7 实现位置

`RunExecutionDrawer.tsx` 已有 `phase` 状态机（详见 `EXECUTION_CENTER.md`）。

---

# 5. Importing 导入反馈（OpenAPI Import）

## 5.1 触发时机

OpenAPI Import 流程分 **3 个阶段**，每个阶段有不同的反馈：

| 阶段 | 触发 | 反馈 |
|---|---|---|
| **1. 解析** | 点击"预览" / 选来源 | Drawer 内 Spin + "正在解析 OpenAPI..." |
| **2. 预览展示** | 解析完成 | 预览列表展示 |
| **3. 确认导入** | 点击"导入" | Modal 内 Spin + "正在导入..." + 导入完成后结果摘要 |

## 5.2 持续时间

| 情况 | 反馈策略 |
|---|---|
| 解析 < 3s | Drawer 内 Spin 显示，解析完成后立即切换 |
| 解析 > 10s | Toast 警告 + 后台继续 |
| 导入 < 5s（小文档） | Modal 内 Spin + "正在导入..." |
| 导入 5s ~ 30s | Modal 内 Spin + "正在导入 N 条用例..." |
| 导入 > 30s | Modal 内 Spin + Toast 警告 |
| 导入成功 | Toast 成功 + 自动跳 Suite 详情 |
| 导入失败 | Modal **保留** + 错误 Alert + 重试按钮 |

## 5.3 文案模板

| 阶段 | 文案 |
|---|---|
| 解析中 | "正在解析 OpenAPI..." |
| 解析成功 | （无文案，直接展示预览） |
| 解析失败 | "解析失败：[错误信息]" + "请检查 OpenAPI 文档是否符合 3.0 / 3.1 规范" |
| 导入中 | "正在导入 X 条用例..." |
| 导入成功 | Toast: "成功导入 N 条用例，跳过 M 条" |
| 导入完成 | 自动跳 Suite 详情 |
| 导入失败 | Modal Alert: "导入失败：[错误信息]" |

## 5.4 颜色 / 视觉

| 元素 | 颜色 |
|---|---|
| 解析中 Spin | 蓝 `#1677ff` |
| 导入中 Spin | 蓝 `#1677ff` |
| 解析失败 Alert | 红 `#ff4d4f` |
| 导入失败 Alert | 红 `#ff4d4f` |
| 成功 Toast | 绿 `#52c41a` |
| 预览展示列表行 | 状态色（passed 绿 / failed 红 / skipped 灰） |

## 5.5 按钮

| 阶段 | 按钮状态 |
|---|---|
| 解析中 | "预览"按钮 disabled |
| 解析成功 | "预览"按钮 enabled；"导入"按钮 enabled |
| 解析失败 | "预览"按钮 enabled（可重试）；"导入"按钮 disabled |
| 导入中 | "导入"按钮 loading + "导入中..."；"取消"按钮 enabled（可中断） |
| 导入成功 | 自动关闭 Modal |
| 导入失败 | Modal 保留，"重试"按钮 enabled |

## 5.6 反例

- ❌ 显示"导入进度 30%"（前端无法估算，无真实进度）
- ❌ 解析中不显示 Spin（用户以为没反应）
- ❌ 导入失败后用户必须重新选文件（应保留解析结果，提供"重试"）

## 5.7 实现位置

`WorkspaceImport.tsx` 已有 mutation 流程；增加 Spin + Alert 反馈。

---

# 6. Deleting 删除反馈

## 6.1 触发时机

| 触发点 | 反馈 |
|---|---|
| Popconfirm 点击"删除" | Popconfirm 按钮 loading + 取消按钮 disabled |
| Modal 二次确认 + 删除 | Modal 按钮 loading + 输入框 disabled |
| 行内删除按钮 | 行变灰 + 按钮 loading |

## 6.2 持续时间

| 情况 | 反馈策略 |
|---|---|
| 删除 < 2s | 行渐隐消失（fade out 200ms） |
| 删除 > 5s | Popconfirm / Modal 保留 loading + 错误 Alert |
| 失败 | Popconfirm **保留** + Toast 错误 + 按钮恢复 |
| 成功 | Toast 成功 + 自动跳转或刷新 |

## 6.3 文案模板

| 操作 | Popconfirm 文案 | 按钮文案 |
|---|---|---|
| 删除 Environment | "删除环境 [name]？该环境已被 Run 引用 N 次（不影响历史 Report）" | "删除中..." |
| 删除 Suite | "删除 Suite [name]？只删除 Suite 及关联，不会删除 API Case 本体" | "删除中..." |
| 删除 Case | "删除 Case [name]？删除后无法恢复（请输入 Case 名确认）" | "删除中..." |
| 删除 Project | "删除 Project [name]？删除后 Environment / Suite / Case 全部消失" | "删除中..." |
| 删除 Run | （暂不支持） | — |
| 删除 User | "禁用用户 [email]？"（软禁用，非物理删除） | "禁用中..." |
| 删除 Role | "删除角色 [name]？" | "删除中..." |

## 6.4 颜色 / 视觉

| 元素 | 颜色 |
|---|---|
| Popconfirm 删除按钮 | 红色 `#ff4d4f`（danger 主题） |
| 成功 Toast | 绿 `#52c41a` |
| 失败 Toast | 红 `#ff4d4f` |
| 行渐隐 | 透明度 100% → 0（200ms 渐变） |

## 6.5 按钮

| 阶段 | 按钮状态 |
|---|---|
| 删除中 | 主按钮 loading + 文案"删除中..." |
| 删除中 | 取消按钮 disabled |
| 删除失败 | 主按钮恢复 + Alert 显示 + Toast 错误 |
| 删除成功 | Popconfirm 自动关闭 + Toast 成功 |

## 6.6 反例

- ❌ 删除后无 Toast 提示（用户不知是否成功）
- ❌ Popconfirm 立即关闭（用户不知是否完成）
- ❌ 删除失败后弹窗自动关闭（用户无法重试）

## 6.7 实现位置

每个 Modal / Popconfirm 已使用 `okButtonProps={{ loading: mutation.isPending }}` 模式（已有结构）。

---

# 7. Toast 短消息反馈

## 7.1 触发时机

用户操作**完成后**（成功 / 失败 / 警告）通过 Toast 通知。**不用于进行中状态**（用 Loading / Submitting）。

| 触发点 | Toast 类型 |
|---|---|
| 创建 / 更新 / 删除成功 | success |
| 表单校验失败 | error |
| 网络错误 / 后端 500 | error |
| 复制成功 | success（"已复制到剪贴板"） |
| 切换 Project | success（"已切换到 Project X"） |
| Token 失效 | warning |
| 操作冲突（如重名） | warning |
| 即将超时的提示 | warning |
| 信息性提示（如"已记录"） | info |

## 7.2 持续时间

| Toast 类型 | 默认时长 | 可配置 |
|---|---|---|
| **success** | 3 秒 | 否（用户已经看到结果） |
| **info** | 3 秒 | 否 |
| **warning** | 5 秒 | 是（用户需要更多时间看） |
| **error** | 5 秒 | 是（用户需要看到错误信息） |

**长错误信息**：若 message > 50 字，使用 **Notification**（带关闭按钮 + 5~8 秒自动关闭）。

## 7.3 文案模板

| 操作 | Toast 文案 |
|---|---|
| 创建 Project | "已创建 Project [name]" |
| 更新 Project | "已保存" |
| 删除 Project | "已删除 Project [name]" |
| 创建 Environment | "已创建环境" |
| 设默认环境 | "[name] 已设为默认环境" |
| 删除 Environment | "已删除环境 [name]" |
| 创建 Suite | "已创建 Suite [name]" |
| 删除 Suite | "已删除 Suite [name]" |
| 创建 Case | "已创建 Case [name]" |
| 更新 Case | "已保存" |
| 删除 Case | "已删除 Case [name]" |
| 添加 Case 到 Suite | "已添加 X 条 Case" |
| 从 Suite 移除 Case | "已从 Suite 移除" |
| Suite 排序 | "顺序已更新" |
| OpenAPI 导入 | "成功导入 X 条用例" / "导入失败：[错误信息]" |
| 执行 Run | "执行完成，正在打开报告" |
| 复制成功 | "已复制到剪贴板" |
| 切换 Project | "已切换到 Project [name]" |
| 切换默认环境 | "默认环境已切换为 [name]" |
| 刷新 | "已刷新" |
| 登录失败 | "账号或密码错误" / "账号已禁用" / "请求过于频繁，请稍后再试" |
| Token 失效 | "登录已过期，正在跳转登录页..." |
| 网络错误 | "网络异常，请检查连接后重试" |

**禁止文案**：

- ❌ "操作成功"（不说做了什么）
- ❌ "Error"（不说具体错误）
- ❌ "成功！" / "失败！"（感叹号显得轻浮）

## 7.4 颜色 / 视觉

| Toast 类型 | 颜色（Ant Design） |
|---|---|
| **success** | 绿 `#52c41a` + 白字 |
| **info** | 蓝 `#1677ff` + 白字 |
| **warning** | 黄 `#faad14` + 白字 |
| **error** | 红 `#ff4d4f` + 白字 |

**位置**：默认右上角（Ant Design 默认），全局统一。

## 7.5 按钮

Toast **不带按钮**（自动消失）。

**例外**：错误 Toast 中若包含"重试"操作，使用 Notification 替代（带"重试"按钮）。

## 7.6 实现位置

全局 `message.success(...)` / `message.error(...)`（Ant Design `App.useApp()`）。

---

# 8. Notification 通知反馈

## 8.1 触发时机

**比 Toast 更重要**的事件，需要**用户主动关闭**或**停留更长时间**：

| 触发点 | 类型 |
|---|---|
| Run 执行失败（不是测试失败，是执行错误） | error |
| Token 即将过期 | warning |
| 数据同步冲突 | warning |
| 长时间操作完成（异步任务，本期无） | success |
| 错误详情（message > 50 字） | error |

## 8.2 持续时间

| Notification 类型 | 默认时长 |
|---|---|
| **success** | 4 秒 |
| **info** | 5 秒 |
| **warning** | 6 秒 |
| **error** | 8 秒（长于 Toast）或**不自动关闭**（需用户手动 ×） |

## 8.3 文案模板

| 场景 | 标题 | 描述 |
|---|---|---|
| Run 执行错误 | "执行失败" | "[Run 名称] 执行失败：[错误码] [错误信息] [重试]" |
| Token 即将过期 | "登录即将过期" | "Token 将在 5 分钟后过期，请保存工作" |
| 数据冲突 | "保存冲突" | "[资源名] 已被其他用户修改，请刷新后重试 [刷新]" |
| 错误详情 | "[操作]失败" | "[详细错误信息 ≥ 50 字]" |

## 8.4 颜色 / 视觉

| 类型 | 颜色 |
|---|---|
| success | 绿 `#52c41a` |
| info | 蓝 `#1677ff` |
| warning | 黄 `#faad14` |
| error | 红 `#ff4d4f` |

**位置**：默认右上角（Ant Design 默认）。

**图标**：每种类型有标准图标（CheckCircleOutlined / InfoCircleOutlined / WarningOutlined / CloseCircleOutlined）。

## 8.5 按钮

| 类型 | 按钮 |
|---|---|
| error（执行失败） | "[重试]" 按钮（点击重试） |
| error（冲突） | "[刷新]" 按钮（点击刷新） |
| warning（Token 过期） | "[保存]" 按钮（点击保存当前编辑） |

## 8.6 实现位置

全局 `notification.error({ message, description, btn })`（Ant Design `App.useApp()`）。

---

# 9. Retry 重试反馈

## 9.1 触发时机

| 触发点 | 重试入口 |
|---|---|
| 列表请求失败 | 列表 ErrorState 显示"[重新加载]"按钮 |
| 详情请求失败 | 详情 ErrorState 显示"[重试]"按钮 |
| Tab 内请求失败 | Tab 内 ErrorState 显示"[重试]"按钮 |
| Drawer 内请求失败 | Drawer 内 Alert + "[重试]"按钮 |
| Mutation 失败 | Toast 失败 + "[重试]"按钮（Notification） |
| Network 错误 | 全局 Toast + 用户主动刷新页面 |

## 9.2 持续时间

重试按钮**一直可见**直到操作成功。

## 9.3 文案模板

| 场景 | 错误文案 | 按钮文案 |
|---|---|---|
| 列表请求失败 | "无法加载 [对象列表]" | "重新加载" |
| 详情请求失败 | "无法加载 [对象详情]" | "重试" |
| Tab 内请求失败 | "[Tab 名] 数据加载失败" | "重试" |
| Drawer 内请求失败 | "[操作]失败：[错误信息]" | "重试" |
| Mutation 失败 | "[操作]失败：[错误信息]" | "重试"（Notification） |
| 404 资源不存在 | "[对象名] 不存在或已被删除" | "返回列表" |
| 403 无权限 | "无权限访问此资源" | "返回 Dashboard" |
| 500 服务器错误 | "服务器开小差了，请稍后再试" | "重试" |
| 网络中断 | "网络连接已断开" | "重试" |

## 9.4 颜色 / 视觉

| 元素 | 颜色 |
|---|---|
| ErrorState 卡片 | 红色边框 `#ff4d4f` + 浅红背景 `#fff2f0` |
| 重试按钮 | Primary 蓝色（主操作） |
| 返回按钮 | Default 灰色（次操作） |

## 9.5 按钮

| 按钮 | 行为 |
|---|---|
| **重试** | 重新发起失败的请求 |
| **返回列表** | 跳转到对应的列表页 |
| **返回 Dashboard** | 跳 Dashboard |
| **取消** | 关闭 Modal / Drawer |

## 9.6 反例

- ❌ 错误状态只显示"网络错误"+ OK 按钮（用户无法重试）
- ❌ 错误文案不具体（"出错了"）
- ❌ 404 直接跳 Dashboard（掩盖问题）

## 9.7 实现位置

复用 `frontend/src/components/AsyncState.tsx` 的 `<ErrorState error onRetry title />`。

---

# 10. Progress 进度反馈

## 10.1 触发时机

| 触发点 | 进度反馈 |
|---|---|
| Run 执行（同步） | **不使用真实进度条**（后端同步执行无进度数据），仅用文案"正在同步执行" |
| OpenAPI Import | **不使用真实进度条**，仅用文案"正在导入 X 条用例..." |
| 批量操作 | **不使用真实进度条**，用文案 + 按钮 loading |
| 文件上传 | （本期无） |

## 10.2 持续时间

N/A（无真实进度）。

## 10.3 文案模板

| 阶段 | 文案 |
|---|---|
| Run 执行 | "正在同步执行，预计 < 30 秒" / "执行时间较长，请耐心等待" |
| OpenAPI Import | "正在解析 OpenAPI..." / "正在导入 X 条用例..." |
| 批量添加 Case | "正在添加 X 条 Case..." |

## 10.4 颜色 / 视觉

| 元素 | 颜色 |
|---|---|
| 文字 | 次要色 `#8c8c8c` |
| Spin | 主色蓝 `#1677ff` |

## 10.5 按钮

无新增按钮（沿用 Submitting / Running 的按钮策略）。

## 10.6 反例

- ❌ 假进度条（如 "30% → 50% → 80%"，但实际无真实数据）
- ❌ "已完成 X / Y"（前端无 Y 估值）
- ❌ 进度条卡在 99%（用户无法判断何时完成）

## 10.7 实现位置

无新增组件；沿用 `<Spin />` + `<Alert type="info" />`。

---

# 11. 全局反馈策略汇总表

| 反馈类型 | 何时出现 | 何时消失 | 文案 | 颜色 | 按钮 |
|---|---|---|---|---|---|
| **Loading** | 数据请求开始 | 请求完成 / 超时 | 无 / "数据加载较慢，请稍候" | 灰骨架 / 蓝 Spin | 无 |
| **Submitting** | 用户提交表单 / 操作 | 提交完成 / 失败 | "保存中..." / "删除中..." | 主按钮蓝 + loading | 主按钮 loading，副按钮 disabled |
| **Running** | 点击 Run Now | 同步执行完成 / 失败 / 超时 | "正在同步执行" / "执行完成，正在打开报告" | 蓝 Alert + 绿 Toast | 主按钮 loading |
| **Importing** | 点击"预览" / "导入" | 解析 / 导入完成 / 失败 | "正在解析 OpenAPI..." / "正在导入 X 条用例..." | 蓝 Spin + 绿 Toast | 主按钮 loading |
| **Deleting** | Popconfirm / Modal 点击删除 | 删除完成 / 失败 | "删除中..." / "已删除 [name]" | 红色按钮 + loading | 主按钮 loading |
| **Toast** | 操作完成后 | 3 秒（success/info） / 5 秒（warning/error） | "[动词] + [对象] + [结果]" | 4 种类型颜色 | 无按钮（Notification 例外） |
| **Notification** | 重要事件 | 4~8 秒 / 用户手动关闭 | 标题 + 描述 | 4 种类型颜色 | 可选重试 / 刷新按钮 |
| **Retry** | 请求失败 / 操作失败 | 一直可见直到成功 | "[动作]失败：[错误信息]" | 红 ErrorState + 蓝 Retry | 重试 / 返回 |
| **Progress** | （不使用真实进度） | N/A | "正在 [动作]..." | 蓝 Spin + 灰文字 | 无新增 |

---

# 12. 反馈优先级

当多个反馈同时出现时，按以下优先级处理：

| 优先级 | 反馈类型 | 行为 |
|:-:|---|---|
| **P0** | Modal / Drawer 内 Alert | 必须保留，不被其他反馈替换 |
| **P0** | Submitting 按钮 loading | 必须保留 |
| **P1** | Notification | 可被 Toast 替换 |
| **P2** | Toast | 自动消失 |
| **P2** | Spin | 自动消失 |

**反例**：Modal 内显示 Toast 后 Modal 自动关闭（用户丢失错误信息）。

---

# 13. 反馈的可达性

## 13.1 键盘可达

| 操作 | 快捷键 |
|---|---|
| 关闭 Toast | Esc |
| 关闭 Notification | Esc 或点击 × |
| 关闭 Modal / Drawer | Esc |
| 重试按钮 | Tab + Enter |
| 确认按钮 | Enter（表单提交） |

## 13.2 屏幕阅读器

- Toast / Notification 内容必须通过 `aria-live` 朗读
- Loading Spin 必须有 `aria-label="加载中"`
- 错误 Alert 必须有 `role="alert"`

## 13.3 颜色 + 文案双通道

- **绝不**只靠颜色区分反馈类型（success/error）—— 必须有**文字 / 图标**
- 颜色 + 图标 + 文字 三通道同时传达

---

# 14. 反馈的国际化预留

虽然本期仅简体中文，但所有反馈文案应：

- **集中存放**：`frontend/src/i18n/zh-CN/feedback.ts`（即便只有中文）
- **不在组件内硬编码**：所有文案从 i18n 文件读取
- **保留 i18n Key 命名规范**：`feedback.{type}.{scenario}`

```typescript
// 后续接入 i18n 时
feedback.toast.project.created = "已创建 Project {name}";
feedback.toast.case.deleted = "已删除 Case {name}";
feedback.error.network = "网络异常，请检查连接后重试";
```

---

# 15. 实施优先级

| # | 任务 | 优先级 | 估时 | 价值 |
|---:|---|:-:|:-:|:-:|
| 1 | 全局 Toast 文案规范 review + 替换 | P0 | 1 天 | 高 |
| 2 | LoadingBlock / Spin / Skeleton 时机统一 | P0 | 0.5 天 | 高 |
| 3 | Submitting 按钮文案统一（"保存中..." 等） | P0 | 0.5 天 | 高 |
| 4 | ErrorState 重试按钮规范化 | P0 | 0.5 天 | 高 |
| 5 | Drawer 失败保留 + Alert 错误 | P0 | 0.5 天 | 高 |
| 6 | Running 阶段超时文案 + Toast 警告 | P0 | 0.5 天 | 高 |
| 7 | Importing 解析 / 预览 / 确认 3 阶段反馈 | P0 | 1 天 | 高 |
| 8 | Deleting 各场景 Popconfirm / Modal 文案 | P0 | 0.5 天 | 高 |
| 9 | Notification（仅 Run 错误 + Token 过期） | P1 | 0.5 天 | 中 |
| 10 | 反馈文案集中到 i18n 文件 | P1 | 1 天 | 中 |
| 11 | 反馈优先级（Alert vs Toast）冲突处理 | P1 | 0.5 天 | 中 |
| 12 | a11y 优化（aria-live / aria-label） | P2 | 1 天 | 中 |

---

# 16. 不在范围（防止范围蔓延）

- ❌ 真实进度条（依赖后端实时进度接口，本期后端为同步执行）
- ❌ 全局通知中心（依赖后端推送接口）
- ❌ 邮件 / 飞书 / 钉钉 通知集成
- ❌ 反馈统计 / 分析（依赖后端埋点）
- ❌ 反馈个性化配置（用户自定义）
- ❌ 多语言 i18n（本期仅简体中文，保留接口）

---

# 17. 验收指标

| 指标 | 计算方式 | 当前 | 目标 |
|---|---|---|---|
| **所有用户操作有反馈** | 操作 → 反馈比例 | — | **100%** |
| **Loading 超时提示** | > 3s 显示提示 | 部分 | **100%** |
| **失败状态可重试** | 错误状态含重试按钮的比例 | — | **100%** |
| **Toast 文案准确率** | 用户调研（5 分制） | — | ≥ 4.5 |
| **失败后用户丢失操作比例** | 失败后 Drawer / Modal 关闭的比例 | 部分 | **0%** |
| **a11y 达标** | 屏幕阅读器可读反馈的比例 | — | **100%** |
| **反馈无虚假进度** | 假进度条 / 假百分比 | — | **0%** |

---

# 18. 文档约束再确认

- ✅ 不新增任何后端 API
- ✅ 不新增任何数据库表 / 字段 / 迁移
- ✅ 不新增任何功能模块（无通知中心、无真实进度、无推送）
- ✅ 所有反馈通过**已有 Ant Design 组件**（Spin / Skeleton / Alert / Modal / Drawer / message / notification）实现
- ✅ 所有文案集中管理，便于后续 i18n

---

> **版本**：v1.0 · 2026-07-16
> **作者**：资深产品经理（测试平台方向）
> **范围**：MVP 阶段所有页面反馈；定时 / 通知中心 / i18n 场景不在本期范围
> **配套使用**：`PRD.md` → `Journey.md` → `WorkflowReview.md` → `FirstRunGuide.md` → `EmptyState.md` → `NavigationUX.md` → `QuickAction.md` → `Feedback.md`（本文档：反馈规范）