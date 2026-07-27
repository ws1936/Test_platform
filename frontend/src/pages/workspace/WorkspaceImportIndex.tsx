import {
  CloudUploadOutlined,
  ImportOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { App, Button, Card, Input, Space, Table, Tag, Typography } from "antd";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { suitesApi } from "../../api/suites";
import { queryKeys } from "../../api/queryKeys";
import type { Suite } from "../../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { formatDateTime } from "../../utils/format";

/**
 * Project 工作区 / 导入 / 选择 Suite 入口。
 *
 * 当用户从工作区侧边栏点击"导入"时，会落到此页。导入模块强依赖一个
 * 目标 Suite（后端 OpenAPI 导入路由形如
 * ``/projects/:pid/suites/:sid/import/openapi``），所以必须先选一个
 * Suite 才能进入向导页（``WorkspaceImport``）。
 *
 * 数据复用：``useProjectWorkspace`` 已经把 suites 拉好了，直接消费
 * ``readiness.hasSuite`` 与上面布局的 query 缓存，避免重复请求。
 */
export default function WorkspaceImportIndexPage() {
  const navigate = useNavigate();
  const { projectId = "" } = useParams();
  const { readiness, refresh: refreshWorkspace } = useProjectWorkspace();
  const { message } = App.useApp();
  const [search, setSearch] = useState("");
  const [committedSearch, setCommittedSearch] = useState("");

  // 该页有一个独立的 suitesQuery（搜索参数独立），同时通过
  // ``queryKeys.suites(projectId, committedSearch)`` 复用既有缓存，
  // 避免在 ProjectWorkspaceLayout 之外再发一次请求。
  const suitesQuery = useQuery({
    queryKey: queryKeys.suites(projectId, committedSearch),
    queryFn: () => suitesApi.list(projectId, committedSearch),
    enabled: Boolean(projectId),
  });
  const suites: Suite[] = suitesQuery.data?.items ?? [];

  const goImport = (suite: Suite) => {
    navigate(`/projects/${projectId}/workspace/import/${suite.id}`);
  };

  return (
    <>
      <PageHeader
        title="导入 OpenAPI"
        description="选择一个 Suite 作为导入目标。OpenAPI 文档会被解析后批量创建该 Suite 下的 API Case。"
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "导入 OpenAPI" },
        ]}
        extra={
          <Button onClick={() => navigate(`/projects/${projectId}/workspace/suite`)}>
            管理 Suite
          </Button>
        }
      />

      <Card className="surface-card">
        <div className="toolbar">
          <div className="toolbar-left">
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="按 Suite 名称搜索"
              style={{ width: 320 }}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onPressEnter={() => setCommittedSearch(search.trim())}
              onClear={() => {
                setSearch("");
                setCommittedSearch("");
              }}
            />
            <Button onClick={() => setCommittedSearch(search.trim())}>搜索</Button>
          </div>
          <Typography.Text type="secondary">
            共 {suitesQuery.data?.total ?? 0} 个 Suite
          </Typography.Text>
        </div>

        {suitesQuery.isLoading ? (
          <LoadingBlock rows={3} />
        ) : suitesQuery.isError ? (
          <ErrorState
            error={suitesQuery.error}
            onRetry={() => {
              void suitesQuery.refetch();
              refreshWorkspace();
            }}
          />
        ) : (
          <Table<Suite>
            rowKey="id"
            dataSource={suites}
            pagination={false}
            scroll={{ x: "max-content" }}
            locale={{
              emptyText: (
                <EmptyState
                  title={
                    committedSearch
                      ? "未找到匹配 Suite"
                      : readiness.hasSuite
                        ? "没有可用的 Suite"
                        : "尚未创建测试套件"
                  }
                  description={
                    committedSearch
                      ? undefined
                      : "先创建 Suite，再把 OpenAPI 文档中的接口导入到该 Suite 下。"
                  }
                  action={
                    !committedSearch ? (
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() =>
                          navigate(`/projects/${projectId}/workspace/suite`)
                        }
                      >
                        新建 Suite
                      </Button>
                    ) : undefined
                  }
                />
              ),
            }}
            columns={[
              {
                title: "Suite 名称",
                dataIndex: "name",
                render: (name: string, suite) => (
                  <Space>
                    <Button
                      type="link"
                      className="table-link"
                      onClick={() =>
                        navigate(`/projects/${projectId}/workspace/suite/${suite.id}`)
                      }
                    >
                      {name}
                    </Button>
                    {readiness.hasSuite && suite.id === suites[0]?.id ? (
                      <Tag color="geekblue" bordered={false}>
                        最近使用
                      </Tag>
                    ) : null}
                  </Space>
                ),
              },
              {
                title: "描述",
                dataIndex: "description",
                ellipsis: true,
                render: (value: string | null) =>
                  value || <Typography.Text type="secondary">暂无描述</Typography.Text>,
              },
              { title: "更新时间", dataIndex: "updated_at", width: 190, render: formatDateTime },
              {
                title: "操作",
                key: "actions",
                width: 180,
                render: (_, suite) => (
                  <Button
                    type="primary"
                    icon={<CloudUploadOutlined />}
                    onClick={() => {
                      message.loading({ content: `准备导入到「${suite.name}」…`, duration: 0.6 });
                      goImport(suite);
                    }}
                  >
                    从此导入
                  </Button>
                ),
              },
            ]}
          />
        )}

        <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0 }}>
          <ImportOutlined /> &nbsp; 导入流程：选择 Suite → 预览（dry_run=true） → 确认创建（dry_run=false）。
          同一 Suite 内冲突策略可选「跳过」或「覆盖」。
        </Typography.Paragraph>
      </Card>
    </>
  );
}