import { Tag } from "antd";
import type { CSSProperties } from "react";
import type {
  HttpMethod,
  ResultStatus,
  RunScope,
  RunStatus,
} from "../api/types";

/**
 * Status & Tags 聚合组件
 * @see docs/02-design/ComponentLibrary.md §6
 */

const METHOD_COLORS: Record<HttpMethod, string> = {
  GET: "green",
  POST: "blue",
  PUT: "orange",
  PATCH: "gold",
  DELETE: "red",
};

export interface MethodTagProps {
  method: HttpMethod;
  className?: string;
  style?: CSSProperties;
}

export function MethodTag({ method, className, style }: MethodTagProps) {
  return (
    <Tag color={METHOD_COLORS[method]} className={className} style={style}>
      {method}
    </Tag>
  );
}

const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  pending: "等待中",
  running: "执行中",
  finished: "已完成",
  failed: "运行失败",
  canceled: "已取消",
};

const RUN_STATUS_COLORS: Record<RunStatus, string> = {
  pending: "default",
  running: "processing",
  finished: "success",
  failed: "error",
  canceled: "warning",
};

export interface RunStatusTagProps {
  status: RunStatus;
  className?: string;
  style?: CSSProperties;
}

export function RunStatusTag({
  status,
  className,
  style,
}: RunStatusTagProps) {
  return (
    <Tag color={RUN_STATUS_COLORS[status]} className={className} style={style}>
      {RUN_STATUS_LABELS[status]}
    </Tag>
  );
}

const RESULT_STATUS_LABELS: Record<ResultStatus, string> = {
  passed: "通过",
  failed: "断言失败",
  skipped: "已跳过",
  error: "执行错误",
};

const RESULT_STATUS_COLORS: Record<ResultStatus, string> = {
  passed: "success",
  failed: "error",
  skipped: "default",
  error: "volcano",
};

export interface ResultStatusTagProps {
  status: ResultStatus;
  className?: string;
  style?: CSSProperties;
}

export function ResultStatusTag({
  status,
  className,
  style,
}: ResultStatusTagProps) {
  return (
    <Tag color={RESULT_STATUS_COLORS[status]} className={className} style={style}>
      {RESULT_STATUS_LABELS[status]}
    </Tag>
  );
}

const SCOPE_LABELS: Record<RunScope, string> = {
  case: "单用例",
  collection: "测试套件",
  project: "整个项目",
};

const SCOPE_COLORS: Record<RunScope, string> = {
  case: "cyan",
  collection: "purple",
  project: "geekblue",
};

export interface ScopeTagProps {
  scope: RunScope;
  className?: string;
  style?: CSSProperties;
}

export function ScopeTag({ scope, className, style }: ScopeTagProps) {
  return (
    <Tag color={SCOPE_COLORS[scope]} className={className} style={style}>
      {SCOPE_LABELS[scope]}
    </Tag>
  );
}

/**
 * 聚合 StatusTags —— 按 type 路由
 * @see docs/02-design/ComponentLibrary.md §15.3
 */
export interface StatusTagUnionProps {
  type: "run" | "result" | "method" | "scope";
  value: string;
  className?: string;
  style?: CSSProperties;
}

export function StatusTag({
  type,
  value,
  className,
  style,
}: StatusTagUnionProps) {
  const extraProps = { className, style };
  if (type === "run") {
    return (
      <RunStatusTag status={value as RunStatus} {...extraProps} />
    );
  }
  if (type === "result") {
    return (
      <ResultStatusTag status={value as ResultStatus} {...extraProps} />
    );
  }
  if (type === "method") {
    return (
      <MethodTag method={value as HttpMethod} {...extraProps} />
    );
  }
  return <ScopeTag scope={value as RunScope} {...extraProps} />;
}