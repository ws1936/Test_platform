# API 自动化测试平台 · Design System

> 版本：v1.0  
> 适用范围：API 自动化测试平台前端（React 18 + Ant Design 5.x）  
> 设计目标：统一视觉语言、降低实现歧义、提升团队协作效率  
> 约束边界：**仅规范视觉与组件用法，不修改任何业务、不新增 API、不改动数据库**

---

## 0. 设计原则

| 原则 | 说明 |
|---|---|
| **单一真相源** | 所有 Token 集中维护，组件不直接写色值 / 字号 / 间距 |
| **与 Ant Design 同构** | 复用 AntD 5 的 Design Token 体系，本系统在 Token 之上做语义层封装 |
| **业务优先** | 视觉服务业务场景：Dashboard / Workspace / Report 各自有节奏，但共享基底 |
| **可降级** | 任意 Token 缺失时，使用 AntD 默认值，不破坏可访问性 |
| **可演进** | Token 通过 CSS 变量暴露，未来支持运行时主题切换 |

---

## ① Color Token · 颜色系统

### 1.1 品牌色（Brand）

| Token | Hex | 用途 |
|---|---|---|
| `--brand-primary` | `#315EFB` | 主操作色、链接、聚焦态 |
| `--brand-primary-hover` | `#1F4AE8` | 主按钮 hover |
| `--brand-primary-active` | `#163DC4` | 主按钮 active |
| `--brand-secondary` | `#7448FF` | 渐变副色、辅助强调 |
| `--brand-gradient` | `linear-gradient(135deg, #315EFB 0%, #7448FF 100%)` | Logo / Workspace Header / 强调区块 |

### 1.2 语义色（Semantic）

| Token | Hex | AntD Alias | 用途 |
|---|---|---|---|
| `--color-primary` | `#315EFB` | `colorPrimary` | 主操作、链接 |
| `--color-success` | `#16A34A` | `colorSuccess` | 通过 / 完成 / 启用 |
| `--color-warning` | `#FAAD14` | `colorWarning` | 警告、跳过、提示 |
| `--color-danger` | `#DC2626` | `colorError` | 错误、删除、断言失败、执行错误 |
| `--color-info` | `#0EA5E9` | `colorInfo` | 进行中、信息提示 |

**辅助色阶**（基于 `antd` 的 `colorPrimaryBg / colorPrimaryBgHover / colorPrimaryBorder` 自动生成）。

### 1.3 中性色（Neutral）

| Token | Hex | 用途 |
|---|---|---|
| `--text-primary` | `#172033` | 标题、正文主色 |
| `--text-secondary` | `#778097` | 次级文本、说明 |
| `--text-tertiary` | `#929AAB` | 辅助、Hint |
| `--text-disabled` | `#C2C8D2` | 禁用态文本 |
| `--text-inverse` | `#FFFFFF` | 深色背景反白文字 |

| Token | Hex | 用途 |
|---|---|---|
| `--bg-page` | `#F5F7FB` | 页面背景 |
| `--bg-surface` | `#FFFFFF` | 卡片 / 弹层背景 |
| `--bg-muted` | `#F7F9FC` | 弱化背景（Dashboard Hint、Metric Box） |
| `--bg-overlay` | `rgba(15, 23, 42, 0.45)` | Drawer / Modal 遮罩 |

### 1.4 边框与分割

| Token | Hex | 用途 |
|---|---|---|
| `--border-default` | `#EDF0F5` | 卡片、表单、分割线 |
| `--border-strong` | `#D9DEE7` | 强调边框、激活态 |
| `--border-danger` | `#FFCCC7` | 危险区域边框（删除卡片等） |
| `--divider` | `#EDF0F5` | 列表 / 内容分隔 |

### 1.5 CSS 变量定义

```css
/* frontend/src/styles.css —— 追加 :root 设计 Token */
:root {
  /* Brand */
  --brand-primary: #315efb;
  --brand-primary-hover: #1f4ae8;
  --brand-primary-active: #163dc4;
  --brand-secondary: #7448ff;
  --brand-gradient: linear-gradient(135deg, #315efb 0%, #7448ff 100%);

  /* Semantic */
  --color-primary: #315efb;
  --color-success: #16a34a;
  --color-warning: #faad14;
  --color-danger:  #dc2626;
  --color-info:    #0ea5e9;

  /* Neutral - Text */
  --text-primary:   #172033;
  --text-secondary: #778097;
  --text-tertiary:  #929aab;
  --text-disabled:  #c2c8d2;
  --text-inverse:   #ffffff;

  /* Neutral - Surface */
  --bg-page:     #f5f7fb;
  --bg-surface:  #ffffff;
  --bg-muted:    #f7f9fc;
  --bg-overlay:  rgba(15, 23, 42, 0.45);

  /* Border */
  --border-default: #edf0f5;
  --border-strong:  #d9dee7;
  --border-danger:  #ffccc7;
  --divider:        #edf0f5;
}
```

### 1.6 AntD 5 Theme 配置

```tsx
// frontend/src/main.tsx —— 在 <ConfigProvider> 中注入 Token
import { ConfigProvider, theme } from "antd";

<ConfigProvider
  theme={{
    algorithm: theme.defaultAlgorithm,
    token: {
      colorPrimary: "#315EFB",
      colorSuccess: "#16A34A",
      colorWarning: "#FAAD14",
      colorError:   "#DC2626",
      colorInfo:    "#0EA5E9",
      colorTextBase: "#172033",
      colorBgLayout: "#F5F7FB",
      colorBorder:   "#EDF0F5",
      borderRadius: 8,
      fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
    },
    components: {
      Layout: {
        siderBg: "#ffffff",
        headerBg: "rgba(255,255,255,0.92)",
      },
      Card: { borderRadiusLG: 12 },
      Tag:   { defaultBg: "#F7F9FC" },
    },
  }}
>
  <App />
</ConfigProvider>
```

### 1.7 颜色使用守则

1. **永远不使用业务文案描述颜色**（禁止"蓝色按钮""红色提示"）。
2. **Status 语义必须映射到 Semantic Token**（passed→success / failed→danger / error→danger / skipped→warning / running→info / pending→text-tertiary）。
3. **文字与背景对比度 ≥ 4.5:1**（WCAG AA）。
4. **禁止硬编码 Hex** 在业务组件中，统一通过 Token 引用。

---

## ② Typography · 字体系统

### 2.1 字体栈

```css
--font-sans: Inter, "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
--font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
```

### 2.2 类型阶梯（Type Scale）

| Token | Size | Line Height | Weight | Letter Spacing | 用途 |
|---|---:|---:|---:|---:|---|
| **H1** | 32 px | 40 px | 700 | -0.5 px | 登录主标题、Empty / Error 全屏标题 |
| **H2** | 24 px | 32 px | 700 | -0.5 px | PageHeader 主标题、Dashboard 指标值 |
| **H3** | 20 px | 28 px | 600 | -0.3 px | Card 标题、Sider 分组标题 |
| **H4** | 17 px | 24 px | 600 | -0.2 px | 弹窗标题、Section 标题 |
| **Body Large** | 16 px | 24 px | 400 | 0 | 长正文、描述 |
| **Body** | 14 px | 22 px | 400 | 0 | 默认正文、表格单元格 |
| **Body Strong** | 14 px | 22 px | 600 | 0 | 表格内强调、表格链接 |
| **Caption** | 13 px | 20 px | 400 | 0 | Hint、辅助说明、表单说明 |
| **Caption Small** | 12 px | 18 px | 400 | 0 | Tag、时间戳、Hint |
| **Caption Tiny** | 11 px | 16 px | 500 | 0.4 px | Eyebrow、All-Caps 分组标签 |

### 2.3 在 AntD 中的映射

```tsx
<Typography.Title level={1}>H1 · 32/40 · 700</Typography.Title>
<Typography.Title level={2}>H2 · 24/32 · 700</Typography.Title>
<Typography.Title level={3}>H3 · 20/28 · 600</Typography.Title>
<Typography.Title level={4}>H4 · 17/24 · 600</Typography.Title>
<Typography.Text>Body · 14/22 · 400</Typography.Text>
<Typography.Text strong>Body Strong</Typography.Text>
<Typography.Text type="secondary">Caption · 13/20</Typography.Text>
<Typography.Text className="text-caption-small">Caption Small</Typography.Text>
```

### 2.4 排版规则

1. **标题层级在一屏内不超过 3 级**（H1 → H3 之后直接走 Body Strong）。
2. **表格内不使用 Typography.Title**，避免破坏行高节奏；用 `strong` + 字号控制。
3. **数字、路径、JSON 一律使用 `font-mono`**，等宽对齐。
4. **中英文混排时** 中文优先使用 PingFang SC；英文优先 Inter。

---

## ③ Spacing · 间距系统

### 3.1 间距阶梯（4 的倍数）

| Token | Value | 典型场景 |
|---|---:|---|
| `space-1` | **4** px | Tag 内边距、Icon 与文字间距、行内紧凑间距 |
| `space-2` | **8** px | 按钮内边距、Tag 间距、表单字段间距 |
| `space-3` | **12** px | 段落紧凑间距、Card 内紧凑布局、Toolbar 子项间距 |
| `space-4` | **16** px | 卡片内主间距、表单字段间距、Drawer 表单垂直节奏 |
| `space-6` | **24** px | Section 间距、Card 之间间距、Modal 表单分段 |
| `space-8` | **32** px | 区块间距、PageHeader 下方、内容主外边距 |
| `space-12` | **48** px | 大区块分隔、全屏 Empty / Error 上下留白 |

### 3.2 CSS 变量

```css
:root {
  --space-1:  4px;
  --space-2:  8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
}
```

### 3.3 间距语义映射

| 场景 | 推荐 Token |
|---|---|
| Toolbar / Form 内子元素横向 gap | `space-2` (8) |
| Form.Item 之间 | `space-3` (12) |
| Card 内主内容 padding | `space-6` (24) |
| Card 之间 gap | `space-6` (24) |
| 页面主内容 padding | `space-8` (32) |
| Section 之间 | `space-8` (32) |
| 全屏 Empty / Error padding | `space-12` (48) |

### 3.4 使用守则

1. **禁止使用任意 px 间距**（如 13px、17px、20px）；只能从 7 个 Token 中取。
2. **AntD Space 组件** `<Space size={8}>` 与 Token 一致；纵向间距使用 `direction="vertical"` + `size`。
3. **Grid gutter** 优先使用 16 / 24，不要使用 20 / 32 之外的奇数。

---

## ④ Radius · 圆角系统

### 4.1 圆角阶梯

| Token | Value | 用途 |
|---|---:|---|
| `--radius-none` | 0 px | 分隔线、严格矩形 |
| `--radius-sm` | **4** px | Tag、小型 Chip |
| `--radius-md` | **8** px | 按钮、输入框、Tag、Card（默认） |
| `--radius-lg` | **12** px | 卡片、Drawer 头部 |
| `--radius-xl` | **14** px | Workspace Header / Card（强调） |
| `--radius-2xl` | **18** px | 登录视觉装饰、特殊强调容器 |
| `--radius-full` | 9999 px | 圆形头像、状态点 |

### 4.2 圆角语义

| 组件 | 默认 Radius |
|---|---|
| Button | `--radius-md` (8) |
| Input / Select / TextArea | `--radius-md` (8) |
| Tag | `--radius-sm` (4) |
| Card | `--radius-lg` (12) |
| Drawer | `--radius-lg` (12) 仅顶部 |
| Modal | `--radius-lg` (12) |
| Workspace Header | `--radius-xl` (14) |
| Avatar | `--radius-full` |

### 4.3 CSS 变量

```css
:root {
  --radius-none: 0px;
  --radius-sm:   4px;
  --radius-md:   8px;
  --radius-lg:  12px;
  --radius-xl:  14px;
  --radius-2xl: 18px;
  --radius-full: 9999px;
}
```

---

## ⑤ Shadow · 阴影系统

### 5.1 阴影阶梯

| Token | Value | 用途 |
|---|---|---|
| `--shadow-none` | none | 平面态 |
| `--shadow-xs` | `0 1px 2px rgba(31, 45, 80, 0.04)` | Input focus、悬浮反馈 |
| `--shadow-sm` | `0 2px 8px rgba(31, 45, 80, 0.05)` | 浮起按钮、Tag |
| `--shadow-md` | `0 6px 22px rgba(31, 45, 80, 0.06)` | Card 默认、Workspace Header |
| `--shadow-lg` | `0 8px 30px rgba(31, 45, 80, 0.08)` | Dropdown、Card hover |
| `--shadow-xl` | `0 14px 38px rgba(31, 45, 80, 0.10)` | Project Card hover、Drawer |
| `--shadow-brand` | `0 6px 16px rgba(49, 94, 251, 0.25)` | Brand Mark、Logo 强调 |
| `--shadow-sider` | `2px 0 12px rgba(26, 39, 74, 0.03)` | 左侧 Sider 描边阴影 |

### 5.2 阴影使用矩阵

| 组件 | 默认 | Hover | 弹出层 |
|---|---|---|---|
| Card（普通） | `--shadow-md` | `--shadow-lg` | — |
| Project Card | `--shadow-md` | `--shadow-xl` + translateY(-2px) | — |
| Workspace Header | `--shadow-md` | — | — |
| Drawer | — | — | `--shadow-xl` |
| Modal | — | — | `--shadow-lg` |
| Dropdown / Tooltip | — | — | `--shadow-lg` |
| Dropdown Menu | — | — | `--shadow-lg` |
| Brand Mark | `--shadow-brand` | — | — |

### 5.3 CSS 变量

```css
:root {
  --shadow-none:   none;
  --shadow-xs:     0 1px 2px rgba(31, 45, 80, 0.04);
  --shadow-sm:     0 2px 8px rgba(31, 45, 80, 0.05);
  --shadow-md:     0 6px 22px rgba(31, 45, 80, 0.06);
  --shadow-lg:     0 8px 30px rgba(31, 45, 80, 0.08);
  --shadow-xl:     0 14px 38px rgba(31, 45, 80, 0.10);
  --shadow-brand:  0 6px 16px rgba(49, 94, 251, 0.25);
  --shadow-sider:  2px 0 12px rgba(26, 39, 74, 0.03);
}
```

### 5.4 阴影守则

1. **阴影透明度一律通过 rgba 通道控制**，避免使用纯黑 + opacity。
2. **同一层级不要叠加阴影**（Card 不再嵌入另一个阴影 Card）。
3. **Hover 阴影 + 轻微位移** 用于强调交互反馈（Project Card 是范例）。

---

## ⑥ Icon · 图标系统

### 6.1 图标库

- **基础库**：`@ant-design/icons@^5.4.0`（已为项目依赖）
- **使用方式**：Outlined 风格为主线，与 AntD 5 默认一致

### 6.2 尺寸阶梯

| Token | Size | 场景 |
|---|---:|---|
| `icon-xs` | 12 px | Tag 内联、表格内联 |
| `icon-sm` | 14 px | Input 前缀 / 后缀、按钮内（Small 按钮） |
| `icon-md` | 16 px | 按钮内（默认）、表格操作按钮 |
| `icon-lg` | 20 px | 弹窗标题图标、Section 标题图标 |
| `icon-xl` | 24 px | 空状态主图、Error 主图 |
| `icon-2xl` | 32 px | Empty 大图、登录视觉辅助 |

### 6.3 语义图标映射（业务高频）

| 语义 | 图标 | 出现位置 |
|---|---|---|
| Project | `ProjectOutlined` / `FolderOpenOutlined` | 侧栏、卡片 |
| Dashboard | `DashboardOutlined` | 侧栏入口 |
| Environment | `DatabaseOutlined` | 侧栏、列表 |
| Suite | `FolderOpenOutlined` / `AppstoreOutlined` | 侧栏、详情 |
| API Case | `ApiOutlined` | 侧栏、详情 |
| Run | `PlayCircleOutlined` | 执行按钮 |
| Report | `FileSearchOutlined` | 侧栏、列表 |
| User / Account | `UserOutlined` / `TeamOutlined` | 账号、用户管理 |
| Role | `SafetyCertificateOutlined` | 角色管理 |
| Settings | `SettingOutlined` | 设置、齿轮 |
| OpenAPI | `ImportOutlined` | 导入按钮 |
| Success | `CheckCircleFilled` | 成功提示 |
| Warning | `WarningFilled` | 警告提示 |
| Danger | `CloseCircleFilled` | 错误提示 |
| Info | `InfoCircleFilled` | 信息提示 |
| Reload | `ReloadOutlined` | 重新加载 |

### 6.4 颜色与图标

```tsx
<CheckCircleFilled style={{ color: "var(--color-success)" }} />
<CloseCircleFilled style={{ color: "var(--color-danger)" }} />
<ApiOutlined style={{ fontSize: 16, color: "var(--color-primary)" }} />
```

### 6.5 使用守则

1. **不混用图标库**：本系统只使用 `@ant-design/icons`，避免引入额外依赖。
2. **Outline 为主、Fill 仅用于状态**：Success / Warning / Danger / Info 用 Filled。
3. **按钮图标尺寸 = 字号**（14px 文字配 14px 图标）。
4. **图标按钮无障碍**：必须带 `aria-label` 或 Tooltip。

---

## ⑦ Table · 表格

### 7.1 基础规格

| 属性 | 值 |
|---|---|
| 行高 | 56 px（含 padding 12） |
| 单元格 padding | `12px 16px` |
| 表头 padding | `12px 16px` |
| 表头背景 | `--bg-muted` (`#F7F9FC`) |
| 表头文字 | `--text-secondary` · 13 / 600 |
| 边框 | `1px solid var(--border-default)` 仅底部分隔线 |
| 圆角 | `--radius-md` (8) |
| 斑马纹 | 默认关闭 |
| Hover 高亮 | `--bg-muted` 透明度 50% |

### 7.2 列类型规范

| 列类型 | 对齐 | 宽度建议 |
|---|---|---|
| 名称 / 标题 | 左 | min 160 |
| 状态 / Tag | 左 | 100~140 |
| 数字 | 右 | 80~120 |
| Method | 左 | 80 |
| 时间 | 左 | 160~200 |
| 操作 | 右 | 120~180 |

### 7.3 通用代码模板

```tsx
import { Table, Tag, Typography, Button, Space } from "antd";
import type { TableColumnsType } from "antd";
import { ReloadOutlined, PlusOutlined } from "@ant-design/icons";

interface Row {
  id: string;
  name: string;
  status: "passed" | "failed" | "running";
  createdAt: string;
}

const columns: TableColumnsType<Row> = [
  {
    title: "名称",
    dataIndex: "name",
    render: (v: string, row) => (
      <Typography.Link strong onClick={() => onOpen(row.id)}>
        {v}
      </Typography.Link>
    ),
  },
  {
    title: "状态",
    dataIndex: "status",
    width: 120,
    render: (v: Row["status"]) => <ResultStatusTag status={v} />,
  },
  {
    title: "创建时间",
    dataIndex: "createdAt",
    width: 180,
    render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text>,
  },
  {
    title: "操作",
    width: 160,
    align: "right",
    render: (_, row) => (
      <Space size={4}>
        <Button type="link" size="small">编辑</Button>
        <Button type="link" size="small" danger>删除</Button>
      </Space>
    ),
  },
];

<Table<Row>
  rowKey="id"
  columns={columns}
  dataSource={rows}
  loading={isLoading}
  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
  size="middle"
/>
```

### 7.4 空 / Loading / Error 三态

```tsx
<Table
  loading={isLoading}              // 内置 Loading 态（骨架行）
  locale={{
    emptyText: (
      <EmptyState
        title="还没有数据"
        description="新建第一条数据开始使用"
        action={<Button type="primary" icon={<PlusOutlined />}>新建</Button>}
      />
    ),
  }}
/>
```

### 7.5 使用守则

1. **必须有 `rowKey`**，禁止使用 index。
2. **操作列永远靠右** (`align: "right"`)。
3. **空态由 Table 自带 `locale.emptyText` 接管**，不要在 Table 外包 Empty。
4. **筛选 / 搜索位于表格上方 Toolbar**，与表格间距 `space-4` (16)。
5. **长文本省略** 使用 `ellipsis: true` + Tooltip，不使用 JS 截断。

---

## ⑧ Card · 卡片

### 8.1 基础规格

| 属性 | 值 |
|---|---|
| 背景 | `--bg-surface` |
| 边框 | `1px solid var(--border-default)` |
| 圆角 | `--radius-lg` (12) |
| 阴影 | `--shadow-md`（默认）→ `--shadow-lg`（hover） |
| 内边距 | `20px`（默认）/ `24px`（强调） |
| 标题 | H3 · 20 / 600 · `--text-primary` |
| Extra 区域 | 与标题同行右对齐，承载次操作 |

### 8.2 类型

| 类型 | 用途 | 关键样式 |
|---|---|---|
| **基础卡片** | 普通容器 | 默认 |
| **指标卡片** | KPI 数字 | `.dashboard-metric-card` body padding `22 24` |
| **项目卡片** | Project 列表 | hover translateY(-2px) + xl 阴影 |
| **危险卡片** | 删除 / 危险区 | `.danger-card` 红边 + 浅红头部 |
| **虚线提示卡片** | Hint | `.dashboard-hint-card` 虚线边框 + `--bg-muted` |
| **作用域卡片** | 范围选择 | 渐变背景 + 描边阴影 |

### 8.3 通用代码模板

```tsx
import { Card, Space, Typography, Button } from "antd";

<Card
  className="surface-card"
  title={<Typography.Title level={4} style={{ margin: 0 }}>API 用例</Typography.Title>}
  extra={<Button type="primary" icon={<PlusOutlined />}>新建</Button>}
  bordered
>
  <Space direction="vertical" size={16} style={{ width: "100%" }}>
    {/* 内容 */}
  </Space>
</Card>
```

### 8.4 危险卡片

```tsx
<Card
  className="surface-card danger-card"
  title="危险操作"
  bordered
>
  <Typography.Paragraph type="secondary">
    删除后无法恢复，所有历史 Run / Report 一并清除。
  </Typography.Paragraph>
  <Button danger>删除 Project</Button>
</Card>
```

### 8.5 使用守则

1. **永远为 Card 设置 `bordered` + 阴影二选一**；本系统统一采用 `bordered` + 阴影。
2. **不要在 Card 内再嵌套 Card**（使用 Space + 分割线代替）。
3. **Extra 区仅放次操作**，主操作放在 Card 外 Page Header。
4. **Card title 不使用 Title 组件**，使用 `<span>` + 自定义字号（保持行高节奏）。

---

## ⑨ Drawer · 抽屉

### 9.1 基础规格

| 属性 | 值 |
|---|---|
| 宽度 | 480 / 720 / 960 三档（按场景选） |
| 圆角 | 顶部 12 px（仅右抽屉） |
| 阴影 | `--shadow-xl` |
| 背景 | `--bg-surface` |
| Header 高度 | 56 px |
| Header 背景 | `--bg-surface`，下边线 `1px solid var(--border-default)` |
| Footer 高度 | 64 px，主操作按钮靠右 |
| 遮罩 | `--bg-overlay` |
| 关闭按钮 | `CloseOutlined` 24 px |

### 9.2 宽度使用矩阵

| 场景 | 宽度 | 说明 |
|---|---:|---|
| 表单（新建 / 编辑） | 480 | 单列简单表单 |
| 表单（执行 / 配置） | 720 | 多字段、表单 + 摘要（`RunExecutionDrawer`） |
| 详情查看 | 960 | 双列布局 + 预览 |

### 9.3 通用代码模板

```tsx
import { Drawer, Space, Button, Form, Input, App } from "antd";
import { CloseOutlined } from "@ant-design/icons";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function ExampleDrawer({ open, onClose }: Props) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  return (
    <Drawer
      title="新建 API Case"
      width={720}
      open={open}
      onClose={submitting ? undefined : onClose}
      maskClosable={!submitting}
      destroyOnClose
      extra={
        <Space>
          <Button onClick={onClose} disabled={submitting}>取消</Button>
          <Button type="primary" loading={submitting} onClick={onSubmit}>保存</Button>
        </Space>
      }
      closeIcon={<CloseOutlined />}
    >
      <Form layout="vertical" form={form} requiredMark="optional">
        {/* fields */}
      </Form>
    </Drawer>
  );
}
```

### 9.4 使用守则

1. **`destroyOnClose`** 一律开启，避免表单残留状态。
2. **提交期间禁止关闭**（`maskClosable={false}` + `onClose` 拦截）。
3. **Drawer 内不嵌 Modal**；如需确认，用 Popconfirm。
4. **Drawer 不超过 960**，更宽使用 Modal 双列布局或独立页面。
5. **表单 Footer 与内容间距 ≥ 24**（`space-6`）。

---

## ⑩ Modal · 模态框

### 10.1 基础规格

| 属性 | 值 |
|---|---|
| 圆角 | `--radius-lg` (12) |
| 阴影 | `--shadow-lg` |
| 背景 | `--bg-surface` |
| Header 高度 | 56 px |
| Header 字号 | H4 · 17 / 600 |
| Footer | 主操作靠右，间距 8 |
| 遮罩 | `--bg-overlay` |
| 居中 | `centered` 默认开启 |

### 10.2 类型

| 类型 | 宽度 | 场景 |
|---|---:|---|
| **确认 Modal** | 416 | 删除、退出等二次确认 |
| **信息 Modal** | 520 | 提示、说明 |
| **表单 Modal** | 640 | 单屏表单 |
| **大表单 Modal** | 880 | 多字段 + 预览 |

### 10.3 通用代码模板（确认）

```tsx
import { Modal, Button, Space, Typography } from "antd";

<Modal
  open={open}
  title="确认删除"
  width={416}
  centered
  onCancel={onCancel}
  footer={
    <Space>
      <Button onClick={onCancel}>取消</Button>
      <Button danger onClick={onConfirm}>确认删除</Button>
    </Space>
  }
>
  <Typography.Paragraph>
    删除 Project <Typography.Text strong>{projectName}</Typography.Text> 后无法恢复，是否继续？
  </Typography.Paragraph>
</Modal>
```

### 10.4 通用代码模板（表单）

```tsx
<Modal
  open={open}
  title="新建 Suite"
  width={640}
  centered
  destroyOnClose
  confirmLoading={submitting}
  okText="保存"
  cancelText="取消"
  onOk={onSubmit}
  onCancel={onCancel}
>
  <Form layout="vertical" form={form} requiredMark="optional">
    {/* fields */}
  </Form>
</Modal>
```

### 10.5 使用守则

1. **危险操作使用 `danger` Button** + 标题明示"确认删除"。
2. **`destroyOnClose`** 用于表单 Modal；纯确认 Modal 不需要。
3. **Modal 内不放 Table / 长列表**（超过 6 行改 Drawer 或独立页）。
4. **Modal 不嵌套 Modal / Drawer**。
5. **重要提示必须配合 Icon**（`ExclamationCircleFilled`）。

---

## ⑪ Empty State · 空状态

### 11.1 规格

| 属性 | 值 |
|---|---|
| 图标 | AntD `<Empty>` `PRESENTED_IMAGE_SIMPLE` 或自定义 Outlined Icon |
| 图标尺寸 | 64 px（默认）/ 96 px（卡片内） |
| 标题 | H4 · 17 / 600 · `--text-primary` |
| 描述 | Caption · 13 · `--text-secondary` |
| 按钮 | Primary（主操作）/ Link（次操作） |
| 内边距 | 48 px（独立）/ 24 px（卡片内） |

### 11.2 通用代码模板

```tsx
import { Empty, Space, Typography, Button } from "antd";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <Space direction="vertical" size={4} align="center">
          <Typography.Text strong>{title}</Typography.Text>
          {description && (
            <Typography.Text type="secondary">{description}</Typography.Text>
          )}
          {action}
        </Space>
      }
    />
  );
}
```

### 11.3 使用守则

1. **空状态必须有"下一步动作"**：创建 / 导入 / 跳转链接，不允许纯展示。
2. **描述必须解释** "为什么会空"+"该怎么继续"。
3. **小空态**（卡片内）使用 `image={Empty.PRESENTED_IMAGE_SIMPLE}`；**大空态**（独立区块）使用 `imageStyle={{ height: 96 }}`。
4. **不允许空状态** 用纯文字描述（必须有图标 / 插画）。

---

## ⑫ Loading · 加载中

### 12.1 规格

| 类型 | 组件 | 场景 |
|---|---|---|
| **按钮加载** | `Button loading={true}` | 提交、保存、执行 |
| **行级加载** | `Table loading={true}` | 列表初次加载 |
| **区块加载** | `<LoadingBlock tip>` | Drawer / 弹窗内 |
| **全屏加载** | `<LoadingBlock fullPage>` | 路由 Suspense |
| **行内轻提示** | `<Spin size="small" />` | 异步轻操作 |

### 12.2 通用代码模板

```tsx
import { Spin, Space, Typography } from "antd";

export function LoadingBlock({
  tip = "加载中…",
  rows = 4,
  fullPage = false,
}: {
  tip?: string;
  rows?: number;
  fullPage?: boolean;
}) {
  return (
    <div className={fullPage ? "state-full-page" : "state-block"}>
      <Spin size="large" tip={tip}>
        <div className="spin-placeholder" />
      </Spin>
    </div>
  );
}
```

### 12.3 使用守则

1. **执行同步操作**（如 Run）必须用 `Spin size="large"` + 文案，不允许用 Spinner-only。
2. **加载文案不超过 12 个汉字**："加载中…"、"执行中…"、"保存中…"。
3. **禁止使用自定义 Spinner**（统一 AntD Spin）。
4. **长任务超过 3 秒** 必须显示说明性文案（例："正在同步执行，请勿重复提交"）。

---

## ⑬ Skeleton · 骨架屏

### 13.1 规格

| 属性 | 值 |
|---|---|
| 组件 | `<Skeleton active paragraph={{ rows }} />` |
| 行数 | 卡片 4 行，详情 6 行，列表 8 行 |
| 圆角 | 4 px |
| 主色 | `rgba(190, 200, 215, 0.2)` |
| 激活色 | `rgba(190, 200, 215, 0.4)` |

### 13.2 通用代码模板

```tsx
import { Skeleton, Card, Space } from "antd";

<Card className="surface-card">
  <Skeleton active paragraph={{ rows: 4 }} />
</Card>

<Skeleton active title={{ width: "40%" }} paragraph={{ rows: 6 }} />

{/* Table 骨架 */}
<Table loading={{ spinning: true, indicator: <Skeleton active /> }} dataSource={[]} />
```

### 13.3 使用守则

1. **Skeleton 用于页面 / 卡片初次加载**，二次加载使用 Spin。
2. **Skeleton 标题宽度** 用百分比（30~60%）模拟真实标题，避免全部 100%。
3. **避免 Skeleton + Loading 同时出现**。
4. **长列表骨架** 渲染 6~10 行，不要 1 行就消失。

---

## ⑭ Error · 错误态

### 14.1 错误分级

| 级别 | 触发条件 | 组件 | 默认操作 |
|---|---|---|---|
| **403** | 无权限 | `Result status="403"` | 返回 Dashboard |
| **404** | 资源不存在 | `Result status="404"` | 返回上级 |
| **500 / 网络** | 服务异常 | `Result status="error"` | 重新加载 |
| **字段错误** | 表单校验 | `Form.Item validateStatus="error"` | 提示文案 |
| **行内错误** | 列表某行失败 | `<Alert type="error">` | 重试按钮 |
| **业务错误** | 后端业务码 | `App.useApp().message.error` | 仅提示 |
| **页面崩溃** | 未捕获异常 | `ErrorBoundary` + `Result status="error"` | 刷新页面 |

### 14.2 通用代码模板

```tsx
import { App, Button, Result, Typography, Space } from "antd";
import { getErrorMessage, getHttpStatus } from "@/api/client";

export function ErrorState({
  error,
  onRetry,
  compact = false,
}: {
  error: unknown;
  onRetry?: () => void;
  compact?: boolean;
}) {
  const status = getHttpStatus(error);
  const resultStatus = status === 403 ? "403" : status === 404 ? "404" : "error";
  const title =
    status === 403 ? "无权访问"
    : status === 404 ? "资源不存在"
    : "加载失败";

  if (compact) {
    return (
      <Result
        status={resultStatus}
        title={title}
        subTitle={getErrorMessage(error)}
        extra={onRetry && <Button onClick={onRetry}>重新加载</Button>}
      />
    );
  }
  return (
    <Result
      status={resultStatus}
      title={title}
      subTitle={getErrorMessage(error)}
      extra={
        <Space>
          <Button onClick={() => window.history.back()}>返回</Button>
          {onRetry && <Button type="primary" onClick={onRetry}>重新加载</Button>}
        </Space>
      }
    />
  );
}
```

### 14.3 行内错误（Alert）

```tsx
import { Alert, Button, Space } from "antd";

<Alert
  type="error"
  showIcon
  message="加载失败"
  description={getErrorMessage(error)}
  action={<Button size="small" onClick={onRetry}>重试</Button>}
/>
```

### 14.4 使用守则

1. **错误提示必须给出原因**（来自后端 message，不允许固定文案"出错了"）。
2. **必须给可执行操作**：返回 / 重试 / 联系管理员。
3. **业务错误用 `message.error` 提示一次**，不阻塞页面。
4. **表单错误就近显示**，不要用全局 Modal。
5. **网络错误必须给重试**。

---

## ⑮ Button · 按钮

### 15.1 类型矩阵

| 类型 | 适用场景 | 关键样式 |
|---|---|---|
| **Primary** | 主操作（保存、提交、执行） | 实心品牌色背景 |
| **Secondary**（Default） | 次操作（取消、返回） | 灰边白底 |
| **Danger** | 危险操作（删除、移除） | 红色实心 / 红色描边 |
| **Ghost** | 深色背景下的按钮（登录视觉） | 透明背景 + 白边 |

### 15.2 规格

| 属性 | Primary | Secondary | Danger | Ghost |
|---|---|---|---|---|
| 背景 | `--color-primary` | `--bg-surface` | `--color-danger` | transparent |
| 文字 | `--text-inverse` | `--text-primary` | `--text-inverse` | `--text-inverse` |
| 边框 | none | `1px solid var(--border-strong)` | none | `1px solid rgba(255,255,255,0.6)` |
| Hover 背景 | `--brand-primary-hover` | `--bg-muted` | `#B91C1C` | `rgba(255,255,255,0.08)` |
| 圆角 | `--radius-md` (8) | `--radius-md` | `--radius-md` | `--radius-md` |
| 高度 | 32 px（默认）/ 24 px（small） / 40 px（large） | 同左 | 同左 | 同左 |

### 15.3 使用矩阵

| 场景 | 按钮类型 | 说明 |
|---|---|---|
| 新建 / 保存 / 执行 | **Primary** | 一个区块只允许 1 个 Primary |
| 取消 / 返回 / 上一步 | **Secondary** (default) | 永远靠右 |
| 删除 / 移除 / 终止执行 | **Danger** | 配二次确认 |
| 登录视觉 / 顶栏操作 | **Ghost** | 深色背景 |
| 表格行内操作 | **Link** | 不占用按钮槽 |
| 弹窗 Footer 主操作 | **Primary** | 单 Primary + 取消 |

### 15.4 通用代码模板

```tsx
import { Button, Space, App } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";

<Space>
  <Button>取消</Button>
  <Button type="primary" icon={<PlusOutlined />} onClick={onSave}>保存</Button>
</Space>

{/* 危险 */}
<Button danger icon={<DeleteOutlined />} onClick={onDelete}>删除</Button>

{/* 链接式（行内操作） */}
<Button type="link" size="small">编辑</Button>

{/* Ghost */}
<Button type="primary" ghost>立即开始</Button>

{/* Loading */}
<Button type="primary" loading={submitting}>提交中…</Button>
```

### 15.5 使用守则

1. **同一区块最多 1 个 Primary**，其余为 Default / Danger / Link。
2. **Primary 不使用 size="small"**；小尺寸场景用 Link 代替。
3. **删除按钮文字必须明确**（"删除 Project" 而非 "删除"）。
4. **按钮文案 ≤ 6 个汉字**（保存、提交、确认、删除）。
5. **危险操作必须二次确认**（Popconfirm / Modal）。
6. **loading 期间禁用按钮**，不允许重复提交。

---

## 附录 A · 全局样式入口（styles.css）

```css
/* frontend/src/styles.css —— Design System Token 入口 */

:root {
  /* Font */
  font-family: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  color: #172033;
  background: #f5f7fb;
  font-synthesis: none;
  text-rendering: optimizeLegibility;

  /* Brand */
  --brand-primary: #315efb;
  --brand-primary-hover: #1f4ae8;
  --brand-primary-active: #163dc4;
  --brand-secondary: #7448ff;
  --brand-gradient: linear-gradient(135deg, #315efb 0%, #7448ff 100%);

  /* Semantic */
  --color-primary: #315efb;
  --color-success: #16a34a;
  --color-warning: #faad14;
  --color-danger:  #dc2626;
  --color-info:    #0ea5e9;

  /* Neutral - Text */
  --text-primary:   #172033;
  --text-secondary: #778097;
  --text-tertiary:  #929aab;
  --text-disabled:  #c2c8d2;
  --text-inverse:   #ffffff;

  /* Neutral - Surface */
  --bg-page:     #f5f7fb;
  --bg-surface:  #ffffff;
  --bg-muted:    #f7f9fc;
  --bg-overlay:  rgba(15, 23, 42, 0.45);

  /* Border */
  --border-default: #edf0f5;
  --border-strong:  #d9dee7;
  --border-danger:  #ffccc7;

  /* Radius */
  --radius-sm:   4px;
  --radius-md:   8px;
  --radius-lg:  12px;
  --radius-xl:  14px;
  --radius-2xl: 18px;
  --radius-full: 9999px;

  /* Shadow */
  --shadow-xs:     0 1px 2px rgba(31, 45, 80, 0.04);
  --shadow-sm:     0 2px 8px rgba(31, 45, 80, 0.05);
  --shadow-md:     0 6px 22px rgba(31, 45, 80, 0.06);
  --shadow-lg:     0 8px 30px rgba(31, 45, 80, 0.08);
  --shadow-xl:     0 14px 38px rgba(31, 45, 80, 0.10);
  --shadow-brand:  0 6px 16px rgba(49, 94, 251, 0.25);
  --shadow-sider:  2px 0 12px rgba(26, 39, 74, 0.03);

  /* Spacing */
  --space-1:  4px;
  --space-2:  8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
}
```

---

## 附录 B · 组件使用 Checklist

### B.1 新增页面 / 区块前

- [ ] 是否需要明确 Container？使用 Card 还是 PageHeader？
- [ ] 是否复用 `<LoadingBlock>` / `<EmptyState>` / `<ErrorState>`？
- [ ] Toolbar 操作是否符合 Primary ≤ 1 原则？
- [ ] 间距是否全部从 7 个 Spacing Token 中取？
- [ ] 颜色是否引用 CSS 变量，未硬编码？

### B.2 新增 Modal / Drawer 前

- [ ] 表单 ≤ 6 字段 → Modal（640）；> 6 → Drawer（720）
- [ ] 是否需要 `destroyOnClose`？
- [ ] 提交期间是否禁用关闭？
- [ ] Footer 按钮是否 `Primary + Default` 二选一结构？
- [ ] 危险操作是否二次确认？

### B.3 新增 Table 前

- [ ] 是否设置了 `rowKey`？
- [ ] 操作列是否 `align: "right"`？
- [ ] 状态列是否使用 `<XxxStatusTag>`？
- [ ] 分页是否带 `showTotal`？
- [ ] 空态是否给出下一步动作？

---

## 附录 C · AntD Token 速查

| 需求 | Token |
|---|---|
| 主色 | `colorPrimary` |
| 成功 | `colorSuccess` |
| 警告 | `colorWarning` |
| 错误 | `colorError` |
| 信息 | `colorInfo` |
| 文本基础 | `colorTextBase` |
| 背景布局 | `colorBgLayout` |
| 边框 | `colorBorder` |
| 圆角 | `borderRadius` |
| 字号基础 | `fontSize` |
| 字体 | `fontFamily` |
| 控件高度 | `controlHeight` |
| 控件高度（小） | `controlHeightSM` |

---

## 附录 D · 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-15 | 初版：Color / Typography / Spacing / Radius / Shadow / Icon / Table / Card / Drawer / Modal / Empty / Loading / Skeleton / Error / Button 全部落地 |

---

**约束再确认**

- ❌ 不修改任何业务逻辑
- ❌ 不新增任何 API
- ❌ 不修改数据库
- ✅ 仅规范视觉与组件用法，作为前端协作的单一真相源