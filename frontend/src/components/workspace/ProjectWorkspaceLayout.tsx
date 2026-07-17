import { ProjectOutlined, WifiOutlined } from "@ant-design/icons";
import { useQueries, useQueryClient } from "@tanstack/react-query";
import { Alert, Skeleton, Spin } from "antd";
import { useMemo, type ReactNode } from "react";
import { Outlet, useParams } from "react-router-dom";
import { environmentsApi } from "../../api/environments";
import { projectsApi } from "../../api/projects";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import { suitesApi } from "../../api/suites";
import { testCasesApi } from "../../api/testCases";
import type { Project, TestRun, TestRunList } from "../../api/types";
import { ErrorState, LoadingBlock } from "../AsyncState";
import {
  ProjectWorkspaceContext,
  type ProjectWorkspaceContextValue,
  type ProjectWorkspaceReadiness,
} from "./projectWorkspaceContext";
import ProjectWorkspaceHeader from "./ProjectWorkspaceHeader";
import ProjectWorkspaceSider from "./ProjectWorkspaceSider";
import ProjectWorkspaceContextPanel from "./ProjectWorkspaceContextPanel";

const SUMMARY_LIMIT = 5;

export type { ProjectWorkspaceContextValue, ProjectWorkspaceReadiness } from "./projectWorkspaceContext";

export default function ProjectWorkspaceLayout({ children }: { children?: ReactNode }) {
  const params = useParams();
  const projectId = (params.projectId ?? "").trim();
  const queryClient = useQueryClient();

  const projectQuery = useQueries({
    queries: [
      {
        queryKey: queryKeys.project(projectId),
        queryFn: () => projectsApi.get(projectId),
        enabled: Boolean(projectId),
        staleTime: 60_000,
      },
      {
        queryKey: queryKeys.environments(projectId, ""),
        queryFn: () => environmentsApi.list(projectId),
        enabled: Boolean(projectId),
        staleTime: 60_000,
      },
      {
        queryKey: queryKeys.suites(projectId, ""),
        queryFn: () => suitesApi.list(projectId),
        enabled: Boolean(projectId),
        staleTime: 60_000,
      },
      {
        queryKey: queryKeys.cases(projectId, ""),
        queryFn: () => testCasesApi.listProject(projectId),
        enabled: Boolean(projectId),
        staleTime: 60_000,
      },
      {
        queryKey: queryKeys.runs(projectId, { limit: SUMMARY_LIMIT }),
        queryFn: () => runsApi.list(projectId, { limit: SUMMARY_LIMIT }),
        enabled: Boolean(projectId),
        staleTime: 15_000,
      },
      {
        queryKey: queryKeys.projectRunSummary(projectId),
        queryFn: () => runsApi.projectSummary(projectId),
        enabled: Boolean(projectId),
        staleTime: 30_000,
      },
    ],
  });
  const [
    projectQueryDetail,
    environmentsQuery,
    suitesQuery,
    casesQuery,
    runsQuery,
    summaryQuery,
  ] = projectQuery;

  const project: Project | null = projectQueryDetail.data ?? null;
  const environments = useMemo(
    () => environmentsQuery.data?.items ?? [],
    [environmentsQuery.data?.items],
  );
  const suites = useMemo(() => suitesQuery.data?.items ?? [], [suitesQuery.data?.items]);
  const caseTotal = casesQuery.data?.total ?? 0;
  const runList: TestRunList | undefined = runsQuery.data as TestRunList | undefined;
  const latestRun: TestRun | null = useMemo(
    () => runList?.items?.[0] ?? null,
    [runList],
  );
  const summary = summaryQuery.data;
  const defaultEnvironment = useMemo(
    () => environments.find((item) => item.is_default) ?? null,
    [environments],
  );

  const readiness = useMemo<ProjectWorkspaceReadiness>(
    () => ({
      hasEnvironment: environments.length > 0,
      hasDefaultEnvironment: defaultEnvironment !== null,
      hasSuite: suites.length > 0,
      hasCase: caseTotal > 0,
      hasRun: (summary?.total_runs ?? 0) > 0,
      hasSuccessfulRun: (summary?.total_passed ?? 0) > 0,
    }),
    [caseTotal, defaultEnvironment, environments.length, suites.length, summary],
  );

  const isLoading =
    projectQueryDetail.isLoading ||
    environmentsQuery.isLoading ||
    suitesQuery.isLoading ||
    casesQuery.isLoading;
  // Only the project detail failure is fatal: the project is the
  // workspace's identity. Sub-resource queries (env / suite / case / run)
  // return empty data for a new project; their failures should be
  // surfaced inline (P2) rather than blocking the entire layout.
  const isError = projectQueryDetail.isError;

  const contextValue = useMemo<ProjectWorkspaceContextValue>(() => {
    const refresh = () => {
      if (!projectId) return;
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.environments(projectId, "") });
      void queryClient.invalidateQueries({ queryKey: queryKeys.suites(projectId, "") });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, "") });
      void queryClient.invalidateQueries({ queryKey: queryKeys.runs(projectId, {}) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projectRunSummary(projectId) });
    };
    return {
      projectId,
      project,
      latestRun,
      defaultEnvironmentId: defaultEnvironment?.id ?? null,
      readiness,
      isReady: project !== null,
      refresh,
    };
  }, [
    projectId,
    project,
    latestRun,
    defaultEnvironment,
    readiness,
    queryClient,
  ]);

  if (isLoading) {
    return <LoadingBlock rows={8} />;
  }

  if (isError) {
    return (
      <ErrorState
        error={
          projectQueryDetail.error ??
          environmentsQuery.error ??
          suitesQuery.error ??
          casesQuery.error
        }
        onRetry={() => contextValue.refresh()}
      />
    );
  }

  if (!project) {
    return (
      <ResultBlock
        title="项目数据为空"
        description="可能已被删除或当前账号无权访问。"
        actionLabel="返回项目列表"
        onAction={() => {
          window.location.assign("/projects");
        }}
      />
    );
  }

  if (!projectId) {
    return <ResultBlock title="缺少项目 ID" description="无法进入工作空间。" />;
  }

  return (
    <ProjectWorkspaceContext.Provider value={contextValue}>
      <div className="workspace-shell">
        <ProjectWorkspaceHeader
          project={project}
          latestRun={latestRun}
          defaultEnvironmentId={defaultEnvironment?.id ?? null}
        />
        <div className="workspace-body">
          <ProjectWorkspaceSider projectId={projectId} />
          <main className="workspace-content">
            {children ?? <Outlet />}
            {isLoading ? (
              <div className="workspace-soft-loading">
                <Spin indicator={<WifiOutlined spin />} size="small" /> 正在刷新 Workspace…
              </div>
            ) : null}
          </main>
          <ProjectWorkspaceContextPanel
            defaultEnvironmentId={defaultEnvironment?.id ?? null}
            defaultEnvironmentName={defaultEnvironment?.name ?? null}
            defaultEnvironmentBaseUrl={defaultEnvironment?.base_url ?? null}
            latestRun={latestRun}
            readiness={readiness}
          />
        </div>
        {!readiness.hasDefaultEnvironment ? (
          <Alert
            className="workspace-soft-alert"
            type="warning"
            showIcon
            message="尚未设置默认环境"
            description="Project Run 之前必须先设置默认环境。Suite 和 Case 也可先准备就绪。"
            style={{ margin: "0 28px 16px" }}
          />
        ) : null}
      </div>
    </ProjectWorkspaceContext.Provider>
  );
}

function ResultBlock({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <Skeleton active paragraph={{ rows: 4 }}>
      <Alert
        className="inline-warning"
        type="warning"
        showIcon
        message={title}
        description={description}
        action={actionLabel && onAction ? <button type="button" onClick={onAction}>{actionLabel}</button> : null}
        icon={<ProjectOutlined />}
      />
    </Skeleton>
  );
}
