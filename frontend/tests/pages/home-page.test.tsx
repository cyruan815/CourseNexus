import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TOKEN_STORAGE_KEY } from "../../src/features/auth/session";
import { THEME_STORAGE_KEY } from "../../src/app/theme";
import type { Course } from "../../src/types/course";
import { HomePage } from "../../src/pages/HomePage";

const backendCourses: Course[] = [
  {
    id: "crs_discrete_math",
    user_id: "usr_123",
    name: "离散数学",
    description: "图论和组合数学复习",
    teacher: "周老师",
    term: "2025-2026-spring",
    status: "active",
    created_at: "2026-07-09T12:00:00+00:00",
    updated_at: "2026-07-09T12:00:00+00:00",
    deleted_at: null,
  },
  {
    id: "crs_os",
    user_id: "usr_123",
    name: "操作系统",
    description: null,
    teacher: null,
    term: null,
    status: "active",
    created_at: "2026-07-10T12:00:00+00:00",
    updated_at: "2026-07-10T12:00:00+00:00",
    deleted_at: null,
  },
  {
    id: "crs_algorithm",
    user_id: "usr_123",
    name: "算法设计",
    description: "图算法和复杂度分析",
    teacher: "李老师",
    term: "2025-2026-autumn",
    status: "active",
    created_at: "2026-07-11T12:00:00+00:00",
    updated_at: "2026-07-11T12:00:00+00:00",
    deleted_at: null,
  },
];

const backendTermOptions = [
  { value: "2027-2028-autumn", label: "2027-2028 秋季" },
  { value: "2027-2028-spring", label: "2027-2028 春季" },
  { value: "2026-2027-autumn", label: "2026-2027 秋季" },
  { value: "2026-2027-spring", label: "2026-2027 春季" },
  { value: "2025-2026-autumn", label: "2025-2026 秋季" },
  { value: "2025-2026-spring", label: "2025-2026 春季" },
  { value: "2024-2025-autumn", label: "2024-2025 秋季" },
  { value: "2024-2025-spring", label: "2024-2025 春季" },
];

function jsonResponse(data: unknown, requestId = "req_test") {
  return Promise.resolve(
    new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function createHomeFetchMock(courses = backendCourses) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/course-terms") {
      return jsonResponse(backendTermOptions, "req_terms");
    }

    if (url.startsWith("/api/v1/todos/today")) {
      return jsonResponse({ date: "2026-07-14", tasks: [] }, "req_today_todos");
    }

    if (url.startsWith("/api/v1/calendar/month")) {
      return jsonResponse({
        month: "2026-07",
        days: [
          {
            date: "2026-07-15",
            course_count: 1,
            task_count: 1,
            subtask_count: 2,
            completed_subtask_count: 0,
            status: "not_started",
            task_summaries: [
              {
                task_id: "task_calendar",
                plan_id: "plan_calendar",
                course_id: "crs_discrete_math",
                course_name: "离散数学",
                title: "组合数学复习",
                status: "not_started",
                derived_status: "not_started",
                sort_order: 1,
              },
              {
                task_id: "task_calendar_extra",
                plan_id: "plan_calendar",
                course_id: "crs_discrete_math",
                course_name: "离散数学",
                title: "图论复习",
                status: "not_started",
                derived_status: "not_started",
                sort_order: 2,
              },
            ],
            hidden_task_count: 1,
          },
        ],
      }, "req_month_calendar");
    }

    return jsonResponse(courses, "req_courses");
  });
}

function LocationProbe() {
  const location = useLocation();

  return (
    <>
      <span data-testid="location-path">{location.pathname}</span>
      <span data-testid="location-state">{JSON.stringify(location.state ?? null)}</span>
    </>
  );
}

function renderHomePage() {
  render(
    <MantineProvider>
      <MemoryRouter>
        <HomePage />
        <LocationProbe />
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("HomePage", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 6, 14, 12));
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("loads courses from the backend and renders real course links", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const fetchMock = createHomeFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    renderHomePage();

    expect(screen.getByRole("heading", { name: "课枢 CourseNexus" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今日待办" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "日历" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "课程概览" })).toBeInTheDocument();
    expect(screen.getByText("正在加载课程...")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "离散数学" })).toHaveAttribute(
      "href",
      "/courses/crs_discrete_math",
    );
    expect(screen.getByRole("link", { name: "打开课程 离散数学" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "操作系统" })).toHaveAttribute("href", "/courses/crs_os");
    expect(screen.getByRole("link", { name: "算法设计" })).toHaveAttribute("href", "/courses/crs_algorithm");
    expect(screen.getByText("全部学期 3 门课程 · 资料统计待接入")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token-home" }),
      }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/course-terms",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token-home" }),
      }),
    );
    expect(screen.getByText("今天还没有学习计划")).toBeInTheDocument();
    expect(screen.queryByText("1 项待安排")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "生成今日计划" })).not.toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: "打开 2026-07-01 的日历" })).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: "打开 2026-07-15 的日历" })).toBeInTheDocument();
    expect(screen.queryByText("暂无计划")).not.toBeInTheDocument();
    expect(screen.getByText("添加课程")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开个人中心" })).toHaveAttribute("href", "/profile");
  });

  it("loads today's todos from the backend and links tasks to execution pages", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/course-terms") {
        return jsonResponse(backendTermOptions, "req_terms");
      }
      if (url === "/api/v1/courses") {
        return jsonResponse(backendCourses, "req_courses");
      }
      if (url.startsWith("/api/v1/calendar/month")) {
        return jsonResponse({ month: "2026-07", days: [] }, "req_month_calendar");
      }
      if (url.startsWith("/api/v1/todos/today")) {
        return jsonResponse({
          date: "2026-07-14",
          tasks: [
            {
              task_id: "task_1",
              plan_id: "plan_1",
              course_id: "crs_discrete_math",
              course_name: "离散数学",
              title: "图论复习",
              task_date: "2026-07-14",
              status: "in_progress",
              derived_status: "in_progress",
              completed_subtask_count: 1,
              total_subtask_count: 3,
              first_incomplete_subtask_id: "subtask_2",
              subtasks: [
                {
                  subtask_id: "subtask_1",
                  title: "学习: 图的基本概念",
                  subtask_type: "learn",
                  description: "整理定义",
                  status: "completed",
                  sort_order: 1,
                  execution_url: null,
                },
              ],
            },
          ],
        }, "req_today_todos");
      }

      return jsonResponse([], "req_fallback");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderHomePage();

    expect(await screen.findByRole("link", { name: "继续学习 图论复习" })).toHaveAttribute(
      "href",
      "/study-subtasks/subtask_2",
    );
    expect(screen.getByRole("link", { name: "离散数学" })).toBeInTheDocument();
    expect(screen.getByText("1/3 个二级任务完成")).toBeInTheDocument();
    expect(screen.queryByText("今天还没有学习计划")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/todos/today?date=2026-07-14",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("shows material and task status on course cards without the created status text", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal("fetch", createHomeFetchMock([{
      ...backendCourses[0],
      material_count: 3,
      name: "Course Card",
      today_task_status: "has_task_today",
    }]));

    renderHomePage();

    expect(await screen.findByRole("link", { name: "Course Card" })).toBeInTheDocument();
    expect(screen.getByText("资料 3 份")).toBeInTheDocument();
    expect(screen.getByText("今日有任务")).toBeInTheDocument();
    expect(screen.queryByText("资料状态待同步")).not.toBeInTheDocument();
    expect(screen.queryByText("今日任务待同步")).not.toBeInTheDocument();
    expect(screen.queryByText("课程已创建")).not.toBeInTheDocument();
  });

  it("maps course list aggregate statuses without per-course study-plan requests", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const fetchMock = createHomeFetchMock([
      { ...backendCourses[0], id: "crs_no_plan", material_count: 0, name: "No Plan", today_task_status: "no_study_plan" },
      { ...backendCourses[1], id: "crs_no_task", material_count: 1, name: "No Task", today_task_status: "no_task_today" },
      { ...backendCourses[2], id: "crs_has_task", material_count: 2, name: "Has Task", today_task_status: "has_task_today" },
    ]);
    vi.stubGlobal("fetch", fetchMock);

    renderHomePage();

    expect(await screen.findByRole("link", { name: "No Plan" })).toBeInTheDocument();
    expect(screen.getByText("资料 0 份")).toBeInTheDocument();
    expect(screen.getByText("资料 1 份")).toBeInTheDocument();
    expect(screen.getByText("资料 2 份")).toBeInTheDocument();
    expect(screen.getByText("无学习计划")).toBeInTheDocument();
    expect(screen.getByText("今日无任务")).toBeInTheDocument();
    expect(screen.getByText("今日有任务")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/study-plans"))).toBe(false);
  });

  it("keeps pending badges before the course list aggregate fields are available", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal("fetch", createHomeFetchMock([{
      ...backendCourses[0],
      name: "Course Card",
    }]));

    renderHomePage();

    expect(await screen.findByRole("link", { name: "Course Card" })).toBeInTheDocument();
    expect(screen.getByText("资料状态待同步")).toBeInTheDocument();
    expect(screen.getByText("今日任务待同步")).toBeInTheDocument();
    expect(screen.queryByText("资料待接入")).not.toBeInTheDocument();
    expect(screen.queryByText("今日任务待接入")).not.toBeInTheDocument();
    expect(screen.queryByText("课程已创建")).not.toBeInTheDocument();
  });

  it("keeps long course card text inspectable without relying on the visible layout", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const longDescription = "12345678901234567890123456789012345678901234567890";
    vi.stubGlobal("fetch", createHomeFetchMock([{
      ...backendCourses[0],
      description: longDescription,
      name: "Very Very Long Course",
    }]));

    renderHomePage();

    expect(await screen.findByRole("link", { name: "Very Very Long Course" })).toHaveAttribute("title", "Very Very Long Course");
    expect(screen.getByText(longDescription)).toHaveAttribute("title", longDescription);
  });

  it("lets the month calendar navigate without fake empty-state overlays", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal("fetch", createHomeFetchMock());

    renderHomePage();

    await screen.findByRole("link", { name: "离散数学" });
    expect(screen.queryByText("暂无计划")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /下个月/ }));
    expect(screen.getByRole("button", { name: /2026 年 8 月/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /上个月/ }));
    expect(screen.getByRole("button", { name: /2026 年 7 月/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /2026 年 7 月/ }));
    expect(screen.queryByRole("dialog", { name: "选择年月" })).not.toBeInTheDocument();
    await waitFor(() => expect(document.querySelector(".home-month-picker")).toBeInTheDocument());
    fireEvent.click(document.querySelector('[aria-label="关闭年月选择"]') as HTMLElement);
    const calendarTaskTitle = await screen.findByText("组合数学复习");
    expect(calendarTaskTitle).toHaveClass("home-calendar-task-title");
    expect(calendarTaskTitle).toHaveAttribute("title", "组合数学复习");
    expect(calendarTaskTitle.closest(".home-calendar-cell-summary")).toBeInTheDocument();
    expect(calendarTaskTitle.closest(".home-calendar-grid")).toHaveClass("home-calendar-compact-grid");
    expect(calendarTaskTitle.closest(".home-calendar-grid")).toHaveClass("home-calendar-roomy-grid");
    const compactSummary = calendarTaskTitle.closest(".home-calendar-cell-summary") as HTMLElement;
    expect(compactSummary.querySelector(".home-calendar-task-more")).not.toBeInTheDocument();
    expect(compactSummary.querySelector(".home-calendar-task-progress")).toHaveTextContent("0/2 完成");

    fireEvent.click(screen.getByRole("gridcell", { name: "打开 2026-07-15 的日历" }));
    expect(screen.getByTestId("location-path")).toHaveTextContent("/calendar");
    expect(screen.getByTestId("location-state")).toHaveTextContent("null");
  });

  it("filters courses by the selected term", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal("fetch", createHomeFetchMock());

    renderHomePage();

    expect(await screen.findByRole("link", { name: "离散数学" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("combobox", { name: "选择学期" }));
    fireEvent.click(await screen.findByRole("option", { name: "2025-2026 秋季", hidden: true }));

    expect(screen.getByText("2025-2026 秋季 1 门课程 · 资料统计待接入")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "算法设计" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "离散数学" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "操作系统" })).not.toBeInTheDocument();
  });

  it("enters a course when clicking the course card body", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal("fetch", createHomeFetchMock());

    renderHomePage();

    fireEvent.click(await screen.findByRole("link", { name: "打开课程 离散数学" }));

    expect(screen.getByTestId("location-path")).toHaveTextContent("/courses/crs_discrete_math");
  });

  it("toggles the persisted color scheme from the home header", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal("fetch", createHomeFetchMock());

    renderHomePage();

    await screen.findByRole("link", { name: "离散数学" });
    const themeButton = screen.getByRole("button", { name: "切换为夜间模式" });
    fireEvent.click(themeButton);

    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement).toHaveAttribute("data-course-nexus-theme", "dark");
    expect(screen.getByRole("button", { name: "切换为日间模式" })).toBeInTheDocument();
  });

  it("creates a course from the home modal and enters the new course", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const createdCourse = {
      id: "crs_linear_algebra",
      user_id: "usr_123",
      name: "线性代数",
      description: "矩阵和向量空间复习",
      teacher: "王老师",
      term: "2025-2026-spring",
      status: "active",
      created_at: "2026-07-12T12:00:00+00:00",
      updated_at: "2026-07-12T12:00:00+00:00",
      deleted_at: null,
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/v1/courses" && init?.method === "POST") {
        return jsonResponse(createdCourse, "req_create");
      }

      if (String(input) === "/api/v1/course-terms") {
        return jsonResponse(backendTermOptions, "req_terms");
      }

      return jsonResponse(backendCourses, "req_courses");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderHomePage();

    await screen.findByRole("link", { name: "离散数学" });
    fireEvent.click(screen.getByRole("button", { name: "添加课程" }));
    fireEvent.change(await screen.findByLabelText("课程名称"), { target: { value: "线性代数" } });
    fireEvent.change(screen.getByLabelText("课程简介"), { target: { value: "矩阵和向量空间复习" } });
    fireEvent.change(screen.getByLabelText("教师"), { target: { value: "王老师" } });
    fireEvent.click(screen.getByRole("combobox", { name: "学期" }));
    const springOptions = await screen.findAllByRole("option", { name: "2025-2026 春季", hidden: true });
    fireEvent.click(springOptions[springOptions.length - 1]);
    fireEvent.click(screen.getByRole("button", { name: "创建课程" }));

    await waitFor(() => expect(screen.getByTestId("location-path")).toHaveTextContent("/courses/crs_linear_algebra"));
    expect(screen.getByTestId("location-state")).toHaveTextContent('"openUploadPrompt":true');
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "线性代数",
          description: "矩阵和向量空间复习",
          teacher: "王老师",
          term: "2025-2026-spring",
        }),
      }),
    );
  });

  it("limits course form text fields to the supported character counts", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal("fetch", createHomeFetchMock());

    renderHomePage();

    await screen.findByRole("link", { name: "离散数学" });
    fireEvent.click(screen.getByRole("button", { name: "添加课程" }));

    expect(await screen.findByLabelText("课程名称")).toHaveAttribute("maxlength", "20");
    expect(screen.getByLabelText("课程简介")).toHaveAttribute("maxlength", "50");
    expect(screen.getByLabelText("教师")).toHaveAttribute("maxlength", "10");
  });

  it("edits and deletes a course from the course card menu", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const updatedCourse = {
      ...backendCourses[0],
      name: "离散数学复习",
      description: "图论和组合数学复习",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/v1/courses/crs_discrete_math" && init?.method === "PATCH") {
        return jsonResponse(updatedCourse, "req_update");
      }

      if (String(input) === "/api/v1/courses/crs_discrete_math" && init?.method === "DELETE") {
        return jsonResponse({ ...updatedCourse, status: "deleted" }, "req_delete");
      }

      if (String(input) === "/api/v1/course-terms") {
        return jsonResponse(backendTermOptions, "req_terms");
      }

      return jsonResponse(backendCourses, "req_courses");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderHomePage();

    await screen.findByRole("link", { name: "离散数学" });
    fireEvent.click(screen.getByRole("button", { name: "离散数学 更多操作" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "编辑课程" }));
    fireEvent.change(await screen.findByLabelText("课程名称"), { target: { value: "离散数学复习" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    expect(await screen.findByRole("link", { name: "离散数学复习" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses/crs_discrete_math",
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining("离散数学复习"),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "离散数学复习 更多操作" }));
    fireEvent.click(await screen.findByText("删除课程"));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => expect(screen.queryByRole("link", { name: "离散数学复习" })).not.toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses/crs_discrete_math",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("preserves an unchanged legacy term when editing another course field", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const legacyCourse = {
      ...backendCourses[0],
      id: "crs_legacy_term",
      name: "旧课程",
      term: "2023-2024-summer",
    };
    const updatedCourse = {
      ...legacyCourse,
      name: "旧课程（已编辑）",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/v1/courses/crs_legacy_term" && init?.method === "PATCH") {
        return jsonResponse(updatedCourse, "req_update_legacy");
      }

      if (String(input) === "/api/v1/course-terms") {
        return jsonResponse(backendTermOptions, "req_terms");
      }

      return jsonResponse([legacyCourse], "req_courses");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderHomePage();

    await screen.findByRole("link", { name: "旧课程" });
    fireEvent.click(screen.getByRole("button", { name: "旧课程 更多操作" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "编辑课程" }));
    expect(screen.getByText("2023-2024-summer（旧学期值，保存其他修改时会保留）")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("课程名称"), { target: { value: "旧课程（已编辑）" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    expect(await screen.findByRole("link", { name: "旧课程（已编辑）" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses/crs_legacy_term",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          name: "旧课程（已编辑）",
          description: "图论和组合数学复习",
          teacher: "周老师",
        }),
      }),
    );
  });

  it("renders an empty course state when the backend returns no courses", async () => {
    vi.stubGlobal("fetch", createHomeFetchMock([]));

    renderHomePage();

    expect(await screen.findByRole("button", { name: "添加课程" })).toBeInTheDocument();
    expect(screen.queryByText("还没有课程")).not.toBeInTheDocument();
    expect(screen.queryByText("创建第一门课程后，这里会展示课程资料和学习入口。")).not.toBeInTheDocument();
  });

  it("renders backend errors without showing mock courses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        if (String(input) === "/api/v1/course-terms") {
          return jsonResponse(backendTermOptions, "req_terms");
        }

        return Promise.resolve(
          new Response(
            JSON.stringify({
              error: { code: "HTTP_ERROR", message: "课程列表加载失败", details: {} },
              meta: { request_id: "req_error" },
            }),
            { status: 500, headers: { "Content-Type": "application/json" } },
          ),
        );
      }),
    );

    renderHomePage();

    expect((await screen.findAllByText("课程列表加载失败")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: "计算机网络" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试加载课程" })).toBeInTheDocument();
  });
});
