import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App, Button, Form, Input, Modal, Select, Space, Switch } from "antd";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { usersApi } from "../api/admin";
import { getErrorMessage } from "../api/client";
import type { Role, User } from "../api/types";

interface UserFormModalProps {
  open: boolean;
  user?: User | null;
  roles: Role[];
  currentUserId?: string;
  onClose: () => void;
}

interface UserFormValues {
  username: string;
  email: string;
  password: string;
  nickname: string;
  phone: string;
  status: number;
  role_id: string | null;
  is_superuser: boolean;
}

export default function UserFormModal({
  open,
  user,
  roles,
  currentUserId,
  onClose,
}: UserFormModalProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const isSelf = user?.id === currentUserId;
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UserFormValues>();

  useEffect(() => {
    if (open) {
      reset({
        username: user?.username ?? "",
        email: user?.email ?? "",
        password: "",
        nickname: user?.nickname ?? "",
        phone: user?.phone ?? "",
        status: user?.status ?? 1,
        role_id: user?.role_id ?? null,
        is_superuser: user?.is_superuser ?? false,
      });
    }
  }, [open, reset, user]);

  const mutation = useMutation({
    mutationFn: async (values: UserFormValues): Promise<void> => {
      if (user) {
        await usersApi.update(user.id, {
          nickname: values.nickname.trim() || null,
          phone: values.phone.trim() || null,
          status: isSelf ? user.status : values.status,
          role_id: values.role_id,
          is_superuser: isSelf ? user.is_superuser : values.is_superuser,
        });
        return;
      }
      await usersApi.create({
        username: values.username.trim(),
        email: values.email.trim(),
        password: values.password,
        nickname: values.nickname.trim() || undefined,
        phone: values.phone.trim() || undefined,
      });
    },
    onSuccess: () => {
      message.success(user ? "用户信息已更新" : "用户已创建");
      void queryClient.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: (error) => message.error(getErrorMessage(error, "用户保存失败")),
  });

  return (
    <Modal
      title={user ? "编辑用户" : "新建用户"}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnClose
      maskClosable={!mutation.isPending}
    >
      <form onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <Form.Item
          label="用户名"
          required={!user}
          validateStatus={errors.username ? "error" : undefined}
          help={errors.username?.message}
        >
          <Input
            disabled={Boolean(user)}
            maxLength={50}
            {...register("username", {
              required: user ? false : "请输入用户名",
              minLength: user ? undefined : { value: 3, message: "用户名至少 3 位" },
            })}
          />
        </Form.Item>
        <Form.Item
          label="邮箱"
          required={!user}
          validateStatus={errors.email ? "error" : undefined}
          help={errors.email?.message}
        >
          <Input
            disabled={Boolean(user)}
            {...register("email", {
              required: user ? false : "请输入邮箱",
              pattern: { value: /^\S+@\S+\.\S+$/, message: "请输入有效邮箱" },
            })}
          />
        </Form.Item>
        {!user ? (
          <Form.Item
            label="初始密码"
            required
            validateStatus={errors.password ? "error" : undefined}
            help={errors.password?.message ?? "至少 8 位；创建后请通过安全渠道通知用户。"}
          >
            <Input.Password
              autoComplete="new-password"
              {...register("password", {
                required: "请输入初始密码",
                minLength: { value: 8, message: "密码至少 8 位" },
              })}
            />
          </Form.Item>
        ) : null}
        <Form.Item label="昵称">
          <Input maxLength={100} {...register("nickname")} />
        </Form.Item>
        <Form.Item label="手机号">
          <Input maxLength={20} {...register("phone")} />
        </Form.Item>
        {user ? (
          <>
            <Form.Item label="角色">
              <Controller
                name="role_id"
                control={control}
                render={({ field }) => (
                  <Select
                    {...field}
                    allowClear
                    placeholder="未分配角色"
                    options={roles.map((role) => ({ value: role.id, label: role.name }))}
                  />
                )}
              />
            </Form.Item>
            <Form.Item label="账号状态" help={isSelf ? "为避免当前会话失效，不能在此禁用自己。" : undefined}>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Select
                    {...field}
                    disabled={isSelf}
                    options={[{ value: 1, label: "启用" }, { value: 0, label: "禁用" }]}
                  />
                )}
              />
            </Form.Item>
            <Form.Item label="超级管理员" help={isSelf ? "不能在当前会话中移除自己的超级管理员标记。" : undefined}>
              <Controller
                name="is_superuser"
                control={control}
                render={({ field }) => (
                  <Switch checked={field.value} onChange={field.onChange} disabled={isSelf} />
                )}
              />
            </Form.Item>
          </>
        ) : null}
        <Space className="modal-actions">
          <Button onClick={onClose} disabled={mutation.isPending}>取消</Button>
          <Button type="primary" htmlType="submit" loading={mutation.isPending}>保存</Button>
        </Space>
      </form>
    </Modal>
  );
}
