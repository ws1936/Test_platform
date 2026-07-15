import { Button, Result } from "antd";
import { useNavigate } from "react-router-dom";

interface SystemResultProps {
  status: "403" | "404";
}

export default function SystemResultPage({ status }: SystemResultProps) {
  const navigate = useNavigate();
  const forbidden = status === "403";
  return (
    <Result
      status={status}
      title={status}
      subTitle={forbidden ? "你没有访问此页面的权限。" : "你访问的页面不存在或已被删除。"}
      extra={
        <Button type="primary" onClick={() => navigate("/dashboard", { replace: true })}>
          返回工作台
        </Button>
      }
    />
  );
}
