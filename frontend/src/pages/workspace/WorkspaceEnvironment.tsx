import {
  CrownOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Drawer,
  Form,
  Input,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { environmentsApi } from "../../api/environments";
import { projectsApi } from "../../api/projects";
import { queryKeys } from "../../api/queryKeys";
import type { Environment, EnvironmentPayload } from "../../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { formatDateTime } from "../../utils/format";
import { parseJsonObject, stringifyJson } from "../../utils/json";

const DRAWER_WIDTH = 720;

interface EnvironmentFormValues {
  name: string;
  base_url: string;
  is_default: boolean;
  headersText: string;
  variablesText: string;
}

function defaultFormValues(env?: Environment | null): EnvironmentFormValues {
  return {
    name: env?.name ?? "",
    base_url: env?.base_url ?? "",
    is_default: env?.is_default ?? false,
    headersText: stringifyJson(env?.headers, "{}"),
    variablesText: stringifyJson(env?.variables, "{}"),
  };
}

export default function WorkspaceEnvironmentPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const { projectId = "" } = useParams();
  const { refresh: refreshWorkspace } = useProjectWorkspace();
  const [search, setSearch] = useState("");
  const [committedSearch, setCommittedSearch] = useState("");
  const [editing, setEditing] = useState<Environment | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("basic");
  const [headersError, setHeadersError] = useState<string | null>(null);
  const [variablesError, setVariablesError] = useState<string | null>(null);
  const [form] = Form.useForm<EnvironmentFormValues>();

  const projectQuery = useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => projectsApi.get(projectId),
    enabled: Boolean(projectId),
  });
  const environmentsQuery = useQuery({
    queryKey: queryKeys.environments(projectId, committedSearch),
    queryFn: () => environmentsApi.list(projectId, committedSearch),
    enabled: Boolean(projectId),
  });

  const environments = environmentsQuery.data?.items ?? [];
  const defaultEnvironment = environments.find((env) => env.is_default) ?? null;
  const projectName = projectQuery.data?.name ?? "项目";

  const refreshEnvironments = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.environments(projectId, "") });
  };
  const refreshAll = () => {
    refreshEnvironments();
    refreshWorkspace();
  };

  const defaultMutation = useMutation({
    mutationFn: environmentsApi.setDefault,
    onSuccess: () => {
      message.success("默认环境已切换");
      refreshAll();
    },
    onError: (error) => message.error(getErrorMessage(error, "设置默认环境失败")),
  });

  const deleteMutation = useMutation({
    mutationFn: environmentsApi.remove,
    onSuccess: () => {
      message.success("环境已删除");
      refreshAll();
    },
    onError: (error) => message.error(getErrorMessage(error, "环境删除失败")),
  });

  const saveMutation = useMutation({
    mutationFn: (payload: EnvironmentPayload) =>
      editing
        ? environmentsApi.update(editing.id, payload)
        : environmentsApi.create(projectId, payload),
    onSuccess: () => {
      message.success(editing ? "环境已更新" : "环境已创建");
      refreshAll();
      setDrawerOpen(false);
    },
    onError: (error) => message.error(getErrorMessage(error, "环境保存失败")),
  });

  const openCreate = () => {
    setEditing(null);
    setActiveTab("basic");
    setHeadersError(null);
    setVariablesError(null);
    form.resetFields();
    form.setFieldsValue(defaultFormValues(null));
    setDrawerOpen(true);
  };

  const openEdit = (env: Environment) => {
    setEditing(env);
    setActiveTab("basic");
    setHeadersError(null);
    setVariablesError(null);
    form.resetFields();
    form.setFieldsValue(defaultFormValues(env));
    setDrawerOpen(true);
  };

  const openEditAtTab = (env: Environment, tab: "headers" | "variables") => {
    openEdit(env);
    setActiveTab(tab);
  };

  const closeDrawer = () => {
    if (saveMutation.isPending) return;
    setDrawerOpen(false);
  };

  const validateJson = (value: string, fieldLabel: string): Record<string, unknown> | null => {
    try {
      return parseJsonObject(value, fieldLabel);
    } catch (error) {
      message.error(getErrorMessage(error, `${fieldLabel} 校验失败`));
      return null;
    }
  };

  const handleSubmit = async () => {
    try {
      const raw = await form.validateFields();
      const headers = validateJson(raw.headersText, "Headers");
      if (headers === null) {
        setActiveTab("headers");
        setHeadersError("Headers 必须是合法 JSON 对象");
        return;
      }
      const variables = validateJson(raw.variablesText, "Variables");
      if (variables === null) {
        setActiveTab("variables");
        setVariablesError("Variables 必须是合法 JSON 对象");
        return;
      }
      saveMutation.mutate({
        name: raw.name.trim(),
        base_url: raw.base_url.trim(),
        is_default: raw.is_default,
        headers,
        variables,
      });
    } catch {
      // Form validation already surfaces errors.
    }
  };

  useEffect(() => {
    if (editing) {
      setHeadersError(null);
      setVariablesError(null);
    }
  }, [editing]);

  const runCount = (value: Environment["headers"]) =>
    Object.keys(value ?? {}).length;

  return (
    <>
      <PageHeader
        title="环境"
        description={`管理 ${projectName} 的执行环境，包括 Base URL、公共 Headers 与 Variables；每个项目最多一个默认环境。`}
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: projectName, href: `/projects/${projectId}/workspace/overview` },
          { title: "环境" },
        ]}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建环境
          </Button>
        }
      />
      <Card className="surface-card">
        <div className="toolbar">
          <div className="toolbar-left">
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="按环境名称搜索"
              style={{ width: 320 }}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onPressEnter={() => setCommittedSearch(search.trim())}
              onClear={() => {
                setSearch("");
                setCommittedSearch("");
              }}
            />
            <Button onClick={() => setCommittedSearch(search.trim())}>搜索</Button>
          </div>
          <Typography.Text type="secondary">
            共 {environmentsQuery.data?.total ?? 0} 个环境
            {defaultEnvironment ? `，默认：${defaultEnvironment.name}` : "，尚未设置默认环境"}
          </Typography.Text>
        </div>
        {environmentsQuery.isError ? (
          <ErrorState
            error={environmentsQuery.error}
            onRetry={() => void environmentsQuery.refetch()}
          />
        ) : (
          <Table<Environment>
            rowKey="id"
            loading={environmentsQuery.isLoading}
            dataSource={environments}
            pagination={false}
            scroll={{ x: "max-content" }}
            locale={{
              emptyText: (
                <EmptyState
                  title={committedSearch ? "未找到匹配环境" : "尚未配置环境"}
                  description={committedSearch ? undefined : "创建环境后才能发起 API 执行。"}
                  action={
                    !committedSearch ? (
                      <Button type="primary" onClick={openCreate}>
                        新建环境
                      </Button>
                    ) : undefined
                  }
                />
              ),
            }}
            columns={[
              {
                title: "环境名称",
                dataIndex: "name",
                render: (name: string, env) => (
                  <Space>
                    <Typography.Text strong>{name}</Typography.Text>
                    {env.is_default ? (
                      <Tag color="blue" icon={<CrownOutlined />}>
                        默认
                      </Tag>
                    ) : null}
                  </Space>
                ),
              },
              {
                title: "Base URL",
                dataIndex: "base_url",
                ellipsis: true,
                render: (value: string) => (
                  <Tooltip title={value}>
                    <Typography.Text code>{value}</Typography.Text>
                  </Tooltip>
                ),
              },
              {
                title: "Headers",
                dataIndex: "headers",
                width: 100,
                render: (_value, env) => (
                  <Button type="link" size="small" onClick={() => openEditAtTab(env, "headers")}>
                    {runCount(env.headers)} 项
                  </Button>
                ),
              },
              {
                title: "Variables",
                dataIndex: "variables",
                width: 110,
                render: (_value, env) => (
                  <Button type="link" size="small" onClick={() => openEditAtTab(env, "variables")}>
                    {runCount(env.variables)} 项
                  </Button>
                ),
              },
              { title: "更新时间", dataIndex: "updated_at", width: 190, render: formatDateTime },
              {
                title: "操作",
                key: "actions",
                width: 280,
                render: (_, environment) => (
                  <Space size={4}>
                    {!environment.is_default ? (
                      <Button
                        type="link"
                        icon={<CrownOutlined />}
                        loading={
                          defaultMutation.isPending &&
                          defaultMutation.variables === environment.id
                        }
                        onClick={() => defaultMutation.mutate(environment.id)}
                      >
                        设为默认
                      </Button>
                    ) : null}
                    <Button
                      type="link"
                      icon={<EditOutlined />}
                      onClick={() => openEdit(environment)}
                    >
                      编辑
                    </Button>
                    {environment.is_default ? (
                      <Tooltip title="默认环境不可删除，请先将另一个环境设为默认">
                        <Button type="link" danger disabled icon={<DeleteOutlined />}>
                          删除
                        </Button>
                      </Tooltip>
                    ) : (
                      <Popconfirm
                        title="删除环境"
                        description={`确认删除“${environment.name}”？历史报告不会被修改。`}
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{
                          danger: true,
                          loading:
                            deleteMutation.isPending &&
                            deleteMutation.variables === environment.id,
                        }}
                        onConfirm={() => deleteMutation.mutate(environment.id)}
                      >
                        <Button type="link" danger icon={<DeleteOutlined />}>
                          删除
                        </Button>
                      </Popconfirm>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Card>

      <Drawer
        title={editing ? `编辑环境：${editing.name}` : "新建环境"}
        width={DRAWER_WIDTH}
        open={drawerOpen}
        onClose={closeDrawer}
        maskClosable={!saveMutation.isPending}
        destroyOnClose
        extra={
          <Space>
            <Button onClick={closeDrawer} disabled={saveMutation.isPending}>
              取消
            </Button>
            <Button
              type="primary"
              loading={saveMutation.isPending}
              onClick={handleSubmit}
            >
              保存
            </Button>
          </Space>
        }
      >
        {drawerOpen ? (
          <Form
            form={form}
            layout="vertical"
            initialValues={defaultFormValues(editing)}
            preserve={false}
          >
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                {
                  key: "basic",
                  label: "基本",
                  children: (
                    <Form.Item
                      label="环境名称"
                      name="name"
                      rules={[
                        { required: true, message: "请输入环境名称" },
                        { max: 50, message: "名称最多 50 字" },
                      ]}
                    >
                      <Input maxLength={50} placeholder="例如：staging" showCount />
                    </Form.Item>
                  ),
                },
                {
                  key: "url",
                  label: "Base URL",
                  children: (
                    <Form.Item
                      label="Base URL"
                      name="base_url"
                      rules={[
                        { required: true, message: "请输入 Base URL" },
                        {
                          pattern: /^https?:\/\//,
                          message: "必须以 http:// 或 https:// 开头",
                        },
                      ]}
                      extra="执行时 Run 会把 Case 的 path 拼接到此处。"
                    >
                      <Input placeholder="https://api-staging.example.com" />
                    </Form.Item>
                  ),
                },
                {
                  key: "default",
                  label: "默认环境",
                  children: (
                    <Form.Item
                      label="默认环境"
                      name="is_default"
                      valuePropName="checked"
                      extra="每个 Project 最多一个默认环境；设为默认会自动取消其他默认设置。"
                    >
                      <Switch />
                    </Form.Item>
                  ),
                },
                {
                  key: "headers",
                  label: "Headers",
                  children: (
                    <Form.Item
                      label="公共 Headers（JSON 对象）"
                      help={headersError ?? "键值均为字符串。"}
                      validateStatus={headersError ? "error" : undefined}
                    >
                      <Form.Item name="headersText" noStyle>
                        <Input.TextArea
                          className="json-editor"
                          rows={10}
                          spellCheck={false}
                          onChange={() => setHeadersError(null)}
                        />
                      </Form.Item>
                    </Form.Item>
                  ),
                },
                {
                  key: "variables",
                  label: "Variables",
                  children: (
                    <Form.Item
                      label="环境 Variables（JSON 对象）"
                      help={variablesError ?? "Case 路径 / Body / Headers 可使用 {{var}} 引用。"}
                      validateStatus={variablesError ? "error" : undefined}
                    >
                      <Form.Item name="variablesText" noStyle>
                        <Input.TextArea
                          className="json-editor"
                          rows={10}
                          spellCheck={false}
                          onChange={() => setVariablesError(null)}
                        />
                      </Form.Item>
                    </Form.Item>
                  ),
                },
              ]}
            />
            {saveMutation.isError ? (
              <Alert
                className="inline-warning"
                type="error"
                showIcon
                message="保存失败"
                description={getErrorMessage(saveMutation.error, "环境保存失败")}
              />
            ) : null}
          </Form>
        ) : (
          <LoadingBlock rows={6} />
        )}
      </Drawer>
    </>
  );
}
