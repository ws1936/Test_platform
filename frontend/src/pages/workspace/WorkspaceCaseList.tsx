import { ToolOutlined } from "@ant-design/icons";
import { EmptyState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";

export default function WorkspaceCaseList() {
  return (
    <>
      <PageHeader
        title="API 用例"
        description="管理当前 Project 的所有 API 用例"
        breadcrumbs={[
          { title: "Project 工作区", href: "../overview" },
          { title: "API 用例" },
        ]}
      />
      <EmptyState
        title="API 用例列表"
        description="Case 列表将在 UI 重构第二期实现。当前可通过后端 API 查询。"
        icon={<ToolOutlined style={{ fontSize: 48, color: "var(--color-warning)" }} />}
        compact
      />
    </>
  );
}