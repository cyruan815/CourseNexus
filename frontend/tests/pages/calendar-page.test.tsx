import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

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
      task_count: 1,
      subtask_count: 2,
      completed_subtask_count: 1,
      status: "in_progress",
      task_summaries: [
        {
          task_id: "task_1",
          plan_id: "plan_1",
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
};

const dayResponse = {
  course_id: "crs_123",
  course_name: "计算机网络",
  date: "2026-07-14",
  tasks: [
    {
      task_id: "task_1",
      plan_id: "plan_1",
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

describe("CalendarPage", () => {
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

      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderCalendarPage();

    expect(container.querySelector(".workbench-page")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar")).toBeInTheDocument();
    expect(container.querySelector(".calendar-course-shell")).toHaveAttribute("data-workbench-scroll", "locked");

    expect(await screen.findByRole("heading", { name: "计算机网络学习日历" })).toBeInTheDocument();
    expect(screen.getByText("物理层复习")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("gridcell", { name: "查看 2026-07-14 的课程任务" }));

    expect(await screen.findByRole("heading", { name: "2026-07-14 任务" })).toBeInTheDocument();
    expect(screen.getByText("学习: 物理层功能")).toBeInTheDocument();
    expect(screen.getByText("测试: 物理层小测")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "继续学习 物理层复习" })).toHaveAttribute(
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

      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderCalendarPage("/calendar?date=2026-07-14");

    expect(container.querySelector(".workbench-page")).toBeInTheDocument();
    expect(container.querySelector(".workbench-topbar")).toBeInTheDocument();
    expect(container.querySelector(".calendar-course-shell")).toHaveAttribute("data-workbench-scroll", "locked");

    expect(await screen.findByRole("heading", { name: "全局学习日历" })).toBeInTheDocument();
    expect(screen.getAllByText("物理层复习").length).toBeGreaterThan(0);
    expect(await screen.findByRole("heading", { name: "2026-07-14 待办" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "计算机网络" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "继续学习 物理层复习" })).toHaveAttribute(
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
});
