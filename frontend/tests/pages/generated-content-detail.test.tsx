import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GeneratedContentDetailPage } from "../../src/pages/GeneratedContentDetailPage";

function successResponse(data: unknown, requestId = "req_1") {
  return new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderDetailPage(path = "/generated-contents/gen_1") {
  render(
    <MantineProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<GeneratedContentDetailPage />} path="/generated-contents/:generatedContentId" />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("GeneratedContentDetailPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads generated content detail without metadata and citation panels", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      successResponse({
        id: "gen_1",
        user_id: "usr_123",
        course_id: "crs_123",
        study_subtask_id: null,
        source_message_id: null,
        content_type: "outline",
        title: "期末复习提纲",
        content: "第一章重点",
        content_json: {
          sections: [
            {
              id: "sec_1",
              title: "函数与极限",
              summary: "梳理极限定义和常见计算方法",
              review_suggestion: "先复盘定义，再做典型题",
              source_citation_ids: ["cit_1"],
              sort_order: 1,
            },
          ],
        },
        generation_status: "success",
        material_scope_json: { include_all_parsed_materials: true, material_ids: [] },
        error_code: null,
        source_citations: [
          {
            id: "cit_1",
            material_id: "mat_1",
            chunk_id: "chk_1",
            material_name: "第一章.md",
            page: null,
            page_index: 0,
            hit_text: "极限定义",
            sort_order: 1,
          },
        ],
        created_at: "2026-07-09T12:00:00+00:00",
        updated_at: "2026-07-09T12:00:00+00:00",
        deleted_at: null,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderDetailPage();

    expect(await screen.findByRole("heading", { name: "复习提纲 · 期末" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "复习提纲" })).toBeInTheDocument();
    expect(screen.getByText("函数与极限")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "函数与极限" }));
    expect(screen.getByText("梳理极限定义和常见计算方法")).toBeInTheDocument();
    expect(screen.getByText("先复盘定义，再做典型题")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "生成信息" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "引用来源" })).not.toBeInTheDocument();
    expect(screen.queryByText("第一章.md · 页码未知")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/generated-contents/gen_1",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("renders failed generated content without pretending it succeeded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        successResponse({
          id: "gen_failed",
          user_id: "usr_123",
          course_id: "crs_123",
          study_subtask_id: null,
          source_message_id: null,
          content_type: "quiz",
          title: "课程自测",
          content: null,
          content_json: null,
          generation_status: "failed",
          material_scope_json: { include_all_parsed_materials: true, material_ids: [] },
          error_code: "GENERATION_SCHEMA_INVALID",
          source_citations: [],
          created_at: "2026-07-09T12:00:00+00:00",
          updated_at: "2026-07-09T12:00:00+00:00",
          deleted_at: null,
        }),
      ),
    );

    renderDetailPage("/generated-contents/gen_failed");

    expect(await screen.findByRole("heading", { name: "Quiz" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("GENERATION_SCHEMA_INVALID");
    expect(screen.queryByText("当前没有可展示的引用来源")).not.toBeInTheDocument();
  });

  it("renders handout markdown without citation panel or citation entries", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        successResponse({
          id: "gen_handout",
          user_id: "usr_123",
          course_id: "crs_123",
          study_subtask_id: "sub_123",
          source_message_id: null,
          content_type: "handout",
          title: "Nyquist 公式讲义",
          content: "# Nyquist 公式讲义\n\n本讲义基于《物理层.pdf》中“Nyquist 公式”相关内容生成。\n\n这是 **重点** 内容。",
          content_json: { format: "markdown", schema_version: 1 },
          generation_status: "success",
          material_scope_json: { include_all_parsed_materials: false, material_ids: ["mat_1"] },
          error_code: null,
          source_citations: [
            {
              id: "cit_1",
              material_id: "mat_1",
              chunk_id: "chk_1",
              material_name: "物理层.pdf",
              page: "12",
              page_index: 11,
              hit_text: "这段逐条引用不应在 handout 详情页展示",
              sort_order: 1,
            },
          ],
          created_at: "2026-07-09T12:00:00+00:00",
          updated_at: "2026-07-09T12:00:00+00:00",
          deleted_at: null,
        }),
      ),
    );

    renderDetailPage("/generated-contents/gen_handout");

    expect(await screen.findAllByRole("heading", { name: "Nyquist 公式讲义" })).toHaveLength(2);
    expect(screen.getByText("本讲义基于《物理层.pdf》中“Nyquist 公式”相关内容生成。")).toBeInTheDocument();
    expect(screen.getByText("重点").tagName).toBe("STRONG");
    expect(screen.queryByRole("heading", { name: "引用来源" })).not.toBeInTheDocument();
    expect(screen.queryByText("物理层.pdf · 12")).not.toBeInTheDocument();
    expect(screen.queryByText("这段逐条引用不应在 handout 详情页展示")).not.toBeInTheDocument();
  });

  it("renders task test generated content with per-question submit feedback and without citation panel", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        successResponse({
          id: "gen_task_test",
          user_id: "usr_123",
          course_id: "crs_123",
          study_subtask_id: "subtask_2",
          source_message_id: null,
          content_type: "task_test",
          title: "基础题任务测试题",
          content: null,
          content_json: {
            instructions: "只读查看，不保存作答。",
            questions: [
              {
                id: "q_001",
                question_type: "single_choice",
                question_text: "向量空间必须满足哪类结构？",
                options: [
                  { id: "A", text: "加法和数乘封闭" },
                  { id: "B", text: "只包含零向量" },
                ],
                correct_answer: "A",
                explanation: "向量空间需要对加法和数乘封闭。",
                source_citation_ids: ["cit_1"],
                sort_order: 1,
              },
              {
                id: "q_002",
                question_type: "true_false",
                question_text: "TCP 是面向连接的协议。",
                options: [],
                correct_answer: true,
                explanation: "TCP 会在传输数据前建立连接。",
                source_citation_ids: ["cit_1"],
                sort_order: 2,
              },
              {
                id: "q_003",
                question_type: "true_false",
                question_text: "UDP 会在传输数据前建立连接。",
                options: [],
                correct_answer: false,
                explanation: "UDP 是无连接协议。",
                source_citation_ids: ["cit_1"],
                sort_order: 3,
              },
            ],
          },
          generation_status: "success",
          material_scope_json: { include_all_parsed_materials: false, material_ids: ["mat_1"] },
          error_code: null,
          source_citations: [
            {
              id: "cit_1",
              material_id: "mat_1",
              chunk_id: "chk_1",
              material_name: "物理层.pdf",
              page: "12",
              page_index: 11,
              hit_text: "测试题引用仍展示",
              sort_order: 1,
            },
          ],
          created_at: "2026-07-09T12:00:00+00:00",
          updated_at: "2026-07-09T12:00:00+00:00",
          deleted_at: null,
        }),
      ),
    );

    renderDetailPage("/generated-contents/gen_task_test");

    expect(await screen.findByRole("heading", { name: "基础题任务测试题" })).toBeInTheDocument();
    expect(screen.getByText("向量空间必须满足哪类结构？")).toBeInTheDocument();
    expect(screen.queryByText("正确答案：A")).not.toBeInTheDocument();

    // 单题导航：逐题前进查看，未提交前不显示答案反馈。
    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    expect(screen.getByText("TCP 是面向连接的协议。")).toBeInTheDocument();
    expect(screen.queryByText("正确答案：正确")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    expect(screen.getByText("UDP 会在传输数据前建立连接。")).toBeInTheDocument();
    expect(screen.queryByText("正确答案：错误")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "上一题" }));
    fireEvent.click(screen.getByRole("button", { name: "上一题" }));

    const firstCard = screen.getByLabelText("第 1 题：向量空间必须满足哪类结构？");
    fireEvent.click(within(firstCard).getByRole("button", { name: "A. 加法和数乘封闭" }));
    fireEvent.click(within(firstCard).getByRole("button", { name: "提交答案" }));
    expect(within(firstCard).getByText("回答正确")).toBeInTheDocument();
    expect(within(firstCard).getByText("正确答案：A")).toBeInTheDocument();
    expect(within(firstCard).getByText("解析：向量空间需要对加法和数乘封闭。")).toBeInTheDocument();

    expect(screen.queryByRole("heading", { name: "引用来源" })).not.toBeInTheDocument();
    expect(screen.queryByText("物理层.pdf · 12")).not.toBeInTheDocument();
    expect(screen.queryByText("测试题引用仍展示")).not.toBeInTheDocument();
  });
});
