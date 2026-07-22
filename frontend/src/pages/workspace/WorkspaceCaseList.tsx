import {
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { environmentsApi } from "../../api/environments";
import { runsApi } from "../../api/runs";
import { suitesApi } from "../../api/suites";
import { testCasesApi } from "../../api/testCases";
import { queryKeys } from "../../api/queryKeys";
import type { TestCase, TestRun } from "../../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { MethodTag } from "../../components/StatusTags";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { formatDateTime } from "../../utils/format";

/**
 * Workspace Case List — 当前 Project 全部 Test Case 列表。
 *
 * 设计要点：
 * 1. 数据源 = testCasesApi.listProject(projectId)（F007 项目级列表）
 * 2. 启用 / 禁用 Switch 走 testCasesApi.update（仅传 enabled 字段）
 * 3. 删除走 testCasesApi.remove（后端级联清理 suite_cases 关联）
 * 4. 列表项支持跳转编辑器 + 单用例运行（需先有默认环境）
 * 5. 新建 Case 必须指定 Suite（F007 设计：case 必有归属 suite）
 */
export default function WorkspaceCaseListPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId = "" } = useParams();
  const { refresh: refreshWorkspace } = useProjectWorkspace();
  const [search, setSearch] = useState("");
  const [committedSearch, setCommittedSearch] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [pendingSuiteId, setPendingSuiteId] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const justCreated = searchParams.get("justCreated") === "1";

  // 列表数据
  const casesQuery = useQuery({
    queryKey: queryKeys.cases(projectId, committedSearch),
    queryFn: () => testCasesApi.listProject(projectId, committedSearch),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });
  // 稳定引用：避免每个 render 都重建数组（影响下游 useMemo deps）
  const cases = useMemo<TestCase[]>(
    () => casesQuery.data?.items ?? [],
    [casesQuery.data?.items],
  );
  const casesTotal = casesQuery.data?.total ?? 0;

  // 套件列表（用于"新建 Case"选择 Suite + 跳到编辑器时附带 suiteId）
  const suitesQuery = useQuery({
    queryKey: queryKeys.suites(projectId, ""),
    queryFn: () => suitesApi.list(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });
  const suites = useMemo(
    () => suitesQuery.data?.items ?? [],
    [suitesQuery.data?.items],
  );

  // 环境列表（用于单用例执行弹窗）
  const environmentsQuery = useQuery({
    queryKey: queryKeys.environments(projectId, ""),
    queryFn: () => environmentsApi.list(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });
  const environments = useMemo(
    () => environmentsQuery.data?.items ?? [],
    [environmentsQuery.data?.items],
  );
  const defaultEnv = useMemo(
    () => environments.find((e) => e.is_default) ?? null,
    [environments],
  );

  // 启用 / 禁用切换
  const enabledMutation = useMutation({
    mutationFn: ({ caseId, enabled }: { caseId: string; enabled: boolean }) =>
      testCasesApi.update(caseId, { enabled }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, committedSearch) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, "") });
    },
    onError: (error, variables) => {
      message.error(getErrorMessage(error, `Case ${variables.enabled ? "启用" : "禁用"}失败`));
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, committedSearch) });
    },
  });

  // 删除
  const deleteMutation = useMutation({
    mutationFn: (caseId: string) => testCasesApi.remove(caseId),
    onSuccess: () => {
      message.success("Case 已删除");
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, "") });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, committedSearch) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.suites(projectId, "") });
      refreshWorkspace();
    },
    onError: (error) => message.error(getErrorMessage(error, "Case 删除失败")),
  });

  // 单用例运行
  const runMutation = useMutation({
    mutationFn: ({ caseId, envId }: { caseId: string; envId: string }) =>
      runsApi.runCase(caseId, envId),
    onSuccess: (run: TestRun) => {
      message.success("执行完成，跳转报告");
      void queryClient.invalidateQueries({ queryKey: queryKeys.runs(projectId, {}) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projectRunSummary(projectId) });
      navigate(`/projects/${projectId}/workspace/report/${run.id}`);
    },
    onError: (error) => message.error(getErrorMessage(error, "执行失败")),
  });

  const openCreate = () => {
    if (suites.length === 0) {
      message.warning("请先创建一个 Suite，再维护 Case。");
      navigate(`/projects/${projectId}/workspace/suite`);
      return;
    }
    setPendingSuiteId(null);
    setCreateModalOpen(true);
  };

  const confirmCreate = () => {
    if (!pendingSuiteId) {
      message.warning("请选择 Suite");
      return;
    }
    setCreateModalOpen(false);
    const next = new URLSearchParams();
    next.set("suiteId", pendingSuiteId);
    navigate(`/projects/${projectId}/workspace/case/new?${next.toString()}`);
  };

  const dismissJustCreated = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("justCreated");
    setSearchParams(next, { replace: true });
  };

  const clearSearch = () => {
    setSearch("");
    setCommittedSearch("");
  };

  const rowCount = cases.length;
  const enabledCount = useMemo(
    () => cases.filter((c) => c.enabled).length,
    [cases],
  );

  return (
    <>
      <PageHeader
        title="API 用例"
        description="管理当前 Project 的所有 API 用例；新建 / 编辑 / 启用 / 禁用 / 单用例执行。"
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "API 用例" },
        ]}
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={openCreate}
            >
              新建 Case
            </Button>
          </Space>
        }
      />

      {justCreated ? (
        <Alert
          className="inline-warning"
          type="success"
          showIcon
          message="Case 创建成功"
          description="你可以在列表中继续维护，或直接发起单用例执行。"
          closable
          onClose={dismissJustCreated}
          style={{ marginBottom: 16 }}
        />
      ) : null}

      <Card className="surface-card">
        <div className="toolbar">
          <div className="toolbar-left">
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="按 Case 名称搜索"
              style={{ width: 320 }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onPressEnter={() => setCommittedSearch(search.trim())}
              onClear={clearSearch}
            />
            <Button onClick={() => setCommittedSearch(search.trim())}>搜索</Button>
          </div>
          <Typography.Text type="secondary">
            共 {casesTotal ?? rowCount} 个 Case
            {rowCount > 0 ? ` · 启用 ${enabledCount}` : ""}
            {defaultEnv ? ` · 默认环境：${defaultEnv.name}` : ""}
          </Typography.Text>
        </div>

        {casesQuery.isError ? (
          <ErrorState
            error={casesQuery.error}
            onRetry={() => void casesQuery.refetch()}
          />
        ) : casesQuery.isLoading ? (
          <LoadingBlock rows={6} />
        ) : rowCount === 0 ? (
          <EmptyState
            title={committedSearch ? "未找到匹配 Case" : "尚未维护任何 Case"}
            description={
              committedSearch
                ? "调整搜索关键字后重试。"
                : "先在 Suite 页面创建 Suite，再回到这里维护 Case；或使用 OpenAPI 导入一键生成。"
            }
            action={
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={openCreate}
                >
                  新建 Case
                </Button>
                {suites.length > 0 ? null : (
                  <Button onClick={() => navigate(`/projects/${projectId}/workspace/suite`)}>
                    前往 Suite
                  </Button>
                )}
              </Space>
            }
          />
        ) : (
          <Table<TestCase>
            rowKey="id"
            dataSource={cases}
            pagination={false}
            columns={[
              {
                title: "Method",
                dataIndex: "method",
                width: 100,
                render: (method: TestCase["method"]) => <MethodTag method={method} />,
              },
              {
                title: "Case 名称",
                dataIndex: "name",
                render: (name: string, row) => (
                  <Button
                    type="link"
                    className="table-link"
                    onClick={() =>
                      navigate(`/projects/${projectId}/workspace/case/${row.id}`)
                    }
                  >
                    {name}
                  </Button>
                ),
              },
              {
                title: "Path",
                dataIndex: "path",
                ellipsis: true,
                render: (value: string) => (
                  <Tooltip title={value}>
                    <span className="code-path">{value}</span>
                  </Tooltip>
                ),
              },
              {
                title: "Body",
                dataIndex: "body_type",
                width: 90,
                render: (value: string) =>
                  value && value !== "none" ? (
                    <Tag color="geekblue">{value}</Tag>
                  ) : (
                    <Typography.Text type="secondary">—</Typography.Text>
                  ),
              },
              {
                title: "断言",
                dataIndex: "assertions",
                width: 80,
                render: (assertions: TestCase["assertions"]) => {
                  const count = Array.isArray(assertions) ? assertions.length : 0;
                  return count > 0 ? (
                    <Tag color="purple">{count} 条</Tag>
                  ) : (
                    <Typography.Text type="secondary">无</Typography.Text>
                  );
                },
              },
              {
                title: "超时",
                dataIndex: "timeout_seconds",
                width: 80,
                render: (value: number) => `${value ?? 30}s`,
              },
              {
                title: "启用",
                dataIndex: "enabled",
                width: 80,
                render: (enabled: boolean, row) => (
                  <Switch
                    size="small"
                    checked={Boolean(enabled)}
                    loading={
                      enabledMutation.isPending &&
                      enabledMutation.variables?.caseId === row.id
                    }
                    onChange={(checked) =>
                      enabledMutation.mutate({ caseId: row.id, enabled: checked })
                    }
                  />
                ),
              },
              {
                title: "更新时间",
                dataIndex: "updated_at",
                width: 170,
                render: formatDateTime,
              },
              {
                title: "操作",
                key: "actions",
                width: 200,
                render: (_, row) => (
                  <Space size={0}>
                    <Tooltip title={defaultEnv ? `用 ${defaultEnv.name} 跑` : "需先设置默认环境"}>
                      <Button
                        type="link"
                        icon={<PlayCircleOutlined />}
                        disabled={!defaultEnv || runMutation.isPending}
                        loading={
                          runMutation.isPending &&
                          runMutation.variables?.caseId === row.id
                        }
                        onClick={() =>
                          defaultEnv &&
                          runMutation.mutate({
                            caseId: row.id,
                            envId: defaultEnv.id,
                          })
                        }
                      >
                        运行
                      </Button>
                    </Tooltip>
                    <Button
                      type="link"
                      icon={<EditOutlined />}
                      onClick={() =>
                        navigate(`/projects/${projectId}/workspace/case/${row.id}`)
                      }
                    >
                      编辑
                    </Button>
                    <Popconfirm
                      title="删除 Case"
                      description="将级联清理 Suite 关联；Case 本身会被永久删除。"
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{
                        danger: true,
                        loading:
                          deleteMutation.isPending &&
                          deleteMutation.variables === row.id,
                      }}
                      onConfirm={() => deleteMutation.mutate(row.id)}
                    >
                      <Button type="link" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Card>

      <Modal
        title="新建 Case — 选择所属 Suite"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={confirmCreate}
        okText="下一步"
        cancelText="取消"
        okButtonProps={{ disabled: !pendingSuiteId }}
        destroyOnClose
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Typography.Text type="secondary">
            每个 Case 必须归属一个 Suite。请选择目标 Suite。
          </Typography.Text>
          <Select
            placeholder="选择 Suite"
            style={{ width: "100%" }}
            value={pendingSuiteId ?? undefined}
            onChange={(value: string) => setPendingSuiteId(value)}
            options={suites.map((s) => ({
              value: s.id,
              label: `${s.name}${s.description ? ` · ${s.description}` : ""}`,
            }))}
            showSearch
            optionFilterProp="label"
          />
        </Space>
      </Modal>
    </>
  );
}
