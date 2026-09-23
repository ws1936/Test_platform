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
  Checkbox,
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
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { openApiImportApi, type DesignMode } from "../../api/openApiImport";
import { suitesApi } from "../../api/suites";
import { queryKeys } from "../../api/queryKeys";
import type { ImportPreview, ImportResult, OperationPreview } from "../../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { MethodTag } from "../../components/StatusTags";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { parseJsonObject } from "../../utils/json";

type SourceMode = "url" | "content";

// F023 (ADR-009) — strategy labels for the schema-driven preview table.
const STRATEGY_LABELS: Record<string, { label: string; color: string }> = {
  happy_path: { label: "Happy Path", color: "green" },
  required_field_missing: { label: "Missing Required", color: "volcano" },
  enum_coverage: { label: "Enum Coverage", color: "geekblue" },
  boundary_min_max: { label: "Boundary", color: "purple" },
  format_invalid: { label: "Format Invalid", color: "magenta" },
  auth_missing: { label: "Missing Auth", color: "red" },
};

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
 *
 * F023/F024 (ADR-009)：``design`` Query 选择 simple（与 F012 字节级一致，
 * 默认） vs schema（启用 F022 TestDesignEngine + F023 TestGenerator，
 * 按策略集合展开 1..N 条用例）。schema 模式下 Preview 表格新增
 * ``strategy`` 列与 ``total_intents`` 统计；用户可按意图勾选后再 commit。
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

  // F023 design mode (default = "simple" = F012 byte-equivalent)
  const [design, setDesign] = useState<DesignMode>("simple");
  // F024 per-intent selection (only meaningful when design="schema").
  // Stores intent indices that the user DESELECTED. We default to ALL
  // selected; toggling a row moves it between selected/deselected.
  const [deselectedIntents, setDeselectedIntents] = useState<Set<number>>(
    new Set<number>(),
  );

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

  // F023: 切换 design 时清掉 preview（preview_id 与 design 绑定）
  useEffect(() => {
    setPreview(null);
    setPreviewId(null);
    setDeselectedIntents(new Set<number>());
  }, [design]);

  // ===== Preview =====
  const previewMutation = useMutation({
    mutationFn: () => {
      const tags = tagsText
        .split(/[,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const payload = {
        source_url: sourceMode === "url" ? sourceUrl.trim() || undefined : undefined,
        source_content: sourceMode === "content" ? (sourceContent as Record<string, unknown>) : undefined,
        tags: tags.length > 0 ? tags : undefined,
      };
      // F023: route to previewSchema() when design="schema" so the
      // operations[] may contain 1..N entries per operation with
      // ``strategy`` labels populated.
      return design === "schema"
        ? openApiImportApi.previewSchema(projectId, suiteId, payload, onConflict, design)
        : openApiImportApi.preview(projectId, suiteId, payload, onConflict);
    },
    onSuccess: (data) => {
      setPreview(data);
      setPreviewId(data.preview_id);
      // Reset deselected intent indices on every fresh preview.
      setDeselectedIntents(new Set<number>());
      const totalMsg =
        data.total_intents != null
          ? `${data.total} 条 operation / ${data.total_intents} 条 intent`
          : `${data.total} 条 operation`;
      message.success(`预览完成：共 ${totalMsg}`);
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
      const payload = {
        source_url: sourceMode === "url" ? sourceUrl.trim() || undefined : undefined,
        source_content: sourceMode === "content" ? (sourceContent as Record<string, unknown>) : undefined,
        tags: tags.length > 0 ? tags : undefined,
      };
      // F023: commit path mirrors preview path so the cached
      // preview_id matches the design that produced it.
      return design === "schema"
        ? openApiImportApi.commitSchema(
            projectId,
            suiteId,
            previewId,
            payload,
            onConflict,
            namePrefix.trim() || undefined,
            design,
          )
        : openApiImportApi.commit(
            projectId,
            suiteId,
            previewId,
            payload,
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

            {/* F023 (ADR-009): ?design= Query — schema-driven generation. */}
            <Form.Item
              label="生成模式 (F023)"
              required
              extra={
                design === "simple"
                  ? "simple：每个 operation 生成 1 条 happy path + 1 个 status_code 断言（与 F012 字节级一致）。"
                  : "schema：按 F022 策略集合（happy_path / required / enum / boundary / format / auth）展开 1..N 条用例，自动生成多类型断言（status_code + json_path + header）。"
              }
            >
              <Radio.Group
                value={design}
                onChange={(e) => setDesign(e.target.value as DesignMode)}
                optionType="button"
                buttonStyle="solid"
              >
                <Radio.Button value="simple">simple（F012 等价）</Radio.Button>
                <Radio.Button value="schema">schema（策略驱动）</Radio.Button>
              </Radio.Group>
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
            <PreviewPanel
              preview={preview}
              previewId={previewId}
              onConflict={onConflict}
              design={design}
              deselectedIntents={deselectedIntents}
              setDeselectedIntents={setDeselectedIntents}
            />
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
  design: DesignMode;
  deselectedIntents: Set<number>;
  setDeselectedIntents: (s: Set<number>) => void;
}

function PreviewPanel({
  preview,
  previewId,
  onConflict,
  design,
  deselectedIntents,
  setDeselectedIntents,
}: PreviewPanelProps) {
  // 统计
  const newCount = preview.operations.filter((o) => o.status === "new").length;
  const existsCount = preview.operations.filter((o) => o.status === "exists").length;
  const overwriteCount = preview.operations.filter((o) => o.status === "overwrite").length;
  const skipCount = existsCount; // skip 模式下的 exists == skipped

  const isSchema = design === "schema";
  // F024: in schema mode, the table is per-intent. Track which row
  // indices are deselected (default = all selected).
  const selectedCount = isSchema
    ? preview.operations.length - deselectedIntents.size
    : preview.operations.length;

  const toggleIntent = (idx: number) => {
    const next = new Set(deselectedIntents);
    if (next.has(idx)) {
      next.delete(idx);
    } else {
      next.add(idx);
    }
    setDeselectedIntents(next);
  };

  const selectAll = () => setDeselectedIntents(new Set<number>());
  const deselectAll = () => {
    const all = new Set<number>();
    preview.operations.forEach((_, i) => all.add(i));
    setDeselectedIntents(all);
  };

  // Columns builder (so we can branch on schema vs simple)
  const columns: ColumnsType<OperationPreview> = [
    ...(isSchema
      ? [
          {
            title: "选择",
            key: "select",
            width: 60,
            render: (_: unknown, _row: OperationPreview, idx: number) => (
              <Checkbox
                checked={!deselectedIntents.has(idx)}
                onChange={() => toggleIntent(idx)}
              />
            ),
          } as const,
        ]
      : []),
    {
      title: "Method",
      dataIndex: "method",
      width: 80,
      render: (m: OperationPreview["method"]) => <MethodTag method={m} />,
    },
    {
      title: "Path",
      dataIndex: "path",
      ellipsis: true,
      render: (p: string) => (
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
    ...(isSchema
      ? [
          {
            title: "Strategy",
            dataIndex: "strategy",
            width: 140,
            render: (s: string | null | undefined) => {
              if (!s) return <Tag>—</Tag>;
              const meta = STRATEGY_LABELS[s] ?? {
                label: s,
                color: "default",
              };
              return <Tag color={meta.color}>{meta.label}</Tag>;
            },
          } as const,
        ]
      : []),
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (s: string) => {
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
  ];

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      <Space size={24} wrap>
        <Statistic title="总计 operation" value={preview.total} />
        {isSchema && preview.total_intents != null ? (
          <Statistic title="总计 intent" value={preview.total_intents} />
        ) : null}
        {isSchema ? (
          <Statistic
            title="本次将创建"
            value={selectedCount}
            valueStyle={{ color: "#722ed1" }}
          />
        ) : null}
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

      {isSchema ? (
        <Space style={{ marginBottom: 4 }}>
          <Button size="small" onClick={selectAll}>
            全选
          </Button>
          <Button size="small" onClick={deselectAll}>
            全不选
          </Button>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            共 {preview.operations.length} 条 intent，已选 {selectedCount}
          </Typography.Text>
        </Space>
      ) : null}

      <Tabs
        size="small"
        defaultActiveKey="operations"
        items={[
          {
            key: "operations",
            label: isSchema
              ? `Intent 列表（${preview.operations.length}）`
              : `Operation 列表（${preview.operations.length}）`,
            children: (
              <Table
                size="small"
                rowKey={(row, idx) =>
                  `${row.method}-${row.path}-${row.strategy ?? "simple"}-${idx}`
                }
                dataSource={preview.operations}
                scroll={{ x: "max-content" }}
                pagination={{ pageSize: 10, size: "small" }}
                columns={columns}
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
