import {
  CheckCircleOutlined,
  CodeOutlined,
  DeleteOutlined,
  PlusOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getErrorMessage } from "../../api/client";
import { suitesApi } from "../../api/suites";
import { testCasesApi } from "../../api/testCases";
import { queryKeys } from "../../api/queryKeys";
import type { BodyType, HttpMethod, TestCase, TestCasePayload } from "../../api/types";
import { EmptyState, ErrorState, LoadingBlock } from "../../components/AsyncState";
import PageHeader from "../../components/PageHeader";
import { useProjectWorkspace } from "../../components/workspace/projectWorkspaceContext";
import { parseJsonObject, parseJsonValue, stringifyJson } from "../../utils/json";

/**
 * Workspace Case Editor — 创建 / 编辑 API Test Case。
 *
 * 支持新建（?suiteId=）和编辑（?caseId=）两种入口。
 *
 * 设计要点（与 F009 对齐）：
 * 1. 断言支持结构化编辑（5 类型 × 12 操作符 + 5 字段）
 * 2. Headers / Query / Body 仍走 JSON 编辑（向后兼容）
 * 3. Body type 切换时自动转换/清空 body 字段
 * 4. 校验前置：所有 JSON 字段在提交前预解析，错误时定位到具体 Tab
 */

const METHODS: HttpMethod[] = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const BODY_TYPES: { value: BodyType; label: string; hint: string }[] = [
  { value: "none", label: "none", hint: "无 Body" },
  { value: "json", label: "json", hint: "JSON 对象 / 数组" },
  { value: "form", label: "form", hint: "表单（key=value）" },
  { value: "raw", label: "raw", hint: "原始文本 / bytes" },
];

const ASSERTION_TYPES = [
  { value: "status_code", label: "状态码", needsPath: false, needsHeader: false },
  { value: "json_path", label: "JSON Path", needsPath: true, needsHeader: false },
  { value: "header", label: "响应头", needsPath: false, needsHeader: true },
  { value: "response_time", label: "响应时间(s)", needsPath: false, needsHeader: false },
  { value: "body_contains", label: "Body 包含", needsPath: false, needsHeader: false },
] as const;

const ASSERTION_OPERATORS_BY_TYPE: Record<string, string[]> = {
  status_code: ["eq", "ne", "gt", "lt", "ge", "le", "in", "not_in"],
  json_path: ["eq", "ne", "gt", "lt", "ge", "le", "contains", "not_contains", "in", "not_in", "exists", "not_exists"],
  header: ["eq", "ne", "contains", "not_contains", "exists", "not_exists"],
  response_time: ["eq", "ne", "gt", "lt", "ge", "le"],
  body_contains: ["contains", "not_contains"],
};

interface AssertionRule {
  type: string;
  operator: string;
  expected?: unknown;
  path?: string;
  header_name?: string;
  case_insensitive?: boolean;
}

export default function WorkspaceCaseEditor() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { projectId = "", caseId } = useParams();
  const [searchParams] = useSearchParams();
  const initialSuiteId = searchParams.get("suiteId");
  const { refresh: refreshWorkspace } = useProjectWorkspace();

  const isEdit = Boolean(caseId);

  // ===== 表单状态 =====
  const [name, setName] = useState("");
  const [method, setMethod] = useState<HttpMethod>("GET");
  const [path, setPath] = useState("/api/example");
  const [headersText, setHeadersText] = useState("{}");
  const [queryParamsText, setQueryParamsText] = useState("{}");
  const [bodyType, setBodyType] = useState<BodyType>("none");
  const [bodyText, setBodyText] = useState("");
  const [assertions, setAssertions] = useState<AssertionRule[]>([]);
  const [timeoutSeconds, setTimeoutSeconds] = useState<number>(30);
  const [enabled, setEnabled] = useState<boolean>(true);
  const [suiteId, setSuiteId] = useState<string | null>(initialSuiteId);

  // JSON 校验错误
  const [headersError, setHeadersError] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [bodyError, setBodyError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<string>("basic");

  // ===== 数据获取 =====
  const caseQuery = useQuery({
    queryKey: queryKeys.testCase(caseId ?? ""),
    queryFn: () => testCasesApi.get(caseId as string),
    enabled: Boolean(caseId),
  });

  // Suites
  const suitesQuery = useQuery({
    queryKey: queryKeys.suites(projectId, ""),
    queryFn: () => suitesApi.list(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });
  const suites = suitesQuery.data?.items ?? [];

  // 编辑模式：回填
  useEffect(() => {
    if (!caseQuery.data) return;
    const data = caseQuery.data;
    setName(data.name);
    setMethod(data.method);
    setPath(data.path);
    setHeadersText(stringifyJson(data.headers, "{}"));
    setQueryParamsText(stringifyJson(data.query_params, "{}"));
    setBodyType((data.body_type ?? "none") as BodyType);
    setBodyText(data.body ? stringifyJson(data.body, "") : "");
    setAssertions(
      Array.isArray(data.assertions)
        ? (data.assertions as unknown as AssertionRule[])
        : [],
    );
    setTimeoutSeconds(data.timeout_seconds ?? 30);
    setEnabled(Boolean(data.enabled));
  }, [caseQuery.data]);

  // ===== 提交 =====
  const saveMutation = useMutation({
    mutationFn: async () => {
      // Suite is required only when creating a case. Existing cases are
      // project assets and are updated through /test-cases/{id}; their Suite
      // associations are managed independently by the Suite APIs.
      const targetSuiteId = suiteId;
      if (!isEdit && !targetSuiteId) {
        throw new Error("请选择 Suite");
      }

      // 校验必填
      if (!name.trim()) {
        throw new Error("请输入 Case 名称");
      }
      if (!path.trim()) {
        throw new Error("请输入请求路径");
      }

      // 解析 JSON
      const headers = parseJsonObject(headersText, "Headers");
      const queryParams = parseJsonObject(queryParamsText, "Query Params");

      // body 解析（用 currentBodyType 避免类型缩窄）
      const currentBodyType: BodyType = bodyType;
      let body: unknown = null;
      if (currentBodyType === "json" || currentBodyType === "form") {
        body = parseJsonValue(bodyText, "Body");
      } else if (currentBodyType === "raw") {
        if (bodyText.trim()) {
          try {
            body = JSON.parse(bodyText);
          } catch {
            body = bodyText;
          }
        }
      }

      const payload: TestCasePayload = {
        name: name.trim(),
        method,
        path: path.trim(),
        headers,
        query_params: queryParams,
        body_type: currentBodyType,
        body,
        assertions:
          assertions.length > 0
            ? (assertions as unknown as Record<string, unknown>[])
            : null,
        timeout_seconds: timeoutSeconds,
        enabled,
      };

      if (isEdit && caseId) {
        return testCasesApi.update(caseId, payload);
      }
      return testCasesApi.create(targetSuiteId as string, payload);
    },
    onSuccess: (saved: TestCase) => {
      message.success(isEdit ? "Case 已更新" : "Case 已创建");
      void queryClient.invalidateQueries({ queryKey: queryKeys.cases(projectId, "") });
      void queryClient.invalidateQueries({ queryKey: queryKeys.testCase(saved.id) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.suites(projectId, "") });
      // A Case can be linked to multiple Suites; invalidate the whole Suite
      // case-link family instead of using the saved Case ID as a Suite ID.
      void queryClient.invalidateQueries({ queryKey: ["suites"] });
      refreshWorkspace();
      const next = new URLSearchParams();
      next.set("justCreated", "1");
      navigate(`/projects/${projectId}/workspace/case?${next.toString()}`);
    },
    onError: (error) => {
      const msg = getErrorMessage(error, "保存失败");
      message.error(msg);
      if (msg.includes("Headers")) setActiveTab("headers");
      else if (msg.includes("Query")) setActiveTab("query");
      else if (msg.includes("Body") || msg.includes("JSON")) setActiveTab("body");
    },
  });

  // ===== 实时 JSON 校验 =====
  useEffect(() => {
    if (!headersText.trim()) {
      setHeadersError(null);
      return;
    }
    try {
      parseJsonObject(headersText, "Headers");
      setHeadersError(null);
    } catch (e) {
      setHeadersError(getErrorMessage(e, "Headers 校验失败"));
    }
  }, [headersText]);

  useEffect(() => {
    if (!queryParamsText.trim()) {
      setQueryError(null);
      return;
    }
    try {
      parseJsonObject(queryParamsText, "Query Params");
      setQueryError(null);
    } catch (e) {
      setQueryError(getErrorMessage(e, "Query 校验失败"));
    }
  }, [queryParamsText]);

  useEffect(() => {
    if (bodyType === "none" || !bodyText.trim() || bodyType === "raw") {
      setBodyError(null);
      return;
    }
    try {
      parseJsonValue(bodyText, "Body");
      setBodyError(null);
    } catch (e) {
      setBodyError(getErrorMessage(e, "Body 校验失败"));
    }
  }, [bodyText, bodyType]);

  // 切换 body_type 时清空 body
  const handleBodyTypeChange = (next: BodyType) => {
    if (next === "none") {
      setBodyText("");
    } else if (bodyType === "none") {
      setBodyText(next === "raw" ? "" : "{}");
    }
    setBodyType(next);
  };

  const breadcrumbName = isEdit
    ? caseQuery.data?.name ?? "编辑 Case"
    : "新建 API Case";

  if (caseQuery.isLoading && isEdit) {
    return <LoadingBlock rows={6} />;
  }
  if (caseQuery.isError && isEdit) {
    return (
      <ErrorState
        error={caseQuery.error}
        onRetry={() => void caseQuery.refetch()}
        title="无法加载 Case"
      />
    );
  }

  return (
    <>
      <PageHeader
        title={breadcrumbName}
        description="配置 API 请求、断言与变量替换；保存后可在 Case 列表或 Suite 详情中查看。"
        breadcrumbs={[
          { title: "项目", href: "/projects" },
          { title: "项目工作区", href: `/projects/${projectId}/workspace/overview` },
          { title: "API 用例", href: `../case` },
          { title: isEdit ? "编辑" : "新建" },
        ]}
        extra={
          <Space>
            <Button onClick={() => navigate(`/projects/${projectId}/workspace/case`)}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              loading={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              保存
            </Button>
          </Space>
        }
      />

      <Card className="surface-card">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: "basic",
              label: "基本",
              children: (
                <BasicTab
                  name={name}
                  setName={setName}
                  method={method}
                  setMethod={setMethod}
                  path={path}
                  setPath={setPath}
                  enabled={enabled}
                  setEnabled={setEnabled}
                  timeoutSeconds={timeoutSeconds}
                  setTimeoutSeconds={setTimeoutSeconds}
                  suiteId={suiteId}
                  setSuiteId={setSuiteId}
                  suites={suites}
                  isEdit={isEdit}
                  setBodyType={handleBodyTypeChange}
                />
              ),
            },
            {
              key: "headers",
              label: "Headers",
              children: (
                <JsonObjectEditor
                  label="请求头（JSON 对象）"
                  hint="键值均为字符串；支持 ${var} 占位符（后端 F008 变量替换）。"
                  value={headersText}
                  onChange={setHeadersText}
                  error={headersError}
                />
              ),
            },
            {
              key: "query",
              label: "Query Params",
              children: (
                <JsonObjectEditor
                  label="查询参数（JSON 对象）"
                  hint="所有值会被序列化为字符串；支持 ${var} 占位符。"
                  value={queryParamsText}
                  onChange={setQueryParamsText}
                  error={queryError}
                />
              ),
            },
            {
              key: "body",
              label: "Body",
              children: (
                <BodyTab
                  bodyType={bodyType}
                  setBodyType={handleBodyTypeChange}
                  bodyText={bodyText}
                  setBodyText={setBodyText}
                  error={bodyError}
                />
              ),
            },
            {
              key: "assertions",
              label: `断言 (${assertions.length})`,
              children: (
                <AssertionTab assertions={assertions} setAssertions={setAssertions} />
              ),
            },
          ]}
        />
      </Card>

      {!isEdit && !suiteId ? (
        <Alert
          className="inline-warning"
          type="warning"
          showIcon
          style={{ marginTop: 16 }}
          message="尚未选择 Suite"
          description="请在「基本」Tab 选择 Case 归属的 Suite，否则无法保存。"
        />
      ) : null}
    </>
  );
}

// ====== Sub-components ======

interface BasicTabProps {
  name: string;
  setName: (v: string) => void;
  method: HttpMethod;
  setMethod: (v: HttpMethod) => void;
  path: string;
  setPath: (v: string) => void;
  enabled: boolean;
  setEnabled: (v: boolean) => void;
  timeoutSeconds: number;
  setTimeoutSeconds: (v: number) => void;
  suiteId: string | null;
  setSuiteId: (v: string) => void;
  suites: { id: string; name: string }[];
  isEdit: boolean;
  setBodyType: (v: BodyType) => void;
}

function BasicTab({
  name,
  setName,
  method,
  setMethod,
  path,
  setPath,
  enabled,
  setEnabled,
  timeoutSeconds,
  setTimeoutSeconds,
  suiteId,
  setSuiteId,
  suites,
  isEdit,
  setBodyType,
}: BasicTabProps) {
  return (
    <Form layout="vertical">
      {!isEdit ? (
        <Form.Item label="归属 Suite" required>
          <Select
            value={suiteId ?? undefined}
            onChange={(v: string) => setSuiteId(v)}
            placeholder="选择 Suite"
            options={suites.map((s) => ({ value: s.id, label: s.name }))}
            showSearch
            optionFilterProp="label"
          />
        </Form.Item>
      ) : null}

      <Form.Item label="Case 名称" required>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={200}
          showCount
          placeholder="例如：获取用户详情"
        />
      </Form.Item>

      <div style={{ display: "grid", gridTemplateColumns: "150px 1fr", gap: 16 }}>
        <Form.Item label="Method" required>
          <Select
            value={method}
            onChange={(v: HttpMethod) => setMethod(v)}
            options={METHODS.map((m) => ({ value: m, label: m }))}
          />
        </Form.Item>
        <Form.Item label="Path" required extra="支持 ${var} 占位符；执行时与 Base URL 拼接。">
          <Input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            maxLength={500}
            placeholder="/api/users/${user_id}"
          />
        </Form.Item>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <Form.Item label="超时（秒）" extra="默认 30s；范围 1-600。">
          <InputNumber
            value={timeoutSeconds}
            onChange={(v) => setTimeoutSeconds(Number(v ?? 30))}
            min={1}
            max={600}
            style={{ width: "100%" }}
          />
        </Form.Item>
        <Form.Item label="启用">
          <Switch checked={enabled} onChange={setEnabled} checkedChildren="启用" unCheckedChildren="禁用" />
        </Form.Item>
        <Form.Item label="快捷模板">
          <Space>
            <Tag
              style={{ cursor: "pointer" }}
              onClick={() => {
                setMethod("GET");
                setPath("/api/health");
                setName("健康检查");
                setEnabled(true);
              }}
            >
              健康检查
            </Tag>
            <Tag
              style={{ cursor: "pointer" }}
              onClick={() => {
                setMethod("POST");
                setPath("/api/login");
                setName("用户登录");
                setBodyType("json");
              }}
            >
              登录模板
            </Tag>
          </Space>
        </Form.Item>
      </div>
    </Form>
  );
}

interface JsonObjectEditorProps {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  error: string | null;
}

function JsonObjectEditor({ label, hint, value, onChange, error }: JsonObjectEditorProps) {
  return (
    <Form layout="vertical">
      <Form.Item
        label={label}
        help={error ?? hint}
        validateStatus={error ? "error" : undefined}
      >
        <Input.TextArea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={10}
          className="json-editor"
          spellCheck={false}
          placeholder='{ "Authorization": "Bearer ${token}" }'
        />
      </Form.Item>
    </Form>
  );
}

interface BodyTabProps {
  bodyType: BodyType;
  setBodyType: (v: BodyType) => void;
  bodyText: string;
  setBodyText: (v: string) => void;
  error: string | null;
}

function BodyTab({ bodyType, setBodyType, bodyText, setBodyText, error }: BodyTabProps) {
  return (
    <Form layout="vertical">
      <Form.Item label="Body 类型" required>
        <Select
          value={bodyType}
          onChange={(v: BodyType) => setBodyType(v)}
          options={BODY_TYPES.map((b) => ({ value: b.value, label: `${b.label} — ${b.hint}` }))}
        />
      </Form.Item>
      {bodyType === "none" ? (
        <Alert
          type="info"
          showIcon
          message="当前 Case 不携带 Body"
          description="Method 必须为 GET/DELETE 等允许无 Body 的请求，或后续切换 Body 类型。"
        />
      ) : (
        <Form.Item
          label={bodyType === "raw" ? "Body 文本" : "Body（JSON）"}
          help={
            error ??
            (bodyType === "raw"
              ? "支持 ${var} 占位符；非 JSON 字符串会按原样发送。"
              : "必须为合法 JSON；嵌套对象 / 数组均可；支持 ${var} 占位符（先 JSON 解析后字符串内替换）。")
          }
          validateStatus={error ? "error" : undefined}
        >
          <Input.TextArea
            value={bodyText}
            onChange={(e) => setBodyText(e.target.value)}
            rows={12}
            className="json-editor"
            spellCheck={false}
            placeholder={
              bodyType === "json"
                ? '{\n  "username": "${username}",\n  "password": "${password}"\n}'
                : bodyType === "form"
                  ? '{\n  "key1": "value1",\n  "key2": "value2"\n}'
                  : "raw text body, ${var} supported"
            }
          />
        </Form.Item>
      )}
    </Form>
  );
}

interface AssertionTabProps {
  assertions: AssertionRule[];
  setAssertions: (a: AssertionRule[]) => void;
}

function AssertionTab({ assertions, setAssertions }: AssertionTabProps) {
  const [editing, setEditing] = useState<AssertionRule | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const addNew = () => {
    setEditing({ type: "status_code", operator: "eq", expected: 200 });
    setEditingIndex(null);
  };
  const editRule = (idx: number) => {
    setEditing({ ...assertions[idx] });
    setEditingIndex(idx);
  };
  const removeRule = (idx: number) => {
    setAssertions(assertions.filter((_, i) => i !== idx));
  };
  const moveRule = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= assertions.length) return;
    const next = [...assertions];
    [next[idx], next[target]] = [next[target], next[idx]];
    setAssertions(next);
  };
  const saveEdit = (rule: AssertionRule) => {
    if (editingIndex === null) {
      setAssertions([...assertions, rule]);
    } else {
      const next = [...assertions];
      next[editingIndex] = rule;
      setAssertions(next);
    }
    setEditing(null);
    setEditingIndex(null);
  };

  return (
    <Space direction="vertical" size={12} style={{ width: "100%" }}>
      <Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={addNew}>
          添加断言
        </Button>
        <Typography.Text type="secondary">
          共 {assertions.length} 条断言。所有断言必须通过，用例才标记为 passed。
        </Typography.Text>
      </Space>

      {assertions.length === 0 ? (
        <EmptyState
          title="尚未配置断言"
          description="无断言的 Case 仅以 HTTP 200 视为通过（与后端默认行为一致）。建议至少配置 1 条断言。"
          icon={<CodeOutlined style={{ fontSize: 28, color: "#1677ff" }} />}
          compact
        />
      ) : (
        <div>
          {assertions.map((a, idx) => (
            <Card
              key={idx}
              size="small"
              style={{ marginBottom: 8 }}
              title={
                <Space>
                  <Tag color="purple">#{idx + 1}</Tag>
                  <Tag color="geekblue">{a.type}</Tag>
                  <Tag>{a.operator}</Tag>
                  {a.path ? <Tag color="cyan">path: {a.path}</Tag> : null}
                  {a.header_name ? <Tag color="cyan">header: {a.header_name}</Tag> : null}
                </Space>
              }
              extra={
                <Space>
                  <Button size="small" onClick={() => moveRule(idx, -1)} disabled={idx === 0}>
                    ↑
                  </Button>
                  <Button size="small" onClick={() => moveRule(idx, 1)} disabled={idx === assertions.length - 1}>
                    ↓
                  </Button>
                  <Button size="small" onClick={() => editRule(idx)}>
                    编辑
                  </Button>
                  <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeRule(idx)}>
                    删除
                  </Button>
                </Space>
              }
            >
              <Typography.Text type="secondary">expected：</Typography.Text>
              <Typography.Text code style={{ marginLeft: 6 }}>
                {a.expected === undefined ? "—" : JSON.stringify(a.expected)}
              </Typography.Text>
            </Card>
          ))}
        </div>
      )}

      <AssertionRuleModal
        open={Boolean(editing)}
        initial={editing}
        onCancel={() => {
          setEditing(null);
          setEditingIndex(null);
        }}
        onSave={saveEdit}
      />
    </Space>
  );
}

interface AssertionRuleModalProps {
  open: boolean;
  initial: AssertionRule | null;
  onCancel: () => void;
  onSave: (rule: AssertionRule) => void;
}

function AssertionRuleModal({ open, initial, onCancel, onSave }: AssertionRuleModalProps) {
  const [rule, setRule] = useState<AssertionRule>(
    initial ?? { type: "status_code", operator: "eq", expected: 200 },
  );
  const [expectedText, setExpectedText] = useState(
    initial ? JSON.stringify(initial.expected) : "200",
  );

  useEffect(() => {
    if (open && initial) {
      setRule({ ...initial });
      setExpectedText(JSON.stringify(initial.expected) ?? "");
    }
  }, [open, initial]);

  if (!open) return null;

  const typeMeta = ASSERTION_TYPES.find((t) => t.value === rule.type);
  const operators = ASSERTION_OPERATORS_BY_TYPE[rule.type] ?? [];
  const needsExpected = !["exists", "not_exists"].includes(rule.operator);
  const expectedError = (() => {
    if (!needsExpected) return null;
    if (!expectedText.trim()) return "请填写 expected";
    try {
      JSON.parse(expectedText);
      return null;
    } catch {
      return "expected 必须是合法 JSON";
    }
  })();

  const canSave = (() => {
    if (typeMeta?.needsPath && !rule.path) return false;
    if (typeMeta?.needsHeader && !rule.header_name) return false;
    if (expectedError) return false;
    return true;
  })();

  const handleSave = () => {
    if (!canSave) return;
    let expected: unknown = undefined;
    if (needsExpected) {
      try {
        expected = JSON.parse(expectedText);
      } catch {
        expected = expectedText;
      }
    }
    onSave({
      type: rule.type,
      operator: rule.operator,
      expected,
      ...(rule.path ? { path: rule.path } : {}),
      ...(rule.header_name ? { header_name: rule.header_name } : {}),
      ...(rule.case_insensitive ? { case_insensitive: true } : {}),
    });
  };

  return (
    <Modal
      title="编辑断言规则"
      open={open}
      onCancel={onCancel}
      onOk={handleSave}
      okText="保存"
      cancelText="取消"
      okButtonProps={{ disabled: !canSave }}
      destroyOnClose
    >
      <Form layout="vertical">
        <Form.Item label="类型" required>
          <Select
            value={rule.type}
            onChange={(v: string) => {
              const firstOp = ASSERTION_OPERATORS_BY_TYPE[v]?.[0] ?? "eq";
              setRule({ type: v, operator: firstOp });
            }}
            options={ASSERTION_TYPES.map((t) => ({ value: t.value, label: t.label }))}
          />
        </Form.Item>
        <Form.Item label="操作符" required>
          <Select
            value={rule.operator}
            onChange={(v: string) => setRule({ ...rule, operator: v })}
            options={operators.map((op) => ({ value: op, label: op }))}
          />
        </Form.Item>

        {typeMeta?.needsPath ? (
          <Form.Item label="JSON Path" required extra="例：data.user.id">
            <Input
              value={rule.path ?? ""}
              onChange={(e) => setRule({ ...rule, path: e.target.value })}
              placeholder="data.user.id"
            />
          </Form.Item>
        ) : null}

        {typeMeta?.needsHeader ? (
          <Form.Item label="Header 名称" required>
            <Input
              value={rule.header_name ?? ""}
              onChange={(e) => setRule({ ...rule, header_name: e.target.value })}
              placeholder="Content-Type"
            />
          </Form.Item>
        ) : null}

        {needsExpected ? (
          <Form.Item
            label="Expected"
            required
            extra="合法 JSON；数值直接写数字，字符串加双引号。"
            validateStatus={expectedError ? "error" : undefined}
            help={expectedError ?? undefined}
          >
            <Input.TextArea
              value={expectedText}
              onChange={(e) => setExpectedText(e.target.value)}
              rows={3}
              className="json-editor"
              spellCheck={false}
            />
          </Form.Item>
        ) : (
          <Alert
            type="info"
            showIcon
            message="exists / not_exists 不需要 expected"
            icon={<WarningOutlined />}
          />
        )}

        {rule.type === "body_contains" ? (
          <Form.Item label="大小写不敏感">
            <Switch
              checked={Boolean(rule.case_insensitive)}
              onChange={(v) => setRule({ ...rule, case_insensitive: v })}
            />
          </Form.Item>
        ) : null}
      </Form>
    </Modal>
  );
}
