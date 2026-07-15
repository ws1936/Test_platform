import { ArrowRightOutlined, FolderOpenOutlined } from "@ant-design/icons";
import { Button, Card, List, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import type { Suite } from "../../api/types";
import { formatDateTime } from "../../utils/format";
import { EmptyState, ErrorState } from "../AsyncState";

interface RecentSuitesPanelProps {
  projectId: string;
  projectName: string;
  suites: Suite[];
  loading: boolean;
  error?: unknown;
  onRetry: () => void;
}

export default function RecentSuitesPanel({
  projectId,
  projectName,
  suites,
  loading,
  error,
  onRetry,
}: RecentSuitesPanelProps) {
  const navigate = useNavigate();

  return (
    <Card
      className="surface-card dashboard-recent-suites"
      title="最近 Suite"
      loading={loading}
      extra={
        projectId ? (
          <Button type="link" onClick={() => navigate(`/projects/${projectId}/suites`)}>
            查看全部 <ArrowRightOutlined />
          </Button>
        ) : null
      }
    >
      {error ? <ErrorState compact error={error} onRetry={onRetry} /> : null}
      {!error && !loading ? (
        <List<Suite>
          dataSource={suites}
          locale={{
            emptyText: (
              <EmptyState
                title={projectId ? "尚未创建 Suite" : "请选择一个 Project"}
                description={projectId ? "创建测试套件来组织 API 回归范围。" : undefined}
                action={
                  projectId ? (
                    <Button type="primary" onClick={() => navigate(`/projects/${projectId}/suites`)}>
                      前往 Suite 管理
                    </Button>
                  ) : undefined
                }
              />
            ),
          }}
          renderItem={(suite) => (
            <List.Item
              className="dashboard-clickable-list-item"
              onClick={() => navigate(`/projects/${projectId}/suites/${suite.id}`)}
            >
              <List.Item.Meta
                avatar={<FolderOpenOutlined className="dashboard-list-icon" />}
                title={<Typography.Text strong>{suite.name}</Typography.Text>}
                description={
                  <Space direction="vertical" size={1}>
                    <Typography.Text type="secondary" ellipsis>
                      {suite.description || `${projectName} · 暂无 Suite 描述`}
                    </Typography.Text>
                    <Typography.Text type="secondary">
                      更新于 {formatDateTime(suite.updated_at)}
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
