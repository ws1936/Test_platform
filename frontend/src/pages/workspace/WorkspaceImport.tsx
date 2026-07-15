import { ToolOutlined } from "@ant-design/icons";
import { EmptyState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";

export default function WorkspaceImport() {
  return (
    <>
      <PageHeader
        title="导入 OpenAPI"
        description="从 OpenAPI 3.x 文档批量创建 API Case"
        breadcrumbs={[
          { title: "Project 工作区", href: "../overview" },
          { title: "导入 OpenAPI" },
        ]}
      />
      <EmptyState
        title="OpenAPI 导入向导"
        description="OpenAPI 导入向导将在 UI 重构第二期实现。"
        icon={<ToolOutlined style={{ fontSize: 48, color: "var(--color-warning)" }} />}
        compact
      />
    </>
  );
}