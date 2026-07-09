import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CourseDetailPage } from "../../src/pages/CourseDetailPage";

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

function renderDetailPage(path = "/courses/crs_123") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<CourseDetailPage />} path="/courses/:courseId" />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CourseDetailPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders course header and reserved workspace sections", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: course, meta: { request_id: "req_1" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    renderDetailPage();

    expect(await screen.findByRole("heading", { name: "高等数学" })).toBeInTheDocument();
    expect(screen.getByText("王老师")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "资料区" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "问答区" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "生成内容区" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "学习计划入口" })).toBeInTheDocument();
  });

  it("renders loading and error states", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "NOT_FOUND", message: "课程不存在", details: {} },
            meta: { request_id: "req_404" },
          }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderDetailPage();

    expect(screen.getByRole("status")).toHaveTextContent("正在加载课程");
    expect(await screen.findByRole("alert")).toHaveTextContent("课程不存在");
  });
});
