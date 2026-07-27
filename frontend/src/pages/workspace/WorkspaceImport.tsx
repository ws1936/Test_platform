import {
  CheckCircleOutlined,
  CloudDownloadOutlined,
  ExclamationCircleOutlined,
  FileSearchOutlined,
  ImportOutlined,
  LinkOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  Radio,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { openApiImportApi } from "../../api/openApiImport";
import { suitesApi } from "../../api/suites";
import { queryKeys } from "../../api/queryKeys";
import type { ImportPreview, ImportResult } from "../../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { MethodTag } from "../../components/StatusTags";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { parseJsonObject } from "../../utils/json";

type SourceMode = "url" | "content";

/**
 * Workspace OpenAPI 导入向导。
 *
 * 两步流程：
 * 1. Preview（?dry_run=true）：拉取/解析 spec，列出每个 operation，
 *    标记 "new" / "exists" / "overwrite"。
 * 2. Commit（?dry_run=false&preview_id=...）：用预览阶段缓存的 spec
 *    真创建 Case，成功后跳到 Suite 详情。
 *
 * 后端 F012 设计为单端点 + 双模式，无需 polling。
 */
export default function WorkspaceImportPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId = "", suiteId = "" } = useParams();
  const { refresh: refreshWorkspace } = useProjectWorkspace();

  // 源模式
  const [sourceMode, setSourceMode] = useState<SourceMode>("url");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceContentText, setSourceContentText] = useState("");
  const [sourceContent, setSourceContent] = useState<Record<string, unknown> | null>(null);
  const [sourceContentError, setSourceContentError] = useState<string | null>(null);
  const [tagsText, setTagsText] = useState("");
  const [onConflict, setOnConflict] = useState<"skip" | "overwrite">("skip");
  const [namePrefix, setNamePrefix] = useState("openapi");

  // Preview state
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);

  // 当前 suite 信息
  const suiteQuery = useQuery({
    queryKey: queryKeys.suite(projectId, suiteId),
    queryFn: () => suitesApi.get(projectId, suiteId),
    enabled: Boolean(projectId && suiteId),
    staleTime: 60_000,
  });
  const suite = suiteQuery.data ?? null;

  // 校验 source_content JSON
  useEffect(() => {
    if (sourceMode !== "content") {
      setSourceContent(null);
      setSourceContentError(null);
      return;
    }
    if (!sourceContentText.trim()) {
      setSourceContent(null);
      setSourceContentError(null);
      return;
    }
    try {
      const obj = parseJsonObject(sourceContentText, "OpenAPI JSON");
      setSourceContent(obj);
      setSourceContentError(null);
    } catch (error) {
      setSourceContent(null);
      setSourceContentError(getErrorMessage(error, "JSON 解析失败"));
    }
  }, [sourceContentText, sourceMode]);

  // 切换模式时清掉 preview
  useEffect(() => {
    setPreview(null);
    setPreviewId(null);
  }, [sourceMode]);

  // ===== Preview =====
  const previewMutation = useMutation({
    mutationFn: () => {
      const tags = tagsText
        .split(/[,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      return openApiImportApi.preview(
        projectId,
        suiteId,
        {
          source_url: sourceMode === "url" ? sourceUrl.trim() || undefined : undefined,
          source_content: sourceMode === "content" ? (sourceContent as Record<string, unknown>) : undefined,
          tags: tags.length > 0 ? tags : undefined,
        },
        onConflict,
      );
    },
    onSuccess: (data) => {
      setPreview(data);
      setPreviewId(data.preview_id);
      message.success(`预览完成：共 ${data.total} 条 operation`);
    },
    onError: (error) => {
      setPreview(null);
      setPreviewId(null);
      message.error(getErrorMessage(error, "预览失败"));
    },
  });

  // ===== Commit =====
  const commitMutation = useMutation({
    mutationFn: () => {
      if (!previewId) {
        throw new Error("缺少 preview_id，请重新预览");
      }
      const tags = tagsText
        .split(/[,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      return openApiImportApi.commit(
        projectId,
        suiteId,
        previewId,
        {
          source_url: sourceMode === "url" ? sourceUrl.trim() || undefined : undefined,
          source_content: sourceMode === "content" ? (sourceContent as Record<string, unknown>) : undefined,
          tags: tags.length > 0 ? tags : undefined,
        },
        onConflict,
        namePrefix.trim() || undefined,
      );
    },
    onSuccess: (result: ImportResult) => {
      message.success(
        `导入完成：新建 ${result.created.length} 条 · 覆盖 ${result.overwritten.length} 条 · 跳过 ${result.skipped.length} 条`,
      );
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, "") });
      void queryClient.invalidateQueries({ queryKey: queryKeys.suites(projectId, "") });
      void queryClient.invalidateQueries({ queryKey: queryKeys.suite(projectId, suiteId) });
      refreshWorkspace();
      navigate(`/projects/${projectId}/workspace/suite/${suiteId}`);
    },
    onError: (error) => {
      message.error(getErrorMessage(error, "导入失败"));
    },
  });

  const canPreview =
    !previewMutation.isPending &&
    (sourceMode === "url"
      ? Boolean(sourceUrl.trim())
      : Boolean(sourceContent) && !sourceContentError);

  const tags = useMemo(
    () =>
      tagsText
        .split(/[,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    [tagsText],
  );

  if (suiteQuery.isLoading) {
    return <LoadingBlock rows={4} />;
  }
  if (suiteQuery.isError) {
    return (
      <ErrorState
        error={suiteQuery.error}
        onRetry={() => void suiteQuery.refetch()}
      />
    );
  }
  if (!suite) {
    return (
      <ErrorState
        error={new Error("Suite 不存在或已被删除")}
        title="无法加载 Suite"
      />
    );
  }

  return (
    <>
      <PageHeader
        title="导入 OpenAPI"
        description={`从 OpenAPI 3.x 文档批量创建 API Case 到「${suite.name}」`}
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "测试套件", href: `../suite` },
          { title: suite.name, href: `../suite/${suiteId}` },
          { title: "OpenAPI 导入" },
        ]}
        extra={
          <Space>
            <Button onClick={() => navigate(`/projects/${projectId}/workspace/suite/${suiteId}`)}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<ImportOutlined />}
              loading={commitMutation.isPending}
              disabled={!preview || !previewId || commitMutation.isPending}
              onClick={() => commitMutation.mutate()}
            >
              确认导入
            </Button>
          </Space>
        }
      />

      <div className="content-grid import-grid">
        <Card className="surface-card grid-span-7" title="1. 选择数据源">
          <Form layout="vertical">
            <Form.Item label="数据源类型" required>
              <Radio.Group
                value={sourceMode}
                onChange={(e) => setSourceMode(e.target.value as SourceMode)}
                optionType="button"
                buttonStyle="solid"
              >
                <Radio.Button value="url">
                  <LinkOutlined /> URL
                </Radio.Button>
                <Radio.Button value="content">
                  <FileSearchOutlined /> 粘贴 JSON
                </Radio.Button>
              </Radio.Group>
            </Form.Item>

            {sourceMode === "url" ? (
              <Form.Item
                label="OpenAPI URL"
                required
                extra="仅支持 http/https 协议；后端超时 5 秒。建议使用稳定托管的 OpenAPI 3.x JSON。"
              >
                <Input
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  placeholder="https://petstore3.swagger.io/api/v3/openapi.json"
                  allowClear
                />
              </Form.Item>
            ) : (
              <Form.Item
                label="OpenAPI JSON 内容"
                required
                extra="粘贴完整的 OpenAPI 3.x JSON；解析失败时会显示错误信息。"
                validateStatus={sourceContentError ? "error" : undefined}
                help={sourceContentError ?? undefined}
              >
                <Input.TextArea
                  value={sourceContentText}
                  onChange={(e) => setSourceContentText(e.target.value)}
                  rows={12}
                  placeholder='{ "openapi": "3.0.0", "paths": { ... } }'
                  className="json-editor"
                  spellCheck={false}
                />
              </Form.Item>
            )}

            <Form.Item
              label="Tag 过滤（可选）"
              extra="仅导入指定 Tag 的 operation；多个用逗号或空格分隔。留空表示全部。"
            >
              <Input
                value={tagsText}
                onChange={(e) => setTagsText(e.target.value)}
                placeholder="例如：pets, users"
                allowClear
              />
              {tags.length > 0 ? (
                <div style={{ marginTop: 6 }}>
                  <Space size={4} wrap>
                    {tags.map((t) => (
                      <Tag key={t} color="geekblue">
                        {t}
                      </Tag>
                    ))}
                  </Space>
                </div>
              ) : null}
            </Form.Item>

            <Form.Item label="冲突策略" required>
              <Select
                value={onConflict}
                onChange={(v: "skip" | "overwrite") => setOnConflict(v)}
                options={[
                  { value: "skip", label: "跳过（推荐）：同 method+path 的 Case 保留" },
                  { value: "overwrite", label: "覆盖：先删除原 Case 再新建" },
                ]}
              />
            </Form.Item>

            <Form.Item
              label="Name 前缀"
              extra="用于生成 Case 名称，避免与手工维护的 Case 重名。"
            >
              <Input
                value={namePrefix}
                onChange={(e) => setNamePrefix(e.target.value)}
                maxLength={80}
                placeholder="openapi"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                icon={<CloudDownloadOutlined />}
                loading={previewMutation.isPending}
                disabled={!canPreview}
                onClick={() => previewMutation.mutate()}
                block
              >
                预览导入
              </Button>
            </Form.Item>
          </Form>
        </Card>

        <Card className="surface-card grid-span-5" title="2. 预览结果">
          {previewMutation.isError ? (
            <Alert
              className="inline-warning"
              type="error"
              showIcon
              message="预览失败"
              description={getErrorMessage(previewMutation.error, "预览失败")}
            />
          ) : !preview ? (
            <EmptyState
              title="尚未预览"
              description="填写数据源后点击「预览导入」，将展示 OpenAPI 文档中可导入的接口列表。"
              icon={<FileSearchOutlined style={{ fontSize: 32, color: "#1677ff" }} />}
              compact
            />
          ) : (
            <PreviewPanel preview={preview} previewId={previewId} onConflict={onConflict} />
          )}

          {commitMutation.isError ? (
            <Alert
              className="inline-warning"
              type="error"
              showIcon
              message="导入失败"
              description={getErrorMessage(commitMutation.error, "导入失败")}
              style={{ marginTop: 12 }}
            />
          ) : null}
        </Card>
      </div>
    </>
  );
}

interface PreviewPanelProps {
  preview: ImportPreview;
  previewId: string | null;
  onConflict: "skip" | "overwrite";
}

function PreviewPanel({ preview, previewId, onConflict }: PreviewPanelProps) {
  // 统计
  const newCount = preview.operations.filter((o) => o.status === "new").length;
  const existsCount = preview.operations.filter((o) => o.status === "exists").length;
  const overwriteCount = preview.operations.filter((o) => o.status === "overwrite").length;
  const skipCount = existsCount; // skip 模式下的 exists == skipped

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      <Space size={24} wrap>
        <Statistic title="总计" value={preview.total} />
        <Statistic
          title="将新建"
          value={newCount}
          valueStyle={{ color: "#52c41a" }}
          prefix={<PlusOutlined />}
        />
        <Statistic
          title="已存在"
          value={existsCount}
          valueStyle={{ color: "#1677ff" }}
        />
        {onConflict === "overwrite" ? (
          <Statistic
            title="将覆盖"
            value={overwriteCount}
            valueStyle={{ color: "#faad14" }}
          />
        ) : (
          <Statistic
            title="将跳过"
            value={skipCount}
            valueStyle={{ color: "#8c8c8c" }}
          />
        )}
      </Space>

      <Tabs
        size="small"
        defaultActiveKey="operations"
        items={[
          {
            key: "operations",
            label: `Operation 列表（${preview.operations.length}）`,
            children: (
              <Table
                size="small"
                rowKey={(row, idx) => `${row.method}-${row.path}-${idx}`}
                dataSource={preview.operations}
                scroll={{ x: "max-content" }}
                pagination={{ pageSize: 10, size: "small" }}
                columns={[
                  {
                    title: "Method",
                    dataIndex: "method",
                    width: 80,
                    render: (m) => <MethodTag method={m} />,
                  },
                  {
                    title: "Path",
                    dataIndex: "path",
                    ellipsis: true,
                    render: (p) => (
                      <Tooltip title={p}>
                        <span className="code-path">{p}</span>
                      </Tooltip>
                    ),
                  },
                  {
                    title: "Name",
                    dataIndex: "name",
                    ellipsis: true,
                  },
                  {
                    title: "状态",
                    dataIndex: "status",
                    width: 90,
                    render: (s) => {
                      if (s === "new") {
                        return (
                          <Tag color="green" icon={<PlusOutlined />}>
                            new
                          </Tag>
                        );
                      }
                      if (s === "exists") {
                        return (
                          <Tag color="blue" icon={<CheckCircleOutlined />}>
                            exists
                          </Tag>
                        );
                      }
                      return (
                        <Tag color="orange" icon={<ExclamationCircleOutlined />}>
                          {s}
                        </Tag>
                      );
                    },
                  },
                ]}
              />
            ),
          },
          {
            key: "meta",
            label: "Spec 元信息",
            children: (
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Typography.Text type="secondary">
                  OpenAPI Version：
                  <Typography.Text code>{preview.spec_version}</Typography.Text>
                </Typography.Text>
                <Typography.Text type="secondary">
                  Base Path：
                  <Typography.Text code>{preview.base_path || "—"}</Typography.Text>
                </Typography.Text>
                <Typography.Text type="secondary">
                  Preview ID：
                  <Typography.Text code>{previewId ?? "—"}</Typography.Text>
                </Typography.Text>
                <Typography.Text type="secondary">
                  套件：
                  <Typography.Text code>{preview.suite_id}</Typography.Text>
                </Typography.Text>
                {preview.errors && preview.errors.length > 0 ? (
                  <Alert
                    type="warning"
                    showIcon
                    message={`解析产生 ${preview.errors.length} 个警告`}
                    description={
                      <ul style={{ marginBottom: 0, paddingLeft: 16 }}>
                        {preview.errors.slice(0, 5).map((e, i) => (
                          <li key={i}>{e}</li>
                        ))}
                      </ul>
                    }
                  />
                ) : null}
              </Space>
            ),
          },
        ]}
      />
    </Space>
  );
}
