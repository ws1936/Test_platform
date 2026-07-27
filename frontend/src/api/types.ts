export type UUID = string;

export interface User {
  id: UUID;
  username: string;
  email: string;
  nickname: string | null;
  phone: string | null;
  status: number;
  role_id: UUID | null;
  is_superuser: boolean;
  last_login_time: string | null;
  created_at: string;
  updated_at: string;
}

export interface PublicUser {
  id: UUID;
  username: string;
  email: string;
  nickname: string | null;
  phone: string | null;
  last_login_time: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  user: PublicUser;
  token: TokenPair;
}

export interface Role {
  id: UUID;
  name: string;
  description: string | null;
  permissions: string[] | null;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: UUID;
  name: string;
  description: string | null;
  owner_id: UUID;
  created_at: string;
  updated_at: string;
}

export interface ProjectList {
  items: Project[];
  total: number;
  page: number;
  size: number;
}

export interface ProjectPayload {
  name: string;
  description?: string | null;
}

export interface Environment {
  id: UUID;
  project_id: UUID;
  name: string;
  base_url: string;
  headers: Record<string, unknown> | null;
  variables: Record<string, unknown> | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface EnvironmentList {
  items: Environment[];
  total: number;
}

export interface EnvironmentPayload {
  name: string;
  base_url: string;
  headers?: Record<string, unknown> | null;
  variables?: Record<string, unknown> | null;
  is_default?: boolean;
}

export interface Suite {
  id: UUID;
  project_id: UUID;
  name: string;
  description: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface SuiteCaseLink {
  id: UUID;
  suite_id: UUID;
  test_case_id: UUID;
  case_id: UUID;
  order: number;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface SuiteDetail extends Suite {
  cases: SuiteCaseLink[];
}

export interface SuiteList {
  items: Suite[];
  total: number;
}

export interface SuitePayload {
  name: string;
  description?: string | null;
}

export interface SuiteBulkResult {
  added: SuiteCaseLink[];
  already_present: UUID[];
}

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
export type BodyType = "none" | "json" | "form" | "raw";

export interface TestCase {
  id: UUID;
  project_id: UUID;
  name: string;
  method: HttpMethod;
  path: string;
  headers: Record<string, unknown> | null;
  query_params: Record<string, unknown> | null;
  body_type: BodyType;
  body: unknown;
  assertions: Record<string, unknown>[] | null;
  timeout_seconds: number;
  sort_order: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface TestCaseList {
  items: TestCase[];
  total: number;
}

export interface TestCasePayload {
  name: string;
  method: HttpMethod;
  path: string;
  headers?: Record<string, unknown> | null;
  query_params?: Record<string, unknown> | null;
  body_type: BodyType;
  body?: unknown;
  assertions?: Record<string, unknown>[] | null;
  timeout_seconds: number;
  enabled: boolean;
}

export type RunScope = "case" | "collection" | "project";
export type RunStatus = "pending" | "running" | "finished" | "failed" | "canceled";
export type ResultStatus = "passed" | "failed" | "skipped" | "error";

export interface TestRun {
  id: UUID;
  project_id: UUID;
  environment_id: UUID;
  name: string;
  scope: RunScope;
  scope_id: UUID | null;
  status: RunStatus;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  error: number;
  started_at: string | null;
  finished_at: string | null;
  triggered_by: UUID | null;
  created_at: string;
  updated_at: string;
  pass_rate: number | null;
  elapsed_seconds: number | null;
}

export interface TestRunList {
  items: TestRun[];
  total: number;
}

export interface TestRunPayload {
  name?: string;
  environment_id: UUID;
  scope: RunScope;
  scope_id: UUID;
}

export interface RunSummary {
  run_id: UUID;
  name: string;
  scope: RunScope;
  scope_id: UUID | null;
  status: RunStatus;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  error: number;
  pass_rate: number | null;
  elapsed_seconds: number | null;
  started_at: string | null;
  finished_at: string | null;
  environment_id: UUID;
}

export interface ProjectRunSummary {
  project_id: UUID;
  total_runs: number;
  total_cases: number;
  total_passed: number;
  total_failed: number;
  total_error: number;
  overall_pass_rate: number | null;
  last_run_at: string | null;
  recent_runs: RunSummary[];
  recent_limit: number;
}

export interface TestResult {
  id: UUID;
  run_id: UUID;
  test_case_id: UUID;
  case_name: string;
  case_method: HttpMethod;
  case_path: string;
  environment_id: UUID;
  status: ResultStatus;
  request_snapshot: Record<string, unknown> | null;
  response_snapshot: Record<string, unknown> | null;
  elapsed_ms: number | null;
  assertions_snapshot: Record<string, unknown>[] | null;
  error_message: string | null;
  error_code: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface TestResultList {
  items: TestResult[];
  total: number;
}

export interface FailureItem {
  result_id: UUID;
  run_id: UUID;
  test_case_id: UUID;
  case_name: string;
  case_method: HttpMethod;
  case_path: string;
  started_at: string | null;
  finished_at: string | null;
  failure_index: number;
  assertion_type: string;
  assertion_operator: string;
  expected: unknown;
  actual: unknown;
  message: string;
  error_code: string | null;
  error_message: string | null;
}

export interface FailureList {
  run_id: UUID;
  total_failures: number;
  items: FailureItem[];
}

export interface OperationPreview {
  operation_id: string | null;
  method: HttpMethod;
  path: string;
  name: string;
  status: string;
}

export interface ImportPreview {
  preview_id: string;
  spec_version: string;
  suite_id: UUID;
  suite_name: string;
  base_path: string;
  total: number;
  new_count: number;
  existing_count: number;
  skipped_count: number;
  operations: OperationPreview[];
  errors: string[];
}

export interface ImportResult {
  created: string[];
  skipped: string[];
  overwritten: string[];
  errors: string[];
  total_attempted: number;
  total_succeeded: number;
}

export interface OpenApiSourcePayload {
  source_url?: string;
  source_content?: Record<string, unknown>;
  tags?: string[];
  on_conflict?: "skip" | "overwrite";
  dry_run?: boolean;
  name_prefix?: string;
}

export interface UserList {
  items: User[];
  total: number;
  page: number;
  size: number;
}

export interface CreateUserPayload {
  username: string;
  email: string;
  password: string;
  nickname?: string;
  phone?: string;
}

export interface UpdateUserPayload {
  nickname?: string | null;
  phone?: string | null;
  status?: number;
  role_id?: UUID | null;
  is_superuser?: boolean;
}

export interface RolePayload {
  name: string;
  description?: string | null;
  permissions?: string[] | null;
}

export interface MessageResponse {
  message: string;
}
