import { describe, expect, it, vi } from "vitest";

import {
  createDiagnosticProfile,
  deleteStudyPlan,
  fetchCourseStudyCalendar,
  fetchCourseStudyCalendarDay,
  fetchGlobalCalendarDayTodos,
  fetchGlobalCalendarMonth,
  fetchSubtaskExecutionContext,
  fetchTodayTodos,
  fetchStudyPlan,
  fetchDiagnosticQuestions,
  generateSubtaskHandout,
  generateSubtaskTaskTest,
  exportGeneratedContentMarkdown,
  exportGeneratedContentPdf,
  listStudyPlans,
  parseStudyPlanConfig,
  previewStudyPlan,
  previewStudyPlanRegeneration,
  replaceStudyPlan,
  saveStudyPlan,
  updateSubtaskCompletion,
} from "../../../src/features/study-plans/api";
import type {
  StudyPlanConfigParseRequest,
  StudyPlanDiagnosticProfileRequest,
  StudyPlanDiagnosticQuestionRequest,
  StudyPlanPreviewRequest,
  StudyPlanReplaceRequest,
  StudyPlanSaveRequest,
} from "../../../src/features/study-plans/types";

const draft: StudyPlanPreviewRequest = {
  goal_text: "三天完成线性代数第一章复习",
  start_date: "2026-07-13",
  duration_days: 3,
  daily_available_minutes: 60,
  daily_minutes_source: "user_modified",
  preference: "balanced",
  material_scope: {
    include_all_parsed_materials: true,
    material_ids: [],
  },
};

const parsePayload: StudyPlanConfigParseRequest = {
  goal_text: "从 7 月 13 日开始三天复习线性代数第一章",
  material_scope: {
    include_all_parsed_materials: true,
    material_ids: [],
  },
};

const diagnosticQuestionPayload: StudyPlanDiagnosticQuestionRequest = {
  goal_text: draft.goal_text,
  material_scope: draft.material_scope,
};

const diagnosticProfilePayload: StudyPlanDiagnosticProfileRequest = {
  question_version: "study_plan_diagnostic_v1",
  topic_mastery: [
    {
      topic_id: "topic_vector_space",
      topic_title: "向量空间",
      mastery_level: "heard",
    },
  ],
  weak_area: "concept",
  diagnostic_note: "希望先补基础概念",
  material_scope: draft.material_scope,
};

const savePayload: StudyPlanSaveRequest = {
  ...draft,
  end_date: "2026-07-15",
  title: "高等数学学习计划",
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

const replacePayload: StudyPlanReplaceRequest = {
  ...savePayload,
  title: "高等数学学习计划 v2",
  expected_updated_at: "2026-07-13T10:00:00+08:00",
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
  it("calls the contracted study plan lifecycle endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => successResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await parseStudyPlanConfig("crs_1", parsePayload);
    await fetchDiagnosticQuestions("crs_1", diagnosticQuestionPayload);
    await createDiagnosticProfile("crs_1", diagnosticProfilePayload);
    await previewStudyPlan("crs_1", draft);
    await saveStudyPlan("crs_1", savePayload, "study-plan-save-key");
    await listStudyPlans("crs_1");
    await fetchStudyPlan("plan_1");
    await previewStudyPlanRegeneration("plan_1", { duration_days: 5 });
    await replaceStudyPlan("plan_1", replacePayload);
    await deleteStudyPlan("plan_1");
    await fetchCourseStudyCalendar("crs_1", "2026-07");
    await fetchCourseStudyCalendarDay("crs_1", "2026-07-14");
    await fetchTodayTodos("2026-07-14");
    await fetchGlobalCalendarMonth("2026-07");
    await fetchGlobalCalendarDayTodos("2026-07-14");
    await fetchSubtaskExecutionContext("subtask_1");
    await updateSubtaskCompletion("subtask_1", true);
    await generateSubtaskHandout("subtask_1", { force_regenerate: false });
    await generateSubtaskTaskTest("subtask_2", { force_regenerate: true, parameters: {} });
    await exportGeneratedContentMarkdown("gen_task_test_1");
    await exportGeneratedContentPdf("gen_handout_1");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/courses/crs_1/study-plan-config-parses",
      expect.objectContaining({
        body: JSON.stringify(parsePayload),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/courses/crs_1/study-plan-diagnostic-questions",
      expect.objectContaining({
        body: JSON.stringify(diagnosticQuestionPayload),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/courses/crs_1/study-plan-diagnostic-profiles",
      expect.objectContaining({
        body: JSON.stringify(diagnosticProfilePayload),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/v1/courses/crs_1/study-plans/preview",
      expect.objectContaining({
        body: JSON.stringify(draft),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
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
      6,
      "/api/v1/courses/crs_1/study-plans",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      7,
      "/api/v1/study-plans/plan_1",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      8,
      "/api/v1/study-plans/plan_1/regeneration-previews",
      expect.objectContaining({
        body: JSON.stringify({ duration_days: 5 }),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      9,
      "/api/v1/study-plans/plan_1",
      expect.objectContaining({
        body: JSON.stringify(replacePayload),
        method: "PUT",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      10,
      "/api/v1/study-plans/plan_1",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      11,
      "/api/v1/courses/crs_1/study-calendar?month=2026-07",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      12,
      "/api/v1/courses/crs_1/study-calendar/days/2026-07-14",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      13,
      "/api/v1/todos/today?date=2026-07-14",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      14,
      "/api/v1/calendar/month?month=2026-07",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      15,
      "/api/v1/calendar/days/2026-07-14/todos",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      16,
      "/api/v1/study-subtasks/subtask_1/execution-context",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      17,
      "/api/v1/study-subtasks/subtask_1/completion",
      expect.objectContaining({
        body: JSON.stringify({ completed: true }),
        method: "PUT",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      18,
      "/api/v1/study-subtasks/subtask_1/handouts",
      expect.objectContaining({
        body: JSON.stringify({ force_regenerate: false }),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      19,
      "/api/v1/study-subtasks/subtask_2/task-tests",
      expect.objectContaining({
        body: JSON.stringify({ force_regenerate: true, parameters: {} }),
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      20,
      "/api/v1/generated-contents/gen_task_test_1/exports/markdown",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      21,
      "/api/v1/generated-contents/gen_handout_1/exports/pdf",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
