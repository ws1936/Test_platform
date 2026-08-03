import { ArrowRightOutlined, ProjectOutlined } from "@ant-design/icons";
import { Button, Card, List, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import type { Project } from "../../api/types";
import { formatDateTime } from "../../utils/format";
import { EmptyState, ErrorState } from "../AsyncState";

interface RecentProjectsPanelProps {
  projects: Project[];
  loading: boolean;
  error?: unknown;
  onRetry: () => void;
  onCreate: () => void;
}

export default function RecentProjectsPanel({
  projects,
  loading,
  error,
  onRetry,
  onCreate,
}: RecentProjectsPanelProps) {
  const navigate = useNavigate();

  return (
    <Card
      className="surface-card dashboard-recent-projects"
      title="最近项目"
      loading={loading}
      // 优化 C: 把"按创建时间"挪到 extra，与"查看全部"并列，避免与 title 抢眼。
      extra={
        <Space size="middle" align="center">
          <Typography.Text type="secondary" className="dashboard-panel-subtitle">
            按创建时间
          </Typography.Text>
          <Button type="link" onClick={() => navigate("/projects")}>
            查看全部 <ArrowRightOutlined />
          </Button>
        </Space>
      }
    >
      {error ? <ErrorState compact error={error} onRetry={onRetry} /> : null}
      {!error && !loading ? (
        <List<Project>
          dataSource={projects}
          locale={{
            emptyText: (
              <EmptyState
                title="尚未创建 Project"
                description="创建第一个项目，开始配置环境与测试资产。"
                action={<Button type="primary" onClick={onCreate}>新建 Project</Button>}
              />
            ),
          }}
          renderItem={(project) => (
            <List.Item
              className="dashboard-clickable-list-item"
              onClick={() => navigate(`/projects/${project.id}/overview`)}
            >
              <List.Item.Meta
                avatar={<ProjectOutlined className="dashboard-list-icon" />}
                title={<Typography.Text strong>{project.name}</Typography.Text>}
                description={
                  <Space direction="vertical" size={1}>
                    <Typography.Text type="secondary" ellipsis>
                      {project.description || "暂无项目描述"}
                    </Typography.Text>
                    <Typography.Text type="secondary">
                      创建于 {formatDateTime(project.created_at)}
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
