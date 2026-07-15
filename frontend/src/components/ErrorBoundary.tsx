import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button, Result } from "antd";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * 全局 Error Boundary
 * @see docs/02-design/ComponentLibrary.md §15.1
 */
export default class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // 敏感上下文不写入控制台；生产环境可接入已批准的脱敏监控。
    if (typeof window !== "undefined" && import.meta.env?.DEV) {
      // eslint-disable-next-line no-console
      console.error("[ErrorBoundary]", error, info);
    }
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div role="alert">
          <Result
            status="error"
            title="页面出现异常"
            subTitle="请刷新页面重试；若问题持续存在，请联系平台管理员。"
            extra={
              <Button
                type="primary"
                onClick={() => window.location.reload()}
                aria-label="刷新页面"
              >
                刷新页面
              </Button>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}