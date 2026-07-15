import {
  ClockCircleOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { Button, Card, Empty, Space, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import type { TestRun } from "../../api/types";
import type { ProjectWorkspaceReadiness } from "./ProjectWorkspaceLayout";
import { formatDateTime, formatPercent } from "../../utils/format";

interface ProjectWorkspaceContextPanelProps {
  defaultEnvironmentId: string | null;
  defaultEnvironmentName: string | null;
  defaultEnvironmentBaseUrl: string | null;
  latestRun: TestRun | null;
  readiness: ProjectWorkspaceReadiness;
}

export default function ProjectWorkspaceContextPanel({
  defaultEnvironmentId,
  defaultEnvironmentName,
  defaultEnvironmentBaseUrl,
  latestRun,
  readiness,
}: ProjectWorkspaceContextPanelProps) {
  const navigate = useNavigate();

  return (
    <aside className="workspace-context">
      <Card className="surface-card workspace-context-card" title="当前默认环境">
        {defaultEnvironmentId ? (
          <Space direction="vertical" size={4}>
            <Space size={6}>
              <DatabaseOutlined style={{ color: "#315efb" }} />
              <Typography.Text strong>{defaultEnvironmentName}</Typography.Text>
            </Space>
            <Typography.Paragraph type="secondary" className="code-path" ellipsis>
              {defaultEnvironmentBaseUrl}
            </Typography.Paragraph>
            <Button type="link" onClick={() => navigate("environment")}>管理环境</Button>
          </Space>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="未设置默认环境"
          />
        )}
      </Card>

      <Card className="surface-card workspace-context-card" title="最近执行">
        {latestRun ? (
          <Space direction="vertical" size={6}>
            <Space>
              <ClockCircleOutlined style={{ color: "#315efb" }} />
              <Typography.Text strong ellipsis style={{ maxWidth: 220 }}>
                {latestRun.name}
              </Typography.Text>
            </Space>
            <Space>
              <Tag color={latestRun.failed + latestRun.error > 0 ? "red" : "green"}>
                通过率 {formatPercent(latestRun.pass_rate)}
              </Tag>
              <Typography.Text type="secondary">
                {formatDateTime(latestRun.created_at)}
              </Typography.Text>
            </Space>
            <Button
              type="link"
              icon={<ThunderboltOutlined />}
              onClick={() => navigate(`report/${latestRun.id}`)}
            >
              打开 Report
            </Button>
          </Space>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="尚无执行记录"
          />
        )}
      </Card>

      <Card className="surface-card workspace-context-card" title="快速创建">
        <Space direction="vertical" size={6}>
          <Button block icon={<PlusOutlined />} onClick={() => navigate("environment")}>
            新建环境
          </Button>
          <Button block icon={<PlusOutlined />} onClick={() => navigate("suite")}>
            新建 Suite
          </Button>
          <Button block icon={<PlusOutlined />} onClick={() => navigate("case/new")}>
            新建 Case
          </Button>
          <Button
            type="primary"
            block
            icon={<PlayCircleOutlined />}
            disabled={!readiness.hasDefaultEnvironment}
            onClick={() => navigate("run")}
          >
            发起执行
          </Button>
        </Space>
      </Card>
    </aside>
  );
}
