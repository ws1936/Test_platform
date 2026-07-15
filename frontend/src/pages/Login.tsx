import { ApiOutlined, LockOutlined, MailOutlined } from "@ant-design/icons";
import { useMutation } from "@tanstack/react-query";
import { Alert, App, Button, Card, Form, Input, Typography } from "antd";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { authApi, type LoginPayload } from "../api/auth";
import { getErrorMessage } from "../api/client";
import { useAuthStore } from "../store/auth";

const { Title, Text } = Typography;

function safeReturnPath(value: string | null | undefined): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/dashboard";
}

export default function LoginPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const setTokens = useAuthStore((state) => state.setTokens);
  const setUser = useAuthStore((state) => state.setUser);
  const clear = useAuthStore((state) => state.clear);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginPayload>();

  const target = useMemo(() => {
    const state = location.state as { from?: string } | null;
    return safeReturnPath(searchParams.get("from") ?? state?.from);
  }, [location.state, searchParams]);

  const loginMutation = useMutation({
    mutationFn: async (values: LoginPayload) => {
      const login = await authApi.login(values);
      setTokens(login.token.access_token, login.token.refresh_token);
      try {
        const user = await authApi.me();
        setUser(user);
        return user;
      } catch (error) {
        clear();
        throw error;
      }
    },
    onSuccess: () => {
      message.success("登录成功");
      navigate(target, { replace: true });
    },
  });

  return (
    <main className="login-page">
      <section className="login-visual" aria-label="产品介绍">
        <div className="login-visual-content">
          <span className="login-eyebrow"><ApiOutlined /> API AUTOMATION PLATFORM</span>
          <h1 className="login-heading">让每一次 API 回归，都清晰可追溯。</h1>
          <p className="login-copy">
            在统一工作区中管理环境、测试套件与 API 用例，发起可靠执行，并从请求、响应和断言快照快速定位失败。
          </p>
        </div>
      </section>
      <section className="login-form-panel">
        <Card className="login-card">
          <Title level={2} className="login-title">欢迎回来</Title>
          <Text type="secondary" className="login-subtitle">使用平台账号登录 API Test Hub</Text>
          {loginMutation.isError ? (
            <Alert
              className="inline-warning"
              type="error"
              showIcon
              message="登录失败"
              description={getErrorMessage(loginMutation.error, "邮箱或密码不正确")}
            />
          ) : null}
          <form onSubmit={handleSubmit((values) => loginMutation.mutate(values))}>
            <Form.Item
              label="邮箱"
              validateStatus={errors.email ? "error" : undefined}
              help={errors.email?.message}
            >
              <Input
                size="large"
                prefix={<MailOutlined />}
                placeholder="user@example.com"
                autoComplete="email"
                {...register("email", {
                  required: "请输入邮箱",
                  pattern: { value: /^\S+@\S+\.\S+$/, message: "请输入有效邮箱" },
                })}
              />
            </Form.Item>
            <Form.Item
              label="密码"
              validateStatus={errors.password ? "error" : undefined}
              help={errors.password?.message}
            >
              <Input.Password
                size="large"
                prefix={<LockOutlined />}
                placeholder="请输入密码"
                autoComplete="current-password"
                {...register("password", { required: "请输入密码" })}
              />
            </Form.Item>
            <Button
              type="primary"
              size="large"
              htmlType="submit"
              block
              loading={loginMutation.isPending}
            >
              登录
            </Button>
          </form>
        </Card>
      </section>
    </main>
  );
}
