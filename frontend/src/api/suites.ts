import { api } from "./client";
import type {
  MessageResponse,
  Suite,
  SuiteBulkResult,
  SuiteCaseLink,
  SuiteDetail,
  SuiteList,
  SuitePayload,
  TestCase,
} from "./types";

export const suitesApi = {
  async list(projectId: string, search = ""): Promise<SuiteList> {
    const response = await api.get<SuiteList>(`/projects/${projectId}/suites`, {
      params: search ? { search } : undefined,
    });
    return response.data;
  },

  async get(projectId: string, suiteId: string): Promise<SuiteDetail> {
    const response = await api.get<SuiteDetail>(
      `/projects/${projectId}/suites/${suiteId}`,
    );
    return response.data;
  },

  async create(projectId: string, payload: SuitePayload): Promise<Suite> {
    const response = await api.post<Suite>(`/projects/${projectId}/suites`, payload);
    return response.data;
  },

  async update(
    projectId: string,
    suiteId: string,
    payload: Partial<SuitePayload>,
  ): Promise<Suite> {
    const response = await api.put<Suite>(
      `/projects/${projectId}/suites/${suiteId}`,
      payload,
    );
    return response.data;
  },

  async remove(projectId: string, suiteId: string): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(
      `/projects/${projectId}/suites/${suiteId}`,
    );
    return response.data;
  },

  async listCases(suiteId: string): Promise<TestCase[]> {
    const response = await api.get<TestCase[]>(`/collections/${suiteId}/cases`);
    return response.data;
  },

  async addCases(
    projectId: string,
    suiteId: string,
    testCaseIds: string[],
  ): Promise<SuiteBulkResult> {
    const response = await api.post<SuiteBulkResult>(
      `/projects/${projectId}/suites/${suiteId}/cases`,
      { test_case_ids: testCaseIds },
    );
    return response.data;
  },

  async reorderCases(
    projectId: string,
    suiteId: string,
    testCaseIds: string[],
  ): Promise<SuiteCaseLink[]> {
    const response = await api.put<SuiteCaseLink[]>(
      `/projects/${projectId}/suites/${suiteId}/cases/order`,
      { test_case_ids: testCaseIds },
    );
    return response.data;
  },

  async removeCase(
    projectId: string,
    suiteId: string,
    caseId: string,
  ): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(
      `/projects/${projectId}/suites/${suiteId}/cases/${caseId}`,
    );
    return response.data;
  },
};
