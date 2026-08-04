# F015 报告导出 — 规格说明

> 状态：Done（核心实现 + 脱敏加固 + 文档同步）  
> 范围：MVP 增强能力；单次 TestRun 报告导出。  
> 设计稿：本文档。配套 ADR 见 `docs/04-rules/ADR.md` ADR-007。

---

## 1. 目标

把 `TestRun` + `TestResult` 的快照导出为 **JSON** 或 **HTML** 文件，
让用户离线打开 / 存档 / 转发 / 嵌入 CI artifact。

不做分布式、不做后台任务、不做 Allure 静态站点托管
（呼应 PRD §7 / AI_RULES §4.4 / §15）。

## 2. 非目标

- Allure / pytest-html / any HTML 报告框架
- jinja2 / mako / weasyprint 等模板/文档库
- PDF / CSV / Excel / XML
- 项目级批量导出（多 run 打包）
- 异步生成 + 邮件通知 + 下载链接
- 报告预生成 / 缓存
- 前端 UI 下载按钮（F016 范围）

## 3. 用户故事

| 场景 | 行为 |
|------|------|
| 用户在 Run 详情页点 "导出 JSON" | 浏览器下载 `run-<时间戳>-<短 uuid>.json` |
| 用户点 "导出 HTML" | 浏览器下载 `run-<时间戳>-<短 uuid>.html`，浏览器直接打开看摘要 |
| 用户传 `?format=xml` | Router 422（pattern 校验），不调用 Service |
| 非 owner / admin 调用 | 403 |
| 调一个不存在的 run | 404 |

## 4. 接口契约

### 4.1 `GET /api/v1/runs/{run_id}/export`

Query 参数：

| 字段 | 类型 | 必填 | 取值范围 | 默认 |
|------|------|------|----------|------|
| `format` | string | 否 | `json` \| `html` | `json` |

Response：

| 状态 | 触发条件 |
|------|----------|
| 200 + 文件流 | 成功 |
| 400 | 暂未直接返回（format 校验在 Router 422 完成） |
| 401 | 未登录 |
| 403 | 非 owner / 非 admin |
| 404 | Run 不存在 |

Content-Type：

| format | Content-Type |
|--------|--------------|
| `json` | `application/json; charset=utf-8` |
| `html` | `text/html; charset=utf-8` |

Content-Disposition：`attachment; filename="run-<YYYYMMDD-HHMMSS>-<uuid>.<fmt>"`。
文件名全 ASCII，不需 RFC 5987。

## 5. 内容契约

### 5.1 JSON 结构

```json
{
  "run": {
    "id": "uuid",
    "name": "...",
    "scope": "case|collection|project",
    "scope_id": "uuid|null",
    "status": "pending|running|finished|failed|canceled",
    "total": 0,
    "passed": 0,
    "failed": 0,
    "error": 0,
    "skipped": 0,
    "started_at": "iso8601|null",
    "finished_at": "iso8601|null",
    "environment_id": "uuid",
    "project_id": "uuid",
    "triggered_by": "uuid|null",
    "pass_rate": 0.95,
    "elapsed_seconds": 12.345
  },
  "results": [
    {
      "id": "uuid",
      "test_case_id": "uuid",
      "case_name": "...",
      "case_method": "GET|POST|...",
      "case_path": "/api/...",
      "status": "passed|failed|skipped|error",
      "elapsed_ms": 42,
      "error_code": "API_EXECUTION_TIMEOUT|null",
      "error_message": "...",
      "started_at": "iso8601|null",
      "finished_at": "iso8601|null",
      "request_snapshot": { ... F010 完整快照（headers 已脱敏）... },
      "response_snapshot": { ... F010 完整快照（headers 在 F015 二次脱敏）... },
      "assertions_snapshot": [ ... F009 断言结果列表 ... ]
    }
  ]
}
```

### 5.2 脱敏策略

| 字段 | 来源 | 脱敏方式 |
|------|------|----------|
| `request_snapshot.headers` | F010 持久化时已走 `_sanitize_headers` | F015 不再二次脱敏（信任 DB 内容） |
| `response_snapshot.headers` | F010 持久化时**未脱敏** | **F015 在 build_payload 走 `_sanitize_headers` 二次脱敏** |

黑名单（F010 / F015 共用）：`authorization` / `cookie` / `set-cookie`
/ `x-auth-token` / `x-api-key` / `x-csrf-token`（大小写不敏感）。

### 5.3 HTML 结构

自包含 HTML（行内 CSS，不依赖外链）：

* 标题：`Run Report: <run.name>`
* Meta：Run ID · Scope · Started → Finished
* Summary 卡片：Total / Passed / Failed / Error / Skipped / Pass Rate
* 进度条：按 pass_rate 渲染宽度
* 结果表：Status / Method / Path / Case / Elapsed (ms) / Error
* **不展示** request / response / assertion 详情（避免 HTML 体积爆炸）

XSS 防护：所有用户控制字段（case_name / case_path / error_message /
status）经 `esc()` 转义后渲染。

## 6. 实现要点

* **独立模块**：`src/app/domain/test_run/exporter.py` 避免污染 service.py。
* **Service 委托**：`TestRunService.export_run` 走 `_load_run_orm` 鉴权
  （owner / superuser）+ 加载 results + 委托 `_export_run_impl`。
* **Router**：FastAPI `Query(default="json", pattern="^(json|html)$")`
  做格式校验；用 `Response` 返回文件流 + Content-Disposition。
* **错误码**：**不新增业务码**，沿用 F010/F011 的 `BadRequestException`
  （在 Router 层被 `pattern` 拦下为 422）+ `TestRunNotFoundException`（404）。

## 7. 可观测性

* 暂未在 exporter / service / router 加专用日志（KISS）。
* 后续如需审计"谁导出了哪份报告"，可在 Service 层加 `logger.info`
  记录 `run_id` + `format` + `current_user.id`。

## 8. 测试覆盖

### 8.1 已有（13 用例）

`src/tests/test_test_run_export.py`：
* exporter 单元：3 用例（json/html 渲染 + 非法 format 拒绝）
* endpoint 集成：5 用例（200 json/html + 401/403/404）
* XSS：1 用例（`test_render_html_escapes_user_input`）
* 基础 esc / XSS：1 用例（`test_esc_basic`）
* 还有 3 个 endpoint 集成（test_export_run_endpoint_returns_json /
  test_export_run_endpoint_returns_html /
  test_export_run_rejects_bad_format 等）

### 8.2 本次新增（4 用例）

* `test_build_payload_includes_full_snapshots` — JSON 含 request /
  response / assertions 三件套；response.headers 脱敏；body /
  status_code / body_truncated 不变。
* `test_build_payload_preserves_sanitized_request_snapshot` — 锁定
  request_snapshot 由 F010 在持久化时脱敏，F015 不再二次处理。
* `test_payload_handles_missing_or_null_snapshots_gracefully` —
  `response_snapshot=None` / `headers={}` 容错。
* `test_html_export_does_not_leak_authorization` — HTML 不含
  Authorization / WWW-Authenticate 等敏感头名；error_message 正常展示。

合计 17/17 全绿，全量 424/424 通过（420 旧 + 4 新），0 回归。

## 9. 风险与权衡

* **HTML 体积**：单 Run 1000 result、每个 64KB body → 64MB HTML。
  本期 HTML 只展示摘要，不塞 request/response，体积可控。
  如未来要"HTML 报告含请求/响应详情"，需切换 StreamingResponse。
* **datetime / UUID 序列化**：`build_payload` 已显式 `.isoformat()` /
  `str()`，JSON 可被 `json.loads` 直接消费。
* **filename 中文**：当前 `run-<时间戳>-<uuid>.<fmt>` 全 ASCII，
  无需 RFC 5987 encoding。
* **HTML f-string 转义**：所有用户字段过 `esc()`，`<` `>` `&` `"`
  均转义。XSS 单元测试已锁定。
* **重复脱敏风险**：F010 已对 request_snapshot.headers 脱敏；
  F015 对 response_snapshot.headers 二次脱敏。如果未来 F010 改了
  持久化口径（如改为不脱敏），F015 仍能兜底 response 侧；
  request 侧则依赖 F010 的契约。

## 10. 后续演进（不在本任务）

* **Allure 服务化**：MVP 后再评估，呼应 PRD §7 / AI_RULES §4.4。
* **流式响应**：超大 Run 用 StreamingResponse 边读边发。
* **报告预生成**：Run 状态变 finished 时后台生成缓存（需 MQ，
  跳出 MVP）。
* **项目级批量打包**：多个 Run 合成一份 zip（避免单文件过大）。

## 11. 关联文档

* `docs/01-product/BACKLOG.md` §3 F015
* `docs/04-rules/ADR.md` ADR-007（F015 决策）
* `docs/02-design/ARCHITECTURE.md` §3.4（F015 标注）
* `docs/03-api/OPENAPI.yaml` `/runs/{run_id}/export`
* `docs/05-test/ACCEPTANCE.md` §F015 验收条目
* `src/app/domain/test_run/exporter.py`
* `src/tests/test_test_run_export.py`
