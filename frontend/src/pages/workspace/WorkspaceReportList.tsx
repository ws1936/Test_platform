import { ToolOutlined } from "@ant-design/icons";
import { EmptyState } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";

export default function WorkspaceReportList() {
  return (
    <>
      <PageHeader
        title="测试报告"
        description="查询历史、判断质量、定位失败"
        breadcrumbs={[
          { title: "Project 工作区", href: "../overview" },
          { title: "测试报告" },
        ]}
      />
      <EmptyState
        title="报告列表"
        description="报告列表将在 UI 重构第二期实现。"
        icon={<ToolOutlined style={{ fontSize: 48, color: "var(--color-warning)" }} />}
        compact
      />
    </>
  );
}