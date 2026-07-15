import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  DeleteOutlined,
  EditOutlined,
  ImportOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  SelectOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Descriptions,
  Empty,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { suitesApi } from "../../api/suites";
import { testCasesApi } from "../../api/testCases";
import { queryKeys } from "../../api/queryKeys";
import type { SuiteCaseLink, TestCase } from "../../api/types";
import { ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { MethodTag } from "../../components/StatusTags";
import SuiteFormModal from "../../components/SuiteFormModal";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { formatDateTime } from "../../utils/format";

const { Text } = Typography;

export default function WorkspaceSuiteDetailPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId = "", suiteId = "" } = useParams();
  const { refresh: refreshWorkspace } = useProjectWorkspace();
  const [editOpen, setEditOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [pendingCaseIds, setPendingCaseIds] = useState<string[]>([]);

  const suiteQuery = useQuery({
    queryKey: queryKeys.suite(projectId, suiteId),
    queryFn: () => suitesApi.get(projectId, suiteId),
    enabled: Boolean(projectId && suiteId),
  });
  const suiteCasesQuery = useQuery({
    queryKey: queryKeys.suiteCases(suiteId),
    queryFn: () => suitesApi.listCases(suiteId),
    enabled: Boolean(suiteId),
  });
  const projectCasesQuery = useQuery({
    queryKey: queryKeys.cases(projectId, ""),
    queryFn: () => testCasesApi.listProject(projectId),
    enabled: Boolean(projectId && addOpen),
  });

  const caseMap = useMemo(() => {
    const map = new Map<string, TestCase>();
    projectCasesQuery.data?.items.forEach((item) => map.set(item.id, item));
    return map;
  }, [projectCasesQuery.data?.items]);

  const linkedCaseIds = useMemo(
    () =>
      new Set(
        ((suiteCasesQuery.data as SuiteCaseLink[] | undefined) ?? []).map(
          (item) => item.case_id,
        ),
      ),
    [suiteCasesQuery.data],
  );
  const availableCases = useMemo(
    () => (projectCasesQuery.data?.items ?? []).filter((item) => !linkedCaseIds.has(item.id)),
    [linkedCaseIds, projectCasesQuery.data?.items],
  );

  const refreshAll = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.suite(projectId, suiteId) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.suiteCases(suiteId) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, "") });
    void queryClient.invalidateQueries({ queryKey: queryKeys.suites(projectId, "") });
    refreshWorkspace();
  };

  const removeMutation = useMutation({
    mutationFn: (caseId: string) => suitesApi.removeCase(projectId, suiteId, caseId),
    onSuccess: () => {
      message.success("已从 Suite 移除");
      refreshAll();
    },
    onError: (error) => message.error(getErrorMessage(error, "移除失败")),
  });
  const addMutation = useMutation({
    mutationFn: (caseIds: string[]) => suitesApi.addCases(projectId, suiteId, caseIds),
    onSuccess: () => {
      message.success("已添加");
      setAddOpen(false);
      setPendingCaseIds([]);
      refreshAll();
    },
    onError: (error) => message.error(getErrorMessage(error, "添加失败")),
  });
  const reorderMutation = useMutation({
    mutationFn: (caseIds: string[]) => suitesApi.reorderCases(projectId, suiteId, caseIds),
    onSuccess: () => {
      refreshAll();
    },
    onError: (error) => message.error(getErrorMessage(error, "顺序更新失败")),
  });
  const deleteSuiteMutation = useMutation({
    mutationFn: () => suitesApi.remove(projectId, suiteId),
    onSuccess: () => {
      message.success("Suite 已删除");
      navigate(`/projects/${projectId}/workspace/suite`);
    },
    onError: (error) => message.error(getErrorMessage(error, "Suite 删除失败")),
  });

  const suite = suiteQuery.data ?? null;
  const linked: SuiteCaseLink[] = (suiteCasesQuery.data as SuiteCaseLink[] | undefined) ?? [];

  const moveCase = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= linked.length) return;
    const ids = linked.map((item) => item.case_id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    reorderMutation.mutate(ids);
  };

  if (suiteQuery.isLoading) return <LoadingBlock rows={6} />;
  if (suiteQuery.isError) {
    return (
      <ErrorState
        error={suiteQuery.error}
        onRetry={() => void suiteQuery.refetch()}
        title="无法加载 Suite 详情"
      />
    );
  }
  if (!suite) {
    return <ErrorState error={new Error("Suite 不存在或已被删除")} />;
  }

  return (
    <>
      <PageHeader
        title={suite.name}
        description={suite.description || "暂无 Suite 描述"}
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "测试套件", href: `/projects/${projectId}/workspace/suite` },
          { title: suite.name },
        ]}
        extra={
          <Space wrap>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() =>
                navigate(`/projects/${projectId}/workspace/run?scope=collection&scopeId=${suiteId}`)
              }
            >
              执行 Suite
            </Button>
            <Button
              icon={<ImportOutlined />}
              onClick={() => navigate(`/projects/${projectId}/workspace/import/${suiteId}`)}
            >
              OpenAPI 导入
            </Button>
            <Button icon={<EditOutlined />} onClick={() => setEditOpen(true)}>编辑</Button>
            <Popconfirm
              title="删除测试套件"
              description="只删除 Suite 及关联关系，不删除 API 用例本体。"
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true, loading: deleteSuiteMutation.isPending }}
              onConfirm={() => deleteSuiteMutation.mutate()}
            >
              <Button danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          </Space>
        }
      />
      <Card className="surface-card">
        <Tabs
          defaultActiveKey="cases"
          items={[
            {
              key: "cases",
              label: "已关联 Case",
              children: (
                <SuiteCaseList
                  projectId={projectId}
                  suiteId={suiteId}
                  linked={linked}
                  caseMap={caseMap}
                  loading={suiteCasesQuery.isLoading || reorderMutation.isPending}
                  error={suiteCasesQuery.isError ? suiteCasesQuery.error : undefined}
                  onAdd={() => {
                    setPendingCaseIds([]);
                    setAddOpen(true);
                  }}
                  onMove={moveCase}
                  onRemove={(caseId) => removeMutation.mutate(caseId)}
                  removingId={removeMutation.isPending ? removeMutation.variables : null}
                  onRetry={() => void suiteCasesQuery.refetch()}
                  navigateToCase={(caseId) =>
                    navigate(`/projects/${projectId}/workspace/case/${caseId}?from=suite&suiteId=${suiteId}`)
                  }
                />
              ),
            },
            {
              key: "info",
              label: "Suite 信息",
              children: (
                <Descriptions
                  bordered
                  column={{ xs: 1, md: 2 }}
                  items={[
                    { key: "id", label: "Suite ID", children: <Text code>{suite.id}</Text> },
                    { key: "project", label: "Project ID", children: <Text code>{suite.project_id}</Text> },
                    { key: "name", label: "名称", children: suite.name },
                    { key: "description", label: "描述", children: suite.description || "暂无描述" },
                    { key: "order", label: "排序", children: suite.sort_order },
                    { key: "created", label: "创建时间", children: formatDateTime(suite.created_at) },
                    { key: "updated", label: "更新时间", children: formatDateTime(suite.updated_at) },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={`向 ${suite.name} 添加 Case`}
        open={addOpen}
        onCancel={() => {
          if (addMutation.isPending) return;
          setAddOpen(false);
          setPendingCaseIds([]);
        }}
        onOk={() => {
          if (pendingCaseIds.length === 0) {
            message.warning("请先选择至少一个 Case");
            return;
          }
          addMutation.mutate(pendingCaseIds);
        }}
        confirmLoading={addMutation.isPending}
        okText="添加"
        cancelText="取消"
        width={640}
        destroyOnClose
      >
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          <Typography.Text type="secondary">
            仅显示未关联到本 Suite 的 Case；最多单次添加 200 条。
          </Typography.Text>
          <Select
            mode="multiple"
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="选择 API Case"
            style={{ width: "100%" }}
            loading={projectCasesQuery.isLoading}
            value={pendingCaseIds}
            onChange={setPendingCaseIds}
            options={availableCases.map((item) => ({
              value: item.id,
              label: `${item.method} ${item.name} · ${item.path}`,
            }))}
            maxTagCount="responsive"
            notFoundContent={
              projectCasesQuery.isLoading
                ? "加载中…"
                : availableCases.length === 0
                  ? "已无更多可添加的 Case"
                  : "无匹配结果"
            }
          />
          {projectCasesQuery.isError ? (
            <Alert
              type="error"
              showIcon
              message="加载项目 Case 失败"
              description={getErrorMessage(projectCasesQuery.error, "无法加载 Case 列表")}
            />
          ) : null}
        </Space>
      </Modal>

      <SuiteFormModal
        open={editOpen}
        projectId={projectId}
        suite={suite}
        onClose={() => setEditOpen(false)}
      />
    </>
  );

  interface SuiteCaseListProps {
    projectId: string;
    suiteId: string;
    linked: SuiteCaseLink[];
    caseMap: Map<string, TestCase>;
    loading: boolean;
    error: unknown;
    onAdd: () => void;
    onMove: (index: number, direction: -1 | 1) => void;
    onRemove: (caseId: string) => void;
    removingId: string | null;
    onRetry: () => void;
    navigateToCase: (caseId: string) => void;
  }
  function SuiteCaseList({
    linked,
    caseMap,
    loading,
    error,
    onAdd,
    onMove,
    onRemove,
    removingId,
    onRetry,
    navigateToCase,
  }: SuiteCaseListProps) {
    return (
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Space>
          <Button
            type="primary"
            icon={<SelectOutlined />}
            onClick={onAdd}
          >
            批量添加 Case
          </Button>
          <Button
            icon={<PlusOutlined />}
            onClick={() => navigate(`/projects/${projectId}/workspace/case/new?suiteId=${suiteId}`)}
          >
            新建 Case
          </Button>
        </Space>
        {error ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : linked.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" size={4}>
                <Text strong>当前 Suite 尚无 Case</Text>
                <Text type="secondary">可批量添加项目已有 Case，或新建 / 导入 Case。</Text>
                <Space>
                  <Button onClick={onAdd} type="primary">添加已有 Case</Button>
                  <Button onClick={() => navigate(`/projects/${projectId}/workspace/import/${suiteId}`)}>
                    OpenAPI 导入
                  </Button>
                </Space>
              </Space>
            }
          />
        ) : (
          <Table<SuiteCaseLink>
            rowKey="id"
            size="small"
            loading={loading}
            dataSource={linked}
            pagination={false}
            columns={[
              {
                title: "顺序",
                width: 110,
                render: (_, __, index) => (
                  <Space size={0}>
                    <Button
                      type="text"
                      size="small"
                      icon={<ArrowUpOutlined />}
                      disabled={index === 0 || loading}
                      onClick={() => onMove(index, -1)}
                    />
                    <Button
                      type="text"
                      size="small"
                      icon={<ArrowDownOutlined />}
                      disabled={index === linked.length - 1 || loading}
                      onClick={() => onMove(index, 1)}
                    />
                  </Space>
                ),
              },
              {
                title: "Method",
                width: 90,
                render: (_, row) => {
                  const item = caseMap.get(row.test_case_id);
                  return item ? <MethodTag method={item.method} /> : <Tag>未知</Tag>;
                },
              },
              {
                title: "Case 名称",
                render: (_, row) => {
                  const item = caseMap.get(row.test_case_id);
                  return (
                    <Button type="link" onClick={() => navigateToCase(row.test_case_id)}>
                      {item?.name ?? row.test_case_id}
                    </Button>
                  );
                },
              },
              {
                title: "Path",
                ellipsis: true,
                render: (_, row) => {
                  const item = caseMap.get(row.test_case_id);
                  return (
                    <Tooltip title={item?.path ?? ""}>
                      <span className="code-path">{item?.path ?? "—"}</span>
                    </Tooltip>
                  );
                },
              },
              {
                title: "启用",
                width: 80,
                render: (_, row) => {
                  const item = caseMap.get(row.test_case_id);
                  return <Switch size="small" checked={item?.enabled ?? false} disabled />;
                },
              },
              {
                title: "操作",
                width: 110,
                render: (_, row) => (
                  <Popconfirm
                    title="从 Suite 移除"
                    description="只移除关联，不会删除 API 用例本身。"
                    okText="移除"
                    cancelText="取消"
                    okButtonProps={{
                      danger: true,
                      loading: removingId === row.test_case_id,
                    }}
                    onConfirm={() => onRemove(row.test_case_id)}
                  >
                    <Button type="link" danger>移除</Button>
                  </Popconfirm>
                ),
              },
            ]}
          />
        )}
      </Space>
    );
  }
}
