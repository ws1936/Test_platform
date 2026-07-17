import { CheckCircleFilled, WarningFilled } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, Empty, List, Progress, Row, Space, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { queryKeys } from "../../api/queryKeys";
import { runsApi } from "../../api/runs";
import type { TestRun } from "../../api/types";
import { ErrorState, LoadingBlock } from "../../components/AsyncState";
import { RunStatusTag, ScopeTag } from "../../components/StatusTags";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { formatDateTime, formatDuration, formatPercent } from "../../utils/format";

export default function WorkspaceOverview() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { projectId, project, readiness, refresh } = useProjectWorkspace();
  const [showCreated, setShowCreated] = useState(false);
  // ``?justCreated=1`` is appended by the create flow so the workspace
  // gives explicit feedback when the user lands here after a successful
  // create.  We strip it after acknowledging so the URL stays clean
  // and a page refresh does not re-show the banner.
  useEffect(() => {
    if (searchParams.get("justCreated") === "1") {
      setShowCreated(true);
      const next = new URLSearchParams(searchParams);
      next.delete("justCreated");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const summaryQuery = useQuery({
    queryKey: queryKeys.projectRunSummary(projectId),
    queryFn: () => runsApi.projectSummary(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });
  const runsQuery = useQuery({
    queryKey: queryKeys.runs(projectId, { limit: 5 }),
    queryFn: () => runsApi.list(projectId, { limit: 5 }),
    enabled: Boolean(projectId),
    staleTime: 15_000,
  });

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      {showCreated && project ? (
        <Alert
          type="success"
          showIcon
          message={`项目 ${project.name} 创建成功`}
          description="资产就绪：环境、默认环境、Suite、Case 都还是空的。下一步：配置默认环境。"
          closable
          onClose={() => setShowCreated(false)}
          action={
            <Button size="small" onClick={() => navigate("environment")}>
              配置环境
            </Button>
          }
        />
      ) : null}

      <Card className="surface-card" title="项目摘要">
        {project ? (
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Typography.Text type="secondary">项目名称</Typography.Text>
              <Typography.Title level={3} style={{ margin: "4px 0 0" }}>{project.name}</Typography.Title>
              <Typography.Text type="secondary">{project.description || "暂无项目描述"}</Typography.Text>
            </Col>
            <Col xs={24} md={8}>
              <Typography.Text type="secondary">资产配置</Typography.Text>
              <Space size={6} wrap style={{ marginTop: 6 }}>
                <Tag color={readiness.hasEnvironment ? "green" : "default"}>环境 {readiness.hasEnvironment ? "✓" : "缺失"}</Tag>
                <Tag color={readiness.hasDefaultEnvironment ? "green" : "default"}>默认环境 {readiness.hasDefaultEnvironment ? "✓" : "缺失"}</Tag>
                <Tag color={readiness.hasSuite ? "green" : "default"}>Suite {readiness.hasSuite ? "✓" : "缺失"}</Tag>
                <Tag color={readiness.hasCase ? "green" : "default"}>Case {readiness.hasCase ? "✓" : "缺失"}</Tag>
              </Space>
            </Col>
            <Col xs={24} md={8}>
              <Typography.Text type="secondary">执行质量</Typography.Text>
              <div style={{ marginTop: 8 }}>
                <Progress
                  type="dashboard"
                  size={120}
                  percent={
                    summaryQuery.data?.overall_pass_rate === null ||
                      summaryQuery.data?.overall_pass_rate === undefined
                      ? 0
                      : Math.round(summaryQuery.data.overall_pass_rate * 100)
                  }
                  format={() => formatPercent(summaryQuery.data?.overall_pass_rate)}
                  status={
                    (summaryQuery.data?.total_failed ?? 0) +
                      (summaryQuery.data?.total_error ?? 0) >
                      0
                      ? "exception"
                      : "success"
                  }
                />
                <Typography.Text type="secondary">
                  最近 Run：{summaryQuery.data ? formatDateTime(summaryQuery.data.last_run_at) : "尚无"}
                </Typography.Text>
              </div>
            </Col>
          </Row>
        ) : null}
      </Card>

      <Card
        className="surface-card"
        title="最近执行"
        extra={<Button type="link" onClick={() => navigate(`report`)}>查看全部 Report</Button>}
      >
        {runsQuery.isLoading ? <LoadingBlock rows={3} /> : null}
        {runsQuery.isError ? (
          <ErrorState error={runsQuery.error} onRetry={refresh} />
        ) : null}
        {runsQuery.data?.items.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="尚无执行记录，可从右侧“快速创建”或顶部“快速执行”开始。"
          />
        ) : null}
        {runsQuery.data && runsQuery.data.items.length > 0 ? (
          <List
            dataSource={runsQuery.data.items}
            renderItem={(run: TestRun) => (
              <List.Item
                className="dashboard-clickable-list-item"
                onClick={() => navigate(`report/${run.id}`)}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <RunStatusTag status={run.status} />
                      <Typography.Text strong>{run.name}</Typography.Text>
                      <ScopeTag scope={run.scope} />
                    </Space>
                  }
                  description={
                    <Space>
                      <Typography.Text type="secondary">通过率 {formatPercent(run.pass_rate)}</Typography.Text>
                      <Typography.Text type="secondary">耗时 {formatDuration(run.elapsed_seconds)}</Typography.Text>
                      <Typography.Text type="secondary">{formatDateTime(run.started_at)}</Typography.Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : null}
      </Card>

      <Card
        className="surface-card"
        title="Workspace 引导"
        extra={<Button type="primary" onClick={refresh}>刷新概览</Button>}
      >
        <Row gutter={[16, 16]}>
          {[
            {
              ok: readiness.hasDefaultEnvironment,
              label: "1. 设置默认环境",
              detail: "执行 Run 前必须先有默认环境；可在 Environment 模块新增并设为默认。",
              action: () => navigate("environment"),
              actionLabel: "前往 Environment",
            },
            {
              ok: readiness.hasSuite,
              label: "2. 创建或导入 Suite",
              detail: "Suite 是用例和导入的归属；可以手工创建，也可以由 Import 模块生成。",
              action: () => navigate("suite"),
              actionLabel: "前往 Suite",
            },
            {
              ok: readiness.hasCase,
              label: "3. 维护 API 用例",
              detail: "配置 Method、Path、Headers、Body、断言与超时，确保执行有意义。",
              action: () => navigate("case"),
              actionLabel: "前往 Case",
            },
            {
              ok: readiness.hasRun,
              label: "4. 发起 Run 并查看 Report",
              detail: "Run 同步执行后跳转 Report，可以从失败项直接回到 Case 编辑器。",
              action: () => navigate("run"),
              actionLabel: "前往 Run",
            },
          ].map((step) => (
            <Col xs={24} md={12} key={step.label}>
              <Card
                className="surface-card workspace-step-card"
                style={{ borderColor: step.ok ? "#b7eb8f" : "#ffe58f", background: step.ok ? "#f6ffed" : "#fffbe6" }}
              >
                <Space align="start">
                  {step.ok ? (
                    <CheckCircleFilled style={{ color: "#52c41a", fontSize: 22 }} />
                  ) : (
                    <WarningFilled style={{ color: "#faad14", fontSize: 22 }} />
                  )}
                  <Space direction="vertical" size={4}>
                    <Typography.Text strong>{step.label}</Typography.Text>
                    <Typography.Text type="secondary">{step.detail}</Typography.Text>
                    <Button size="small" type="link" onClick={step.action}>
                      {step.actionLabel} →
                    </Button>
                  </Space>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
    </Space>
  );
}
