import { describe, expect, it, vi } from "vitest";

import {
  fetchStudyPlan,
  listStudyPlans,
  previewStudyPlan,
  saveStudyPlan,
} from "../../../src/features/study-plans/api";
import type { StudyPlanSaveRequest, StudyPlanPreviewRequest } from "../../../src/features/study-plans/types";

const draft: StudyPlanPreviewRequest = {
  goal_text: "三天完成线性代数第一章复习",
  start_date: "2026-07-13",
  end_date: "2026-07-15",
  daily_available_minutes: 60,
  preference: "balanced",
  material_scope: {
    include_all_parsed_materials: true,
    material_ids: [],
  },
};

const savePayload: StudyPlanSaveRequest = {
  ...draft,
  title: "楂樼瓑鏁板瀛︿範璁″垝",
  client_flow: "wizard_v1",
  tasks: [
    {
      title: "第 1 天学习任务",
      task_date: "2026-07-13",
      sort_order: 1,
      subtasks: [
        {
          title: "学习: 向量空间",
          subtask_type: "learn",
          description: "阅读并整理概念",
          related_material_ids: ["mat_1"],
          estimated_minutes: 45,
          citation_chunk_ids: ["chunk_1"],
          generation_parameters: {},
          sort_order: 1,
        },
      ],
    },
  ],
};

function successResponse(data: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify({ data, meta: { request_id: "req_1" } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("study plans api", () => {
  it("calls the contracted study plan endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => successResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await listStudyPlans("crs_1");
    await previewStudyPlan("crs_1", draft);
    await saveStudyPlan("crs_1", savePayload, "study-plan-save-key");
    await fetchStudyPlan("plan_1");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/courses/crs_1/study-plans",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/courses/crs_1/study-plans/preview",
      expect.objectContaining({
        body: JSON.stringify(draft),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/courses/crs_1/study-plans",
      expect.objectContaining({
        body: JSON.stringify(savePayload),
        headers: expect.objectContaining({
          "Idempotency-Key": "study-plan-save-key",
        }),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/study-plans/plan_1",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
