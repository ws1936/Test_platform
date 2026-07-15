import { api } from "./client";
import type {
  MessageResponse,
  TestCase,
  TestCaseList,
  TestCasePayload,
} from "./types";

export const testCasesApi = {
  async listProject(projectId: string, search = ""): Promise<TestCaseList> {
    const response = await api.get<TestCaseList>(`/projects/${projectId}/test-cases`, {
      params: search ? { search } : undefined,
    });
    return response.data;
  },

  async get(caseId: string): Promise<TestCase> {
    const response = await api.get<TestCase>(`/test-cases/${caseId}`);
    return response.data;
  },

  async create(suiteId: string, payload: TestCasePayload): Promise<TestCase> {
    const response = await api.post<TestCase>(`/collections/${suiteId}/cases`, payload);
    return response.data;
  },

  async update(caseId: string, payload: Partial<TestCasePayload>): Promise<TestCase> {
    const response = await api.put<TestCase>(`/test-cases/${caseId}`, payload);
    return response.data;
  },

  async remove(caseId: string): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(`/test-cases/${caseId}`);
    return response.data;
  },
};
