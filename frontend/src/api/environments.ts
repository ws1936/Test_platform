import { api } from "./client";
import type {
  Environment,
  EnvironmentList,
  EnvironmentPayload,
  MessageResponse,
} from "./types";

export const environmentsApi = {
  async list(projectId: string, search = ""): Promise<EnvironmentList> {
    const response = await api.get<EnvironmentList>(
      `/projects/${projectId}/environments`,
      { params: search ? { search } : undefined },
    );
    return response.data;
  },

  async get(environmentId: string): Promise<Environment> {
    const response = await api.get<Environment>(`/environments/${environmentId}`);
    return response.data;
  },

  async create(projectId: string, payload: EnvironmentPayload): Promise<Environment> {
    const response = await api.post<Environment>(
      `/projects/${projectId}/environments`,
      payload,
    );
    return response.data;
  },

  async update(
    environmentId: string,
    payload: Partial<EnvironmentPayload>,
  ): Promise<Environment> {
    const response = await api.put<Environment>(
      `/environments/${environmentId}`,
      payload,
    );
    return response.data;
  },

  async setDefault(environmentId: string): Promise<Environment> {
    const response = await api.post<Environment>(
      `/environments/${environmentId}/set-default`,
    );
    return response.data;
  },

  async remove(environmentId: string): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(`/environments/${environmentId}`);
    return response.data;
  },
};
