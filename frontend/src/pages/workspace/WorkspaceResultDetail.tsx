import { useQuery } from "@tanstack/react-query";
import { Alert, Card, Descriptions, Empty, Space, Table, Tabs, Tag, Typography } from "antd";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import JsonPreview from "../../components/JsonPreview";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { environmentsApi } from "../../api/environments";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import type { TestResult } from "../../api/types";
import { formatDateTime, formatMilliseconds } from "../../utils/format";

const { Text } = Typography;

const TAB_KEYS = ["request", "response", "assertions", "error", "overview"] as const;
type TabKey = (typeof TAB_KEYS)[number];

function pickInitialTab(status: TestResult["status"]): TabKey {
  if (status === "passed") return "response";
  if (status === "failed") return "assertions";
  if (status === "error") return "error";
  return "request";
}

function readTab(searchParams: URLSearchParams, fallback: TabKey): TabKey {
  const raw = searchParams.get("tab");
  return (TAB_KEYS as readonly string[]).includes(raw ?? "")
    ? (raw as TabKey)
    : fallback;
}

function statusColor(status: TestResult["status"]): string {
  if (status === "passed") return "green";
  if (status === "failed") return "red";
  if (status === "error") return "orange";
  return "default";
}

function asEntries(value: unknown): [string, string][] {
  if (!value || typeof value !== "object") return [];
  return Object.entries(value as Record<string, unknown>).map(([k, v]) => [
    k,
    v === null || v === undefined ? "—" : typeof v === "string" ? v : JSON.stringify(v),
  ]);
}

export default function WorkspaceResultDetailPage() {
  const navigate = useNavigate();
  const { projectId = "", runId = "", resultId = "" } = useParams();
  const { refresh: refreshWorkspace } = useProjectWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();

  const resultQuery = useQuery({
    queryKey: queryKeys.result(resultId),
    queryFn: () => runsApi.result(resultId),
    enabled: Boolean(resultId),
  });
  const runQuery = useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => runsApi.get(runId),
    enabled: Boolean(runId),
  });
  const environmentsQuery = useQuery({
    queryKey: queryKeys.environments(projectId, ""),
    queryFn: () => environmentsApi.list(projectId),
    enabled: Boolean(projectId),
  });

  if (resultQuery.isLoading || runQuery.isLoading) {
    return <LoadingBlock rows={7} />;
  }
  if (resultQuery.isError) {
    return <ErrorState error={resultQuery.error} onRetry={() => void resultQuery.refetch()} />;
  }
  if (runQuery.isError) {
    return <ErrorState error={runQuery.error} onRetry={() => void runQuery.refetch()} />;
  }

  const result = resultQuery.data;
  const run = runQuery.data;
  if (!result) {
    return <ErrorState error={new Error("Result 不存在或已被删除")} />;
  }
  if (!run) {
    return <ErrorState error={new Error("所属 Run 不存在或已被删除")} />;
  }
  if (result.run_id !== runId) {
    return <ErrorState error={new Error("该 Result 不属于当前 Run")} />;
  }
  if (run.project_id !== projectId) {
    return <ErrorState error={new Error("该 Run 不属于当前项目")} />;
  }

  const initialTab = pickInitialTab(result.status);
  const activeTab = readTab(searchParams, initialTab);
  const environment = environmentsQuery.data?.items.find((item) => item.id === result.environment_id);
  const requestHeaders = asEntries(result.request_snapshot?.headers);
  const requestBody = result.request_snapshot?.body;
  const responseHeaders = asEntries(result.response_snapshot?.headers);
  const responseBody = result.response_snapshot?.body;
  const responseStatus = typeof responseBody === "object" && responseBody
    ? (responseBody as { status?: number }).status
    : undefined;

  const updateTab = (key: string) => {
    if (!TAB_KEYS.includes(key as TabKey)) return;
    const next = new URLSearchParams(searchParams);
    next.set("tab", key);
    setSearchParams(next, { replace: true });
  };

  return (
    <>
      <PageHeader
        title={result.case_name}
        description={`Result ${result.id}`}
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "测试报告", href: `/projects/${projectId}/workspace/report` },
          { title: run.name, href: `/projects/${projectId}/workspace/report/${runId}` },
          { title: result.case_name },
        ]}
        extra={
          <Space>
            <button
              type="button"
              className="ant-btn ant-btn-default"
              onClick={() =>
                navigate(
                  `/projects/${projectId}/workspace/case/${result.test_case_id}?from=report&runId=${runId}&resultId=${resultId}`,
                )
              }
            >
              跳到 Case 编辑器
            </button>
            <button
              type="button"
              className="ant-btn ant-btn-default"
              onClick={() => {
                void resultQuery.refetch();
                void runQuery.refetch();
                void environmentsQuery.refetch();
                refreshWorkspace();
              }}
            >
              刷新
            </button>
          </Space>
        }
      />
      {result.response_snapshot?.body_truncated ? (
        <Alert
          className="inline-warning"
          type="warning"
          showIcon
          message="响应已被后端截断"
          description="响应 Body 超过 64 KiB，后端只返回前 64 KiB 内容。"
        />
      ) : null}
      <Card className="surface-card" style={{ marginBottom: 18 }}>
        <Space direction="vertical" size={4}>
          <Space>
            <Tag color={statusColor(result.status)}>{result.status}</Tag>
            <Text strong>{result.case_method}</Text>
            <Text code>{result.case_path}</Text>
            <Text type="secondary">{formatMilliseconds(result.elapsed_ms)}</Text>
          </Space>
          <Text type="secondary">
            环境：{environment ? `${environment.name} · ${environment.base_url}` : result.environment_id}
          </Text>
          <Space>
            <Text type="secondary">开始：{formatDateTime(result.started_at)}</Text>
            <Text type="secondary">结束：{formatDateTime(result.finished_at)}</Text>
          </Space>
        </Space>
      </Card>
      <Card className="surface-card">
        <Tabs
          activeKey={activeTab}
          onChange={updateTab}
          items={[
            {
              key: "request",
              label: "请求",
              children: <RequestTab headers={requestHeaders} body={requestBody} />,
            },
            {
              key: "response",
              label: "响应",
              children: <ResponseTab status={responseStatus} headers={responseHeaders} body={responseBody} />,
            },
            {
              key: "assertions",
              label: "断言",
              children: <AssertionsTab assertions={result.assertions_snapshot} />,
            },
            {
              key: "error",
              label: "错误",
              children: <ErrorTab code={result.error_code} message={result.error_message} />,
            },
            {
              key: "overview",
              label: "概览",
              children: <OverviewTab result={result} />,
            },
          ]}
        />
      </Card>
    </>
  );
}

function RequestTab({ headers, body }: { headers: [string, string][]; body: unknown }) {
  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      <Card type="inner" title="Headers">
        {headers.length === 0 ? <Empty description="无 Headers 快照" /> : (
          <Descriptions bordered column={1} size="small">
            {headers.map(([k, v]) => (
              <Descriptions.Item key={k} label={k}>
                <Text code>{v}</Text>
              </Descriptions.Item>
            ))}
          </Descriptions>
        )}
      </Card>
      <Card type="inner" title="Body">
        {body === null || body === undefined ? <Empty description="无 Body 快照" /> : <JsonPreview value={body} />}
      </Card>
    </Space>
  );
}

function ResponseTab({
  status,
  headers,
  body,
}: {
  status: number | undefined;
  headers: [string, string][];
  body: unknown;
}) {
  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      <Card type="inner" title={status ? `状态：${status}` : "状态"}>
        <Space>
          {status ? (
            <Tag color={status >= 500 ? "red" : status >= 400 ? "orange" : status >= 300 ? "blue" : "green"}>
              {status}
            </Tag>
          ) : null}
          {status && status >= 200 && status < 300 ? <Tag color="green">2xx</Tag> : null}
          {status && status >= 300 && status < 400 ? <Tag color="blue">3xx</Tag> : null}
          {status && status >= 400 && status < 500 ? <Tag color="orange">4xx</Tag> : null}
          {status && status >= 500 ? <Tag color="red">5xx</Tag> : null}
        </Space>
      </Card>
      <Card type="inner" title="Headers">
        {headers.length === 0 ? <Empty description="无 Headers 快照" /> : (
          <Descriptions bordered column={1} size="small">
            {headers.map(([k, v]) => (
              <Descriptions.Item key={k} label={k}>
                <Text code>{v}</Text>
              </Descriptions.Item>
            ))}
          </Descriptions>
        )}
      </Card>
      <Card type="inner" title="Body">
        {body === null || body === undefined ? <Empty description="无 Body 快照" /> : <JsonPreview value={body} />}
      </Card>
    </Space>
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

function AssertionsTab({ assertions }: { assertions: unknown }) {
  if (!Array.isArray(assertions) || assertions.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无断言快照" />;
  }
  const rows: AssertionRow[] = assertions.map((item) => item as AssertionRow);
  return (
    <Table<AssertionRow>
      rowKey={(_value, index) => String(index)}
      scroll={{ x: "max-content" }}
      size="small"
      dataSource={rows}
      pagination={false}
      columns={[
        {
          title: "状态",
          width: 80,
          render: (_value, row) =>
            row.passed ? <Tag color="green">通过</Tag> : <Tag color="red">失败</Tag>,
        },
        { title: "类型", dataIndex: "type", width: 160 },
        { title: "操作符", dataIndex: "operator", width: 100 },
        {
          title: "期望",
          dataIndex: "expected",
          render: (value) => <Text code>{JSON.stringify(value)}</Text>,
        },
        {
          title: "实际",
          dataIndex: "actual",
          render: (value) => <Text code>{JSON.stringify(value)}</Text>,
        },
        {
          title: "错误",
          dataIndex: "message",
          render: (value: string | undefined) => value || "—",
        },
      ]}
    />
  );
}

function ErrorTab({ code, message }: { code: string | null; message: string | null }) {
  if (!code && !message) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本条 Result 没有错误" />;
  }
  return (
    <Card type="inner" title="错误">
      <Descriptions bordered column={1}>
        {code ? (
          <Descriptions.Item label="错误码">
            <Text code>{code}</Text>
          </Descriptions.Item>
        ) : null}
        {message ? (
          <Descriptions.Item label="错误信息">
            <Text type="danger">{message}</Text>
          </Descriptions.Item>
        ) : null}
        {!message && code ? (
          <Descriptions.Item label="说明">
            <Text type="secondary">后端仅返回错误码，无详细描述。</Text>
          </Descriptions.Item>
        ) : null}
      </Descriptions>
    </Card>
  );
}

function OverviewTab({ result }: { result: TestResult }) {
  const items: { key: string; label: string; children: React.ReactNode }[] = [
    { key: "id", label: "Result ID", children: <Text code>{result.id}</Text> },
    { key: "case", label: "Case ID", children: <Text code>{result.test_case_id}</Text> },
    { key: "env", label: "Environment", children: <Text code>{result.environment_id}</Text> },
    { key: "status", label: "状态", children: <Tag color={statusColor(result.status)}>{result.status}</Tag> },
    { key: "method", label: "Method", children: <Text code>{result.case_method}</Text> },
    { key: "path", label: "Path", children: <Text code>{result.case_path}</Text> },
    { key: "duration", label: "耗时", children: formatMilliseconds(result.elapsed_ms) },
    { key: "started", label: "开始", children: formatDateTime(result.started_at) },
    { key: "finished", label: "结束", children: formatDateTime(result.finished_at) },
    { key: "created", label: "记录时间", children: formatDateTime(result.created_at) },
  ];
  return <Descriptions bordered column={{ xs: 1, md: 2 }} items={items} />;
}
