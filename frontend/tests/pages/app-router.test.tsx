import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getSessionToken, setSessionToken } from "../../src/features/auth/session";
import { AppRouter } from "../../src/router/AppRouter";

function renderRouter() {
  render(
    <MantineProvider>
      <AppRouter />
    </MantineProvider>,
  );
}

describe("AppRouter", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
  });

  it("redirects anonymous users to login", () => {
    window.history.pushState({}, "", "/");

    renderRouter();

    expect(screen.getByRole("heading", { name: /课枢 CourseNexus/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "开始" })).toHaveAttribute("href", "/login");
  });

  it("renders home for authenticated users", async () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/");
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const response = (data: unknown, requestId: string) => Promise.resolve(
        new Response(
          JSON.stringify({ data, meta: { request_id: requestId } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

      if (url.endsWith("/api/v1/courses")) {
        return response([
          {
            id: "crs_network",
            user_id: "usr_123",
            name: "计算机网络",
            description: "网络协议复习",
            teacher: "王老师",
            term: "2025-2026-spring",
            material_count: 2,
            today_task_status: "has_task_today",
            status: "active",
            created_at: "2026-07-09T12:00:00+00:00",
            updated_at: "2026-07-09T12:00:00+00:00",
            deleted_at: null,
          },
        ], "req_courses");
      }

      if (url.endsWith("/api/v1/course-terms")) {
        return response([
          { value: "2025-2026-spring", label: "2025-2026 春季" },
        ], "req_terms");
      }

      if (url.includes("/api/v1/todos/today")) {
        return response({ date: "2026-07-14", tasks: [] }, "req_today");
      }

      if (url.includes("/api/v1/calendar/month")) {
        return response({ month: "2026-07", days: [] }, "req_month");
      }

      return response({}, "req_unknown");
    }));

    renderRouter();

    expect(screen.getByRole("heading", { name: "课枢 CourseNexus" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "课程概览" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "计算机网络" })).toHaveAttribute("href", "/courses/crs_network");
  });

  it("keeps login page public", () => {
    window.history.pushState({}, "", "/login");

    renderRouter();

    expect(screen.getByRole("heading", { name: "登录 CourseNexus" })).toBeInTheDocument();
  });

  it("keeps register page public", () => {
    window.history.pushState({}, "", "/register");

    renderRouter();

    expect(screen.getByRole("heading", { name: "注册 CourseNexus" })).toBeInTheDocument();
  });

  it("renders protected course detail route for authenticated users", async () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/courses/crs_123");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: {
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
            },
            meta: { request_id: "req_1" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderRouter();

    expect(await screen.findByRole("heading", { name: "高等数学" })).toBeInTheDocument();
  });

  it("renders protected generated content detail route for authenticated users", async () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/generated-contents/gen_1");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: {
              id: "gen_1",
              user_id: "usr_123",
              course_id: "crs_123",
              study_subtask_id: null,
              source_message_id: null,
              content_type: "knowledge_list",
              title: "知识点清单",
              content: null,
              content_json: { items: [] },
              generation_status: "success",
              material_scope_json: { include_all_parsed_materials: true, material_ids: [] },
              error_code: null,
              source_citations: [],
              created_at: "2026-07-09T12:00:00+00:00",
              updated_at: "2026-07-09T12:00:00+00:00",
              deleted_at: null,
            },
            meta: { request_id: "req_1" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderRouter();

    expect(await screen.findByRole("heading", { name: "知识点清单" })).toBeInTheDocument();
  });

  it("renders protected study plan create route for authenticated users", async () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/courses/crs_123/study-plans/new");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: {
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
            },
            meta: { request_id: "req_1" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderRouter();

    expect(await screen.findByRole("heading", { name: "想生成什么学习计划？" })).toBeInTheDocument();
  });

  it("renders protected study plan detail route for authenticated users", async () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/courses/crs_123/study-plans/plan_1");
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/courses/crs_123")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                data: {
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
                },
                meta: { request_id: "req_course" },
              }),
              { status: 200, headers: { "Content-Type": "application/json" } },
            ),
          );
        }

        return Promise.resolve(
          new Response(
            JSON.stringify({
              data: {
                plan: {
                  id: "plan_1",
                  user_id: "usr_123",
                  course_id: "crs_123",
                  title: "高等数学学习计划",
                  goal_text: "期末复习",
                  parsed_config_json: null,
                  start_date: "2026-07-13",
                  end_date: "2026-07-15",
                  daily_available_minutes: 60,
                  status: "active",
                  created_at: "2026-07-09T12:00:00+00:00",
                  updated_at: "2026-07-09T12:00:00+00:00",
                  deleted_at: null,
                },
                tasks: [],
                subtasks: [],
              },
              meta: { request_id: "req_plan" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }),
    );

    renderRouter();

    expect(await screen.findByRole("heading", { name: "高等数学学习计划" })).toBeInTheDocument();
  });

  it("returns to the public entry when an authenticated request is unauthorized", async () => {
    setSessionToken("expired-token");
    window.history.pushState({}, "", "/");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "UNAUTHORIZED", message: "登录已失效", details: {} },
            meta: { request_id: "req_unauthorized" },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderRouter();

    await waitFor(() => expect(screen.getByRole("link", { name: "开始" })).toHaveAttribute("href", "/login"));
    expect(getSessionToken()).toBeNull();
  });
});
