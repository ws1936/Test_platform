// 统一 Report Center 的 Card / Empty / Loading / Error 状态。

import { ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Empty, Skeleton, Space, Typography } from "antd";
import type { CSSProperties, ReactNode } from "react";
import { Link } from "react-router-dom";

const { Text } = Typography;

/**
 * 统一 Report Card 容器
 * - 保留 surface-card class 以继承 Design System。
 * - 内部居中布局，承载 Title / Value / Hint / Action。
 */
export interface ReportCardProps {
  title: ReactNode;
  value?: ReactNode;
  hint?: ReactNode;
  action?: ReactNode;
  loading?: boolean;
  className?: string;
  style?: CSSProperties;
  bodyStyle?: CSSProperties;
  children?: ReactNode;
}

export function ReportCard({
  title,
  value,
  hint,
  action,
  loading = false,
  className,
  style,
  bodyStyle,
  children,
}: ReportCardProps) {
  return (
    <Card
      className={["report-card", className].filter(Boolean).join(" ")}
      style={style}
      bodyStyle={bodyStyle}
      loading={loading}
    >
      <Space direction="vertical" size={8} style={{ width: "100%" }}>
        {typeof title === "string" ? (
          <Text type="secondary" className="report-card-title">
            {title}
          </Text>
        ) : (
          title
        )}
        {value !== undefined ? (
          <Typography.Title level={3} className="report-card-value">
            {value}
          </Typography.Title>
        ) : null}
        {hint ? <Text type="secondary" className="report-card-hint">{hint}</Text> : null}
        {children}
        {action ? <div className="report-card-action">{action}</div> : null}
      </Space>
    </Card>
  );
}

/**
 * Report 专用轻量 Loading：使用 AntD Skeleton 卡片骨架，避免与 LoadingBlock 重复。
 */
export interface ReportSkeletonProps {
  count?: number;
  className?: string;
  style?: CSSProperties;
}

export function ReportSkeleton({ count = 4, className, style }: ReportSkeletonProps) {
  const cards = Array.from({ length: count }, (_, i) => i);
  return (
    <Space size={[16, 16]} wrap className={className} style={style}>
      {cards.map((i) => (
        <Card key={i} className="report-card report-card--skeleton" style={{ width: 220 }}>
          <Skeleton active paragraph={{ rows: 2 }} title={false} />
        </Card>
      ))}
    </Space>
  );
}

/**
 * Report 通用 Empty：统一的空态展示。
 */
export interface ReportEmptyProps {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export function ReportEmpty({
  title,
  description,
  action,
  icon,
  className,
  style,
}: ReportEmptyProps) {
  return (
    <div
      className={["report-empty", className].filter(Boolean).join(" ")}
      style={style}
      role="region"
      aria-label="Report 空状态"
    >
      <Empty
        image={icon ?? Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={6} align="center">
            <Text strong>{title}</Text>
            {description ? <Text type="secondary">{description}</Text> : null}
            {action}
          </Space>
        }
      />
    </div>
  );
}

/**
 * Report 通用 Error：提供错误描述 + 重试 + 上下文返回。
 */
export interface ReportErrorProps {
  error: unknown;
  onRetry?: () => void;
  onBack?: () => void;
  title?: string;
  className?: string;
  style?: CSSProperties;
}

export function ReportError({
  error,
  onRetry,
  onBack,
  title = "Report 加载失败",
  className,
  style,
}: ReportErrorProps) {
  const message = readErrorMessage(error);
  return (
    <div
      className={["report-error", className].filter(Boolean).join(" ")}
      style={style}
      role="alert"
    >
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={6} align="center">
            <Text strong>{title}</Text>
            <Text type="secondary">{message}</Text>
            <Space>
              {onRetry ? (
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={onRetry}
                >
                  重试
                </Button>
              ) : null}
              {onBack ? <Button onClick={onBack}>返回</Button> : null}
            </Space>
          </Space>
        }
      />
    </div>
  );
}

function readErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error) {
    const value = (error as { message?: unknown }).message;
    if (typeof value === "string") return value;
  }
  return "未知错误";
}

/**
 * 通用快捷链接：用于 Card Action。
 */
export interface ReportLinkActionProps {
  to: string;
  label: ReactNode;
  className?: string;
}

export function ReportLinkAction({ to, label, className }: ReportLinkActionProps) {
  return (
    <Link to={to} className={["report-link", className].filter(Boolean).join(" ")}>
      {label}
    </Link>
  );
}
