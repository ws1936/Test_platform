import { api } from "./client";
import type {
  FailureList,
  ProjectRunSummary,
  RunStatus,
  TestResult,
  TestResultList,
  TestRun,
  TestRunList,
  TestRunPayload,
} from "./types";

const RUN_TIMEOUT_MS = 610_000;

export interface RunListParams {
  limit?: number;
  offset?: number;
  status?: RunStatus;
}

export interface CreateRunOptions {
  /** F014: 单 Run 内同时在飞的最大 case 数（1 ≤ N ≤ 64），以 query 形式附加。 */
  concurrency?: number;
}

export const runsApi = {
  async create(
    projectId: string,
    payload: TestRunPayload,
    options: CreateRunOptions = {},
  ): Promise<TestRun> {
    const params = options.concurrency
      ? { concurrency: options.concurrency }
      : undefined;
    const response = await api.post<TestRun>(`/projects/${projectId}/runs`, payload, {
      timeout: RUN_TIMEOUT_MS,
      ...(params ? { params } : {}),
    });
    return response.data;
  },

  async runCase(
    caseId: string,
    environmentId: string,
    name?: string,
    options: CreateRunOptions = {},
  ): Promise<TestRun> {
    const params = {
      environment_id: environmentId,
      ...(name ? { name } : {}),
      ...(options.concurrency ? { concurrency: options.concurrency } : {}),
    };
    const response = await api.post<TestRun>(
      `/test-cases/${caseId}/run`,
      undefined,
      {
        params,
        timeout: RUN_TIMEOUT_MS,
      },
    );
    return response.data;
  },

  /**
   * F015：下载 Run 报告（JSON / HTML），触发浏览器文件下载。
   * 走 axios 拿 blob（自动带 Authorization header），再创建临时 <a>
   * 触发下载。不在 URL 里塞 token，避免泄露到浏览器历史。
   */
  async exportReport(
    runId: string,
    format: "json" | "html",
  ): Promise<void> {
    const response = await api.get<Blob>(`/runs/${runId}/export`, {
      params: { format },
      responseType: "blob",
      // 报告可能较大，跳过默认 15s 超时
      timeout: 60_000,
    });
    const contentType = format === "json" ? "application/json" : "text/html";
    const blob = new Blob([response.data], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    // filename 由后端 Content-Disposition 提供；这里设个默认值提升 UX
    a.download = `run-${runId}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  async list(projectId: string, params: RunListParams = {}): Promise<TestRunList> {
    const response = await api.get<TestRunList>(`/projects/${projectId}/runs`, {
      params,
    });
    return response.data;
  },

  async projectSummary(projectId: string, recentLimit = 10): Promise<ProjectRunSummary> {
    const response = await api.get<ProjectRunSummary>(
      `/projects/${projectId}/runs/summary`,
      { params: { recent_limit: recentLimit } },
    );
    return response.data;
  },

  async get(runId: string): Promise<TestRun> {
    const response = await api.get<TestRun>(`/runs/${runId}`);
    return response.data;
  },

  async results(runId: string): Promise<TestResultList> {
    const response = await api.get<TestResultList>(`/runs/${runId}/results`);
    return response.data;
  },

  async failures(runId: string): Promise<FailureList> {
    const response = await api.get<FailureList>(`/runs/${runId}/failures`);
    return response.data;
  },

  async result(resultId: string): Promise<TestResult> {
    const response = await api.get<TestResult>(`/results/${resultId}`);
    return response.data;
  },
};
