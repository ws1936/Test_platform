// Report Center 首屏：Summary + History（视图切换）。

import {
  AppstoreOutlined,
  CalendarOutlined,
  DashboardOutlined,
  ReloadOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Segmented, Space, Table, Tag, Typography } from "antd";
import type { TablePaginationConfig } from "antd";
import { useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import {
  useReportEnvironments,
  useReportHistory,
  useReportSummary,
} from "../../api/report";
import type {
  Environment,
  FailureItem,
  RunStatus,
  RunScope,
  TestResult,
  TestRun,
} from "../../api/types";
import { FailureAnalysisPanel } from "../../components/report/FailureAnalysisPanel";
import {
  ReportEmpty,
  ReportError,
  ReportLinkAction,
  ReportSkeleton,
} from "../../components/report/ReportCard";
import PageHeader from "../../components/PageHeader";
import { ScopeTag, RunStatusTag } from "../../components/StatusTags";
import { formatDateTime, formatDuration, formatPercent } from "../../utils/format";

const { Text } = Typography;

type ReportView = "summary" | "history";

const SUMMARY_HISTORY_WINDOW = 50;

const VIEW_OPTIONS = [
  { label: "Summary", value: "summary" as ReportView, icon: <DashboardOutlined /> },
  { label: "History", value: "history" as ReportView, icon: <UnorderedListOutlined /> },
];

export default function WorkspaceReportList() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const viewFromUrl = searchParams.get("view");
  const activeView: ReportView = viewFromUrl === "history" ? "history" : "summary";

  const setView = (next: ReportView) => {
    const nextParams = new URLSearchParams(searchParams);
    if (next === "summary") nextParams.delete("view");
    else nextParams.set("view", next);
    setSearchParams(nextParams, { replace: true });
  };

  const summaryQuery = useReportSummary({ projectId });
  const envQuery = useReportEnvironments(projectId);
  const envName = (envId: string) =>
    envQuery.data?.items.find((item) => item.id === envId)?.name ?? envId;

  return (
    <>
      <PageHeader
        title="测试报告"
        description="查询历史、判断质量、定位失败"
        breadcrumbs={[
          { title: "Project 工作区", href: "../overview" },
          { title: "测试报告" },
        ]}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                void summaryQuery.refetch();
                void envQuery.refetch();
              }}
            >
              刷新
            </Button>
          </Space>
        }
      />

      <div className="report-toolbar">
        <Segmented<ReportView>
          options={VIEW_OPTIONS}
          value={activeView}
          onChange={(value) => setView(value as ReportView)}
        />
        <Text type="secondary" className="report-toolbar-hint">
          首屏以 Summary 展示最近一次执行；History 列出最近 {SUMMARY_HISTORY_WINDOW} 条执行。
        </Text>
      </div>

      {activeView === "summary" ? (
        <ReportSummaryView
          projectId={projectId}
          summaryQuery={summaryQuery}
          envQuery={envQuery}
          envName={envName}
          onOpenRun={(runId) => navigate(`../report/${runId}`)}
          onOpenFailureList={(runId) => navigate(`../report/${runId}?tab=failures`)}
          onOpenTimeline={(runId) => navigate(`../report/${runId}?tab=timeline`)}
          onOpenRunCenter={() => navigate(`../run`)}
          onOpenHistory={() => setView("history")}
        />
      ) : (
        <ReportHistoryView
          projectId={projectId}
          envName={envName}
          navigateToRun={(runId) => navigate(`../report/${runId}`)}
        />
      )}
    </>
  );
}

type SummaryQuery = ReturnType<typeof useReportSummary>;
type EnvironmentsQuery = ReturnType<typeof useReportEnvironments>;
type RecentRun = NonNullable<NonNullable<SummaryQuery["data"]>["recent_runs"]>[number];

interface ReportSummaryViewProps {
  projectId: string;
  summaryQuery: SummaryQuery;
  envQuery: EnvironmentsQuery;
  envName: (envId: string) => string;
  onOpenRun: (runId: string) => void;
  onOpenFailureList: (runId: string) => void;
  onOpenTimeline: (runId: string) => void;
  onOpenRunCenter: () => void;
  onOpenHistory: () => void;
}

function ReportSummaryView({
  projectId,
  summaryQuery,
  envQuery,
  envName,
  onOpenRun,
  onOpenFailureList,
  onOpenTimeline,
  onOpenRunCenter,
  onOpenHistory,
}: ReportSummaryViewProps) {
  if (summaryQuery.isLoading) return <ReportSkeleton count={6} />;
  if (summaryQuery.isError) {
    return (
      <ReportError
        error={summaryQuery.error}
        onRetry={() => void summaryQuery.refetch()}
        title="Summary 加载失败"
      />
    );
  }
  const summary = summaryQuery.data;
  if (!summary) {
    return (
      <ReportEmpty
        title="Summary 数据为空"
        description="Project 聚合接口未返回数据。"
      />
    );
  }
  const recent = summary.recent_runs ?? [];
  const latest = recent[0];

  return (
    <div className="report-summary-view">
      <section className="report-summary-section">
        <header className="report-summary-header">
          <Space direction="vertical" size={2}>
            <Text type="secondary">Project 累计</Text>
            <Text strong className="report-summary-eyebrow">
              {`Project Overall Pass Rate：${formatPercent(summary.overall_pass_rate)}`}
            </Text>
          </Space>
        </header>
        <SummaryProjectCards summary={summary} />
      </section>

      {latest ? (
        <LatestRunCard
          projectId={projectId}
          latest={latest}
          envName={envName(latest.environment_id)}
          environment={
            envQuery.data?.items.find((item) => item.id === latest.environment_id) ?? null
          }
          onOpenRun={onOpenRun}
          onOpenFailureList={onOpenFailureList}
          onOpenTimeline={onOpenTimeline}
        />
      ) : (
        <ReportEmpty
          title="暂无最近一次 Run"
          description="Project 还没有可查看的执行报告。"
          action={
            <Space>
              <Button type="primary" icon={<AppstoreOutlined />} onClick={onOpenRunCenter}>
                前往执行中心
              </Button>
            </Space>
          }
        />
      )}

      <RecentRunsSection
        recent={recent}
        envName={envName}
        onOpenRun={onOpenRun}
        onOpenHistory={onOpenHistory}
      />
    </div>
  );
}

function SummaryProjectCards({ summary }: { summary: NonNullable<SummaryQuery["data"]> }) {
  return (
    <div className="report-summary-cards">
      <SummaryCard title="Total Runs" value={summary.total_runs} hint="累计 Run 数" />
      <SummaryCard title="Results" value={summary.total_cases} hint="累计 Result / Case 数" />
      <SummaryCard
        title="Pass Rate"
        value={formatPercent(summary.overall_pass_rate)}
        hint="Project 总体通过率"
      />
      <SummaryCard title="Last Run" value={formatDateTime(summary.last_run_at)} hint="最近一次执行时间" />
    </div>
  );
}

interface LatestRunCardProps {
  projectId: string;
  latest: RecentRun;
  envName: string;
  environment: Environment | null;
  onOpenRun: (runId: string) => void;
  onOpenFailureList: (runId: string) => void;
  onOpenTimeline: (runId: string) => void;
}

function LatestRunCard({
  projectId,
  latest,
  envName,
  environment,
  onOpenRun,
  onOpenFailureList,
  onOpenTimeline,
}: LatestRunCardProps) {
  return (
    <div className="report-summary-section">
      <header className="report-summary-header">
        <Space>
          <Text type="secondary">Latest Run</Text>
          <RunStatusTag status={latest.status} />
          <Text strong>{latest.name}</Text>
          <Tag color="geekblue">{latest.run_id.slice(0, 8)}</Tag>
        </Space>
        <Space>
          <Button type="primary" onClick={() => onOpenRun(latest.run_id)}>
            查看 Run Detail
          </Button>
        </Space>
      </header>

      <div className="report-summary-cards">
        <SummaryCard
          title="Pass Rate"
          value={formatPercent(latest.pass_rate)}
          hint="latest Run"
          action={
            <Button type="link" onClick={() => onOpenRun(latest.run_id)}>
              Run Detail →
            </Button>
          }
        />
        <SummaryCard title="Passed" value={latest.passed} hint="latest Run" />
        <SummaryCard
          title="Failed"
          value={latest.failed}
          hint="latest Run"
          action={
            latest.failed + latest.error > 0 ? (
              <Button type="link" danger onClick={() => onOpenFailureList(latest.run_id)}>
                查看 Failure List →
              </Button>
            ) : null
          }
        />
        <SummaryCard
          title="Duration"
          value={formatDuration(latest.elapsed_seconds)}
          hint="latest Run"
          action={
            <Button type="link" onClick={() => onOpenTimeline(latest.run_id)}>
              Timeline →
            </Button>
          }
        />
        <SummaryCard title="Environment" value={envName} hint="latest Run" />
        <SummaryCard title="Scope" value={<ScopeTag scope={latest.scope} />} hint="latest Run" />
        <SummaryCard
          title="Run Time"
          value={
            <Space direction="vertical" size={0}>
              <Text>{formatDateTime(latest.started_at)}</Text>
              <Text type="secondary">→ {formatDateTime(latest.finished_at)}</Text>
            </Space>
          }
          hint="latest Run"
        />
        <SummaryCard title="Error" value={latest.error} hint="Execution Error 数量" />
      </div>

      <Text type="secondary" className="report-summary-meta">
        Project {projectId.slice(0, 8)} · 每次 Summary 仅以 latest Run 作为结论数据源。
      </Text>

      {environment ? (
        <Text type="secondary" className="report-summary-meta">
          当前 Environment：<Tag color="blue">{environment.name}</Tag>
        </Text>
      ) : null}
    </div>
  );
}

interface RecentRunsSectionProps {
  recent: NonNullable<SummaryQuery["data"]>["recent_runs"];
  envName: (envId: string) => string;
  onOpenRun: (runId: string) => void;
  onOpenHistory: () => void;
}

function RecentRunsSection({ recent, envName, onOpenRun, onOpenHistory }: RecentRunsSectionProps) {
  return (
    <div className="report-summary-section">
      <header className="report-summary-header">
        <Space>
          <CalendarOutlined />
          <Text type="secondary">Recent Runs（最近 5 条）</Text>
        </Space>
        <Button onClick={onOpenHistory}>查看全部 History →</Button>
      </header>
      {recent.length === 0 ? (
        <ReportEmpty title="暂无最近 Run" description="Project 还没有执行记录。" />
      ) : (
        <div className="report-recent-runs">
          {recent.slice(0, 5).map((run) => (
            <div
              key={run.run_id}
              className="report-recent-run"
              onClick={() => onOpenRun(run.run_id)}
            >
              <Space direction="vertical" size={4}>
                <Space>
                  <RunStatusTag status={run.status} />
                  <Text strong>{run.name}</Text>
                </Space>
                <Space size={8} wrap>
                  <Tag color="geekblue">{run.scope}</Tag>
                  <Text type="secondary">{envName(run.environment_id)}</Text>
                </Space>
                <Space size={8} wrap>
                  <Tag color="success">Pass {run.passed}</Tag>
                  <Tag color="error">Fail {run.failed}</Tag>
                  <Tag color="volcano">Error {run.error}</Tag>
                  <Tag color="default">Skip {run.skipped}</Tag>
                  <Tag color="blue">{formatDuration(run.elapsed_seconds)}</Tag>
                </Space>
                <Text type="secondary">{formatDateTime(run.started_at)}</Text>
              </Space>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface ReportHistoryViewProps {
  projectId: string;
  envName: (envId: string) => string;
  navigateToRun: (runId: string) => void;
}

interface HistoryFilters {
  status: RunStatus | undefined;
  page: number;
  pageSize: number;
  search: string;
  environment: string | undefined;
  scope: RunScope | undefined;
  duration: DurationKey | undefined;
}

type DurationKey = "all" | "lt1s" | "1to10s" | "10to60s" | "gt60s";

const DURATION_OPTIONS: { label: string; value: DurationKey }[] = [
  { label: "全部", value: "all" },
  { label: "< 1s", value: "lt1s" },
  { label: "1s – 10s", value: "1to10s" },
  { label: "10s – 60s", value: "10to60s" },
  { label: "> 60s", value: "gt60s" },
];

const STATUS_OPTIONS: { label: string; value: RunStatus | "all" }[] = [
  { label: "全部", value: "all" },
  { label: "pending", value: "pending" },
  { label: "running", value: "running" },
  { label: "finished", value: "finished" },
  { label: "failed", value: "failed" },
  { label: "canceled", value: "canceled" },
];

const SCOPE_OPTIONS: { label: string; value: RunScope | "all" }[] = [
  { label: "全部", value: "all" },
  { label: "collection", value: "collection" },
  { label: "case", value: "case" },
  { label: "project", value: "project" },
];

function ReportHistoryView({ projectId, envName, navigateToRun }: ReportHistoryViewProps) {
  const [filters, setFilters] = useState<HistoryFilters>({
    status: undefined,
    page: 1,
    pageSize: 20,
    search: "",
    environment: undefined,
    scope: undefined,
    duration: "all",
  });
  const [preview, setPreview] = useState<{ runId: string } | null>(null);

  const historyQuery = useReportHistory({
    projectId,
    status: filters.status,
    limit: SUMMARY_HISTORY_WINDOW,
    offset: 0,
  });
  const envQuery = useReportEnvironments(projectId);
  const resultsQuery = useQuery({
    queryKey: queryKeys.runResults(preview?.runId ?? ""),
    queryFn: () => runsApi.results(preview?.runId ?? ""),
    enabled: Boolean(preview?.runId),
  });
  const failuresQuery = useQuery({
    queryKey: queryKeys.runFailures(preview?.runId ?? ""),
    queryFn: () => runsApi.failures(preview?.runId ?? ""),
    enabled: Boolean(preview?.runId),
  });

  const filteredRuns = useMemo(
    () => filterRunsLocally(historyQuery.data?.items ?? [], filters, envName),
    [historyQuery.data, filters, envName],
  );

  const totalServer = historyQuery.data?.total ?? 0;
  const loadedCount = historyQuery.data?.items.length ?? 0;

  const onTableChange = (pagination: TablePaginationConfig) => {
    setFilters((prev) => ({
      ...prev,
      page: pagination.current ?? 1,
      pageSize: pagination.pageSize ?? prev.pageSize,
    }));
  };

  return (
    <div className="report-history-view">
      <HistoryToolbar
        filters={filters}
        onChange={(next) => setFilters({ ...filters, ...next, page: 1 })}
        environments={envQuery.data?.items ?? []}
        searchLoading={historyQuery.isFetching}
        onClear={() =>
          setFilters({
            status: undefined,
            page: 1,
            pageSize: 20,
            search: "",
            environment: undefined,
            scope: undefined,
            duration: "all",
          })
        }
      />
      <HistoryMeta
        totalServer={totalServer}
        loadedCount={loadedCount}
        filteredCount={filteredRuns.length}
        hasStatus={Boolean(filters.status)}
      />
      {historyQuery.isLoading ? (
        <ReportSkeleton count={4} />
      ) : historyQuery.isError ? (
        <ReportError
          error={historyQuery.error}
          onRetry={() => void historyQuery.refetch()}
          title="Run History 加载失败"
        />
      ) : filteredRuns.length === 0 ? (
        <ReportEmpty
          title="当前筛选没有匹配的 Run"
          description="可以调整 Status / Environment / Suite / Duration / Search，或前往执行中心发起新 Run。"
        />
      ) : (
        <Table<TestRun>
          size="small"
          rowKey="id"
          dataSource={filteredRuns}
          scroll={{ x: "max-content" }}
          pagination={{
            current: filters.page,
            pageSize: filters.pageSize,
            total: filteredRuns.length,
            showSizeChanger: true,
          }}
          onChange={onTableChange}
          onRow={(row) => ({ onClick: () => setPreview({ runId: row.id }) })}
          columns={[
            {
              title: "#",
              width: 48,
              render: (_v, _r, index) => (filters.page - 1) * filters.pageSize + index + 1,
            },
            {
              title: "Run",
              dataIndex: "name",
              render: (name: string, record) => (
                <Space direction="vertical" size={0}>
                  <Text strong>{name}</Text>
                  <Text type="secondary">{record.id.slice(0, 8)}…</Text>
                </Space>
              ),
            },
            {
              title: "Status",
              dataIndex: "status",
              width: 96,
              render: (status: RunStatus) => <RunStatusTag status={status} />,
            },
            {
              title: "Scope",
              dataIndex: "scope",
              width: 110,
              render: (scope: RunScope) => <ScopeTag scope={scope} />,
            },
            {
              title: "Environment",
              dataIndex: "environment_id",
              width: 160,
              render: (id: string) => <Text>{envName(id)}</Text>,
            },
            {
              title: "Pass / Total",
              width: 120,
              render: (_v, record) => (
                <Text>
                  {record.passed} / {record.total}
                </Text>
              ),
            },
            {
              title: "Pass Rate",
              dataIndex: "pass_rate",
              width: 110,
              render: (rate: number | null) => formatPercent(rate),
            },
            {
              title: "Duration",
              dataIndex: "elapsed_seconds",
              width: 110,
              render: (value: number | null) => formatDuration(value),
            },
            {
              title: "Run Time",
              dataIndex: "started_at",
              width: 180,
              render: (value: string | null, record) => (
                <Space direction="vertical" size={0}>
                  <Text>{formatDateTime(value)}</Text>
                  <Text type="secondary">→ {formatDateTime(record.finished_at)}</Text>
                </Space>
              ),
            },
            {
              title: "操作",
              dataIndex: "id",
              width: 120,
              render: (id: string) => (
                <ReportLinkAction to={`../report/${id}`} label="打开 →" />
              ),
            },
          ]}
        />
      )}

      {preview?.runId ? (
        <HistoryPreviewPanel
          projectId={projectId}
          runId={preview.runId}
          results={resultsQuery.data?.items ?? []}
          failureItems={failuresQuery.data?.items ?? []}
          loading={resultsQuery.isLoading || failuresQuery.isLoading}
          error={resultsQuery.error ?? failuresQuery.error}
          onRetry={() => {
            void resultsQuery.refetch();
            void failuresQuery.refetch();
          }}
          onClose={() => setPreview(null)}
          onOpenRun={navigateToRun}
        />
      ) : null}
    </div>
  );
}

interface HistoryToolbarProps {
  filters: HistoryFilters;
  onChange: (next: Partial<HistoryFilters>) => void;
  environments: Environment[];
  searchLoading: boolean;
  onClear: () => void;
}

function HistoryToolbar({
  filters,
  onChange,
  environments,
  searchLoading,
  onClear,
}: HistoryToolbarProps) {
  return (
    <div className="report-history-toolbar">
      <Space wrap size={[12, 8]} className="report-history-toolbar-row">
        <HistorySelect
          label="Status"
          value={(filters.status ?? "all") as RunStatus | "all"}
          options={STATUS_OPTIONS}
          onChange={(value) =>
            onChange({ status: value === "all" ? undefined : (value as RunStatus) })
          }
        />
        <HistorySelect
          label="Environment"
          value={filters.environment ?? "all"}
          options={[
            { label: "全部", value: "all" },
            ...environments.map((env) => ({ label: env.name, value: env.id })),
          ]}
          onChange={(value) =>
            onChange({ environment: value === "all" ? undefined : String(value) })
          }
        />
        <HistorySelect
          label="Suite / Scope"
          value={(filters.scope ?? "all") as RunScope | "all"}
          options={SCOPE_OPTIONS}
          onChange={(value) =>
            onChange({ scope: value === "all" ? undefined : (value as RunScope) })
          }
        />
        <HistorySelect
          label="Duration"
          value={filters.duration ?? "all"}
          options={DURATION_OPTIONS}
          onChange={(value) => onChange({ duration: value as DurationKey })}
        />
        <input
          type="search"
          className="report-history-search"
          placeholder="搜索 Run name / Run ID"
          value={filters.search}
          onChange={(event) => onChange({ search: event.target.value })}
          aria-label="搜索 Run"
        />
        <Button onClick={onClear} icon={<ReloadOutlined />}>
          清除筛选
        </Button>
        {searchLoading ? <Text type="secondary">同步中…</Text> : null}
      </Space>
    </div>
  );
}

interface HistorySelectProps<T extends string> {
  label: string;
  value: T;
  options: { label: string; value: T }[];
  onChange: (value: T) => void;
}

function HistorySelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: HistorySelectProps<T>) {
  return (
    <label className="report-history-select">
      <span className="report-history-select-label">{label}</span>
      <select
        className="report-history-select-input"
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

interface HistoryMetaProps {
  totalServer: number;
  loadedCount: number;
  filteredCount: number;
  hasStatus: boolean;
}

function HistoryMeta({
  totalServer,
  loadedCount,
  filteredCount,
  hasStatus,
}: HistoryMetaProps) {
  return (
    <Text type="secondary" className="report-history-meta">
      服务端共 {totalServer} 条 · 当前加载 {loadedCount} 条 · 本地筛选命中 {filteredCount} 条
      {hasStatus ? " · Status 已使用服务端过滤" : ""}
    </Text>
  );
}

function filterRunsLocally(
  runs: TestRun[],
  filters: HistoryFilters,
  envName: (envId: string) => string,
): TestRun[] {
  const keyword = filters.search.trim().toLowerCase();
  return runs.filter((run) => {
    if (filters.environment && run.environment_id !== filters.environment) return false;
    if (filters.scope && run.scope !== filters.scope) return false;
    if (filters.duration && !matchDuration(run.elapsed_seconds, filters.duration)) return false;
    if (keyword) {
      const haystack = `${run.name} ${run.id} ${envName(run.environment_id)}`.toLowerCase();
      if (!haystack.includes(keyword)) return false;
    }
    return true;
  });
}

function matchDuration(seconds: number | null, key: DurationKey): boolean {
  if (key === "all") return true;
  if (seconds === null) return false;
  if (key === "lt1s") return seconds < 1;
  if (key === "1to10s") return seconds >= 1 && seconds < 10;
  if (key === "10to60s") return seconds >= 10 && seconds < 60;
  if (key === "gt60s") return seconds >= 60;
  return true;
}

interface SummaryCardProps {
  title: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  action?: React.ReactNode;
}

function SummaryCard({ title, value, hint, action }: SummaryCardProps) {
  return (
    <div className="report-summary-card">
      <Text type="secondary" className="report-summary-card-title">
        {title}
      </Text>
      <div className="report-summary-card-value">{value}</div>
      {hint ? (
        <Text type="secondary" className="report-summary-card-hint">
          {hint}
        </Text>
      ) : null}
      {action ? <div className="report-summary-card-action">{action}</div> : null}
    </div>
  );
}

interface HistoryPreviewPanelProps {
  projectId: string;
  runId: string;
  results: TestResult[];
  failureItems: FailureItem[];
  loading: boolean;
  error?: unknown;
  onRetry?: () => void;
  onClose: () => void;
  onOpenRun: (runId: string) => void;
}

function HistoryPreviewPanel({
  projectId,
  runId,
  results,
  failureItems,
  loading,
  error,
  onRetry,
  onClose,
  onOpenRun,
}: HistoryPreviewPanelProps) {
  return (
    <div className="report-history-preview">
      <header className="report-history-preview-header">
        <Space>
          <Text strong>Run {runId.slice(0, 8)}</Text>
          <Text type="secondary">
            Failure {failureItems.length} · Results {results.length}
          </Text>
        </Space>
        <Space>
          <Button onClick={() => onOpenRun(runId)}>打开 Run Detail →</Button>
          <Button onClick={onClose}>关闭</Button>
        </Space>
      </header>
      <FailureAnalysisPanel
        projectId={projectId}
        runId={runId}
        environment={null}
        results={results}
        failureItems={failureItems}
        loading={loading}
        error={error}
        onRetry={onRetry}
      />
    </div>
  );
}
