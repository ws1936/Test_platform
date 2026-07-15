import { PlayCircleOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Col, Descriptions, Empty, Row, Space, Statistic, Table, Tabs, Tag, Typography } from "antd";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { environmentsApi } from "../../api/environments";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import type {
  FailureItem,
  FailureList,
  TestResult,
  TestResultList,
  TestRun,
} from "../../api/types";
import { formatDateTime, formatDuration, formatMilliseconds, formatPercent } from "../../utils/format";

const { Text, Paragraph } = Typography;

const TAB_KEYS = ["overview", "failures", "results", "meta"] as const;
type TabKey = (typeof TAB_KEYS)[number];

function readTabFromUrl(searchParams: URLSearchParams, fallback: TabKey): TabKey {
  const raw = searchParams.get("tab");
  return (TAB_KEYS as readonly string[]).includes(raw ?? "")
    ? (raw as TabKey)
    : fallback;
}

export default function WorkspaceReportDetailPage() {
  const navigate = useNavigate();
  const { projectId = "", runId = "" } = useParams();
  const { refresh: refreshWorkspace } = useProjectWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = readTabFromUrl(searchParams, "overview");

  const runQuery = useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => runsApi.get(runId),
    enabled: Boolean(runId),
  });
  const failuresQuery = useQuery({
    queryKey: queryKeys.runFailures(runId),
    queryFn: () => runsApi.failures(runId),
    enabled: Boolean(runId),
  });
  const resultsQuery = useQuery({
    queryKey: queryKeys.runResults(runId),
    queryFn: () => runsApi.results(runId),
    enabled: Boolean(runId),
  });
  const environmentsQuery = useQuery({
    queryKey: queryKeys.environments(projectId, ""),
    queryFn: () => environmentsApi.list(projectId),
    enabled: Boolean(projectId),
  });

  if (runQuery.isLoading) return <LoadingBlock rows={7} />;
  if (runQuery.isError) {
    return <ErrorState error={runQuery.error} onRetry={() => void runQuery.refetch()} />;
  }
  const run: TestRun | undefined = runQuery.data;
  if (!run) {
    return <ErrorState error={new Error("Run 不存在或已被删除")} />;
  }
  if (run.project_id !== projectId) {
    return <ErrorState error={new Error("该 Run 不属于当前项目")} />;
  }

  const failures: FailureList | undefined = failuresQuery.data;
  const results: TestResultList | undefined = resultsQuery.data;
  const environment = environmentsQuery.data?.items.find((item) => item.id === run.environment_id);
  const totalFailed = run.failed + run.error;
  const passRate = run.pass_rate;

  const initialTab: TabKey = totalFailed > 0 ? "failures" : "overview";
  const currentTab: TabKey = TAB_KEYS.includes(activeTab) ? activeTab : initialTab;

  const updateTab = (key: string) => {
    if (!TAB_KEYS.includes(key as TabKey)) return;
    const next = new URLSearchParams(searchParams);
    next.set("tab", key);
    setSearchParams(next, { replace: true });
  };

  return (
    <>
      <PageHeader
        title={run.name}
        description={`Run ID ${run.id}`}
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "测试报告", href: `/projects/${projectId}/workspace/report` },
          { title: run.name },
        ]}
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => navigate(`/projects/${projectId}/workspace/run?scope=${run.scope}&scopeId=${run.id}`)}
            >
              再次执行
            </Button>
            <Button
              onClick={() => {
                void runQuery.refetch();
                void failuresQuery.refetch();
                void resultsQuery.refetch();
                refreshWorkspace();
              }}
            >
              刷新
            </Button>
          </Space>
        }
      />
      <Card className="surface-card" style={{ marginBottom: 18 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={8}>
            <Space direction="vertical" size={4}>
              <Space>
                <Tag color={run.status === "finished" ? "green" : totalFailed > 0 ? "red" : "default"}>
                  {run.status}
                </Tag>
                <Text strong>{run.name}</Text>
              </Space>
              <Text type="secondary">
                环境：{environment ? `${environment.name} · ${environment.base_url}` : run.environment_id}
              </Text>
              <Text type="secondary">触发人：{run.triggered_by ?? "—"}</Text>
            </Space>
          </Col>
          <Col xs={24} md={8}>
            <Statistic
              title="通过率"
              value={passRate ?? undefined}
              precision={2}
              formatter={(value) => formatPercent(value as number | undefined)}
              valueStyle={{
                color:
                  passRate && passRate >= 0.8
                    ? "#52c41a"
                    : passRate && passRate >= 0.5
                      ? "#faad14"
                      : "#ff4d4f",
              }}
            />
          </Col>
          <Col xs={24} md={8}>
            <Statistic title="耗时" value={formatDuration(run.elapsed_seconds)} />
          </Col>
        </Row>
      </Card>

      <Card className="surface-card">
        <Tabs
          activeKey={currentTab}
          onChange={updateTab}
          items={[
            {
              key: "overview",
              label: "概览",
              children: (
                <OverviewTab
                  run={run}
                  results={results?.items ?? []}
                />
              ),
            },
            {
              key: "failures",
              label: `失败原因 (${failures?.total_failures ?? totalFailed})`,
              children: (
                <FailureListTab
                  loading={failuresQuery.isLoading}
                  error={failuresQuery.isError ? failuresQuery.error : undefined}
                  items={failures?.items ?? []}
                  onRetry={() => void failuresQuery.refetch()}
                  navigateToResult={(resultId) =>
                    navigate(`/projects/${projectId}/workspace/report/${runId}/result/${resultId}`)
                  }
                />
              ),
            },
            {
              key: "results",
              label: `全部 Result (${results?.items.length ?? run.total})`,
              children: (
                <ResultListTab
                  loading={resultsQuery.isLoading}
                  error={resultsQuery.isError ? resultsQuery.error : undefined}
                  items={results?.items ?? []}
                  onRetry={() => void resultsQuery.refetch()}
                  navigateToResult={(resultId) =>
                    navigate(`/projects/${projectId}/workspace/report/${runId}/result/${resultId}`)
                  }
                />
              ),
            },
            {
              key: "meta",
              label: "元信息",
              children: <MetaTab run={run} />,
            },
          ]}
        />
      </Card>
    </>
  );
}

interface OverviewTabProps {
  run: TestRun;
  results: TestResult[];
}

function OverviewTab({ run, results }: OverviewTabProps) {
  const head = results.slice(0, 5);
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}><Statistic title="总数" value={run.total} /></Col>
        <Col xs={12} md={6}>
          <Statistic title="通过" value={run.passed} valueStyle={{ color: "#52c41a" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="失败" value={run.failed} valueStyle={{ color: "#ff4d4f" }} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="错误" value={run.error} valueStyle={{ color: "#fa8c16" }} />
        </Col>
      </Row>
      <Card type="inner" title="前 5 条 Result">
        {head.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无 Result 数据" /> : (
          <ul style={{ paddingLeft: 18, margin: 0 }}>
            {head.map((result) => (
              <li key={result.id}>
                <Text>{result.case_method}</Text>{" "}
                <Text code>{result.case_path}</Text>{" "}
                <Text type="secondary">{result.case_name}</Text>{" "}
                <Tag color={result.status === "passed" ? "green" : result.status === "failed" ? "red" : "orange"}>
                  {result.status}
                </Tag>{" "}
                <Text type="secondary">{formatMilliseconds(result.elapsed_ms)}</Text>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </Space>
  );
}

interface FailureListTabProps {
  items: FailureItem[];
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  navigateToResult: (resultId: string) => void;
}

function FailureListTab({ items, loading, error, onRetry, navigateToResult }: FailureListTabProps) {
  if (loading) return <LoadingBlock rows={3} />;
  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (items.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本次执行无失败项" />;
  }
  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      {items.map((item) => (
        <Card
          key={`${item.result_id}-${item.failure_index}`}
          type="inner"
          hoverable
          onClick={() => navigateToResult(item.result_id)}
          style={{ borderColor: item.error_code ? "#fa8c16" : "#ff4d4f", cursor: "pointer" }}
        >
          <Space direction="vertical" size={4} style={{ width: "100%" }}>
            <Space>
              <Tag color="red">✗</Tag>
              <Text strong>{item.case_name}</Text>
              <Text code>{item.case_method}</Text>
              <Text code>{item.case_path}</Text>
              <Text type="secondary">{formatDateTime(item.started_at)}</Text>
            </Space>
            <Space size={16} wrap>
              <span>
                <Text type="secondary">断言：</Text>
                <Tag>{item.assertion_type}</Tag>
                <Text type="secondary">操作符：</Text>
                <Tag>{item.assertion_operator}</Tag>
              </span>
            </Space>
            <Space size={16} wrap>
              <span>
                <Text type="secondary">Expected：</Text>
                <Text code>{JSON.stringify(item.expected)}</Text>
              </span>
              <span>
                <Text type="secondary">Actual：</Text>
                <Text code>{JSON.stringify(item.actual)}</Text>
              </span>
            </Space>
            {item.message ? <Paragraph type="danger">{item.message}</Paragraph> : null}
            {item.error_code ? <Text type="secondary">错误码：{item.error_code}</Text> : null}
          </Space>
        </Card>
      ))}
    </Space>
  );
}

interface ResultListTabProps {
  items: TestResult[];
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  navigateToResult: (resultId: string) => void;
}

function ResultListTab({ items, loading, error, onRetry, navigateToResult }: ResultListTabProps) {
  if (loading) return <LoadingBlock rows={4} />;
  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (items.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本次 Run 没有 Result 数据" />;
  }
  return (
    <Table
      rowKey="id"
      size="small"
      dataSource={items}
      pagination={false}
      onRow={(row) => ({
        onClick: () => navigateToResult(row.id),
        style: { cursor: "pointer" },
      })}
      columns={[
        {
          title: "状态",
          dataIndex: "status",
          width: 96,
          render: (status) => (
            <Tag color={status === "passed" ? "green" : status === "failed" ? "red" : "orange"}>
              {status}
            </Tag>
          ),
        },
        { title: "Method", dataIndex: "case_method", width: 100 },
        { title: "名称", dataIndex: "case_name" },
        { title: "Path", dataIndex: "case_path", ellipsis: true, render: (path: string) => <Text code>{path}</Text> },
        { title: "耗时", dataIndex: "elapsed_ms", width: 100, render: formatMilliseconds },
        { title: "错误", dataIndex: "error_message", ellipsis: true, render: (value: string | null) => value || "—" },
      ]}
    />
  );
}

function MetaTab({ run }: { run: TestRun }) {
  const items: { key: string; label: string; children: React.ReactNode }[] = [
    { key: "id", label: "Run ID", children: <Text code>{run.id}</Text> },
    { key: "project", label: "Project", children: <Text code>{run.project_id}</Text> },
    { key: "environment", label: "Environment", children: <Text code>{run.environment_id}</Text> },
    { key: "scope", label: "Scope", children: <Text code>{run.scope}</Text> },
    { key: "status", label: "Status", children: <Text code>{run.status}</Text> },
    { key: "trigger", label: "Triggered By", children: <Text code>{run.triggered_by ?? "—"}</Text> },
    { key: "started", label: "Started At", children: formatDateTime(run.started_at) },
    { key: "finished", label: "Finished At", children: formatDateTime(run.finished_at) },
    { key: "elapsed", label: "Elapsed", children: formatDuration(run.elapsed_seconds) },
    { key: "created", label: "Created At", children: formatDateTime(run.created_at) },
  ];
  return <Descriptions bordered column={{ xs: 1, md: 2 }} items={items} />;
}
