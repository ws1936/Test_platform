import { api } from "./client";
import type {
  ImportPreview,
  ImportResult,
  OpenApiSourcePayload,
} from "./types";

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
};
