import {
  ApiOutlined,
  AppstoreOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FolderOpenOutlined,
  KeyOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlayCircleOutlined,
  ProjectOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  App,
  Avatar,
  Button,
  Dropdown,
  Layout,
  Menu,
  Select,
  Space,
  Tooltip,
  Typography,
  type MenuProps,
} from "antd";
import { Suspense, useMemo, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { authApi } from "../api/auth";
import { getErrorMessage } from "../api/client";
import { projectsApi } from "../api/projects";
import { queryKeys } from "../api/queryKeys";
import { useAuthStore } from "../store/auth";
import { LoadingBlock } from "./AsyncState";
import ChangePasswordModal from "./ChangePasswordModal";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

function getProjectId(pathname: string): string | null {
  const match = pathname.match(/^\/projects\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function selectedMenuKey(pathname: string, projectId: string | null): string {
  if (pathname.startsWith("/admin/users")) return "/admin/users";
  if (pathname.startsWith("/admin/roles")) return "/admin/roles";
  if (!projectId) {
    return pathname.startsWith("/projects") ? "/projects" : "/dashboard";
  }
  const base = `/projects/${projectId}`;
  const modules = ["environments", "suites", "cases", "runs", "reports", "settings"];
  const module = modules.find((name) => pathname.startsWith(`${base}/${name}`));
  return module ? `${base}/${module}` : `${base}/overview`;
}

function getProjectSwitchTarget(pathname: string, currentId: string, nextId: string): string {
  const suffix = pathname.slice(`/projects/${currentId}`.length);
  const module = suffix.match(/^\/(overview|environments|suites|cases|runs|reports|settings)/)?.[1];
  return `/projects/${nextId}/${module ?? "overview"}`;
}

export default function AppShell() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clear);
  const projectId = getProjectId(location.pathname);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects({ page: 1, size: 100, shell: true }),
    queryFn: () => projectsApi.list({ page: 1, size: 100 }),
    staleTime: 60_000,
  });
  const projectQuery = useQuery({
    queryKey: queryKeys.project(projectId ?? ""),
    queryFn: () => projectsApi.get(projectId ?? ""),
    enabled: Boolean(projectId),
  });

  const menuItems = useMemo<MenuProps["items"]>(() => {
    const items: MenuProps["items"] = [
      { key: "/dashboard", icon: <DashboardOutlined />, label: "工作台" },
      { key: "/projects", icon: <ProjectOutlined />, label: "项目列表" },
    ];

    if (projectId) {
      const base = `/projects/${projectId}`;
      items.push({ type: "divider" });
      items.push({
        type: "group",
        key: "project-workspace",
        label: collapsed ? "" : projectQuery.data?.name ?? "当前项目",
        children: [
          { key: `${base}/overview`, icon: <AppstoreOutlined />, label: "项目概览" },
          { key: `${base}/environments`, icon: <DatabaseOutlined />, label: "环境管理" },
          {
            key: "project-assets",
            icon: <FolderOpenOutlined />,
            label: "测试资产",
            children: [
              { key: `${base}/suites`, icon: <FolderOpenOutlined />, label: "测试套件" },
              { key: `${base}/cases`, icon: <ApiOutlined />, label: "API 用例" },
            ],
          },
          { key: `${base}/runs`, icon: <PlayCircleOutlined />, label: "执行中心" },
          { key: `${base}/reports`, icon: <FileSearchOutlined />, label: "测试报告" },
          { key: `${base}/settings`, icon: <SettingOutlined />, label: "项目设置" },
        ],
      });
    }

    if (user?.is_superuser) {
      items.push({ type: "divider" });
      items.push({
        type: "group",
        key: "admin",
        label: collapsed ? "" : "系统管理",
        children: [
          { key: "/admin/users", icon: <TeamOutlined />, label: "用户管理" },
          {
            key: "/admin/roles",
            icon: <SafetyCertificateOutlined />,
            label: "角色管理",
          },
        ],
      });
    }
    return items;
  }, [collapsed, projectId, projectQuery.data?.name, user?.is_superuser]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      message.warning(`服务端退出未确认：${getErrorMessage(error)}`);
    } finally {
      clearAuth();
      navigate("/login", { replace: true });
    }
  };

  const accountMenu: MenuProps = {
    items: [
      { key: "profile", icon: <UserOutlined />, label: user?.email ?? "当前账号", disabled: true },
      { key: "password", icon: <KeyOutlined />, label: "修改密码" },
      { type: "divider" },
      { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true },
    ],
    onClick: ({ key }) => {
      if (key === "password") setPasswordOpen(true);
      if (key === "logout") void handleLogout();
    },
  };

  return (
    <Layout className="app-layout">
      <Sider
        theme="light"
        width={248}
        collapsedWidth={72}
        collapsible
        trigger={null}
        collapsed={collapsed}
        className="app-sider"
      >
        <button className="brand" type="button" onClick={() => navigate("/dashboard")}>
          <span className="brand-mark"><ApiOutlined /></span>
          {!collapsed ? <span className="brand-name">API Test Hub</span> : null}
        </button>
        {projectId && !collapsed ? (
          <div className="project-switcher">
            <Text type="secondary" className="project-switcher-label">当前项目</Text>
            <Select
              value={projectId}
              loading={projectsQuery.isLoading}
              status={projectsQuery.isError ? "error" : undefined}
              showSearch
              optionFilterProp="label"
              options={(projectsQuery.data?.items ?? []).map((project) => ({
                value: project.id,
                label: project.name,
              }))}
              onChange={(nextId) =>
                navigate(getProjectSwitchTarget(location.pathname, projectId, nextId))
              }
              className="project-switcher-select"
              aria-label="切换项目"
            />
          </div>
        ) : null}
        <Menu
          mode="inline"
          items={menuItems}
          selectedKeys={[selectedMenuKey(location.pathname, projectId)]}
          defaultOpenKeys={["project-assets"]}
          onClick={({ key }) => {
            if (key.startsWith("/")) navigate(key);
          }}
          className="app-menu"
        />
        <Tooltip title={collapsed ? "展开菜单" : "收起菜单"} placement="right">
          <Button
            type="text"
            className="collapse-button"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? "展开菜单" : "收起菜单"}
          />
        </Tooltip>
      </Sider>
      <Layout>
        <Header className="app-header">
          <div />
          <Dropdown menu={accountMenu} placement="bottomRight" trigger={["click"]}>
            <button type="button" className="account-button">
              <Space>
                <Avatar size="small" icon={<UserOutlined />} />
                <span className="account-name">{user?.nickname || user?.username}</span>
              </Space>
            </button>
          </Dropdown>
        </Header>
        <Content className="app-content">
          <Suspense fallback={<LoadingBlock rows={6} />}>
            <Outlet />
          </Suspense>
        </Content>
      </Layout>
      <ChangePasswordModal open={passwordOpen} onClose={() => setPasswordOpen(false)} />
    </Layout>
  );
}
