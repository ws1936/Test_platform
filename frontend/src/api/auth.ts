import { api } from "./client";
import type {
  LoginResponse,
  MessageResponse,
  TokenPair,
  User,
} from "./types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
}

export const authApi = {
  async login(payload: LoginPayload): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>("/auth/login", payload);
    return response.data;
  },

  async me(): Promise<User> {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  async logout(): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/auth/logout");
    return response.data;
  },

  async refresh(refreshToken: string): Promise<TokenPair> {
    const response = await api.post<TokenPair>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async changePassword(payload: ChangePasswordPayload): Promise<MessageResponse> {
    const response = await api.put<MessageResponse>("/users/me/password", payload);
    return response.data;
  },
};
