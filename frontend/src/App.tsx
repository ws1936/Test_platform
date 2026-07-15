import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import { AdminRoute, ProtectedRoute } from "./components/RouteGuards";
import ProjectWorkspaceLayout from "./components/workspace/ProjectWorkspaceLayout";
import LoginPage from "./pages/Login";
import SystemResultPage from "./pages/SystemResult";
import WorkspaceCaseEditor from "./pages/workspace/WorkspaceCaseEditor";
import WorkspaceCaseList from "./pages/workspace/WorkspaceCaseList";
import WorkspaceEnvironment from "./pages/workspace/WorkspaceEnvironment";
import WorkspaceImport from "./pages/workspace/WorkspaceImport";
import WorkspaceInformation from "./pages/workspace/WorkspaceInformation";
import WorkspaceOverview from "./pages/workspace/WorkspaceOverview";
import WorkspaceReportDetail from "./pages/workspace/WorkspaceReportDetail";
import WorkspaceReportList from "./pages/workspace/WorkspaceReportList";
import WorkspaceResultDetail from "./pages/workspace/WorkspaceResultDetail";
import WorkspaceRun from "./pages/workspace/WorkspaceRun";
import WorkspaceSuiteDetail from "./pages/workspace/WorkspaceSuiteDetail";
import WorkspaceSuiteList from "./pages/workspace/WorkspaceSuiteList";

const DashboardPage = lazy(() => import("./pages/Dashboard"));
const ProjectsPage = lazy(() => import("./pages/Projects"));
const RolesPage = lazy(() => import("./pages/admin/Roles"));
const UsersPage = lazy(() => import("./pages/admin/Users"));
const ProjectSettingsLegacyPage = WorkspaceInformation;

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />

        <Route path="projects/:projectId" element={<Navigate to="workspace/overview" replace />} />
        <Route path="projects/:projectId/overview" element={<Navigate to="workspace/overview" replace />} />

        <Route path="projects/:projectId/environments" element={<Navigate to="workspace/environment" replace />} />
        <Route path="projects/:projectId/suites" element={<Navigate to="workspace/suite" replace />} />
        <Route path="projects/:projectId/suites/:suiteId" element={<Navigate to={`workspace/suite/${undefined}`} replace />} />
        <Route
          path="projects/:projectId/suites/:suiteId/import/openapi"
          element={<Navigate to="../import" replace />}
        />
        <Route path="projects/:projectId/cases" element={<Navigate to="workspace/case" replace />} />
        <Route path="projects/:projectId/cases/new" element={<Navigate to="workspace/case/new" replace />} />
        <Route path="projects/:projectId/cases/:caseId" element={<Navigate to="workspace/case" replace />} />
        <Route path="projects/:projectId/runs" element={<Navigate to="workspace/run" replace />} />
        <Route path="projects/:projectId/reports" element={<Navigate to="workspace/report" replace />} />
        <Route
          path="projects/:projectId/reports/:runId"
          element={<Navigate to="../report" replace />}
        />
        <Route
          path="projects/:projectId/reports/:runId/results/:resultId"
          element={<Navigate to="../report" replace />}
        />
        <Route
          path="projects/:projectId/settings"
          element={<ProjectSettingsLegacyPage />}
        />

        <Route path="projects/:projectId/workspace" element={<ProjectWorkspaceLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<WorkspaceOverview />} />
          <Route path="environment" element={<WorkspaceEnvironment />} />
          <Route path="suite" element={<WorkspaceSuiteList />} />
          <Route path="suite/:suiteId" element={<WorkspaceSuiteDetail />} />
          <Route path="case" element={<WorkspaceCaseList />} />
          <Route path="case/new" element={<WorkspaceCaseEditor />} />
          <Route path="case/:caseId" element={<WorkspaceCaseEditor />} />
          <Route path="run" element={<WorkspaceRun />} />
          <Route path="report" element={<WorkspaceReportList />} />
          <Route path="report/:runId" element={<WorkspaceReportDetail />} />
          <Route path="report/:runId/result/:resultId" element={<WorkspaceResultDetail />} />
          <Route path="import/:suiteId" element={<WorkspaceImport />} />
          <Route path="information" element={<WorkspaceInformation />} />
        </Route>

        <Route
          path="admin/users"
          element={
            <AdminRoute>
              <UsersPage />
            </AdminRoute>
          }
        />
        <Route
          path="admin/roles"
          element={
            <AdminRoute>
              <RolesPage />
            </AdminRoute>
          }
        />
        <Route path="403" element={<SystemResultPage status="403" />} />
        <Route path="*" element={<SystemResultPage status="404" />} />
      </Route>
    </Routes>
  );
}
