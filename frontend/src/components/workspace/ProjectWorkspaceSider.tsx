import {
  ApiOutlined,
  AppstoreOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FolderOpenOutlined,
  ImportOutlined,
  PlayCircleOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { Menu, type MenuProps } from "antd";
import { useLocation, useNavigate } from "react-router-dom";
import type { ProjectWorkspaceReadiness } from "./projectWorkspaceContext";
import { useProjectWorkspace } from "./projectWorkspaceContext";

interface ProjectWorkspaceSiderProps {
  projectId: string;
}

const MODULES: Array<{
  key: string;
  label: string;
  icon: React.ReactNode;
  flag: keyof ProjectWorkspaceReadiness | "always";
}> = [
  { key: "overview", label: "概览", icon: <AppstoreOutlined />, flag: "always" },
  { key: "environment", label: "环境", icon: <DatabaseOutlined />, flag: "hasEnvironment" },
  { key: "suite", label: "套件", icon: <FolderOpenOutlined />, flag: "hasSuite" },
  { key: "case", label: "用例", icon: <ApiOutlined />, flag: "hasCase" },
  { key: "run", label: "执行", icon: <PlayCircleOutlined />, flag: "hasEnvironment" },
  { key: "report", label: "报告", icon: <FileSearchOutlined />, flag: "hasRun" },
  { key: "import", label: "导入", icon: <ImportOutlined />, flag: "hasSuite" },
  { key: "information", label: "信息", icon: <SettingOutlined />, flag: "always" },
];

export default function ProjectWorkspaceSider({ projectId }: ProjectWorkspaceSiderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { readiness } = useProjectWorkspace();

  const basePath = `/projects/${projectId}/workspace`;
  const moduleKey = location.pathname.startsWith(basePath)
    ? location.pathname.slice(basePath.length).split("/").filter(Boolean)[0] ?? "overview"
    : "";

  const items: MenuProps["items"] = MODULES.map((module) => {
    const isReady = module.flag === "always" || readiness[module.flag];
    return {
      key: module.key,
      icon: module.icon,
      label: (
        <span>
          {module.label}
          {!isReady ? <span className="workspace-sider-flag">·</span> : null}
        </span>
      ),
    };
  });

  return (
    <aside className="workspace-sider">
      <div className="workspace-sider-title">项目工作区</div>
      <Menu
        mode="inline"
        selectedKeys={[moduleKey]}
        items={items}
        onClick={({ key }) => {
          navigate(`${basePath}/${key}`);
        }}
        className="workspace-sider-menu"
      />
    </aside>
  );
}
