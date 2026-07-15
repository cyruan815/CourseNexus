import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

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
});
