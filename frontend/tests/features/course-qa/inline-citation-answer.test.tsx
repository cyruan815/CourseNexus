import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  InlineCitationAnswer,
  type InlineAnswerCitation,
} from "../../../src/features/course-qa/InlineCitationAnswer";

const citations: InlineAnswerCitation[] = [
  {
    chunk_id: "chk_1",
    hit_text: "高带宽、抗干扰、低衰减",
    material_id: "mat_1",
    material_name: "Chap7 物理层.pdf",
    page: 18,
    page_index: 17,
  },
  {
    chunk_id: "chk_2",
    hit_text: "光纤属于有线介质",
    material_id: "mat_1",
    material_name: "Chap7 物理层.pdf",
    page: 15,
    page_index: 14,
  },
];

describe("InlineCitationAnswer", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders adjacent standard and single-bracket citation markers", () => {
    render(
      <MantineProvider>
        <InlineCitationAnswer citations={citations} content="答案是光纤 [[cite:1]][cite:2]" />
      </MantineProvider>,
    );

    expect(screen.getByRole("button", { name: "查看引用 1：Chap7 物理层.pdf" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看引用 2：Chap7 物理层.pdf" })).toBeInTheDocument();
    expect(screen.queryByText("[cite:2]", { exact: false })).not.toBeInTheDocument();
  });

  it("opens an accessible PDF at the cited page", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        data: {
          id: "mat_1",
          course_id: "crs_1",
          user_id: "usr_1",
          folder_id: null,
          name: "Chap7 物理层.pdf",
          material_type: "pdf",
          source_type: "file",
          file_url: "materials/source.pdf",
          source_url: null,
          file_size: 1024,
          mime_type: "application/pdf",
          parse_status: "parsed",
          parse_error: null,
          page_count: 20,
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-01T00:00:00Z",
          deleted_at: null,
        },
        meta: { request_id: "req_material" },
      }), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response("%PDF-1.4", {
        status: 200,
        headers: { "Content-Type": "application/pdf" },
      }));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:citation-pdf"),
      revokeObjectURL: vi.fn(),
    });

    render(
      <MantineProvider>
        <InlineCitationAnswer citations={citations} content="答案是光纤 [[cite:1]]" />
      </MantineProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "查看引用 1：Chap7 物理层.pdf" }));

    expect(await screen.findByTitle("Chap7 物理层.pdf 第 18 页")).toHaveAttribute(
      "src",
      "blob:citation-pdf#page=18",
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/materials/mat_1",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/materials/mat_1/content",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("shows the saved parsed-text snippet when no page is available", async () => {
    const markdownCitation: InlineAnswerCitation = {
      chunk_id: "chk_markdown",
      hit_text: "这是生成回答时保存的解析文本片段。",
      material_id: "mat_markdown",
      material_name: "课堂笔记.md",
      page: null,
      page_index: 0,
    };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      data: {
        id: "mat_markdown",
        course_id: "crs_1",
        user_id: "usr_1",
        folder_id: null,
        name: "课堂笔记.md",
        material_type: "markdown",
        source_type: "file",
        file_url: "materials/source.md",
        source_url: null,
        file_size: 128,
        mime_type: "text/markdown",
        parse_status: "parsed",
        parse_error: null,
        page_count: null,
        created_at: "2026-07-01T00:00:00Z",
        updated_at: "2026-07-01T00:00:00Z",
        deleted_at: null,
      },
      meta: { request_id: "req_material" },
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MantineProvider>
        <InlineCitationAnswer citations={[markdownCitation]} content="课堂笔记说明了这一点 [[cite:1]]" />
      </MantineProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "查看引用 1：课堂笔记.md" }));

    expect(await screen.findByRole("dialog", { name: /引用来源.*课堂笔记\.md/ })).toBeInTheDocument();
    expect(screen.getByText("解析文本")).toBeInTheDocument();
    expect(screen.getByText("页码未知")).toBeInTheDocument();
    expect(screen.getByText("这是生成回答时保存的解析文本片段。")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("keeps a citation snapshot visible when the source was deleted", () => {
    const deletedCitation: InlineAnswerCitation = {
      chunk_id: null,
      hit_text: "历史回答保存的合法引用快照。",
      material_id: null,
      material_name: "已删除资料.pdf",
      page: 6,
      page_index: 5,
    };
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MantineProvider>
        <InlineCitationAnswer citations={[deletedCitation]} content="历史回答 [[cite:1]]" />
      </MantineProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "查看引用 1：已删除资料.pdf" }));

    expect(screen.getByRole("alert")).toHaveTextContent("来源不可用");
    expect(screen.getByText("历史回答保存的合法引用快照。")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
