import { Card, Progress, Space, Typography } from "antd";
import type { CSSProperties, ReactNode } from "react";
import { ErrorState, EmptyState } from "../AsyncState";

interface DashboardMetricCardProps {
  title: string;
  value: string;
  hint: string;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  emptyTitle?: string;
  percent?: number | null;
  onClick?: () => void;
  className?: string;
  bodyStyle?: CSSProperties;
  style?: CSSProperties;
  extra?: ReactNode;
}

export default function DashboardMetricCard({
  title,
  value,
  hint,
  loading = false,
  error,
  onRetry,
  emptyTitle,
  percent,
  onClick,
  className,
  bodyStyle,
  style,
  extra,
}: DashboardMetricCardProps) {
  return (
    <Card
      className={["surface-card dashboard-metric-card", className].filter(Boolean).join(" ")}
      loading={loading}
      hoverable={Boolean(onClick)}
      onClick={onClick}
      bodyStyle={bodyStyle}
      style={style}
      extra={extra}
    >
      {error ? <ErrorState compact error={error} onRetry={onRetry} /> : null}
      {!error && emptyTitle ? <EmptyState title={emptyTitle} /> : null}
      {!error && !emptyTitle ? (
        <Space direction="vertical" size={10} style={{ width: "100%" }}>
          <Typography.Text type="secondary">{title}</Typography.Text>
          <Typography.Title level={2} className="dashboard-metric-value">
            {value}
          </Typography.Title>
          {percent !== undefined && percent !== null ? (
            <Progress
              percent={Math.round(percent * 100)}
              showInfo={false}
              status={percent >= 0.8 ? "success" : percent >= 0.5 ? "normal" : "exception"}
            />
          ) : null}
          <Typography.Text type="secondary" className="dashboard-metric-hint">
            {hint}
          </Typography.Text>
        </Space>
      ) : null}
    </Card>
  );
}
