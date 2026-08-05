import {
  AppstoreOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  RocketOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Radio,
  Select,
  Slider,
  Space,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { environmentsApi } from "../../api/environments";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import { suitesApi } from "../../api/suites";
import { testCasesApi } from "../../api/testCases";
import type {
  RunScope,
  SuiteCaseLink,
  TestCase,
  TestRun,
} from "../../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { MethodTag } from "../../components/StatusTags";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";

// F014 客户端默认值 / 上限（与后端 settings.TEST_RUN_MAX_CONCURRENCY 同步）。
// 前后端任一改动需过 ADR；这里只承担"UI 默认值 / 上限"职责，
// 真正的并发度由后端 TestRunner 决定（服务侧兜底 max(1, raw)）。
const DEFAULT_CONCURRENCY = 4;
const MIN_CONCURRENCY = 1;
const MAX_CONCURRENCY = 64;

/**
 * Workspace Run Center — 手动发起执行。
 *
 * 三种 scope：
 * - project：执行当前项目所有启用的 Case
 * - collection：执行某个 Suite 下关联的 Case
 * - case：执行单个 Case
 *
 * 设计要点：
 * 1. 同步执行：submit 后端返回的是 finished 状态（已有 610s 超时）
 * 2. 提交前显示预期 Case 数（防止误发大型 Run）
 * 3. 默认环境优先选中；无默认环境时阻止执行（与后端语义一致）
 * 4. 支持 ?scope=...&scopeId=... 预填（Header 的"快速执行"按钮）
 * 5. F014：暴露 max_concurrency（1-64）供用户覆盖 server 默认
 */
export default function WorkspaceRunPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId = "" } = useParams();
  const { refresh: refreshWorkspace, defaultEnvironmentId } = useProjectWorkspace();
  const [searchParams] = useSearchParams();

  // 预填 scope/scopeId（来自 Header 快速执行按钮）
  const initialScope = (searchParams.get("scope") ?? "project") as RunScope;
  const initialScopeId = searchParams.get("scopeId") ?? null;

  const [scope, setScope] = useState<RunScope>(initialScope);
  const [scopeId, setScopeId] = useState<string | null>(initialScopeId);
  const [environmentId, setEnvironmentId] = useState<string | null>(
    defaultEnvironmentId,
  );
  const [runName, setRunName] = useState("");
  // F014：用户可在 UI 上覆盖单 Run 的并发度。默认值与后端 settings.TEST_RUN_MAX_CONCURRENCY 对齐。
  const [concurrency, setConcurrency] = useState<number>(DEFAULT_CONCURRENCY);

  // 同步默认环境
  useEffect(() => {
    if (!environmentId && defaultEnvironmentId) {
      setEnvironmentId(defaultEnvironmentId);
    }
  }, [defaultEnvironmentId, environmentId]);

  // 切换 scope 时清空 scopeId
  useEffect(() => {
    if (scope === "project") {
      setScopeId(null);
    }
  }, [scope]);

  // ===== 数据 =====
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

  const casesQuery = useQuery({
    queryKey: queryKeys.cases(projectId, ""),
    queryFn: () => testCasesApi.listProject(projectId, ""),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });
  const allCases = useMemo<TestCase[]>(
    () => casesQuery.data?.items ?? [],
    [casesQuery.data?.items],
  );

  // 选中 Suite 时获取其关联 Case
  const suiteCasesQuery = useQuery({
    queryKey: queryKeys.suiteCases(scopeId ?? ""),
    queryFn: () => suitesApi.listCases(scopeId as string),
    enabled: scope === "collection" && Boolean(scopeId),
    staleTime: 30_000,
  });
  const suiteLinkedCases = useMemo<SuiteCaseLink[]>(
    () => (suiteCasesQuery.data as SuiteCaseLink[] | undefined) ?? [],
    [suiteCasesQuery.data],
  );

  // ===== 预期执行 Case 列表（用于预演 + 计数） =====
  const expectedCases: TestCase[] = useMemo(() => {
    if (scope === "project") {
      return allCases.filter((c) => c.enabled);
    }
    if (scope === "collection") {
      const linkedIds = new Set(suiteLinkedCases.map((s) => s.test_case_id));
      return allCases.filter((c) => linkedIds.has(c.id) && c.enabled);
    }
    if (scope === "case" && scopeId) {
      return allCases.filter((c) => c.id === scopeId && c.enabled);
    }
    return [];
  }, [scope, scopeId, allCases, suiteLinkedCases]);

  // ===== 提交 =====
  const createRunMutation = useMutation({
    mutationFn: async () => {
      if (!environmentId) {
        throw new Error("请选择环境");
      }
      if (scope !== "project" && !scopeId) {
        throw new Error("请选择执行范围");
      }
      return runsApi.create(
        projectId,
        {
          name: runName.trim() || undefined,
          environment_id: environmentId,
          scope,
          scope_id: scopeId ?? projectId,
        },
        // F014：把 UI 上的 concurrency 透传到后端 query ?concurrency=
        { concurrency },
      );
    },
    onSuccess: (run: TestRun) => {
      message.success("执行完成，跳转报告");
      void queryClient.invalidateQueries({ queryKey: queryKeys.runs(projectId, {}) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projectRunSummary(projectId) });
      refreshWorkspace();
      navigate(`/projects/${projectId}/workspace/report/${run.id}`);
    },
    onError: (error) => message.error(getErrorMessage(error, "执行失败")),
  });

  // ===== 校验 =====
  const hasEnv = Boolean(environmentId);
  const targetReady =
    (scope === "project" && Boolean(projectId)) ||
    (scope === "collection" && Boolean(scopeId)) ||
    (scope === "case" && Boolean(scopeId));
  const hasCases = expectedCases.length > 0;
  const canSubmit = hasEnv && targetReady && hasCases && !createRunMutation.isPending;
  // F014：concurrent_candidates = expectedCases.length 时并发才有意义；并发度不应超过 case 数。
  const effectiveConcurrency = Math.max(MIN_CONCURRENCY, Math.min(concurrency, Math.max(expectedCases.length, MIN_CONCURRENCY)));

  // ===== 渲染 =====
  if (casesQuery.isLoading || environmentsQuery.isLoading) {
    return <LoadingBlock rows={4} />;
  }
  if (casesQuery.isError) {
    return (
      <ErrorState
        error={casesQuery.error}
        onRetry={() => void casesQuery.refetch()}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="执行中心"
        description="选择执行范围 / 环境，发起 Run。后端同步执行（最长 610 秒）。"
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "执行中心" },
        ]}
        extra={
          <Space>
            <Tooltip title="已就绪时执行">
              <Button
                type="primary"
                icon={<RocketOutlined />}
                loading={createRunMutation.isPending}
                disabled={!canSubmit}
                onClick={() => createRunMutation.mutate()}
              >
                立即执行
              </Button>
            </Tooltip>
          </Space>
        }
      />

      {!defaultEnvironmentId ? (
        <Alert
          className="inline-warning"
          type="warning"
          showIcon
          message="尚未设置默认环境"
          description="请前往 Environment 页面新建并设置默认环境。手动选择其他环境也可继续，但建议在项目内为每次执行明确指定环境。"
          style={{ marginBottom: 16 }}
        />
      ) : null}

      {createRunMutation.isError ? (
        <Alert
          className="inline-warning"
          type="error"
          showIcon
          message="执行失败"
          description={getErrorMessage(createRunMutation.error, "执行失败")}
          style={{ marginBottom: 16 }}
        />
      ) : null}

      <div className="content-grid run-center-grid">
        <Card className="surface-card grid-span-8" title="执行配置">
          <Form layout="vertical">
            <Form.Item label="执行范围" required>
              <Radio.Group
                value={scope}
                onChange={(e) => setScope(e.target.value as RunScope)}
                optionType="button"
                buttonStyle="solid"
              >
                <Radio.Button value="project">整个项目</Radio.Button>
                <Radio.Button value="collection">测试套件</Radio.Button>
                <Radio.Button value="case">单用例</Radio.Button>
              </Radio.Group>
            </Form.Item>

            {scope === "collection" ? (
              <Form.Item label="选择 Suite" required>
                <Select
                  placeholder="选择 Suite"
                  value={scopeId ?? undefined}
                  onChange={(v: string) => setScopeId(v)}
                  options={suites.map((s) => ({
                    value: s.id,
                    label: `${s.name}${s.description ? ` · ${s.description}` : ""}`,
                  }))}
                  showSearch
                  optionFilterProp="label"
                />
                {suites.length === 0 ? (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    暂无 Suite，请先创建。
                  </Typography.Text>
                ) : null}
              </Form.Item>
            ) : null}

            {scope === "case" ? (
              <Form.Item label="选择 Case" required>
                <Select
                  placeholder="选择 Case"
                  value={scopeId ?? undefined}
                  onChange={(v: string) => setScopeId(v)}
                  showSearch
                  optionFilterProp="label"
                  filterOption={(input, option) =>
                    String(option?.label ?? "").toLowerCase().includes(input.toLowerCase())
                  }
                  options={allCases
                    .filter((c) => c.enabled)
                    .map((c) => ({
                      value: c.id,
                      label: `${c.method}  ${c.name}  ·  ${c.path}`,
                    }))}
                />
                {allCases.length === 0 ? (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    暂无启用 Case，请先维护。
                  </Typography.Text>
                ) : null}
              </Form.Item>
            ) : null}

            <Form.Item label="执行环境" required>
              <Select
                placeholder="选择执行环境"
                value={environmentId ?? undefined}
                onChange={(v: string) => setEnvironmentId(v)}
                options={environments.map((e) => ({
                  value: e.id,
                  label: `${e.name}${e.is_default ? "（默认）" : ""} · ${e.base_url}`,
                }))}
              />
              {environments.length === 0 ? (
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  暂无环境，请前往 Environment 页面创建。
                </Typography.Text>
              ) : null}
            </Form.Item>

            <Form.Item
              label="执行名称（可选）"
              extra="留空将自动生成 'Run @ {时间戳}'"
            >
              <Input
                allowClear
                maxLength={200}
                showCount
                value={runName}
                onChange={(e) => setRunName(e.target.value)}
                placeholder="例如：用户服务回归 - v1.2"
              />
            </Form.Item>

            {/* F014：单 Run 并发度。传 1 等于串行；后端兜底非法值。 */}
            <Form.Item
              label={
                <Space size={6}>
                  <span>并发度（F014）</span>
                  <Tooltip title="单 Run 内同时在飞的最大 case 数。1=串行；后端默认 4；上限 64。高并发可能触发被测服务限流。">
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      （?concurrency=）
                    </Typography.Text>
                  </Tooltip>
                </Space>
              }
              extra={`当前预期 Case 数：${expectedCases.length}；实际生效 ${effectiveConcurrency}`}
            >
              <Space.Compact style={{ width: "100%" }}>
                <Slider
                  min={MIN_CONCURRENCY}
                  max={MAX_CONCURRENCY}
                  value={concurrency}
                  onChange={(v: number) => setConcurrency(v)}
                  style={{ flex: 1, marginRight: 16 }}
                  marks={{
                    1: "1",
                    [DEFAULT_CONCURRENCY]: String(DEFAULT_CONCURRENCY),
                    [MAX_CONCURRENCY]: String(MAX_CONCURRENCY),
                  }}
                  disabled={!hasCases}
                />
                <InputNumber
                  min={MIN_CONCURRENCY}
                  max={MAX_CONCURRENCY}
                  value={concurrency}
                  onChange={(v) => {
                    if (typeof v === "number" && Number.isFinite(v)) {
                      setConcurrency(v);
                    }
                  }}
                  disabled={!hasCases}
                  style={{ width: 96 }}
                />
              </Space.Compact>
            </Form.Item>
          </Form>
        </Card>

        <Card className="surface-card grid-span-4" title="执行预览">
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <PreviewRow
              label="Scope"
              value={
                <Tag color={scope === "project" ? "geekblue" : scope === "collection" ? "purple" : "cyan"}>
                  {scope === "project" ? "整个项目" : scope === "collection" ? "测试套件" : "单用例"}
                </Tag>
              }
            />
            <PreviewRow
              label="目标"
              value={
                scope === "project" ? (
                  <Typography.Text>当前 Project 全部启用 Case</Typography.Text>
                ) : scope === "collection" && scopeId ? (
                  <Typography.Text>
                    {suites.find((s) => s.id === scopeId)?.name ?? "—"}
                  </Typography.Text>
                ) : scope === "case" && scopeId ? (
                  <Typography.Text>
                    {allCases.find((c) => c.id === scopeId)?.name ?? "—"}
                  </Typography.Text>
                ) : (
                  <Typography.Text type="secondary">未选择</Typography.Text>
                )
              }
            />
            <PreviewRow
              label="环境"
              value={
                environmentId ? (
                  <Tag color="blue">
                    {environments.find((e) => e.id === environmentId)?.name ?? "—"}
                  </Tag>
                ) : (
                  <Tag color="orange">未选择</Tag>
                )
              }
            />
            <PreviewRow
              label="预期 Case"
              value={
                hasCases ? (
                  <Tag color="green" icon={<CheckCircleOutlined />}>
                    {expectedCases.length} 条
                  </Tag>
                ) : (
                  <Tag color="orange" icon={<ExclamationCircleOutlined />}>
                    0 条
                  </Tag>
                )
              }
            />
            <PreviewRow
              label="并发度"
              value={
                hasCases ? (
                  <Tag color={effectiveConcurrency === 1 ? "default" : "geekblue"}>
                    {effectiveConcurrency === 1 ? "串行" : `${effectiveConcurrency} 路并行`}
                  </Tag>
                ) : (
                  <Tag color="orange">—</Tag>
                )
              }
            />

            {expectedCases.length > 0 ? (
              <div className="run-preview-list">
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  前 {Math.min(expectedCases.length, 8)} 条预览：
                </Typography.Text>
                <div className="run-preview-list-body">
                  {expectedCases.slice(0, 8).map((c) => (
                    <Space key={c.id} size={6} className="run-preview-list-item">
                      <MethodTag method={c.method} />
                      <Typography.Text ellipsis style={{ maxWidth: 220 }}>
                        {c.name}
                      </Typography.Text>
                    </Space>
                  ))}
                  {expectedCases.length > 8 ? (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      … 还有 {expectedCases.length - 8} 条
                    </Typography.Text>
                  ) : null}
                </div>
              </div>
            ) : (
              <EmptyState
                title="当前范围没有可执行 Case"
                description="启用至少 1 条 Case，或调整执行范围。"
                icon={<AppstoreOutlined style={{ fontSize: 28, color: "#faad14" }} />}
                compact
              />
            )}
          </Space>
        </Card>
      </div>
    </>
  );
}

function PreviewRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="run-preview-row">
      <Typography.Text type="secondary" className="run-preview-row-label">
        {label}
      </Typography.Text>
      <div className="run-preview-row-value">{value}</div>
    </div>
  );
}
