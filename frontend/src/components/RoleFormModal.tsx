import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App, Button, Form, Input, Modal, Space } from "antd";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { rolesApi } from "../api/admin";
import { getErrorMessage } from "../api/client";
import type { Role, RolePayload } from "../api/types";

interface RoleFormModalProps {
  open: boolean;
  role?: Role | null;
  onClose: () => void;
}

interface RoleFormValues {
  name: string;
  description: string;
  permissionsText: string;
}

export default function RoleFormModal({ open, role, onClose }: RoleFormModalProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<RoleFormValues>();

  useEffect(() => {
    if (open) {
      reset({
        name: role?.name ?? "",
        description: role?.description ?? "",
        permissionsText: (role?.permissions ?? []).join("\n"),
      });
    }
  }, [open, reset, role]);

  const mutation = useMutation({
    mutationFn: (values: RoleFormValues) => {
      const payload: RolePayload = {
        name: values.name.trim(),
        description: values.description.trim() || null,
        permissions: values.permissionsText
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
      };
      return role ? rolesApi.update(role.id, payload) : rolesApi.create(payload);
    },
    onSuccess: () => {
      message.success(role ? "角色已更新" : "角色已创建");
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
      onClose();
    },
    onError: (error) => message.error(getErrorMessage(error, "角色保存失败")),
  });

  return (
    <Modal title={role ? "编辑角色" : "新建角色"} open={open} onCancel={onClose} footer={null} destroyOnClose>
      <form onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <Form.Item label="角色名称" required validateStatus={errors.name ? "error" : undefined} help={errors.name?.message}>
          <Input maxLength={50} {...register("name", { required: "请输入角色名称" })} />
        </Form.Item>
        <Form.Item label="描述">
          <Input.TextArea rows={3} maxLength={255} showCount {...register("description")} />
        </Form.Item>
        <Form.Item label="权限字符串" help="每行一个权限字符串。当前没有权限字典接口，不构造虚假的资源树。">
          <Input.TextArea className="json-editor" rows={8} placeholder={"project:read\nproject:write\nreport:read"} {...register("permissionsText")} />
        </Form.Item>
        <Space className="modal-actions">
          <Button onClick={onClose} disabled={mutation.isPending}>取消</Button>
          <Button type="primary" htmlType="submit" loading={mutation.isPending}>保存</Button>
        </Space>
      </form>
    </Modal>
  );
}
