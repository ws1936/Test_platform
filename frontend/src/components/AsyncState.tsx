import { ReloadOutlined } from "@ant-design/icons";
import { Button, Empty, Result, Skeleton, Space, Spin, Typography } from "antd";
import type { CSSProperties, ReactNode } from "react";
import { getErrorMessage, getHttpStatus } from "../api/client";

/**
 * Loading 状态
 * @see docs/02-design/ComponentLibrary.md §9.2
 */
export interface LoadingBlockProps {
  /** Skeleton 行数 */
  rows?: number;
  /** Spin 提示文案（提供则用 Spin，否则用 Skeleton） */
  tip?: string;
  /** 全屏模式 */
  fullPage?: boolean;
  className?: string;
  style?: CSSProperties;
  testId?: string;
  /** 测试 ID */
}

export function LoadingBlock({
  rows = 4,
  tip,
  fullPage = false,
  className,
  style,
  testId,
}: LoadingBlockProps) {
  const wrapperClass = [
    fullPage ? "state-full-page" : "state-block",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (tip) {
    return (
      <div
        className={wrapperClass}
        style={style}
        data-testid={testId}
        role="status"
        aria-live="polite"
      >
        <Spin size="large" tip={tip}>
          <div className="spin-placeholder" />
        </Spin>
      </div>
    );
  }
  return (
    <div
      className={wrapperClass}
      style={style}
      data-testid={testId}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <Skeleton active paragraph={{ rows }} />
    </div>
  );
}

/**
 * Error 状态
 * @see docs/02-design/ComponentLibrary.md §9.3
 */
export interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
  /** 紧凑模式（行内 / 卡片内） */
  compact?: boolean;
  /** 自定义状态（默认根据 error 自动判断） */
  status?: "403" | "404" | "error" | "warning";
  onBack?: () => void;
  className?: string;
  style?: CSSProperties;
  testId?: string;
}

export function ErrorState({
  error,
  onRetry,
  title,
  compact = false,
  status,
  onBack,
  className,
  style,
  testId,
}: ErrorStateProps) {
  const httpStatus = getHttpStatus(error);
  const resultStatus =
    status ??
    (httpStatus === 403 ? "403" : httpStatus === 404 ? "404" : "error");
  const resolvedTitle =
    title ??
    (httpStatus === 403
      ? "无权访问"
      : httpStatus === 404
        ? "资源不存在"
        : "加载失败");

  const retryButton = onRetry ? (
    <Button icon={<ReloadOutlined />} onClick={onRetry} aria-label="重新加载">
      重新加载
    </Button>
  ) : undefined;

  if (compact) {
    return (
      <div
        className={className}
        style={style}
        data-testid={testId}
        role="alert"
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size={4} align="center">
              <Typography.Text strong>{resolvedTitle}</Typography.Text>
              <Typography.Text type="secondary">
                {getErrorMessage(error)}
              </Typography.Text>
              <Space>
                {retryButton}
                {onBack ? (
                  <Button onClick={onBack} aria-label="返回">
                    返回
                  </Button>
                ) : null}
              </Space>
            </Space>
          }
        />
      </div>
    );
  }

  return (
    <div
      className={className}
      style={style}
      data-testid={testId}
      role="alert"
    >
      <Result
        status={resultStatus}
        title={resolvedTitle}
        subTitle={getErrorMessage(error)}
        extra={
          <Space>
            {onBack ? (
              <Button onClick={onBack} aria-label="返回">
                返回
              </Button>
            ) : null}
            {retryButton}
          </Space>
        }
      />
    </div>
  );
}

/**
 * Empty 状态
 * @see docs/02-design/ComponentLibrary.md §9.1
 */
export interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  /** 紧凑模式（卡片内 / 表格内） */
  compact?: boolean;
  className?: string;
  style?: CSSProperties;
  testId?: string;
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  compact = false,
  className,
  style,
  testId,
}: EmptyStateProps) {
  return (
    <div
      className={className}
      style={style}
      data-testid={testId}
      role="region"
      aria-label="空状态"
    >
      <Empty
        image={icon ?? Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={4} align="center">
            <Typography.Text strong>{title}</Typography.Text>
            {description ? (
              <Typography.Text type="secondary">
                {description}
              </Typography.Text>
            ) : null}
            {action}
          </Space>
        }
        style={{ padding: compact ? 24 : 48 }}
      />
    </div>
  );
}