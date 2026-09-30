import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CalendarPage } from "../../src/pages/CalendarPage";

function successResponse(data: unknown, requestId = "req_1") {
  return new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderCalendarPage(path = "/calendar?courseId=crs_123&date=2026-07-14") {
  return render(
    <MantineProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<CalendarPage />} path="/calendar" />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

const monthResponse = {
  course_id: "crs_123",
  course_name: "计算机网络",
  month: "2026-07",
  days: [
    {
      date: "2026-07-14",
      course_count: 1,
      task_count: 4,
      subtask_count: 2,
      completed_subtask_count: 1,
      status: "in_progress",
      task_summaries: [
        {
          task_id: "task_1",
          plan_id: "plan_1",
          plan_title: "计算机网络冲刺",
          course_id: "crs_123",
          course_name: "计算机网络",
          title: "物理层复习",
          status: "in_progress",
          derived_status: "in_progress",
          sort_order: 1,
        },
        {
          task_id: "task_2",
          plan_id: "plan_1",
          plan_title: "计算机网络冲刺",
          course_id: "crs_123",
          course_name: "计算机网络",
          title: "信道与有线介质",
          status: "not_started",
          derived_status: "not_started",
          sort_order: 2,
        },
        {
          task_id: "task_3",
          plan_id: "plan_1",
          plan_title: "计算机网络冲刺",
          course_id: "crs_123",
          course_name: "计算机网络",
          title: "物理层安全隐患",
          status: "not_started",
          derived_status: "not_started",
          sort_order: 3,
        },
      ],
      hidden_task_count: 1,
    },
  ],
};

const dayResponse = {
  course_id: "crs_123",
  course_name: "计算机网络",
  date: "2026-07-14",
  tasks: [
    {
      task_id: "task_1",
      plan_id: "plan_1",
      plan_title: "计算机网络冲刺",
      course_id: "crs_123",
      course_name: "计算机网络",
      title: "物理层复习",
      task_date: "2026-07-14",
      status: "in_progress",
      derived_status: "in_progress",
      completed_subtask_count: 1,
      total_subtask_count: 2,
      first_incomplete_subtask_id: "subtask_2",
      subtasks: [
        {
          subtask_id: "subtask_1",
          title: "学习: 物理层功能",
          subtask_type: "learn",
          description: "阅读资料并整理概念",
          status: "completed",
          sort_order: 1,
          execution_url: null,
        },
        {
          subtask_id: "subtask_2",
          title: "测试: 物理层小测",
          subtask_type: "quiz",
          description: "完成自测题",
          status: "not_started",
          sort_order: 2,
          execution_url: null,
        },
      ],
    },
  ],
};

const coursesResponse = [
  {
    id: "crs_123",
    user_id: "usr_123",
    name: "计算机网络",
    description: null,
    teacher: "CourseNexus",
    term: "2025-2026-spring",
    status: "active",
    created_at: "2026-07-01T00:00:00+00:00",
    updated_at: "2026-07-01T00:00:00+00:00",
    deleted_at: null,
  },
  {
    id: "crs_math",
    user_id: "usr_123",
    name: "高等数学",
    description: null,
    teacher: null,
    term: null,
    status: "active",
    created_at: "2026-07-01T00:00:00+00:00",
    updated_at: "2026-07-01T00:00:00+00:00",
    deleted_at: null,
  },
];

describe("CalendarPage", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads a course month calendar and opens day tasks from the real course endpoints", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/study-calendar?month=2026-07")) {
        return Promise.resolve(successResponse(monthResponse, "req_month"));
      }
      if (url.endsWith("/study-calendar/days/2026-07-14")) {
        return Promise.resolve(successResponse(dayResponse, "req_day"));
      }
      if (url.endsWith("/courses")) {
        return Promise.resolve(successResponse(coursesResponse, "req_courses"));
      }

      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderCalendarPage();

    expect(container.querySelector(".workbench-page")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar")).toBeInTheDocument();
    expect(container.querySelector(".calendar-course-shell")).toHaveAttribute("data-workbench-scroll", "locked");
    expect(container.querySelector(".workbench-topbar-left .workbench-back-button")).not.toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar-right .workbench-back-button")).toBeInTheDocument();

    expect(await screen.findByRole("heading", { level: 1, name: "学习日历" })).toBeInTheDocument();
    expect(screen.getAllByText("计算机网络").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "返回首页" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("button", { name: "返回" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /切换为/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开个人中心" })).toHaveAttribute("href", "/profile");
    expect(screen.getByText("计算机网络冲刺 · 物理层复习")).toBeInTheDocument();
    expect(screen.getByText("计算机网络冲刺 · 信道与有线介质")).toBeInTheDocument();
    expect(container.querySelector(".calendar-cell-task-progress")).toHaveTextContent("1/2 完成");
    expect(container.querySelector(".calendar-cell-task-more")).toHaveTextContent("...");

    fireEvent.click(screen.getByRole("gridcell", { name: "查看 2026-07-14 的课程任务" }));

    expect(await screen.findByRole("heading", { name: "2026-07-14 任务" })).toBeInTheDocument();
    expect(screen.getByText("所属计划：计算机网络冲刺")).toBeInTheDocument();
    expect(screen.getByText("1/2")).toBeInTheDocument();
    expect(screen.queryByText("1/2 个二级任务完成")).not.toBeInTheDocument();
    expect(screen.getByText("学习: 物理层功能")).toBeInTheDocument();
    expect(screen.getByText("测试: 物理层小测")).toBeInTheDocument();
    expect(screen.getByText("学习")).toBeInTheDocument();
    expect(screen.getByText("小测")).toBeInTheDocument();
    expect(screen.queryByText("阅读资料并整理概念", { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByText("完成自测题", { exact: false })).not.toBeInTheDocument();
    expect(container.querySelector(".calendar-subtask-list")).toBeInTheDocument();
    expect(container.querySelectorAll(".calendar-subtask-row")).toHaveLength(2);
    const taskActions = screen.getByRole("group", { name: "物理层复习操作" });
    expect(taskActions).toHaveClass("calendar-task-actions");
    expect(within(taskActions).getByRole("link", { name: "查看计划详情 物理层复习" })).toHaveAttribute(
      "href",
      "/courses/crs_123/study-plans/plan_1",
    );
    expect(within(taskActions).getByRole("link", { name: "继续学习 物理层复习" })).toHaveAttribute(
      "href",
      "/study-subtasks/subtask_2",
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-calendar?month=2026-07",
        expect.objectContaining({ method: "GET" }),
      );
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/study-calendar/days/2026-07-14",
        expect.objectContaining({ method: "GET" }),
      );
    });
  });

  it("loads the global month calendar and selected day todos without a course id", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/calendar/month?month=2026-07")) {
        return Promise.resolve(successResponse({
          month: "2026-07",
          days: [
            {
              date: "2026-07-14",
              course_count: 1,
              task_count: 1,
              subtask_count: 2,
              completed_subtask_count: 1,
              status: "in_progress",
              task_summaries: [
                {
                  task_id: "task_1",
                  plan_id: "plan_1",
                  plan_title: "计算机网络冲刺",
                  course_id: "crs_123",
                  course_name: "计算机网络",
                  title: "物理层复习",
                  status: "in_progress",
                  derived_status: "in_progress",
                  sort_order: 1,
                },
              ],
              hidden_task_count: 0,
            },
          ],
        }, "req_global_month"));
      }
      if (url.endsWith("/calendar/days/2026-07-14/todos")) {
        return Promise.resolve(successResponse({
          date: "2026-07-14",
          courses: [
            {
              course_id: "crs_123",
              course_name: "计算机网络",
              plan_ids: ["plan_1"],
              tasks: dayResponse.tasks,
            },
          ],
        }, "req_global_day"));
      }
      if (url.endsWith("/courses")) {
        return Promise.resolve(successResponse(coursesResponse, "req_courses"));
      }

      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderCalendarPage("/calendar?date=2026-07-14");

    expect(container.querySelector(".workbench-page")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar")).toBeInTheDocument();
    expect(container.querySelector(".calendar-course-shell")).toHaveAttribute("data-workbench-scroll", "locked");
    expect(container.querySelector(".workbench-topbar-left .workbench-back-button")).not.toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar-right .workbench-back-button")).toBeInTheDocument();

    expect(await screen.findByRole("heading", { level: 1, name: "学习日历" })).toBeInTheDocument();
    expect(screen.getByText("全局")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回首页" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("button", { name: "返回" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /切换为/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开个人中心" })).toHaveAttribute("href", "/profile");
    expect(screen.getByText("计算机网络冲刺 · 物理层复习")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "2026-07-14 待办" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "计算机网络" })).toBeInTheDocument();
    const taskActions = screen.getByRole("group", { name: "物理层复习操作" });
    expect(taskActions).toHaveClass("calendar-task-actions");
    expect(within(taskActions).getByRole("link", { name: "查看计划详情 物理层复习" })).toHaveAttribute(
      "href",
      "/courses/crs_123/study-plans/plan_1",
    );
    expect(within(taskActions).getByRole("link", { name: "继续学习 物理层复习" })).toHaveAttribute(
      "href",
      "/study-subtasks/subtask_2",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/calendar/month?month=2026-07",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/calendar/days/2026-07-14/todos",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("lets users manually filter the global calendar by course and clear the filter", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/courses")) {
        return Promise.resolve(successResponse(coursesResponse, "req_courses"));
      }
      if (url.endsWith("/calendar/month?month=2026-07")) {
        return Promise.resolve(successResponse({ month: "2026-07", days: [] }, "req_global_month"));
      }
      if (url.endsWith("/courses/crs_123/study-calendar?month=2026-07")) {
        return Promise.resolve(successResponse(monthResponse, "req_course_month"));
      }
      if (url.endsWith("/courses/crs_123/study-calendar/days/2026-07-14")) {
        return Promise.resolve(successResponse(dayResponse, "req_course_day"));
      }

      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderCalendarPage("/calendar?date=2026-07-14");

    expect(await screen.findByRole("combobox", { name: "课程筛选" })).toHaveValue("全部课程");
    fireEvent.click(screen.getByRole("combobox", { name: "课程筛选" }));
    fireEvent.click(await screen.findByRole("option", { name: "计算机网络", hidden: true }));

    expect((await screen.findAllByText(monthResponse.days[0].task_summaries[0].title)).length).toBeGreaterThan(0);
    expect(screen.getByRole("combobox", { name: "课程筛选" })).toHaveValue("计算机网络");

    fireEvent.click(screen.getByRole("button", { name: "清除课程筛选" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/calendar/month?month=2026-07",
        expect.objectContaining({ method: "GET" }),
      );
    });
    expect(screen.getByRole("combobox", { name: "课程筛选" })).toHaveValue("全部课程");
  });
});
