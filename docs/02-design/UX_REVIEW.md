# API 自动化平台 UX Review

> 角色：资深产品经理  
> 范围：登录 → 创建 Project → Environment → 导入 OpenAPI → Suite → Case → Run → Report 全链路 UX 评估  
> 评估维度：流程顺畅度、跳转次数、断点、迷失感、重复页面、企业级标准

---

## 0. 评估方式

按用户视角串起主流程，逐页面记录每一步操作与潜在摩擦；按严重程度分为 High / Medium / Low 三个等级。

评分原则：

- High：阻塞主流程、导致用户放弃、企业级产品不能接受。
- Medium：影响效率或清晰度，但能完成。
- Low：细节优化，提升体验。

---

## 1. 主流程逐页面走查

### 1.1 登录页 `/login`

- 状态：单页表单。
- 优点：邮箱 + 密码 + 登录按钮，极简。
- 风险：
  - 登录失败 / 账号禁用时仅显示后端 message，未提供“忘记密码 / 申请账号”入口。
  - 没有展示后端支持哪些账号来源（首个用户自动为 superuser，普通用户需 superuser 邀请）。
  - 没有 demo 账号提示，运维 / 演示场景使用成本偏高。
- 结论：**中等** 问题，缺密码找回 / 账号说明。

### 1.2 Dashboard `/dashboard`

- 状态：欢迎 + KPI（Project / 角色 / 推荐工作路径 / Recent Run / 最近 Project）。
- 优点：Recent Project 与 Recent Run 区域对企业用户已具备基本导览价值。
- 风险：
  - KPI 仅展示 Project 数量与角色，缺少“总执行 / 总失败 / 全局通过率”等企业级指标。
  - “推荐工作路径”对已完成配置的用户长期存在，产生“教学卡”噪音。
  - Dashboard 是无 Project 数据范围选择时进入的“入口”，但 Project 选择器显示在顶部；新用户在没有 Project 时会看到空状态而不是被引导去创建。
- 结论：**低** 问题，KPI 较少 + 教学卡长期存在。

### 1.3 Project 列表 `/projects`

- 状态：表格 + 搜索 + 分页。
- 优点：典型 CRUD 列表。
- 风险：
  - 进入列表后必须点“名称”才能进入 Workspace；新建 Project 后跳 Workspace 概览，列表与 Workspace 之间无明确过渡。
  - 不显示 Project 摘要（Owner / 资产数 / 状态），无法在列表内决定优先级。
- 结论：**低** 问题，信息密度可加强。

### 1.4 Workspace 概览 `/projects/{id}/workspace/overview`

- 状态：Header + 项目摘要 / 资产配置 / 执行质量 / 引导 / Workspace 引导 / 最近 Run。
- 优点：KPI 完整，引导步骤 1~4 明确。
- 风险：
  - 引导步骤 1 默认环境缺失时跳到 Environment；2 Suite；3 Case；4 Run。每一步都是“独立跳转”，用户需在 Sider、页面顶部操作、抽屉之间切换。
  - “最近 Run” 区域紧接一个完整 Report 表格 + 行点击 → Report 详情；同一信息（Run 列表）也出现在 `/report` 列表页，造成功能重复。
  - Overview 页内出现 Run 列表 + Run 状态 Tab，让 Overview 同时承担“项目摘要 + Report 列表”，边界模糊。
- 结论：**中** 问题，引导链路 + Overview 与 Report 列表的功能重复。

### 1.5 Environment 模块 `/environment`

- 状态：搜索 + Table + 新建/编辑 Drawer + 删除 Popconfirm + 默认徽标。
- 优点：默认环境限制、Header / Variables 区分、JSON 编辑器 + 校验完整。
- 风险：
  - Workspace 概览“1. 设置默认环境”会跳到这里；但当用户没有 default 时，进入 Run Drawer 已经给出 Alert，概览与 Drawer 引导存在重复，缺少“点此去设置”快捷入口。
  - 环境名“Base URL”列只显示 URL，没有“复制 / 测试连接”按钮，对企业级调试不友好。
  - 删除非默认环境时只是 Popconfirm，没有“此环境已被 X 个 Suite / Run 引用”提示。
- 结论：**中** 问题，引导重复 + 缺少引用关系提示。

### 1.6 OpenAPI 导入 `/import/:suiteId`

- 状态：选择来源（URL / JSON）+ 预览 + 确认。
- 优点：完全复用现有后端能力，UI 完整。
- 风险：
  - 仅支持 Suite 上下文入口；Workspace 概览、Suite 详情、Case 列表三处都可以跳进去，但入口不统一（只有 Suite 详情顶部有 OpenAPI 按钮）。
  - 当前 `preview_id` 不可用时，确认按钮被禁用，但提示“预览功能不可用”写得不够明显，企业用户可能误以为系统故障。
  - Tags / 冲突策略 / 名称前缀一次性给出，没有“智能推荐”默认值。
- 结论：**中** 问题，入口分散 + 错误提示不友好。

### 1.7 Suite 列表 `/suite`

- 状态：搜索 + Table + 新建 / 编辑 Suite。
- 优点：极简。
- 风险：
  - 列表中 Suite 是“桶”，看不到“Case 数量 / 上次执行 / 上次通过率”等关键信息；点击进入 Suite 详情才能看到，体验断点较深。
  - Suite 描述列只展示原文，缺少“被 Run 引用次数”等上下文。
- 结论：**中** 问题，列表信息密度不足。

### 1.8 Suite 详情 `/suite/:suiteId`

- 状态：Header（执行 / 导入 / 编辑 / 删除）+ 关联 Case 表 + 上下移 + 添加 Case Modal。
- 优点：与后端 `test_case_ids` 顺序接口完全对齐。
- 风险：
  - “执行 Suite”会打开 Execution Drawer，与 Run Center 的 Drawer 重复出现（同一组件，但是否走 Run Center 的表单 / 上下文待定）。
  - 行内“跳到 Case”使用 `?from=suite&suiteId=` 上下文，但 Case 列表的来源标识与 Case 编辑器的“返回”按钮并未统一；返回时 Suite 详情应能识别并刷新，新用户难以判断。
  - “添加 Case”Modal 过滤已添加的 Case，但当 Suite 内已有很多 Case 时，剩余可选 Case 列表会很长，缺少搜索与按 Method 过滤（已有 search，但没有高级筛选）。
- 结论：**中** 问题，与 Run Center 重复 + 上下文返回不一致。

### 1.9 Case 列表 `/case`

- 状态：搜索 + Method / 启用筛选 + Table + 执行 / 编辑 / 删除。
- 优点：CRUD 与筛选完整。
- 风险：
  - 当 Case 未归属于任何 Suite 时，列表通过服务端 `?search=` 也会返回。UI 中没有“未归属 Suite”标识，导致用户不知道 Case 是否真的可以 Run。
  - 列表项点击“名称”跳 Case 编辑器，但 Case 编辑器为单页表单，URL 切换丢失搜索参数；返回后无法回到筛选状态。
  - “执行”按钮当 Case disabled 时被禁用，Tooltip 缺失具体原因。
- 结论：**中** 问题，归属标识与编辑返回路径。

### 1.10 Case 编辑器

- 状态：单页表单（基本信息 / 请求配置 / 断言配置）。
- 优点：Drawer 风格、保存前后保留 Suite 上下文、Method 限制、断言类型完整。
- 风险：
  - “Body” 字段依赖 Body Type，多个 Tab 但所有都是 textarea，缺少“可视化 JSON 编辑 / 校验”提示。
  - “保存”出错时保留 Suite 上下文，但行级 loading 与表单整体 loading 重复，UI 节奏不清晰。
- 结论：**低** 问题，Body 编辑器可增强。

### 1.11 Run Center `/run`

- 状态：表单（名称 / 环境 / Variables / 范围）+ 提交 + 最近 5 Run。
- 优点：与 Execution Center Drawer 共享参数。
- 风险：
  - Run Center 与 Suite 详情 / Case 编辑器的 Execution Drawer 高度重复：三个入口都打开“同一个 Drawer”，但 Run Center 是直接跳到“Run Center 表单”，没有“Execution Center Drawer”概念。Workspace 概览的“快速执行”则直接调用 Execution Center Drawer。
  - 出现三处执行入口 + 三种入口交互，文档/界面不一致。
  - “最近 5 Run”直接显示 5 行状态，没有跳转按钮（虽然在 Overview 与 Report 列表已有，但此处用户期望的是“5 条 → 报告列表”）。
- 结论：**High** 问题，三处执行入口重复。

### 1.12 Report 列表 `/report`

- 状态：KPI + Recent Runs + Run 历史（带状态筛选 + 搜索）。
- 优点：与 Workspace Overview 的 Report 区块功能高度一致（因为我们做了 KPI 摘要 + Recent Runs），筛选 + 搜索完整。
- 风险：
  - 与 Workspace Overview 的“最近 Run”区块完全重复：同样的 KPI、同样 5 条 Run、同样状态 / 通过率。
  - 两处都有 KPI 卡 + Recent Runs + Run 历史，重复面积大。
  - Report 列表与 Overview 内的 Run 列表表头几乎相同，用户从 Overview 看到 Run 列表，点击进 Run 详情，再返回 Overview 又能看到相同列表；这是“信息重复 + 路由重复”的典型反模式。
- 结论：**High** 问题，Report 列表与 Overview Report 区块重复。

### 1.13 Run 详情 `/report/:runId`

- 状态：Header（状态 / 通过率 / 耗时 / 环境）+ 4 Tab（概览 / 失败原因 / 全部 Result / 元信息）。
- 优点：默认 Tab 智能切换、URL `?tab=` 同步、失败原因为 Allure 风格断言对比。
- 风险：
  - “概览”Tab 内重复了 KPI（通过 / 失败 / 错误 / 耗时），与 Report 列表的 KPI 视觉重复。
  - 全部 Result Tab 与 Report 列表的 Run 表格内容相似但更详细，与 Report 列表顶部 Recent Runs 重复。
  - 跳到 Case 编辑器保留 `?from=report&runId=&resultId=`，但 Case 编辑器返回时是否回 Run 详情需手动验证；用户从 Result 详情跳 Case 编辑再返回，可能回到 Run 列表。
- 结论：**中** 问题，跨页面信息重复 + 返回路径不一致。

### 1.14 Result 详情 `/report/:runId/result/:resultId`

- 状态：Header（状态 / Method / Path / 环境）+ 5 Tab（请求 / 响应 / 断言 / 错误 / 概览）。
- 优点：5 个 Tab 完全覆盖需求、状态码色块、JSON 智能解析、body_truncated 提示。
- 风险：
  - 5 个 Tab 的内容与 Run 详情 Tab 高度重复（Run 详情全部 Result Tab 与 Result 详情请求/响应 Tab 是同一份数据）。
  - “概览”Tab 信息密度低，对企业用户来说与 Run 详情元信息 Tab 重复。
- 结论：**中** 问题，跨 Tab 信息重复。

### 1.15 Information Tab（项目设置）

- 状态：基本信息 + 危险操作（删除项目，输入名称二次确认）。
- 优点：删除高危操作有二次确认。
- 风险：
  - 没有“Project 改名 / 描述修改”入口，目前仅“删除”能进入 Workspace，缺少对项目元数据的常规维护。
  - 删除提示“删除后无法恢复”，但没说明“历史 Run 报告是否保留”，企业用户关心。
- 结论：**中** 问题，缺少元数据编辑 + 删除影响说明。

### 1.16 Project 切换器（左侧 Sider 顶部）

- 优点：跨 Project 切换有视觉锚点。
- 风险：
  - 切换 Project 时仅“当前 Project 模块”上下文保留，**URL / 搜索状态 / Tab 状态不重置**；用户在 Project A 打开 Report 详情（URL 含 runId），切到 Project B 后 Workspace 仍指向 Project A 页面，但 Sider 显示 Project B。**典型断点 / 迷失**。
  - Project 切换器只显示当前用户拥有的 Project，多 Project 用户可能找不到“我要回到 Project A”。
- 结论：**High** 问题，Project 切换上下文不重置。

### 1.17 系统管理（User / Role）

- 状态：表格 + 搜索 + 启停 + 角色分配。
- 优点：与后端 API 对齐。
- 风险：
  - User 表中“用户当前角色”只展示 Role ID（lookup 表），如未加载 Role 列表则显示“未知角色”。
  - 角色管理只展示权限字符串列表，没有“权限分组 / 搜索”，企业级权限管理需要按 domain 分组。
  - 当前用户自助修改“superuser 标记”虽然前端锁定，但缺少“操作日志 / 审计”入口（与当前后端能力对应，但企业产品通常要求）。
- 结论：**中** 问题，角色管理缺乏分组与审计入口。

### 1.18 全局导航 Sider

- 优点：固定侧栏 + Project 切换器 + 模块列表。
- 风险：
  - 没有“面包屑 / 全局搜索 / 帮助中心 / 通知 / 最近访问”模块。Workspace 内虽然用 PageHeader 提供面包屑，但全局 Sider 没有“搜索 Run / Case / Suite”入口，企业用户查找历史数据较慢。
  - 顶部没有“用户中心 / 偏好 / 通知 / 主题切换”。
- 结论：**中** 问题，缺乏全局搜索 / 通知 / 偏好。

---

## 2. 问题清单（按优先级）

### High

- **H1. Project 切换上下文不重置**：URL（含 runId / caseId / tab 参数）在 Project 切换后保留，导致 Project B 中显示 Project A 的资源；用户极易迷失。
- **H2. 三处执行入口重复**：Suite 详情 / Case 编辑器 / Run Center / Workspace Header 都打开“执行表单”，但 UI / 入口命名 / 流程不一致。
- **H3. Report 列表与 Overview 区块内容重复**：KPI + Recent Runs + Run 历史在 Workspace Overview 与 Report 列表中重复出现，缺少唯一价值。

### Medium

- **M1. Overview 与 Run Detail 概览 Tab KPI 重复**：相同指标在多个页面展示，缺乏职责划分。
- **M2. Workspace Overview 引导步骤跳转过多**：4 步引导从 Overview → Environment → Suite → Case → Run，每步都需在 Sider、Page Header、Drawer 之间切换；缺“下一步直接动作”按钮。
- **M3. Environment 缺复制 / 测试连接 / 引用关系提示**：Base URL 列只展示 URL；删除时未提示“被 N 个 Run 引用”。
- **M4. Suite 列表信息密度不足**：缺少“Case 数量 / 最近通过率”等关键信息，导致必须进入详情才能决策。
- **M5. OpenAPI 导入错误提示不友好**：当 `preview_id` 不可用时，错误信息仅以“预览功能不可用”概述，企业用户可能误以为系统故障。
- **M6. Case 列表归属标识 + 编辑返回路径**：未归属 Suite 的 Case 缺少标识；Case 编辑器返回时丢失搜索状态。
- **M7. Run 详情与 Result 详情 Tab 信息重复**：全部 Result Tab 与 Result 详情请求 / 响应 Tab 是同一份数据。
- **M8. Information Tab 缺元数据编辑 + 删除影响说明**：项目改名 / 描述修改无入口；删除项目时未说明 Run 报告是否保留。
- **M9. 系统管理缺乏权限分组 + 审计入口**：角色权限字符串列表难维护；操作日志缺。
- **M10. 全局导航缺搜索 / 通知 / 偏好**：无全局搜索 Run / Case / Suite，无通知中心，无偏好设置。

### Low

- **L1. 登录页缺密码找回 / 账号说明**：无“忘记密码 / 申请账号”入口。
- **L2. Dashboard KPI 单一**：仅 Project 数量与角色；缺少总执行 / 通过率等企业级指标。
- **L3. Dashboard 教学卡长期存在**：已完成配置的用户仍看到“推荐工作路径”。
- **L4. Project 列表摘要不完整**：缺 Owner / 资产数 / 状态。
- **L5. Case 编辑器 Body 字段可视化弱**：全为 textarea，缺 JSON 校验提示。
- **L6. Run Center 与 Execution Center 入口命名不一致**：执行 / Run Center / Drawer 名称在 UI 中混用。
- **L7. “最近 Run” 区域缺跳转提示**：Overview 与 Report 列表都展示 5 条 Run，但无明确“查看更多 / 进入报告列表”入口。

---

## 3. 关键断点 / 迷失点

1. **Project 切换 URL 不重置**：H1。
2. **同一 Run 信息在 Overview / Report 列表 / Run 详情 / Result 详情 中重复出现**，用户难以判断下一步该看哪里。
3. **执行入口分散**：Run Center / Suite 详情 / Case 编辑器 / Header 都有执行入口，新用户需要记住哪个入口打开哪个 Drawer。
4. **Case 编辑器返回丢失搜索 / 筛选状态**：Case 列表 → 编辑 → 返回，可能跳到空筛选的全列表。
5. **Role 表显示 Role ID（lookup 失败时显示“未知角色”）**：用户无法快速识别角色。

---

## 4. 重复页面 / 重复区块

| 重复项 | 位置 1 | 位置 2 | 重复程度 |
|---|---|---|---|
| Run 历史列表（含 KPI + 5 条 Recent Runs） | Workspace Overview | Report 列表 | **完全重复** |
| 全部 Result 表 | Run 详情 Results Tab | Report 列表 Run 表格 | 高度重复 |
| 失败原因为断言对比 | Run 详情 Failures Tab | FailureItem 详情 | 重复但粒度不同 |
| 状态码 / Method / Path / 耗时 / 错误 | Run 详情 Overview Tab | Result 详情 Overview Tab | 重复 |
| 通过 / 失败 / 错误 KPI | Workspace Overview | Report 列表 | 重复 |
| 执行 Drawer | Suite 详情按钮 | Case 编辑器按钮 | Run Center 表单 | Workspace Header | 同一组件四处入口，参数路径不一致 |
| 快速执行 Drawer 与 Run Center 表单 | Workspace 概览 Run | Run Center | 一致但来源不同 |

---

## 5. 企业产品评估

| 维度 | 评估 |
|---|---|
| 视觉与品牌 | 中等：色块 + Tabs + KPI 已有企业感，但缺少品牌定制（Logo / 主题色 / 多语言） |
| 权限模型 | 较弱：仅 superuser / Role 字串，缺 RBAC、审计、组织 / 团队 |
| 全局搜索 | 缺失：无法跨 Project 搜索 Run / Case / Suite |
| 通知 / 告警 | 缺失：无通知中心 / 邮件 / 飞书 / 钉钉集成 |
| 审计 / 操作日志 | 缺失：删除 / 修改 / 设默认 / 导入等操作无审计 |
| 性能 / 大数据 | 未验证：列表 50 条 / Case 1000 时是否仍流畅 |
| 多语言 | 缺失：仅有简体中文 |
| 备份 / 导出 | 缺失：项目 / Suite / Report 不可导出 / 备份 |
| 监控 / 运维 | 缺失：无健康检查 / 队列 / 调度后台任务视图 |

---

## 6. 修复优先级建议（按改动量 / 价值排序）

1. **H1 Project 切换 URL 重置**（1~2 天 / 极高价值）
2. **H2 统一 Execution 入口**（2~3 天 / 高价值）
3. **H3 拆分 Overview 报告区块 / Report 列表**（1~2 天 / 高价值）
4. **M2 Workspace 引导步骤动作化**（2~3 天 / 中价值）
5. **M4 Suite 列表摘要**（0.5 天 / 中价值）
6. **M5 OpenAPI 错误提示**（0.5 天 / 中价值）
7. **M6 Case 列表归属 + 返回路径**（1 天 / 中价值）
8. **M7 拆分 Run / Result Tab**（1 天 / 中价值）
9. **M9 Role 分组**（1 天 / 中价值）
10. **M10 全局搜索**（3~5 天 / 中长期）

---

## 7. 总结

平台整体功能闭环，UI 风格与状态管理成熟。主要 UX 风险集中在三点：

1. **Project 切换不重置上下文**（High）。
2. **执行入口与报告页面重复**（High）。
3. **Overview 与 Report 列表双重 KPI / 重复 Run 列表**（High）。

按 H → M → L 修复，可显著降低用户迷失感并提高企业级产品成熟度。
