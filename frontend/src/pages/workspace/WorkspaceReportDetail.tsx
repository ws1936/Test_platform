// Run Detail 页面：展示单次 Run 的概览、Failure Analysis、Timeline 与 Result Evidence Drawer。

import {
  CloudDownloadOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, App, Button, Card, Col, Descriptions, Dropdown, Row, Space, Statistic, Tag, Typography } from "antd";
import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import {
  useReportEnvironments,
  useReportRun,
} from "../../api/report";
import type { Environment, TestResult, TestRun } from "../../api/types";
import { FailureAnalysisPanel } from "../../components/report/FailureAnalysisPanel";
import { ReportEmpty, ReportError } from "../../components/report/ReportCard";
import { ResultEvidenceDrawer } from "../../components/report/ResultEvidenceDrawer";
import { TimelinePanel } from "../../components/report/TimelinePanel";
import PageHeader from "../../components/PageHeader";
import { RunStatusTag, ScopeTag } from "../../components/StatusTags";
import { LoadingBlock } from "../../components/AsyncState";
import { formatDateTime, formatDuration, formatPercent } from "../../utils/format";

const { Text, Paragraph } = Typography;

type RunTab = "detail" | "failures" | "timeline";

const TAB_KEYS: RunTab[] = ["detail", "failures", "timeline"];

function readTabFromUrl(params: URLSearchParams, fallback: RunTab): RunTab {
  const raw = params.get("tab");
  return TAB_KEYS.includes(raw as RunTab) ? (raw as RunTab) : fallback;
}

function pickInitialTab(run: TestRun | undefined): RunTab {
  if (!run) return "detail";
  if (run.failed + run.error > 0) return "failures";
  return "detail";
}

export default function WorkspaceReportDetailPage() {
  const navigate = useNavigate();
  const { projectId = "", runId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = readTabFromUrl(searchParams, "detail");

  const runQuery = useReportRun(runId);
  const envQuery = useReportEnvironments(projectId);
  const resultsQuery = useQuery({
    queryKey: queryKeys.runResults(runId),
    queryFn: () => runsApi.results(runId),
    enabled: Boolean(runId),
  });
  const failuresQuery = useQuery({
    queryKey: queryKeys.runFailures(runId),
    queryFn: () => runsApi.failures(runId),
    enabled: Boolean(runId),
  });
  const [drawerResultId, setDrawerResultId] = useState<string | null>(null);

  // F015：导出报告（JSON / HTML）。一个 useMutation 复用，format 作为变量。
  const { message } = App.useApp();
  const exportMutation = useMutation({
    mutationFn: (format: "json" | "html") => runsApi.exportReport(runId, format),
    onSuccess: (_void, format) => {
      message.success(`已下载 ${format.toUpperCase()} 报告`);
    },
    onError: (error) => message.error(getErrorMessage(error, "导出失败")),
  });

  if (runQuery.isLoading) return <LoadingBlock rows={6} />;
  if (runQuery.isError) {
    return (
      <ReportError
        error={runQuery.error}
        onRetry={() => void runQuery.refetch()}
        title="Run 加载失败"
      />
    );
  }

  const run = runQuery.data;
  if (!run) {
    return (
      <ReportEmpty
        title="Run 不存在"
        description="该 Run 已被删除或不属于当前 Project。"
        action={
          <Button type="primary" onClick={() => navigate("../report")}>
            返回 Report
          </Button>
        }
      />
    );
  }
  if (run.project_id !== projectId) {
    return (
      <ReportError
        error={new Error("该 Run 不属于当前项目")}
        title="上下文错误"
        onBack={() => navigate("../report")}
      />
    );
  }

  const environment = envQuery.data?.items.find((item) => item.id === run.environment_id) ?? null;
  const results = resultsQuery.data?.items ?? [];
  const failureItems = failuresQuery.data?.items ?? [];
  const totalFailed = run.failed + run.error;

  const setTab = (next: RunTab) => {
    const params = new URLSearchParams(searchParams);
    if (next === "detail") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  const initialTab = pickInitialTab(run);
  const currentTab = activeTab ?? initialTab;

  return (
    <>
      <PageHeader
        title={run.name}
        description={`Run ID ${run.id}`}
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "Project 工作区", href: `../overview` },
          { title: "测试报告", href: "../report" },
          { title: run.name },
        ]}
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() =>
                navigate(
                  `../run?scope=${run.scope}&scopeId=${run.scope_id ?? run.project_id}`,
                )
              }
            >
              再次执行
            </Button>
            {/* F015：报告导出。Dropdown 选 JSON / HTML，走 runsApi.exportReport */}
            <Dropdown
              menu={{
                items: [
                  {
                    key: "json",
                    label: "导出 JSON（完整快照）",
                    disabled: exportMutation.isPending,
                  },
                  {
                    key: "html",
                    label: "导出 HTML（自包含报告）",
                    disabled: exportMutation.isPending,
                  },
                ],
                onClick: ({ key }) => {
                  if (key === "json" || key === "html") {
                    exportMutation.mutate(key);
                  }
                },
              }}
            >
              <Button
                icon={<CloudDownloadOutlined />}
                loading={exportMutation.isPending}
              >
                导出报告
              </Button>
            </Dropdown>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                void runQuery.refetch();
                void resultsQuery.refetch();
                void failuresQuery.refetch();
                void envQuery.refetch();
              }}
            >
              刷新
            </Button>
          </Space>
        }
      />

      {resultsQuery.isError ? (
        <Alert
          className="inline-warning"
          type="warning"
          showIcon
          message="Result 数据加载失败"
          description="Run Header 已加载，但 Result 列表需要重试。"
          action={
            <Button onClick={() => void resultsQuery.refetch()}>重试</Button>
          }
        />
      ) : null}

      <RunHeaderCard run={run} environment={environment} totalFailed={totalFailed} />

      <Card className="surface-card">
        <RunTabs
          currentTab={currentTab}
          failureCount={failureItems.length}
          resultCount={results.length}
          failedResultCount={results.filter((r) => r.status === "failed" || r.status === "error").length}
          onChange={setTab}
        />

        {currentTab === "detail" ? (
          <DetailTab
            run={run}
            results={results}
            environment={environment}
            onOpenResult={(resultId) => setDrawerResultId(resultId)}
          />
        ) : null}

        {currentTab === "failures" ? (
          <div className="report-run-tab-body">
            <FailureAnalysisPanel
              projectId={projectId}
              runId={runId}
              environment={environment}
              results={results}
              failureItems={failureItems}
              loading={resultsQuery.isLoading || failuresQuery.isLoading}
              error={resultsQuery.error ?? failuresQuery.error}
              onRetry={() => {
                void resultsQuery.refetch();
                void failuresQuery.refetch();
              }}
            />
          </div>
        ) : null}

        {currentTab === "timeline" ? (
          <div className="report-run-tab-body">
            <TimelinePanel
              projectId={projectId}
              runId={runId}
              run={run}
              results={results}
              loading={resultsQuery.isLoading}
              error={resultsQuery.error}
              onRetry={() => void resultsQuery.refetch()}
            />
          </div>
        ) : null}
      </Card>

      <ResultEvidenceDrawer
        open={Boolean(drawerResultId)}
        projectId={projectId}
        runId={runId}
        resultId={drawerResultId ?? ""}
        onClose={() => setDrawerResultId(null)}
      />
    </>
  );
}

interface RunHeaderCardProps {
  run: TestRun;
  environment: Environment | null;
  totalFailed: number;
}

function RunHeaderCard({ run, environment, totalFailed }: RunHeaderCardProps) {
  return (
    <Card className="surface-card" style={{ marginBottom: 16 }}>
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} md={9}>
          <Space direction="vertical" size={4}>
            <Space>
              <RunStatusTag status={run.status} />
              <Text strong>{run.name}</Text>
            </Space>
            <Text type="secondary">
              环境：
              {environment
                ? `${environment.name} · ${environment.base_url}`
                : run.environment_id}
            </Text>
            <Text type="secondary">触发人：{run.triggered_by ?? "—"}</Text>
            <Text type="secondary">
              {formatDateTime(run.started_at)} → {formatDateTime(run.finished_at)}
            </Text>
          </Space>
        </Col>
        <Col xs={12} md={5}>
          <Statistic
            title="Pass Rate"
            value={formatPercent(run.pass_rate)}
            valueStyle={{
              color: run.pass_rate === null
                ? "inherit"
                : run.pass_rate >= 0.8
                  ? "#52c41a"
                  : run.pass_rate >= 0.5
                    ? "#faad14"
                    : "#ff4d4f",
            }}
          />
        </Col>
        <Col xs={12} md={5}>
          <Statistic title="Duration" value={formatDuration(run.elapsed_seconds)} />
        </Col>
        <Col xs={12} md={5}>
          <Statistic
            title="Failed / Error"
            value={totalFailed}
            valueStyle={{ color: totalFailed > 0 ? "#ff4d4f" : "#52c41a" }}
          />
        </Col>
      </Row>
    </Card>
  );
}

interface RunTabsProps {
  currentTab: RunTab;
  failureCount: number;
  resultCount: number;
  failedResultCount: number;
  onChange: (next: RunTab) => void;
}

function RunTabs({
  currentTab,
  failureCount,
  resultCount,
  failedResultCount,
  onChange,
}: RunTabsProps) {
  const items: { key: RunTab; label: string }[] = [
    { key: "detail", label: `概览 (${resultCount})` },
    { key: "failures", label: `Failure (${failedResultCount})` },
    { key: "timeline", label: "Timeline" },
  ];
  return (
    <div className="report-run-tabs">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          className={[
            "report-run-tab",
            currentTab === item.key ? "report-run-tab--active" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={() => onChange(item.key)}
        >
          {item.label}
          {item.key === "failures" && failureCount > 0 ? (
            <Tag color="error" className="report-run-tab-tag">
              {failureCount}
            </Tag>
          ) : null}
        </button>
      ))}
    </div>
  );
}

interface DetailTabProps {
  run: TestRun;
  results: TestResult[];
  environment: Environment | null;
  onOpenResult: (resultId: string) => void;
}

function DetailTab({ run, results, environment, onOpenResult }: DetailTabProps) {
  const passed = results.filter((r) => r.status === "passed").length;
  const failed = results.filter((r) => r.status === "failed").length;
  const errored = results.filter((r) => r.status === "error").length;
  const skipped = results.filter((r) => r.status === "skipped").length;

  return (
    <Space direction="vertical" size={16} className="report-run-tab-body">
      <div className="report-run-tab-cards">
        <ResultStat title="Total" value={run.total} color="default" />
        <ResultStat title="Passed" value={passed} color="success" />
        <ResultStat title="Failed" value={failed} color="error" />
        <ResultStat title="Error" value={errored} color="volcano" />
        <ResultStat title="Skip" value={skipped} color="default" />
      </div>

      <Descriptions
        column={{ xs: 1, md: 2 }}
        bordered
        size="small"
        items={[
          { key: "id", label: "Run ID", children: <Text code>{run.id}</Text> },
          { key: "scope", label: "Scope", children: <ScopeTag scope={run.scope} /> },
          {
            key: "environment",
            label: "Environment",
            children: environment ? <Text>{environment.name}</Text> : <Text code>{run.environment_id}</Text>,
          },
          { key: "trigger", label: "Triggered By", children: <Text code>{run.triggered_by ?? "—"}</Text> },
          { key: "started", label: "Started At", children: formatDateTime(run.started_at) },
          { key: "finished", label: "Finished At", children: formatDateTime(run.finished_at) },
          { key: "elapsed", label: "Elapsed", children: formatDuration(run.elapsed_seconds) },
          { key: "created", label: "Created At", children: formatDateTime(run.created_at) },
        ]}
      />

      {results.length === 0 ? (
        <ReportEmpty title="本次 Run 没有 Result 数据" description="Result API 未返回任何条目。" />
      ) : (
        <div className="report-run-tab-list">
          {results.map((result) => (
            <button
              key={result.id}
              type="button"
              className="report-run-tab-row"
              onClick={() => onOpenResult(result.id)}
            >
              <Space>
                <Tag color={statusColor(result.status)}>{result.status}</Tag>
                <Text strong>{result.case_name}</Text>
                <Text type="secondary">
                  {result.case_method} {result.case_path}
                </Text>
                <Text type="secondary">{(result.elapsed_ms ?? 0)} ms</Text>
              </Space>
              {result.error_message ? (
                <Paragraph type="danger" className="report-run-tab-row-error">
                  {result.error_message}
                </Paragraph>
              ) : null}
            </button>
          ))}
        </div>
      )}
    </Space>
  );
}

function statusColor(status: TestResult["status"]): string {
  if (status === "passed") return "success";
  if (status === "failed") return "error";
  if (status === "error") return "volcano";
  return "default";
}

interface ResultStatProps {
  title: string;
  value: number;
  color: string;
}

function ResultStat({ title, value, color }: ResultStatProps) {
  return (
    <div className="report-run-tab-stat">
      <Text type="secondary">{title}</Text>
      <div className="report-run-tab-stat-value" style={{ color }}>
        {value}
      </div>
    </div>
  );
}



