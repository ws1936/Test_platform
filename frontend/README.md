# Frontend · Test Platform

API 自动化测试平台 MVP 前端（React 18 + Vite + TypeScript + Ant Design）。

## 启动

```bash
# 1. 安装依赖（与后端同一 .venv 之外的 node_modules）
npm install

# 2. 启动 dev server（默认 http://localhost:5173）
npm run dev

# 3. 类型检查 + ESLint + 生产构建（一次性全跑）
npm run check
```

## 与后端联调

默认后端地址 `http://localhost:8000/api/v1`，由 `vite.config.ts` 的 `server.proxy`
转发到后端，避免浏览器 CORS 问题。

如需自定义，可在 `frontend/.env.local` 中覆盖：

```bash
VITE_API_BASE=/api/v1
```

## 目录结构

```
src/
├── api/                  # 后端 HTTP 客户端（按资源分模块 + queryKeys factory）
│   ├── client.ts         # Axios 实例 + 401 自动 refresh + 错误归一化
│   ├── auth.ts
│   ├── projects.ts
│   ├── environments.ts
│   ├── suites.ts
│   ├── testCases.ts
│   ├── runs.ts           # F014 concurrency + F015 exportReport
│   ├── report.ts
│   ├── openApiImport.ts  # F012/F013 dry_run + batch=true
│   └── admin.ts
│
├── components/           # 通用 UI 组件
│   ├── AppShell.tsx       # 侧边栏 + 顶栏 + outlet
│   ├── AsyncState.tsx     # Loading / Empty / Error 三态
│   ├── PageHeader.tsx
│   ├── RouteGuards.tsx    # ProtectedRoute / AdminRoute
│   ├── StatusTags.tsx
│   ├── *FormModal.tsx     # 各资源创建/编辑模态框
│   ├── dashboard/         # Dashboard 卡片 + Recent 面板
│   ├── execution/         # RunExecutionDrawer
│   ├── report/            # FailureAnalysis / ResultEvidence / Timeline
│   └── workspace/         # ProjectWorkspace Layout / Sider / Header / Context
│
├── pages/                # 路由叶子组件（每页一个文件）
│   ├── Dashboard.tsx
│   ├── Login.tsx
│   ├── Projects.tsx
│   ├── SystemResult.tsx   # 403 / 404
│   ├── admin/             # Users / Roles
│   └── workspace/         # 12 个工作区页面（overview / environment / suite / case / run / report / import / information）
│
├── store/                 # Zustand
│   └── auth.ts            # token + current user（仅 client state）
│
├── utils/                 # 纯函数
│   ├── format.ts          # 时间 / 百分比 / duration 格式化
│   ├── json.ts            # JSON 安全解析
│   └── dashboard.ts
│
├── App.tsx                # 路由表（AppShell 包裹 + lazy 加载）
├── main.tsx                # React 入口
└── styles.css              # 全局 CSS（与 Tailwind 不同，使用 antd 主题 + 自定义类）
```

## 状态管理

| 层 | 工具 | 职责 |
|----|------|------|
| Server state | TanStack Query 5 | 列表 / 详情 / mutation；`api/queryKeys.ts` factory 统一管理 cache key |
| Client state | Zustand 4 | 仅 `auth.ts`（token + user）；其他 UI 状态用 useState |
| Form state | React Hook Form 7 | 5 个 FormModal + CaseEditor |
| URL state | React Router 6 | tab / 分页 / filter 通过 search params |

## 鉴权

- `ProtectedRoute`（`<AppShell>` 外层）拦截未登录 → 跳 `/login`
- `AdminRoute` 包裹管理员页 → 非 admin 跳 `/403`
- Axios 拦截器：401 自动用 refresh token 续签；续签失败跳 `/login`
- Token 存 `localStorage`：`access_token` / `refresh_token`

## 核心约定

1. **类型**：从 `api/types.ts` 引用后端 Pydantic 镜像，**不**自造类型
2. **Query Key**：所有 cache key 在 `api/queryKeys.ts` 定义；mutation 必须 `invalidateQueries` 相关 key
3. **错误处理**：用 `getErrorMessage(error)` / `getApiError(error)` 统一提取后端 `code/message/detail` 字段
4. **样式**：用 antd 主题 + `styles.css` 自定义类（如 `.surface-card` / `.run-preview-row`）；**不**引入 Tailwind / CSS-in-JS
5. **代码风格**：`snake_case` 变量 / `PascalCase` 组件 / 命名导出优于默认导出（除 page 组件）
6. **零前端自动化测试**（KISS）：项目不引入 vitest / RTL / Cypress / Playwright；新功能靠手测 + 后端 pytest 兜底

## P1 集成点

| Feature | 前端入口 | 后端 API |
|---------|---------|---------|
| F012 OpenAPI 导入 | `WorkspaceImport` / `WorkspaceImportIndex` | `POST /projects/{pid}/suites/{sid}/import/openapi` |
| F013 OpenAPI 批量 | 同上 + `?batch=true` | 同上 + `documents[]` |
| F014 有限并发 | `WorkspaceRun` 中 Slider/InputNumber（1-64） | `POST /projects/{pid}/runs?concurrency=N` |
| F015 报告导出 | `WorkspaceReportDetail` 中「导出报告」Dropdown | `GET /runs/{run_id}/export?format=json\|html` |

## 已知限制

- 无 SSR / SSG（Vite SPA）
- 无 i18n（中文硬编码）
- 无暗色模式
- 无 WebSocket 实时进度
- Bundle 单 chunk ~1.5MB（gzip ~480KB），未做 code-split；本期范围外
