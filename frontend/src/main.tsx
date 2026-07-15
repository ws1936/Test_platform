import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntdApp, ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { getHttpStatus } from "./api/client";
import ErrorBoundary from "./components/ErrorBoundary";
import "./styles.css";

/**
 * Ant Design Theme
 * 单一来源：docs/02-design/DesignSystem.md
 * 这里的 token 与 CSS 变量保持一致；CSS 变量用于组件级覆盖。
 */
const themeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    // 品牌色
    colorPrimary: "#315efb",
    colorInfo: "#315efb",
    colorSuccess: "#16a34a",
    colorWarning: "#faad14",
    colorError: "#dc2626",
    // 中性色
    colorTextBase: "#172033",
    colorTextSecondary: "#778097",
    colorTextTertiary: "#929aab",
    colorTextDisabled: "#c2c8d2",
    colorBgBase: "#ffffff",
    colorBgLayout: "#f5f7fb",
    colorBgContainer: "#ffffff",
    colorBorder: "#edf0f5",
    colorBorderSecondary: "#edf0f5",
    // 圆角
    borderRadius: 8,
    borderRadiusSM: 4,
    borderRadiusLG: 12,
    borderRadiusXS: 4,
    // 字体
    fontFamily:
      'Inter, "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif',
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeSM: 13,
    fontSizeXL: 20,
    fontSizeHeading1: 32,
    fontSizeHeading2: 24,
    fontSizeHeading3: 20,
    fontSizeHeading4: 17,
    fontSizeHeading5: 16,
    // 控件
    controlHeight: 32,
    controlHeightSM: 24,
    controlHeightLG: 40,
    // 线
    lineHeight: 1.57,
    lineHeightLG: 1.5,
    // 阴影
    boxShadow:
      "0 6px 22px rgba(31, 45, 80, 0.06)",
    boxShadowSecondary:
      "0 2px 8px rgba(31, 45, 80, 0.05)",
    // 动效
    motionDurationFast: "0.12s",
    motionDurationMid: "0.16s",
    motionDurationSlow: "0.24s",
  },
  components: {
    Layout: {
      headerBg: "rgba(255,255,255,0.92)",
      siderBg: "#ffffff",
      bodyBg: "#f5f7fb",
      headerHeight: 64,
      headerPadding: "0 28px",
    },
    Menu: {
      itemBorderRadius: 8,
      itemMarginInline: 10,
      itemHeight: 40,
      itemSelectedBg: "#eaf0ff",
      itemSelectedColor: "#315efb",
      itemHoverBg: "rgba(31,45,80,0.04)",
      itemActiveBg: "#eaf0ff",
      iconSize: 16,
    },
    Card: {
      headerFontSize: 16,
      headerHeight: 48,
      paddingLG: 24,
      borderRadiusLG: 12,
    },
    Button: {
      borderRadius: 8,
      borderRadiusLG: 8,
      controlHeight: 32,
      controlHeightLG: 40,
      controlHeightSM: 24,
      fontWeight: 500,
      primaryShadow: "0 2px 8px rgba(49, 94, 251, 0.16)",
    },
    Input: {
      borderRadius: 8,
      controlHeight: 32,
      paddingBlock: 4,
      paddingInline: 12,
    },
    Select: {
      borderRadius: 8,
      controlHeight: 32,
    },
    Modal: {
      borderRadiusLG: 12,
      paddingContentHorizontalLG: 24,
    },
    Drawer: {
      paddingLG: 24,
    },
    Tag: {
      borderRadiusSM: 4,
      defaultBg: "#f7f9fc",
    },
    Table: {
      headerBg: "#f7f9fc",
      headerColor: "#778097",
      headerSortActiveBg: "#f7f9fc",
      headerSortHoverBg: "#f7f9fc",
      rowHoverBg: "rgba(31,45,80,0.04)",
      borderColor: "#edf0f5",
      cellPaddingBlock: 12,
      cellPaddingInline: 16,
    },
    Tooltip: {
      borderRadius: 4,
      colorBgSpotlight: "#172033",
    },
    Breadcrumb: {
      itemColor: "#778097",
      lastItemColor: "#172033",
      separatorColor: "#c2c8d2",
    },
    Form: {
      labelColor: "#172033",
      labelFontSize: 14,
      verticalLabelPadding: "0 0 4px",
    },
    Alert: {
      borderRadiusLG: 8,
    },
    Result: {
      titleFontSize: 24,
    },
  },
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        const status = getHttpStatus(error);
        if (status && [400, 401, 403, 404, 409, 422].includes(status)) return false;
        return failureCount < 2;
      },
    },
    mutations: { retry: false },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ConfigProvider locale={zhCN} theme={themeConfig}>
        <AntdApp>
          <QueryClientProvider client={queryClient}>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </QueryClientProvider>
        </AntdApp>
      </ConfigProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);