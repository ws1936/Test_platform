import { PlayCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Avatar, Button, Space, Tag, Tooltip, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { queryKeys } from "../../api/queryKeys";
import { environmentsApi } from "../../api/environments";
import type { Project, TestRun } from "../../api/types";
import { useProjectWorkspace } from "./projectWorkspaceContext";
import { formatDateTime, formatPercent } from "../../utils/format";

interface ProjectWorkspaceHeaderProps {
  project: Project;
  latestRun: TestRun | null;
  defaultEnvironmentId: string | null;
}

export default function ProjectWorkspaceHeader({
  project,
  latestRun,
  defaultEnvironmentId,
}: ProjectWorkspaceHeaderProps) {
  const navigate = useNavigate();
  const { refresh, readiness } = useProjectWorkspace();
  const environmentsQuery = useQuery({
    queryKey: queryKeys.environments(project.id, ""),
    queryFn: () => environmentsApi.list(project.id),
    enabled: Boolean(project.id),
    staleTime: 60_000,
  });
  const defaultEnvironment = environmentsQuery.data?.items.find((env) => env.id === defaultEnvironmentId) ?? null;

  const summaryItems: { label: string; pass: boolean; hint?: string }[] = [
    {
      label: "环境",
      pass: readiness.hasEnvironment,
      hint: readiness.hasEnvironment ? "已配置" : "尚未配置",
    },
    {
      label: "默认环境",
      pass: readiness.hasDefaultEnvironment,
      hint: readiness.hasDefaultEnvironment ? defaultEnvironment?.name ?? "已设置" : "未设置",
    },
    {
      label: "Suite",
      pass: readiness.hasSuite,
      hint: readiness.hasSuite ? "已就绪" : "尚未创建",
    },
    {
      label: "Case",
      pass: readiness.hasCase,
      hint: readiness.hasCase ? "已就绪" : "尚未创建",
    },
  ];

  return (
    <header className="workspace-header">
      <div className="workspace-header-main">
        <Space align="center" size={16}>
          <Avatar size={48} shape="square" className="workspace-header-avatar">
            {project.name.slice(0, 1).toUpperCase()}
          </Avatar>
          <Space direction="vertical" size={2}>
            <Space size={8} align="center">
              <Typography.Title level={3} className="workspace-header-title" onClick={() => navigate(`/projects/${project.id}/workspace/overview`)}>
                {project.name}
              </Typography.Title>
              <Tag color="blue" bordered={false}>Project</Tag>
              <Tooltip title={project.description ?? "暂无描述"}>
                <Typography.Text type="secondary" ellipsis style={{ maxWidth: 360 }}>
                  {project.description || "暂无项目描述"}
                </Typography.Text>
              </Tooltip>
            </Space>
            <Space size={12} align="center" wrap>
              <Typography.Text type="secondary">Owner</Typography.Text>
              <Typography.Text code className="workspace-header-owner">
                {project.owner_id.slice(0, 8)}…
              </Typography.Text>
              <Typography.Text type="secondary">· 更新于 {formatDateTime(project.updated_at)}</Typography.Text>
            </Space>
          </Space>
        </Space>
        <Space wrap>
          {summaryItems.map((item) => (
            <Tooltip key={item.label} title={item.hint}>
              <Tag color={item.pass ? "green" : "default"} bordered={false} className="workspace-header-tag">
                {item.label}：{item.hint}
              </Tag>
            </Tooltip>
          ))}
        </Space>
        <Space>
          {latestRun ? (
            <Tooltip title={`通过率 ${formatPercent(latestRun.pass_rate)} · ${formatDateTime(latestRun.created_at)}`}>
              <Button
                onClick={() => navigate(`/projects/${project.id}/workspace/report/${latestRun.id}`)}
              >
                最近执行
              </Button>
            </Tooltip>
          ) : null}
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() =>
              navigate(`/projects/${project.id}/workspace/run?scope=project`)
            }
          >
            快速执行
          </Button>
          <Button icon={<ReloadOutlined />} onClick={refresh}>
            刷新
          </Button>
        </Space>
      </div>
    </header>
  );
}
