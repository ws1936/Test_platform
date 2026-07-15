import { App, Button, Form, Input, Modal, Space } from "antd";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { authApi } from "../api/auth";
import { getErrorMessage } from "../api/client";

interface ChangePasswordModalProps {
  open: boolean;
  onClose: () => void;
}

interface ChangePasswordForm {
  old_password: string;
  new_password: string;
  confirm_password: string;
}

export default function ChangePasswordModal({
  open,
  onClose,
}: ChangePasswordModalProps) {
  const { message } = App.useApp();
  const {
    register,
    handleSubmit,
    getValues,
    reset,
    formState: { errors },
  } = useForm<ChangePasswordForm>();

  const mutation = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      message.success("密码修改成功，请在下次登录时使用新密码");
      reset();
      onClose();
    },
    onError: (error) => message.error(getErrorMessage(error, "密码修改失败")),
  });

  const close = () => {
    if (mutation.isPending) return;
    reset();
    onClose();
  };

  return (
    <Modal
      title="修改密码"
      open={open}
      onCancel={close}
      footer={null}
      destroyOnClose
    >
      <form
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            old_password: values.old_password,
            new_password: values.new_password,
          }),
        )}
      >
        <Form.Item
          label="当前密码"
          validateStatus={errors.old_password ? "error" : undefined}
          help={errors.old_password?.message}
        >
          <Input.Password
            autoComplete="current-password"
            {...register("old_password", { required: "请输入当前密码" })}
          />
        </Form.Item>
        <Form.Item
          label="新密码"
          validateStatus={errors.new_password ? "error" : undefined}
          help={errors.new_password?.message}
        >
          <Input.Password
            autoComplete="new-password"
            {...register("new_password", {
              required: "请输入新密码",
              minLength: { value: 8, message: "新密码至少 8 位" },
              validate: (value) =>
                value !== getValues("old_password") || "新密码不能与当前密码相同",
            })}
          />
        </Form.Item>
        <Form.Item
          label="确认新密码"
          validateStatus={errors.confirm_password ? "error" : undefined}
          help={errors.confirm_password?.message}
        >
          <Input.Password
            autoComplete="new-password"
            {...register("confirm_password", {
              required: "请再次输入新密码",
              validate: (value) => value === getValues("new_password") || "两次密码不一致",
            })}
          />
        </Form.Item>
        <Space className="modal-actions">
          <Button onClick={close} disabled={mutation.isPending}>
            取消
          </Button>
          <Button type="primary" htmlType="submit" loading={mutation.isPending}>
            确认修改
          </Button>
        </Space>
      </form>
    </Modal>
  );
}
