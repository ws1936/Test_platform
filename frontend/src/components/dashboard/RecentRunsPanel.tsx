import { ArrowRightOutlined } from "@ant-design/icons";
import { Button, Card, Space, Table, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import type { TestRun } from "../../api/types";
import { formatDateTime, formatPercent } from "../../utils/format";
import { EmptyState, ErrorState } from "../AsyncState";
import { RunStatusTag, ScopeTag } from "../StatusTags";

interface RecentRunsPanelProps {
  projectId: string;
  runs: TestRun[];
  loading: boolean;
  error?: unknown;
  onRetry: () => void;
}

export default function RecentRunsPanel({
  projectId,
  runs,
  loading,
  error,
  onRetry,
}: RecentRunsPanelProps) {
  const navigate = useNavigate();
  const reportsPath = projectId ? `/projects/${projectId}/reports` : "/dashboard";
  // P1-4: 在 projectId 为空时，禁用行点击与鼠标指针，避免拼出 `/projects//reports/<id>`。
  const rowsClickable = Boolean(projectId);

  return (
    <Card
      className="surface-card dashboard-recent-runs"
      title="最近执行"
      extra={
        projectId ? (
          <Button type="link" onClick={() => navigate(reportsPath)}>
            查看全部 <ArrowRightOutlined />
          </Button>
        ) : null
      }
    >
      {error ? <ErrorState compact error={error} onRetry={onRetry} /> : null}
      {!error ? (
        <Table<TestRun>
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={runs}
          pagination={false}
          locale={{
            emptyText: (
              <EmptyState
                title={projectId ? "暂无执行记录" : "请选择一个 Project"}
                description={
                  projectId ? "发起第一次执行后，最近 Run 会显示在这里。" : undefined
                }
                action={
                  projectId ? (
                    <Button type="primary" onClick={() => navigate(`/projects/${projectId}/runs`)}>
                      发起执行
                    </Button>
                  ) : undefined
                }
              />
            ),
          }}
          onRow={(run) =>
            rowsClickable
              ? {
                  onClick: () => navigate(`/projects/${projectId}/workspace/report/${run.id}`),
                  style: { cursor: "pointer" },
                }
              : { style: { cursor: "default" } }
          }
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 96,
              render: (status) => <RunStatusTag status={status} />,
            },
            {
              title: "执行名称",
              dataIndex: "name",
              ellipsis: true,
            },
            {
              title: "范围",
              dataIndex: "scope",
              width: 100,
              responsive: ["md"],
              render: (scope) => <ScopeTag scope={scope} />,
            },
            {
              title: "结果",
              width: 120,
              responsive: ["lg"],
              render: (_, run) => (
                <Space size={4}>
                  <Typography.Text type="success">{run.passed}</Typography.Text>
                  <Typography.Text type="secondary">/ {run.total}</Typography.Text>
                  {run.failed + run.error > 0 ? (
                    <Typography.Text type="danger">-{run.failed + run.error}</Typography.Text>
                  ) : null}
                </Space>
              ),
            },
            {
              title: "通过率",
              dataIndex: "pass_rate",
              width: 90,
              responsive: ["md"],
              render: formatPercent,
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 168,
              responsive: ["xl"],
              render: formatDateTime,
            },
          ]}
        />
      ) : null}
    </Card>
  );
}
