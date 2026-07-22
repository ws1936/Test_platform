import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App, Button, Form, Input, Modal, Space } from "antd";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
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
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SuitePayload>({
    defaultValues: { name: "", description: "" },
  });

  // Reset form whenever the modal opens or the target suite changes.
  // NOTE: do NOT add `mutation` to deps — TanStack Query v5 returns a NEW
  // mutation object every render (`return { ...result, mutate }`), which
  // would otherwise re-fire `reset()` on every keystroke and blow away
  // the user's input mid-typing.
  useEffect(() => {
    if (open) {
      reset({
        name: suite?.name ?? "",
        description: suite?.description ?? "",
      });
    }
    // (eslint-disable removed: was unused)
  }, [open, suite, reset]);

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

  const submit = (values: SuitePayload) => {
    mutation.mutate({
      name: values.name.trim(),
      description: values.description?.trim() ? values.description.trim() : null,
    });
  };

  return (
    <Modal title={suite ? "编辑测试套件" : "新建测试套件"} open={open} onCancel={onClose} footer={null} destroyOnClose>
      <form onSubmit={handleSubmit(submit)} noValidate>
        <Form.Item
          label="套件名称"
          validateStatus={errors.name ? "error" : undefined}
          help={errors.name?.message}
        >
          <Controller
            control={control}
            name="name"
            rules={{
              required: "请输入套件名称",
              maxLength: { value: 100, message: "套件名称最多 100 字" },
            }}
            render={({ field }) => (
              <Input
                {...field}
                value={field.value ?? ""}
                maxLength={100}
                showCount
                placeholder="例如：冒烟回归"
              />
            )}
          />
        </Form.Item>
        <Form.Item label="描述">
          <Controller
            control={control}
            name="description"
            render={({ field }) => (
              <Input.TextArea
                {...field}
                value={field.value ?? ""}
                rows={4}
                placeholder="说明该套件覆盖的业务范围"
              />
            )}
          />
        </Form.Item>
        <Space className="modal-actions">
          <Button onClick={onClose} disabled={mutation.isPending}>取消</Button>
          <Button type="primary" htmlType="submit" loading={mutation.isPending}>保存</Button>
        </Space>
      </form>
    </Modal>
  );
}