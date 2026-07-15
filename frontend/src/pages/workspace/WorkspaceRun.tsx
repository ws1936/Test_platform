import { ToolOutlined } from "@ant-design/icons";
import { EmptyState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";

export default function WorkspaceRun() {
  return (
    <>
      <PageHeader
        title="执行中心"
        description="选择范围 / 环境，发起 Run"
        breadcrumbs={[
          { title: "Project 工作区", href: "../overview" },
          { title: "执行中心" },
        ]}
      />
      <EmptyState
        title="执行配置"
        description="执行中心页面将在 UI 重构第二期实现。当前可使用 Workspace Header 的「快速执行」按钮。"
        icon={<ToolOutlined style={{ fontSize: 48, color: "var(--color-warning)" }} />}
        compact
      />
    </>
  );
}