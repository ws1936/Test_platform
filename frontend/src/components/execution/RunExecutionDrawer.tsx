import { PlayCircleOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Drawer,
  Empty,
  Form,
  Input,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { environmentsApi } from "../../api/environments";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import type {
  Environment,
  RunScope,
  TestCase,
  TestRun,
  TestRunPayload,
} from "../../api/types";
import { stringifyJson } from "../../utils/json";

const { Text } = Typography;

export type RunExecutionSource =
  | { kind: "project" }
  | { kind: "suite"; suiteId: string; suiteName?: string }
  | { kind: "case"; caseItem: TestCase };

export interface RunExecutionDrawerProps {
  open: boolean;
  source: RunExecutionSource | null;
  projectId: string;
  environments: Environment[];
  defaultEnvironmentId: string | null;
  enabledCaseCount: number;
  onClose: () => void;
}

interface RunExecutionValues {
  environment_id: string;
  name: string;
  variablesText: string;
}

const DRAWER_WIDTH = 720;

export default function RunExecutionDrawer({
  open,
  source,
  projectId,
  environments,
  defaultEnvironmentId,
  enabledCaseCount,
  onClose,
}: RunExecutionDrawerProps) {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [form] = Form.useForm<RunExecutionValues>();
  const [phase, setPhase] = useState<"configuring" | "submitting">("configuring");
  const [error, setError] = useState<string | null>(null);

  const sourceScope: RunScope | null = useMemo(() => {
    if (!source) return null;
    if (source.kind === "project") return "project";
    if (source.kind === "suite") return "collection";
    return "case";
  }, [source]);
  const sourceScopeId = useMemo(() => {
    if (!source) return "";
    if (source.kind === "project") return projectId;
    if (source.kind === "suite") return source.suiteId;
    return source.caseItem.id;
  }, [projectId, source]);
  const scopeTitle = useMemo(() => {
    if (!source) return "";
    if (source.kind === "project") return "整个 Project";
    if (source.kind === "suite") return `Suite：${source.suiteName ?? "未命名"}`;
    return `Case：${source.caseItem.name}`;
  }, [source]);

  const watchEnvironment = Form.useWatch("environment_id", form);

  const selectedEnv = useMemo(
    () => environments.find((item) => watchEnvironment === item.id),
    [environments, watchEnvironment],
  );

  const environmentsList = useQuery({
    queryKey: queryKeys.environments(projectId, ""),
    queryFn: () => environmentsApi.list(projectId),
    enabled: Boolean(projectId && open),
  });

  useEffect(() => {
    if (open) {
      const env = defaultEnvironmentId ?? environments[0]?.id ?? "";
      const envRecord = environments.find((item) => item.id === env);
      form.setFieldsValue({
        environment_id: env,
        name: "",
        variablesText: stringifyJson(envRecord?.variables, "{}"),
      });
      setError(null);
      setPhase("configuring");
    }
  }, [defaultEnvironmentId, environments, form, open]);

  useEffect(() => {
    if (watchEnvironment) {
      const env = environments.find((item) => item.id === watchEnvironment);
      form.setFieldsValue({ variablesText: stringifyJson(env?.variables, "{}") });
    }
  }, [watchEnvironment, environments, form]);

  const canRun = useMemo(() => {
    if (!source || !sourceScope || !sourceScopeId) return false;
    if (!selectedEnv) return false;
    if (source.kind === "project" && enabledCaseCount === 0) return false;
    if (source.kind === "suite" && enabledCaseCount === 0) return false;
    if (source.kind === "case" && !source.caseItem.enabled) return false;
    return true;
  }, [enabledCaseCount, selectedEnv, source, sourceScope, sourceScopeId]);

  const runMutation = useMutation({
    mutationFn: (values: RunExecutionValues) => {
      const payload: TestRunPayload = {
        name: values.name?.trim() || undefined,
        environment_id: values.environment_id,
        scope: sourceScope!,
        scope_id: sourceScopeId,
      };
      if (source?.kind === "case") {
        return runsApi.runCase(source.caseItem.id, values.environment_id, payload.name);
      }
      return runsApi.create(projectId, payload);
    },
    onSuccess: (run: TestRun) => {
      message.success("执行完成，正在打开报告");
      onClose();
      navigate(`/projects/${projectId}/workspace/report/${run.id}`);
    },
    onError: (err) => {
      setPhase("configuring");
      setError(getErrorMessage(err, "执行失败"));
    },
  });

  const handleSubmit = async () => {
    try {
      const values = (await form.validateFields()) as RunExecutionValues;
      if (!source || !sourceScope || !sourceScopeId) {
        message.error("执行范围不合法");
        return;
      }
      setError(null);
      setPhase("submitting");
      runMutation.mutate(values);
    } catch {
      // Form validation has surfaced errors.
    }
  };

  const closeDrawer = () => {
    if (phase === "submitting") return;
    onClose();
  };

  return (
    <Drawer
      title={
        <Space>
          <PlayCircleOutlined />
          {sourceScope === "project" && "执行 Project"}
          {sourceScope === "collection" && "执行 Suite"}
          {sourceScope === "case" && "执行 Case"}
        </Space>
      }
      width={DRAWER_WIDTH}
      open={open}
      onClose={closeDrawer}
      maskClosable={phase !== "submitting"}
      destroyOnClose
      extra={
        <Space>
          <Button onClick={closeDrawer} disabled={phase === "submitting"}>
            取消
          </Button>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={phase === "submitting"}
            disabled={!canRun || phase === "submitting"}
            onClick={handleSubmit}
          >
            {phase === "submitting" ? "正在同步执行…" : "Run Now"}
          </Button>
        </Space>
      }
    >
      {!open ? null : (
        <Space direction="vertical" size={20} style={{ width: "100%" }}>
          <Space size={8} wrap>
            <Tag color="blue">范围：{scopeTitle}</Tag>
            {selectedEnv ? (
              <Tag color="cyan">环境：{selectedEnv.name}</Tag>
            ) : (
              <Tag color="orange">未选择环境</Tag>
            )}
            {source?.kind === "project" || source?.kind === "suite" ? (
              <Tag color="purple">范围内启用 Case：{enabledCaseCount}</Tag>
            ) : null}
          </Space>

          {!defaultEnvironmentId && (
            <Alert
              type="warning"
              showIcon
              message="尚未设置默认环境"
              description="Project Run 之前必须先设置默认环境。"
              action={
                <Button
                  size="small"
                  onClick={() => navigate(`/projects/${projectId}/workspace/environment`)}
                >
                  前往 Environment
                </Button>
              }
            />
          )}

          {environmentsList.isError ? (
            <Alert
              type="error"
              showIcon
              message="环境列表加载失败"
              description={getErrorMessage(environmentsList.error, "无法加载环境")}
            />
          ) : null}

          {source?.kind === "project" && enabledCaseCount === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="当前 Project 没有启用的 Case，无法执行 Project Run。"
            />
          ) : null}
          {source?.kind === "suite" && enabledCaseCount === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="当前 Suite 内没有启用的 Case。"
            />
          ) : null}
          {source?.kind === "case" && !source.caseItem.enabled ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="该 Case 已禁用，无法执行。"
            />
          ) : null}

          <Form<RunExecutionValues>
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{
              environment_id: defaultEnvironmentId ?? environments[0]?.id ?? "",
              name: "",
              variablesText: "{}",
            }}
          >
            <Form.Item
              label="Environment"
              name="environment_id"
              rules={[{ required: true, message: "请选择执行环境" }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                loading={environmentsList.isLoading}
                placeholder="选择环境"
                disabled={phase === "submitting"}
                options={environments.map((env) => ({
                  value: env.id,
                  label: env.is_default
                    ? `${env.name}（默认）`
                    : env.name,
                }))}
              />
            </Form.Item>

            <Form.Item
              label="Run Name"
              name="name"
              extra="可选；留空时由后端自动生成。"
            >
              <Input
                maxLength={200}
                placeholder="例如：用户服务回归测试"
                disabled={phase === "submitting"}
              />
            </Form.Item>

            <Form.Item
              label="Variables（仅展示）"
              name="variablesText"
              tooltip="后端执行时使用 Environment 自身的 Variables；此处只读显示，不可直接覆盖。"
            >
              <Input.TextArea
                rows={8}
                spellCheck={false}
                readOnly
                className="json-editor"
                placeholder="{}"
              />
            </Form.Item>
          </Form>

          {phase === "submitting" ? (
            <Alert
              type="info"
              showIcon
              message="正在同步执行"
              description="后端为同步执行；请勿关闭或重复提交。"
            />
          ) : null}

          {error ? (
            <Alert
              className="inline-warning"
              type="error"
              showIcon
              message="执行失败"
              description={error}
            />
          ) : null}

          {phase === "submitting" ? (
            <Space align="center" style={{ justifyContent: "center", width: "100%" }}>
              <Spin />
              <Text type="secondary">同步执行中，完成后会自动跳 Report</Text>
            </Space>
          ) : null}
        </Space>
      )}
    </Drawer>
  );
}
