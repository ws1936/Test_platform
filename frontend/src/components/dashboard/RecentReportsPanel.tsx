import { ArrowRightOutlined, FileSearchOutlined } from "@ant-design/icons";
import { Button, Card, List, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import type { TestRun } from "../../api/types";
import { formatDateTime, formatDuration, formatPercent } from "../../utils/format";
import { EmptyState, ErrorState } from "../AsyncState";

interface RecentReportsPanelProps {
  projectId: string;
  reports: TestRun[];
  loading: boolean;
  error?: unknown;
  onRetry: () => void;
}

export default function RecentReportsPanel({
  projectId,
  reports,
  loading,
  error,
  onRetry,
}: RecentReportsPanelProps) {
  const navigate = useNavigate();

  return (
    <Card
      className="surface-card dashboard-recent-reports"
      title="最近 Report"
      loading={loading}
      extra={
        projectId ? (
          <Button type="link" onClick={() => navigate(`/projects/${projectId}/reports`)}>
            全部 <ArrowRightOutlined />
          </Button>
        ) : null
      }
    >
      {error ? <ErrorState compact error={error} onRetry={onRetry} /> : null}
      {!error && !loading ? (
        <List<TestRun>
          dataSource={reports}
          locale={{
            emptyText: (
              <EmptyState
                title={projectId ? "暂无可查看 Report" : "请选择一个 Project"}
                description={projectId ? "完成执行后，报告入口会显示在这里。" : undefined}
              />
            ),
          }}
          renderItem={(report) => (
            <List.Item
              className="dashboard-clickable-list-item"
              onClick={() => navigate(`/projects/${projectId}/workspace/report/${report.id}`)}
            >
              <List.Item.Meta
                avatar={<FileSearchOutlined className="dashboard-list-icon" />}
                title={<Typography.Text strong ellipsis>{report.name}</Typography.Text>}
                description={
                  <Space direction="vertical" size={1}>
                    <Typography.Text type="secondary">
                      通过率 {formatPercent(report.pass_rate)} · 失败 {report.failed} · 错误 {report.error}
                    </Typography.Text>
                    <Typography.Text type="secondary">
                      {formatDuration(report.elapsed_seconds)} · {formatDateTime(report.finished_at)}
                    </Typography.Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      ) : null}
    </Card>
  );
}
