# API 自动化测试平台 · UX Expert 走查 Review

> 文档类型：UX Expert 走查 Review（资深 UX 视角）
> 走查身份：模拟**第一次使用平台的测试工程师**
> 走查任务：完成 `Project → Environment → Import → Suite → Run → Report` 6 步主流程
> 评估维度：**学习成本 / 点击次数 / 重复操作 / 提示 / 空页面 / 错误恢复 / 效率**
> 严重等级：**High（阻塞主流程）/ Medium（影响效率）/ Low（细节优化）**
> 配套：`PRD.md`、`INFORMATION_ARCHITECTURE.md`、`PROJECT_WORKSPACE.md`、`NavigationUX.md`、`Journey.md`、`WorkflowReview.md`、`FirstRunGuide.md`、`EmptyState.md`、`QuickAction.md`、`Feedback.md`、`Recovery.md`

---

## 0. 走查方法

### 0.1 模拟身份

- **身份**：张三，某互联网公司测试工程师，3 年 API 测试经验
- **经验**：熟练使用 Postman / Apifox / JMeter，**第一次使用本平台**
- **预期**：30 分钟内完成"创建 Project → 导入 OpenAPI → 跑通第一条测试"
- **设备**：1440×900 桌面端，Chrome 浏览器

### 0.2 走查方法

1. **认知走查**（Cognitive Walkthrough）：每步问"用户的目标 / 能否成功 / 是否困惑"
2. **启发式评估**（Heuristic Evaluation）：对照 Nielsen 10 大启发式
3. **指标度量**：点击数 / 完成时间 / 错误次数

### 0.3 走查路径

```text
登录 → Dashboard → Project 列表 → 新建 Project → Workspace Overview
  → 环境管理 → 创建环境 → 设默认 → Suite 列表 → 创建 Suite
  → Suite 详情 → OpenAPI Import → 导入 → Case 列表
  → 执行中心 → Run Drawer → 执行 → Run 报告
  → 失败项 → Result 详情 → Case 编辑器 → 修复 → 再执行 → 新报告
```

---

## 1. 走查全程实录（按 6 步走查）

> 每步记录：**用户行为 / 思考 / 困惑 / 评估**

---

### Step 1 · 登录 + 进入 Dashboard

#### 用户行为

```text
1. 打开 https://platform.example.com/login
2. 输入邮箱 + 密码
3. 点击"登录"
4. 跳转 Dashboard
```

#### 用户思考

- ✅ 登录表单极简，邮箱 + 密码 + 按钮，**1 秒找到输入框**
- ✅ 登录成功跳转 Dashboard
- ⚠️ 不知道"我是谁"、"我有什么 Project"、"下一步该做什么"

#### 评估（学习成本 + 提示 + 空页面）

| 维度 | 评分 | 问题 |
|---|---|---|
| 学习成本 | ⭐⭐⭐⭐⭐ | 登录页极简，新用户无压力 |
| 点击次数 | ⭐⭐⭐⭐⭐ | 仅 3 次点击（输入邮箱 → 输入密码 → 登录） |
| 提示 | ⭐⭐ | Dashboard 是空页面（0 Project），**仅显示"推荐工作路径"教学卡**，但**无明确的下一步引导**（用户问"我该点哪个？"） |
| 空页面 | ⭐⭐ | Dashboard 空态**有卡片但无主操作按钮**，用户需要再点"Sider → 项目列表 → 新建 Project"3 步才能开始 |

#### 发现的问题

| ID | 等级 | 维度 | 问题描述 |
|---|:-:|---|---|
| **1-L1** | Medium | 提示 / 空页面 | Dashboard 无 Project 时**仅显示教学卡**，没有 **"📁 创建第一个 Project" 主按钮**，用户需在 Sider 找模块 |
| **1-L2** | Low | 学习成本 | 登录页无"忘记密码" / "申请账号"入口（企业级必备，但本期不做） |
| **1-L3** | Low | 提示 | 登录失败文案泛化（"账号或密码错误"），未区分"账号禁用 / 密码错误 / 请求过于频繁" |

---

### Step 2 · 新建 Project

#### 用户行为

```text
1. Sider → "项目" → 跳转 /projects
2. 点击"新建 Project"按钮
3. 填表：名称 = "用户服务 API"，描述（跳过）
4. 点击"创建"
5. 跳转到 Workspace Overview
```

#### 用户思考

- ✅ "新建 Project"按钮位置明显
- ⚠️ 表单中有"owner"字段，**用户不知道选谁**（其实是当前用户，但没说）
- ⚠️ 描述字段不知写什么（标签文字过简）
- ✅ 保存后自动跳转 Workspace

#### 评估（点击次数 + 提示 + 重复操作）

| 维度 | 评分 | 问题 |
|---|---|---|
| 点击次数 | ⭐⭐ | **6 步**：Sider → 项目列表 → 新建按钮 → 填名 → 创建 → 跳转 |
| 提示 | ⭐⭐ | 表单字段说明不足（owner / description） |
| 重复操作 | ⭐⭐⭐ | Dashboard 空态 + Project 列表空态 + Workspace Overview 引导卡**三处都提示"创建 Project"** |

#### 发现的问题

| ID | 等级 | 维度 | 问题描述 |
|---|:-:|---|---|
| **2-L1** | Medium | 点击次数 | 从 Dashboard "创建第一个 Project"需 **6 步**，应该有 Dashboard 引导卡 1 步直达 |
| **2-L2** | Medium | 提示 | ProjectFormModal 中 "owner" 字段隐藏当前用户，**新用户不知选了谁** |
| **2-L3** | Low | 重复操作 | 创建 Project 的引导在 Dashboard / 列表 / Overview **3 处重复**（仅 OK 可接受，但易混淆） |

---

### Step 3 · 创建 Environment

#### 用户行为

```text
1. 跳转 Workspace Overview
2. 看到资产计数：环境 0 / Suite 0 / Case 0
3. 看到引导步骤 1（创建环境）
4. Sider → Environment 模块
5. 点击"新建环境"
6. 填表：名称 / Base URL / Headers / Variables
7. 点击"创建"
8. 列表中点击"设为默认"
```

#### 用户思考

- ✅ 资产计数明确，新用户知道"还差什么"
- ⚠️ **Base URL 不知道填什么**（用户公司用 `https://api.example.com`，但没说是否需要带版本号）
- ⚠️ Headers / Variables 是 **JSON 编辑器**，新手看到一堆 `{}` 懵了
- ⚠️ **"设为默认"是额外一次点击**（Drawer 中有 Switch，但默认关闭）
- ✅ 设为默认后 Header 徽标更新（如果实现的话）

#### 评估（学习成本 + 点击次数 + 提示 + 重复操作）

| 维度 | 评分 | 问题 |
|---|---|---|
| 学习成本 | ⭐⭐ | **Base URL / Headers / Variables 三个概念对新手不友好**，需查文档 |
| 点击次数 | ⭐⭐ | **8 步**才能创建并设为默认环境 |
| 提示 | ⭐⭐ | Headers / Variables 编辑器是 JSON，新手需要手动编辑 JSON |
| 重复操作 | ⭐⭐ | 设默认是额外操作（应自动勾选） |

#### 发现的问题

| ID | 等级 | 维度 | 问题描述 |
|---|:-:|---|---|
| **3-L1** | **High** | 学习成本 | Headers / Variables JSON 编辑器**对新手不友好**，应默认键值表模式 |
| **3-L2** | **High** | 提示 | Base URL 字段**没有示例 / placeholder**，用户不知该填什么 |
| **3-L3** | Medium | 点击次数 | "设为默认"是**额外一次点击**，新建环境时**应自动勾选** |
| **3-L4** | Medium | 重复操作 | 创建环境引导在 Overview / Run Drawer / Environment 三处都有，**用户易混淆** |

---

### Step 4 · OpenAPI Import

#### 用户行为

```text
1. Sider → Suite 模块（创建 Suite）
2. 新建 Suite，名称 = "冒烟回归"
3. 进入 Suite 详情
4. 点击 "OpenAPI 导入"按钮
5. 选择"URL 来源"，输入 OpenAPI URL
6. 点击"预览"
7. 等待预览返回
8. 选择"导入"
9. 等待导入完成
10. 跳转 Suite 详情，看到导入的 Case
```

#### 用户思考

- ✅ Suite 详情顶部"OpenAPI 导入"按钮位置明显
- ⚠️ **Import 必须有 Suite**，但用户从 Project 维度进入时没有 Suite 上下文（已有 Step 4 调整）
- ⚠️ 预览阶段**没有冲突策略说明**，用户不知 skip / overwrite 的差异
- ⚠️ 导入完成后**必须手动返回 Suite**，没有"自动跳回"按钮
- ✅ 导入成功后看到 N 条 Case 创建

#### 评估（学习成本 + 点击次数 + 提示）

| 维度 | 评分 | 问题 |
|---|---|---|
| 学习成本 | ⭐⭐⭐ | 导入流程较清晰，但 skip/overwrite 概念需要解释 |
| 点击次数 | ⭐⭐⭐ | **10 步**才能完成导入 |
| 提示 | ⭐⭐ | 冲突策略 / 名称前缀 / 标签过滤**一次性给出，新手懵** |
| 空页面 | ⭐⭐ | 导入失败时**错误信息模糊**（"预览功能不可用"） |

#### 发现的问题

| ID | 等级 | 维度 | 问题描述 |
|---|:-:|---|---|
| **4-L1** | Medium | 提示 | OpenAPI Import **入口分散**在 Suite 详情 / Case 列表，新用户不知从哪进 |
| **4-L2** | Medium | 提示 | 冲突策略 **skip / overwrite 默认值非最优**，且无解释 |
| **4-L3** | Medium | 重复操作 | 导入完成后**必须手动返回 Suite**，应自动跳回 |
| **4-L4** | Medium | 错误恢复 | `preview_id` 不可用时**错误信息模糊**（"预览功能不可用"），企业用户误以为系统故障 |
| **4-L5** | Low | 学习成本 | Suite 必须先创建才能 Import，**Order 不直观** |

---

### Step 5 · 创建 / 选择 Suite

> 用户在 Step 4 已经创建了 Suite 用于 Import，此步验证 Suite 流程。

#### 用户行为

```text
1. Suite 详情顶部点击"新建 Suite"按钮
2. 填表：名称 / 描述
3. 保存
4. 回到 Suite 列表
```

#### 用户思考

- ✅ 流程顺畅
- ⚠️ Suite **描述字段不知写什么**
- ⚠️ 列表信息密度低（仅名称 / 描述 / 时间，看不到 Case 数 / 通过率）

#### 评估（提示 + 效率）

| 维度 | 评分 | 问题 |
|---|---|---|
| 提示 | ⭐⭐ | 描述字段无 placeholder |
| 效率 | ⭐⭐ | Suite 列表**无法快速判断该 Suite 是否重要**（Case 数 / 通过率） |

#### 发现的问题

| ID | 等级 | 维度 | 问题描述 |
|---|:-:|---|---|
| **5-L1** | Medium | 效率 | Suite 列表**缺 Case 数 / 最近通过率 / 上次执行时间**，用户必须进入详情才能判断 |
| **5-L2** | Low | 提示 | Suite 描述字段无 placeholder 引导 |

---

### Step 6 · 执行 Run

#### 用户行为

```text
1. Suite 详情点击"执行 Suite"按钮
2. 跳转到 Run 中心
3. 重新选择 scope=collection + suiteId
4. 选择环境
5. 点击"Run Now"
6. 等待执行
7. 自动跳转 Run 报告详情
```

#### 用户思考

- ✅ "执行 Suite"按钮明显
- ⚠️ **点击"执行 Suite"后跳到 Run 中心**，不是直接打开 Drawer（**2 次跳转**）
- ⚠️ Run 中心**重复选择 scope**（已知是 collection，为什么还要选？）
- ⚠️ **Variables 字段是只读**，要修改必须去 Environment 模块
- ✅ 执行完成后自动跳 Report

#### 评估（点击次数 + 重复操作 + 效率）

| 维度 | 评分 | 问题 |
|---|---|---|
| 点击次数 | ⭐⭐ | **8 步**才能跑一次 Suite |
| 重复操作 | ⭐⭐ | "选择 scope"是**冗余操作**（已知 scope=collection） |
| 效率 | ⭐⭐ | Suite 详情"执行 Suite"按钮跳 Run 中心是**多余的跳转** |

#### 发现的问题

| ID | 等级 | 维度 | 问题描述 |
|---|:-:|---|---|
| **6-L1** | **High** | 重复操作 | Suite 详情"执行 Suite"跳 Run 中心，**2 次跳转才到 Drawer** |
| **6-L2** | **High** | 重复操作 | 四处执行入口不一致（Suite / Case / Header / Run Center），参数路径不同 |
| **6-L3** | Medium | 重复操作 | Run Drawer 中 scope 需手动选择，**应自动锁定** scope=collection+suiteId |
| **6-L4** | Medium | 重复操作 | Run Center "最近 Run"区与 Workspace Overview "最近 Run"**完全重复** |
| **6-L5** | Medium | 提示 | Run Drawer Variables 只读，**修改需跨页面** |
| **6-L6** | Low | 错误恢复 | Run 执行失败时按钮立即恢复，**用户可能没看清错误信息** |

---

### Step 7 · 查看 Report + 修复失败

#### 用户行为

```text
1. Run 报告详情默认 Tab = 概览
2. 切换到"失败原因"Tab
3. 点击失败项，进入 Result 详情
4. 点击"修改 Case 定义"
5. 跳到 Case 编辑器
6. 修改 Case 配置
7. 点击"保存"
8. 回到 Case 列表（不在 Suite 详情！）
9. 再次点击"执行 Suite"
10. 选择 scope / 环境
11. Run Now
12. 跳新报告
```

#### 用户思考

- ✅ Run 报告 KPI 清晰（通过率 / 耗时 / 失败数）
- ⚠️ 默认 Tab = 概览，但用户更关心"失败在哪"—— **应默认失败原因 Tab**
- ⚠️ 失败项**无法直接看到断言详情**（折叠），必须点进 Result
- ✅ Result 详情有请求 / 响应 / 断言快照
- ⚠️ **Case 编辑器返回丢失 Suite 上下文**（返回 Case 列表，不是 Suite 详情）
- ⚠️ 修改 Case 后必须**手动回到 Suite 详情**，再点"执行 Suite"

#### 评估（点击次数 + 上下文丢失 + 效率 + 错误恢复）

| 维度 | 评分 | 问题 |
|---|---|---|
| 点击次数 | ⭐ | **12 步**才能完成"修复 1 条失败" |
| 上下文丢失 | ⭐ | **Case 编辑器返回丢失搜索状态 + 来源 Suite** |
| 效率 | ⭐ | 修改 Case 后必须手动回到 Suite / 再选 scope |
| 错误恢复 | ⭐⭐ | Result 详情"跳 Case 编辑器"按钮带 `?from=report` 但**Case 编辑器忽略** |

#### 发现的问题

| ID | 等级 | 维度 | 问题描述 |
|---|:-:|---|---|
| **7-L1** | **High** | 上下文丢失 | **Case 编辑器返回丢失 Suite 上下文**，跳到 Case 列表（不在 Suite 详情） |
| **7-L2** | **High** | 上下文丢失 | **Case 列表搜索 / 筛选 / 分页全部丢失**（未入 URL Query） |
| **7-L3** | **High** | 上下文丢失 | **Result 详情→Case 编辑器→返回**丢失 `?from=report&runId=&resultId=` |
| **7-L4** | Medium | 重复操作 | 失败原因 Tab **默认折叠** expected/actual，用户必须点开看 |
| **7-L5** | Medium | 提示 | Run 详情 **默认 Tab = 概览**，但用户更关心失败 |
| **7-L6** | Medium | 重复操作 | Run 详情"全部 Result Tab" + Result 详情"请求/响应 Tab"**数据重复** |
| **7-L7** | Medium | 重复操作 | 修改 Case 后**没有"保存并执行"按钮**，必须再点执行 |
| **7-L8** | Medium | 重复操作 | **Report 列表 + Overview "最近 Run"区完全重复** |

---

## 2. 问题清单（按严重程度分类）

### 2.1 High 级（阻塞主流程 / 严重迷失）

| ID | 等级 | 维度 | 位置 | 问题 | 修复方案 |
|---|:-:|---|---|---|---|
| **H1** | **High** | 学习成本 | Environment Drawer | **Headers / Variables 是 JSON 编辑器**，新手懵 | 改为键值表模式（key/value 两列 + +按钮） |
| **H2** | **High** | 提示 | Environment Drawer | **Base URL 字段无示例 / placeholder** | 加 placeholder + 帮助 tooltip |
| **H3** | **High** | 重复操作 | Suite 详情"执行 Suite" | **跳 Run Center 是 2 次跳转**，应直开 Drawer | 直接调用 `RunExecutionDrawer`，跳过 Run Center |
| **H4** | **High** | 重复操作 | Run Center / Suite / Case / Header | **四处执行入口不一致** | 统一为 Drawer 入口，删除 Run Center 表单 |
| **H5** | **High** | 上下文丢失 | Case 编辑器返回 | **丢失 Suite 上下文 + 搜索/筛选/分页** | URL Query 持久化 + 读 `?returnTo=` |
| **H6** | **High** | 上下文丢失 | Result → Case 编辑器 | **丢失 from/runId/resultId 上下文** | Case 编辑器 onSuccess 读 `?returnTo=` |
| **H7** | **High** | 提示 | Dashboard 0 Project | **Dashboard 教学卡无主操作按钮**，用户不知点哪 | Dashboard 加"📁 创建第一个 Project"主按钮 |
| **H8** | **High** | 空页面 | Dashboard 0 Project | **Dashboard 空态无明确下一步**，3 步冗余 | Dashboard 主按钮 1 步打开 ProjectFormModal |

### 2.2 Medium 级（影响效率 / 清晰度）

| ID | 等级 | 维度 | 位置 | 问题 | 修复方案 |
|---|:-:|---|---:|---|---|
| **M1** | Medium | 重复操作 | Overview + Report 列表 | **"最近 Run"区块完全重复** | Overview 限 Top 3 + "查看全部"，Report 列表做完整 |
| **M2** | Medium | 重复操作 | Run 详情 + Result 详情 | **Tab 数据重复** | 精简 Run 详情"全部 Result Tab"，详情仅在 Result |
| **M3** | Medium | 提示 | Run 详情 | **默认 Tab = 概览**，用户更关心失败 | 默认 Tab = 失败原因（若有 failed/error） |
| **M4** | Medium | 提示 | 失败原因 Tab | **expected/actual 折叠** | 默认展开（前 80 字符） |
| **M5** | Medium | 点击次数 | Case 编辑器 | **没有"保存并执行"按钮** | Case 编辑器增加 "💾 保存并执行" 副按钮 |
| **M6** | Medium | 点击次数 | Run 详情 | **没有"再次执行"按钮**，必须回 Run 中心 | Run 详情增加"▶️ 再次执行"按钮 |
| **M7** | Medium | 点击次数 | Run 详情 | **没有"修复第一条失败"按钮** | 增加"🔧 修复 3 条失败"按钮，1 步跳 |
| **M8** | Medium | 提示 | ProjectFormModal | **"owner"字段隐藏当前用户，新用户不知选了谁** | Drawer 顶部显示"将以当前用户 [name] 创建" |
| **M9** | Medium | 点击次数 | Environment Drawer | **"设为默认"是额外点击**，应自动勾选 | 新建环境 Drawer 默认勾选 is_default |
| **M10** | Medium | 重复操作 | 创建环境引导 | Overview / Run Drawer / Environment 三处引导 | Environment 列表顶部主引导，其他地方弱化 |
| **M11** | Medium | 重复操作 | Run Drawer | **scope 需手动选择** | Suite 详情触发时锁定 scope=collection+suiteId |
| **M12** | Medium | 提示 | OpenAPI Import | **冲突策略默认值非最优** | 默认 skip + 高级设置折叠 |
| **M13** | Medium | 重复操作 | OpenAPI Import | **导入完成后需手动返回 Suite** | 自动 navigate 回 Suite 详情 |
| **M14** | Medium | 错误恢复 | OpenAPI Import | **`preview_id` 不可用时错误信息模糊** | 错误信息分三档（preview_id / OpenAPI 版本 / 其他） |
| **M15** | Medium | 提示 | OpenAPI Import | **入口分散**（Suite / Case 列表都有） | 统一为 Suite 详情顶部主操作 |
| **M16** | Medium | 效率 | Suite 列表 | **缺 Case 数 / 最近通过率** | 列表行新增列"Case 数 / 通过率 / 上次执行时间" |
| **M17** | Medium | 提示 | Environment Drawer | **Headers / Variables 键值表模式** | 默认表模式 + JSON 模式切换按钮 |
| **M18** | Medium | 提示 | Run Drawer | **Variables 只读，修改需跨页面** | Drawer 顶部 Tag 显示 Variables 摘要 + 提示去 Environment |
| **M19** | Medium | 上下文 | Project 切换 | **URL 中 runId/caseId 残留** | 实施三层切换策略（A/B/C） |
| **M20** | Medium | 提示 | Drawer / Modal | **Back 行为不一致**（Drawer 是 Portal，Back 无反应） | Drawer 关闭时 push `?drawer=closed` 或拦截 popstate |

### 2.3 Low 级（细节优化）

| ID | 等级 | 维度 | 位置 | 问题 | 修复方案 |
|---|:-:|---|---:|---|---|
| **L1** | Low | 提示 | Login | **登录失败文案泛化** | 区分账号禁用 / 密码错误 / 请求过于频繁 |
| **L2** | Low | 学习成本 | Login | **无"忘记密码"入口** | 后期加（本期不做） |
| **L3** | Low | 提示 | Dashboard 教学卡 | **对老用户长期显示** | 引导完成后自动消失 |
| **L4** | Low | 提示 | ProjectFormModal | **描述字段无 placeholder** | 加 placeholder + "?"图标 |
| **L5** | Low | 提示 | SuiteFormModal | **描述字段无 placeholder** | 同上 |
| **L6** | Low | 提示 | Environment Drawer | **设默认环境后 Header 徽标不实时刷新** | 列表"设为默认"成功后调 `refresh()` |
| **L7** | Low | 提示 | Drawer / Modal | **关闭 Drawer 时不创建 history 记录**，Back 键无反应 | Drawer 关闭时 push history |
| **L8** | Low | 重复操作 | Overview + Run Center | **最近 Run 区块重复** | 移除 Run Center 区块 |
| **L9** | Low | 提示 | 失败 Tab | **error_code 信息缺失** | 失败行增加 error_code 列 |
| **L10** | Low | 提示 | Environment Drawer | **删除时无引用次数提示** | Popconfirm 加"该环境已被 N 个 Run 引用" |
| **L11** | Low | 提示 | Result 详情 | **5 个 Tab 无默认引导** | Tab 默认规则 + 建议标识 |
| **L12** | Low | 提示 | Case 编辑器 | **"保存并执行"是隐藏次操作** | 主操作应是"保存并执行"（冒烟场景下） |
| **L13** | Low | 提示 | Workspace Header | **缺 Project 状态徽标** | Header 显示"资产齐全 / 缺环境 / 缺 Suite"徽标 |
| **L14** | Low | 提示 | Suite 详情排序 | **行内"上移 / 下移"按钮全表 loading** | Table 不传 loading，仅按钮 loading |
| **L15** | Low | 错误恢复 | 失败 Toast | **错误 Toast 仅 5 秒，长错误信息看不清** | 错误信息 > 50 字用 Notification |
| **L16** | Low | 提示 | Login | **登录成功后落点单一** | 登录后判断 Recent Project → 1 步进概览 |
| **L17** | Low | 错误恢复 | 403 错误页 | **不区分路由级 / 资源级 / 操作级** | 三种 403 用不同组件 + 文案 |
| **L18** | Low | 提示 | Drawer 内表单 | **错误信息不包含 request_id** | 错误信息统一格式：主标题 + 详情 + 错误码 + request_id |

---

## 3. 按 7 个评估维度汇总

### 3.1 学习成本（Learning Cost）

| 等级 | 数量 | 主要问题 |
|---|:-:|---|
| High | 2 | JSON 编辑器门槛 / Base URL 无示例 |
| Medium | 3 | Skip/Overwrite 概念 / 404 vs Dashboard 跳转 / Owner 字段隐藏 |
| Low | 2 | 描述字段无 placeholder / 403 不区分级别 |

**核心症结**：新手最易卡在 **Environment 创建**（Headers / Variables 概念）和 **OpenAPI Import**（冲突策略）。

### 3.2 点击次数（Click Count）

| 等级 | 数量 | 主要问题 |
|---|:-:|---|
| High | 3 | Dashboard 创建 Project 6 步 / Case 编辑器返回丢上下文 / Result 跳 Case 丢上下文 |
| Medium | 4 | Run 详情无"再次执行" / 无"修复失败" / Drawer 跳转 2 次 / Case 编辑器无"保存并执行" |
| Low | 2 | 登录落点单一 / 重复 Run 区块 |

**核心症结**：**首次跑通需要 ~18 次点击**（理想 ≤ 10 次），主要冗余在 ① Dashboard 创建 Project 路径 ② Case 编辑器返回路径 ③ Run 详情修复失败路径。

### 3.3 重复操作（Repeated Operations）

| 等级 | 数量 | 主要问题 |
|---|:-:|---|
| High | 3 | 四处执行入口 / Suite 跳 Run Center / Case 编辑器返回跳错 |
| Medium | 5 | Overview + Report 重复 / Run + Result Tab 重复 / Run Center + Overview 重复 / Run Drawer scope 重选 / OpenAPI 手动返回 |
| Low | 1 | Run Center 与 Overview 最近 Run 重复 |

**核心症结**：**信息重复面积大**（同一份数据在 Overview / Report / Run Center 3 处展示）。

### 3.4 提示（Hints）

| 等级 | 数量 | 主要问题 |
|---|:-:|---|
| High | 2 | Dashboard 无主操作按钮 / Base URL 无示例 |
| Medium | 5 | 失败 Tab 折叠 / Run 详情默认 Tab / Owner 字段隐藏 / OpenAPI 冲突策略 / 错误 Toast 5 秒太短 |
| Low | 5 | 描述无 placeholder / 失败无 error_code / Result Tab 无引导 / Header 缺状态徽标 / 登录失败文案 |

**核心症结**：**新手进入 Dashboard 不知该做什么**（无主操作按钮），**失败时不知为什么失败**（错误信息不完整）。

### 3.5 空页面（Empty Pages）

| 等级 | 数量 | 主要问题 |
|---|:-:|---|
| High | 1 | Dashboard 0 Project 无明确下一步 |
| Medium | 1 | OpenAPI Import 预览为空时无引导 |
| Low | 0 | （Run / Report 等空态已有 FirstRunGuide / EmptyState 规范） |

**核心症结**：**Dashboard 空态"教学卡"不够直接**——用户需要再点 Sider 才能开始，应**主按钮 1 步直达**。

### 3.6 错误恢复（Error Recovery）

| 等级 | 数量 | 主要问题 |
|---|:-:|---|
| High | 0 | （大部分错误有重试按钮） |
| Medium | 2 | OpenAPI 错误信息模糊 / Case 编辑器忽略 from 上下文 |
| Low | 3 | Drawer 失败 Toast 太短 / 错误不暴露 request_id / 403 不区分级别 |

**核心症结**：**错误信息缺少企业级排查线索**（错误码 + request_id），**Drawer / Modal 失败时易丢失用户输入**。

### 3.7 效率（Efficiency）

| 等级 | 数量 | 主要问题 |
|---|:-:|---|
| High | 0 | （同上） |
| Medium | 3 | Run 详情无快捷再执行 / Suite 列表缺信息密度 / Run 详情无快捷修复 |
| Low | 1 | Overview + Run Center 最近 Run 重复 |

**核心症结**：**"修复 1 条失败"需 12 步**，应有"▶️ 再次执行"和"🔧 修复第一条失败"按钮降至 3 步。

---

## 4. 整体评估

### 4.1 整体评级（按维度）

| 维度 | 评级 | 说明 |
|---|---|---|
| 学习成本 | ⭐⭐⭐ 中 | 概念清晰，但 Headers/Variables / 冲突策略需查文档 |
| 点击次数 | ⭐⭐ 差 | ~18 步跑通主流程，应 ≤ 10 步 |
| 重复操作 | ⭐⭐ 差 | 信息重复面积大，执行入口分裂 |
| 提示 | ⭐⭐⭐ 中 | 大部分提示清晰，但 Dashboard / Base URL 等关键节点不足 |
| 空页面 | ⭐⭐⭐ 中 | Empty State 已有规范，但 Dashboard 缺主按钮 |
| 错误恢复 | ⭐⭐⭐⭐ 良 | 大部分错误有重试，仅个别信息不完整 |
| 效率 | ⭐⭐ 差 | 缺少快捷操作（再次执行 / 修复失败） |

**整体评级**：⭐⭐⭐ **中** —— 功能闭环完成，但 **效率与重复操作是主要短板**，需 P0 修复。

### 4.2 三大核心问题

1. **执行入口分裂**（H3+H4）—— 4 个入口，2 次跳转，参数路径不一致
2. **上下文丢失严重**（H5+H6）—— Case 编辑器返回 + Result 跳 Case 返回都丢上下文
3. **信息重复面积大**（M1+M2+L8）—— KPI / Run 列表 / Tab 数据在 3 处展示

### 4.3 三大优先修复

| 优先级 | 问题 | 修复策略 | 估时 |
|:-:|---|---|:-:|
| P0 | **执行入口分裂** | 统一 Drawer 入口，删除 Run Center 表单 | 2 天 |
| P0 | **上下文丢失** | URL Query 持久化 + `useUrlQueryState` Hook | 2 天 |
| P0 | **Case 编辑器返回路径** | `?returnTo=` + 编辑器 onSuccess 读取 | 1 天 |
| P1 | **Overview + Report 重复** | Overview 限 Top 3 + "查看全部"，Report 列表完整 | 1 天 |
| P1 | **Dashboard 空态** | 教学卡 + 主操作按钮（1 步创建 Project） | 0.5 天 |
| P1 | **Environment Headers/Variables** | 键值表模式 + JSON 模式切换 | 1 天 |
| P2 | **OpenAPI 错误信息** | 错误信息分档 + overwrite 二次确认 | 1 天 |

---

## 5. 与既有文档的关系

| 本文档 | 与既有文档的对应 |
|---|---|
| §1 Step 1~7 走查实录 | `Journey.md` ① 新用户 Journey（流程视角） |
| §2 问题清单 | `WorkflowReview.md` §2~3（已识别 H1~H6 + M1~M20） |
| §3 七维度评估 | `EmptyState.md`（空页面）/ `Feedback.md`（提示）/ `Recovery.md`（错误恢复）/ `QuickAction.md`（效率） |
| §4 整体评级 | 整合上述 7 个文档的结论 |

**结论**：本文档是**资深 UX Expert 的"端到端走查"**，与其他产品文档（Journey / WorkflowReview / FirstRunGuide / EmptyState / QuickAction / Feedback / Recovery / NavigationUX）形成完整的产品 UX 闭环。本文档提供**优先级排序与实施序列**，其他文档提供**具体修复策略**。

---

## 6. 验收指标（修复后）

| 指标 | 计算方式 | 当前 | 目标 |
|---|---|---|---|
| 首次跑通主流程点击数 | Step 1~6 总点击数 | ~18 | **≤ 10** |
| 首次跑通主流程耗时 | 登录 → Run 报告 | ~30 分钟 | **≤ 8 分钟** |
| 修复 1 条失败点击数 | Run 详情 → 修改 Case → 再执行 | ~12 | **≤ 3** |
| 学习成本（新手调研） | 用户首次使用完成率 | — | ≥ 80% |
| 空页面明确下一步率 | 空态含主操作按钮 | — | **100%** |
| 错误恢复路径完整率 | 错误状态含"重试 / 返回"按钮 | — | **100%** |
| 信息重复面积（重复展示同一数据的位置数） | — | 3 | ≤ 1 |
| 上下文丢失次数 | 编辑 / Drawer 返回后丢失 URL Query | 高 | **0** |

---

## 7. 不在范围

- ❌ 视觉设计 / 配色 / 字体（属于 DesignSystem 范畴）
- ❌ 后端 API / 数据库 / 性能（属于技术范畴）
- ❌ 移动端 / 平板适配（本期仅桌面端）
- ❌ 多语言 / i18n（本期仅简体中文）

---

## 8. 文档约束再确认

- ✅ 不新增任何后端 API
- ✅ 不新增任何数据库表 / 字段 / 迁移
- ✅ 不新增任何功能模块
- ✅ 所有问题均可通过**前端组件 + 路由 + URL Query + LocalStorage + 已有 Ant Design 组件**修复
- ✅ 18 项 High / Medium / 5 项 Low 问题**全部**已有对应修复策略（在其他 7 个文档中）

---

> **版本**：v1.0 · 2026-07-16
> **作者**：资深 UX Expert
> **走查身份**：第一次使用平台的测试工程师
> **范围**：MVP 阶段首次使用全流程；定时 / 通知 / AI 场景不在本期范围
> **配套使用**：`PRD.md` → `Journey.md` → `WorkflowReview.md` → `FirstRunGuide.md` → `EmptyState.md` → `NavigationUX.md` → `QuickAction.md` → `Feedback.md` → `Recovery.md` → `UXReview.md`（本文档：UX Expert 走查）