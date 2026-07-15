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

export const runsApi = {
  async create(projectId: string, payload: TestRunPayload): Promise<TestRun> {
    const response = await api.post<TestRun>(`/projects/${projectId}/runs`, payload, {
      timeout: RUN_TIMEOUT_MS,
    });
    return response.data;
  },

  async runCase(
    caseId: string,
    environmentId: string,
    name?: string,
  ): Promise<TestRun> {
    const response = await api.post<TestRun>(
      `/test-cases/${caseId}/run`,
      undefined,
      {
        params: { environment_id: environmentId, ...(name ? { name } : {}) },
        timeout: RUN_TIMEOUT_MS,
      },
    );
    return response.data;
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
