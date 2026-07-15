import { MantineProvider } from "@mantine/core";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
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

  it("adds a flashcard without dropping cards outside the missed-card practice deck", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: {
      id: "gen_cards", content_json: { cards: [
        { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
        { id: "card_002", sort_order: 2, front: "Front 2", back: "Back 2", tags: [], mastery_status: "unknown" },
        { id: "card_003", sort_order: 3, front: "New front", back: "New back", tags: [], mastery_status: "unknown" },
      ] },
    } }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<FlashcardResult generatedContentId="gen_cards" cards={[
      { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
      { id: "card_002", sort_order: 2, front: "Front 2", back: "Back 2", tags: [], mastery_status: "unknown" },
    ]} />);

    fireEvent.click(screen.getByRole("button", { name: "答错 0" }));
    fireEvent.click(screen.getByRole("button", { name: "下一张" }));
    fireEvent.click(screen.getByRole("button", { name: "答对 0" }));
    fireEvent.click(screen.getByRole("button", { name: "上一张" }));
    fireEvent.click(screen.getByRole("button", { name: "只练未掌握" }));
    fireEvent.click(screen.getByRole("button", { name: "更多操作" }));
    fireEvent.click(await screen.findByText("添加卡片"));
    fireEvent.change(await screen.findByRole("textbox", { name: "问题" }), { target: { value: "New front" } });
    fireEvent.change(screen.getByRole("textbox", { name: "答案" }), { target: { value: "New back" } });
    fireEvent.click(screen.getByRole("button", { name: "保存卡片" }));

    expect(await screen.findByText("1 / 3")).toBeInTheDocument();
    const request = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(request.cards.map((card: { front: string }) => card.front)).toEqual(["Front 1", "Front 2", "New front"]);
    vi.unstubAllGlobals();
  });

  it("deletes from a missed-card practice deck without dropping cards outside that deck", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: {
      id: "gen_cards", content_json: { cards: [
        { id: "card_001", sort_order: 1, front: "Front 2", back: "Back 2", tags: [], mastery_status: "unknown" },
      ] },
    } }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<FlashcardResult generatedContentId="gen_cards" cards={[
      { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
      { id: "card_002", sort_order: 2, front: "Front 2", back: "Back 2", tags: [], mastery_status: "unknown" },
    ]} />);

    fireEvent.click(screen.getByRole("button", { name: "答错 0" }));
    fireEvent.click(screen.getByRole("button", { name: "下一张" }));
    fireEvent.click(screen.getByRole("button", { name: "答对 0" }));
    fireEvent.click(screen.getByRole("button", { name: "上一张" }));
    fireEvent.click(screen.getByRole("button", { name: "只练未掌握" }));
    fireEvent.click(screen.getByRole("button", { name: "更多操作" }));
    fireEvent.click(await screen.findByText("删除当前卡片"));
    fireEvent.click(await screen.findByRole("button", { name: "确认删除" }));

    expect(await screen.findByText("Front 2")).toBeInTheDocument();
    const request = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(request.cards.map((card: { front: string }) => card.front)).toEqual(["Front 2"]);
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
    expect(screen.getByRole("heading", { name: "本次答题记录" })).toBeInTheDocument();
    const firstRecord = screen.getByRole("article", { name: "第 1 题答题记录" });
    const secondRecord = screen.getByRole("article", { name: "第 2 题答题记录" });
    expect(within(firstRecord).getByText("Q1")).toBeInTheDocument();
    expect(within(secondRecord).getByText("Q2")).toBeInTheDocument();
    expect(screen.getAllByText("你的选择：B")).toHaveLength(2);
    expect(within(firstRecord).getByRole("radio", { name: "B. B" })).toHaveClass("gc-quiz-option-correct");
    expect(within(secondRecord).getByRole("radio", { name: "B. B" })).toHaveClass("gc-quiz-option-wrong");
    expect(within(secondRecord).getByRole("radio", { name: "A. A" })).toHaveClass("gc-quiz-option-correct");
    expect(screen.getAllByRole("radio")).toHaveLength(8);
    expect(screen.getAllByRole("radio").every((option) => option.hasAttribute("disabled"))).toBe(true);
    expect(screen.queryByRole("button", { name: "下一题" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看提示" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重新开始" }));
    expect(screen.getByText("Q1")).toBeInTheDocument();
    expect(screen.queryByText("本次答题记录")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "B. B" })).not.toBeDisabled();
  });

  it("flips flashcards and retries missed cards", () => {
    renderUi(<FlashcardResult cards={[
      { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
      { id: "card_002", sort_order: 2, front: "Front 2", back: "Back 2", tags: [], mastery_status: "unknown" },
    ]} />);
    expect(screen.queryByText("Back 1")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看答案" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "翻转查看答案" }));
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

  it("shows the flashcard title without the workspace kicker", () => {
    renderUi(<FlashcardResult cards={[
      { id: "card_001", sort_order: 1, front: "Front 1", back: "Back 1", tags: [], mastery_status: "unknown" },
    ]} />);

    expect(screen.getByRole("heading", { name: "知识闪卡" })).toBeInTheDocument();
    expect(screen.queryByText("CourseNexus · 学习工作台")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "打乱卡片" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "更多操作" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看答案" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "翻转查看答案" }));
    expect(screen.getByText("Back 1")).toBeInTheDocument();
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
    renderUi(<KnowledgeListResult generatedContentId="gen_knowledge" items={[
      { id: "kp_001", sort_order: 1, name: "Euler", definition: "Path", importance: "high", related_section: "Graph" },
      { id: "kp_002", sort_order: 2, name: "Matrix", definition: "Array", importance: "low", related_section: "Algebra" },
    ]} />);
    expect(screen.getByRole("heading", { name: "知识点清单" })).toBeInTheDocument();
    expect(screen.queryByText("Graph")).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("搜索知识点"), { target: { value: "Euler" } });
    expect(screen.getByText("Euler")).toBeInTheDocument();
    expect(screen.queryByText("Matrix")).not.toBeInTheDocument();
  });

  it("persists learned knowledge items and keeps progress based on the full list", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: {
      id: "gen_knowledge",
      content_json: { items: [
        { id: "kp_001", sort_order: 1, name: "奈奎斯特定理", definition: "理想信道限制", importance: "high", related_section: "物理层", learned: true },
        { id: "kp_002", sort_order: 2, name: "香农定理", definition: "有噪声信道限制", importance: "high", related_section: "信道容量", learned: true },
      ] },
    } }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<KnowledgeListResult generatedContentId="gen_knowledge" items={[
      { id: "kp_001", sort_order: 1, name: "奈奎斯特定理", definition: "理想信道限制", importance: "high", related_section: "物理层", learned: true },
      { id: "kp_002", sort_order: 2, name: "香农定理", definition: "有噪声信道限制", importance: "high", related_section: "信道容量" },
    ]} />);

    expect(screen.getByText("已学习 1 / 2")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText("奈奎斯特定理").closest("article")).toHaveClass("is-learned");
    fireEvent.change(screen.getByPlaceholderText("搜索知识点"), { target: { value: "香农" } });
    expect(screen.getByText("已学习 1 / 2")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "标记香农定理为已学习" }));

    expect(await screen.findByText("已学习 2 / 2")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("香农定理").closest("article")).toHaveClass("is-learned");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/generated-contents/gen_knowledge/knowledge-items/kp_002/learning-state",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ learned: true }) }),
    );
    vi.unstubAllGlobals();
  });

  it("rolls back a knowledge learning state when persistence fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: "SAVE_FAILED", message: "保存失败" },
    }), { status: 500, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<KnowledgeListResult generatedContentId="gen_knowledge" items={[
      { id: "kp_001", sort_order: 1, name: "奈奎斯特定理", definition: "理想信道限制", importance: "high", related_section: "物理层" },
    ]} />);

    fireEvent.click(screen.getByRole("button", { name: "标记奈奎斯特定理为已学习" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("保存失败");
    expect(screen.getByText("已学习 0 / 1")).toBeInTheDocument();
    expect(screen.getByText("奈奎斯特定理").closest("article")).not.toHaveClass("is-learned");
    vi.unstubAllGlobals();
  });

  it("combines the unlearned button with the importance filter without changing progress", async () => {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    renderUi(<KnowledgeListResult generatedContentId="gen_knowledge" items={[
      { id: "kp_001", sort_order: 1, name: "已学习高重点", definition: "A", importance: "high", related_section: "第一章", learned: true },
      { id: "kp_002", sort_order: 2, name: "未学习高重点", definition: "B", importance: "high", related_section: "第一章" },
      { id: "kp_003", sort_order: 3, name: "未学习低重点", definition: "C", importance: "low", related_section: "第二章" },
    ]} />);

    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(await screen.findByRole("option", { name: "高" }));
    const unlearnedButton = screen.getByRole("button", { name: "未学习" });
    fireEvent.click(unlearnedButton);

    expect(unlearnedButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByText("已学习高重点")).not.toBeInTheDocument();
    expect(screen.getByText("未学习高重点")).toBeInTheDocument();
    expect(screen.queryByText("未学习低重点")).not.toBeInTheDocument();
    expect(screen.getByText("已学习 1 / 3")).toBeInTheDocument();
    expect(screen.getByText("33%")).toBeInTheDocument();
  });
});
