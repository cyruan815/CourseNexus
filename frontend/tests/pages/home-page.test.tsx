import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TOKEN_STORAGE_KEY } from "../../src/features/auth/session";
import { HomePage } from "../../src/pages/HomePage";

const backendCourses = [
  {
    id: "crs_discrete_math",
    user_id: "usr_123",
    name: "离散数学",
    description: "图论和组合数学复习",
    teacher: "周老师",
    term: "2025-2026 春季",
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
    term: "2025-2026 秋季",
    status: "active",
    created_at: "2026-07-11T12:00:00+00:00",
    updated_at: "2026-07-11T12:00:00+00:00",
    deleted_at: null,
  },
];

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
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("loads courses from the backend and renders real course links", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: backendCourses, meta: { request_id: "req_courses" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderHomePage();

    expect(screen.getByRole("heading", { name: "课枢 CourseNexus" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今日待办" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "日历" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "课程概览" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("正在加载课程");
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
    expect(screen.getByText("今天还没有学习计划")).toBeInTheDocument();
    expect(screen.queryByText("1 项待安排")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "生成今日计划" })).not.toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: "1" })).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: "15" })).toBeInTheDocument();
    expect(screen.getByText("添加课程")).toBeInTheDocument();
  });

  it("filters courses by the selected term", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: backendCourses, meta: { request_id: "req_courses" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: backendCourses, meta: { request_id: "req_courses" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    renderHomePage();

    fireEvent.click(await screen.findByRole("link", { name: "打开课程 离散数学" }));

    expect(screen.getByTestId("location-path")).toHaveTextContent("/courses/crs_discrete_math");
  });

  it("creates a course from the home modal and enters the new course", async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "token-home");
    const createdCourse = {
      id: "crs_linear_algebra",
      user_id: "usr_123",
      name: "线性代数",
      description: "矩阵和向量空间复习",
      teacher: "王老师",
      term: "2025-2026 春季",
      status: "active",
      created_at: "2026-07-12T12:00:00+00:00",
      updated_at: "2026-07-12T12:00:00+00:00",
      deleted_at: null,
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/v1/courses" && init?.method === "POST") {
        return Promise.resolve(
          new Response(JSON.stringify({ data: createdCourse, meta: { request_id: "req_create" } }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }

      return Promise.resolve(
        new Response(JSON.stringify({ data: backendCourses, meta: { request_id: "req_courses" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
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
          term: "2025-2026 春季",
        }),
      }),
    );
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
        return Promise.resolve(
          new Response(JSON.stringify({ data: updatedCourse, meta: { request_id: "req_update" } }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }

      if (String(input) === "/api/v1/courses/crs_discrete_math" && init?.method === "DELETE") {
        return Promise.resolve(
          new Response(
            JSON.stringify({ data: { ...updatedCourse, status: "deleted" }, meta: { request_id: "req_delete" } }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }

      return Promise.resolve(
        new Response(JSON.stringify({ data: backendCourses, meta: { request_id: "req_courses" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
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

  it("renders an empty course state when the backend returns no courses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: [], meta: { request_id: "req_empty" } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    renderHomePage();

    expect(await screen.findByText("还没有课程")).toBeInTheDocument();
    expect(screen.getByText("创建第一门课程后，这里会展示课程资料和学习入口。")).toBeInTheDocument();
  });

  it("renders backend errors without showing mock courses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "HTTP_ERROR", message: "课程列表加载失败", details: {} },
            meta: { request_id: "req_error" },
          }),
          { status: 500, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderHomePage();

    expect(await screen.findByRole("alert")).toHaveTextContent("课程列表加载失败");
    expect(screen.queryByRole("link", { name: "计算机网络" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试加载课程" })).toBeInTheDocument();
  });
});
