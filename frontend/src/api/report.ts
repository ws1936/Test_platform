// Report Center 共享 hooks
// 仅复用现有 Run / Result / Failure API；不新增业务能力、接口或数据库。

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { environmentsApi } from "./environments";
import { queryKeys } from "./queryKeys";
import { runsApi } from "./runs";
import type {
  Environment,
  EnvironmentList,
  FailureList,
  ProjectRunSummary,
  ResultStatus,
  TestResult,
  TestResultList,
  TestRun,
  TestRunList,
  RunStatus,
} from "./types";

export interface ReportRunHeader {
  run: TestRun;
  environment: Environment | null;
}

export interface FailureCategorySummary {
  key: FailureCategoryKey;
  label: string;
  /** 唯一 Result 数量。Assertion Fail / Error 视作 Result 级证据。 */
  resultCount: number;
  /** 唯一 Case / 测试用例数量。 */
  caseCount: number;
  /** 该分类是否基于 API 返回的真实证据。 */
  hasEvidence: boolean;
  /** 该分类最常出现的描述。 */
  hint: string;
}

export type FailureCategoryKey =
  | "assertion"
  | "httpError"
  | "variable"
  | "timeout"
  | "network";

export interface FailureAnalysisResult {
  totals: {
    failureItems: number;
    caseCount: number;
  };
  categories: FailureCategorySummary[];
  cases: TestResult[];
}

export interface UseReportSummaryArgs {
  projectId: string;
  recentLimit?: number;
}

export function useReportSummary({
  projectId,
  recentLimit = 10,
}: UseReportSummaryArgs): UseQueryResult<ProjectRunSummary, Error> {
  return useQuery({
    queryKey: queryKeys.projectRunSummary(projectId),
    queryFn: () => runsApi.projectSummary(projectId, recentLimit),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });
}

export function useReportRun(runId: string): UseQueryResult<TestRun, Error> {
  return useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: () => runsApi.get(runId),
    enabled: Boolean(runId),
  });
}

export function useReportEnvironments(
  projectId: string,
): UseQueryResult<EnvironmentList, Error> {
  return useQuery({
    queryKey: queryKeys.environments(projectId, ""),
    queryFn: () => environmentsApi.list(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });
}

export function useReportRunResults(runId: string): UseQueryResult<TestResultList, Error> {
  return useQuery({
    queryKey: queryKeys.runResults(runId),
    queryFn: () => runsApi.results(runId),
    enabled: Boolean(runId),
  });
}

export function useReportRunFailures(runId: string): UseQueryResult<FailureList, Error> {
  return useQuery({
    queryKey: queryKeys.runFailures(runId),
    queryFn: () => runsApi.failures(runId),
    enabled: Boolean(runId),
  });
}

export function useReportResult(resultId: string): UseQueryResult<TestResult, Error> {
  return useQuery({
    queryKey: queryKeys.result(resultId),
    queryFn: () => runsApi.result(resultId),
    enabled: Boolean(resultId),
  });
}

export interface UseReportHistoryArgs {
  projectId: string;
  status?: RunStatus;
  limit?: number;
  offset?: number;
}

export function useReportHistory({
  projectId,
  status,
  limit = 50,
  offset = 0,
}: UseReportHistoryArgs): UseQueryResult<TestRunList, Error> {
  return useQuery({
    queryKey: queryKeys.runs(projectId, { status, limit, offset }),
    queryFn: () => runsApi.list(projectId, { status, limit, offset }),
    enabled: Boolean(projectId),
  });
}

// Failure Analysis：基于 Run / Result / Failure 已有数据
// 不新增 API、不写数据库；只在前端按已有证据归类。

const VARIABLE_TOKENS = ["{{", "${"];
const TIMEOUT_CODES = new Set(["API_EXECUTION_TIMEOUT"]);
const NETWORK_CODES = new Set(["API_CONNECTION_ERROR"]);

function responseStatusOf(result: TestResult): number | undefined {
  const snapshot = result.response_snapshot;
  if (!snapshot || typeof snapshot !== "object") return undefined;
  const value = (snapshot as { status?: unknown }).status;
  return typeof value === "number" ? value : undefined;
}

function isHttpErrorStatus(status: number | undefined): boolean {
  return typeof status === "number" && status >= 400;
}

function isErrorResult(result: TestResult): boolean {
  return result.status === "error";
}

function isFailedResult(result: TestResult): boolean {
  return result.status === "failed";
}

export interface FailureAnalysisInput {
  results: TestResult[];
  failureItems: { result_id: string; assertion_type: string; expected: unknown; actual: unknown; message: string }[];
}

function findVariableTokens(value: unknown, found: string[] = []): string[] {
  if (found.length >= 3) return found;
  if (value === null || value === undefined) return found;
  if (typeof value === "string") {
    VARIABLE_TOKENS.forEach((token) => {
      const idx = value.indexOf(token);
      if (idx === -1) return;
      const end = value.indexOf("}}", idx);
      const endAlt = value.indexOf("}", idx);
      const close = end === -1 ? endAlt : end;
      const tokenEnd = close === -1 ? Math.min(value.length, idx + 24) : close + 2;
      const item = value.slice(idx, tokenEnd).trim();
      if (item && !found.includes(item)) found.push(item);
    });
    return found;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      if (found.length >= 3) return found;
      findVariableTokens(item, found);
    }
    return found;
  }
  if (typeof value === "object") {
    for (const v of Object.values(value as Record<string, unknown>)) {
      if (found.length >= 3) return found;
      findVariableTokens(v, found);
    }
  }
  return found;
}

function collectVariableEvidence(result: TestResult): string[] {
  if (result.status !== "error" && result.status !== "failed") return [];
  const sources: unknown[] = [];
  if (result.error_message) sources.push(result.error_message);
  if (result.request_snapshot && typeof result.request_snapshot === "object") {
    const req = result.request_snapshot as Record<string, unknown>;
    if (typeof req.url === "string") sources.push(req.url);
    if (req.path) sources.push(req.path);
    if (req.body) sources.push(req.body);
  }
  const tokens: string[] = [];
  for (const source of sources) {
    findVariableTokens(source, tokens);
    if (tokens.length >= 3) break;
  }
  if (tokens.length === 0) {
    const text = (result.error_message ?? "").toLowerCase();
    if (text.includes("missing variable") || text.includes("unresolved variable")) {
      tokens.push("未解析变量");
    }
  }
  return tokens;
}

function countUniqueCases(
  resultIds: Set<string>,
  byResultId: Map<string, TestResult>,
): number {
  const caseIds = new Set<string>();
  for (const id of resultIds) {
    const result = byResultId.get(id);
    if (result) caseIds.add(result.test_case_id);
  }
  return caseIds.size;
}

export function analyzeFailures({
  results,
  failureItems,
}: FailureAnalysisInput): FailureAnalysisResult {
  const byResultId = new Map(results.map((result) => [result.id, result]));

  const categoryResultIds = {
    assertion: new Set<string>(),
    httpError: new Set<string>(),
    variable: new Set<string>(),
    timeout: new Set<string>(),
    network: new Set<string>(),
  } as Record<FailureCategoryKey, Set<string>>;

  for (const item of failureItems) {
    if (item.assertion_type !== "execution") {
      categoryResultIds.assertion.add(item.result_id);
    }
  }

  for (const result of results) {
    const errorCode = result.error_code ?? null;
    const httpStatus = responseStatusOf(result);
    if (isHttpErrorStatus(httpStatus)) {
      categoryResultIds.httpError.add(result.id);
    }
    if (isErrorResult(result)) {
      if (errorCode && TIMEOUT_CODES.has(errorCode)) {
        categoryResultIds.timeout.add(result.id);
      } else if (errorCode && NETWORK_CODES.has(errorCode)) {
        categoryResultIds.network.add(result.id);
      }
    }
    const variableTokens = collectVariableEvidence(result);
    if (variableTokens.length > 0) {
      categoryResultIds.variable.add(result.id);
    }
  }

  const buildCategory = (
    key: FailureCategoryKey,
    label: string,
    hint: string,
    hasEvidence: boolean,
  ): FailureCategorySummary => ({
    key,
    label,
    resultCount: categoryResultIds[key].size,
    caseCount: countUniqueCases(categoryResultIds[key], byResultId),
    hasEvidence,
    hint,
  });

  const categories: FailureCategorySummary[] = [
    buildCategory(
      "assertion",
      "Assertion Fail",
      "来自后端已扁平的失败断言",
      categoryResultIds.assertion.size > 0,
    ),
    buildCategory(
      "httpError",
      "HTTP Error",
      "Response Status >= 400",
      categoryResultIds.httpError.size > 0,
    ),
    buildCategory(
      "variable",
      "Variable Missing",
      "请求或错误信息中保留未解析变量",
      categoryResultIds.variable.size > 0,
    ),
    buildCategory(
      "timeout",
      "Timeout",
      "error_code = API_EXECUTION_TIMEOUT",
      categoryResultIds.timeout.size > 0,
    ),
    buildCategory(
      "network",
      "Network",
      "error_code = API_CONNECTION_ERROR",
      categoryResultIds.network.size > 0,
    ),
  ];

  return {
    totals: {
      failureItems: failureItems.length,
      caseCount: new Set(results.map((r) => r.test_case_id)).size,
    },
    categories,
    cases: results.filter(
      (r) =>
        isFailedResult(r) || isErrorResult(r) || categoryResultIds.httpError.has(r.id),
    ),
  };
}

export function resultStatusLabel(status: ResultStatus): string {
  switch (status) {
    case "passed":
      return "通过";
    case "failed":
      return "断言失败";
    case "error":
      return "执行错误";
    case "skipped":
      return "已跳过";
    default:
      return status;
  }
}

export function resultStatusColor(status: ResultStatus): string {
  switch (status) {
    case "passed":
      return "success";
    case "failed":
      return "error";
    case "error":
      return "volcano";
    case "skipped":
      return "default";
    default:
      return "default";
  }
}
