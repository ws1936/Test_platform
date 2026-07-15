import { EditOutlined, PlusOutlined, StopOutlined, UnlockOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Input, Popconfirm, Space, Table, Tag, Typography } from "antd";
import { useState } from "react";
import { rolesApi, usersApi } from "../../api/admin";
import { getErrorMessage } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import type { User } from "../../api/types";
import { EmptyState, ErrorState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import UserFormModal from "../../components/UserFormModal";
import { useAuthStore } from "../../store/auth";
import { formatDateTime } from "../../utils/format";

const PAGE_SIZE = 20;

export default function UsersPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((state) => state.user);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);

  const usersQuery = useQuery({
    queryKey: queryKeys.users({ page, size: PAGE_SIZE, search }),
    queryFn: () => usersApi.list({ page, size: PAGE_SIZE, search: search || undefined }),
  });
  const rolesQuery = useQuery({ queryKey: queryKeys.roles, queryFn: rolesApi.list });
  const roleNames = new Map((rolesQuery.data ?? []).map((role) => [role.id, role.name]));

  const statusMutation = useMutation({
    mutationFn: async ({ userId, status }: { userId: string; status: number }): Promise<void> => {
      if (status === 0) await usersApi.disable(userId);
      else await usersApi.update(userId, { status: 1 });
    },
    onSuccess: (_, variables) => {
      message.success(variables.status === 0 ? "用户已禁用" : "用户已启用");
      void queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => message.error(getErrorMessage(error, "用户状态更新失败")),
  });

  const openCreate = () => { setEditing(null); setFormOpen(true); };

  return (
    <>
      <PageHeader
        title="用户管理"
        description="管理平台账号、角色、状态与超级管理员标记。"
        breadcrumbs={[{ title: "系统管理" }, { title: "用户管理" }]}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用户</Button>}
      />
      <Card className="surface-card">
        <div className="toolbar">
          <Input.Search
            allowClear
            placeholder="搜索邮箱、用户名或昵称"
            style={{ width: 340 }}
            onSearch={(value) => { setSearch(value.trim()); setPage(1); }}
          />
          <Typography.Text type="secondary">共 {usersQuery.data?.total ?? 0} 个用户</Typography.Text>
        </div>
        {usersQuery.isError ? (
          <ErrorState error={usersQuery.error} onRetry={() => void usersQuery.refetch()} />
        ) : (
          <Table<User>
            rowKey="id"
            loading={usersQuery.isLoading}
            dataSource={usersQuery.data?.items ?? []}
            locale={{ emptyText: <EmptyState title={search ? "未找到匹配用户" : "暂无用户"} action={!search ? <Button type="primary" onClick={openCreate}>新建用户</Button> : undefined} /> }}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: usersQuery.data?.total ?? 0,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 项`,
              onChange: setPage,
            }}
            columns={[
              {
                title: "用户",
                render: (_, user) => (
                  <Space direction="vertical" size={0}>
                    <Typography.Text strong>{user.nickname || user.username}</Typography.Text>
                    <Typography.Text type="secondary">{user.email}</Typography.Text>
                  </Space>
                ),
              },
              { title: "用户名", dataIndex: "username", width: 150 },
              { title: "角色", dataIndex: "role_id", width: 150, render: (roleId: string | null) => roleId ? roleNames.get(roleId) ?? "未知角色" : <Typography.Text type="secondary">未分配</Typography.Text> },
              { title: "权限级别", width: 130, render: (_, user) => user.is_superuser ? <Tag color="purple">超级管理员</Tag> : <Tag>普通用户</Tag> },
              { title: "状态", dataIndex: "status", width: 100, render: (status: number) => <Tag color={status === 1 ? "green" : "red"}>{status === 1 ? "启用" : "禁用"}</Tag> },
              { title: "最后登录", dataIndex: "last_login_time", width: 190, render: formatDateTime },
              {
                title: "操作",
                width: 200,
                render: (_, user) => {
                  const isSelf = currentUser?.id === user.id;
                  return (
                    <Space>
                      <Button type="link" icon={<EditOutlined />} onClick={() => { setEditing(user); setFormOpen(true); }}>编辑</Button>
                      {user.status === 1 ? (
                        <Popconfirm title="禁用用户" description={isSelf ? "不能禁用当前登录账号。" : "禁用后该用户已有 Token 将失效。"} disabled={isSelf} okText="禁用" cancelText="取消" okButtonProps={{ danger: true }} onConfirm={() => statusMutation.mutate({ userId: user.id, status: 0 })}>
                          <Button type="link" danger disabled={isSelf} icon={<StopOutlined />}>禁用</Button>
                        </Popconfirm>
                      ) : (
                        <Button type="link" icon={<UnlockOutlined />} onClick={() => statusMutation.mutate({ userId: user.id, status: 1 })}>启用</Button>
                      )}
                    </Space>
                  );
                },
              },
            ]}
          />
        )}
      </Card>
      <UserFormModal
        open={formOpen}
        user={editing}
        roles={rolesQuery.data ?? []}
        currentUserId={currentUser?.id}
        onClose={() => setFormOpen(false)}
      />
    </>
  );
}
