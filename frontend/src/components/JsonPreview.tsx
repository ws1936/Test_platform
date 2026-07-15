import { Empty, Typography } from "antd";
import type { CSSProperties } from "react";
import { stringifyJson } from "../utils/json";

/**
 * JSON 预览
 * @see docs/02-design/ComponentLibrary.md §12.6
 */
export interface JsonPreviewProps {
  /** 要展示的 JSON 数据 */
  value: unknown;
  /** 空值文案 */
  emptyText?: string;
  /** 最大高度（默认 480） */
  maxHeight?: number;
  /** 是否显示复制按钮 */
  copyable?: boolean;
  className?: string;
  style?: CSSProperties;
  testId?: string;
}

export default function JsonPreview({
  value,
  emptyText = "暂无数据",
  maxHeight = 480,
  copyable = true,
  className,
  style,
  testId,
}: JsonPreviewProps) {
  if (value === null || value === undefined) {
    return (
      <div data-testid={testId}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />
      </div>
    );
  }

  const text = stringifyJson(value, "");
  return (
    <Typography.Paragraph
      className={["json-preview", className].filter(Boolean).join(" ")}
      style={{ maxHeight, ...style }}
      copyable={copyable ? { text } : false}
      data-testid={testId}
    >
      <pre>{text}</pre>
    </Typography.Paragraph>
  );
}