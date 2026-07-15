import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GeneratedContentRenderer } from "../../../src/features/generated-content/GeneratedContentRenderer";

const base = { generation_status: "success", content: null, content_json: null };

describe("GeneratedContentRenderer", () => {
  it("dispatches valid content and degrades malformed or unknown content", () => {
    const { rerender } = render(<MantineProvider><GeneratedContentRenderer content={{ ...base, content_type: "outline", content_json: { sections: [{ id: "sec_001", sort_order: 1, title: "Section", summary: "Summary", review_suggestion: "Review" }] } } as never} /></MantineProvider>);
    const section = screen.getByRole("button", { name: "Section" });
    expect(section).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(section);
    expect(section).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Summary")).toBeInTheDocument();
    rerender(<MantineProvider><GeneratedContentRenderer content={{ ...base, content_type: "quiz", content_json: { questions: "broken" } } as never} /></MantineProvider>);
    expect(screen.getByText("内容结构不可读取")).toBeInTheDocument();
    rerender(<MantineProvider><GeneratedContentRenderer content={{ ...base, content_type: "future_type", content: "Readable fallback" } as never} /></MantineProvider>);
    expect(screen.getByText("Readable fallback")).toBeInTheDocument();
  });

  it("renders handout content as markdown without citation entries", () => {
    render(<MantineProvider><GeneratedContentRenderer content={{ ...base, content_type: "handout", content: "# Handout title\n\nSource note.\n\nThis is **important**.\n\nInline math $R_B = 2 \\times R_b$.", source_citations: [{ material_name: "notes.md", hit_text: "hidden citation" }] } as never} /></MantineProvider>);

    expect(screen.getByRole("heading", { name: "Handout title" })).toBeInTheDocument();
    expect(screen.getByText("Source note.")).toBeInTheDocument();
    expect(screen.getByText("important").tagName).toBe("STRONG");
    expect(document.querySelector(".handout-markdown")).toBeInTheDocument();
    expect(document.querySelector(".katex")).toBeInTheDocument();
    expect(screen.queryByText("notes.md")).not.toBeInTheDocument();
    expect(screen.queryByText("hidden citation")).not.toBeInTheDocument();
  });

  it("renders task test answers only after a question is submitted", () => {
    render(
      <MantineProvider>
        <GeneratedContentRenderer
          content={{
            ...base,
            content_type: "task_test",
            content_json: {
              questions: [
                {
                  id: "q_1",
                  sort_order: 1,
                  question_type: "true_false",
                  question_text: "TCP 是面向连接的协议。",
                  options: [],
                  correct_answer: true,
                  explanation: "TCP 会在传输数据前建立连接。",
                },
              ],
            },
          } as never}
        />
      </MantineProvider>,
    );

    expect(screen.getByText("TCP 是面向连接的协议。")).toBeInTheDocument();
    expect(screen.queryByText("正确答案：正确")).not.toBeInTheDocument();
    const card = screen.getByLabelText("第 1 题：TCP 是面向连接的协议。");
    fireEvent.click(within(card).getByRole("button", { name: "正确" }));
    fireEvent.click(within(card).getByRole("button", { name: "提交答案" }));
    expect(within(card).getByText("回答正确")).toBeInTheDocument();
    expect(within(card).getByText("正确答案：正确")).toBeInTheDocument();
  });
  it("resets task test interaction state when rendered content id changes", () => {
    const oldContent = {
      ...base,
      id: "gen_old",
      content_type: "task_test",
      content_json: {
        questions: [
          {
            id: "q_001",
            sort_order: 1,
            question_type: "single_choice",
            question_text: "旧题：向量空间必须满足哪类结构？",
            options: [
              { id: "A", text: "加法和数乘封闭" },
              { id: "B", text: "只包含零向量" },
            ],
            correct_answer: "A",
            explanation: "旧解析。",
          },
        ],
      },
    };
    const newContent = {
      ...oldContent,
      id: "gen_new",
      content_json: {
        questions: [
          {
            id: "q_001",
            sort_order: 1,
            question_type: "single_choice",
            question_text: "新题：线性相关说明什么？",
            options: [
              { id: "A", text: "存在非零系数使线性组合为零" },
              { id: "B", text: "所有向量都为零" },
            ],
            correct_answer: "A",
            explanation: "新解析。",
          },
        ],
      },
    };

    const { rerender } = render(<MantineProvider><GeneratedContentRenderer content={oldContent as never} /></MantineProvider>);
    const oldCard = screen.getByLabelText("第 1 题：旧题：向量空间必须满足哪类结构？");
    fireEvent.click(within(oldCard).getByRole("button", { name: "B. 只包含零向量" }));
    fireEvent.click(within(oldCard).getByRole("button", { name: "提交答案" }));
    expect(within(oldCard).getByText("回答错误")).toBeInTheDocument();

    rerender(<MantineProvider><GeneratedContentRenderer content={newContent as never} /></MantineProvider>);

    const newCard = screen.getByLabelText("第 1 题：新题：线性相关说明什么？");
    expect(within(newCard).getByRole("button", { name: "A. 存在非零系数使线性组合为零" })).not.toBeDisabled();
    expect(within(newCard).getByRole("button", { name: "提交答案" })).toBeDisabled();
    expect(within(newCard).queryByText("正确答案：A")).not.toBeInTheDocument();
    expect(within(newCard).queryByText("解析：新解析。")).not.toBeInTheDocument();
  });
});
