import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Popconfirm, Space, Table, Tag, Tooltip, Typography } from "antd";
import { useState } from "react";
import { rolesApi } from "../../api/admin";
import { getErrorMessage } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import type { Role } from "../../api/types";
import { EmptyState, ErrorState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import RoleFormModal from "../../components/RoleFormModal";
import { formatDateTime } from "../../utils/format";

export default function RolesPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Role | null>(null);
  const rolesQuery = useQuery({ queryKey: queryKeys.roles, queryFn: rolesApi.list });
  const deleteMutation = useMutation({
    mutationFn: rolesApi.remove,
    onSuccess: () => {
      message.success("角色已删除");
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
    },
    onError: (error) => message.error(getErrorMessage(error, "角色删除失败")),
  });
  const openCreate = () => { setEditing(null); setFormOpen(true); };

  return (
    <>
      <PageHeader
        title="角色管理"
        description="维护角色元数据与已有权限字符串；系统角色不可删除。"
        breadcrumbs={[{ title: "系统管理" }, { title: "角色管理" }]}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建角色</Button>}
      />
      <Card className="surface-card">
        {rolesQuery.isError ? (
          <ErrorState error={rolesQuery.error} onRetry={() => void rolesQuery.refetch()} />
        ) : (
          <Table<Role>
            rowKey="id"
            loading={rolesQuery.isLoading}
            scroll={{ x: "max-content" }}
            dataSource={rolesQuery.data ?? []}
            pagination={false}
            locale={{ emptyText: <EmptyState title="暂无角色" action={<Button type="primary" onClick={openCreate}>新建角色</Button>} /> }}
            columns={[
              { title: "角色名称", dataIndex: "name", render: (name: string, role) => <Space><Typography.Text strong>{name}</Typography.Text>{role.is_system ? <Tag color="blue">系统角色</Tag> : null}</Space> },
              { title: "描述", dataIndex: "description", ellipsis: true, render: (value: string | null) => value || "—" },
              {
                title: "权限字符串",
                dataIndex: "permissions",
                render: (permissions: string[] | null) => permissions?.length ? <Space wrap>{permissions.slice(0, 5).map((permission) => <Tag key={permission}>{permission}</Tag>)}{permissions.length > 5 ? <Tooltip title={permissions.slice(5).join("、")}><Tag>+{permissions.length - 5}</Tag></Tooltip> : null}</Space> : <Typography.Text type="secondary">未配置</Typography.Text>,
              },
              { title: "更新时间", dataIndex: "updated_at", width: 190, render: formatDateTime },
              {
                title: "操作",
                width: 180,
                render: (_, role) => (
                  <Space>
                    <Button type="link" icon={<EditOutlined />} onClick={() => { setEditing(role); setFormOpen(true); }}>编辑</Button>
                    {role.is_system ? (
                      <Tooltip title="系统角色不可删除"><Button type="link" danger disabled icon={<DeleteOutlined />}>删除</Button></Tooltip>
                    ) : (
                      <Popconfirm title="删除角色" description="若角色仍被用户使用，后端可能拒绝删除。" okText="删除" cancelText="取消" okButtonProps={{ danger: true }} onConfirm={() => deleteMutation.mutate(role.id)}>
                        <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                      </Popconfirm>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Card>
      <RoleFormModal open={formOpen} role={editing} onClose={() => setFormOpen(false)} />
    </>
  );
}
