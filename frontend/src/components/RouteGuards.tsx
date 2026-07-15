import { useEffect, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router-dom";
import { authApi } from "../api/auth";
import { queryKeys } from "../api/queryKeys";
import { useAuthStore } from "../store/auth";
import { ErrorState, LoadingBlock } from "./AsyncState";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation();
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const meQuery = useQuery({
    queryKey: queryKeys.me,
    queryFn: authApi.me,
    enabled: Boolean(token),
    staleTime: 5 * 60_000,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.data) setUser(meQuery.data);
  }, [meQuery.data, setUser]);

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (meQuery.isLoading) return <LoadingBlock fullPage tip="正在验证登录状态…" />;
  if (meQuery.isError) {
    return <ErrorState error={meQuery.error} onRetry={() => void meQuery.refetch()} />;
  }
  if (
    meQuery.data &&
    (!user || user.id !== meQuery.data.id || user.is_superuser !== meQuery.data.is_superuser)
  ) {
    return <LoadingBlock fullPage tip="正在同步账号权限…" />;
  }
  return children;
}

export function AdminRoute({ children }: { children: ReactNode }) {
  const user = useAuthStore((state) => state.user);
  if (!user?.is_superuser) return <Navigate to="/403" replace />;
  return children;
}
