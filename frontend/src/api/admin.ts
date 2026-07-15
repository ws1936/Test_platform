import { api } from "./client";
import type {
  CreateUserPayload,
  LoginResponse,
  MessageResponse,
  Role,
  RolePayload,
  UpdateUserPayload,
  User,
  UserList,
} from "./types";

export interface UserListParams {
  page?: number;
  size?: number;
  search?: string;
}

export const usersApi = {
  async list(params: UserListParams = {}): Promise<UserList> {
    const response = await api.get<UserList>("/users", { params });
    return response.data;
  },

  async get(userId: string): Promise<User> {
    const response = await api.get<User>(`/users/${userId}`);
    return response.data;
  },

  async create(payload: CreateUserPayload): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>("/auth/register", payload);
    return response.data;
  },

  async update(userId: string, payload: UpdateUserPayload): Promise<User> {
    const response = await api.put<User>(`/users/${userId}`, payload);
    return response.data;
  },

  async disable(userId: string): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(`/users/${userId}`);
    return response.data;
  },
};

export const rolesApi = {
  async list(): Promise<Role[]> {
    const response = await api.get<Role[]>("/roles");
    return response.data;
  },

  async get(roleId: string): Promise<Role> {
    const response = await api.get<Role>(`/roles/${roleId}`);
    return response.data;
  },

  async create(payload: RolePayload): Promise<Role> {
    const response = await api.post<Role>("/roles", payload);
    return response.data;
  },

  async update(roleId: string, payload: Partial<RolePayload>): Promise<Role> {
    const response = await api.put<Role>(`/roles/${roleId}`, payload);
    return response.data;
  },

  async remove(roleId: string): Promise<void> {
    await api.delete(`/roles/${roleId}`);
  },
};
