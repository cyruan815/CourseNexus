import { MantineProvider } from "@mantine/core";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FlashcardResult } from "../../../src/features/generated-content/renderers/FlashcardResult";
import { KnowledgeListResult } from "../../../src/features/generated-content/renderers/KnowledgeListResult";
import { OutlineResult } from "../../../src/features/generated-content/renderers/OutlineResult";
import { QuizResult } from "../../../src/features/generated-content/renderers/QuizResult";

function renderUi(ui: React.ReactNode) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("generated content renderers", () => {
  it("shows flashcard feedback for one second and advances automatically", () => {
    vi.useFakeTimers();
    renderUi(<FlashcardResult cards={[
      { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
      { id: "card_002", sort_order: 2, front: "Front 2", back: "Back 2", tags: [], mastery_status: "unknown" },
    ]} />);
    fireEvent.click(screen.getByRole("button", { name: "答对 0" }));
    expect(screen.getByText("答对了！")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(999));
    expect(screen.queryByText("Front 2")).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1));
    expect(screen.getByText("Front 2")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("adds a flashcard from the more menu and persists the deck", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: {
      id: "gen_cards", content_json: { cards: [
        { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
        { id: "card_002", sort_order: 2, front: "New front", back: "New back", tags: [], mastery_status: "unknown" },
      ] },
    } }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<FlashcardResult generatedContentId="gen_cards" cards={[
      { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
    ]} />);
    fireEvent.click(screen.getByRole("button", { name: "更多操作" }));
    fireEvent.click(await screen.findByText("添加卡片"));
    fireEvent.change(await screen.findByRole("textbox", { name: "问题" }), { target: { value: "New front" } });
    fireEvent.change(screen.getByRole("textbox", { name: "答案" }), { target: { value: "New back" } });
    fireEvent.click(screen.getByRole("button", { name: "保存卡片" }));
    expect(await screen.findByText("1 / 2")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/generated-contents/gen_cards/flashcards", expect.objectContaining({ method: "PATCH" }));
    vi.unstubAllGlobals();
  });

  it("shows one quiz question, judges immediately, and reports final accuracy", () => {
    renderUi(<QuizResult questions={[
      { id: "q_001", sort_order: 1, question_text: "Q1", options: (["A", "B", "C", "D"] as const).map((id) => ({ id, text: id, explanation: `Reason ${id}` })), correct_answer: "B", explanation: "Because B", difficulty: "easy", hint: "Think first" },
      { id: "q_002", sort_order: 2, question_text: "Q2", options: (["A", "B", "C", "D"] as const).map((id) => ({ id, text: id })), correct_answer: "A", explanation: "Because A", difficulty: "medium" },
    ]} />);
    expect(screen.getByText("Q1")).toBeInTheDocument();
    expect(screen.queryByText("Q2")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: /B\. B/ }));
    expect(screen.getByText("Reason A")).toBeInTheDocument();
    expect(screen.getByText("Reason B")).toBeInTheDocument();
    expect(screen.getByText("Reason C")).toBeInTheDocument();
    expect(screen.getByText("Reason D")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    fireEvent.click(screen.getByRole("radio", { name: /B\. B/ }));
    expect(screen.queryByText(/正确结论/)).not.toBeInTheDocument();
    expect(screen.queryByText(/与本题考查/)).not.toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "查看答案" }));
    expect(screen.getByText("Back 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "翻转回问题" }));
    expect(screen.getByText("Front 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "答错 0" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "答对 0" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "答错 0" }));
    expect(screen.getByText("再接再厉")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一张" }));
    fireEvent.click(screen.getByRole("button", { name: "答对 0" }));
    expect(screen.getByText("答对了！")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "上一张" }));
    fireEvent.click(screen.getByRole("button", { name: "只练未掌握" }));
    expect(screen.getByText("Front 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "答对 0" }));
    expect(screen.getByRole("button", { name: "练习全部" })).toBeInTheDocument();
  });

  it("navigates outline sections and filters knowledge items", () => {
    const { unmount } = renderUi(<OutlineResult sections={[
      { id: "sec_001", sort_order: 1, title: "First", summary: "One", review_suggestion: "Review one" },
      { id: "sec_002", sort_order: 2, title: "Second", summary: "Two", review_suggestion: "Review two" },
    ]} />);
    expect(screen.queryByText("Two")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Second" }));
    expect(screen.getByText("Two")).toBeVisible();
    expect(screen.getByText("Review two")).toBeVisible();
    unmount();
    renderUi(<KnowledgeListResult items={[
      { id: "kp_001", sort_order: 1, name: "Euler", definition: "Path", importance: "high", related_section: "Graph" },
      { id: "kp_002", sort_order: 2, name: "Matrix", definition: "Array", importance: "low", related_section: "Algebra" },
    ]} />);
    expect(screen.getByRole("heading", { name: "知识点清单" })).toBeInTheDocument();
    expect(screen.queryByText("Graph")).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("搜索知识点"), { target: { value: "Euler" } });
    expect(screen.getByText("Euler")).toBeInTheDocument();
    expect(screen.queryByText("Matrix")).not.toBeInTheDocument();
  });
});
