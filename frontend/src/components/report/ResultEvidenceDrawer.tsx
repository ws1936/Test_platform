// Result Evidence Drawer：Request / Response / Assertion 只读证据。

import {
  ClockCircleOutlined,
  CodeOutlined,
  FileSearchOutlined,
  LinkOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Badge,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Segmented,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useReportEnvironments, useReportResult, useReportRun } from "../../api/report";
import type { Environment, TestResult } from "../../api/types";
import { formatDateTime, formatMilliseconds } from "../../utils/format";
import { stringifyJson } from "../../utils/json";
import { ResultStatusTag } from "../StatusTags";

const { Text } = Typography;

type EvidenceTab = "request" | "response" | "assertions";

const TAB_LABELS: Record<EvidenceTab, string> = {
  request: "Request",
  response: "Response",
  assertions: "Assertion",
};

const TAB_ICONS: Record<EvidenceTab, React.ReactNode> = {
  request: <LinkOutlined />,
  response: <FileSearchOutlined />,
  assertions: <CodeOutlined />,
};

const STATUS_GROUP_COLOR: Record<number, string> = {
  2: "success",
  3: "processing",
  4: "warning",
  5: "error",
};

function statusGroupOf(status?: number): { label: string; color: string } | null {
  if (status === undefined) return null;
  if (status >= 200 && status < 300) return { label: "2xx", color: STATUS_GROUP_COLOR[2] };
  if (status >= 300 && status < 400) return { label: "3xx", color: STATUS_GROUP_COLOR[3] };
  if (status >= 400 && status < 500) return { label: "4xx", color: STATUS_GROUP_COLOR[4] };
  if (status >= 500 && status < 600) return { label: "5xx", color: STATUS_GROUP_COLOR[5] };
  return null;
}

function pickInitialTab(result: TestResult | undefined): EvidenceTab {
  if (!result) return "request";
  if (result.status === "passed") return "response";
  if (result.status === "failed") return "assertions";
  if (result.status === "error") return "response";
  return "request";
}

interface ResultEvidenceDrawerProps {
  open: boolean;
  projectId: string;
  runId: string;
  resultId: string;
  onClose?: () => void;
}

export function ResultEvidenceDrawer({
  open,
  projectId,
  runId,
  resultId,
  onClose,
}: ResultEvidenceDrawerProps) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const tabFromUrl: EvidenceTab | null =
    rawTab === "request" || rawTab === "response" || rawTab === "assertions"
      ? rawTab
      : null;

  const resultQuery = useReportResult(open ? resultId : "");
  const runQuery = useReportRun(open ? runId : "");
  const envQuery = useReportEnvironments(open ? projectId : "");

  const [internalTab, setInternalTab] = useState<EvidenceTab>(tabFromUrl ?? "request");

  useEffect(() => {
    if (open && !tabFromUrl) {
      const fallback = pickInitialTab(resultQuery.data);
      setInternalTab(fallback);
    }
    if (tabFromUrl) setInternalTab(tabFromUrl);
  }, [open, tabFromUrl, resultQuery.data]);

  const activeTab: EvidenceTab = tabFromUrl ?? internalTab;

  const handleTabChange = (next: string | number) => {
    const value = String(next) as EvidenceTab;
    setInternalTab(value);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("tab", value);
    setSearchParams(nextParams, { replace: true });
  };

  const handleClose = () => {
    if (onClose) onClose();
    else navigate(`/projects/${projectId}/workspace/report/${runId}`);
  };

  const result = resultQuery.data;
  const run = runQuery.data;
  const environment = useMemo<Environment | null>(() => {
    if (!result || !envQuery.data) return null;
    return envQuery.data.items.find((item) => item.id === result.environment_id) ?? null;
  }, [result, envQuery.data]);

  const responseStatus = readResponseStatus(result);
  const requestHeaders = asEntries(result?.request_snapshot?.headers);
  const requestBody = result?.request_snapshot?.body;
  const responseHeaders = asEntries(result?.response_snapshot?.headers);
  const responseBody = result?.response_snapshot?.body;
  const bodyTruncated = Boolean(result?.response_snapshot?.body_truncated);

  return (
    <Drawer
      open={open}
      onClose={handleClose}
      width={720}
      destroyOnClose
      title={
        result ? (
          <Space direction="vertical" size={2} className="report-drawer-title">
            <Space>
              <ResultStatusTag status={result.status} />
              <Text strong>{result.case_name}</Text>
              <Text type="secondary">·</Text>
              <Tag color="default">{result.case_method}</Tag>
              <Text code>{result.case_path}</Text>
            </Space>
            <Text type="secondary" className="report-drawer-subtitle">
              {run ? `Run ${run.name} · ${environment ? environment.name : result.environment_id}` : "加载 Run 中…"}
              {result.elapsed_ms !== null ? ` · ${formatMilliseconds(result.elapsed_ms)}` : ""}
            </Text>
          </Space>
        ) : (
          "Result Evidence"
        )
      }
      extra={
        result ? (
          <Space>
            <Button
              onClick={() =>
                navigate(
                  `/projects/${projectId}/workspace/case/${result.test_case_id}?from=report&runId=${runId}&resultId=${resultId}`,
                )
              }
            >
              跳到 Case 编辑器
            </Button>
            <Button type="primary" onClick={handleClose}>
              关闭
            </Button>
          </Space>
        ) : null
      }
    >
      {bodyTruncated ? (
        <Alert
          type="warning"
          showIcon
          message="响应 Body 已被后端截断"
          description="响应超过 64 KiB，Viewer 只展示后端返回的快照内容。"
          className="report-evidence-alert"
        />
      ) : null}

      {resultQuery.isLoading ? (
        <div className="report-drawer-loading">
          <Spin tip="正在加载 Result 快照…" />
        </div>
      ) : resultQuery.isError ? (
        <ResultEvidenceError
          error={resultQuery.error}
          onRetry={() => void resultQuery.refetch()}
        />
      ) : !result ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="该 Result 不存在或已被删除"
        />
      ) : run && result.run_id !== runId ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="该 Result 不属于当前 Run"
        />
      ) : run && run.project_id !== projectId ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="该 Run 不属于当前项目"
        />
      ) : (
        <>
          <Segmented<EvidenceTab>
            value={activeTab}
            onChange={handleTabChange}
            options={[
              { value: "request", label: TAB_LABELS.request, icon: TAB_ICONS.request },
              { value: "response", label: TAB_LABELS.response, icon: TAB_ICONS.response },
              { value: "assertions", label: TAB_LABELS.assertions, icon: TAB_ICONS.assertions },
            ]}
            className="report-drawer-segmented"
          />

          <div className="report-drawer-content">
            {activeTab === "request" ? (
              <RequestPanel
                method={result.case_method}
                url={asString(result.request_snapshot?.url)}
                configuredUrl={buildConfiguredUrl(environment, result.case_path)}
                headers={requestHeaders}
                body={requestBody}
              />
            ) : null}

            {activeTab === "response" ? (
              <ResponsePanel
                status={responseStatus}
                headers={responseHeaders}
                body={responseBody}
                truncated={bodyTruncated}
              />
            ) : null}

            {activeTab === "assertions" ? (
              <AssertionsPanel
                assertions={result.assertions_snapshot}
                errorCode={result.error_code}
                errorMessage={result.error_message}
                status={result.status}
                elapsedMs={result.elapsed_ms}
                startedAt={result.started_at}
                finishedAt={result.finished_at}
              />
            ) : null}
          </div>
        </>
      )}
    </Drawer>
  );
}

function ResultEvidenceError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message = error instanceof Error ? error.message : "未知错误";
  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <Space direction="vertical" size={4} align="center">
          <Text strong>Result 加载失败</Text>
          <Text type="secondary">{message}</Text>
          <Button type="primary" onClick={onRetry}>
            重试
          </Button>
        </Space>
      }
    />
  );
}

function RequestPanel({
  method,
  url,
  configuredUrl,
  headers,
  body,
}: {
  method: string;
  url: string | null;
  configuredUrl: string | null;
  headers: [string, string][];
  body: unknown;
}) {
  return (
    <Space direction="vertical" size={16} className="report-evidence-section">
      <div>
        <Text type="secondary" className="report-evidence-label">Method / URL</Text>
        <div className="report-evidence-method">
          <Tag color="blue" className="report-evidence-method-tag">{method}</Tag>
          <div className="report-evidence-url-block">
            {url ? (
              <>
                <Text type="secondary" className="report-evidence-url-label">Actual Request URL</Text>
                <Text code className="report-evidence-url">{url}</Text>
              </>
            ) : configuredUrl ? (
              <>
                <Text type="secondary" className="report-evidence-url-label">Configured URL</Text>
                <Text code className="report-evidence-url">{configuredUrl}</Text>
                <Text type="secondary" className="report-evidence-url-hint">
                  来自 Environment.base_url + Case path，非请求实际 URL。
                </Text>
              </>
            ) : (
              <Text type="secondary">无 URL 快照</Text>
            )}
          </div>
        </div>
      </div>
      <HeaderBlock title="Request Headers" entries={headers} />
      <BodyBlock title="Request Body" value={body} emptyHint="无 Request Body 快照" />
    </Space>
  );
}

function ResponsePanel({
  status,
  headers,
  body,
  truncated,
}: {
  status: number | undefined;
  headers: [string, string][];
  body: unknown;
  truncated: boolean;
}) {
  const group = statusGroupOf(status);
  return (
    <Space direction="vertical" size={16} className="report-evidence-section">
      <div>
        <Text type="secondary" className="report-evidence-label">Status / Duration</Text>
        <div className="report-evidence-status">
          {status !== undefined ? (
            <Tag color={group?.color ?? "default"} className="report-evidence-status-tag">
              {status}
            </Tag>
          ) : (
            <Tag color="default">—</Tag>
          )}
          {group ? <Badge color={group.color} text={group.label} /> : null}
          {truncated ? (
            <Text type="warning" className="report-evidence-truncated">
              响应 Body 已被后端截断
            </Text>
          ) : null}
        </div>
      </div>
      <HeaderBlock title="Response Headers" entries={headers} />
      <BodyBlock
        title="Response Body"
        value={body}
        emptyHint="无 Response Body 快照"
        truncated={truncated}
      />
    </Space>
  );
}

function AssertionsPanel({
  assertions,
  errorCode,
  errorMessage,
  status,
  elapsedMs,
  startedAt,
  finishedAt,
}: {
  assertions: TestResult["assertions_snapshot"];
  errorCode: string | null;
  errorMessage: string | null;
  status: TestResult["status"];
  elapsedMs: number | null;
  startedAt: string | null;
  finishedAt: string | null;
}) {
  if (!Array.isArray(assertions) || assertions.length === 0) {
    if (status === "error" && (errorCode || errorMessage)) {
      return <ErrorPanel code={errorCode} message={errorMessage} />;
    }
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="无断言快照"
      />
    );
  }

  const passed = assertions.filter((a) => isPassed(a)).length;
  const failed = assertions.length - passed;

  const rows = (assertions as AssertionRow[]).map((row, index) => ({
    key: index,
    index,
    row,
  }));

  return (
    <Space direction="vertical" size={12} className="report-evidence-section">
      <div className="report-evidence-assertion-summary">
        <Text type="secondary">断言 {passed} / {assertions.length} 通过</Text>
        {failed > 0 ? <Badge status="error" text={`失败 ${failed}`} /> : null}
        {errorCode ? <Tag color="volcano">{errorCode}</Tag> : null}
      </div>
      <Table
        size="small"
        pagination={false}
        dataSource={rows}
        columns={[
          {
            title: "状态",
            dataIndex: "index",
            width: 96,
            render: (_value, record) =>
              record.row.passed ? (
                <Tag color="success">通过</Tag>
              ) : (
                <Tag color="error">失败</Tag>
              ),
          },
          {
            title: "类型",
            dataIndex: "row",
            render: (row: AssertionRow) => <Tag>{row.type ?? "—"}</Tag>,
          },
          {
            title: "操作符",
            dataIndex: "row",
            width: 110,
            render: (row: AssertionRow) => <Text type="secondary">{row.operator ?? "—"}</Text>,
          },
          {
            title: "期望",
            dataIndex: "row",
            render: (row: AssertionRow) => <Text code>{stringifyJson(row.expected, "—")}</Text>,
          },
          {
            title: "实际",
            dataIndex: "row",
            render: (row: AssertionRow) => <Text code>{stringifyJson(row.actual, "—")}</Text>,
          },
          {
            title: "说明",
            dataIndex: "row",
            render: (row: AssertionRow) => row.message ?? "—",
          },
        ]}
      />
      {errorCode || errorMessage ? <ErrorPanel code={errorCode} message={errorMessage} /> : null}
      <div className="report-evidence-meta">
        <Space size="large">
          <span>
            <ClockCircleOutlined /> {formatMilliseconds(elapsedMs)}
          </span>
          <span>Started {formatDateTime(startedAt)}</span>
          <span>Finished {formatDateTime(finishedAt)}</span>
        </Space>
      </div>
    </Space>
  );
}

function ErrorPanel({ code, message }: { code: string | null; message: string | null }) {
  if (!code && !message) {
    return null;
  }
  return (
    <div className="report-evidence-error">
      <Descriptions
        column={1}
        size="small"
        bordered
        items={[
          code
            ? { key: "code", label: "错误码", children: <Text code>{code}</Text> }
            : { key: "code-empty", label: "错误码", children: <Text type="secondary">—</Text> },
          message
            ? {
                key: "message",
                label: "错误信息",
                children: (
                  <Text type="danger" className="report-evidence-error-message">
                    {message}
                  </Text>
                ),
              }
            : { key: "message-empty", label: "错误信息", children: <Text type="secondary">—</Text> },
        ]}
      />
      {!message && code ? (
        <Text type="secondary" className="report-evidence-error-hint">
          后端仅返回错误码，无详细描述。
        </Text>
      ) : null}
    </div>
  );
}

function HeaderBlock({
  title,
  entries,
}: {
  title: string;
  entries: [string, string][];
}) {
  return (
    <div>
      <Text type="secondary" className="report-evidence-label">{title}</Text>
      <div className="report-evidence-card">
        {entries.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`无 ${title} 快照`} />
        ) : (
          <Descriptions
            column={1}
            size="small"
            bordered
            items={entries.map(([key, value]) => ({
              key,
              label: <Text strong>{key}</Text>,
              children: <Text code>{value}</Text>,
            }))}
          />
        )}
      </div>
    </div>
  );
}

function BodyBlock({
  title,
  value,
  emptyHint,
  truncated,
}: {
  title: string;
  value: unknown;
  emptyHint: string;
  truncated?: boolean;
}) {
  return (
    <div>
      <Text type="secondary" className="report-evidence-label">{title}</Text>
      <div className="report-evidence-card report-evidence-card--body">
        {value === null || value === undefined ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyHint} />
        ) : (
          <pre className="report-evidence-pre">{stringifyJson(value, "")}</pre>
        )}
        {truncated ? (
          <Text type="warning" className="report-evidence-truncated">
            响应 Body 已被后端截断，当前内容不是完整响应。
          </Text>
        ) : null}
      </div>
    </div>
  );
}

interface AssertionRow {
  type?: string;
  operator?: string;
  expected?: unknown;
  actual?: unknown;
  passed?: boolean;
  message?: string;
}

function isPassed(row: unknown): boolean {
  if (!row || typeof row !== "object") return false;
  return (row as { passed?: unknown }).passed === true;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string" || value.length === 0) return null;
  return value;
}

function buildConfiguredUrl(env: Environment | null, path: string | null): string | null {
  if (!env || !env.base_url || !path) return null;
  return `${env.base_url.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

function asEntries(value: unknown): [string, string][] {
  if (!value || typeof value !== "object") return [];
  return Object.entries(value as Record<string, unknown>).map(([k, v]) => [
    k,
    formatHeaderValue(v),
  ]);
}

function formatHeaderValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return "—";
  }
}

function readResponseStatus(result: TestResult | undefined): number | undefined {
  if (!result || !result.response_snapshot || typeof result.response_snapshot !== "object") {
    return undefined;
  }
  const value = (result.response_snapshot as { status?: unknown }).status;
  return typeof value === "number" ? value : undefined;
}
