import { DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Input, Popconfirm, Space, Table, Typography } from "antd";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { suitesApi } from "../../api/suites";
import { queryKeys } from "../../api/queryKeys";
import type { Suite } from "../../api/types";
import { EmptyState, ErrorState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import SuiteFormModal from "../../components/SuiteFormModal";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { formatDateTime } from "../../utils/format";

export default function WorkspaceSuiteListPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId = "" } = useParams();
  const { refresh: refreshWorkspace } = useProjectWorkspace();
  const [search, setSearch] = useState("");
  const [committedSearch, setCommittedSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Suite | null>(null);

  const suitesQuery = useQuery({
    queryKey: queryKeys.suites(projectId, committedSearch),
    queryFn: () => suitesApi.list(projectId, committedSearch),
    enabled: Boolean(projectId),
  });
  const suites = suitesQuery.data?.items ?? [];

  const refreshAll = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.suites(projectId, "") });
    refreshWorkspace();
  };

  const deleteMutation = useMutation({
    mutationFn: (suiteId: string) => suitesApi.remove(projectId, suiteId),
    onSuccess: () => {
      message.success("测试套件已删除");
      refreshAll();
    },
    onError: (error) => message.error(getErrorMessage(error, "测试套件删除失败")),
  });

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  return (
    <>
      <PageHeader
        title="测试套件"
        description="按业务场景组织 API 用例；同一 Project 内的 Suite 互不冲突。"
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "测试套件" },
        ]}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建 Suite
          </Button>
        }
      />
      <Card className="surface-card">
        <div className="toolbar">
          <div className="toolbar-left">
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="按 Suite 名称搜索"
              style={{ width: 320 }}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onPressEnter={() => setCommittedSearch(search.trim())}
              onClear={() => {
                setSearch("");
                setCommittedSearch("");
              }}
            />
            <Button onClick={() => setCommittedSearch(search.trim())}>搜索</Button>
          </div>
          <Typography.Text type="secondary">共 {suitesQuery.data?.total ?? 0} 个 Suite</Typography.Text>
        </div>
        {suitesQuery.isError ? (
          <ErrorState error={suitesQuery.error} onRetry={() => void suitesQuery.refetch()} />
        ) : (
          <Table<Suite>
            rowKey="id"
            loading={suitesQuery.isLoading}
            dataSource={suites}
            pagination={false}
            scroll={{ x: "max-content" }}
            locale={{
              emptyText: (
                <EmptyState
                  title={committedSearch ? "未找到匹配 Suite" : "尚未创建测试套件"}
                  description={committedSearch ? undefined : "先创建 Suite，再手工创建或导入 API 用例。"}
                  action={
                    !committedSearch ? (
                      <Button type="primary" onClick={openCreate}>
                        新建 Suite
                      </Button>
                    ) : undefined
                  }
                />
              ),
            }}
            columns={[
              {
                title: "Suite 名称",
                dataIndex: "name",
                render: (name: string, suite) => (
                  <Button
                    type="link"
                    className="table-link"
                    onClick={() => navigate(`/projects/${projectId}/workspace/suite/${suite.id}`)}
                  >
                    {name}
                  </Button>
                ),
              },
              {
                title: "描述",
                dataIndex: "description",
                ellipsis: true,
                render: (value: string | null) => value || <Typography.Text type="secondary">暂无描述</Typography.Text>,
              },
              { title: "排序", dataIndex: "sort_order", width: 90 },
              { title: "更新时间", dataIndex: "updated_at", width: 190, render: formatDateTime },
              {
                title: "操作",
                key: "actions",
                width: 220,
                render: (_, suite) => (
                  <Space>
                    <Button
                      type="link"
                      icon={<EditOutlined />}
                      onClick={() => {
                        setEditing(suite);
                        setFormOpen(true);
                      }}
                    >
                      编辑
                    </Button>
                    <Popconfirm
                      title="删除测试套件"
                      description="只删除 Suite 及关联关系，不删除 API 用例本体。"
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{
                        danger: true,
                        loading: deleteMutation.isPending && deleteMutation.variables === suite.id,
                      }}
                      onConfirm={() => deleteMutation.mutate(suite.id)}
                    >
                      <Button type="link" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Card>
      <SuiteFormModal
        open={formOpen}
        projectId={projectId}
        suite={editing}
        onClose={() => setFormOpen(false)}
      />
    </>
  );
}
