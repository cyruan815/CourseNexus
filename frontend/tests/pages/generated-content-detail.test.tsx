import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
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

  it("loads generated content detail and renders outline sections with citations", async () => {
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
    expect(screen.getByText("复习提纲")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "函数与极限" })).toBeInTheDocument();
    expect(screen.getByText("梳理极限定义和常见计算方法")).toBeInTheDocument();
    expect(screen.getByText("先复盘定义，再做典型题")).toBeInTheDocument();
    expect(screen.getByText("第一章.md · 页码未知")).toBeInTheDocument();
    expect(screen.getByText("极限定义")).toBeInTheDocument();
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
    expect(screen.getByText("当前没有可展示的引用来源")).toBeInTheDocument();
  });
});
