import { ToolOutlined } from "@ant-design/icons";
import { useParams } from "react-router-dom";
import { EmptyState } from "../../components/AsyncState";

/**
 * Workspace Case Editor 占位页
 *
 * 历史说明：原实现重定向到旧 pages/project/CaseEditor，该文件已被清理。
 * 当前为路由占位，UI 重构后业务实现将在 P2 阶段补齐。
 */
export default function WorkspaceCaseEditor() {
  const { caseId } = useParams();
  const isNew = !caseId;
  return (
    <EmptyState
      title={isNew ? "新建 API Case" : "编辑 API Case"}
      description={
        isNew
          ? "Case 编辑器将在 UI 重构第二期实现。当前可使用 Case 列表页查看已有数据。"
          : `Case ID: ${caseId}（${caseId}）的详情将在第二期实现。`
      }
      icon={<ToolOutlined style={{ fontSize: 48, color: "var(--color-warning)" }} />}
      compact
    />
  );
}