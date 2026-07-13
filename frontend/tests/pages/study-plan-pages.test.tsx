import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StudyPlanCreatePage } from "../../src/pages/StudyPlanCreatePage";
import { StudyPlanDetailPage } from "../../src/pages/StudyPlanDetailPage";

const course = {
  id: "crs_123",
  user_id: "usr_123",
  name: "高等数学",
  description: "期末复习",
  teacher: "王老师",
  term: "2026 Spring",
  status: "active",
  created_at: "2026-07-09T12:00:00+00:00",
  updated_at: "2026-07-09T12:00:00+00:00",
  deleted_at: null,
};

const preview = {
  course_id: "crs_123",
  title: "高等数学学习计划",
  goal_text: "三天完成线性代数第一章复习",
  start_date: "2026-07-13",
  end_date: "2026-07-15",
  daily_available_minutes: 60,
  material_scope: {
    include_all_parsed_materials: true,
    material_ids: [],
  },
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

const savedDetail = {
  plan: {
    id: "plan_1",
    user_id: "usr_123",
    course_id: "crs_123",
    title: "高等数学学习计划",
    goal_text: "三天完成线性代数第一章复习",
    parsed_config_json: null,
    start_date: "2026-07-13",
    end_date: "2026-07-15",
    daily_available_minutes: 60,
    status: "active",
    created_at: "2026-07-09T12:00:00+00:00",
    updated_at: "2026-07-09T12:00:00+00:00",
    deleted_at: null,
  },
  tasks: [
    {
      id: "task_1",
      plan_id: "plan_1",
      course_id: "crs_123",
      title: "第 1 天学习任务",
      task_date: "2026-07-13",
      status: "not_started",
      sort_order: 1,
      start_time: null,
      end_time: null,
      created_at: "2026-07-09T12:00:00+00:00",
      updated_at: "2026-07-09T12:00:00+00:00",
    },
  ],
  subtasks: [
    {
      id: "subtask_1",
      task_id: "task_1",
      plan_id: "plan_1",
      course_id: "crs_123",
      title: "学习: 向量空间",
      subtask_type: "learn",
      description: "阅读并整理概念",
      related_material_ids_json: ["mat_1"],
      status: "not_started",
      completed_at: null,
      sort_order: 1,
      created_at: "2026-07-09T12:00:00+00:00",
      updated_at: "2026-07-09T12:00:00+00:00",
    },
  ],
};

const diagnosticQuestions = {
  question_version: "study_plan_diagnostic_v1",
  questions: [
    {
      question_id: "topic_mastery_vector_space",
      question_type: "topic_mastery",
      question_text: "你对「向量空间」了解多少？",
      sort_order: 1,
      required: true,
      topic_id: "topic_vector_space",
      topic_title: "向量空间",
      options: [
        { value: "none", label: "完全不了解" },
        { value: "heard", label: "听说过，但不清楚" },
        { value: "some", label: "了解一些" },
        { value: "familiar", label: "比较熟悉" },
      ],
      placeholder: null,
    },
    {
      question_id: "weak_area",
      question_type: "weak_area",
      question_text: "你最担心哪类内容？",
      sort_order: 2,
      required: true,
      topic_id: null,
      topic_title: null,
      options: [
        { value: "concept", label: "概念理解" },
        { value: "calculation", label: "计算推导" },
        { value: "application", label: "做题应用" },
        { value: "memorization", label: "记忆重点" },
        { value: "other", label: "其他" },
      ],
      placeholder: null,
    },
    {
      question_id: "diagnostic_note",
      question_type: "diagnostic_note",
      question_text: "还有什么想特别补的地方？",
      sort_order: 3,
      required: false,
      topic_id: null,
      topic_title: null,
      options: [],
      placeholder: "可选填写",
    },
  ],
};

const diagnosticProfile = {
  question_version: "study_plan_diagnostic_v1",
  prior_knowledge_level: "little",
  foundation_needed: true,
  weak_topics: ["topic_vector_space"],
  weak_area: "concept",
  explanation_style: "plain_language",
  diagnostic_note: "希望先补基础",
};

function successResponse(data: unknown, requestId = "req_1") {
  return new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderStudyPlanRoutes(initialPath = "/courses/crs_123/study-plans/new") {
  return render(
    <MantineProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route element={<StudyPlanCreatePage />} path="/courses/:courseId/study-plans/new" />
          <Route element={<StudyPlanDetailPage />} path="/courses/:courseId/study-plans/:planId" />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

function requestIdempotencyKey(call: [RequestInfo | URL, RequestInit | undefined]): string | undefined {
  const headers = call[1]?.headers;
  if (headers instanceof Headers) {
    return headers.get("Idempotency-Key") ?? undefined;
  }
  if (Array.isArray(headers)) {
    return headers.find(([name]) => name === "Idempotency-Key")?.[1];
  }
  return (headers as Record<string, string> | undefined)?.["Idempotency-Key"];
}

describe("study plan pages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("previews, invalidates stale previews, then saves and navigates to detail", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plans/preview")) {
        return Promise.resolve(successResponse(preview, "req_preview"));
      }
      if (url.endsWith("/courses/crs_123/study-plans") && init?.method === "POST") {
        return Promise.resolve(successResponse(savedDetail, "req_save"));
      }
      if (url.endsWith("/study-plans/plan_1")) {
        return Promise.resolve(successResponse(savedDetail, "req_detail"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "创建学习计划" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "三天完成线性代数第一章复习" },
    });
    fireEvent.change(screen.getByLabelText("开始日期"), { target: { value: "2026-07-13" } });
    fireEvent.change(screen.getByLabelText("结束日期"), { target: { value: "2026-07-15" } });
    fireEvent.change(screen.getByLabelText("每日可用学习时长"), { target: { value: "60" } });

    fireEvent.click(screen.getByRole("button", { name: "生成预览" }));
    expect(await screen.findByText("第 1 天学习任务")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存计划" })).toBeEnabled();

    fireEvent.change(screen.getByLabelText("每日可用学习时长"), { target: { value: "75" } });
    expect(screen.getByText("配置已修改，请重新生成预览后保存。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存计划" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "生成预览" }));
    expect(await screen.findByText("预览已生成")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "保存计划" }));

    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
    expect(screen.getByText("学习: 向量空间")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始学习（待接入）" })).toBeDisabled();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plans",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "三天完成线性代数第一章复习",
            start_date: "2026-07-13",
            end_date: "2026-07-15",
            daily_available_minutes: 75,
            preference: "balanced",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
            title: preview.title,
            client_flow: "wizard_v1",
            tasks: preview.tasks,
          }),
          headers: expect.objectContaining({
            "Idempotency-Key": expect.stringMatching(/^study-plan-crs_123-/),
          }),
          method: "POST",
        }),
      );
    });
  });

  it("creates a diagnostic profile and sends it with the preview request", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plan-diagnostic-questions")) {
        return Promise.resolve(successResponse(diagnosticQuestions, "req_diagnostic_questions"));
      }
      if (url.endsWith("/study-plan-diagnostic-profiles")) {
        return Promise.resolve(successResponse(diagnosticProfile, "req_diagnostic_profile"));
      }
      if (url.endsWith("/study-plans/preview")) {
        return Promise.resolve(successResponse(preview, "req_preview"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "创建学习计划" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "三天完成线性代数第一章复习" },
    });
    fireEvent.change(screen.getByLabelText("开始日期"), { target: { value: "2026-07-13" } });
    fireEvent.change(screen.getByLabelText("结束日期"), { target: { value: "2026-07-15" } });
    fireEvent.change(screen.getByLabelText("每日可用学习时长"), { target: { value: "60" } });

    fireEvent.click(screen.getByRole("button", { name: "开始学情诊断" }));
    expect(await screen.findByText("你对「向量空间」了解多少？")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("听说过，但不清楚"));
    fireEvent.click(screen.getByLabelText("概念理解"));
    fireEvent.change(screen.getByLabelText("还有什么想特别补的地方？"), {
      target: { value: "希望先补基础" },
    });
    fireEvent.click(screen.getByRole("button", { name: "提交诊断" }));

    expect(await screen.findByText("诊断已完成")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "生成预览" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plans/preview",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "三天完成线性代数第一章复习",
            start_date: "2026-07-13",
            end_date: "2026-07-15",
            daily_available_minutes: 60,
            preference: "balanced",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
            diagnostic_profile: diagnosticProfile,
          }),
          method: "POST",
        }),
      );
    });
  });

  it("keeps the plan draft after refreshing the create page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
          return Promise.resolve(successResponse(course, "req_course"));
        }
        return Promise.resolve(successResponse({}));
      }),
    );

    const { unmount } = renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "创建学习计划" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "三天完成线性代数第一章复习" },
    });
    fireEvent.change(screen.getByLabelText("开始日期"), { target: { value: "2026-07-13" } });
    fireEvent.change(screen.getByLabelText("结束日期"), { target: { value: "2026-07-15" } });
    fireEvent.change(screen.getByLabelText("每日可用学习时长"), { target: { value: "60" } });

    unmount();
    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "创建学习计划" })).toBeInTheDocument();
    expect(screen.getByLabelText("学习目标")).toHaveValue("三天完成线性代数第一章复习");
    expect(screen.getByLabelText("开始日期")).toHaveValue("2026-07-13");
    expect(screen.getByLabelText("结束日期")).toHaveValue("2026-07-15");
    expect(screen.getByLabelText("每日可用学习时长")).toHaveValue(60);
  });

  it("previews without a diagnostic profile because diagnosis is optional", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plans/preview")) {
        return Promise.resolve(successResponse(preview, "req_preview"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "创建学习计划" })).toBeInTheDocument();
    expect(screen.getByText("学情诊断可跳过，生成预览时会按基础配置直接生成计划。")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "三天完成线性代数第一章复习" },
    });
    fireEvent.change(screen.getByLabelText("开始日期"), { target: { value: "2026-07-13" } });
    fireEvent.change(screen.getByLabelText("结束日期"), { target: { value: "2026-07-15" } });
    fireEvent.change(screen.getByLabelText("每日可用学习时长"), { target: { value: "60" } });

    fireEvent.click(screen.getByRole("button", { name: "生成预览" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plans/preview",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "三天完成线性代数第一章复习",
            start_date: "2026-07-13",
            end_date: "2026-07-15",
            daily_available_minutes: 60,
            preference: "balanced",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
          }),
          method: "POST",
        }),
      );
    });
  });

  it("reuses the same idempotency key for unchanged preview retries and resets it after a new preview", async () => {
    let saveAttempts = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plans/preview")) {
        return Promise.resolve(successResponse(preview, "req_preview"));
      }
      if (url.endsWith("/courses/crs_123/study-plans") && init?.method === "POST") {
        saveAttempts += 1;
        if (saveAttempts <= 2) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                error: {
                  code: "INTERNAL_ERROR",
                  message: "network timeout",
                  details: {},
                },
                meta: { request_id: "req_save_failed" },
              }),
              {
                status: 500,
                headers: { "Content-Type": "application/json" },
              },
            ),
          );
        }
        return Promise.resolve(successResponse(savedDetail, "req_save"));
      }
      if (url.endsWith("/study-plans/plan_1")) {
        return Promise.resolve(successResponse(savedDetail, "req_detail"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderStudyPlanRoutes();
    await screen.findByRole("heading", { level: 1 });

    const goalInput = container.querySelector("textarea");
    const dateInputs = container.querySelectorAll('input[type="date"]');
    const minutesInput = container.querySelector('input[type="number"]');
    expect(goalInput).not.toBeNull();
    expect(dateInputs).toHaveLength(2);
    expect(minutesInput).not.toBeNull();

    fireEvent.change(goalInput!, { target: { value: preview.goal_text } });
    fireEvent.change(dateInputs[0], { target: { value: "2026-07-13" } });
    fireEvent.change(dateInputs[1], { target: { value: "2026-07-15" } });
    fireEvent.change(minutesInput!, { target: { value: "60" } });

    const actionButtons = () => Array.from(container.querySelectorAll("button")).slice(-2);
    const previewButton = () => actionButtons()[0] as HTMLButtonElement;
    const saveButton = () => actionButtons()[1] as HTMLButtonElement;

    fireEvent.click(previewButton());
    await waitFor(() => expect(saveButton()).toBeEnabled());

    fireEvent.click(saveButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("network timeout");

    fireEvent.click(saveButton());
    await waitFor(() => expect(saveAttempts).toBe(2));

    fireEvent.change(minutesInput!, { target: { value: "75" } });
    expect(saveButton()).toBeDisabled();

    fireEvent.click(previewButton());
    await waitFor(() => expect(saveButton()).toBeEnabled());
    fireEvent.click(saveButton());
    await waitFor(() => expect(saveAttempts).toBe(3));

    const saveCalls = fetchMock.mock.calls.filter(([input, init]) => (
      String(input).endsWith("/courses/crs_123/study-plans") && init?.method === "POST"
    )) as [RequestInfo | URL, RequestInit | undefined][];
    expect(saveCalls).toHaveLength(3);
    expect(saveCalls[0]?.[1]?.headers).toEqual(expect.objectContaining({
      "Idempotency-Key": expect.stringMatching(/^study-plan-crs_123-/),
    }));
    expect(requestIdempotencyKey(saveCalls[1])).toBe(requestIdempotencyKey(saveCalls[0]));
    expect(requestIdempotencyKey(saveCalls[2])).toMatch(/^study-plan-crs_123-/);
    expect(requestIdempotencyKey(saveCalls[2])).not.toBe(requestIdempotencyKey(saveCalls[0]));
  });

  it("renders readonly detail from the detail endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/courses/crs_123")) {
          return Promise.resolve(successResponse(course, "req_course"));
        }
        return Promise.resolve(successResponse(savedDetail, "req_detail"));
      }),
    );

    renderStudyPlanRoutes("/courses/crs_123/study-plans/plan_1");

    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
    expect(screen.getByText("未开始")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "导出计划（待接入）" })).toBeDisabled();
  });
});
