import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
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

    expect(await screen.findByRole("heading", { name: "期末复习提纲" })).toBeInTheDocument();
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

    expect(await screen.findByRole("heading", { name: "课程自测" })).toBeInTheDocument();
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
          title: "Nyquist ????",
          content: "# Nyquist ????\n\n?????????.pdf???Nyquist ??????????\n\n?? **??** ???",
          content_json: { format: "markdown", schema_version: 1 },
          generation_status: "success",
          material_scope_json: { include_all_parsed_materials: false, material_ids: ["mat_1"] },
          error_code: null,
          source_citations: [
            {
              id: "cit_1",
              material_id: "mat_1",
              chunk_id: "chk_1",
              material_name: "???.pdf",
              page: "12",
              page_index: 11,
              hit_text: "????????? handout ?????",
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

    expect(await screen.findAllByRole("heading", { name: "Nyquist ????" })).toHaveLength(2);
    expect(screen.getByText("?????????.pdf???Nyquist ??????????")).toBeInTheDocument();
    expect(screen.getByText("??").tagName).toBe("STRONG");
    expect(screen.queryByRole("heading", { name: "????" })).not.toBeInTheDocument();
    expect(screen.queryByText("???.pdf ? 12")).not.toBeInTheDocument();
    expect(screen.queryByText("????????? handout ?????")).not.toBeInTheDocument();
  });

  it("renders task test generated content as a readonly review view and keeps citations", async () => {
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
          title: "????????",
          content: null,
          content_json: {
            instructions: "???????????",
            questions: [
              {
                id: "q_001",
                question_type: "single_choice",
                question_text: "?????????????",
                options: [
                  { id: "A", text: "???????" },
                  { id: "B", text: "??????" },
                ],
                correct_answer: "A",
                explanation: "???????????????",
                source_citation_ids: ["cit_1"],
                sort_order: 1,
              },
              {
                id: "q_002",
                question_type: "true_false",
                question_text: "TCP ?????????",
                options: [],
                correct_answer: true,
                explanation: "TCP ????????????",
                source_citation_ids: ["cit_1"],
                sort_order: 2,
              },
              {
                id: "q_003",
                question_type: "true_false",
                question_text: "UDP ????????????",
                options: [],
                correct_answer: false,
                explanation: "UDP ???????",
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
              material_name: "???.pdf",
              page: "12",
              page_index: 11,
              hit_text: "????????",
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

    expect(await screen.findByRole("heading", { name: "????????" })).toBeInTheDocument();
    expect(screen.getByText("?????????????")).toBeInTheDocument();
    expect(screen.getByText("?????A")).toBeInTheDocument();
    expect(screen.getByText("TCP ?????????")).toBeInTheDocument();
    expect(screen.getByText("???????")).toBeInTheDocument();
    expect(screen.getByText("UDP ????????????")).toBeInTheDocument();
    expect(screen.getByText("???????")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "????" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "????" })).toBeInTheDocument();
    expect(screen.getByText("???.pdf ? 12")).toBeInTheDocument();
    expect(screen.getByText("????????")).toBeInTheDocument();
  });
});
