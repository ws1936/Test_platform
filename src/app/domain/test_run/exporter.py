"""F015 报告导出 — 独立模块，避免污染现有 service.py。

把 export_run + HTML 渲染放在这里，service.py 只 import + delegate。

设计要点（呼应 PRD §5.8 + §6 可追溯、AI_RULES §6 不进日志敏感数据）：

* JSON 输出必须包含每条 result 的 ``request_snapshot`` / ``response_snapshot``
  / ``assertions_snapshot``，否则导出报告失去“失败定位”的价值。
* ``response_snapshot.headers`` 复用 F010 的 :func:`_sanitize_headers`，
  防止 ``Authorization`` / ``Cookie`` / API Key 等敏感头泄到导出文件里。
* body 截断由 F010 在持久化时完成（``response_snapshot.body_truncated``
  标记），F015 不再二次截断。
"""
from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# 复用 F010 的脱敏黑名单 —— 这是一个 module 级 frozenset，公开 re-export，
# 位于 ``runner.__all__``，所以这里是合法导入。
from app.domain.test_engine.runner import (
    _sanitize_headers as _sanitize_headers,
)

# HTML entities. The entity itself starts with ``&``; using ``chr(38)``
# keeps the literals unambiguous while producing standards-compliant output.
_AMP = chr(38) + "amp;"
_LT = chr(38) + "lt;"
_GT = chr(38) + "gt;"
_QUOT = chr(38) + "quot;"
_MID = chr(183)  # ·
_ARR = chr(8594)  # →


def esc(s: Any) -> str:
    """最小 HTML 转义。"""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("&", _AMP).replace("<", _LT).replace(">", _GT)
    s = s.replace(chr(34), _QUOT)
    return s


def _sanitize_response_snapshot(snap: Any) -> Any:
    """F015：复用 F010 脱敏逻辑过滤 ``response_snapshot.headers``。

    snapshot 是从 DB 读出的 dict，本身已是 JSON-safe；这里只动 ``headers``
    子字段，不改 ``body`` / ``status_code`` / ``elapsed_ms``。
    返回的是新 dict，不修改原对象，保证 idempotent。
    """
    if not snap or not isinstance(snap, dict):
        return snap
    headers = snap.get("headers")
    if not headers:
        return snap
    # copy 后替换 headers，不污染原 snapshot（调用方可能复用 ORM 对象）
    new_snap = dict(snap)
    new_snap["headers"] = _sanitize_headers(dict(headers))
    return new_snap


def build_payload(run: Any, results: List[Any]) -> Dict[str, Any]:
    """把 ORM 对象转为可序列化的 dict。

    Run 级口径与 F011 :class:`TestRunResponse` + :meth:`_decorate_run_response`
    对齐，包含 F011 计算字段 ``pass_rate`` / ``elapsed_seconds``。
    Result 级口径包含完整的请求/响应/断言快照（脱敏后）以满足 PRD §5.8。
    """
    total = run.total or 0
    passed = run.passed or 0
    pass_rate = (passed / total) if total else None
    elapsed_seconds: Any = None
    if run.started_at and run.finished_at:
        elapsed_seconds = round(
            (run.finished_at - run.started_at).total_seconds(), 3
        )

    return {
        "run": {
            "id": str(run.id),
            "name": run.name,
            "scope": run.scope,
            "scope_id": str(run.scope_id) if run.scope_id else None,
            "status": run.status,
            "total": run.total,
            "passed": run.passed,
            "failed": run.failed,
            "error": run.error,
            "skipped": run.skipped,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "environment_id": str(run.environment_id),
            "project_id": str(run.project_id),
            "triggered_by": str(run.triggered_by) if run.triggered_by else None,
            "pass_rate": pass_rate,
            "elapsed_seconds": elapsed_seconds,
        },
        "results": [
            {
                "id": str(r.id),
                "test_case_id": str(r.test_case_id),
                "case_name": r.case_name,
                "case_method": r.case_method,
                "case_path": r.case_path,
                "status": r.status,
                "elapsed_ms": r.elapsed_ms,
                "error_code": r.error_code,
                "error_message": r.error_message,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                # F015 核心：完整快照，让“失败定位”不依赖原始 DB 查询。
                # response_snapshot.headers 在 _sanitize_response_snapshot
                # 里走与 F010 runner._sanitize_headers 同一套黑名单。
                "request_snapshot": r.request_snapshot,
                "response_snapshot": _sanitize_response_snapshot(
                    r.response_snapshot
                ),
                "assertions_snapshot": r.assertions_snapshot,
            }
            for r in results
        ],
    }


def render_json(payload: Dict[str, Any]) -> str:
    return _json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def render_html(payload: Dict[str, Any]) -> str:
    """简易 HTML 报告（无 jinja2 依赖）。"""
    run = payload["run"]
    results = payload["results"]
    total = run["total"] or len(results)
    passed = run["passed"] or 0
    failed = run["failed"] or 0
    error_count = run["error"] or 0
    skipped = run["skipped"] or 0
    pass_rate = (passed / total) if total else 0
    bar_width = int(pass_rate * 100)

    # 用 chr() 拼接避免被 strip
    rows_html = []
    for r in results:
        status = r["status"]
        status_class = {
            "passed": "pass",
            "failed": "fail",
            "error": "err",
            "skipped": "skip",
        }.get(status, "")
        err_msg = r["error_message"] or ""
        elapsed = r["elapsed_ms"] if r["elapsed_ms"] is not None else "-"
        # 整行 HTML 一次性 escape + 拼接
        row = (
            '<tr class="' + status_class + '">'
            + '<td><span class="status ' + status_class + '">'
            + esc(status)
            + "</span></td>"
            + "<td>" + esc(r["case_method"]) + "</td>"
            + '<td><code>' + esc(r["case_path"]) + "</code></td>"
            + "<td>" + esc(r["case_name"]) + "</td>"
            + '<td class="num">' + str(elapsed) + "</td>"
            + '<td class="err">' + esc(err_msg) + "</td>"
            + "</tr>"
        )
        rows_html.append(row)
    if rows_html:
        rows_joined = "".join(rows_html)
    else:
        rows_joined = (
            '<tr><td colspan="6" '
            'style="text-align:center;color:#999">No results</td></tr>'
        )

    started = esc(run["started_at"] or "-")
    finished = esc(run["finished_at"] or "-")
    name = esc(run["name"])
    scope = esc(run["scope"])
    rid = esc(run["id"])
    pass_rate_str = ("%.1f%%" % (pass_rate * 100)) if total else "-"

    # 整段 HTML：避免在源码中嵌入 & < > " 等字符
    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="zh-CN">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append("<title>Run Report " + rid + "</title>")
    parts.append("<style>")
    parts.append(
        "body{font-family:-apple-system,Segoe UI,PingFang SC,sans-serif;"
        "margin:24px;color:#1f1f1f;}"
    )
    parts.append("h1{font-size:20px;margin:0 0 8px;}")
    parts.append(".meta{color:#666;font-size:13px;margin-bottom:16px;}")
    parts.append(
        ".summary{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;}"
    )
    parts.append(
        ".card{border:1px solid #e5e5e5;border-radius:6px;"
        "padding:12px 16px;min-width:80px;}"
    )
    parts.append(
        ".card .num{font-size:24px;font-weight:600;}"
        ".card .label{font-size:12px;color:#888;}"
    )
    parts.append(
        ".bar-wrap{background:#f0f0f0;border-radius:4px;height:8px;"
        "margin-bottom:24px;overflow:hidden;}"
    )
    parts.append(
        ".bar{background:#52c41a;height:100%;width:"
        + str(bar_width)
        + "%;transition:width 0.3s;}"
    )
    parts.append("table{width:100%;border-collapse:collapse;font-size:13px;}")
    parts.append(
        "th,td{padding:8px 10px;text-align:left;"
        "border-bottom:1px solid #f0f0f0;}"
    )
    parts.append("th{background:#fafafa;font-weight:500;color:#555;}")
    parts.append("td.num{text-align:right;font-variant-numeric:tabular-nums;}")
    parts.append(
        "td.err{color:#cf1322;font-size:12px;max-width:320px;"
        "word-break:break-word;}"
    )
    parts.append(
        "code{background:#f5f5f5;padding:1px 4px;border-radius:3px;"
        "font-size:12px;}"
    )
    parts.append(
        ".status{padding:1px 6px;border-radius:3px;font-size:11px;"
        "font-weight:500;}"
    )
    parts.append(".status.pass{background:#f6ffed;color:#389e0d;}")
    parts.append(".status.fail{background:#fff1f0;color:#cf1322;}")
    parts.append(".status.err{background:#fff7e6;color:#d46b08;}")
    parts.append(".status.skip{background:#fafafa;color:#8c8c8c;}")
    parts.append(".footer{margin-top:32px;color:#999;font-size:12px;}")
    parts.append("</style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append("<h1>Run Report: " + name + "</h1>")
    parts.append('<div class="meta">')
    parts.append(
        "<strong>Run ID</strong>: "
        + rid
        + " "
        + _MID
        + " <strong>Scope</strong>: "
        + scope
        + "<br>"
    )
    parts.append(
        "<strong>Started</strong>: "
        + started
        + " "
        + _ARR
        + " <strong>Finished</strong>: "
        + finished
    )
    parts.append("</div>")
    parts.append('<div class="summary">')
    parts.append(
        '<div class="card"><div class="num">'
        + str(total)
        + '</div><div class="label">Total</div></div>'
    )
    parts.append(
        '<div class="card"><div class="num">'
        + str(passed)
        + '</div><div class="label">Passed</div></div>'
    )
    parts.append(
        '<div class="card"><div class="num">'
        + str(failed)
        + '</div><div class="label">Failed</div></div>'
    )
    parts.append(
        '<div class="card"><div class="num">'
        + str(error_count)
        + '</div><div class="label">Error</div></div>'
    )
    parts.append(
        '<div class="card"><div class="num">'
        + str(skipped)
        + '</div><div class="label">Skipped</div></div>'
    )
    parts.append(
        '<div class="card"><div class="num">'
        + pass_rate_str
        + '</div><div class="label">Pass Rate</div></div>'
    )
    parts.append("</div>")
    parts.append('<div class="bar-wrap"><div class="bar"></div></div>')
    parts.append("<table>")
    parts.append("<thead><tr>")
    parts.append(
        "<th>Status</th><th>Method</th><th>Path</th>"
        "<th>Case</th><th>Elapsed (ms)</th><th>Error</th>"
    )
    parts.append("</tr></thead>")
    parts.append("<tbody>" + rows_joined + "</tbody>")
    parts.append("</table>")
    parts.append(
        '<div class="footer">Generated by Test Platform '
        + _MID
        + " F015 "
        + _AMP
        + "nbsp;F015 报告导出</div>"
    )
    # 修正：上面 _AMP + "nbsp;F015..." 应该是 "+nbsp;F015..." 让我们清理一下
    # 实际写法：把 "F015 报告导出" 直接写
    parts[-1] = (
        '<div class="footer">Generated by Test Platform '
        + _MID
        + " F015 报告导出</div>"
    )
    parts.append("</body>")
    parts.append("</html>")
    return "".join(parts)


def export_run(
    run: Any, results: List[Any], fmt: str
) -> Tuple[str, str, str]:
    """F015 主入口。

    Returns:
        (content, media_type, filename)
    """
    if fmt not in ("json", "html"):
        raise ValueError(f"format must be 'json' or 'html', got {fmt!r}")

    payload = build_payload(run, results)
    if fmt == "json":
        content = render_json(payload)
        media_type = "application/json; charset=utf-8"
    else:
        content = render_html(payload)
        media_type = "text/html; charset=utf-8"

    ts = (
        run.started_at.strftime("%Y%m%d-%H%M%S")
        if isinstance(run.started_at, datetime)
        else "unknown"
    )
    filename = f"run-{ts}-{run.id}.{fmt}"
    return content, media_type, filename
