import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, type InitialEntry, useLocation } from "react-router-dom";
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
const generatedContent = {
  id: "gen_1",
  user_id: "usr_123",
  course_id: "crs_123",
  study_subtask_id: null,
  source_message_id: null,
  content_type: "outline",
  title: "期末复习提纲",
  content: "第一章重点",
  content_json: null,
  generation_status: "success",
  material_scope_json: { include_all_parsed_materials: true, material_ids: [] },
  error_code: null,
  source_citations: [],
  created_at: "2026-07-09T12:00:00+00:00",
  updated_at: "2026-07-09T12:00:00+00:00",
  deleted_at: null,
};
const studyPlan = {
  id: "plan_1",
  user_id: "usr_123",
  course_id: "crs_123",
  title: "高等数学期末计划",
  goal_text: "期末复习",
  parsed_config_json: null,
  start_date: "2026-07-10",
  end_date: "2026-07-12",
  daily_available_minutes: 60,
  status: "active",
  created_at: "2026-07-09T12:00:00+00:00",
  updated_at: "2026-07-09T12:00:00+00:00",
  deleted_at: null,
};

function LocationStateProbe() {
  const location = useLocation();

  return <span data-testid="location-state">{JSON.stringify(location.state ?? null)}</span>;
}

function renderDetailPage(path: InitialEntry = "/courses/crs_123") {
  render(
    <MantineProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            element={(
              <>
                <CourseDetailPage />
                <LocationStateProbe />
              </>
            )}
            path="/courses/:courseId"
          />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

function successResponse(data: unknown, requestId = "req_1") {
  return new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("CourseDetailPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders course header and reserved workspace sections", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/material-folders") || url.endsWith("/materials")) {
        return Promise.resolve(successResponse([], "req_materials"));
      }
      if (url.endsWith("/generated-contents")) {
        return Promise.resolve(successResponse([], "req_generated"));
      }
      if (url.endsWith("/study-plans")) {
        return Promise.resolve(successResponse([], "req_plans"));
      }
      if (url.endsWith("/conversations")) {
        return Promise.resolve(successResponse([], "req_conversations"));
      }

      return Promise.resolve(successResponse(course));
    }));

    renderDetailPage();

    expect(await screen.findByRole("heading", { name: "高等数学" })).toBeInTheDocument();
    expect(screen.getByText("王老师")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "资料区" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "问答区" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "生成内容区" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "制定学习计划" })).toHaveAttribute("href", "/courses/crs_123/study-plans/new");
    expect(screen.queryByRole("button", { name: "查看今日待办（待接入）" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看全部（待接入）" })).not.toBeInTheDocument();
    expect(screen.queryByText("生成入口")).not.toBeInTheDocument();
    expect(screen.queryByText("保存入口")).not.toBeInTheDocument();
  });

  it("opens a dismissible upload prompt after creating a course", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/material-folders") || url.endsWith("/materials")) {
        return Promise.resolve(successResponse([], "req_materials"));
      }
      if (url.endsWith("/generated-contents")) {
        return Promise.resolve(successResponse([], "req_generated"));
      }
      if (url.endsWith("/study-plans")) {
        return Promise.resolve(successResponse([], "req_plans"));
      }
      if (url.endsWith("/conversations")) {
        return Promise.resolve(successResponse([], "req_conversations"));
      }

      return Promise.resolve(successResponse(course));
    }));

    renderDetailPage({ pathname: "/courses/crs_123", state: { openUploadPrompt: true } });

    expect(await screen.findByRole("dialog", { name: "上传课程资料" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("location-state")).toHaveTextContent("null"));
    fireEvent.click(screen.getByRole("button", { name: "关闭上传资料弹窗" }));

    expect(screen.queryByRole("dialog", { name: "上传课程资料" })).not.toBeInTheDocument();
  });

  it("loads backend workspace data and sends course questions", async () => {
    const answer = {
      answer_text: "模型用于描述和解释现象。",
      answer_type: "grounded",
      assistant_message_id: "msg_assistant",
      conversation_id: "cnv_1",
      source_citations: [
        {
          chunk_id: "chk_1",
          hit_text: "模型描述现象",
          material_id: "mat_1",
          material_name: "理论模型概述.pdf",
          page: "12",
          page_index: null,
        },
      ],
      user_message_id: "msg_user",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/material-folders") || url.endsWith("/materials")) {
        return Promise.resolve(successResponse([], "req_materials"));
      }
      if (url.endsWith("/generated-contents")) {
        return Promise.resolve(successResponse([generatedContent], "req_generated"));
      }
      if (url.endsWith("/study-plans")) {
        return Promise.resolve(successResponse([studyPlan], "req_plans"));
      }
      if (url.endsWith("/conversations")) {
        return Promise.resolve(successResponse([], "req_conversations"));
      }
      if (url.endsWith("/qa/questions") && init?.method === "POST") {
        return Promise.resolve(successResponse(answer, "req_answer"));
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderDetailPage();

    expect(await screen.findByText("期末复习提纲")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看生成内容 期末复习提纲" })).toHaveAttribute("href", "/generated-contents/gen_1");
    expect(screen.getByRole("link", { name: "高等数学期末计划" })).toHaveAttribute("href", "/courses/crs_123/study-plans/plan_1");

    fireEvent.change(screen.getByLabelText("输入你的问题"), {
      target: { value: "什么是模型？" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));

    expect(await screen.findByText("模型用于描述和解释现象。")).toBeInTheDocument();
    expect(screen.getByText("理论模型概述.pdf · 12")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/qa/questions",
        expect.objectContaining({
          body: JSON.stringify({
            conversation_id: null,
            material_scope: { include_all_parsed_materials: true, material_ids: [] },
            question: "什么是模型？",
            source_page: "course_detail",
          }),
          method: "POST",
        }),
      );
    });
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

  it("generates content from the whole tool card", async () => {
    const generatedQuiz = {
      ...generatedContent,
      id: "gen_quiz",
      content_type: "quiz",
      title: "Quiz",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/material-folders") || url.endsWith("/materials")) {
        return Promise.resolve(successResponse([], "req_materials"));
      }
      if (url.endsWith("/generated-contents")) {
        return Promise.resolve(successResponse([], "req_generated"));
      }
      if (url.endsWith("/study-plans")) {
        return Promise.resolve(successResponse([], "req_plans"));
      }
      if (url.endsWith("/conversations")) {
        return Promise.resolve(successResponse([], "req_conversations"));
      }
      if (url.endsWith("/generations") && init?.method === "POST") {
        return Promise.resolve(successResponse(generatedQuiz, "req_generation"));
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderDetailPage();

    fireEvent.click(await screen.findByRole("button", { name: "生成 Quiz" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/generations",
        expect.objectContaining({
          body: JSON.stringify({
            content_type: "quiz",
            material_scope: { include_all_parsed_materials: true, material_ids: [] },
            parameters: {},
          }),
          method: "POST",
        }),
      );
    });
    expect(screen.queryByRole("button", { name: "生成" })).not.toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "查看生成内容 Quiz" })).toHaveAttribute("href", "/generated-contents/gen_quiz");
  });
});
