import { ToolOutlined } from "@ant-design/icons";
import { EmptyState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";

export default function WorkspaceInformation() {
  return (
    <>
      <PageHeader
        title="项目信息"
        description="查看 Project 基本信息、修改名称 / 描述、删除 Project"
        breadcrumbs={[
          { title: "Project 工作区", href: "../overview" },
          { title: "项目信息" },
        ]}
      />
      <EmptyState
        title="项目设置"
        description="项目设置（修改信息 / 删除 Project）将在 UI 重构第二期实现。"
        icon={<ToolOutlined style={{ fontSize: 48, color: "var(--color-warning)" }} />}
        compact
      />
    </>
  );
}