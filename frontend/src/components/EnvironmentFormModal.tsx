import { useMutation, useQueryClient } from "@tanstack/react-query";
import { App, Button, Form, Input, Modal, Space, Switch } from "antd";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { getErrorMessage } from "../api/client";
import { environmentsApi } from "../api/environments";
import type { Environment, EnvironmentPayload } from "../api/types";
import { parseJsonObject, stringifyJson } from "../utils/json";

interface EnvironmentFormModalProps {
  open: boolean;
  projectId: string;
  environment?: Environment | null;
  onClose: () => void;
}

interface EnvironmentFormValues {
  name: string;
  base_url: string;
  headersText: string;
  variablesText: string;
  is_default: boolean;
}

export default function EnvironmentFormModal({
  open,
  projectId,
  environment,
  onClose,
}: EnvironmentFormModalProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<EnvironmentFormValues>();

  useEffect(() => {
    if (open) {
      reset({
        name: environment?.name ?? "",
        base_url: environment?.base_url ?? "",
        headersText: stringifyJson(environment?.headers, "{}"),
        variablesText: stringifyJson(environment?.variables, "{}"),
        is_default: environment?.is_default ?? false,
      });
    }
  }, [environment, open, reset]);

  const mutation = useMutation({
    mutationFn: (payload: EnvironmentPayload) =>
      environment
        ? environmentsApi.update(environment.id, payload)
        : environmentsApi.create(projectId, payload),
    onSuccess: () => {
      message.success(environment ? "环境已更新" : "环境已创建");
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "environments"] });
      onClose();
    },
    onError: (error) => message.error(getErrorMessage(error, "环境保存失败")),
  });

  const submit = (values: EnvironmentFormValues) => {
    let headers: Record<string, unknown> | null;
    let variables: Record<string, unknown> | null;
    try {
      headers = parseJsonObject(values.headersText, "公共 Headers");
    } catch (error) {
      setError("headersText", { message: getErrorMessage(error) });
      return;
    }
    try {
      variables = parseJsonObject(values.variablesText, "环境 Variables");
    } catch (error) {
      setError("variablesText", { message: getErrorMessage(error) });
      return;
    }
    mutation.mutate({
      name: values.name.trim(),
      base_url: values.base_url.trim(),
      headers,
      variables,
      is_default: values.is_default,
    });
  };

  return (
    <Modal
      title={environment ? "编辑环境" : "新建环境"}
      open={open}
      onCancel={onClose}
      footer={null}
      width={680}
      destroyOnClose
      maskClosable={!mutation.isPending}
    >
      <form onSubmit={handleSubmit(submit)}>
        <Form.Item label="环境名称" validateStatus={errors.name ? "error" : undefined} help={errors.name?.message}>
          <Input maxLength={50} placeholder="例如：staging" {...register("name", { required: "请输入环境名称" })} />
        </Form.Item>
        <Form.Item label="Base URL" validateStatus={errors.base_url ? "error" : undefined} help={errors.base_url?.message}>
          <Input placeholder="https://api-staging.example.com" {...register("base_url", { required: "请输入 Base URL", pattern: { value: /^https?:\/\//, message: "必须以 http:// 或 https:// 开头" } })} />
        </Form.Item>
        <Form.Item label="公共 Headers（JSON 对象）" validateStatus={errors.headersText ? "error" : undefined} help={errors.headersText?.message}>
          <Input.TextArea className="json-editor" rows={6} spellCheck={false} {...register("headersText")} />
        </Form.Item>
        <Form.Item label="环境 Variables（JSON 对象）" validateStatus={errors.variablesText ? "error" : undefined} help={errors.variablesText?.message ?? "变量可在 Path、Headers、Query、Body 和断言中引用。"}>
          <Input.TextArea className="json-editor" rows={6} spellCheck={false} {...register("variablesText")} />
        </Form.Item>
        <Form.Item label="默认环境">
          <Controller
            name="is_default"
            control={control}
            render={({ field }) => <Switch checked={field.value} onChange={field.onChange} checkedChildren="是" unCheckedChildren="否" />}
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
