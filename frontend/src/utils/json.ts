export function stringifyJson(value: unknown, fallback: string): string {
  if (value === null || value === undefined) return fallback;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return fallback;
  }
}

export function parseJsonObject(
  value: string,
  fieldLabel: string,
): Record<string, unknown> | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed: unknown = JSON.parse(trimmed);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(`${fieldLabel} 必须是 JSON 对象`);
  }
  return parsed as Record<string, unknown>;
}

export function parseJsonArray(
  value: string,
  fieldLabel: string,
): Record<string, unknown>[] | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed: unknown = JSON.parse(trimmed);
  if (!Array.isArray(parsed)) {
    throw new Error(`${fieldLabel} 必须是 JSON 数组`);
  }
  if (parsed.some((item) => !item || Array.isArray(item) || typeof item !== "object")) {
    throw new Error(`${fieldLabel} 中的每一项都必须是 JSON 对象`);
  }
  return parsed as Record<string, unknown>[];
}

export function parseJsonValue(value: string, fieldLabel: string): unknown {
  const trimmed = value.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    throw new Error(`${fieldLabel} 不是有效 JSON`);
  }
}
