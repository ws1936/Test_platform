import { api } from "./client";
import type { MessageResponse, Project, ProjectList, ProjectPayload } from "./types";

export interface ProjectListParams {
  page?: number;
  size?: number;
  search?: string;
}

export const projectsApi = {
  async list(params: ProjectListParams = {}): Promise<ProjectList> {
    const response = await api.get<ProjectList>("/projects", { params });
    return response.data;
  },

  async get(projectId: string): Promise<Project> {
    const response = await api.get<Project>(`/projects/${projectId}`);
    return response.data;
  },

  async create(payload: ProjectPayload, signal?: AbortSignal): Promise<Project> {
    const response = await api.post<Project>("/projects", payload, { signal });
    return response.data;
  },

  async update(
    projectId: string,
    payload: Partial<ProjectPayload>,
    signal?: AbortSignal,
  ): Promise<Project> {
    const response = await api.put<Project>(`/projects/${projectId}`, payload, { signal });
    return response.data;
  },

  async remove(projectId: string): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(`/projects/${projectId}`);
    return response.data;
  },
};
