import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App, Button, Form, Input, Modal, Space } from "antd";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { getErrorMessage } from "../api/client";
import { suitesApi } from "../api/suites";
import type { Suite, SuitePayload } from "../api/types";

interface SuiteFormModalProps {
  open: boolean;
  projectId: string;
  suite?: Suite | null;
  onClose: () => void;
}

export default function SuiteFormModal({ open, projectId, suite, onClose }: SuiteFormModalProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<SuitePayload>();

  useEffect(() => {
    if (open) reset({ name: suite?.name ?? "", description: suite?.description ?? "" });
  }, [open, reset, suite]);

  const mutation = useMutation({
    mutationFn: (payload: SuitePayload) =>
      suite ? suitesApi.update(projectId, suite.id, payload) : suitesApi.create(projectId, payload),
    onSuccess: () => {
      message.success(suite ? "测试套件已更新" : "测试套件已创建");
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "suites"] });
      onClose();
    },
    onError: (error) => message.error(getErrorMessage(error, "测试套件保存失败")),
  });

  return (
    <Modal title={suite ? "编辑测试套件" : "新建测试套件"} open={open} onCancel={onClose} footer={null} destroyOnClose>
      <form onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <Form.Item label="套件名称" validateStatus={errors.name ? "error" : undefined} help={errors.name?.message}>
          <Input maxLength={100} showCount placeholder="例如：冒烟回归" {...register("name", { required: "请输入套件名称" })} />
        </Form.Item>
        <Form.Item label="描述">
          <Input.TextArea rows={4} placeholder="说明该套件覆盖的业务范围" {...register("description")} />
        </Form.Item>
        <Space className="modal-actions">
          <Button onClick={onClose} disabled={mutation.isPending}>取消</Button>
          <Button type="primary" htmlType="submit" loading={mutation.isPending}>保存</Button>
        </Space>
      </form>
    </Modal>
  );
}
