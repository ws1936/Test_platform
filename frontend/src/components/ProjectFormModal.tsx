import { useEffect, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, App, Button, Form, Input, Modal, Space } from "antd";
import { Controller, useForm } from "react-hook-form";

import { getApiError } from "../api/client";
import { projectsApi } from "../api/projects";
import { queryKeys } from "../api/queryKeys";
import type { Project, ProjectPayload, ProjectList } from "../api/types";

interface ProjectFormModalProps {
  open: boolean;
  project?: Project | null;
  onClose: () => void;
  onSaved?: (project: Project) => void;
}

const FIELD_MESSAGES: Record<string, string> = {
  name: "请输入项目名称",
};

/**
 * Project create/edit modal — full P1 state machine.
 *
 * Phases (controlled by mutation + form):
 *   - idle / editing
 *   - validating  (RHF)
 *   - submitting
 *   - success    (auto-close + cache handoff + navigate)
 *   - failed     (persistent Alert + field error mapping)
 *
 * The form preserves typed input on failed submissions, and supports
 * AbortController for in-flight requests.  After closing the dialog
 * the mutation is reset so the next open starts in a clean state.
 */
export default function ProjectFormModal({
  open,
  project,
  onClose,
  onSaved,
}: ProjectFormModalProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    setError,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<ProjectPayload>({
    shouldFocusError: true,
    defaultValues: { name: "", description: "" },
  });

  const mutation = useMutation({
    mutationFn: (payload: ProjectPayload) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      return project
        ? projectsApi.update(project.id, payload, controller.signal)
        : projectsApi.create(payload, controller.signal);
    },
    onSuccess: (saved) => {
      // Direct cache handoff: saved Project is now visible in every
      // place that reads the same key, without waiting for refetch.
      queryClient.setQueryData(queryKeys.project(saved.id), saved);
      queryClient.setQueryData<ProjectList | undefined>(
        queryKeys.projects({ page: 1, size: 20 }),
        (prev) => {
          if (!prev) return prev;
          const exists = prev.items.some((item) => item.id === saved.id);
          if (exists) {
            return {
              ...prev,
              items: prev.items.map((item) =>
                item.id === saved.id ? saved : item,
              ),
              total: prev.items.length,
            };
          }
          return {
            ...prev,
            items: [saved, ...prev.items],
            total: prev.items.length + 1,
          };
        },
      );
      message.success(
        project ? `已更新项目 ${saved.name}` : `已创建项目 ${saved.name}`,
      );
      onSaved?.(saved);
      onClose();
    },
    onError: (error) => {
      const apiError = getApiError(error);

      // Field-level mapping for 422 validation details.
      if (apiError.code === "VALIDATION_ERROR" && apiError.fields) {
        for (const [rawField, message] of Object.entries(apiError.fields)) {
          const field = rawField.replace(/^body\./, "");
          setError(field as keyof ProjectPayload, {
            type: "server",
            message,
          });
        }
        return;
      }

      // Domain conflict -> highlight the name field.
      if (apiError.code === "PROJECT_NAME_TAKEN") {
        setError("name", {
          type: "server",
          message: apiError.message || "项目名称已存在",
        });
      }
    },
  });

  // Reset form whenever the modal opens or the target project changes.
  // NOTE: intentionally does NOT depend on `mutation` — TanStack Query v5
  // returns a NEW mutation object every render (`return { ...result, mutate }`),
  // which would otherwise re-fire this effect (and call `reset()`) on every
  // keystroke, blowing away the user's input mid-typing.
  useEffect(() => {
    if (open) {
      reset({
        name: project?.name ?? "",
        description: project?.description ?? "",
      });
    }
    // Closing-side cleanup is handled in `close()` so we don't need
    // `mutation` / `abortRef` here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, project, reset]);

  const close = () => {
    if (mutation.isPending) return;
    // Drop the mutation state and abort any in-flight request so the
    // next open is a clean slate.
    mutation.reset();
    abortRef.current?.abort();
    abortRef.current = null;
    onClose();
  };

  const submit = (values: ProjectPayload) => {
    mutation.mutate({
      name: values.name.trim(),
      description: values.description?.trim() ? values.description.trim() : null,
    });
  };

  const apiError = mutation.error ? getApiError(mutation.error) : null;
  const showPersistentAlert =
    !!mutation.isError && apiError && !apiError.code.startsWith("VALIDATION_");

  const retry = () => {
    // Re-submit the current form values (preserves user input).
    const current = getValues();
    submit({
      name: (current.name ?? "").trim(),
      description: current.description?.trim()
        ? current.description.trim()
        : null,
    });
  };

  return (
    <Modal
      title={project ? "编辑项目" : "新建项目"}
      open={open}
      onCancel={close}
      footer={null}
      destroyOnClose
      maskClosable={!mutation.isPending}
      closable={!mutation.isPending}
    >
      <form onSubmit={handleSubmit(submit)} noValidate>
        <Form.Item
          label="项目名称"
          required
          validateStatus={errors.name ? "error" : undefined}
          help={errors.name?.message ?? FIELD_MESSAGES.name}
        >
          <Controller
            control={control}
            name="name"
            rules={{
              required: "请输入项目名称",
              maxLength: { value: 100, message: "项目名称最多 100 字" },
            }}
            render={({ field }) => (
              <Input
                {...field}
                value={field.value ?? ""}
                placeholder="例如：用户服务 API"
                maxLength={100}
                showCount
                autoFocus
              />
            )}
          />
        </Form.Item>
        <Form.Item
          label="项目描述"
          validateStatus={errors.description ? "error" : undefined}
          help={errors.description?.message}
        >
          <Controller
            control={control}
            name="description"
            render={({ field }) => (
              <Input.TextArea
                {...field}
                value={field.value ?? ""}
                rows={4}
                placeholder="说明测试范围、服务边界或维护约定"
              />
            )}
          />
        </Form.Item>

        {showPersistentAlert && apiError ? (
          <Alert
            className="inline-warning"
            type="error"
            showIcon
            message={apiError.code === "INTERNAL_ERROR" ? "创建失败" : "保存失败"}
            description={apiError.message}
            action={
              <Button size="small" onClick={retry}>
                重新提交
              </Button>
            }
          />
        ) : null}

        <Space className="modal-actions">
          <Button onClick={close} disabled={mutation.isPending}>
            取消
          </Button>
          <Button
            type="primary"
            htmlType="submit"
            loading={mutation.isPending || isSubmitting}
          >
            {project
              ? mutation.isError
                ? "重新保存"
                : "保存"
              : mutation.isError
                ? "重新提交"
                : "创建并进入"}
          </Button>
        </Space>
      </form>
    </Modal>
  );
}
