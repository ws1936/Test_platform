// Failure Analysis Panel：基于已有 Failure / Result 数据归类。

import { ApiOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import { Badge, Button, Empty, Space, Table, Tabs, Tag, Typography } from "antd";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  analyzeFailures,
  type FailureCategoryKey,
  type FailureCategorySummary,
} from "../../api/report";
import type {
  Environment,
  FailureItem,
  TestResult,
} from "../../api/types";
import { formatMilliseconds } from "../../utils/format";
import { ResultStatusTag } from "../StatusTags";

const { Text } = Typography;

type CategoryTabKey = "all" | FailureCategoryKey;

const CATEGORY_TABS: { key: CategoryTabKey; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "assertion", label: "Assertion Fail" },
  { key: "httpError", label: "HTTP Error" },
  { key: "variable", label: "Variable Missing" },
  { key: "timeout", label: "Timeout" },
  { key: "network", label: "Network" },
];

const CATEGORY_COLOR: Record<FailureCategoryKey, string> = {
  assertion: "error",
  httpError: "warning",
  variable: "magenta",
  timeout: "volcano",
  network: "red",
};

interface FailureAnalysisPanelProps {
  projectId: string;
  runId: string;
  environment: Environment | null;
  results: TestResult[];
  failureItems: FailureItem[];
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
}

export function FailureAnalysisPanel({
  projectId,
  runId,
  environment,
  results,
  failureItems,
  loading = false,
  error,
  onRetry,
}: FailureAnalysisPanelProps) {
  const [activeTab, setActiveTab] = useState<CategoryTabKey>("all");

  const analysis = useMemo(
    () => analyzeFailures({ results, failureItems }),
    [results, failureItems],
  );

  const failedResults = analysis.cases;
  const resultIndex = useMemo(() => {
    const map = new Map<string, TestResult>();
    results.forEach((result) => map.set(result.id, result));
    return map;
  }, [results]);

  const filteredResults = useMemo(() => {
    if (activeTab === "all") return failedResults;
    return filterResultsByCategory(failedResults, activeTab, resultIndex);
  }, [failedResults, activeTab, resultIndex]);

  const renderCategoryCards = () => (
    <Space size={[16, 16]} wrap className="report-failure-cards">
      {analysis.categories.map((category) => (
        <CategoryCard
          key={category.key}
          category={category}
          isActive={activeTab === category.key}
          onClick={() => setActiveTab(category.key)}
        />
      ))}
    </Space>
  );

  if (loading) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="正在加载 Failure 数据…"
      />
    );
  }
  if (error) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={4} align="center">
            <Text strong>Failure 加载失败</Text>
            {onRetry ? (
              <Button type="primary" onClick={onRetry}>
                重试
              </Button>
            ) : null}
          </Space>
        }
      />
    );
  }

  return (
    <Space direction="vertical" size={16} className="report-failure-analysis">
      {renderCategoryCards()}

      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key as CategoryTabKey)}
        items={CATEGORY_TABS.map((item) => {
          const count =
            item.key === "all"
              ? failedResults.length
              : analysis.categories.find((cat) => cat.key === item.key)?.resultCount ?? 0;
          return {
            key: item.key,
            label: `${item.label} (${count})`,
          };
        })}
      />

      {filteredResults.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={activeTab === "all" ? "本次 Run 无失败项" : "当前分类没有命中证据"}
        />
      ) : (
        <FailureCaseTable
          projectId={projectId}
          runId={runId}
          environment={environment}
          rows={filteredResults}
          failureItems={failureItems}
        />
      )}
    </Space>
  );
}

function CategoryCard({
  category,
  isActive,
  onClick,
}: {
  category: FailureCategorySummary;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      type="default"
      onClick={onClick}
      className={[
        "report-category-card",
        isActive ? "report-category-card--active" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <Space direction="vertical" size={4} align="start">
        <Space>
          <Text strong className="report-category-card-title">
            {category.label}
          </Text>
          <Tag color={CATEGORY_COLOR[category.key]}>{category.resultCount}</Tag>
        </Space>
        <Text type="secondary" className="report-category-card-hint">
          涉及 {category.caseCount} 个 Case
        </Text>
        <Text type="secondary" className="report-category-card-hint">
          {category.hint}
        </Text>
      </Space>
    </Button>
  );
}

function filterResultsByCategory(
  results: TestResult[],
  category: FailureCategoryKey,
  resultIndex: Map<string, TestResult>,
): TestResult[] {
  return results.filter((result) => matchCategory(result, category, resultIndex));
}

function matchCategory(
  result: TestResult,
  category: CategoryTabKey,
  resultIndex: Map<string, TestResult>,
): boolean {
  void resultIndex;
  if (category === "all") return true;
  if (result.status === "failed" && category === "assertion") return true;
  if (result.status === "failed" && category === "httpError") {
    return typeof readResponseStatus(result) === "number";
  }
  if (result.status === "error" && category === "timeout") {
    return result.error_code === "API_EXECUTION_TIMEOUT";
  }
  if (result.status === "error" && category === "network") {
    return result.error_code === "API_CONNECTION_ERROR";
  }
  if (category === "variable") {
    return Boolean(result.error_message) || hasUnresolvedVariableInRequest(result);
  }
  return false;
}

function readResponseStatus(result: TestResult): number | undefined {
  if (!result.response_snapshot || typeof result.response_snapshot !== "object") {
    return undefined;
  }
  const value = (result.response_snapshot as { status?: unknown }).status;
  return typeof value === "number" ? value : undefined;
}

function hasUnresolvedVariableInRequest(result: TestResult): boolean {
  const snapshot = result.request_snapshot;
  if (!snapshot || typeof snapshot !== "object") return false;
  const record = snapshot as Record<string, unknown>;
  for (const value of Object.values(record)) {
    if (typeof value === "string" && (value.includes("{{") || value.includes("${"))) {
      return true;
    }
  }
  return false;
}

interface FailureCaseTableProps {
  projectId: string;
  runId: string;
  environment: Environment | null;
  rows: TestResult[];
  failureItems: FailureItem[];
}

function FailureCaseTable({
  projectId,
  runId,
  environment,
  rows,
  failureItems,
}: FailureCaseTableProps) {
  const itemsByResult = useMemo(() => {
    const map = new Map<string, FailureItem[]>();
    failureItems.forEach((item) => {
      const list = map.get(item.result_id) ?? [];
      list.push(item);
      map.set(item.result_id, list);
    });
    return map;
  }, [failureItems]);

  return (
    <Table<TestResult>
      size="small"
      rowKey="id"
      pagination={false}
      dataSource={rows}
      columns={[
        {
          title: "状态",
          dataIndex: "status",
          width: 96,
          render: (status: TestResult["status"]) => <ResultStatusTag status={status} />,
        },
        {
          title: "Case",
          dataIndex: "case_name",
          render: (name: string, record) => (
            <Space direction="vertical" size={0}>
              <Text strong>{name}</Text>
              <Text type="secondary" className="report-failure-meta">
                {record.case_method} {record.case_path}
              </Text>
            </Space>
          ),
        },
        {
          title: "证据",
          dataIndex: "id",
          render: (id: string) => {
            const items = itemsByResult.get(id) ?? [];
            if (items.length > 0) {
              return (
                <Space direction="vertical" size={2}>
                  {items.slice(0, 3).map((item) => (
                    <Tag color="red" key={`${item.result_id}-${item.failure_index}`}>
                      {item.assertion_type} {item.assertion_operator}
                    </Tag>
                  ))}
                  {items.length > 3 ? (
                    <Text type="secondary">+{items.length - 3} more</Text>
                  ) : null}
                </Space>
              );
            }
            if (recordErrorMessage(itemsByResult, id)) {
              return (
                <Tag color="volcano" icon={<ExclamationCircleOutlined />}>
                  Execution Error
                </Tag>
              );
            }
            return <Text type="secondary">—</Text>;
          },
        },
        {
          title: "耗时",
          dataIndex: "elapsed_ms",
          width: 100,
          render: (value: number | null) => formatMilliseconds(value),
        },
        {
          title: "环境",
          dataIndex: "environment_id",
          width: 140,
          render: (id: string) =>
            environment && environment.id === id ? (
              <Text>{environment.name}</Text>
            ) : (
              <Text type="secondary">{id}</Text>
            ),
        },
        {
          title: "操作",
          dataIndex: "id",
          width: 140,
          render: (id: string) => (
            <Link to={`/projects/${projectId}/workspace/report/${runId}/result/${id}?tab=failures`}>
              <Button type="link" size="small" icon={<ApiOutlined />}>
                查看证据
              </Button>
            </Link>
          ),
        },
      ]}
    />
  );
}

function recordErrorMessage(
  itemsByResult: Map<string, FailureItem[]>,
  id: string,
): boolean {
  const items = itemsByResult.get(id) ?? [];
  return items.some((item) => item.assertion_type === "execution");
}

void Badge;
