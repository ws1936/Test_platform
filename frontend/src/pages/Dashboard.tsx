import {
  PlayCircleOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App,
  Alert,
  Button,
  Card,
  Col,
  Row,
  Select,
  Space,
  Typography,
} from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { projectsApi } from "../api/projects";
import { queryKeys } from "../api/queryKeys";
import { runsApi } from "../api/runs";
import { suitesApi } from "../api/suites";
import type { Project, TestRun, TestRunList } from "../api/types";
import PageHeader from "../components/PageHeader";
import ProjectFormModal from "../components/ProjectFormModal";
import DashboardMetricCard from "../components/dashboard/DashboardMetricCard";
import RecentProjectsPanel from "../components/dashboard/RecentProjectsPanel";
import RecentReportsPanel from "../components/dashboard/RecentReportsPanel";
import RecentRunsPanel from "../components/dashboard/RecentRunsPanel";
import RecentSuitesPanel from "../components/dashboard/RecentSuitesPanel";
import { useAuthStore } from "../store/auth";
import { deriveDashboardRunData, getRecentSuites } from "../utils/dashboard";
import { formatPercent } from "../utils/format";

// 与 AppShell 的项目切换器共享同一缓存（page=1, size=DASHBOARD_PROJECTS_SIZE），
// 以避免在两个外壳同时调 /projects 时重复请求。
const DASHBOARD_PROJECTS_SIZE = 100;
const DASHBOARD_RUN_WINDOW = 200;

function isUuid(value: string | null): value is string {
  if (!value) return false;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedProjectId = searchParams.get("project");
  const [createOpen, setCreateOpen] = useState(false);

  const projectsQuery = useQuery({
    // P1-3: 移除 queryKey 中无意义的 `dashboard: true` 维度，便于与 AppShell 共享缓存键。
    queryKey: queryKeys.projects({ page: 1, size: DASHBOARD_PROJECTS_SIZE }),
    queryFn: () => projectsApi.list({ page: 1, size: DASHBOARD_PROJECTS_SIZE }),
  });

  const ownedProjects = useMemo<Project[]>(
    () => projectsQuery.data?.items ?? [],
    [projectsQuery.data?.items],
  );
  const ownedProjectIds = useMemo(
    () => new Set(ownedProjects.map((project) => project.id)),
    [ownedProjects],
  );

  // P1-2: URL 中的合法 projectId 在 Project 列表仍在 loading 时保留为"待应用 ID"，
  // 避免刷新 /dashboard?project=<id> 时，列表尚未回来 → 闪空 → 再恢复。
  const resolvedRequestedId = useMemo(() => {
    if (requestedProjectId && ownedProjectIds.has(requestedProjectId)) {
      return requestedProjectId;
    }
    if (
      requestedProjectId &&
      isUuid(requestedProjectId) &&
      projectsQuery.isLoading
    ) {
      return requestedProjectId;
    }
    return null;
  }, [ownedProjectIds, projectsQuery.isLoading, requestedProjectId]);

  const setProject = useCallback(
    (projectId: string) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          if (projectId) next.set("project", projectId);
          else next.delete("project");
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleProjectsError = useCallback(() => {
    if (projectsQuery.isError) {
      return getErrorMessage(projectsQuery.error, "项目列表加载失败");
    }
    return null;
  }, [projectsQuery.error, projectsQuery.isError]);

  // P1-1: 将"URL 指定的项目不可用"判定从渲染过程迁到 useEffect，
  // 避免 StrictMode / 并发渲染下 message.warning 被多次触发。
  useEffect(() => {
    if (!requestedProjectId) return;
    if (!isUuid(requestedProjectId)) return;
    if (projectsQuery.isLoading) return;
    // 列表成功加载且非空、且 ID 不在列表中 → 提示并回退。
    if (!projectsQuery.isError && !ownedProjectIds.size) return;
    if (ownedProjectIds.has(requestedProjectId)) return;
    message.warning("URL 中指定的项目不可用，已回退到最近创建的项目。");
    setProject("");
  }, [
    ownedProjectIds,
    projectsQuery.isError,
    projectsQuery.isLoading,
    message,
    requestedProjectId,
    setProject,
  ]);

  const selectedProject = useMemo(
    () => ownedProjects.find((project) => project.id === resolvedRequestedId) ?? null,
    [ownedProjects, resolvedRequestedId],
  );
  // P1-2 配套: 当 URL 项目被暂存为"待应用"、ownedProjects 尚未包含它时，
  // 仍允许 selectedProjectId 取到 resolvedRequestedId，便于下方 Panel 文案/链接保持稳定。
  const selectedProjectId = selectedProject?.id ?? resolvedRequestedId;
  const selectedProjectName = selectedProject?.name ?? "未选择项目";
  const runsUrl = selectedProjectId ? `/projects/${selectedProjectId}/runs` : "/dashboard";
  const reportsUrl = selectedProjectId ? `/projects/${selectedProjectId}/reports` : "/dashboard";

  const runsArgs: { projectId: string; params: { limit: number } } | null =
    selectedProjectId
      ? { projectId: selectedProjectId, params: { limit: DASHBOARD_RUN_WINDOW } }
      : null;

  const dashboardQueries = useQueries({
    queries: [
      {
        queryKey: selectedProjectId
          ? queryKeys.runs(selectedProjectId, { limit: DASHBOARD_RUN_WINDOW })
          : ["dashboard", "runs", "idle"],
        queryFn: () => {
          if (!runsArgs) throw new Error("未选择项目，无法加载执行");
          return runsApi.list(runsArgs.projectId, runsArgs.params);
        },
        enabled: Boolean(selectedProjectId),
        staleTime: 15_000,
      },
      {
        queryKey: selectedProjectId
          ? queryKeys.suites(selectedProjectId, "dashboard")
          : ["dashboard", "suites", "idle"],
        queryFn: () => {
          if (!selectedProjectId) throw new Error("未选择项目，无法加载 Suite");
          return suitesApi.list(selectedProjectId);
        },
        enabled: Boolean(selectedProjectId),
        staleTime: 60_000,
      },
    ],
  });
  const runsResult = dashboardQueries[0];
  const suitesResult = dashboardQueries[1];

  const runList: TestRunList | undefined = runsResult.data as TestRunList | undefined;
  const runs: TestRun[] = useMemo(
    () => (runList?.items ?? []) as TestRun[],
    [runList],
  );
  const totalRuns = runList?.total ?? 0;
  const suites = useMemo(() => suitesResult.data?.items ?? [], [suitesResult.data?.items]);
  const projectRunData = useMemo(
    () => deriveDashboardRunData(runs, totalRuns),
    [runs, totalRuns],
  );
  const recentProjects = useMemo(() => ownedProjects.slice(0, 5), [ownedProjects]);
  const recentSuites = useMemo(() => getRecentSuites(suites), [suites]);

  // 选中项目后：仅保留"最近 Suite"作为当前 Project 的最后一站；
  // "最近 Project"语义与已选项目维度冲突，隐藏以聚焦。
  // 兜底：在 Scope 卡里放一个"切换项目"出口（指向 /projects）。
  const recentProjectsVisible = !selectedProjectId;
  // 未选中时 Suite 与 Projects 并排各占 6 列；选中后 Suite 单独占 12 列。
  const recentSuitesSpanClass = selectedProjectId ? "grid-span-12" : "grid-span-6";

  const handleRefresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["projects"] });
    if (selectedProjectId) {
      void queryClient.invalidateQueries({ queryKey: queryKeys.runs(selectedProjectId, { limit: DASHBOARD_RUN_WINDOW }) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.suites(selectedProjectId, "dashboard") });
    }
  };

  return (
    <>
      <PageHeader
        title={`你好，${user?.nickname || user?.username || "用户"}`}
        description={
          selectedProjectId
            ? `当前数据范围：${selectedProjectName}`
            : "请选择一个 Project 查看最近执行、最近 Report 与 KPI。"
        }
        extra={
          <Space wrap>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              disabled={projectsQuery.isFetching || runsResult.isFetching || suitesResult.isFetching}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              disabled={!selectedProjectId}
              onClick={() => navigate(runsUrl)}
            >
              发起执行
            </Button>
          </Space>
        }
      />

      <Card className="surface-card dashboard-scope-card" bordered={false}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={8}>
            <Typography.Text type="secondary">数据范围</Typography.Text>
            <Select
              value={selectedProjectId ?? undefined}
              loading={projectsQuery.isLoading}
              disabled={projectsQuery.isError || !ownedProjects.length}
              placeholder={ownedProjects.length ? "选择 Project" : "尚无 Project"}
              options={ownedProjects.map((project) => ({ value: project.id, label: project.name }))}
              onChange={(value) => setProject(value)}
              showSearch
              optionFilterProp="label"
              className="dashboard-scope-select"
              aria-label="Dashboard 数据范围"
            />
            {projectsQuery.isError ? (
              <Typography.Text type="danger" className="dashboard-scope-hint">
                {handleProjectsError()}
              </Typography.Text>
            ) : null}
          </Col>
          <Col xs={24} md={16}>
            <Space wrap className="dashboard-scope-meta">
              <Typography.Text type="secondary">
                共 {ownedProjects.length} 个 Project
              </Typography.Text>
              {selectedProjectId ? (
                <>
                  <Typography.Text type="secondary">·</Typography.Text>
                  <Typography.Text>当前 Project：{selectedProjectName}</Typography.Text>
                </>
              ) : null}
              {user?.is_superuser ? (
                <>
                  <Typography.Text type="secondary">·</Typography.Text>
                  <Button
                    size="small"
                    icon={<TeamOutlined />}
                    onClick={() => navigate("/admin/users")}
                  >
                    用户管理
                  </Button>
                  <Button
                    size="small"
                    icon={<SafetyCertificateOutlined />}
                    onClick={() => navigate("/admin/roles")}
                  >
                    角色管理
                  </Button>
                </>
              ) : null}
              {/* 兜底：选中项目后，提供一个"切换项目"文字链，避免隐藏"最近项目"后失去横向导航能力。 */}
              {selectedProjectId ? (
                <>
                  <Typography.Text type="secondary">·</Typography.Text>
                  <Button
                    size="small"
                    type="link"
                    icon={<SwapOutlined />}
                    onClick={() => navigate("/projects")}
                  >
                    切换项目
                  </Button>
                </>
              ) : null}
            </Space>
          </Col>
        </Row>
      </Card>

      {!ownedProjects.length && !projectsQuery.isLoading && !projectsQuery.isError ? (
        <Alert
          className="inline-warning"
          type="info"
          showIcon
          message="尚未创建 Project"
          description="Platform 仅提供 Project 维度的执行与报告数据；请先创建 Project 后再查看 Dashboard。"
          action={<Button onClick={() => setCreateOpen(true)}>新建 Project</Button>}
        />
      ) : null}

      {selectedProjectId && projectsQuery.isError ? (
        <Alert
          className="inline-warning"
          type="error"
          showIcon
          message="项目列表加载失败"
          description="无法解析 Dashboard 数据范围，请稍后重试。"
        />
      ) : null}

      <div className="content-grid dashboard-grid">
        {/* BUG 修复: emptyTitle 必须由"真实数据为 0"派生，而不是 selectedProjectId。
            之前一旦选了项目，emptyTitle 永远为真，导致 DashboardMetricCard 永远走
            EmptyState 分支、value/percent/hint 全部不画。 */}
        <DashboardMetricCard
          className="grid-span-6"
          title="Run Success Rate"
          value={projectRunData.successRate === null ? "—" : formatPercent(projectRunData.successRate)}
          hint={`成功 ${projectRunData.successfulCount} / 已完成 ${projectRunData.completedCount} Run · 最近最多 ${DASHBOARD_RUN_WINDOW} 条`}
          loading={runsResult.isLoading}
          error={selectedProjectId ? runsResult.error : null}
          onRetry={handleRefresh}
          percent={projectRunData.successRate ?? undefined}
          emptyTitle={
            selectedProjectId && projectRunData.completedCount === 0
              ? "暂无已完成 Run"
              : undefined
          }
          onClick={selectedProjectId ? () => navigate(reportsUrl) : undefined}
        />
        <DashboardMetricCard
          className="grid-span-6"
          title="今日执行次数"
          value={selectedProjectId ? projectRunData.todayDisplay : "—"}
          hint={
            selectedProjectId
              ? `当前 Project · ${projectRunData.todayIsExact ? "按本地时区统计" : "至少 200+，实际可能更多"}`
              : "请先选择 Project"
          }
          loading={runsResult.isLoading}
          error={selectedProjectId ? runsResult.error : null}
          onRetry={handleRefresh}
          emptyTitle={
            selectedProjectId && projectRunData.todayCount === 0
              ? "今日尚无执行"
              : undefined
          }
          onClick={selectedProjectId ? () => navigate(reportsUrl) : undefined}
        />

        <div className="grid-span-8">
          <RecentRunsPanel
            projectId={selectedProjectId ?? ""}
            runs={projectRunData.recentRuns}
            loading={runsResult.isLoading || runsResult.isFetching}
            error={selectedProjectId ? runsResult.error : null}
            onRetry={handleRefresh}
          />
        </div>
        <div className="grid-span-4">
          <RecentReportsPanel
            projectId={selectedProjectId ?? ""}
            reports={projectRunData.recentReports}
            loading={runsResult.isLoading || runsResult.isFetching}
            error={selectedProjectId ? runsResult.error : null}
            onRetry={handleRefresh}
          />
        </div>

        {recentProjectsVisible ? (
          <div className="grid-span-6">
            <RecentProjectsPanel
              projects={recentProjects}
              loading={projectsQuery.isLoading || projectsQuery.isFetching}
              error={projectsQuery.error}
              onRetry={handleRefresh}
              onCreate={() => setCreateOpen(true)}
            />
          </div>
        ) : null}
        <div className={recentSuitesSpanClass}>
          <RecentSuitesPanel
            projectId={selectedProjectId ?? ""}
            projectName={selectedProjectName}
            suites={recentSuites}
            loading={suitesResult.isLoading || suitesResult.isFetching}
            error={selectedProjectId ? suitesResult.error : null}
            onRetry={handleRefresh}
          />
        </div>

        {/* 优化 G: 删去 dashboard-hint-card，与各 Panel 自带提示重复。*/}
      </div>

      <ProjectFormModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSaved={(project) => {
          setProject(project.id);
          const next = new URLSearchParams();
          next.set("justCreated", "1");
          navigate(`/projects/${project.id}/workspace/overview?${next.toString()}`);
        }}
      />
    </>
  );
}
