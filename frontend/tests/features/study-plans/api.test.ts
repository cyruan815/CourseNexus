import { describe, expect, it, vi } from "vitest";

import {
  fetchStudyPlan,
  listStudyPlans,
  previewStudyPlan,
  saveStudyPlan,
} from "../../../src/features/study-plans/api";
import type { StudyPlanDraftRequest } from "../../../src/features/study-plans/types";

const draft: StudyPlanDraftRequest = {
  goal_text: "三天完成线性代数第一章复习",
  start_date: "2026-07-13",
  end_date: "2026-07-15",
  daily_available_minutes: 60,
  material_scope: {
    include_all_parsed_materials: true,
    material_ids: [],
  },
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
    await saveStudyPlan("crs_1", draft);
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
        body: JSON.stringify(draft),
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
