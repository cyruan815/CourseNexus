import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, type InitialEntry, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import courseDetailSource from "../../src/pages/CourseDetailPage.tsx?raw";
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
  title: "第七章 物理层",
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
const studyPlanHandout = {
  ...generatedContent,
  id: "gen_study_handout",
  study_subtask_id: "subtask_1",
  content_type: "handout",
  title: "学习滑动窗口讲义",
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
const parsedMaterials = [
  {
    id: "mat_1",
    course_id: "crs_123",
    user_id: "usr_123",
    folder_id: null,
    name: "计算机网络期末考试.pdf",
    material_type: "pdf",
    source_type: "file",
    file_url: "stored/network.pdf",
    source_url: null,
    file_size: 100,
    mime_type: "application/pdf",
    parse_status: "parsed",
    parse_error: null,
    page_count: 10,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
    deleted_at: null,
  },
  {
    id: "mat_2",
    course_id: "crs_123",
    user_id: "usr_123",
    folder_id: null,
    name: "演示资料.md",
    material_type: "markdown",
    source_type: "file",
    file_url: "stored/demo.md",
    source_url: null,
    file_size: 20,
    mime_type: "text/markdown",
    parse_status: "parsed",
    parse_error: null,
    page_count: null,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
    deleted_at: null,
  },
];

function LocationStateProbe() {
  const location = useLocation();

  return <span data-testid="location-state">{JSON.stringify(location.state ?? null)}</span>;
}

function renderDetailPage(path: InitialEntry = "/courses/crs_123") {
  return render(
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
          <Route element={<LocationStateProbe />} path="/courses/:courseId/study-plans/new" />
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

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });

  return { promise, reject, resolve };
}

describe("CourseDetailPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps course detail source copy readable instead of unicode escapes or mojibake", () => {
    expect(courseDetailSource).not.toMatch(/\\u[0-9a-fA-F]{4}/);
    expect(courseDetailSource).not.toContain("璺?");
    expect(courseDetailSource).toContain('placeholder="输入你的问题..."');
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
    const studio = screen.getByRole("region", { name: "学习工具与 AI 生成内容" });
    expect(within(studio).getByRole("region", { name: "学习工具区" })).toBeInTheDocument();
    expect(within(studio).getByRole("separator", { name: "学习工具与 AI 生成内容分隔线" })).toBeInTheDocument();
    expect(within(studio).getByRole("region", { name: "AI 生成内容区" })).toBeInTheDocument();
    expect(within(studio).queryByRole("heading", { name: "AI 生成内容" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "制定学习计划" })).toHaveAttribute("href", "/courses/crs_123/study-plans/new");
    expect(screen.queryByRole("button", { name: "查看今日待办（待接入）" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看全部（待接入）" })).not.toBeInTheDocument();
    expect(screen.queryByText("生成入口")).not.toBeInTheDocument();
    expect(screen.queryByText("保存入口")).not.toBeInTheDocument();
    expect(screen.queryByText("学习笔记")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "生成 知识点清单" })).toHaveClass("is-wide");
  });

  it("passes the current parsed-material selection as a plan-creation snapshot", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/material-folders")) {
        return Promise.resolve(successResponse([], "req_folders"));
      }
      if (url.endsWith("/materials")) {
        return Promise.resolve(successResponse(parsedMaterials, "req_materials"));
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
    const firstMaterial = await screen.findByRole("checkbox", { name: `选择资料 ${parsedMaterials[0].name}` });
    const secondMaterial = screen.getByRole("checkbox", { name: `选择资料 ${parsedMaterials[1].name}` });
    fireEvent.click(firstMaterial);
    fireEvent.click(secondMaterial);
    fireEvent.click(screen.getByRole("link", { name: "制定学习计划" }));

    expect(screen.getByTestId("location-state")).toHaveTextContent(JSON.stringify({
      studyPlanMaterialSelection: parsedMaterials.map((material) => ({ id: material.id, name: material.name })),
    }));
  });

  it("shows readable course terms in the detail header without rendering the description", async () => {
    let courseRequestCount = 0;
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

      courseRequestCount += 1;
      return Promise.resolve(successResponse({
        ...course,
        description: "Do not render this description",
        name: courseRequestCount === 1 ? "Course A" : "Course B",
        teacher: "Teacher A",
        term: courseRequestCount === 1 ? "2026-2027-AUTUMN" : "2026-2027-SPRING",
      }));
    }));

    const view = renderDetailPage();

    expect(await screen.findByRole("heading", { name: "Course A" })).toBeInTheDocument();
    expect(screen.getByText("2026-2027 秋季")).toBeInTheDocument();
    expect(screen.getByText("Teacher A")).toBeInTheDocument();
    expect(screen.queryByText("Do not render this description")).not.toBeInTheDocument();
    expect(screen.queryByText("课程已创建")).not.toBeInTheDocument();

    view.unmount();
    renderDetailPage();

    expect(await screen.findByRole("heading", { name: "Course B" })).toBeInTheDocument();
    expect(screen.getByText("2026-2027 春季")).toBeInTheDocument();
    expect(screen.queryByText("2026-2027-SPRING")).not.toBeInTheDocument();
  });

  it("shows the latest study plan as a linked summary with calendar access", async () => {
    const olderPlan = {
      ...studyPlan,
      id: "plan_old",
      title: "旧学习计划",
      created_at: "2026-07-09T12:00:00+00:00",
      updated_at: "2026-07-10T12:00:00+00:00",
    };
    const latestPlan = {
      ...studyPlan,
      id: "plan_latest",
      title: "最新学习计划",
      start_date: "2026-07-13",
      end_date: "2026-07-19",
      created_at: "2026-07-11T12:00:00+00:00",
      updated_at: "2026-07-12T12:00:00+00:00",
    };

    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/material-folders") || url.endsWith("/materials")) {
        return Promise.resolve(successResponse([], "req_materials"));
      }
      if (url.endsWith("/generated-contents")) {
        return Promise.resolve(successResponse([], "req_generated"));
      }
      if (url.endsWith("/study-plans")) {
        return Promise.resolve(successResponse([olderPlan, latestPlan], "req_plans"));
      }
      if (url.endsWith("/conversations")) {
        return Promise.resolve(successResponse([], "req_conversations"));
      }

      return Promise.resolve(successResponse(course));
    }));

    renderDetailPage();

    const summaryLink = await screen.findByRole("link", { name: /查看学习计划 最新学习计划/ });
    expect(summaryLink).toHaveAttribute("href", "/courses/crs_123/study-plans/plan_latest");
    expect(summaryLink).toHaveTextContent("2026-07-13 - 2026-07-19");
    expect(screen.queryByText("旧学习计划")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "新建学习计划" })).toHaveAttribute("href", "/courses/crs_123/study-plans/new");
    expect(screen.getByRole("link", { name: "查看更多" })).toHaveAttribute("href", "/calendar?courseId=crs_123");
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
      answer_text: "模型用于描述和解释现象。 [[cite:1]]",
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
    const markdownAnswer = {
      ...answer,
      answer_text: "**模型**用途：\n\n- 描述现象\n- 解释规律",
      assistant_message_id: "msg_assistant_2",
      user_message_id: "msg_user_2",
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
        const body = JSON.parse(String(init.body));
        return Promise.resolve(successResponse(body.question.includes("第二") ? markdownAnswer : answer, "req_answer"));
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderDetailPage();

    const generatedTitle = await screen.findByText("复习提纲 · 第七章 物理层");
    expect(generatedTitle).toHaveAttribute("title", "复习提纲 · 第七章 物理层");
    expect(screen.getByRole("link", { name: "查看生成内容 复习提纲 · 第七章 物理层" })).toHaveAttribute("href", "/generated-contents/gen_1");
    expect(screen.getByRole("link", { name: "查看学习计划 高等数学期末计划" })).toHaveAttribute("href", "/courses/crs_123/study-plans/plan_1");

    fireEvent.change(screen.getByLabelText("输入你的问题"), {
      target: { value: "什么是模型？" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));

    expect(await screen.findByText("模型用于描述和解释现象。", { exact: false })).toBeInTheDocument();
    const citationMarker = screen.getByRole("button", { name: "查看引用 1：理论模型概述.pdf" });
    expect(citationMarker).toHaveTextContent("1");
    expect(screen.queryByText("模型描述现象")).not.toBeInTheDocument();
    fireEvent.mouseEnter(citationMarker);
    await waitFor(() => expect(screen.getByLabelText("引用 1 详情")).toHaveStyle({ opacity: "1" }));
    const citationTooltip = screen.getByLabelText("引用 1 详情");
    expect(citationTooltip).toHaveTextContent("理论模型概述.pdf");
    expect(citationTooltip).toHaveTextContent("第 12 页");
    expect(citationTooltip).toHaveTextContent("模型描述现象");
    expect(screen.queryByText("引用来源")).not.toBeInTheDocument();
    expect(screen.queryByText(/寮|鏉|簮|锟/)).not.toBeInTheDocument();
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

  it("restores inline citation popovers from conversation history", async () => {
    const citation = {
      chunk_id: "chk_history",
      hit_text: "历史回答引用的资料片段。",
      material_id: "mat_history",
      material_name: "历史资料.pdf",
      page: null,
      page_index: 2,
    };
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
      if (url.endsWith("/courses/crs_123/conversations")) {
        return Promise.resolve(successResponse([{
          id: "cnv_history",
          user_id: "usr_123",
          course_id: "crs_123",
          title: "历史问题",
          source_page: "course_detail",
          status: "active",
          created_at: "2026-07-14T00:00:00Z",
          updated_at: "2026-07-14T00:00:00Z",
          deleted_at: null,
        }], "req_conversations"));
      }
      if (url.endsWith("/conversations/cnv_history/messages")) {
        return Promise.resolve(successResponse([
          {
            id: "msg_history_user",
            conversation_id: "cnv_history",
            course_id: "crs_123",
            role: "user",
            content: "历史问题",
            answer_type: null,
            generation_status: null,
            error_code: null,
            material_scope_json: null,
            source_citations: [],
            created_at: "2026-07-14T00:00:00Z",
          },
          {
            id: "msg_history_assistant",
            conversation_id: "cnv_history",
            course_id: "crs_123",
            role: "assistant",
            content: "这是旧格式历史回答。",
            answer_type: "grounded",
            generation_status: "success",
            error_code: null,
            material_scope_json: null,
            source_citations: [citation],
            created_at: "2026-07-14T00:00:01Z",
          },
        ], "req_messages"));
      }
      return Promise.resolve(successResponse(course));
    }));

    renderDetailPage();

    expect(await screen.findByText("这是旧格式历史回答。", { exact: false })).toBeInTheDocument();
    const marker = screen.getByRole("button", { name: "查看引用 1：历史资料.pdf" });
    fireEvent.mouseEnter(marker);
    await waitFor(() => expect(screen.getByLabelText("引用 1 详情")).toHaveStyle({ opacity: "1" }));
    const tooltip = screen.getByLabelText("引用 1 详情");
    expect(tooltip).toHaveTextContent("第 3 页");
    expect(tooltip).toHaveTextContent("历史回答引用的资料片段。");
  });

  it("syncs the visible material scope and question payload as selections change", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/material-folders")) {
        return Promise.resolve(successResponse([], "req_folders"));
      }
      if (url.endsWith("/materials")) {
        return Promise.resolve(successResponse(parsedMaterials, "req_materials"));
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
      if (url.endsWith("/qa/questions") && init?.method === "POST") {
        return Promise.resolve(successResponse({
          answer_text: "回答",
          answer_type: "no_source",
          assistant_message_id: `assistant_${fetchMock.mock.calls.length}`,
          conversation_id: "cnv_1",
          source_citations: [],
          user_message_id: `user_${fetchMock.mock.calls.length}`,
        }, "req_answer"));
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderDetailPage();

    expect(await screen.findByText("资料范围：当前课程全部已解析资料")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("输入你的问题"), { target: { value: "默认全资料问答" } });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/qa/questions",
        expect.objectContaining({
          body: JSON.stringify({
            conversation_id: null,
            material_scope: { include_all_parsed_materials: true, material_ids: [] },
            question: "默认全资料问答",
            source_page: "course_detail",
          }),
          method: "POST",
        }),
      );
    });

    fireEvent.click(screen.getByRole("checkbox", { name: "全部已解析资料" }));
    expect(screen.getByText("资料范围：当前课程全部已解析资料")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("输入你的问题"), { target: { value: "全资料问答" } });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/qa/questions",
        expect.objectContaining({
          body: JSON.stringify({
            conversation_id: "cnv_1",
            material_scope: { include_all_parsed_materials: true, material_ids: [] },
            question: "全资料问答",
            source_page: "course_detail",
          }),
          method: "POST",
        }),
      );
    });

    fireEvent.click(screen.getByRole("checkbox", { name: "选择资料 计算机网络期末考试.pdf" }));
    expect(screen.getByText("资料范围：已选择")).toBeInTheDocument();
    expect(screen.getByText("共 1 份资料")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("输入你的问题"), { target: { value: "部分资料问答" } });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/courses/crs_123/qa/questions",
        expect.objectContaining({
          body: JSON.stringify({
            conversation_id: "cnv_1",
            material_scope: { include_all_parsed_materials: false, material_ids: ["mat_2"] },
            question: "部分资料问答",
            source_page: "course_detail",
          }),
          method: "POST",
        }),
      );
    });

    fireEvent.click(screen.getByRole("checkbox", { name: "选择资料 演示资料.md" }));
    expect(screen.getByText("资料范围：当前课程全部已解析资料")).toBeInTheDocument();
  });

  it("keeps a continuous qa conversation and renders assistant markdown", async () => {
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
      if (url.endsWith("/qa/questions") && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        return Promise.resolve(successResponse({
          answer_text: body.question.includes("Second")
            ? "# Review focus\n\n**Model** uses:\n\n- describe facts\n- explain rules\n\n```ts\nconst model = \"network\";\n```\n\n<script>alert('xss')</script>"
            : "First answer",
          answer_type: "grounded",
          assistant_message_id: body.question.includes("Second") ? "msg_assistant_2" : "msg_assistant_1",
          conversation_id: "cnv_1",
          source_citations: [],
          user_message_id: body.question.includes("Second") ? "msg_user_2" : "msg_user_1",
        }, "req_answer"));
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    const view = renderDetailPage();
    const textbox = await screen.findByRole("textbox");
    const sendButton = view.container.querySelector(".course-detail-send-button") as HTMLElement;

    fireEvent.change(textbox, { target: { value: "First question" } });
    fireEvent.click(sendButton);
    expect(await screen.findByText("First question")).toBeInTheDocument();
    expect(await screen.findByText("First answer")).toBeInTheDocument();

    fireEvent.change(textbox, { target: { value: "Second question" } });
    fireEvent.click(sendButton);
    expect(await screen.findByText("Second question")).toBeInTheDocument();
    expect(screen.getByText("First question")).toBeInTheDocument();
    expect(screen.getByText("First answer")).toBeInTheDocument();
    expect(screen.getByText("Model").tagName).toBe("STRONG");
    expect(screen.getByText("describe facts").tagName).toBe("LI");
    expect(screen.getByText("explain rules").tagName).toBe("LI");
    expect(screen.getByRole("heading", { level: 1, name: "Review focus" })).toBeInTheDocument();
    expect(screen.getByText('const model = "network";').tagName).toBe("CODE");
    expect(document.querySelector("script")).not.toBeInTheDocument();
  });

  it("shows sending state without a thinking row", async () => {
    const pendingAnswer = deferred<Response>();
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
      if (url.endsWith("/qa/questions") && init?.method === "POST") {
        return pendingAnswer.promise;
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    const view = renderDetailPage();
    const textbox = await screen.findByRole("textbox");
    const sendButton = view.container.querySelector(".course-detail-send-button") as HTMLButtonElement;

    fireEvent.change(textbox, { target: { value: "Pending question" } });
    fireEvent.click(sendButton);

    await waitFor(() => expect(screen.getAllByText("Pending question").length).toBeGreaterThanOrEqual(2));
    expect(sendButton).toBeDisabled();
    expect(screen.queryByText("AI 助教正在思考...")).not.toBeInTheDocument();

    pendingAnswer.resolve(successResponse({
      answer_text: "Done",
      answer_type: "grounded",
      assistant_message_id: "msg_assistant_pending",
      conversation_id: "cnv_1",
      source_citations: [],
      user_message_id: "msg_user_pending",
    }, "req_answer"));

    expect(await screen.findByText("Done")).toBeInTheDocument();
  });

  it("keeps the qa input anchored while long input scrolls inside the textarea", async () => {
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

    const view = renderDetailPage();
    const qaRegion = await screen.findByRole("region", { name: "问答区" });
    const textbox = screen.getByLabelText("输入你的问题");
    const inputArea = view.container.querySelector(".course-detail-qa-input-area");
    const conversation = view.container.querySelector(".course-detail-conversation");

    expect(qaRegion).toHaveClass("course-detail-qa");
    expect(inputArea).toBeInTheDocument();
    expect(conversation).toBeInTheDocument();
    expect(textbox).toHaveAttribute("rows", "2");

    fireEvent.change(textbox, {
      target: { value: Array.from({ length: 20 }, (_, index) => `第 ${index + 1} 行长输入`).join("\n") },
    });

    expect((textbox as HTMLTextAreaElement).value).toContain("第 20 行长输入");
    expect(inputArea).toContainElement(textbox);
  });

  it("keeps the user message and shows an assistant error bubble when qa fails", async () => {
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
      if (url.endsWith("/qa/questions") && init?.method === "POST") {
        return Promise.reject(new Error("Network failed"));
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    const view = renderDetailPage();
    const textbox = await screen.findByRole("textbox");
    const sendButton = view.container.querySelector(".course-detail-send-button") as HTMLElement;

    fireEvent.change(textbox, { target: { value: "失败时不要丢掉我" } });
    fireEvent.click(sendButton);

    await waitFor(() => expect(screen.getAllByText("失败时不要丢掉我").length).toBeGreaterThanOrEqual(2));
    expect(await screen.findByText("回答生成失败，请稍后重试。")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
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

  it("shows independent disabled rows while generated contents run concurrently", async () => {
    const generatedQuiz = {
      ...generatedContent,
      id: "gen_quiz",
      content_type: "quiz",
      title: "Quiz（共 10 道）",
    };
    const generatedMindmap = {
      ...generatedContent,
      id: "gen_mindmap",
      content_type: "mindmap",
      title: "思维导图（共 42 个节点）",
    };
    const pendingQuiz = deferred<Response>();
    const pendingMindmap = deferred<Response>();
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
        const body = JSON.parse(String(init.body));
        return body.content_type === "quiz" ? pendingQuiz.promise : pendingMindmap.promise;
      }

      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderDetailPage();

    const quizButton = await screen.findByRole("button", { name: "生成 Quiz" });
    fireEvent.click(quizButton);
    fireEvent.click(screen.getByRole("button", { name: "生成 Mind Map" }));

    expect(quizButton).toBeEnabled();
    expect(screen.getByLabelText("正在生成 Quiz")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByLabelText("正在生成 思维导图")).toHaveAttribute("aria-disabled", "true");
    expect(screen.queryByRole("link", { name: "正在生成 Quiz" })).not.toBeInTheDocument();
    expect(screen.getByText("正在生成题目与逐项解析")).toBeInTheDocument();
    expect(screen.getByText("正在梳理概念关系")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/generations"))).toHaveLength(2);
    });

    pendingQuiz.resolve(successResponse(generatedQuiz, "req_quiz"));
    expect(await screen.findByRole("link", { name: "查看生成内容 Quiz" })).toHaveAttribute("href", "/generated-contents/gen_quiz");
    expect(screen.queryByText("Quiz（共 10 道）")).not.toBeInTheDocument();
    expect(screen.getByLabelText("正在生成 思维导图")).toBeInTheDocument();

    pendingMindmap.resolve(successResponse(generatedMindmap, "req_mindmap"));
    expect(await screen.findByRole("link", { name: "查看生成内容 思维导图" })).toHaveAttribute("href", "/generated-contents/gen_mindmap");
    expect(screen.queryByText("思维导图（共 42 个节点）")).not.toBeInTheDocument();
    expect(screen.queryByText("已完成")).not.toBeInTheDocument();
    expect(screen.queryByText("success")).not.toBeInTheDocument();
  });

  it("mounts the approved disabled loading and spinner hooks", () => {
    expect(courseDetailSource).toContain('className="course-detail-generated-item is-pending"');
    expect(courseDetailSource).toContain('className="course-detail-generation-spinner"');
    expect(courseDetailSource).toContain('aria-disabled="true"');
  });

  it("does not show study plan handouts in course generated contents", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/material-folders") || url.endsWith("/materials")) {
        return Promise.resolve(successResponse([], "req_materials"));
      }
      if (url.endsWith("/generated-contents")) {
        return Promise.resolve(successResponse([generatedContent, studyPlanHandout], "req_generated"));
      }
      if (url.endsWith("/study-plans") || url.endsWith("/conversations")) {
        return Promise.resolve(successResponse([], "req_workspace"));
      }
      return Promise.resolve(successResponse(course));
    }));

    renderDetailPage();

    expect(await screen.findByText("复习提纲 · 第七章 物理层")).toBeInTheDocument();
    expect(screen.queryByText(studyPlanHandout.title)).not.toBeInTheDocument();
  });

  it("renames and deletes generated content from the item menu", async () => {
    const renamedContent = {
      ...generatedContent,
      title: "自定义期末提纲",
      updated_at: "2026-07-15T12:00:00+00:00",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/material-folders") || url.endsWith("/materials")) {
        return Promise.resolve(successResponse([], "req_materials"));
      }
      if (url.endsWith("/generated-contents/gen_1") && init?.method === "PATCH") {
        return Promise.resolve(successResponse(renamedContent, "req_rename"));
      }
      if (url.endsWith("/generated-contents/gen_1") && init?.method === "DELETE") {
        return Promise.resolve(successResponse({ ...renamedContent, deleted_at: "2026-07-15T12:01:00+00:00" }, "req_delete"));
      }
      if (url.endsWith("/generated-contents")) {
        return Promise.resolve(successResponse([generatedContent], "req_generated"));
      }
      if (url.endsWith("/study-plans")) {
        return Promise.resolve(successResponse([], "req_plans"));
      }
      if (url.endsWith("/conversations")) {
        return Promise.resolve(successResponse([], "req_conversations"));
      }
      return Promise.resolve(successResponse(course));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderDetailPage();

    fireEvent.click(await screen.findByRole("button", { name: "复习提纲 · 第七章 物理层 更多操作" }));
    const renameItemLabel = await screen.findByText("重命名");
    const deleteItemLabel = screen.getByText("删除");
    expect(renameItemLabel.closest('[role="menuitem"]')).toBeInTheDocument();
    expect(deleteItemLabel.closest('[role="menuitem"]')).toBeInTheDocument();
    fireEvent.click(renameItemLabel);
    fireEvent.change(screen.getByRole("textbox", { name: "生成内容名称" }), {
      target: { value: " 自定义期末提纲 " },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    expect(await screen.findByRole("link", { name: "查看生成内容 复习提纲 · 自定义期末提纲" })).toHaveAttribute(
      "href",
      "/generated-contents/gen_1",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/generated-contents/gen_1",
      expect.objectContaining({
        body: JSON.stringify({ title: "自定义期末提纲" }),
        method: "PATCH",
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "复习提纲 · 自定义期末提纲 更多操作" }));
    fireEvent.click(await screen.findByText("删除"));
    expect(screen.getByRole("dialog", { name: "删除生成内容" })).toHaveTextContent("自定义期末提纲");
    expect(screen.getByRole("dialog", { name: "删除生成内容" })).toHaveTextContent(
      "该内容及其引用记录将被永久删除，无法恢复",
    );
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => {
      expect(screen.queryByRole("link", { name: "查看生成内容 复习提纲 · 自定义期末提纲" })).not.toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/generated-contents/gen_1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
