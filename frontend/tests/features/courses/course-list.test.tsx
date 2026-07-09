import { render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CourseList } from "../../../src/features/courses/CourseList";
import type { Course } from "../../../src/types/course";

const course: Course = {
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

function renderCourseList(props: Partial<ComponentProps<typeof CourseList>> = {}) {
  render(
    <MemoryRouter>
      <CourseList courses={[]} {...props} />
    </MemoryRouter>,
  );
}

describe("CourseList", () => {
  it("renders loading state", () => {
    renderCourseList({ isLoading: true });

    expect(screen.getByRole("status")).toHaveTextContent("正在加载课程");
  });

  it("renders empty state", () => {
    renderCourseList({ courses: [] });

    expect(screen.getByText("还没有课程")).toBeInTheDocument();
  });

  it("renders error state", () => {
    renderCourseList({ error: "网络错误" });

    expect(screen.getByRole("alert")).toHaveTextContent("网络错误");
  });

  it("renders course links", () => {
    renderCourseList({ courses: [course] });

    const link = screen.getByRole("link", { name: "高等数学" });
    expect(link).toHaveAttribute("href", "/courses/crs_123");
    expect(screen.getByText("王老师")).toBeInTheDocument();
    expect(screen.getByText("2026 Spring")).toBeInTheDocument();
  });
});
