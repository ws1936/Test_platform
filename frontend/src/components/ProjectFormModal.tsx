import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App, Button, Form, Input, Modal, Space } from "antd";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { getErrorMessage } from "../api/client";
import { projectsApi } from "../api/projects";
import type { Project, ProjectPayload } from "../api/types";

interface ProjectFormModalProps {
  open: boolean;
  project?: Project | null;
  onClose: () => void;
  onSaved?: (project: Project) => void;
}

export default function ProjectFormModal({
  open,
  project,
  onClose,
  onSaved,
}: ProjectFormModalProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProjectPayload>();

  useEffect(() => {
    if (open) {
      reset({ name: project?.name ?? "", description: project?.description ?? "" });
    }
  }, [open, project, reset]);

  const mutation = useMutation({
    mutationFn: (payload: ProjectPayload) =>
      project ? projectsApi.update(project.id, payload) : projectsApi.create(payload),
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      message.success(project ? "项目已更新" : "项目已创建");
      onSaved?.(saved);
      onClose();
    },
    onError: (error) => message.error(getErrorMessage(error)),
  });

  return (
    <Modal
      title={project ? "编辑项目" : "新建项目"}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnClose
      maskClosable={!mutation.isPending}
    >
      <form onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <Form.Item
          label="项目名称"
          validateStatus={errors.name ? "error" : undefined}
          help={errors.name?.message}
        >
          <Input
            placeholder="例如：用户服务 API"
            maxLength={100}
            showCount
            {...register("name", { required: "请输入项目名称" })}
          />
        </Form.Item>
        <Form.Item label="项目描述">
          <Input.TextArea
            rows={4}
            placeholder="说明测试范围、服务边界或维护约定"
            {...register("description")}
          />
        </Form.Item>
        <Space className="modal-actions">
          <Button onClick={onClose} disabled={mutation.isPending}>取消</Button>
          <Button type="primary" htmlType="submit" loading={mutation.isPending}>
            {project ? "保存" : "创建并进入"}
          </Button>
        </Space>
      </form>
    </Modal>
  );
}
