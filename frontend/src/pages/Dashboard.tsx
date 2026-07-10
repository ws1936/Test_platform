import { Layout, Menu, Avatar, Dropdown, Typography, Card, Space } from "antd";
import {
  UserOutlined,
  LogoutOutlined,
  DashboardOutlined,
  ProjectOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { api } from "../api/client";

const { Header, Content, Sider } = Layout;
const { Text } = Typography;

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);

  const onLogout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore network errors on logout */
    }
    clear();
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          background: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
        }}
      >
        <Text strong style={{ fontSize: 18 }}>
          自动化测试平台
        </Text>
        <Dropdown
          menu={{
            items: [
              {
                key: "logout",
                icon: <LogoutOutlined />,
                label: "退出登录",
                onClick: onLogout,
              },
            ],
          }}
        >
          <Space style={{ cursor: "pointer" }}>
            <Avatar icon={<UserOutlined />} />
            <Text>{user?.username}</Text>
          </Space>
        </Dropdown>
      </Header>
      <Layout>
        <Sider width={220} theme="light">
          <Menu
            mode="inline"
            defaultSelectedKeys={["dashboard"]}
            items={[
              { key: "dashboard", icon: <DashboardOutlined />, label: "概览" },
              { key: "projects", icon: <ProjectOutlined />, label: "项目" },
              { key: "users", icon: <UserOutlined />, label: "用户管理" },
            ]}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          <Card title="欢迎">
            <p>你好，{user?.username}。这里是仪表盘（占位页面）。</p>
            <p>邮箱：{user?.email}</p>
          </Card>
        </Content>
      </Layout>
    </Layout>
  );
}
