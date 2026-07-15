# API 自动化测试平台 · UI Review

> 版本：v1.0  
> 角色：资深 UX Designer  
> 范围：全平台前端 UI 全量审查  
> 配套：`UX_REVIEW.md`（首轮发现）、`DesignSystem.md` / `Layout.md` / `NavigationUX.md` / `ComponentLibrary.md` / `Wireframe.md` / `StateFlow.md` / `Interaction.md`（已落地的设计规范）  
> 评估方式：按 12 个维度系统性评估，按 High / Medium / Low 三档分类

---

## 0. 评估方法论

### 0.1 评分原则

| 等级 | 标准 |
|---|---|
| **High** | 阻塞主流程、导致用户放弃、企业级产品**不能接受** |
| **Medium** | 影响效率或清晰度，但流程仍能完成 |
| **Low** | 细节优化，提升专业感 |

### 0.2 评估维度

| # | 维度 | 评估内容 |
|---:|---|---|
| 1 | 一致性 | 视觉 / 行为 / 命名 / 文案一致性 |
| 2 | 学习成本 | 新用户能否快速上手 |
| 3 | 操作效率 | 完成主要任务需要多少点击 |
| 4 | 视觉层级 | 重要信息是否突出，次要信息是否弱化 |
| 5 | 导航 | 用户能否找到入口、回到上级、跨模块跳转 |
| 6 | 空页面 | 首次访问 / 搜索无结果 / 数据被删的引导 |
| 7 | 错误提示 | 错误是否清晰、有原因、有解决方案 |
| 8 | Loading | 加载反馈是否及时、避免闪烁 |
| 9 | 组件重复 | 是否有可复用组件被复制粘贴 |
| 10 | 按钮风格 | 主次操作是否清晰、危险操作是否警示 |
| 11 | 表单 | 校验 / dirty / 提交 / 反馈是否完整 |
| 12 | 可访问性 | 键盘 / 屏幕阅读器 / 焦点管理 |

---

## ① 总览

### 1.1 问题统计

| 等级 | 数量 | 占比 |
|---|---:|---:|
| High | **8** | 22% |
| Medium | **18** | 50% |
| Low | **10** | 36 |
| **总计** | **36** | 100% |

### 1.2 各维度问题分布

| 维度 | High | Medium | Low | 总计 |
|---|---:|---:|---:|---:|
| 一致性 | 2 | 3 | 1 | 6 |
| 学习成本 | 1 | 2 | 0 | 3 |
| 操作效率 | 2 | 2 | 1 | 5 |
| 视觉层级 | 0 | 2 | 2 | 4 |
| 导航 | 2 | 2 | 0 | 4 |
| 空页面 | 0 | 1 | 1 | 2 |
| 错误提示 | 1 | 1 | 1 | 3 |
| Loading | 0 | 1 | 1 | 2 |
| 组件重复 | 0 | 2 | 0 | 2 |
| 按钮风格 | 0 | 1 | 1 | 2 |
| 表单 | 0 | 1 | 1 | 2 |
| 可访问性 | 0 | 0 | 1 | 1 |

### 1.3 整体评分

| 维度 | 评分（5 分制） | 说明 |
|---|:---:|---|
| 视觉设计 | ⭐⭐⭐⭐ | 品牌色 / 排版 / 阴影专业，但部分页面信息密度过高 |
| 一致性 | ⭐⭐⭐ | 整体一致，但执行入口、报告区块仍有重复 |
| 易用性 | ⭐⭐⭐ | 大部分流程顺畅，但 Run Center / Report 双入口是反模式 |
| 导航 | ⭐⭐⭐ | 三级面包屑清晰，但 Project 切换有上下文丢失 |
| 表单 | ⭐⭐⭐⭐ | 校验完整，dirty 检测到位 |
| 错误处理 | ⭐⭐⭐ | 大部分有重试，少数缺错误原因 |
| 可访问性 | ⭐⭐ | 缺少键盘快捷键与 ARIA 标签 |
| **综合** | **⭐⭐⭐ (3.4)** | **企业级产品的"够用"，但未达"优秀"** |

---

## ② High 优先级问题（8 项）

> 必须修复；阻塞主流程或企业级不可接受。

---

### H1 · 执行入口重复（H2 in UX_REVIEW）

**维度**：一致性 + 操作效率

**问题描述**：

平台有 **4 处** 入口可触发 Run Execution Drawer：

| 入口 | 位置 | 触发对象 |
|---|---|---|
| ① Workspace Header "快速执行" | Project 内任意页 | scope=project |
| ② Run Center "Run Now" | `/run` 页面 | scope=project/suite/case |
| ③ Suite 详情 "执行 Suite" | Suite 详情页 | scope=suite |
| ④ Case 编辑器 / 列表 "执行 Case" | Case 相关页 | scope=case |

**影响**：

- 用户不知道哪个入口是"规范的"
- 不同入口的预填行为不一致（如 ② 的 scope 切换，③ ④ 已固定）
- 同一 Drawer 4 处入口，UX 复杂

**根因**：缺少"单一主入口"原则的约束

**修复建议**：

1. **保留 1 个主入口 + 3 个上下文入口**：
   - 主入口：Workspace Header "快速执行"（默认 scope=project）
   - 上下文入口：Suite 详情 "执行 Suite"、Case 列表 / 编辑器 "执行 Case"、Run Center 主页
2. 入口命名统一为 "执行 XXX"，加图标 ⚡
3. 文档化"Run Center = 高级配置入口"（含批量变量、批量环境），与快速执行区分

**预期收益**：用户点击次数不变，但入口意图清晰

---

### H2 · Project 切换后上下文丢失（H1 in UX_REVIEW）

**维度**：导航

**问题描述**：

`/projects/:id/workspace/report/:runId` → 切换到 Project B → URL 不变 → 后端 404。

**用户场景**：

```text
1. 在 Project A 打开 Run #0715-001（URL 含 runId）
2. 想看 Project B 的 Run
3. 在 Sider 切换到 Project B
4. 页面卡在 404（或显示 Project A 的数据）
5. 用户迷失："我切了吗？怎么还在 Project A？"
```

**影响**：用户高频迷失点；企业级产品典型反模式

**根因**：`getProjectSwitchTarget` 已在 AppShell 中实现，但只在 L2 模块页生效；详情页（URL 含对象 ID）未触发

**修复建议**：

1. 实现 NavigationUX §8.2 的 A/B/C 三层策略：
   - **A 静默切换**：L2 列表页 → 同名模块
   - **B 详情上下文切换**：L3 详情页 → 查询新 Project 是否有同名对象
   - **C 强制回概览**：Run/Result/OpenAPI 导入（不跨 Project 共享）
2. 切换前若表单 dirty / Run 进行中，弹 Popconfirm

**优先级**：P0（**这是 UX H1 的根因**）

---

### H3 · Report 列表与 Overview 重复（H3 in UX_REVIEW）

**维度**：一致性 + 操作效率

**问题描述**：

| 页面 | KPI 卡片 | Recent Runs（5 条） | Run 历史（完整列表） |
|---|:---:|:---:|:---:|
| Workspace Overview | ✅ | ✅ | ❌ |
| Report 列表 | ✅ | ✅ | ✅ |
| Dashboard | ✅（部分） | ✅ | ❌ |

**影响**：

- KPI 在 Overview 和 Report 重复展示
- Recent Runs 在 3 个页面都有
- 用户不知道"看 Run 该去哪个页面"

**根因**：每个页面都试图"独立完整"，导致职责重叠

**修复建议**：

1. **Workspace Overview** 只显示：Project 摘要 + 配置就绪度 + 最近 5 条 Run（轻量）
2. **Report 列表** 作为 Run 历史的**唯一入口**：包含 KPI + Recent Runs + 完整列表 + 筛选
3. **Dashboard** 不展示 Run 相关内容（Project 维度）

**预期收益**：用户知道"我要看 Run → Report 列表"；KPI 不再重复

---

### H4 · Run Detail 与 Result Detail 数据重复（M7 in UX_REVIEW）

**维度**：一致性 + 操作效率

**问题描述**：

- Run Detail 的 "全部结果" Tab 与 Result Detail 的 "请求 / 响应" Tab 是同一份数据
- Run Detail 的 "概览" Tab KPI 与 Report 列表 KPI 重复

**影响**：用户反复查看相同数据；认知负担

**修复建议**：

1. Run Detail 默认 Tab 改为 **"失败原因"**（而非 "概览"）
2. Run Detail 的 "全部结果" Tab 精简为：状态 + Method + Path + 耗时，点击进 Result Detail
3. Run Detail 的 "概览" Tab 移除 KPI（KPI 已在 Report 列表），仅保留元信息

---

### H5 · Case 编辑器返回丢失搜索状态（M6 in UX_REVIEW）

**维度**：导航 + 操作效率

**问题描述**：

Case 列表（已筛选 `?search=test&method=GET`）→ 点击 "编辑" → Case 编辑器 → 返回 → 列表显示**未筛选的全列表**

**根因**：返回路径使用 `history.back()` 或硬编码 `/cases`，未携带 URL Query

**修复建议**：

1. 进入 Case 编辑器时记录来源 URL 到 `?returnTo=/cases?search=test&method=GET`
2. 保存 / 取消时跳回 `returnTo`
3. 推广到所有"列表 → 详情 → 返回"场景（Suite / Environment / Run / Result）

---

### H6 · OpenAPI 导入错误提示不友好（M5 in UX_REVIEW）

**维度**：错误提示

**问题描述**：

```text
预览功能不可用
```

这是后端 message 直传，对企业用户不友好，无法判断是系统故障还是用户操作问题。

**修复建议**：

| 后端 message | 用户文案 |
|---|---|
| `preview_id expired` | "预览已过期（超过 30 分钟），请重新导入" |
| `cannot parse OpenAPI` | "OpenAPI 文档解析失败：[具体错误位置]" |
| `unsupported version` | "仅支持 OpenAPI 3.0 / 3.1，当前版本 [X] 不支持" |
| `network timeout` | "网络超时，请检查 OpenAPI 来源是否可访问" |

**原则**：前端必须把后端 message 翻译成"用户能理解的业务语言"。

---

### H7 · 无统一"快捷键 + 全局搜索"

**维度**：操作效率 + 学习成本

**问题描述**：

- 无 `Ctrl/Cmd+K` 全局搜索
- 列表页 / 详情页无键盘快捷键
- 用户必须鼠标点击，效率低

**影响**：高频用户操作效率低；无"专家模式"

**修复建议**：

1. **v1.1 实现 `Ctrl/Cmd+K` 全局搜索**：跨 Project 搜 Run / Case / Suite
2. **v1.1 列表页快捷键**：`/` 聚焦搜索 / `N` 新建 / `R` 刷新 / `↑↓` 选择 / `Enter` 进入
3. **v1.1 详情页快捷键**：`Esc` 返回 / `E` 编辑 / `Delete` 删除
4. 在 PageHeader 加 `?` 按钮显示快捷键面板

---

### H8 · 加载中文案与时机的"闪烁"

**维度**：Loading + 一致性

**问题描述**：

1. 部分 Loading 显示瞬间（< 200ms）就消失，造成视觉闪烁
2. 部分 Loading 30 秒后仍无任何提示，用户不知是卡死还是慢
3. Skeleton 加载完成切换到真实数据时，整页"跳一下"

**影响**：用户感受到"系统不稳定"

**修复建议**：

1. **延迟显示**：`useDelayLoading(300ms)`，300ms 内的请求不显示 Loading
2. **超时反馈**：> 10 秒显示 "加载较慢" + 重试按钮
3. **Skeleton 平滑过渡**：数据就绪后 100ms 淡出 Skeleton，再淡入真实内容（避免闪烁）
4. **参考 StateFlow.md §2.4 / §3.5** 已建立标准，需在所有 React Query 调用点统一

---

## ③ Medium 优先级问题（18 项）

> 影响效率或清晰度，建议在 v1.1 ~ v1.2 修复。

---

### M1 · Suite 列表信息密度低（M4 in UX_REVIEW）

**维度**：操作效率

**问题描述**：Suite 列表只显示"名称 / 描述 / 时间"，用户必须点进详情才能判断优先级。

**修复建议**：增加 Case 数、最近通过率、最近执行时间三列。

---

### M2 · Dashboard KPI 单一（L2 in UX_REVIEW）

**维度**：学习成本 + 视觉层级

**问题描述**：Dashboard 仅显示"Project 数 + 角色"，缺少 Run 总数、通过率、错误率等关键指标。

**修复建议**：增加 6 个 KPI：Project 总数 / Run 总数（30 天） / 通过率 / 失败数 / 错误数 / 最近 Run 时间。

---

### M3 · Dashboard 教学卡长期存在（L3 in UX_REVIEW）

**维度**：学习成本

**问题描述**：完成首次配置的用户仍看到 "推荐工作路径" 教学卡。

**修复建议**：根据 `recentActivities.length > 0` 判断，配置完成后自动隐藏。

---

### M4 · Project 列表摘要不完整（L4 in UX_REVIEW）

**维度**：视觉层级

**修复建议**：列表行增加 Owner 头像、Case 数、最后访问时间。

---

### M5 · Case 编辑器 Body 字段可视化弱（L5 in UX_REVIEW）

**维度**：表单

**问题描述**：Body 全为 textarea，无 JSON 校验、无可视化编辑。

**修复建议**：集成 Monaco Editor 或 JSON Schema Form；至少做 JSON 合法性校验 + 错误提示。

---

### M6 · Run Center 与 Execution Center 入口命名不一致（L6 in UX_REVIEW）

**维度**：一致性

**问题描述**：UI 中混用 "Run Now"、"执行"、"快速执行"、"Run Center"、"Execution Center"。

**修复建议**：统一为 **"执行 XXX"**（如"执行 Project"、"执行 Suite"、"执行 Case"）；页面名统称"执行中心"。

---

### M7 · "最近 Run" 区域缺跳转提示（L7 in UX_REVIEW）

**维度**：导航

**问题描述**：Dashboard / Overview / Report 列表都展示 5 条 Run，但只有 "查看全部" 按钮，没有明显"这是历史报告"的提示。

**修复建议**：增加副标题"最近 5 次执行" + "查看全部"按钮更醒目（Primary Ghost）。

---

### M8 · 系统管理缺乏权限分组 + 审计入口（M9 in UX_REVIEW）

**维度**：一致性 + 学习成本

**问题描述**：角色权限字符串列表难维护；操作日志缺。

**修复建议**：

1. v1.1 权限按 domain 分组（Project / Environment / Suite / Case / Run / Report / System）
2. v1.2 增加操作审计入口（仅 superuser 可见）

---

### M9 · 全局导航缺搜索 / 通知 / 偏好（M10 in UX_REVIEW）

**维度**：导航

**修复建议**：v1.1 实现 `Ctrl+K` 全局搜索；v1.2 实现通知中心（即使为空壳）。

---

### M10 · Environment 缺复制 / 测试连接 / 引用关系提示（M3 in UX_REVIEW）

**维度**：操作效率

**修复建议**：行内增加 "复制 Base URL" 图标按钮；删除时显示 "被 N 个 Run 引用"。

---

### M11 · 三处执行入口的预填不一致

**维度**：一致性

**问题描述**：

| 入口 | 环境预填 | Run Name 预填 | Variables 显示 |
|---|---|---|---|
| Workspace Header | 默认环境 | 空 | 只读 |
| Run Center | 默认环境 | 空 | 只读 |
| Suite 详情 "执行 Suite" | 默认环境 | "Suite: 冒烟回归" | 只读 |
| Case 编辑器 "执行 Case" | 默认环境 | "Case: 获取用户详情" | 只读 |

前两者 Run Name 留空，后两者自动生成。**风格不统一**。

**修复建议**：统一定为 **"留空由后端自动生成"**；或在所有入口都自动生成（"执行 XXX #时间戳"）。

---

### M12 · Workspace 引导步骤跳转过多（M2 in UX_REVIEW）

**维度**：学习成本

**修复建议**：改为"串行 Drawer"模式（用户不离开当前页，按顺序打开 4 个 Drawer 创建）。

---

### M13 · 全局搜索栏缺失（M10 in UX_REVIEW）

**维度**：操作效率

**修复建议**：Header 加全局搜索框（v1.1），跨 Project 搜 Run / Case / Suite。

---

### M14 · 删除操作的"延迟按钮"未实现

**维度**：按钮风格 + 错误提示

**问题描述**：高危删除（删 Project）应 3 秒后才可点击，但当前直接可点。

**修复建议**：v1.1 实现延迟按钮（参考 Interaction.md §12.4）。

---

### M15 · 表单 dirty 离开确认未统一

**维度**：表单

**问题描述**：部分 Drawer / Modal 在表单 dirty 时未拦截 Esc / 路由切换 / 关闭。

**修复建议**：封装统一 `<DirtyGuard>` 组件；接入所有 Form Drawer / Modal。

---

### M16 · Run 进行中切换 Project 缺少警告

**维度**：一致性

**问题描述**：用户在 Run 进行中切换 Project，应弹 Modal 警告，但当前未实现。

**修复建议**：实现 NavigationUX §8.4 切换前确认。

---

### M17 · Skeleton 缺少"完成过渡"动画

**维度**：Loading + 视觉层级

**问题描述**：Skeleton → 真实数据是瞬间切换，造成"跳一下"。

**修复建议**：用 100ms 淡出 + 100ms 淡入的交叉动画。

---

### M18 · "保存并执行" 合并按钮缺失

**维度**：操作效率

**问题描述**：Case 编辑完成后用户需点击 "保存" → 再点击 "执行"。可合并为 "保存并执行"。

**修复建议**：v1.1 增加 "保存并执行" 按钮，自动跳 Run Drawer。

---

## ④ Low 优先级问题（10 项）

> 细节优化，提升专业感。

---

### L1 · 输入框聚焦时缺少视觉强调

**问题**：聚焦边框颜色变化不够明显。

**修复**：聚焦时增加 2px 主色 outline + 边框加粗。

---

### L2 · Tag 在窄屏下截断

**问题**：Method Tag 在窄屏（< 820px）下被截断为 "..."。

**修复**：窄屏下显示 Method 全名（不带颜色）或加 Tooltip。

---

### L3 · 表格行 Hover 颜色过浅

**问题**：当前 `--bg-muted` 50% 透明度，颜色过浅，弱视用户难以察觉。

**修复**：使用 `--bg-muted` 100% 或加深 5%。

---

### L4 · 面包屑分隔符风格

**问题**：当前 `/`，可改为 `›` 更符合中文阅读习惯。

**修复**：统一分隔符为 `›`。

---

### L5 · PageHeader 标题字号不统一

**问题**：部分 PageHeader 用 `level={2}`（24px），部分用 `level={3}`（20px）。

**修复**：统一为 `level={2}`，副标题 Caption。

---

### L6 · Drawer 关闭按钮 [×] 与 Esc 提示

**问题**：Esc 关闭无视觉提示，新用户不知道可用 Esc。

**修复**：在 Drawer 顶部增加 "按 Esc 关闭" 提示文字。

---

### L7 · EmptyView 图标使用 Outlined，应统一

**问题**：部分 EmptyView 用 Outlined，部分用 Filled。

**修复**：统一为 Outlined（与 AntD 默认一致）。

---

### L8 · 状态 Tag 在不同页面文案不一致

**问题**：失败状态文案有 "失败"、"断言失败"、"运行失败" 三种。

**修复**：统一为 **"断言失败"**（Result）+ **"运行失败"**（Run）。

---

### L9 · Tooltip 默认延迟 500ms 过长

**问题**：用户悬停 500ms 才显示 Tooltip，偏慢。

**修复**：改为 300ms。

---

### L10 · 焦点环颜色对比度不足

**问题**：当前 outline 使用主色 `#315EFB`，在白底上对比度 4.0，未达 WCAG AA 4.5。

**修复**：加深为 `#163DC4`，对比度 6.5。

---

## ⑤ 按组件 / 页面的问题清单

### 5.1 组件级问题

| 组件 | 问题 | 等级 |
|---|---|---|
| `AppShell` | Sider 折叠时 Project 切换器视觉弱 | Low |
| `AppHeader` | 无全局搜索 / 通知 | Medium（M9） |
| `PageHeader` | 标题字号不统一 | Low（L5） |
| `ProjectCard` | 无 Owner / Case 数 / 最后访问 | Medium（M4） |
| `EnvironmentTable` | 缺复制 URL / 引用关系 | Medium（M10） |
| `SuiteTable` | 信息密度低 | Medium（M1） |
| `CaseTable` | 无 Suite 归属筛选 | Low |
| `RunTable` | 状态文案不一致 | Low（L8） |
| `RunExecutionDrawer` | 三种 Scope 入口重复 | High（H1） |
| `ErrorBoundary` | 无错误码 / 反馈渠道 | Low |
| `DashboardMetricCard` | KPI 单一 | Medium（M2） |

### 5.2 页面级问题

| 页面 | 问题 | 等级 |
|---|---|---|
| Dashboard | 教学卡长期存在 | Medium（M3） |
| Login | 缺忘记密码 / 账号说明 | Low |
| Workspace Overview | 与 Report 列表 KPI 重复 | High（H3） |
| Environment 列表 | 缺复制 / 引用 | Medium（M10） |
| Suite 列表 | 信息密度低 | Medium（M1） |
| Suite 详情 | 添加 Case Modal 无搜索 / 高级筛选 | Medium |
| Case 列表 | 无归属标识（M6） | Medium |
| Case 编辑器 | Body 可视化弱 | Medium（M5） |
| Run Center | 命名 / 入口与 Execution Center 不一致 | Medium（M6） |
| Report 列表 | 与 Overview 重复 | High（H3） |
| Run Detail | 默认 Tab 不是 Failure | High（H4） |
| Result Detail | 与 Run Detail Tab 重复 | High（H4） |
| User 管理 | 角色显示为 ID | Medium |
| Role 管理 | 权限字符串列表难维护 | Medium（M8） |

---

## ⑥ 各评估维度的综合结论

### 6.1 一致性 ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| H1 执行入口重复 | High |
| H3 Report 与 Overview 重复 | High |
| M6 Run Center / Execution Center 命名不一致 | Medium |
| M11 三处执行入口预填不一致 | Medium |
| L5 PageHeader 标题字号 | Low |
| L8 状态 Tag 文案 | Low |

**结论**：整体一致性 60 分。需通过 NavigationUX + Interaction 规范彻底收敛。

---

### 6.2 学习成本 ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| H7 无快捷键 / 全局搜索 | High |
| M2 Dashboard KPI 单一 | Medium |
| M3 教学卡长期存在 | Medium |
| M12 Workspace 引导步骤多 | Medium |

**结论**：新用户上手成本偏高。需通过"减少点击 + 引导收敛 + 快捷键"降低。

---

### 6.3 操作效率 ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| H1 执行入口重复 | High |
| H4 Run / Result 数据重复 | High |
| H5 Case 返回丢失搜索 | High |
| M1 Suite 列表信息密度低 | Medium |
| M10 Environment 缺快捷操作 | Medium |
| M13 全局搜索缺失 | Medium |
| M18 "保存并执行" 未实现 | Medium |

**结论**：主流程点击数偏多。需通过"信息前置 + 上下文保持 + 合并操作"削减。

---

### 6.4 视觉层级 ⭐⭐⭐⭐

| 问题 | 等级 |
|---|---|
| M4 Project 列表摘要 | Medium |
| L3 表格行 Hover 颜色过浅 | Low |
| L10 焦点环对比度不足 | Low |

**结论**：整体视觉层级清晰，少数细节待优化。

---

### 6.5 导航 ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| H2 Project 切换上下文丢失 | High |
| H5 Case 返回丢失搜索 | High |
| M7 "最近 Run" 缺跳转提示 | Medium |
| M9 全局搜索 / 通知缺失 | Medium |

**结论**：导航基本到位，但 Project 切换是最大坑点。

---

### 6.6 空页面 ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| 无 "导入 OpenAPI" CTA 在 Case 空态 | Medium |
| Dashboard 空态文案可优化 | Low |

**结论**：空态已实现但 CTA 不够丰富。

---

### 6.7 错误提示 ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| H6 OpenAPI 错误不友好 | High |
| 部分 Loading 无超时反馈 | High（H8） |
| L1 错误页缺错误码 | Low |

**结论**：错误处理基本到位，但后端 message 直接展示用户看不懂。

---

### 6.8 Loading ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| H8 闪烁 / 超时无反馈 | High |
| M17 Skeleton 切换跳变 | Medium |

**结论**：Loading 基础已实现，但完成过渡 + 超时反馈缺失。

---

### 6.9 组件重复 ⭐⭐⭐

| 问题 | 等级 |
|---|---|
| `/project/*` 与 `/workspace/*` 重复实现 | Medium |
| `RunStatus` / `ResultStatus` 已封装（✓） | — |

**结论**：核心组件已封装（`StatusTags` / `AsyncState` / `PageHeader`），但 `/project/` 老路径与 `/workspace/` 新路径并存是技术债。

---

### 6.10 按钮风格 ⭐⭐⭐⭐

| 问题 | 等级 |
|---|---|
| M14 高危删除缺延迟按钮 | Medium |

**结论**：按钮规范基本落地，仅延迟按钮待实现。

---

### 6.11 表单 ⭐⭐⭐⭐

| 问题 | 等级 |
|---|---|
| M15 dirty 离开确认未统一 | Medium |

**结论**：表单规范基本到位，校验完整。

---

### 6.12 可访问性 ⭐⭐

| 问题 | 等级 |
|---|---|
| 缺少键盘快捷键 | Medium（H7） |
| ARIA 标签不完整 | Low |
| L10 焦点环对比度不足 | Low |

**结论**：可访问性是最大短板，未达企业级标准。

---

## ⑦ 修复优先级（按价值 / 改动量）

### 7.1 P0 立即修复（1~2 周）

| # | 任务 | 估时 | 价值 |
|---:|---|---:|---|
| 1 | H2 Project 切换 A/B/C 策略 | 3 天 | 极高 |
| 2 | H3 Report / Overview 去重 | 2 天 | 高 |
| 3 | H1 执行入口统一 | 2 天 | 高 |
| 4 | H8 Loading 闪烁 + 超时反馈 | 1 天 | 高 |

### 7.2 P1 短期优化（1 个月内）

| # | 任务 | 估时 | 价值 |
|---:|---|---:|---|
| 5 | H4 Run / Result Tab 去重 | 2 天 | 中 |
| 6 | H5 Case 返回携带 URL Query | 1 天 | 高 |
| 7 | H6 OpenAPI 错误翻译 | 1 天 | 中 |
| 8 | M1 Suite 列表摘要 | 0.5 天 | 中 |
| 9 | M2 Dashboard KPI 扩展 | 1 天 | 中 |
| 10 | M11 / M16 执行入口预填统一 + 切换确认 | 1 天 | 中 |
| 11 | M15 dirty 守卫封装 | 1 天 | 中 |

### 7.3 P2 中期优化（2~3 个月）

| # | 任务 | 估时 | 价值 |
|---:|---|---:|---|
| 12 | H7 全局快捷键 v1.1 | 5 天 | 高 |
| 13 | M13 全局搜索 v1.1 | 5 天 | 中 |
| 14 | M8 Role 权限分组 + 审计 | 3 天 | 中 |
| 15 | M12 Workspace 引导改为串行 Drawer | 3 天 | 中 |
| 16 | M5 Case Body 可视化编辑器 | 5 天 | 中 |
| 17 | M14 高危删除延迟按钮 | 0.5 天 | 中 |
| 18 | M17 Skeleton 平滑过渡 | 1 天 | 低 |
| 19 | M18 保存并执行 | 1 天 | 中 |

### 7.4 P3 长期优化（3 个月+）

| # | 任务 | 估时 | 价值 |
|---:|---|---:|---|
| 20 | M9 通知中心 v1.2 | 5 天 | 中 |
| 21 | L 系列（10 项细节优化） | 1 周 | 低 |
| 22 | 可访问性 ARIA 全量补齐 | 1 周 | 中 |

---

## ⑧ 不在本期范围

| 项 | 原因 |
|---|---|
| 移动端原生 App | 当前仅桌面场景 |
| PWA / 离线访问 | 当前业务不需要 |
| 多语言 i18n | 当前仅简体中文 |
| 项目模板 / Marketplace | 超出当前业务范围 |
| AI 助手 | 不属于 MVP |
| 实时协作 | 单一用户工作场景 |

---

## ⑨ 总结

### 9.1 平台 UI 现状

✅ **做对的**：

- 视觉风格专业（蓝紫渐变 + 中性色 + 多级阴影）
- 核心组件已封装（`StatusTags` / `AsyncState` / `PageHeader` / `ErrorBoundary`）
- 表单校验完整，dirty 检测到位
- Workspace + App Shell 双层架构清晰
- 状态机 + 交互规范已文档化（`StateFlow.md` / `Interaction.md`）

❌ **需要改进的**：

- 执行入口 4 处分散（高）
- Project 切换上下文丢失（高）
- Report 与 Overview 重复（高）
- 无快捷键 / 全局搜索（高）
- 部分错误信息不够友好（高）

### 9.2 综合评价

**当前等级**："企业级产品的 MVP 完成度"

**目标等级**："企业级产品的成熟度"

**差距**：约 2~3 个月工作量

**关键路径**：

1. 完成 NavigationUX 落地（H2 Project 切换）
2. 完成 Report / Overview 去重（H3）
3. 统一执行入口（H1）
4. 实施 Loading 规范（H8）
5. 上线快捷键（H7）

完成后平台 UX 可达 4.5/5。

---

## 附录 A · 评估方法说明

### A.1 评估来源

- `docs/02-design/UX_REVIEW.md`（首轮发现，4 High / 10 Medium / 7 Low）
- `frontend/src/components/` 全部组件代码走读
- `frontend/src/pages/` 全部页面代码走读
- `styles.css` 视觉规范检查
- 12 维度系统性评估

### A.2 优先级判定

| 信号 | 判定为 High |
|---|---|
| 用户高频迷失 | ✅ |
| 主流程点击数 > 10 | ✅ |
| 阻塞业务流程 | ✅ |
| 企业级产品典型反模式 | ✅ |

| 信号 | 判定为 Medium |
|---|---|
| 影响效率（> 30% 操作变慢） | ✅ |
| 信息密度不足 / 过多 | ✅ |
| 缺少行业最佳实践 | ✅ |

| 信号 | 判定为 Low |
|---|---|
| 视觉细节 | ✅ |
| 文案优化 | ✅ |
| 专业感提升 | ✅ |

---

## 附录 B · 12 维度评分明细

| 维度 | 当前评分 | 目标 | 改进项 |
|---|:---:|:---:|---|
| 一致性 | 3.0 | 4.5 | H1 / H3 / M6 / M11 |
| 学习成本 | 3.0 | 4.0 | H7 / M2 / M3 |
| 操作效率 | 3.0 | 4.5 | H1 / H4 / H5 / M1 / M13 |
| 视觉层级 | 4.0 | 4.5 | M4 / L3 / L10 |
| 导航 | 3.0 | 4.5 | H2 / H5 / M7 / M9 |
| 空页面 | 3.5 | 4.0 | CTA 丰富 |
| 错误提示 | 3.0 | 4.0 | H6 / H8 |
| Loading | 3.0 | 4.0 | H8 / M17 |
| 组件重复 | 3.5 | 4.5 | 老路径收敛 |
| 按钮风格 | 4.0 | 4.5 | M14 |
| 表单 | 4.0 | 4.5 | M15 |
| 可访问性 | 2.0 | 4.0 | 快捷键 + ARIA |
| **综合** | **3.4** | **4.4** | — |

---

## 附录 C · 修复计划时间线

```text
2026-07-15  ━━ Review 完成
2026-07-22  ━━ P0 完成（4 项 High，估时 8 天）
2026-08-15  ━━ P1 完成（7 项 Medium，估时 7.5 天）
2026-09-30  ━━ P2 完成（8 项，估时 24.5 天）
2026-12-31  ━━ P3 完成（10+ 项，估时 ~3 周）
2027-Q1     ━━ 可访问性 + 性能优化
```

---

## 附录 D · 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-15 | 初版：12 维度系统性 Review，36 个问题（8 High / 18 Medium / 10 Low） |

---

**约束再确认**

- 本 Review 基于当前代码状态、设计规范文档、UX_REVIEW 文档综合得出
- 修复优先级结合"价值 / 改动量"评估
- 所有问题不涉及业务逻辑改动，可通过前端组件 / 状态 / 路由 / URL Query 解决
- 与 DesignSystem.md / Layout.md / NavigationUX.md / ComponentLibrary.md / Wireframe.md / StateFlow.md / Interaction.md 完整对齐