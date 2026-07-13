import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FlashcardResult } from "../../../src/features/generated-content/renderers/FlashcardResult";
import { KnowledgeListResult } from "../../../src/features/generated-content/renderers/KnowledgeListResult";
import { OutlineResult } from "../../../src/features/generated-content/renderers/OutlineResult";
import { QuizResult } from "../../../src/features/generated-content/renderers/QuizResult";

function renderUi(ui: React.ReactNode) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("generated content renderers", () => {
  it("shows one quiz question, judges immediately, and reports final accuracy", () => {
    renderUi(<QuizResult questions={[
      { id: "q_001", sort_order: 1, question_text: "Q1", options: (["A", "B", "C", "D"] as const).map((id) => ({ id, text: id })), correct_answer: "B", explanation: "Because B", difficulty: "easy" },
      { id: "q_002", sort_order: 2, question_text: "Q2", options: (["A", "B", "C", "D"] as const).map((id) => ({ id, text: id })), correct_answer: "A", explanation: "Because A", difficulty: "medium" },
    ]} />);
    expect(screen.getByText("Q1")).toBeInTheDocument();
    expect(screen.queryByText("Q2")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: /B\. B/ }));
    expect(screen.getByText(/回答正确/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    fireEvent.click(screen.getByRole("radio", { name: /B\. B/ }));
    expect(screen.getByText(/回答错误/)).toBeInTheDocument();
    expect(screen.getByText("Because A")).toBeInTheDocument();
    expect(screen.queryByText("小测完成")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "完成测验" }));
    expect(screen.getByText("正确率 50%")).toBeInTheDocument();
  });

  it("flips flashcards and retries missed cards", () => {
    renderUi(<FlashcardResult cards={[
      { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
      { id: "card_002", sort_order: 2, front: "Front 2", back: "Back 2", tags: [], mastery_status: "unknown" },
    ]} />);
    expect(screen.queryByText("Back 1")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "翻转卡片" }));
    expect(screen.getByText("Back 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "未掌握" }));
    fireEvent.click(screen.getByRole("button", { name: "翻转卡片" }));
    fireEvent.click(screen.getByRole("button", { name: "已掌握" }));
    fireEvent.click(screen.getByRole("button", { name: "只练未掌握" }));
    expect(screen.getByText("Front 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "翻转卡片" }));
    fireEvent.click(screen.getByRole("button", { name: "已掌握" }));
    expect(screen.getByRole("button", { name: "练习全部" })).toBeInTheDocument();
  });

  it("navigates outline sections and filters knowledge items", () => {
    const { unmount } = renderUi(<OutlineResult sections={[
      { id: "sec_001", sort_order: 1, title: "First", summary: "One", review_suggestion: "Review one" },
      { id: "sec_002", sort_order: 2, title: "Second", summary: "Two", review_suggestion: "Review two" },
    ]} />);
    fireEvent.click(screen.getByRole("button", { name: "Second" }));
    expect(screen.getByText("Two")).toBeInTheDocument();
    unmount();
    renderUi(<KnowledgeListResult items={[
      { id: "kp_001", sort_order: 1, name: "Euler", definition: "Path", importance: "high", related_section: "Graph" },
      { id: "kp_002", sort_order: 2, name: "Matrix", definition: "Array", importance: "low", related_section: "Algebra" },
    ]} />);
    fireEvent.change(screen.getByPlaceholderText("搜索知识点"), { target: { value: "Euler" } });
    expect(screen.getByText("Euler")).toBeInTheDocument();
    expect(screen.queryByText("Matrix")).not.toBeInTheDocument();
  });
});
