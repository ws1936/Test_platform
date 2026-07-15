# API 自动化测试平台 · Interaction 交互规范

> 版本：v1.0  
> 适用范围：API 自动化测试平台前端所有用户交互行为  
> 配套：`DesignSystem.md`（视觉）、`Wireframe.md`（线框）、`StateFlow.md`（状态）、`ComponentLibrary.md`（组件）  
> 约束边界：**仅规范交互行为的一致性，不修改任何业务、不新增 API、不改动数据库**

---

## 0. 文档定位

本文档定义平台所有**用户交互行为的一致性规则**，确保用户在任何页面、任何组件上感受到的交互体验是**可预测、符合预期**的。

共定义 **14 类交互模式**：

| # | 交互 | 类型 |
|---:|---|---|
| 1 | Create | 主动创建对象 |
| 2 | Edit | 修改对象 |
| 3 | Delete | 删除对象 |
| 4 | Import | 批量导入 |
| 5 | Run | 执行 |
| 6 | Report | 报告查看 |
| 7 | Drawer | 侧滑浮层 |
| 8 | Dialog | 居中模态 |
| 9 | Toast | 顶部提示 |
| 10 | Notification | 通知中心 |
| 11 | Confirmation | 二次确认 |
| 12 | 快捷键 | 键盘加速 |
| 13 | Hover | 鼠标悬停 |
| 14 | 右键菜单 | 上下文操作 |

---

## ① 交互设计原则

| # | 原则 | 说明 | 反例 |
|---:|---|---|---|
| 1 | **一致性优先**：相同操作在不同页面行为完全一致 | "新建"始终打开同一形态 Drawer | "新建" 在 A 页用 Drawer，在 B 页用 Modal |
| 2 | **结果可逆**：操作前给"取消"，操作后给"撤销" | 删除前 Popconfirm；删除后保留 Toast | 删除直接消失，无任何提示 |
| 3 | **就近反馈**：反馈出现在用户视线焦点附近 | 行内删除在该行附近显示 Toast | 操作后跳到 Dashboard 顶部 Toast |
| 4 | **进度透明**：长任务显示进度或心跳 | Run Drawer 显示 "正在同步执行" + Spin | 点击后无任何变化 |
| 5 | **确认前倾**：危险操作必须二次确认 | 删除 Project 需输入名称 | 一键删除无确认 |
| 6 | **可中断**：长任务允许用户取消（除非同步执行） | Run 可在执行前取消 | Run 一旦发起无法停止 |
| 7 | **键盘可达**：所有交互支持键盘 | Tab / Enter / Esc 全覆盖 | 必须鼠标点击 |
| 8 | **触屏友好**：按钮 / 行内操作 ≥ 32 px | 行内删除按钮高度 32 px | 仅 16 px 的图标按钮 |

---

## ② Create · 创建

### 2.1 触发入口

| 位置 | 形式 |
|---|---|
| PageHeader 右侧 | 主操作按钮 `[+ 新建 XXX]` |
| EmptyView 中心 | 大按钮 `[+ 新建 XXX]` |
| Toolbar | 主操作按钮（列表为空时高亮） |
| 右键菜单 | "新建 XXX" 项 |
| 快捷键 | （未来）`Ctrl/Cmd + N` |

### 2.2 行为规范

| 维度 | 规范 |
|---|---|
| 入口按钮 | Primary 主按钮 + 加号图标 |
| 入口文案 | `+ 新建 {对象名}`，≤ 10 个汉字 |
| 打开形态 | **Drawer**（默认 480~720px）或 **Modal**（单屏简单表单） |
| 默认值 | owner = 当前用户 / enabled = true / sort_order = 末尾 |
| 必填项 | `requiredMark="optional"`（不标 *），错误时红字 |
| 取消行为 | 弹"离开确认"（若表单 dirty） |
| 提交按钮 | "保存"（创建）或 "下一步"（多步） |
| 成功后行为 | Toast + 自动关闭 + 列表更新 + 跳新对象（依场景） |

### 2.3 Drawer / Modal 选择

| 场景 | 选择 |
|---|---|
| 表单字段 ≤ 6 个 | Modal（640px） |
| 表单字段 7~15 个 | Drawer（720px） |
| 表单字段 > 15 个 | Drawer（960px）或独立页 |
| 创建时需要"上下文"提示 | Drawer（保留背景可见） |
| 简单确认（如创建后立刻 Run） | Modal |

### 2.4 各对象创建规则

| 对象 | 创建后行为 |
|---|---|
| Project | 自动跳新 Project 概览 |
| Environment | 留在 Environment 列表，Toast "创建成功" |
| Suite | 留在 Suite 列表，Toast |
| Case | 留在 Suite 详情（含新 Case），Toast |
| Run | 立即跳 Run 报告详情 |
| User | 留在 User 列表，Toast |
| Role | 留在 Role 列表，Toast |

---

## ③ Edit · 编辑

### 3.1 触发入口

| 位置 | 形式 |
|---|---|
| PageHeader 右侧 | "编辑" 文字按钮 |
| Table 操作列 | "编辑" 文字按钮 |
| 详情页表单 | "保存" 主按钮（内联编辑） |
| 右键菜单 | "编辑 XXX" 项 |
| 快捷键 | `Enter`（表单内）或 `E`（行内） |

### 3.2 行为规范

| 维度 | 规范 |
|---|---|
| 入口按钮 | Default / Link 按钮 + 编辑图标 |
| 打开形态 | **Drawer / Modal**（与创建共用同一组件） |
| 初始值 | 从后端加载（Loading → Skeleton → 表单） |
| dirty 检测 | `Form.useForm()[0].isFieldsTouched()` |
| 取消行为 | 弹"离开确认"（若 dirty） |
| 提交按钮 | "保存" |
| 成功后行为 | Toast + 自动关闭 + 详情页数据更新（不跳走） |

### 3.3 与 Create 的差异

| 维度 | Create | Edit |
|---|---|---|
| 标题 | "+ 新建 XXX" | "编辑 XXX" |
| API | POST | PATCH / PUT |
| initialValues | 默认值 | 加载当前对象 |
| 字段是否可改 | 全部可填 | 关键字段只读（如 owner / createdAt） |
| 关闭后行为 | 留在列表 | 留在原详情页 |
| Loading | 表单打开前显示 | 表单打开前显示 |

### 3.4 字段只读规则

| 字段 | 是否可编辑 |
|---|---|
| id | ❌ 只读 |
| owner_id | ❌ 只读 |
| created_at | ❌ 只读 |
| updated_at | ❌ 只读 |
| name | ✅ 可编辑 |
| description | ✅ 可编辑 |
| enabled | ✅ 可编辑 |
| 关联 ID | ❌ 只读（不允许修改归属） |

---

## ④ Delete · 删除

### 4.1 触发入口

| 位置 | 形式 |
|---|---|
| Table 操作列 | "删除" 文字按钮（danger） |
| 详情页 PageHeader | "删除" 文字按钮（danger） |
| 多选批量 | "批量删除" 按钮 |
| 右键菜单 | "删除 XXX" 项 |

### 4.2 三档危险等级

| 等级 | 场景 | 确认方式 |
|---|---|---|
| **普通** | 删除无引用对象 | Popconfirm 二次确认 |
| **危险** | 删除有引用对象 | Modal 二次确认 + 显示引用详情 |
| **高危** | 删除 Project / 自身账号 | Modal + 输入对象名 + 延迟按钮 |

### 4.3 Popconfirm 规范

| 维度 | 规范 |
|---|---|
| 位置 | 紧贴触发按钮下方 |
| 标题 | "确认删除 XXX？" |
| 描述 | 简短说明（不超过 20 字） |
| 按钮 | "取消" + "确认删除"（danger） |
| 点击外部 | 自动关闭（不执行删除） |

### 4.4 Modal 二次确认（危险 / 高危）

| 维度 | 规范 |
|---|---|
| 标题 | "确认删除 XXX？" |
| 描述 | 详细说明（包括影响、引用关系） |
| 高危额外 | 输入对象名才可继续（disabled 直到输入正确） |
| 按钮 | "取消" + "确认删除"（danger / 高危显示红色） |
| 延迟按钮 | 高危删除按钮"确认删除" 3 秒后才可点击（防误触） |

### 4.5 批量删除

| 场景 | 行为 |
|---|---|
| 选中 1 个 | 行内操作 "删除" 按钮 |
| 选中 2+ 个 | Toolbar 出现 "批量删除" 按钮（数字徽标） |
| 点击批量删除 | Modal 列出待删除对象 + "确认删除 N 个" |
| 删除成功 | Toast "成功删除 N 个" + 列表刷新 |
| 部分失败 | Toast "成功 N，失败 M" + 失败明细 |

### 4.6 删除前引用检查

| 场景 | 提示 |
|---|---|
| 无引用 | "删除后无法恢复" |
| 有引用 | "该 XXX 被 N 个 YYY 引用，删除后这些 YYY 将..." |
| 级联删除 | "将同时删除 N 个关联的 XXX" |

### 4.7 删除后行为

| 场景 | 行为 |
|---|---|
| 列表中删除 | 该行消失 + Toast "删除成功" |
| 详情页删除 | 跳列表 + Toast |
| 删除最后一项 | 列表显示 EmptyView |
| 软删除 | 后端标记 deleted_at，列表过滤已删除 |
| 硬删除 | 物理删除，不可恢复 |

---

## ⑤ Import · 导入

### 5.1 触发入口

| 位置 | 形式 |
|---|---|
| Suite 详情 | "导入 OpenAPI" 按钮 |
| Case 列表 Toolbar | "导入 OpenAPI" 按钮 |
| 空态引导 | "导入 OpenAPI" CTA |

### 5.2 流程规范

```text
[步骤 1] 选择来源    → URL / JSON 内容
       ↓
[步骤 2] 过滤        → Tags / 关键词
       ↓
[步骤 3] 冲突策略    → skip（默认） / overwrite
       ↓
[步骤 4] 预览        → 展示 operation 列表 + 冲突标记
       ↓
[步骤 5] 确认导入    → 后端执行 + 返回结果
       ↓
[步骤 6] 查看结果    → 新增 N / 跳过 M / 覆盖 K / 失败 E
       ↓
[步骤 7] 自动跳回    → 目标 Suite 详情
```

### 5.3 步骤条规范

| 步骤数 | 位置 |
|---|---|
| 单步导入 | Modal 单屏 |
| 多步导入（≥ 2 步） | Drawer（720px） |
| 复杂导入（含预览） | Drawer（960px） |

### 5.4 预览页规范

| 元素 | 规范 |
|---|---|
| Operation 列表 | Table 形式（Method / Path / 名称 / 状态） |
| 冲突标记 | 黄色高亮 + 提示文字 |
| 错误标记 | 红色高亮 + 错误信息 |
| 全选 / 反选 | 表头 Checkbox |
| 计数 | "共 N 个 operation，新增 M 个，冲突 K 个" |

### 5.5 导入后结果展示

| 类型 | 提示 |
|---|---|
| 新增 | "导入成功：新增 N，跳过 M，覆盖 K，失败 E" |
| 全失败 | Error Alert + 失败明细 + 重试按钮 |
| 部分失败 | Toast + Alert 列出失败项 |

---

## ⑥ Run · 执行

### 6.1 触发入口

| 位置 | 形式 |
|---|---|
| Run Center 主页 | "Run Now" 主按钮 |
| Workspace Header | "快速执行" 主按钮 |
| Suite 详情 | "执行 Suite" 按钮 |
| Case 编辑器 | "选择环境并执行" 按钮 |
| Case 列表行 | "执行" Link |
| Suite 列表行 | "执行" Link |
| Run 详情 | "再次执行" 按钮 |

### 6.2 三种 Scope

| Scope | 来源 | 预填 |
|---|---|---|
| **Project** | Run Center / Workspace Header | 默认环境 + 全部启用 Case |
| **Suite** | Suite 详情 / Run Center 切换 | 当前 Suite + 默认环境 |
| **Case** | Case 编辑器 / Case 列表行 | 当前 Case + 默认环境 |

### 6.3 执行流程

```text
[步骤 1] 打开 RunExecutionDrawer
       ↓
[步骤 2] 用户预填（环境 / Run Name）
       ↓
[步骤 3] 点击 "Run Now"
       ↓
[步骤 4] Drawer 进入 Submitting + Running 态
       ↓
[步骤 5] 同步执行（后端处理）
       ↓
[步骤 6] 自动跳 Run 报告详情
```

### 6.4 Run Execution Drawer 规范

| 元素 | 规范 |
|---|---|
| 顶部 Tag | "范围:XXX" + "环境:XXX" + "启用 Case: N" |
| Environment 必填 | 默认选中 Project 默认环境 |
| Run Name 可选 | 留空由后端自动生成 |
| Variables 只读 | 显示当前环境的 Variables |
| 未设默认环境 | 顶部 Alert "尚未设置默认环境" + 跳转按钮 |
| 主按钮 | "Run Now"（执行中变 "正在同步执行…"） |
| 关闭按钮 | Submitting / Running 期间禁用 |

### 6.5 Run 进行中行为

| 状态 | 行为 |
|---|---|
| Run 列表 | Run 状态显示 "执行中" + 耗时累加 |
| Run 详情 | 页面显示 "执行中" Spin + "请稍候" |
| Drawer | 不可关闭 + "正在同步执行…" |
| 路由切换 | 弹 Popconfirm "Run 正在执行，确定离开？" |

### 6.6 Run 完成后

| 结果 | 行为 |
|---|---|
| 成功 | Toast "执行完成" + 自动跳 Run 报告详情 |
| 失败 | Alert "执行失败：[后端 message]" + 重试按钮 |
| 超时 | 跳错误页 "Run 超时，请在报告中查看结果" |

---

## ⑦ Report · 报告

### 7.1 触发入口

| 位置 | 形式 |
|---|---|
| Run 列表 | Run 名称点击 |
| Recent Runs | Run 卡片点击 |
| Workspace Header | "最近执行" 按钮 |
| Toast 跳转 | Run 完成后自动跳 |

### 7.2 Run 报告详情

| Tab | 内容 |
|---|---|
| 概览 | 6 格 KPI + 元信息 |
| 失败原因 | 失败项展开 + 断言对比 + 跳 Result |
| 全部结果 | Result 列表（Table） |
| 元信息 | Run ID / 范围 / 环境 / 触发人 / 耗时 / 快照 |

### 7.3 Result 详情

| Tab | 内容 |
|---|---|
| 请求 | Method / URL / Headers / Body |
| 响应 | Status / Headers / Body（截断提示） |
| 断言 | 期望值 vs 实际值对比 |
| 错误 | Error Code / Error Message |
| 概览 | Case 快照 / 时间 / Case 定义 |

### 7.4 报告交互

| 操作 | 入口 | 行为 |
|---|---|---|
| 查看请求快照 | Result 详情 "请求" Tab | 等宽字体 + 折叠 |
| 查看响应快照 | Result 详情 "响应" Tab | 等宽字体 + 折叠 |
| 查看断言对比 | Result 详情 "断言" Tab | 期望值/实际值并列 |
| 跳 Case 定义 | Result 详情 PageHeader | 跳 Case 编辑器（带 `?from=result`） |
| 再次执行 | Run / Result 详情 | 打开 RunExecutionDrawer 预填原 scope / env |

---

## ⑧ Drawer · 抽屉

### 8.1 三档宽度

| 宽度 | 场景 | 示例 |
|---:|---|---|
| **480** | 简单表单（≤ 6 字段） | 新建 Suite、修改密码 |
| **720** | 中等表单 / 执行配置 | 新建 / 编辑 Environment、RunExecutionDrawer |
| **960** | 复杂表单 / 含预览 | OpenAPI 导入、详细设置 |

### 8.2 通用规范

| 元素 | 规范 |
|---|---|
| 位置 | 右侧 100% 高度滑入 |
| Header | 图标 + 标题 + 关闭 [×] |
| Header 高度 | 56 px |
| Body padding | 24 px |
| Footer 高度 | 64 px |
| Footer 位置 | 右下角（Cancel + 主操作） |
| Footer 背景 | `--bg-surface` + 上边线 |
| Body 滚动 | 自身 `overflow: auto`（非文档滚动） |

### 8.3 关闭行为

| 时机 | 行为 |
|---|---|
| 正常关闭 | `onClose` 触发，destroyOnClose 清空状态 |
| 表单 dirty | Popconfirm "有未保存更改，确定关闭？" |
| Submitting | **禁用关闭**（按钮禁用 + mask 不响应） |
| Esc 键 | 正常关闭（除非 Submitting） |
| 点击 mask | 正常关闭（`maskClosable=true`；表单 dirty 需确认） |

### 8.4 Drawer 标题规范

| 模式 | 标题 |
|---|---|
| 创建 | "+ 新建 {对象名}" |
| 编辑 | "编辑 {对象名}" |
| 查看 | "{对象名}（只读）" |
| 执行 | "⚡ 执行 {scope}" |
| 导入 | "导入 OpenAPI" |

### 8.5 Drawer 嵌套限制

- Drawer 内**不嵌** Drawer
- Drawer 内**不嵌** Modal
- 如需二级确认，用 Popconfirm

---

## ⑨ Dialog · 模态框

### 9.1 四档宽度

| 宽度 | 场景 | 示例 |
|---:|---|---|
| **416** | 二次确认 | 删除确认、离开确认 |
| **520** | 信息提示 | 重要警告 |
| **640** | 单屏表单 | 新建简单对象 |
| **880** | 大表单 / 含预览 | OpenAPI 预览 |

### 9.2 通用规范

| 元素 | 规范 |
|---|---|
| 位置 | 屏幕居中（`centered=true`） |
| 圆角 | `--radius-lg` (12px) |
| 阴影 | `--shadow-lg` |
| Header 高度 | 56 px |
| Header 字号 | H4 (17 / 600) |
| Body padding | 24 px |
| Footer 高度 | 64 px |
| Footer 位置 | 右下角 |
| 遮罩 | 半透明 + 模糊 |

### 9.3 关闭行为

| 时机 | 行为 |
|---|---|
| 正常关闭 | `onCancel` 触发 |
| Esc 键 | 关闭 |
| 点击 mask | 默认关闭；危险操作可禁用（`maskClosable=false`） |
| Submitting | **禁用关闭** |
| Cancel 按钮 | 默认位置 Footer 左 |

### 9.4 Dialog 标题规范

| 模式 | 标题 |
|---|---|
| 确认 | "确认 XXX？" |
| 表单 | "新建 XXX" / "编辑 XXX" |
| 信息 | 直接陈述（如 "导入完成"） |
| 警告 | "⚠ XXX" |

---

## ⑩ Toast · 顶部提示

### 10.1 触发场景

| 操作 | Toast 类型 | 时长 |
|---|---|---|
| 创建成功 | `success` | 3s |
| 更新成功 | `success` | 3s |
| 删除成功 | `success` | 3s |
| 执行完成 | `success` | 3s |
| 复制成功 | `success` | 2s |
| 一般信息 | `info` | 3s |
| 警告 | `warning` | 4s |
| 错误 | `error` | 5s |
| 加载中 | `loading` | 不自动消失 |
| Token 失效 | `warning` | 3s |

### 10.2 文案规范

| 规则 | 示例 |
|---|---|
| 主动语态 | "保存成功" 而非 "已为您保存" |
| 简明扼要 | ≤ 20 个汉字 |
| 后端 message 优先 | "[后端 msg]" 而非固定文案 |
| 不用 Emoji | "保存成功" 而非 "✅ 保存成功" |
| 不用第一人称 | "已保存" 而非 "我们已保存" |

### 10.3 位置与样式

| 元素 | 规范 |
|---|---|
| 位置 | 屏幕顶部（top: 24px） |
| 宽度 | 固定 384 px |
| 层级 | Z-Index 1100（永远在最上） |
| 堆叠 | 最多 3 个，超出排队 |
| 背景 | 浅色（success=绿、error=红、warning=黄、info=蓝） |
| 图标 | Filled 图标 + 左侧 |
| 关闭按钮 | 右侧 [×] |
| 动画 | 上滑进入 + 自动消失 |

### 10.4 多 Toast 处理

| 场景 | 处理 |
|---|---|
| 同时多个成功 | 排队显示，第 1 个消失后第 2 个立即出现 |
| 错误 + 成功混合 | 错误优先（顶部） |
| Loading + 后续 | Loading 自动转为 success / error |
| 重复 Toast | 自动合并（同 key） |

### 10.5 平台标准 Toast 文案

| 场景 | 文案 |
|---|---|
| 创建 Project | "Project 创建成功" |
| 创建 Environment | "环境创建成功" |
| 创建 Suite | "Suite 创建成功" |
| 创建 Case | "Case 创建成功" |
| 创建 User | "用户创建成功" |
| 创建 Role | "角色创建成功" |
| 编辑 | "保存成功" |
| 删除 | "删除成功" |
| 批量删除 | "成功删除 N 个" |
| 设置默认 | "已设为默认环境" |
| 复制 | "已复制到剪贴板" |
| 启用 / 禁用 | "已启用" / "已禁用" |
| 导入 | "导入成功：新增 N，跳过 M，覆盖 K" |
| 执行 | "执行完成，正在打开报告" |
| 修改密码 | "密码修改成功" |
| 退出 | "已退出登录" |

---

## ⑪ Notification · 通知中心

> 当前未实现；预留设计。

### 11.1 与 Toast 的区别

| 维度 | Toast | Notification |
|---|---|---|
| 位置 | 屏幕顶部 | 右上角抽屉 |
| 时长 | 短（2~5 秒） | 长（直到关闭） |
| 重要性 | 操作反馈 | 系统消息 |
| 来源 | 当前页操作 | 系统 / 后端推送 |
| 数量 | 1~3 个 | 不限 |

### 11.2 未来设计（参考）

| 元素 | 规范 |
|---|---|
| 触发器 | 顶栏 🔔 图标 + 数字徽标 |
| 列表 | 时间倒序，未读高亮 |
| 分类 | 通知 / 待办 / 公告 |
| 操作 | "全部已读" / "查看" / "忽略" |
| 持久化 | 后端持久化 |

### 11.3 当前替代

- 操作反馈：Toast
- 重要提示：Alert（页面内）
- 长效提醒：Workspace Soft Alert

---

## ⑫ Confirmation · 二次确认

### 12.1 三档确认方式

| 档 | 组件 | 场景 |
|---|---|---|
| 轻量 | **Popconfirm** | 单字段确认（删除、启用） |
| 中等 | **Modal** | 多字段说明（删除有引用、批量） |
| 高危 | **Modal + 输入确认** | 删除 Project、修改密码 |

### 12.2 Popconfirm 规范

| 元素 | 规范 |
|---|---|
| 触发 | 危险按钮（链接或文字按钮） |
| 位置 | 触发按钮下方（默认 `placement="topRight"`） |
| 标题 | "确认 XXX？" |
| 描述 | 简短（≤ 30 汉字） |
| 按钮 | "取消" + "确认"（危险时 red） |
| 点击外部 | 自动关闭 |
| Esc | 关闭 |
| Loading | 提交期间禁用 Cancel |

### 12.3 Modal 二次确认（中等危险）

| 元素 | 规范 |
|---|---|
| 标题 | "确认删除 XXX？" |
| 描述 | 详细影响说明 |
| 宽度 | 480 px |
| 按钮 | "取消" + "确认删除"（danger） |
| Loading | 提交期间禁用 Cancel |

### 12.4 高危 Modal

| 元素 | 规范 |
|---|---|
| 标题 | "⚠ 确认删除 XXX？" |
| 描述 | 级联影响、引用关系 |
| 宽度 | 520 px |
| 输入框 | "请输入 XXX 名称以确认：" |
| 按钮 | "取消" + "确认删除"（disabled 直到输入正确） |
| 延迟按钮 | "确认删除" 按钮 3 秒后才可点击 |
| 加载 | 提交期间所有操作禁用 |

### 12.5 离开确认（表单 dirty）

| 触发 | 行为 |
|---|---|
| Drawer Cancel 按钮 | Popconfirm "有未保存更改，确定关闭？" |
| Drawer [×] | 同上 |
| Drawer Esc | 同上 |
| Drawer mask 点击 | 同上 |
| 路由切换 | Popconfirm "有未保存更改，确定离开？" |
| 浏览器关闭 | `beforeunload` 拦截 |

---

## ⑬ 快捷键 · Keyboard Shortcuts

### 13.1 全局快捷键

| 快捷键 | 行为 | 备注 |
|---|---|---|
| `Ctrl/Cmd + K` | 全局搜索 | （未来） |
| `Ctrl/Cmd + S` | 保存当前表单 | 仅表单页生效 |
| `Esc` | 关闭顶层 Modal / Drawer / Dropdown | 不在 Submitting 时 |
| `?` 或 `Shift + /` | 显示快捷键面板 | （未来） |

### 13.2 列表页快捷键

| 快捷键 | 行为 |
|---|---|
| `/` | 聚焦搜索框 |
| `N` | 新建对象（打开 Drawer / Modal） |
| `R` | 刷新列表 |
| `↑` `↓` | 上下选择行 |
| `Enter` | 进入选中行详情 |
| `Delete` | 删除选中行（需 Popconfirm） |

### 13.3 详情页快捷键

| 快捷键 | 行为 |
|---|---|
| `Esc` | 返回上级 |
| `E` | 编辑当前对象 |
| `Delete` | 删除当前对象（需 Popconfirm） |
| `Tab` | 切换 Tab（如有） |

### 13.4 表单内快捷键

| 快捷键 | 行为 |
|---|---|
| `Tab` | 下一字段 |
| `Shift + Tab` | 上一字段 |
| `Enter` | 提交表单（在字段上） |
| `Esc` | 关闭 Drawer / Modal |

### 13.5 实施规则

| 规则 | 说明 |
|---|---|
| 快捷键不与浏览器冲突 | `Ctrl+S` 浏览器默认保存网页，需 preventDefault |
| 在 input / textarea 中禁用非 Enter / Tab 的快捷键 | 避免干扰输入 |
| 快捷键全局显示 | 在 Drawer / Modal 内不响应全局快捷键 |
| 提供快捷键提示 | Hover 按钮时 Tooltip 显示（"保存 (Ctrl+S)"） |

---

## ⑭ Hover · 鼠标悬停

### 14.1 Hover 反馈

| 元素 | Hover 行为 |
|---|---|
| 主操作按钮 | 颜色加深（`--brand-primary-hover`）+ 阴影加重 |
| Default 按钮 | 背景变 `--bg-muted` |
| Link 按钮 | 文字下划线 |
| Card（可点击） | 阴影加重（`--shadow-xl`）+ translateY(-2px) |
| 表格行 | 背景变 `--bg-muted` 50% |
| 菜单项 | 背景变 `--bg-muted` + 左侧 3px 主色高亮 |
| Tag | 不变化（已是最小可点击单位） |

### 14.2 Tooltip 触发

| 场景 | Tooltip 文案 |
|---|---|
| 按钮禁用 | 禁用原因（如 "请先选择环境"） |
| 状态 Tag | 详细状态说明（如 "Run 已被取消"） |
| 图标按钮 | 功能说明（如 "复制 Base URL"） |
| 截断文字 | 完整内容 |
| 加载中 | "加载中…" |
| 错误状态 | "请稍后重试" |

### 14.3 Tooltip 规范

| 元素 | 规范 |
|---|---|
| 出现时机 | Hover 500ms 后 |
| 位置 | 默认 top（自动避让） |
| 背景 | `--text-primary` |
| 文字 | `--text-inverse` |
| 字号 | Caption Small (12 / 18) |
| 圆角 | `--radius-sm` (4px) |
| 箭头 | 默认显示 |
| 消失时机 | 鼠标离开 100ms 后 |

### 14.4 Hover 禁用场景

| 场景 | 行为 |
|---|---|
| 禁用按钮 | 不显示 Tooltip（或显示禁用原因） |
| Submitting 期间 | 不显示 Tooltip（避免干扰 Loading） |
| Drawer / Modal 打开时 | 底层 hover 暂停 |

---

## ⑮ 右键菜单 · Context Menu

### 15.1 触发条件

| 场景 | 是否启用 |
|---|---|
| 表格行 | ✅ 启用 |
| 列表项 | ✅ 启用 |
| 卡片 | ✅ 启用 |
| 文件 / 资源树 | ✅ 启用 |
| 普通区域 | ❌ 不启用 |
| 输入框 / TextArea | ❌ 不启用（使用原生菜单） |

### 15.2 菜单项规范

| 类型 | 样式 | 示例 |
|---|---|---|
| 主操作 | 默认色 + 图标 | "编辑" |
| 危险操作 | 红色 + 图标 | "删除" |
| 分隔线 | 灰色横线 | — |
| 不可用项 | 灰色 + 不可点击 | "禁用" |
| 子菜单 | 右侧箭头 ▶ | "移动到 >" |
| 快捷键提示 | 右侧灰色文字 | "编辑 (E)" |

### 15.3 标准菜单项（按对象）

#### Project

| 菜单项 | 快捷键 |
|---|---|
| 进入 Workspace | Enter |
| 编辑 | E |
| 复制 ID | Cmd+C |
| 设为常用 | （未来） |
| — | — |
| 删除 | Delete |

#### Environment

| 菜单项 | 快捷键 |
|---|---|
| 复制 Base URL | Cmd+C |
| 编辑 | E |
| 设为默认 | D |
| — | — |
| 删除 | Delete |

#### Suite / Case

| 菜单项 | 快捷键 |
|---|---|
| 查看详情 | Enter |
| 编辑 | E |
| 执行 | R |
| 复制 ID | Cmd+C |
| — | — |
| 删除 | Delete |

#### Run / Result

| 菜单项 | 快捷键 |
|---|---|
| 查看详情 | Enter |
| 再次执行 | R |
| 复制 Run ID | Cmd+C |

### 15.4 菜单行为

| 维度 | 规范 |
|---|---|
| 位置 | 鼠标右键位置 + 视口边缘避让 |
| 宽度 | 180~220 px |
| 关闭时机 | 点击菜单项 / 点击外部 / Esc |
| 危险项 | 红色 + Popconfirm / Modal 二次确认 |
| 图标 | 与按钮保持一致 |
| 快捷键 | 右侧灰色提示 |
| 嵌套 | 不超过 2 级 |

---

## ⑯ 通用交互守则

### 16.1 主操作 vs 次操作

| 规则 | 说明 |
|---|---|
| 一个区块 1 个 Primary | 避免多个主按钮抢焦点 |
| 主操作放右侧 | PageHeader / Drawer / Modal Footer 都遵循 |
| 次操作默认样式 | 不抢视觉 |
| 危险操作低优先 | 不与主操作相邻 |

### 16.2 Loading vs Disabled

| 状态 | 视觉 |
|---|---|
| Loading | 按钮内显示旋转 icon + 文字变为 "X 中…" |
| Disabled | 灰色 + cursor: not-allowed |
| Loading + Disabled | Loading 优先（仍禁用点击） |

### 16.3 反馈时机

| 操作类型 | 反馈时机 |
|---|---|
| 纯前端操作（如复制） | 即时（< 100ms） |
| 简单 API（如 GET） | < 500ms 不显示 Loading |
| 复杂 API（如 POST） | 立即显示 Loading |
| 长任务（如 Run） | 显示进度文案 |
| 失败 | 立即 Toast / Alert |
| 成功 | 立即 Toast + 自动行为 |

### 16.4 撤销与重做

| 操作 | 是否可撤销 | 撤销方式 |
|---|---|---|
| 删除 | ❌ 不可撤销（危险） | — |
| 编辑 | ❌ 不可撤销（点击 Cancel 即放弃） | — |
| 启用 / 禁用 | ✅ 可切换 | 再次点击 |
| 设置默认 | ✅ 可切换 | 选其它设为默认 |
| Run | ❌ 不可撤销（异步） | — |

> 平台当前不实现 Undo Stack；如未来需要，引入 redux-undo 等。

### 16.5 表单提交通用规则

| 规则 | 说明 |
|---|---|
| Enter 提交 | 表单内任意字段按 Enter 提交（除非在 TextArea） |
| 提交期间禁用 | 所有字段 + 按钮 + Cancel |
| 失败恢复 | 表单恢复可编辑 + 字段错误提示 |
| 成功关闭 | Drawer / Modal 自动关闭 + 列表更新 |
| 防重复提交 | 提交期间按钮 disabled，防止双击 |

---

## ⑰ 触屏 / 移动端适配

### 17.1 点击目标尺寸

| 元素 | 最小尺寸 |
|---|---|
| 主操作按钮 | 88 × 32 px（移动端可放大到 40 px） |
| 次操作按钮 | 64 × 32 px |
| 行内操作 Link | 80 × 32 px |
| 图标按钮 | 32 × 32 px |
| Tag | 48 × 24 px（移动端 56 × 28） |

### 17.2 Hover 替代

| 桌面端 | 移动端 |
|---|---|
| Hover 显示 Tooltip | 长按 500ms 显示 |
| Hover 显示下拉 | 点击展开 |
| Hover 显示删除按钮 | 行右侧固定显示 |

### 17.3 触屏手势

| 手势 | 行为 |
|---|---|
| 左滑列表项 | 显示快捷操作（删除 / 归档） |
| 下拉刷新 | 刷新列表 |
| 双指缩放 | （不支持，保留桌面布局） |

---

## ⑱ 无障碍（a11y）规范

### 18.1 键盘可达

| 元素 | 行为 |
|---|---|
| 按钮 | Enter / Space 触发 |
| 链接 | Enter 触发 |
| 表单字段 | Tab 切换 |
| Drawer / Modal | Esc 关闭 |
| Dropdown | ↑↓ 选择，Enter 确认 |
| DatePicker | 完整键盘支持（AntD 内置） |

### 18.2 焦点管理

| 场景 | 焦点 |
|---|---|
| Modal 打开 | 焦点落到主操作按钮 |
| Modal 关闭 | 焦点回到触发按钮 |
| Drawer 打开 | 焦点落到第一个字段 |
| Drawer 关闭 | 焦点回到触发按钮 |
| Submitting 期间 | 焦点不切换 |
| 错误提示 | 焦点跳到第一个错误字段 |

### 18.3 ARIA 标签

| 元素 | ARIA |
|---|---|
| 按钮（仅图标） | `aria-label="新建项目"` |
| Loading 区块 | `role="status" aria-live="polite"` |
| EmptyView | `role="region" aria-label="空状态"` |
| 危险按钮 | `aria-label="危险操作：删除"` |
| 必填字段 | `aria-required="true"` |
| 错误字段 | `aria-invalid="true" aria-describedby="error-id"` |

---

## ⑲ 交互一致性检查表

### 19.1 新增交互前

- [ ] 是否复用已有的 Component（不新建）
- [ ] 是否符合 Drawer / Modal 选择矩阵
- [ ] 触发入口是否覆盖 PageHeader / Toolbar / Empty / 右键菜单
- [ ] 主操作按钮是否 ≤ 1 个
- [ ] 是否提供键盘快捷键
- [ ] 是否提供 loading / disabled / success 三态

### 19.2 新增表单前

- [ ] 是否使用 Form.Item + 校验
- [ ] 必填项是否用 `requiredMark="optional"`（不标 *）
- [ ] 提交按钮是否显示 loading
- [ ] 失败是否显示 Toast / Alert
- [ ] 成功是否自动关闭 + 列表更新
- [ ] dirty 是否触发离开确认

### 19.3 新增删除前

- [ ] 是否选择 Popconfirm / Modal / 高危 Modal
- [ ] 是否显示引用关系
- [ ] 高危是否要求输入对象名
- [ ] 是否使用 danger 样式
- [ ] 是否 Toast 反馈

### 19.4 新增 Toast 前

- [ ] 文案是否符合规范（≤ 20 汉字，主动语态）
- [ ] 类型是否正确（success / info / warning / error）
- [ ] 时长是否合理（2~5 秒）
- [ ] 是否有 close 按钮
- [ ] 是否与现有 Toast 合并

---

## ⑳ 实施优先级

| # | 任务 | 优先级 | 价值 |
|---:|---|---|---|
| 1 | Toast / Confirmation 统一（文案、时长、类型） | P0 | 高 |
| 2 | Create / Edit Drawer 复用 | P0 | 高 |
| 3 | Delete 三档确认（Popconfirm / Modal / 高危） | P0 | 高 |
| 4 | Run Drawer 三种 Scope 预填 | P0 | 高 |
| 5 | 全局快捷键 Esc 关闭 Drawer | P1 | 中 |
| 6 | 表格右键菜单（基础版） | P1 | 中 |
| 7 | 离开确认（表单 dirty） | P1 | 中 |
| 8 | 触屏适配（点击目标尺寸） | P2 | 中 |
| 9 | 全局快捷键 Ctrl+K（搜索） | P3 | 低（未来） |
| 10 | Notification 通知中心 | P3 | 低（未来） |

---

## 附录 A · 交互事件映射

| 用户意图 | 触发动作 | 响应 |
|---|---|---|
| 创建对象 | 点击 [+ 新建] | 打开 Drawer / Modal |
| 修改对象 | 点击 [编辑] | 打开 Drawer / Modal（带 initialValues） |
| 查看对象 | 点击名称 / 链接 | 跳详情页 |
| 删除对象 | 点击 [删除] | Popconfirm / Modal |
| 执行 | 点击 [执行] | 打开 Run Drawer |
| 批量操作 | 选中多行 + 点击操作 | Modal 确认 |
| 导入 | 点击 [导入] | Drawer（多步） |
| 搜索 | 输入关键字 | 防抖 300ms 后查询 |
| 筛选 | 切换 Filter | 即时查询 |
| 排序 | 点击表头 | 切换 asc / desc |
| 翻页 | 点击页码 | 跳页 |
| 切换 Tab | 点击 Tab | 切换内容 |
| 关闭 | 点 [×] / Esc / 取消 | 关闭浮层 |
| 刷新 | 点击 [刷新] | 重新加载 |
| 全屏切换 | F11 | （浏览器原生） |

---

## 附录 B · 组件 vs 交互映射

| 交互 | 组件 |
|---|---|
| Create / Edit | `XxxFormDrawer` / `XxxFormModal` |
| Delete | `ConfirmDialog` / AntD Popconfirm |
| Import | `XxxImportDrawer`（多步） |
| Run | `RunExecutionDrawer` |
| Drawer | AntD `Drawer` + 统一封装 |
| Dialog | AntD `Modal` + 统一封装 |
| Toast | AntD `App.useApp().message` |
| Notification | AntD `notification`（未来） |
| 快捷键 | 自定义 `useKeyboard` Hook |
| Hover | AntD `Tooltip` + CSS `:hover` |
| 右键菜单 | AntD `Dropdown` + `trigger="contextMenu"` |

---

## 附录 C · 文案风格指南

### C.1 语气

| ✅ 推荐 | ❌ 不推荐 |
|---|---|
| "保存成功" | "操作已为您完成" |
| "删除失败" | "未能完成您的请求" |
| "环境创建成功" | "您已成功创建了一个新的环境配置" |
| "确认删除？" | "您是否要删除此项目？" |

### C.2 大小写

- 中文：标题用正常书写，**不**加句号
- 英文：标题用 Sentence case（仅首字母大写）
- 按钮：动词开头，"保存"而非"保存此对象"

### C.3 错误描述

| 场景 | 格式 |
|---|---|
| 字段错误 | "请输入 XXX" |
| 业务错误 | 后端 message |
| 系统错误 | "服务异常，请稍后重试" |
| 网络错误 | "网络连接失败，请检查网络" |

---

## 附录 D · 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-15 | 初版：14 类交互模式（Create/Edit/Delete/Import/Run/Report/Drawer/Dialog/Toast/Notification/Confirmation/快捷键/Hover/右键菜单） |

---

**约束再确认**

- ❌ 不修改任何业务逻辑
- ❌ 不新增任何 API
- ❌ 不修改数据库
- ✅ 仅规范所有交互行为的一致性，作为前端协作的交互字典