import type { Suite, TestRun } from "../api/types";

const DASHBOARD_ITEM_LIMIT = 5;

export interface DashboardRunData {
  recentRuns: TestRun[];
  recentReports: TestRun[];
  completedCount: number;
  successfulCount: number;
  successRate: number | null;
  todayCount: number;
  todayDisplay: string;
  todayIsExact: boolean;
}

function startOfLocalDay(now: Date): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

export function deriveDashboardRunData(
  runs: TestRun[],
  total: number,
  now = new Date(),
): DashboardRunData {
  const sortedRuns = [...runs].sort(
    (left, right) =>
      new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
  const completedRuns = sortedRuns.filter(
    (run) => run.status === "finished" || run.status === "failed",
  );
  const successfulRuns = completedRuns.filter(
    (run) => run.status === "finished" && run.failed === 0 && run.error === 0,
  );
  const start = startOfLocalDay(now).getTime();
  const todayRuns = sortedRuns.filter(
    (run) => new Date(run.created_at).getTime() >= start,
  );
  const oldestLoaded = sortedRuns[sortedRuns.length - 1];
  const crossedDayBoundary =
    oldestLoaded !== undefined && new Date(oldestLoaded.created_at).getTime() < start;
  const todayIsExact = total <= sortedRuns.length || crossedDayBoundary;

  return {
    recentRuns: sortedRuns.slice(0, DASHBOARD_ITEM_LIMIT),
    recentReports: completedRuns.slice(0, DASHBOARD_ITEM_LIMIT),
    completedCount: completedRuns.length,
    successfulCount: successfulRuns.length,
    successRate:
      completedRuns.length > 0 ? successfulRuns.length / completedRuns.length : null,
    todayCount: todayRuns.length,
    todayDisplay: todayIsExact ? String(todayRuns.length) : `${todayRuns.length}+`,
    todayIsExact,
  };
}

export function getRecentSuites(suites: Suite[]): Suite[] {
  return [...suites]
    .sort(
      (left, right) =>
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
    )
    .slice(0, DASHBOARD_ITEM_LIMIT);
}
