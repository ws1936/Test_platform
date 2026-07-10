import { Form, Input, Button, Card, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";

const { Title } = Typography;

interface LoginValues {
  email: string;
  password: string;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const onFinish = async (values: LoginValues) => {
    try {
      const resp = await api.post("/auth/login", values);
      const { access_token, refresh_token } = resp.data.token;
      localStorage.setItem("refresh_token", refresh_token);
      setAuth(access_token, resp.data.user);
      message.success("登录成功");
      navigate("/");
    } catch (err: any) {
      message.error(err?.response?.data?.message ?? "登录失败");
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f0f2f5",
      }}
    >
      <Card style={{ width: 380 }}>
        <Title level={3} style={{ textAlign: "center" }}>
          自动化测试平台
        </Title>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item
            label="邮箱"
            name="email"
            rules={[{ required: true, type: "email", message: "请输入有效邮箱" }]}
          >
            <Input placeholder="user@example.com" />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, min: 8, message: "密码至少 8 位" }]}
          >
            <Input.Password placeholder="******" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
