import { api } from "./client";
import type {
  ImportPreview,
  ImportResult,
  OpenApiSourcePayload,
} from "./types";

/**
 * F023 design-mode literal. ``"simple"`` is the F012 byte-equivalent
 * default; ``"schema"`` switches to schema-driven generation via
 * F022 TestDesignEngine + F023 TestGenerator (per-intent preview,
 * multi-type assertions, name-prefixed per strategy).
 *
 * See ``docs/01-product/F023_SPEC.md`` + ADR-009.
 */
export type DesignMode = "simple" | "schema";

export const openApiImportApi = {
  async preview(
    projectId: string,
    suiteId: string,
    payload: OpenApiSourcePayload,
    onConflict: "skip" | "overwrite",
  ): Promise<ImportPreview> {
    const response = await api.post<ImportPreview>(
      `/projects/${projectId}/suites/${suiteId}/import/openapi`,
      { ...payload, on_conflict: onConflict, dry_run: true },
      { params: { dry_run: true, on_conflict: onConflict } },
    );
    return response.data;
  },

  async commit(
    projectId: string,
    suiteId: string,
    previewId: string,
    payload: OpenApiSourcePayload,
    onConflict: "skip" | "overwrite",
    namePrefix?: string,
  ): Promise<ImportResult> {
    const response = await api.post<ImportResult>(
      `/projects/${projectId}/suites/${suiteId}/import/openapi`,
      { ...payload, on_conflict: onConflict, dry_run: false, name_prefix: namePrefix },
      {
        params: {
          dry_run: false,
          preview_id: previewId,
          on_conflict: onConflict,
          ...(namePrefix ? { name_prefix: namePrefix } : {}),
        },
      },
    );
    return response.data;
  },

  /**
   * F024: schema-driven preview. Hits the same endpoint as
   * ``preview()`` but with ``?design=schema`` so the response
   * ``operations[]`` may contain 1..N entries per operation
   * (one per ``TestIntent``), each tagged with a ``strategy``.
   *
   * Falls through to ``preview()`` for ``design="simple"`` callers
   * who still want to use the dedicated method (back-compat).
   */
  async previewSchema(
    projectId: string,
    suiteId: string,
    payload: OpenApiSourcePayload,
    onConflict: "skip" | "overwrite",
    design: DesignMode = "schema",
  ): Promise<ImportPreview> {
    const response = await api.post<ImportPreview>(
      `/projects/${projectId}/suites/${suiteId}/import/openapi`,
      { ...payload, on_conflict: onConflict, dry_run: true },
      {
        params: {
          dry_run: true,
          on_conflict: onConflict,
          design,
        },
      },
    );
    return response.data;
  },

  /**
   * F024: schema-driven commit. Same as ``commit()`` but with
   * ``?design=schema``. Caller must have previously called
   * ``previewSchema()`` and obtained the matching ``preview_id``.
   */
  async commitSchema(
    projectId: string,
    suiteId: string,
    previewId: string,
    payload: OpenApiSourcePayload,
    onConflict: "skip" | "overwrite",
    namePrefix?: string,
    design: DesignMode = "schema",
  ): Promise<ImportResult> {
    const response = await api.post<ImportResult>(
      `/projects/${projectId}/suites/${suiteId}/import/openapi`,
      {
        ...payload,
        on_conflict: onConflict,
        dry_run: false,
        name_prefix: namePrefix,
      },
      {
        params: {
          dry_run: false,
          preview_id: previewId,
          on_conflict: onConflict,
          design,
          ...(namePrefix ? { name_prefix: namePrefix } : {}),
        },
      },
    );
    return response.data;
  },
};
