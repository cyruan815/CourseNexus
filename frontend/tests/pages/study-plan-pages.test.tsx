import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StudyPlanCreatePage } from "../../src/pages/StudyPlanCreatePage";
import { StudyPlanDetailPage } from "../../src/pages/StudyPlanDetailPage";
import { StudyTaskExecutionPage } from "../../src/pages/StudyTaskExecutionPage";
import { StudyPlanTaskDescription } from "../../src/features/study-plans/components/StudyPlanTaskDescription";

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
  source_citations: [
    {
      id: "cite_handout_1",
      material_id: "mat_1",
      chunk_id: "chunk_1",
      material_name: "线代第一章.pdf",
      page: "3",
      page_index: 2,
      hit_text: "向量空间定义",
      sort_order: 1,
    },
  ],
  created_at: "2026-07-13T03:00:00+00:00",
  updated_at: "2026-07-13T03:00:00+00:00",
  deleted_at: null,
};

const generatedMarkdownHandout = {
  ...generatedHandout,
  content: [
    "# 向量空间讲义",
    "",
    "本讲义基于《线代第一章.pdf》中“学习: 向量空间”相关内容生成。",
    "",
    "## 学习目标",
    "",
    "- 理解 **向量空间** 的封闭性。",
    "",
    "## 延迟对比",
    "",
    "| 类型 | 计算方法 |",
    "| --- | --- |",
    "| 发送时延 | $d_{\\text{trans}} = \\frac{L}{R}$ |",
    "",
    "$$ d_{\\text{total}} = d_{\\text{proc}} + d_{\\text{queue}} + d_{\\text{trans}} + d_{\\text{prop}} $$",
    "",
    "> [!NOTE] 关键区别",
    "> 发送时延取决于分组长度和链路速率。",
  ].join("\n"),
  content_json: {
    format: "markdown",
    schema_version: 1,
  },
  source_citations: [],
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

const regeneratedTaskTest = {
  ...generatedTaskTest,
  id: "gen_task_test_2",
  title: "基础题任务测试题（重生成）",
  content_json: {
    instructions: "只读查看题目与解析，作答记录暂不保存。",
    questions: [
      {
        id: "q_001",
        question_type: "single_choice",
        question_text: "线性相关说明什么？",
        options: [
          { id: "A", text: "存在非零系数使线性组合为零" },
          { id: "B", text: "所有向量都为零" },
        ],
        correct_answer: "A",
        explanation: "线性相关表示存在不全为零的系数组合得到零向量。",
        source_citation_ids: [],
        sort_order: 1,
      },
    ],
  },
};
const diagnosticQuestions = {
  question_version: "study_plan_diagnostic_v2",
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
  question_version: "study_plan_diagnostic_v2",
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
          <Route element={<StudyTaskExecutionPage />} path="/study-subtasks/:subtaskId" />
          <Route element={<div>课程详情已返回</div>} path="/courses/:courseId" />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
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

function freezeStudyPlanDate() {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 6, 12, 12));
}

function deferredSuccessResponse(data: unknown, requestId = "req_deferred") {
  let resolve!: () => void;
  const promise = new Promise<Response>((next) => {
    resolve = () => next(successResponse(data, requestId));
  });
  return { promise, resolve };
}

describe("study plan pages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it("renders the create page inside the fixed workbench layout", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/courses/crs_123")) {
          return Promise.resolve(successResponse(course, "req_course"));
        }
        if (url.endsWith("/courses/crs_123/materials")) {
          return Promise.resolve(successResponse(materials, "req_materials"));
        }

        return Promise.resolve(successResponse({}));
      }),
    );

    const { container } = renderStudyPlanRoutes();

    await waitFor(() => expect(container.querySelector(".study-plan-create-flow")).toBeInTheDocument());
    expect(container.querySelector(".workbench-page")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar")).not.toBeInTheDocument();
    expect(container.querySelector(".study-plan-create-nav")).toBeInTheDocument();
    expect(container.querySelector(".study-plan-shell")).toHaveAttribute("data-workbench-scroll", "locked");
    expect(container.querySelector(".study-plan-create-shell")).toHaveClass("is-centered-flow");
    expect(container.querySelector(".study-plan-goal-card")).toBeInTheDocument();
    expect(container.querySelector(".study-plan-goal-input")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "返回上一步" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "回到课程详情" })).toHaveAttribute("href", "/courses/crs_123");
    expect(screen.getByText("创建学习计划 / 高等数学")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /切换为/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "打开个人中心" })).not.toBeInTheDocument();
  });

  it("shows a short questionnaire preparation animation while questions are loading", async () => {
    const parseDeferred = deferredSuccessResponse({
      goal_text: "复习线性代数第一章",
      start_date: null,
      end_date: null,
      duration_days: null,
      daily_available_minutes: null,
      preference: "balanced",
      material_scope: {
        include_all_parsed_materials: true,
        material_ids: [],
      },
      unresolved_fields: ["start_date", "duration_days"],
    }, "req_config_parse");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return parseDeferred.promise;
      }
      if (url.endsWith("/study-plan-diagnostic-questions")) {
        return Promise.resolve(successResponse(diagnosticQuestions, "req_diagnostic_questions"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/courses/crs_123/materials", expect.anything());
    });
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "复习线性代数第一章" },
    });
    fireEvent.click(screen.getByTestId("study-plan-goal-submit"));

    expect(await screen.findByText("正在整理问卷")).toBeInTheDocument();
    expect(screen.queryByText("理解目标")).not.toBeInTheDocument();
    expect(screen.queryByText("匹配资料")).not.toBeInTheDocument();
    expect(screen.queryByText("准备问题")).not.toBeInTheDocument();
    expect(screen.queryByText("+00.018")).not.toBeInTheDocument();

    parseDeferred.resolve();
    expect(await screen.findByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();
  });

  it("asks date follow-up questions when a new goal does not parse dates even if an old draft had dates", async () => {
    freezeStudyPlanDate();
    window.localStorage.setItem("course-nexus:study-plan-create:crs_123", JSON.stringify({
      goalText: "旧目标三天完成",
      startDate: "2026-07-15",
      endDate: "2026-07-17",
      durationDays: "3",
      preference: "balanced",
      materialScope: {
        include_all_parsed_materials: true,
        material_ids: [],
      },
    }));
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return Promise.resolve(successResponse({
          goal_text: "学习LAN",
          start_date: null,
          end_date: null,
          duration_days: null,
          daily_available_minutes: null,
          preference: "balanced",
          material_scope: {
            include_all_parsed_materials: true,
            material_ids: [],
          },
          unresolved_fields: ["start_date", "duration_days"],
        }, "req_config_parse"));
      }
      if (url.endsWith("/study-plan-diagnostic-questions")) {
        return Promise.resolve(successResponse(diagnosticQuestions, "req_diagnostic_questions"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "学习LAN" },
    });
    fireEvent.click(screen.getByTestId("study-plan-goal-submit"));

    expect(await screen.findByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();
    expect(screen.getByText("你想从哪天开始学习？")).toBeInTheDocument();
    expect(screen.queryByText(/2026-07-15 - 2026-07-17/)).not.toBeInTheDocument();
  });

  it("renders the detail page inside the fixed workbench layout", async () => {
    const otherPlan = {
      ...savedDetail.plan,
      id: "plan_2",
      title: "期末冲刺计划",
      goal_text: "集中复习错题",
      start_date: "2026-07-16",
      end_date: "2026-07-18",
      updated_at: "2026-07-14T12:00:00+00:00",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/courses/crs_123")) {
          return Promise.resolve(successResponse(course, "req_course"));
        }
        if (url.endsWith("/courses/crs_123/study-plans")) {
          return Promise.resolve(successResponse([savedDetail.plan, otherPlan], "req_plan_list"));
        }
        return Promise.resolve(successResponse(savedDetail, "req_detail"));
      }),
    );

    const { container } = renderStudyPlanRoutes("/courses/crs_123/study-plans/plan_1");

    await waitFor(() => expect(container.querySelector(".study-plan-detail-layout")).toBeInTheDocument());
    expect(container.querySelector(".workbench-page")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar")).toBeInTheDocument();
    expect(container.querySelector(".study-plan-shell")).toHaveAttribute("data-workbench-scroll", "locked");
    expect(container.querySelector(".workbench-topbar-left .workbench-back-button")).not.toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar-right .workbench-back-button")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar .workbench-actions")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回首页" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("button", { name: "返回" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "学习计划" })).toBeInTheDocument();
    expect(screen.getAllByText("高等数学学习计划").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /切换为/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开个人中心" })).toHaveAttribute("href", "/profile");
    expect(screen.queryByRole("heading", { name: "学习入口" })).not.toBeInTheDocument();
    expect(container.querySelector(".study-plan-course-layout")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "本课程计划" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /期末冲刺计划/ })).toHaveAttribute(
      "href",
      "/courses/crs_123/study-plans/plan_2",
    );
    expect(screen.getByRole("link", { name: /高等数学学习计划/ })).toHaveAttribute("aria-current", "page");
  });

  it("renders the execution page inside the fixed workbench layout", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
          return Promise.resolve(successResponse(executionContext, "req_execution"));
        }

        return Promise.resolve(successResponse({}));
      }),
    );

    const { container } = renderStudyPlanRoutes("/study-subtasks/subtask_1");

    await waitFor(() => expect(container.querySelector(".study-plan-execution-grid")).toBeInTheDocument());
    expect(container.querySelector(".workbench-page")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar")).toBeInTheDocument();
    expect(container.querySelector(".study-plan-execution-shell")).toHaveAttribute("data-workbench-scroll", "locked");
    expect(container.querySelector(".workbench-topbar-left .workbench-back-button")).not.toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar-right .workbench-back-button")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回首页" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("button", { name: "返回" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "任务执行" })).toBeInTheDocument();
    expect(screen.getAllByText("学习: 向量空间").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /切换为/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开个人中心" })).toHaveAttribute("href", "/profile");
    const sidebarHeader = container.querySelector(".study-plan-execution-sidebar-header");
    expect(sidebarHeader).toBeInTheDocument();
    expect(within(sidebarHeader as HTMLElement).getByRole("link", { name: "查看计划详情" })).toHaveAttribute(
      "href",
      "/courses/crs_123/study-plans/plan_1",
    );
    expect(container.querySelector(".study-plan-execution-taskrail .study-plan-plan-detail-link")).not.toBeInTheDocument();
    expect(container.querySelector(".study-plan-execution-main")).toHaveClass("has-pinned-completion");
    expect(container.querySelector(".study-plan-completion-actions")).toHaveClass("is-pinned-bottom");
    expect(container.querySelector(".study-plan-task-qa-response")).toBeInTheDocument();
    expect(container.querySelector(".study-plan-task-qa-composer")).toBeInTheDocument();
  });

  it("lets learners drag execution page gutters to resize the three columns", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
          return Promise.resolve(successResponse(executionContext, "req_execution"));
        }

        return Promise.resolve(successResponse({}));
      }),
    );

    const { container } = renderStudyPlanRoutes("/study-subtasks/subtask_1");

    const grid = await waitFor(() => {
      const executionGrid = container.querySelector(".study-plan-execution-grid") as HTMLElement | null;
      expect(executionGrid).toBeInTheDocument();
      return executionGrid as HTMLElement;
    });
    const leftGutter = screen.getByRole("separator", { name: "调整任务列表宽度" });

    fireEvent.mouseDown(leftGutter, { clientX: 300 });
    fireEvent.mouseMove(window, { clientX: 360 });
    fireEvent.mouseUp(window, { clientX: 360 });

    expect(grid.style.getPropertyValue("--study-plan-execution-left")).toBe("360px");
    expect(grid.style.getPropertyValue("--study-plan-execution-main")).toBe("545px");
    expect(window.localStorage.getItem("course-nexus:study-plan-execution-columns")).toContain("\"left\":360");
  });

  it("fits persisted execution column widths to the current grid", async () => {
    window.localStorage.setItem("course-nexus:study-plan-execution-columns", JSON.stringify({
      left: 500,
      main: 900,
      right: 500,
    }));
    const boundingRectSpy = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      bottom: 800,
      height: 800,
      left: 0,
      right: 1200,
      toJSON: () => ({}),
      top: 0,
      width: 1200,
      x: 0,
      y: 0,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
          return Promise.resolve(successResponse(executionContext, "req_execution"));
        }

        return Promise.resolve(successResponse({}));
      }),
    );

    const { container } = renderStudyPlanRoutes("/study-subtasks/subtask_1");
    const grid = await waitFor(() => {
      const executionGrid = container.querySelector(".study-plan-execution-grid") as HTMLElement | null;
      expect(executionGrid).toBeInTheDocument();
      expect(executionGrid?.style.getPropertyValue("--study-plan-execution-left")).not.toBe("500px");
      return executionGrid as HTMLElement;
    });
    const fittedTotal = ["left", "main", "right"].reduce((total, column) => (
      total + Number.parseInt(grid.style.getPropertyValue(`--study-plan-execution-${column}`), 10)
    ), 0);

    expect(fittedTotal).toBe(1180);
    expect(JSON.parse(window.localStorage.getItem("course-nexus:study-plan-execution-columns") ?? "{}")).toEqual({
      left: expect.any(Number),
      main: expect.any(Number),
      right: expect.any(Number),
    });
    boundingRectSpy.mockRestore();
  });

  it("turns a natural language goal into a mixed questionnaire, auto-saves, and enters detail after calendar preview", async () => {
    freezeStudyPlanDate();
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return Promise.resolve(successResponse({
          goal_text: "复习线性代数第一章",
          start_date: null,
          end_date: null,
          duration_days: null,
          daily_available_minutes: null,
          preference: "balanced",
          material_scope: {
            include_all_parsed_materials: true,
            material_ids: [],
          },
          unresolved_fields: ["start_date", "duration_days"],
        }, "req_config_parse"));
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

    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/courses/crs_123/materials", expect.anything());
    });
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "复习线性代数第一章" },
    });

    fireEvent.click(screen.getByTestId("study-plan-goal-submit"));
    expect(await screen.findByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();

    expect(screen.getByText("你想从哪天开始学习？")).toBeInTheDocument();
    expect(screen.getByLabelText(/A\. 今天/)).toBeInTheDocument();
    expect(screen.getByLabelText(/B\. 明天/)).toBeInTheDocument();
    expect(screen.getByLabelText(/C\. 下周一/)).toBeInTheDocument();
    expect(screen.getByLabelText(/D\. 自定义开始日期/)).toBeInTheDocument();
    expect(screen.getByText("这次计划准备学几天？")).toBeInTheDocument();
    expect(screen.getByLabelText(/A\. 2 天/)).toBeInTheDocument();
    expect(screen.getByLabelText(/D\. 自定义学习天数/)).toBeInTheDocument();
    expect(screen.getByText("你对「向量空间」了解多少？")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(/B\. 明天/));
    fireEvent.click(screen.getByLabelText(/A\. 2 天/));
    expect(screen.getByText("你想从哪天开始学习？")).toBeInTheDocument();
    expect(screen.getByText("这次计划准备学几天？")).toBeInTheDocument();
    expect(screen.queryByText(/2026-07-13 - 2026-07-14/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("听说过，但不清楚"));
    fireEvent.click(screen.getByLabelText("概念理解"));
    fireEvent.change(screen.getByLabelText("还有什么想特别补的地方？"), {
      target: { value: "希望先补基础" },
    });
    fireEvent.click(screen.getByTestId("study-plan-questionnaire-submit"));

    expect(await screen.findByText("第 1 天学习任务")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "进入计划" }));
    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
    expect(screen.getByText("学习: 向量空间")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "开始学习" })).toHaveAttribute("href", "/study-subtasks/subtask_1");

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plan-config-parses",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "复习线性代数第一章",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
          }),
          method: "POST",
        }),
      );
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plan-diagnostic-questions",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "复习线性代数第一章",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
            confirmed_config: {
              start_date: null,
              duration_days: null,
              preference: "balanced",
              daily_available_minutes: null,
              daily_minutes_source: null,
            },
          }),
          method: "POST",
        }),
      );
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plan-diagnostic-profiles",
        expect.objectContaining({
          body: JSON.stringify({
            question_version: "study_plan_diagnostic_v2",
            topic_mastery: [
              {
                topic_id: "topic_vector_space",
                topic_title: "向量空间",
                mastery_level: "heard",
              },
            ],
            weak_area: "concept",
            diagnostic_note: "希望先补基础",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
          }),
          method: "POST",
        }),
      );
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plans/preview",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "复习线性代数第一章",
            preference: "balanced",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
            start_date: "2026-07-13",
            end_date: "2026-07-14",
            diagnostic_profile: diagnosticProfile,
          }),
          method: "POST",
        }),
      );
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-plans",
        expect.objectContaining({
          body: JSON.stringify({
            goal_text: "复习线性代数第一章",
            preference: "balanced",
            material_scope: {
              include_all_parsed_materials: true,
              material_ids: [],
            },
            start_date: "2026-07-13",
            end_date: "2026-07-14",
            diagnostic_profile: diagnosticProfile,
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

  it("reuses the prepared save payload and idempotency key after a lost save response", async () => {
    freezeStudyPlanDate();
    const saveRequests: RequestInit[] = [];
    let saveAttemptCount = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return Promise.resolve(successResponse({
          goal_text: "复习线性代数第一章",
          start_date: null,
          end_date: null,
          duration_days: null,
          daily_available_minutes: null,
          preference: "balanced",
          material_scope: {
            include_all_parsed_materials: true,
            material_ids: [],
          },
          unresolved_fields: ["start_date", "duration_days"],
        }, "req_config_parse"));
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
      if (url.endsWith("/courses/crs_123/study-plans") && init?.method === "POST") {
        saveRequests.push(init);
        saveAttemptCount += 1;
        if (saveAttemptCount === 1) {
          return Promise.reject(new TypeError("模拟保存响应丢失"));
        }
        return Promise.resolve(successResponse(savedDetail, "req_save"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();
    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/courses/crs_123/materials", expect.anything());
    });
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "复习线性代数第一章" },
    });
    fireEvent.click(screen.getByTestId("study-plan-goal-submit"));
    expect(await screen.findByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/B\. 明天/));
    fireEvent.click(screen.getByLabelText(/A\. 2 天/));
    fireEvent.click(screen.getByLabelText("听说过，但不清楚"));
    fireEvent.click(screen.getByLabelText("概念理解"));

    fireEvent.click(screen.getByTestId("study-plan-questionnaire-submit"));
    expect(await screen.findByText("模拟保存响应丢失")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("study-plan-questionnaire-submit"));
    expect(await screen.findByRole("button", { name: "进入计划" })).toBeInTheDocument();

    expect(saveRequests).toHaveLength(2);
    expect(saveRequests[0]?.body).toBe(saveRequests[1]?.body);
    expect((saveRequests[0]?.headers as Record<string, string>)["Idempotency-Key"]).toBe(
      (saveRequests[1]?.headers as Record<string, string>)["Idempotency-Key"],
    );
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/study-plan-diagnostic-profiles"))).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/study-plans/preview"))).toHaveLength(1);
    expect(window.localStorage.getItem("course-nexus:study-plan-create:crs_123")).toBeNull();
  });

  it("shows a calendar planning animation while the plan is being generated", async () => {
    freezeStudyPlanDate();
    const profileDeferred = deferredSuccessResponse(diagnosticProfile, "req_diagnostic_profile");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return Promise.resolve(successResponse({
          goal_text: "复习线性代数第一章",
          start_date: null,
          end_date: null,
          duration_days: null,
          daily_available_minutes: null,
          preference: "balanced",
          material_scope: {
            include_all_parsed_materials: true,
            material_ids: [],
          },
          unresolved_fields: ["start_date", "duration_days"],
        }, "req_config_parse"));
      }
      if (url.endsWith("/study-plan-diagnostic-questions")) {
        return Promise.resolve(successResponse(diagnosticQuestions, "req_diagnostic_questions"));
      }
      if (url.endsWith("/study-plan-diagnostic-profiles")) {
        return profileDeferred.promise;
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

    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/courses/crs_123/materials", expect.anything());
    });
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "复习线性代数第一章" },
    });
    fireEvent.click(screen.getByTestId("study-plan-goal-submit"));
    expect(await screen.findByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/B\. 明天/));
    fireEvent.click(screen.getByLabelText(/A\. 2 天/));
    fireEvent.click(screen.getByLabelText("听说过，但不清楚"));
    fireEvent.click(screen.getByLabelText("概念理解"));

    fireEvent.click(screen.getByTestId("study-plan-questionnaire-submit"));

    expect(await screen.findByText("正在拆分每日任务")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上个月" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下个月" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /选择年月|Today|应用/ })).not.toBeInTheDocument();
    expect(screen.getByText("July 2026")).toBeInTheDocument();
    expect(screen.getByText("生成学习计划")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith("/api/v1/courses/crs_123/study-calendar?month=2026-07", expect.anything());
    expect(screen.getByRole("grid", { name: "生成中的计划日历" })).toBeInTheDocument();
    expect(screen.queryByText("日期冲突")).not.toBeInTheDocument();
    expect(screen.queryByText("汇总问卷答案")).not.toBeInTheDocument();
    expect(screen.queryByText("保存学习计划")).not.toBeInTheDocument();
    expect(screen.queryByText("第 1 天学习任务")).not.toBeInTheDocument();

    profileDeferred.resolve();
    expect(await screen.findByText("第 1 天学习任务")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "高等数学学习计划" })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "进入计划" }));
    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
  });

  it("shows recoverable messages when automatic plan generation fails", async () => {
    freezeStudyPlanDate();
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      if (url.endsWith("/study-plan-config-parses")) {
        return Promise.resolve(successResponse({
          goal_text: "复习线性代数第一章",
          start_date: null,
          end_date: null,
          duration_days: null,
          daily_available_minutes: null,
          preference: "balanced",
          material_scope: {
            include_all_parsed_materials: true,
            material_ids: [],
          },
          unresolved_fields: ["start_date", "duration_days"],
        }, "req_config_parse"));
      }
      if (url.endsWith("/study-plan-diagnostic-questions")) {
        return Promise.resolve(successResponse(diagnosticQuestions, "req_diagnostic_questions"));
      }
      if (url.endsWith("/study-plan-diagnostic-profiles")) {
        return Promise.resolve(successResponse(diagnosticProfile, "req_diagnostic_profile"));
      }
      if (url.endsWith("/study-plans/preview")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              error: {
                code: "NO_PARSED_MATERIAL",
                message: "backend raw no material",
                details: {},
              },
              meta: { request_id: "req_no_material" },
            }),
            { status: 400, headers: { "Content-Type": "application/json" } },
          ),
        );
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes();
    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/courses/crs_123/materials", expect.anything());
    });
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "复习线性代数第一章" },
    });
    fireEvent.click(screen.getByTestId("study-plan-goal-submit"));
    expect(await screen.findByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/B\. 明天/));
    fireEvent.click(screen.getByLabelText(/A\. 2 天/));
    fireEvent.click(screen.getByLabelText("听说过，但不清楚"));
    fireEvent.click(screen.getByLabelText("概念理解"));

    fireEvent.click(screen.getByTestId("study-plan-questionnaire-submit"));

    expect(await screen.findByText("当前资料还没有可用解析结果，请先上传或等待至少一份资料解析完成。")).toBeInTheDocument();
    expect(screen.queryByText("backend raw no material")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "开始前确认一下" })).toBeInTheDocument();
  });

  it("keeps the plan draft after refreshing the create page", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/crs_123") && init?.method !== "POST") {
        return Promise.resolve(successResponse(course, "req_course"));
      }
      if (url.endsWith("/courses/crs_123/materials")) {
        return Promise.resolve(successResponse(materials, "req_materials"));
      }
      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("学习目标"), {
      target: { value: "三天完成线性代数第一章复习" },
    });

    unmount();
    renderStudyPlanRoutes();

    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
    expect(screen.getByLabelText("学习目标")).toHaveValue("三天完成线性代数第一章复习");
    expect(screen.queryByText(/2026-07-13 - 2026-07-15/)).not.toBeInTheDocument();
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
    const topbar = document.querySelector(".workbench-topbar");
    expect(topbar).not.toBeNull();
    expect(within(topbar as HTMLElement).queryByRole("button", { name: "重新生成" })).not.toBeInTheDocument();
    expect(within(topbar as HTMLElement).queryByRole("button", { name: "删除计划" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "学习入口" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "导出计划（待接入）" })).not.toBeInTheDocument();
    expect(screen.getByText("阅读并整理概念")).toBeInTheDocument();
    expect(screen.queryByText("含义")).not.toBeInTheDocument();
    expect(document.querySelector(".study-plan-task-structure-panel")).toBeInTheDocument();
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
    expect(screen.getByText("进度")).toBeInTheDocument();
    expect(screen.getAllByText("2/2").length).toBeGreaterThan(0);

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
          answer_text: "先看线代第一章.pdf 的向量空间定义，再做基础题。 [[cite:1]]",
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

    expect(await screen.findByText("先看线代第一章.pdf 的向量空间定义，再做基础题。", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText(/\[\[cite:1\]\]/)).not.toBeInTheDocument();
    const citationMarker = screen.getByRole("button", { name: "查看引用 1：线代第一章.pdf" });
    fireEvent.mouseEnter(citationMarker);
    await waitFor(() => expect(screen.getByLabelText("引用 1 详情")).toHaveStyle({ opacity: "1" }));
    const citationTooltip = screen.getByLabelText("引用 1 详情");
    expect(citationTooltip).toHaveTextContent("第 3 页");
    expect(citationTooltip).toHaveTextContent("向量空间定义");
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

  it("switches subtasks inside the execution workspace without leaving the page", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContext, "req_execution_1"));
      }
      if (url.endsWith("/study-subtasks/subtask_2/execution-context")) {
        return Promise.resolve(successResponse(quizExecutionContext, "req_execution_2"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /切换到任务/ })[1]);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_2/execution-context",
        expect.objectContaining({ method: "GET" }),
      );
    });
    expect(screen.getByRole("button", { name: /完成|瀹屾垚/ })).toBeInTheDocument();
  });

  it("shows an existing handout preview without generating new content", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContextWithHandout, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_handout_1")) {
        return Promise.resolve(successResponse(generatedHandout, "req_generated_content"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "查看任务讲义" })).not.toBeInTheDocument();
    expect(await screen.findByText("向量空间今日讲义")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "生成任务讲义" })).not.toBeInTheDocument();
  });

  it("renders an existing handout Markdown body inside the execution page", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContextWithHandout, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_handout_1")) {
        return Promise.resolve(successResponse(generatedMarkdownHandout, "req_generated_content"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "向量空间讲义" })).toBeInTheDocument();
    expect(screen.getByText("向量空间")).toBeInTheDocument();
    expect(screen.getByText("的封闭性。", { exact: false })).toBeInTheDocument();
    const renderedTable = document.querySelector(".study-plan-handout-preview table");
    expect(renderedTable).not.toBeNull();
    expect(renderedTable?.querySelector("th")?.textContent).toBe("类型");
    expect(renderedTable?.textContent).toContain("发送时延");
    expect(document.querySelector(".study-plan-handout-preview .katex")).not.toBeNull();
    expect(screen.queryByText("$$", { exact: false })).not.toBeInTheDocument();
    expect(screen.getByTestId("handout-callout-note")).toHaveTextContent("关键区别");
    expect(screen.getByTestId("handout-callout-note")).toHaveTextContent("发送时延取决于分组长度和链路速率。");
    expect(screen.queryByText("当前没有可展示的引用来源")).not.toBeInTheDocument();
  });

  it("keeps a regeneration failure after an older detail request resolves", async () => {
    let resolveDetail: ((value: Response) => void) | undefined;
    const pendingDetail = new Promise<Response>((resolve) => {
      resolveDetail = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContextWithHandout, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_handout_1")) {
        return pendingDetail;
      }
      if (url.endsWith("/study-subtasks/subtask_1/handouts") && init?.method === "POST") {
        return Promise.resolve(new Response(JSON.stringify({
          error: { code: "GENERATION_FAILED", message: "生成失败" },
        }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        }));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/generated-contents/gen_handout_1",
        expect.objectContaining({ method: "GET" }),
      );
    });
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));

    expect(await screen.findByRole("alert", { name: "内容生成失败" })).toBeInTheDocument();
    resolveDetail?.(successResponse(generatedHandout, "req_stale_detail"));

    await waitFor(() => {
      expect(screen.getByRole("alert", { name: "内容生成失败" })).toBeInTheDocument();
    });
    expect(screen.queryByText("向量空间今日讲义")).not.toBeInTheDocument();
  });

  it("does not let an older detail request overwrite regenerated content", async () => {
    let resolveDetail: ((value: Response) => void) | undefined;
    const pendingDetail = new Promise<Response>((resolve) => {
      resolveDetail = resolve;
    });
    const regeneratedHandout = {
      ...generatedHandout,
      id: "gen_handout_2",
      title: "向量空间新讲义",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContextWithHandout, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_handout_1")) {
        return pendingDetail;
      }
      if (url.endsWith("/study-subtasks/subtask_1/handouts") && init?.method === "POST") {
        return Promise.resolve(successResponse(regeneratedHandout, "req_regenerated"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/generated-contents/gen_handout_1",
        expect.objectContaining({ method: "GET" }),
      );
    });
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));

    expect(await screen.findByText("向量空间新讲义")).toBeInTheDocument();
    resolveDetail?.(successResponse(generatedHandout, "req_stale_detail"));

    await waitFor(() => {
      expect(screen.getByText("向量空间新讲义")).toBeInTheDocument();
    });
    expect(screen.queryByText("向量空间今日讲义")).not.toBeInTheDocument();
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
    expect(screen.queryByRole("link", { name: "查看任务讲义" })).not.toBeInTheDocument();

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
        const body = JSON.parse(String(init.body)) as { force_regenerate: boolean };
        return Promise.resolve(successResponse(body.force_regenerate ? regeneratedTaskTest : generatedTaskTest, "req_task_test"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_2");

    expect(await screen.findByRole("heading", { name: "练习: 基础题" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "生成任务测试题" }));

    expect(await screen.findByText("基础题任务测试题")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "查看任务测试题" })).not.toBeInTheDocument();
    expect(screen.getByText("向量空间必须满足哪类结构？")).toBeInTheDocument();
    expect(screen.queryByText("正确答案：A")).not.toBeInTheDocument();
    const generatedTaskTestCard = screen.getByLabelText("第 1 题：向量空间必须满足哪类结构？");
    fireEvent.click(within(generatedTaskTestCard).getByRole("button", { name: "A. 加法和数乘封闭" }));
    fireEvent.click(within(generatedTaskTestCard).getByRole("button", { name: "提交答案" }));
    expect(within(generatedTaskTestCard).getByText("回答正确")).toBeInTheDocument();
    expect(within(generatedTaskTestCard).getByText("正确答案：A")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));
    expect(await screen.findByText("基础题任务测试题（重生成）")).toBeInTheDocument();
    const regeneratedTaskTestCard = screen.getByLabelText("第 1 题：线性相关说明什么？");
    expect(within(regeneratedTaskTestCard).getByRole("button", { name: "A. 存在非零系数使线性组合为零" })).not.toBeDisabled();
    expect(within(regeneratedTaskTestCard).getByRole("button", { name: "B. 所有向量都为零" })).not.toBeDisabled();
    expect(within(regeneratedTaskTestCard).getByRole("button", { name: "提交答案" })).toBeDisabled();
    expect(within(regeneratedTaskTestCard).queryByText("正确答案：A")).not.toBeInTheDocument();
    expect(within(regeneratedTaskTestCard).queryByText("解析：线性相关表示存在不全为零的系数组合得到零向量。")).not.toBeInTheDocument();

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

  it("generates switched task content concurrently and keeps results independent", async () => {
    let resolveHandout: ((value: Response) => void) | undefined;
    let resolveTaskTest: ((value: Response) => void) | undefined;
    const pendingHandout = new Promise<Response>((resolve) => {
      resolveHandout = resolve;
    });
    const pendingTaskTest = new Promise<Response>((resolve) => {
      resolveTaskTest = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_1/execution-context")) {
        return Promise.resolve(successResponse(executionContext, "req_execution"));
      }
      if (url.endsWith("/study-subtasks/subtask_2/execution-context")) {
        return Promise.resolve(successResponse(quizExecutionContextWithTaskTest, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_task_test_1")) {
        return Promise.resolve(successResponse(generatedTaskTest, "req_generated_content"));
      }
      if (url.endsWith("/study-subtasks/subtask_1/handouts") && init?.method === "POST") {
        return pendingHandout;
      }
      if (url.endsWith("/study-subtasks/subtask_2/task-tests") && init?.method === "POST") {
        return pendingTaskTest;
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_1");

    expect(await screen.findByRole("heading", { name: "学习: 向量空间" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "生成任务讲义" }));
    fireEvent.click(screen.getByRole("button", { name: /切换到任务 练习: 基础题/ }));

    expect(await screen.findByRole("heading", { name: "练习: 基础题" })).toBeInTheDocument();
    expect(await screen.findByText("基础题任务测试题")).toBeInTheDocument();
    expect(screen.getByText("已切换任务；原任务内容仍在后台生成，不会影响当前页面。")).toBeInTheDocument();
    expect(screen.getByText("其他任务的内容也在后台生成中，完成后会自动保存到对应任务。")).toBeInTheDocument();
    expect(screen.getByText("向量空间必须满足哪类结构？")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_1/handouts",
        expect.objectContaining({ method: "POST" }),
      );
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/study-subtasks/subtask_2/task-tests",
        expect.objectContaining({ method: "POST" }),
      );
    });

    resolveHandout?.(successResponse(generatedHandout, "req_handout"));
    resolveTaskTest?.(successResponse(generatedTaskTest, "req_task_test"));

    await waitFor(() => {
      expect(screen.queryByText("已切换任务；原任务内容仍在后台生成，不会影响当前页面。")).not.toBeInTheDocument();
    });
    expect(screen.queryByText("其他任务的内容也在后台生成中，完成后会自动保存到对应任务。")).not.toBeInTheDocument();
    expect(screen.getByText("基础题任务测试题")).toBeInTheDocument();
    expect(screen.queryByText("向量空间今日讲义")).not.toBeInTheDocument();
  });

  it("loads an existing task test detail when reopening the execution page", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-subtasks/subtask_2/execution-context")) {
        return Promise.resolve(successResponse(quizExecutionContextWithTaskTest, "req_execution"));
      }
      if (url.endsWith("/generated-contents/gen_task_test_1")) {
        return Promise.resolve(successResponse(generatedTaskTest, "req_generated_content"));
      }

      return Promise.resolve(successResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderStudyPlanRoutes("/study-subtasks/subtask_2");

    expect(await screen.findByText("基础题任务测试题")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "查看任务测试题" })).not.toBeInTheDocument();
    expect(screen.getByText("向量空间必须满足哪类结构？")).toBeInTheDocument();
    expect(screen.queryByText("正确答案：A")).not.toBeInTheDocument();
    const existingTaskTestCard = screen.getByLabelText("第 1 题：向量空间必须满足哪类结构？");
    fireEvent.click(within(existingTaskTestCard).getByRole("button", { name: "A. 加法和数乘封闭" }));
    fireEvent.click(within(existingTaskTestCard).getByRole("button", { name: "提交答案" }));
    expect(within(existingTaskTestCard).getByText("回答正确")).toBeInTheDocument();
    expect(within(existingTaskTestCard).getByText("正确答案：A")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/generated-contents/gen_task_test_1",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("keeps plain task descriptions intact and splits generic labeled descriptions", () => {
    const { rerender } = render(
      <MantineProvider>
        <StudyPlanTaskDescription description="阅读材料后完成两道练习，条件：如果时间不够就先做基础题。" />
      </MantineProvider>,
    );

    expect(screen.getByText("阅读材料后完成两道练习，条件：如果时间不够就先做基础题。")).toBeInTheDocument();
    expect(screen.queryByText("条件")).not.toBeInTheDocument();

    rerender(
      <MantineProvider>
        <StudyPlanTaskDescription description="目标：理解局域网核心概念。方法：画出流程图。检查：完成口头复述。" />
      </MantineProvider>,
    );

    expect(screen.getByText("目标")).toBeInTheDocument();
    expect(screen.getByText("理解局域网核心概念。")).toBeInTheDocument();
    expect(screen.getByText("方法")).toBeInTheDocument();
    expect(screen.getByText("画出流程图。")).toBeInTheDocument();
    expect(screen.getByText("检查")).toBeInTheDocument();
    expect(screen.getByText("完成口头复述。")).toBeInTheDocument();
  });
});
