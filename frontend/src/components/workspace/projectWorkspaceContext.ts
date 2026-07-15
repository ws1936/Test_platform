import { createContext, useContext } from "react";
import type { Project, TestRun } from "../../api/types";

export interface ProjectWorkspaceReadiness {
  hasEnvironment: boolean;
  hasDefaultEnvironment: boolean;
  hasSuite: boolean;
  hasCase: boolean;
  hasRun: boolean;
  hasSuccessfulRun: boolean;
}

export interface ProjectWorkspaceContextValue {
  projectId: string;
  project: Project | null;
  latestRun: TestRun | null;
  defaultEnvironmentId: string | null;
  readiness: ProjectWorkspaceReadiness;
  isReady: boolean;
  refresh: () => void;
}

export const ProjectWorkspaceContext = createContext<ProjectWorkspaceContextValue | null>(null);

export function useProjectWorkspace(): ProjectWorkspaceContextValue {
  const context = useContext(ProjectWorkspaceContext);
  if (!context) {
    throw new Error("useProjectWorkspace 必须在 ProjectWorkspaceLayout 内部使用");
  }
  return context;
}
