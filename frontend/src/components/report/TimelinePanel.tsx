// Execution Timeline Panel：基于已有 Run / Result 时间字段。

import { ClockCircleOutlined } from "@ant-design/icons";
import { Button, Empty, Space, Statistic, Table, Tag, Typography } from "antd";
import type { CountdownProps, StatisticProps } from "antd";
import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { TestResult, TestRun } from "../../api/types";
import { formatDateTime, formatDuration, formatMilliseconds } from "../../utils/format";
import { ResultStatusTag, RunStatusTag } from "../StatusTags";

const { Text } = Typography;

interface TimelinePanelProps {
  projectId: string;
  runId: string;
  run: TestRun | undefined;
  results: TestResult[];
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
}

interface TimelineNode {
  result: TestResult;
  startedAt: string;
}

export function TimelinePanel({
  projectId,
  runId,
  run,
  results,
  loading = false,
  error,
  onRetry,
}: TimelinePanelProps) {
  const orderedResults = useMemo(() => orderByStartedAt(results), [results]);
  const nodes = useMemo<TimelineNode[]>(
    () =>
      orderedResults
        .filter((result) => Boolean(result.started_at))
        .map((result) => ({ result, startedAt: result.started_at as string })),
    [orderedResults],
  );

  if (loading) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="正在加载 Timeline…" />;
  }
  if (error) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={4} align="center">
            <Text strong>Timeline 加载失败</Text>
            {onRetry ? (
              <Button type="primary" onClick={onRetry}>
                重试
              </Button>
            ) : null}
          </Space>
        }
      />
    );
  }
  if (!run) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Run 数据缺失" />;
  }

  return (
    <Space direction="vertical" size={16} className="report-timeline-panel">
      <Space size={[16, 16]} wrap>
        <RunSummaryStat title="Duration" value={formatDuration(run.elapsed_seconds)} />
        <RunSummaryStat
          title="Pass"
          value={run.passed}
          color="success"
        />
        <RunSummaryStat title="Fail" value={run.failed} color="error" />
        <RunSummaryStat title="Error" value={run.error} color="volcano" />
        <RunSummaryStat title="Skip" value={run.skipped} color="default" />
      </Space>

      {orderedResults.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="本次 Run 没有 Result 时间节点"
        />
      ) : (
        <div className="report-timeline-tree">
          <TimelineStart run={run} />
          {nodes.length > 0 ? (
            nodes.map((node, index) => (
              <TimelineRow
                key={node.result.id}
                projectId={projectId}
                runId={runId}
                result={node.result}
                index={index + 1}
                isLast={index === nodes.length - 1}
              />
            ))
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Result 缺少 started_at，使用 Run Header 时间"
            />
          )}
          <TimelineEnd run={run} />
        </div>
      )}

      <Table<TestResult>
        size="small"
        rowKey="id"
        pagination={false}
        dataSource={orderedResults}
        title={() => (
          <Text type="secondary">Case 时间信息（按 started_at 排序）</Text>
        )}
        columns={[
          {
            title: "#",
            dataIndex: "index",
            width: 48,
            render: (_v, _r, index) => index + 1,
          },
          {
            title: "状态",
            dataIndex: "status",
            width: 96,
            render: (status: TestResult["status"]) => <ResultStatusTag status={status} />,
          },
          {
            title: "Case",
            dataIndex: "case_name",
            render: (name: string, record) => (
              <Space direction="vertical" size={0}>
                <Text strong>{name}</Text>
                <Text type="secondary" className="report-timeline-meta">
                  {record.case_method} {record.case_path}
                </Text>
              </Space>
            ),
          },
          {
            title: "Started",
            dataIndex: "started_at",
            width: 180,
            render: (value: string | null) => formatDateTime(value),
          },
          {
            title: "Finished",
            dataIndex: "finished_at",
            width: 180,
            render: (value: string | null) => formatDateTime(value),
          },
          {
            title: "Elapsed",
            dataIndex: "elapsed_ms",
            width: 100,
            render: (value: number | null) => formatMilliseconds(value),
          },
          {
            title: "操作",
            dataIndex: "id",
            width: 110,
            render: (id: string) => (
              <Link to={`/projects/${projectId}/workspace/report/${runId}/result/${id}?tab=request`}>
                <Button type="link" size="small" icon={<ClockCircleOutlined />}>
                  查看
                </Button>
              </Link>
            ),
          },
        ]}
      />
    </Space>
  );
}

function RunSummaryStat({
  title,
  value,
  color,
}: {
  title: string;
  value: StatisticProps["value"] | CountdownProps["value"];
  color?: string;
}) {
  return (
    <Statistic
      title={title}
      value={value}
      valueStyle={{ color: color ?? "inherit" }}
    />
  );
}

function TimelineStart({ run }: { run: TestRun }) {
  return (
    <div className="report-timeline-node report-timeline-node--start">
      <span className="report-timeline-marker" />
      <Space direction="vertical" size={2}>
        <Space>
          <RunStatusTag status={run.status} />
          <Text strong>{run.name}</Text>
        </Space>
        <Text type="secondary">Started {formatDateTime(run.started_at)}</Text>
      </Space>
    </div>
  );
}

function TimelineEnd({ run }: { run: TestRun }) {
  return (
    <div className="report-timeline-node report-timeline-node--end">
      <span className="report-timeline-marker" />
      <Space direction="vertical" size={2}>
        <Text strong>Run Finished</Text>
        <Text type="secondary">
          Finished {formatDateTime(run.finished_at)} · {formatDuration(run.elapsed_seconds)}
        </Text>
      </Space>
    </div>
  );
}

function TimelineRow({
  projectId,
  runId,
  result,
  index,
  isLast,
}: {
  projectId: string;
  runId: string;
  result: TestResult;
  index: number;
  isLast: boolean;
}) {
  return (
    <div className="report-timeline-row">
      <div className={["report-timeline-axis", isLast ? "report-timeline-axis--last" : ""].filter(Boolean).join(" ")}>
        <span className="report-timeline-marker" />
      </div>
      <div className="report-timeline-content">
        <Space className="report-timeline-meta" size={8}>
          <Tag color="default">#{index}</Tag>
          <ResultStatusTag status={result.status} />
          <Text type="secondary">{formatDateTime(result.started_at)}</Text>
          <Text type="secondary">→ {formatDateTime(result.finished_at)}</Text>
          <Text type="secondary">{formatMilliseconds(result.elapsed_ms)}</Text>
        </Space>
        <Space className="report-timeline-case" size={8}>
          <Text strong>{result.case_name}</Text>
          <Text code>
            {result.case_method} {result.case_path}
          </Text>
        </Space>
        <Link to={`/projects/${projectId}/workspace/report/${runId}/result/${result.id}?tab=failures`}>
          <Button type="link" size="small">
            查看证据
          </Button>
        </Link>
      </div>
    </div>
  );
}

function orderByStartedAt(results: TestResult[]): TestResult[] {
  const withTime = results
    .map((result, originalIndex) => ({ result, originalIndex }))
    .sort((a, b) => {
      const aTime = a.result.started_at;
      const bTime = b.result.started_at;
      if (aTime && bTime) {
        return aTime.localeCompare(bTime);
      }
      if (aTime) return -1;
      if (bTime) return 1;
      return a.originalIndex - b.originalIndex;
    });
  return withTime.map((entry) => entry.result);
}
