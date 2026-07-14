import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StudyPlanCreatePage } from "../../src/pages/StudyPlanCreatePage";
import { StudyPlanDetailPage } from "../../src/pages/StudyPlanDetailPage";
import { StudyTaskExecutionPage } from "../../src/pages/StudyTaskExecutionPage";

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

const materials = [
  {
    id: "mat_1",
    course_id: "crs_123",
    user_id: "usr_123",
    folder_id: null,
    name: "线代第一章.pdf",
    material_type: "pdf",
    source_type: "upload",
    file_url: "/files/mat_1.pdf",
    source_url: null,
    file_size: 1024,
    mime_type: "application/pdf",
    parse_status: "parsed",
    parse_error: null,
    page_count: 12,
    created_at: "2026-07-09T12:00:00+00:00",
    updated_at: "2026-07-09T12:00:00+00:00",
    deleted_at: null,
  },
  {
    id: "mat_2",
    course_id: "crs_123",
    user_id: "usr_123",
    folder_id: null,
    name: "未解析习题.pdf",
    material_type: "pdf",
    source_type: "upload",
    file_url: "/files/mat_2.pdf",
    source_url: null,
    file_size: 2048,
    mime_type: "application/pdf",
    parse_status: "parsing",
    parse_error: null,
    page_count: null,
    created_at: "2026-07-09T12:00:00+00:00",
    updated_at: "2026-07-09T12:00:00+00:00",
    deleted_at: null,
  },
];

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

const replacementPreview = {
  ...preview,
  title: "高等数学冲刺计划",
  goal_text: "两天冲刺线性代数第一章",
  start_date: "2026-07-14",
  end_date: "2026-07-15",
  daily_available_minutes: 90,
  preference: "sprint",
  tasks: [
    {
      title: "第 1 天强化任务",
      task_date: "2026-07-14",
      sort_order: 1,
      subtasks: [
        {
          title: "复习: 向量空间核心概念",
          subtask_type: "review",
          description: "整理核心定义并完成回顾",
          related_material_ids: ["mat_1"],
          estimated_minutes: 60,
          citation_chunk_ids: ["chunk_1"],
          generation_parameters: {},
          sort_order: 1,
        },
      ],
    },
  ],
};

const replacedDetail = {
  ...savedDetail,
  plan: {
    ...savedDetail.plan,
    title: replacementPreview.title,
    goal_text: replacementPreview.goal_text,
    start_date: replacementPreview.start_date,
    end_date: replacementPreview.end_date,
    daily_available_minutes: replacementPreview.daily_available_minutes,
    updated_at: "2026-07-13T11:00:00+00:00",
  },
  tasks: [
    {
      ...savedDetail.tasks[0],
      title: "第 1 天强化任务",
      task_date: "2026-07-14",
      updated_at: "2026-07-13T11:00:00+00:00",
    },
  ],
  subtasks: [
    {
      ...savedDetail.subtasks[0],
      title: "复习: 向量空间核心概念",
      subtask_type: "review",
      description: "整理核心定义并完成回顾",
      updated_at: "2026-07-13T11:00:00+00:00",
    },
  ],
};

const executionContext = {
  course: {
    course_id: "crs_123",
    name: "高等数学",
  },
  plan: {
    plan_id: "plan_1",
    title: "高等数学学习计划",
    status: "active",
  },
  execution_date: "2026-07-13",
  current_subtask_id: "subtask_1",
  related_materials: [
    {
      material_id: "mat_1",
      name: "线代第一章.pdf",
      material_type: "pdf",
      parse_status: "parsed",
      availability: "available",
    },
  ],
  handout_content_id: null,
  task_test_content_id: null,
  tasks: [
    {
      task_id: "task_1",
      title: "第 1 天学习任务",
      task_date: "2026-07-13",
      status: "not_started",
      sort_order: 1,
      subtasks: [
        {
          subtask_id: "subtask_1",
          title: "学习: 向量空间",
          subtask_type: "learn",
          description: "阅读并整理概念",
          status: "not_started",
          completed_at: null,
          sort_order: 1,
        },
        {
          subtask_id: "subtask_2",
          title: "练习: 基础题",
          subtask_type: "quiz",
          description: null,
          status: "completed",
          completed_at: "2026-07-13T02:00:00+00:00",
          sort_order: 2,
        },
      ],
    },
  ],
};

const executionContextWithHandout = {
  ...executionContext,
  handout_content_id: "gen_handout_1",
};

const quizExecutionContext = {
  ...executionContext,
  current_subtask_id: "subtask_2",
  handout_content_id: null,
  task_test_content_id: null,
};

const quizExecutionContextWithTaskTest = {
  ...quizExecutionContext,
  task_test_content_id: "gen_task_test_1",
};

const completedResult = {
  changed: true,
  subtask: {
    subtask_id: "subtask_1",
    status: "completed",
    completed_at: "2026-07-13T03:00:00+00:00",
  },
  task: {
    task_id: "task_1",
    status: "completed",
    completed_subtask_count: 2,
    total_subtask_count: 2,
  },
  plan: {
    plan_id: "plan_1",
    status: "completed",
  },
  checkin: {
    date: "2026-07-13",
    planned_task_count: 1,
    completed_task_count: 1,
    planned_subtask_count: 2,
    completed_subtask_count: 2,
    completed: true,
    first_completed_at: "2026-07-13T03:00:00+00:00",
    last_completed_at: "2026-07-13T03:00:00+00:00",
  },
};

const uncompletedResult = {
  ...completedResult,
  changed: true,
  subtask: {
    subtask_id: "subtask_1",
    status: "not_started",
    completed_at: null,
  },
  task: {
    task_id: "task_1",
    status: "in_progress",
    completed_subtask_count: 1,
    total_subtask_count: 2,
  },
  plan: {
    plan_id: "plan_1",
    status: "active",
  },
  checkin: {
    ...completedResult.checkin,
    completed_task_count: 0,
    completed_subtask_count: 1,
    completed: true,
  },
};

const generatedHandout = {
  id: "gen_handout_1",
  user_id: "usr_123",
  course_id: "crs_123",
  study_subtask_id: "subtask_1",
  source_message_id: null,
  content_type: "handout",
  title: "向量空间今日讲义",
  content: "",
  content_json: {},
  generation_status: "success",
  material_scope_json: {
    include_all_parsed_materials: false,
    material_ids: ["mat_1"],
  },
  error_code: null,
  source_citations: [],
  created_at: "2026-07-13T03:00:00+00:00",
  updated_at: "2026-07-13T03:00:00+00:00",
  deleted_at: null,
};

const generatedTaskTest = {
  ...generatedHandout,
  id: "gen_task_test_1",
  study_subtask_id: "subtask_2",
  content_type: "task_test",
  title: "基础题任务测试题",
  content_json: {
    instructions: "只读查看题目与解析，作答记录暂不保存。",
    questions: [
      {
        id: "q_001",
        question_type: "single_choice",
        question_text: "向量空间必须满足哪类结构？",
        options: [
          { id: "A", text: "加法和数乘封闭" },
          { id: "B", text: "只能包含零向量" },
        ],
        correct_answer: "A",
        explanation: "向量空间需要对加法和数乘封闭，并满足对应公理。",
        source_citation_ids: [],
        sort_order: 1,
      },
    ],
  },
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

const parsedConfig = {
  goal_text: "两天复习线性代数第一章",
  start_date: "2026-07-13",
  end_date: "2026-07-14",
  duration_days: 2,
  daily_available_minutes: 90,
  recommended_daily_minutes: null,
  daily_minutes_source: "user_text",
  preference: "sprint",
  material_scope: {
    include_all_parsed_materials: true,
    material_ids: [],
  },
  unresolved_fields: [
    "start_date",
    "end_date",
    "duration_days",
    "daily_available_minutes",
    "recommended_daily_minutes",
    "daily_minutes_source",
    "preference",
    "diagnostic_profile",
    "material_snapshot",
    "coverage",
    "capacity",
    "generation_metadata",
  ],
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
          <Route element={<StudyTaskExecutionPage />} path="/study-subtasks/:subtaskId" />
          <Route element={<div>课程详情已返回</div>} path="/courses/:courseId" />
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

function installDownloadMocks() {
  Object.defineProperty(window.URL, "createObjectURL", {
    configurable: true,
    value: vi.fn(() => "blob:course-nexus-export"),
  });
  Object.defineProperty(window.URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
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
    expect(screen.getByRole("link", { name: "开始学习" })).toHaveAttribute("href", "/study-subtasks/subtask_1");

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

  it("uses the selected parsed material scope for parse and preview requests", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      if (url.endsWith("/study-plans/preview")) {
        return Promise.resolve(successResponse(preview, "req_preview"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return Promise.resolve(successResponse(parsedConfig, "req_config_parse"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderStudyPlanRoutes();

    await screen.findByRole("heading", { level: 1 });
    await screen.findByText("线代第一章.pdf");

    fireEvent.click(screen.getByTestId("scope-mode-specific"));
    expect(screen.getByLabelText("线代第一章.pdf")).toBeChecked();
    expect(screen.getByLabelText("未解析习题.pdf")).toBeDisabled();

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

    fireEvent.click(screen.getByTestId("study-plan-preview"));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plans/preview",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: preview.goal_text,
            start_date: "2026-07-13",
            end_date: "2026-07-15",
            daily_available_minutes: 60,
            preference: "balanced",
            material_scope: {
              include_all_parsed_materials: false,
              material_ids: ["mat_1"],
            },
          }),
          method: "POST",
        }),
      );
    });
    await waitFor(() => expect(screen.getByTestId("study-plan-save")).toBeEnabled());

    fireEvent.click(screen.getByTestId("scope-mode-all"));
    expect(screen.getByTestId("study-plan-save")).toBeDisabled();
    fireEvent.click(screen.getByTestId("scope-mode-specific"));

    fireEvent.click(screen.getByTestId("study-plan-parse-config"));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plan-config-parses",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: preview.goal_text,
            material_scope: {
              include_all_parsed_materials: false,
              material_ids: ["mat_1"],
            },
          }),
          method: "POST",
        }),
      );
    });

    expect(screen.getByTestId("study-plan-save")).toBeDisabled();
  });

  it("parses natural language config into editable fields and expires the existing preview", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plans/preview")) {
        return Promise.resolve(successResponse(preview, "req_preview"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return Promise.resolve(successResponse(parsedConfig, "req_config_parse"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "创建学习计划" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "今天是2026年7月13日，两天复习线性代数第一章，每天90分钟，冲刺强化" },
    });
    fireEvent.change(screen.getByLabelText("开始日期"), { target: { value: "2026-07-13" } });
    fireEvent.change(screen.getByLabelText("结束日期"), { target: { value: "2026-07-15" } });
    fireEvent.change(screen.getByLabelText("每日可用学习时长"), { target: { value: "60" } });

    fireEvent.click(screen.getByRole("button", { name: "生成预览" }));
    expect(await screen.findByText("第 1 天学习任务")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存计划" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "自动解析配置" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plan-config-parses",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "今天是2026年7月13日，两天复习线性代数第一章，每天90分钟，冲刺强化",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
          }),
          method: "POST",
        }),
      );
    });

    expect(screen.getByLabelText("学习目标")).toHaveValue("两天复习线性代数第一章");
    expect(screen.getByLabelText("开始日期")).toHaveValue("2026-07-13");
    expect(screen.getByLabelText("结束日期")).toHaveValue("2026-07-14");
    expect(screen.getByLabelText("每日可用学习时长")).toHaveValue(90);
    expect(screen.getByText("当前学习方式：冲刺强化。保存前可先查看任务预览。")).toBeInTheDocument();
    expect(screen.queryByText("开始日期：需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("结束日期：需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("学习天数：需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("每日可用学习时长：需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("recommended_daily_minutes: 需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("daily_minutes_source: 需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("diagnostic_profile: 需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("material_snapshot: 需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("coverage: 需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("capacity: 需手动补齐")).not.toBeInTheDocument();
    expect(screen.queryByText("generation_metadata: 需手动补齐")).not.toBeInTheDocument();
    expect(screen.getByText("配置已修改，请重新生成预览后保存。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存计划" })).toBeDisabled();
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
    expect(await screen.findByText("network timeout")).toBeInTheDocument();

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
    expect(screen.getByRole("link", { name: "进入学习：学习: 向量空间" })).toHaveAttribute(
      "href",
      "/study-subtasks/subtask_1",
    );
  });

  it("regenerates a preview and replaces the saved plan with expected updated time", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123")) {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plans/plan_1/regeneration-previews") && init?.method === "POST") {
        return Promise.resolve(successResponse(replacementPreview, "req_regeneration_preview"));
      }
      if (url.endsWith("/study-plans/plan_1") && init?.method === "PUT") {
        return Promise.resolve(successResponse(replacedDetail, "req_replace"));
      }
      if (url.endsWith("/study-plans/plan_1")) {
        return Promise.resolve(successResponse(savedDetail, "req_detail"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/courses/crs_123/study-plans/plan_1");

    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));
    expect(screen.getByRole("heading", { name: "调整并重新生成" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("调整目标"), {
      target: { value: replacementPreview.goal_text },
    });
    fireEvent.change(screen.getByLabelText("调整开始日期"), { target: { value: "2026-07-14" } });
    fireEvent.change(screen.getByLabelText("调整结束日期"), { target: { value: "2026-07-15" } });
    fireEvent.change(screen.getByLabelText("调整每日学习时长"), { target: { value: "90" } });
    fireEvent.change(screen.getByLabelText("调整学习方式"), { target: { value: "sprint" } });
    fireEvent.click(screen.getByRole("button", { name: "生成替换预览" }));

    expect(await screen.findByText("第 1 天强化任务")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认替换计划" }));

    expect(await screen.findByRole("heading", { name: "高等数学冲刺计划" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-plans/plan_1/regeneration-previews",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: replacementPreview.goal_text,
            start_date: "2026-07-14",
            end_date: "2026-07-15",
            daily_available_minutes: 90,
            preference: "sprint",
          }),
          method: "POST",
        }),
      );
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-plans/plan_1",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: replacementPreview.goal_text,
            start_date: replacementPreview.start_date,
            end_date: replacementPreview.end_date,
            daily_available_minutes: replacementPreview.daily_available_minutes,
            preference: replacementPreview.preference,
            material_scope: replacementPreview.material_scope,
            title: replacementPreview.title,
            client_flow: "wizard_v1",
            tasks: replacementPreview.tasks,
            expected_updated_at: savedDetail.plan.updated_at,
          }),
          method: "PUT",
        }),
      );
    });
  });

  it("deletes a study plan after confirmation and returns to the course detail page", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123")) {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plans/plan_1") && init?.method === "DELETE") {
        return Promise.resolve(
          successResponse({ ...savedDetail.plan, status: "deleted", deleted_at: "2026-07-13T11:00:00+00:00" }),
        );
      }
      if (url.endsWith("/study-plans/plan_1")) {
        return Promise.resolve(successResponse(savedDetail, "req_detail"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/courses/crs_123/study-plans/plan_1");

    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "删除计划" }));
    expect(screen.getByRole("heading", { name: "确认删除计划" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    expect(await screen.findByText("课程详情已返回")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-plans/plan_1",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });

  it("opens the execution page from a plan subtask and completes then uncompletes it", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123")) {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/study-plans/plan_1")) {
        return Promise.resolve(successResponse(savedDetail, "req_detail"));
      }
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContext, "req_execution"));
      }
      if (url.endsWith("/study-subtasks/subtask_1/completion") && init?.method === "PUT") {
        const body = JSON.parse(String(init.body)) as { completed: boolean };
        return Promise.resolve(successResponse(body.completed ? completedResult : uncompletedResult, "req_completion"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/courses/crs_123/study-plans/plan_1");

    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "进入学习：学习: 向量空间" }));

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    expect(screen.getByText("线代第一章.pdf")).toBeInTheDocument();
    expect(screen.getByText("第 1 天学习任务")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "完成任务" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "取消完成" })).toBeInTheDocument());
    expect(screen.getByText("打卡进度：2/2")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "取消完成" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "完成任务" })).toBeInTheDocument());

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_1/completion",
        expect.objectContaining({
          body: JSON.stringify({ completed: true }),
          method: "PUT",
        }),
      );
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_1/completion",
        expect.objectContaining({
          body: JSON.stringify({ completed: false }),
          method: "PUT",
        }),
      );
    });
  });

  it("asks the AI helper about the current subtask without changing material scope", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContext, "req_execution"));
      }
      if (url.endsWith("/study-subtasks/subtask_1/qa/questions") && init?.method === "POST") {
        return Promise.resolve(successResponse({
          conversation_id: "conv_task_1",
          user_message_id: "msg_user_1",
          assistant_message_id: "msg_assistant_1",
          answer_text: "先看线代第一章.pdf 的向量空间定义，再做基础题。",
          answer_type: "grounded",
          source_citations: [
            {
              id: "cite_1",
              material_id: "mat_1",
              material_name: "线代第一章.pdf",
              chunk_id: "chunk_1",
              hit_text: "向量空间定义",
              page: "3",
              page_index: 3,
              sort_order: 1,
            },
          ],
          used_material_ids: ["mat_1"],
        }, "req_task_qa"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "向 AI 助教提问" }), {
      target: { value: "这个任务先看哪份资料？" },
    });
    fireEvent.click(screen.getByRole("button", { name: "提问" }));

    expect(await screen.findByText("先看线代第一章.pdf 的向量空间定义，再做基础题。")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_1/qa/questions",
        expect.objectContaining({
          body: JSON.stringify({ conversation_id: null, question: "这个任务先看哪份资料？" }),
          method: "POST",
        }),
      );
    });
  });

  it("shows an existing handout link without generating new content", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContextWithHandout, "req_execution"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看任务讲义" })).toHaveAttribute(
      "href",
      "/generated-contents/gen_handout_1",
    );
    expect(screen.queryByRole("button", { name: "生成任务讲义" })).not.toBeInTheDocument();
  });

  it("exports an existing handout as a PDF file", async () => {
    installDownloadMocks();
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContextWithHandout, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_handout_1/exports/pdf")) {
        return Promise.resolve(
          new Response(new Blob(["%PDF"], { type: "application/pdf" }), {
            status: 200,
            headers: {
              "Content-Type": "application/pdf",
              "Content-Disposition": 'attachment; filename="handout-gen_handout_1.pdf"',
            },
          }),
        );
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "导出PDF" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/generated-contents/gen_handout_1/exports/pdf",
        expect.objectContaining({ method: "GET" }),
      );
    });
  });

  it("exports an existing task test as a Markdown file", async () => {
    installDownloadMocks();
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_2/execution-context")) {
        return Promise.resolve(successResponse(quizExecutionContextWithTaskTest, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_task_test_1/exports/markdown")) {
        return Promise.resolve(
          new Response(new Blob(["# 测试题"], { type: "text/markdown;charset=utf-8" }), {
            status: 200,
            headers: {
              "Content-Type": "text/markdown; charset=utf-8",
              "Content-Disposition": 'attachment; filename="task-test-gen_task_test_1.md"',
            },
          }),
        );
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_2");

    expect(await screen.findByRole("heading", { name: "练习: 基础题" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "导出Markdown" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/generated-contents/gen_task_test_1/exports/markdown",
        expect.objectContaining({ method: "GET" }),
      );
    });
  });

  it("generates a handout for learn and review subtasks", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContext, "req_execution"));
      }
      if (url.endsWith("/study-subtasks/subtask_1/handouts") && init?.method === "POST") {
        return Promise.resolve(successResponse(generatedHandout, "req_handout"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "生成任务讲义" }));

    expect(await screen.findByText("向量空间今日讲义")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看任务讲义" })).toHaveAttribute(
      "href",
      "/generated-contents/gen_handout_1",
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_1/handouts",
        expect.objectContaining({
          body: JSON.stringify({ force_regenerate: false }),
          method: "POST",
        }),
      );
    });
  });

  it("generates a task test for quiz and test subtasks", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_2/execution-context")) {
        return Promise.resolve(successResponse(quizExecutionContext, "req_execution"));
      }
      if (url.endsWith("/study-subtasks/subtask_2/task-tests") && init?.method === "POST") {
        return Promise.resolve(successResponse(generatedTaskTest, "req_task_test"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_2");

    expect(await screen.findByRole("heading", { name: "练习: 基础题" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "生成任务测试题" }));

    expect(await screen.findByText("基础题任务测试题")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看任务测试题" })).toHaveAttribute(
      "href",
      "/generated-contents/gen_task_test_1",
    );
    expect(screen.getByText("向量空间必须满足哪类结构？")).toBeInTheDocument();
    expect(screen.getByText("正确答案：A")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "提交答案" })).not.toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_2/task-tests",
        expect.objectContaining({
          body: JSON.stringify({ force_regenerate: false }),
          method: "POST",
        }),
      );
    });
  });
});
