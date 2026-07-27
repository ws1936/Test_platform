import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Input, Popconfirm, Space, Table, Typography } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { projectsApi } from "../api/projects";
import { queryKeys } from "../api/queryKeys";
import type { Project } from "../api/types";
import { EmptyState, ErrorState } from "../components/AsyncState";
import PageHeader from "../components/PageHeader";
import ProjectFormModal from "../components/ProjectFormModal";
import { formatDateTime, shortId } from "../utils/format";

const PAGE_SIZE = 20;

export default function ProjectsPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects({ page, size: PAGE_SIZE, search }),
    queryFn: () => projectsApi.list({ page, size: PAGE_SIZE, search: search || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: projectsApi.remove,
    onSuccess: () => {
      message.success("项目已删除");
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error) => message.error(getErrorMessage(error, "项目删除失败")),
  });

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  return (
    <>
      <PageHeader
        title="项目"
        description="Project 是环境、测试资产、执行与报告的统一归属边界。"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建项目</Button>}
      />
      <Card className="surface-card">
        <div className="toolbar">
          <div className="toolbar-left">
            <Input.Search
              allowClear
              placeholder="按项目名称搜索"
              style={{ width: 320 }}
              onSearch={(value) => { setSearch(value.trim()); setPage(1); }}
            />
          </div>
          <Typography.Text type="secondary">共 {projectsQuery.data?.total ?? 0} 个项目</Typography.Text>
        </div>
        {projectsQuery.isError ? (
          <ErrorState error={projectsQuery.error} onRetry={() => void projectsQuery.refetch()} />
        ) : (
          <Table<Project>
            rowKey="id"
            loading={projectsQuery.isLoading}
            scroll={{ x: "max-content" }}
            dataSource={projectsQuery.data?.items ?? []}
            locale={{
              emptyText: <EmptyState title={search ? "未找到匹配项目" : "尚未创建项目"} action={!search ? <Button type="primary" onClick={openCreate}>新建项目</Button> : undefined} />,
            }}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: projectsQuery.data?.total ?? 0,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 项`,
              onChange: setPage,
            }}
            columns={[
              {
                title: "项目名称",
                dataIndex: "name",
                render: (name: string, project) => (
                  <Button type="link" className="table-link" onClick={() => navigate(`/projects/${project.id}/overview`)}>{name}</Button>
                ),
              },
              {
                title: "描述",
                dataIndex: "description",
                ellipsis: true,
                render: (value: string | null) => value || <Typography.Text type="secondary">暂无描述</Typography.Text>,
              },
              { title: "Owner", dataIndex: "owner_id", width: 130, render: shortId },
              { title: "更新时间", dataIndex: "updated_at", width: 190, render: formatDateTime },
              {
                title: "操作",
                key: "actions",
                width: 180,
                render: (_, project) => (
                  <Space>
                    <Button type="link" icon={<EditOutlined />} onClick={() => { setEditing(project); setFormOpen(true); }}>编辑</Button>
                    <Popconfirm
                      title="删除项目"
                      description={`确认永久删除“${project.name}”及其下属资产？`}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true, loading: deleteMutation.isPending }}
                      onConfirm={() => deleteMutation.mutate(project.id)}
                    >
                      <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Card>
      <ProjectFormModal
        open={formOpen}
        project={editing}
        onClose={() => setFormOpen(false)}
        onSaved={(project) => {
          if (!editing) {
            const next = new URLSearchParams();
            next.set("justCreated", "1");
            navigate(`/projects/${project.id}/workspace/overview?${next.toString()}`);
          }
        }}
      />
    </>
  );
}
