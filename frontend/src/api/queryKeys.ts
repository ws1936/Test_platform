export const queryKeys = {
  me: ["auth", "me"] as const,
  projects: (params?: object) => ["projects", params ?? {}] as const,
  project: (projectId: string) => ["projects", projectId] as const,
  environments: (projectId: string, search = "") =>
    ["projects", projectId, "environments", search] as const,
  environment: (environmentId: string) => ["environments", environmentId] as const,
  suites: (projectId: string, search = "") =>
    ["projects", projectId, "suites", search] as const,
  suite: (projectId: string, suiteId: string) =>
    ["projects", projectId, "suites", suiteId] as const,
  suiteCases: (suiteId: string) => ["suites", suiteId, "cases"] as const,
  cases: (projectId: string, search = "") =>
    ["projects", projectId, "cases", search] as const,
  testCase: (caseId: string) => ["test-cases", caseId] as const,
  runs: (projectId: string, params?: object) =>
    ["projects", projectId, "runs", params ?? {}] as const,
  projectRunSummary: (projectId: string) =>
    ["projects", projectId, "runs", "summary"] as const,
  run: (runId: string) => ["runs", runId] as const,
  runSummary: (runId: string) => ["runs", runId, "summary"] as const,
  runResults: (runId: string) => ["runs", runId, "results"] as const,
  runFailures: (runId: string) => ["runs", runId, "failures"] as const,
  result: (resultId: string) => ["results", resultId] as const,
  users: (params?: object) => ["users", params ?? {}] as const,
  user: (userId: string) => ["users", userId] as const,
  roles: ["roles"] as const,
  role: (roleId: string) => ["roles", roleId] as const,
};
