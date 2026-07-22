import { DeleteOutlined, EditOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Descriptions,
  Popconfirm,
  Space,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { projectsApi } from "../../api/projects";
import { queryKeys } from "../../api/queryKeys";
import { LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import ProjectFormModal from "../../components/ProjectFormModal";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { formatDateTime, shortId } from "../../utils/format";

/**
 * Workspace Information — 项目设置 / 信息维护。
 *
 * 提供三项能力：
 * 1. 查看 Project 元数据（id / owner / 创建 / 更新时间 / 当前就绪态）
 * 2. 编辑 Project 名称 / 描述（复用 Projects 页的 ProjectFormModal）
 * 3. 删除 Project（带级联资产二次确认）
 */
export default function WorkspaceInformation() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId, project, readiness, refresh } = useProjectWorkspace();
  const [editOpen, setEditOpen] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => projectsApi.remove(projectId),
    onSuccess: () => {
      message.success("项目已删除");
      // 失效所有 projects 相关缓存，并跳到列表页
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate("/projects", { replace: true });
    },
    onError: (error) => message.error(getErrorMessage(error, "项目删除失败")),
  });

  if (!project) {
    return <LoadingBlock rows={6} />;
  }

  return (
    <>
      <PageHeader
        title="项目信息"
        description="查看 Project 基本信息、修改名称 / 描述、删除 Project"
        breadcrumbs={[
          { title: "Project 工作区", href: "../overview" },
          { title: "项目信息" },
        ]}
        extra={
          <Space>
            <Button icon={<EditOutlined />} onClick={() => setEditOpen(true)}>
              编辑
            </Button>
            <Popconfirm
              title="删除项目"
              description={
                <Space direction="vertical" size={4}>
                  <span>
                    确认永久删除项目「
                    <Typography.Text strong>{project.name}</Typography.Text>」？
                  </span>
                  <Typography.Text type="warning">
                    将级联删除其下所有 Environment / Suite / TestCase / Run / Result。
                  </Typography.Text>
                </Space>
              }
              okText="确认删除"
              okButtonProps={{
                danger: true,
                loading: deleteMutation.isPending,
              }}
              cancelText="取消"
              icon={<ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />}
              onConfirm={() => deleteMutation.mutate()}
            >
              <Button danger icon={<DeleteOutlined />}>
                删除项目
              </Button>
            </Popconfirm>
          </Space>
        }
      />

      {deleteMutation.isError ? (
        <Alert
          className="inline-warning"
          type="error"
          showIcon
          message="项目删除失败"
          description={getErrorMessage(deleteMutation.error, "项目删除失败")}
          action={
            <Button size="small" onClick={() => deleteMutation.reset()}>
              关闭
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      ) : null}

      <Card className="surface-card" title="基本信息">
        <Descriptions
          column={{ xs: 1, md: 2 }}
          bordered
          size="small"
          items={[
            {
              key: "id",
              label: "Project ID",
              children: <Typography.Text code>{project.id}</Typography.Text>,
            },
            {
              key: "name",
              label: "名称",
              children: <Typography.Text strong>{project.name}</Typography.Text>,
            },
            {
              key: "description",
              label: "描述",
              children: project.description || (
                <Typography.Text type="secondary">暂无描述</Typography.Text>
              ),
              span: 2,
            },
            {
              key: "owner",
              label: "Owner",
              children: <Typography.Text code>{shortId(project.owner_id)}</Typography.Text>,
            },
            {
              key: "created",
              label: "创建时间",
              children: formatDateTime(project.created_at),
            },
            {
              key: "updated",
              label: "更新时间",
              children: formatDateTime(project.updated_at),
            },
          ]}
        />
      </Card>

      <Card className="surface-card" title="资产就绪态" style={{ marginTop: 16 }}>
        <Descriptions
          column={{ xs: 1, md: 2 }}
          size="small"
          items={[
            {
              key: "env",
              label: "环境",
              children: readiness.hasEnvironment ? (
                <Tag color="green">已配置</Tag>
              ) : (
                <Tag>未配置</Tag>
              ),
            },
            {
              key: "defaultEnv",
              label: "默认环境",
              children: readiness.hasDefaultEnvironment ? (
                <Tag color="green">已设置</Tag>
              ) : (
                <Tag color="orange">未设置</Tag>
              ),
            },
            {
              key: "suite",
              label: "Suite",
              children: readiness.hasSuite ? (
                <Tag color="green">已创建</Tag>
              ) : (
                <Tag>未创建</Tag>
              ),
            },
            {
              key: "case",
              label: "Case",
              children: readiness.hasCase ? (
                <Tag color="green">已维护</Tag>
              ) : (
                <Tag>未维护</Tag>
              ),
            },
            {
              key: "run",
              label: "Run 历史",
              children: readiness.hasRun ? (
                <Tag color="green">已有执行记录</Tag>
              ) : (
                <Tag>暂无</Tag>
              ),
              span: 2,
            },
          ]}
        />
        <div style={{ marginTop: 12 }}>
          <Button onClick={refresh} size="small">
            刷新就绪态
          </Button>
        </div>
      </Card>

      <ProjectFormModal
        open={editOpen}
        project={project}
        onClose={() => setEditOpen(false)}
        onSaved={() => {
          // 关闭后立即触发 Workspace 上下文刷新（让 Header / Sider 反映新名称）
          refresh();
          void queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
        }}
      />
    </>
  );
}
