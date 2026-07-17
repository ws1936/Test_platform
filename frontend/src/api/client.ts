import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "../store/auth";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const DEFAULT_TIMEOUT_MS = 15_000;

interface RetryRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

interface ErrorPayload {
  message?: string;
  detail?: string | { message?: string } | Array<{ msg?: string }>;
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: DEFAULT_TIMEOUT_MS,
});

let refreshPromise: Promise<string> | null = null;

function redirectToLogin(): void {
  const current = `${window.location.pathname}${window.location.search}`;
  if (window.location.pathname !== "/login") {
    window.location.assign(`/login?from=${encodeURIComponent(current)}`);
  }
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) throw new Error("No refresh token");

  const response = await axios.post<{
    access_token: string;
    refresh_token: string;
  }>(
    `${API_BASE}/auth/refresh`,
    { refresh_token: refreshToken },
    { timeout: DEFAULT_TIMEOUT_MS },
  );

  const { access_token: accessToken, refresh_token: nextRefreshToken } = response.data;
  useAuthStore.getState().setTokens(accessToken, nextRefreshToken);
  return accessToken;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as RetryRequestConfig | undefined;
    const isUnauthorized = error.response?.status === 401;
    const isAuthRequest = request?.url?.includes("/auth/login") || request?.url?.includes("/auth/refresh");

    if (isUnauthorized && request && !request._retry && !isAuthRequest) {
      request._retry = true;
      try {
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
        const accessToken = await refreshPromise;
        request.headers.Authorization = `Bearer ${accessToken}`;
        return await api(request);
      } catch {
        useAuthStore.getState().clear();
        redirectToLogin();
      }
    }

    return Promise.reject(error);
  },
);

export function getErrorMessage(error: unknown, fallback = "操作失败，请稍后重试"): string {
  if (axios.isAxiosError<ErrorPayload>(error)) {
    const payload = error.response?.data;
    if (payload?.message) return payload.message;
    if (typeof payload?.detail === "string") return payload.detail;
    if (payload?.detail && !Array.isArray(payload.detail) && payload.detail.message) {
      return payload.detail.message;
    }
    if (Array.isArray(payload?.detail)) {
      const validationMessage = payload.detail.find((item) => item.msg)?.msg;
      if (validationMessage) return validationMessage;
    }
    if (error.code === "ECONNABORTED") return "请求超时，请检查网络或稍后重试";
    if (!error.response) return "无法连接服务，请检查网络和服务状态";
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function getHttpStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined;
}

export interface ApiError {
  code: string;
  message: string;
  status: number | undefined;
  fields?: Record<string, string>;
  raw: unknown;
}

/**
 * Extract a structured {@link ApiError} from an unknown error.
 *
 * - Reads ``code`` / ``message`` / ``details`` from the backend
 *   ``code/message/details`` envelope (our handlers emit this shape).
 * - Maps the FastAPI-style ``detail`` array to ``fields`` for backward
 *   compatibility so existing ``VALIDATION_ERROR`` 422 responses can
 *   still be matched.
 * - Returns a stable shape that the UI can switch on.
 */
export function getApiError(error: unknown): ApiError {
  const fallback: ApiError = {
    code: "UNKNOWN_ERROR",
    message: "未知错误",
    status: getHttpStatus(error),
    raw: error,
  };

  if (!axios.isAxiosError(error)) {
    if (error instanceof Error) {
      return { ...fallback, message: error.message };
    }
    return fallback;
  }

  const status = error.response?.status;
  const data = error.response?.data as
    | {
        code?: string;
        message?: string;
        details?: unknown;
        detail?: unknown;
      }
    | undefined;

  if (!data) {
    return { ...fallback, status };
  }

  let fields: Record<string, string> | undefined;
  if (Array.isArray(data.detail)) {
    fields = {};
    for (const item of data.detail) {
      if (item && typeof item === "object" && "loc" in item) {
        const loc = (item as { loc: unknown }).loc;
        const field = Array.isArray(loc)
          ? loc.filter((l) => l !== "body").join(".")
          : "body";
        const message =
          (item as { msg?: string }).msg ?? "字段不合法";
        fields[field] = message;
      }
    }
  } else if (data.details && typeof data.details === "object") {
    fields = data.details as Record<string, string>;
  }

  return {
    code: data.code ?? fallback.code,
    message: data.message ?? fallback.message,
    status,
    fields,
    raw: error,
  };
}
