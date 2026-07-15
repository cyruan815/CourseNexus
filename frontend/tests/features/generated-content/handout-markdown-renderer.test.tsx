import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HandoutMarkdownRenderer } from "../../../src/features/generated-content/renderers/handout/HandoutMarkdownRenderer";

const mermaidMocks = vi.hoisted(() => ({
  initialize: vi.fn(),
  render: vi.fn(),
}));

vi.mock("mermaid", () => ({
  default: mermaidMocks,
}));

describe("HandoutMarkdownRenderer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mermaidMocks.render.mockResolvedValue({
      svg: '<svg data-testid="mermaid-svg" viewBox="0 0 100 40"><text>Flow</text></svg>',
    });
  });

  it("renders supported handout callouts as rounded color blocks", () => {
    render(
      <HandoutMarkdownRenderer
        markdown={[
          "# 第七章 物理层",
          "",
          "> [!NOTE] 注意",
          "> 物理层并不是具体的传输媒体本身。",
          "",
          "> [!EXAMPLE] 例题 1",
          "> 已知信道带宽为 3 kHz，求理论最大传输速率。",
          "",
          "> [!SUMMARY] 核心结论",
          "> 信噪比越高，信道容量越大。",
          "",
          "> [!WARNING] 易错点",
          "> 不能直接把 30 dB 当作普通信噪比代入公式。",
          "",
          "> [!TIP] 解题提示",
          "> 先把 dB 换算为普通比值。",
        ].join("\n")}
      />,
    );

    const note = screen.getByTestId("handout-callout-note");
    expect(note).toHaveClass("handout-callout", "handout-callout-note");
    expect(within(note).getByText("注意")).toBeInTheDocument();
    expect(within(note).getByText("物理层并不是具体的传输媒体本身。")).toBeInTheDocument();

    expect(screen.getByTestId("handout-callout-example")).toHaveClass("handout-callout-example");
    expect(screen.getByTestId("handout-callout-summary")).toHaveClass("handout-callout-summary");
    expect(screen.getByTestId("handout-callout-warning")).toHaveClass("handout-callout-warning");
    expect(screen.getByTestId("handout-callout-tip")).toHaveClass("handout-callout-tip");
  });

  it("keeps bold terms inside callout body inline with formulas", () => {
    render(
      <HandoutMarkdownRenderer
        markdown={[
          "> [!SUMMARY] 核心结论",
          "> - **码元速率** $= B_d$（Baud），**数据率** $= B_d \\log_2 L$ bps。",
        ].join("\n")}
      />,
    );

    const summary = screen.getByTestId("handout-callout-summary");
    const bodyStrong = within(summary).getByText("码元速率");
    expect(bodyStrong).not.toHaveClass("handout-callout-title");
    expect(document.querySelectorAll(".handout-callout-summary .katex").length).toBeGreaterThanOrEqual(2);
  });

  it("keeps ordinary blockquotes and renders math and tables with the formal renderer", () => {
    render(
      <HandoutMarkdownRenderer
        markdown={[
          "> 普通引用不会被当成提示块。",
          "",
          "$$",
          "C = B \\log_2(1 + S/N)",
          "$$",
          "",
          "行内公式 $R_B = 2 \\times R_b$ 也应该渲染。",
          "",
          "| 符号 | 含义 |",
          "| --- | --- |",
          "| C | 信道容量 |",
          "| B | 信道带宽 |",
        ].join("\n")}
      />,
    );

    expect(screen.getByText("普通引用不会被当成提示块。").closest("blockquote")).toHaveClass("handout-blockquote");
    expect(document.querySelectorAll(".katex").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("table")).toHaveClass("handout-table");
    expect(screen.getByRole("columnheader", { name: "符号" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "信道容量" })).toBeInTheDocument();
  });

  it("preserves inline Markdown and math in numbered third-level headings", () => {
    render(<HandoutMarkdownRenderer markdown={"### 1.1 **码元速率** $R_B$"} />);

    const heading = screen.getByRole("heading", { level: 3 });
    expect(within(heading).getByText("码元速率").tagName).toBe("STRONG");
    expect(heading.querySelector(".handout-heading-number")).toHaveTextContent("1.1");
    expect(heading.querySelector(".katex")).not.toBeNull();
  });

  it("keeps callout-looking examples inside fenced code blocks", () => {
    render(
      <HandoutMarkdownRenderer
        markdown={[
          "```md",
          "> [!NOTE] 示例",
          "> 这只是语法示例。",
          "```",
        ].join("\n")}
      />,
    );

    expect(screen.queryByTestId("handout-callout-note")).not.toBeInTheDocument();
    expect(screen.getByText(/\[!NOTE\] 示例/).closest("code")).toBeInTheDocument();
  });

  it("renders fenced Mermaid code as an SVG diagram", async () => {
    render(
      <HandoutMarkdownRenderer
        markdown={["```mermaid", "flowchart LR", "  A[Input] --> B[Output]", "```"].join("\n")}
      />,
    );

    expect(await screen.findByTestId("mermaid-svg")).toBeInTheDocument();
    expect(document.querySelector(".handout-mermaid-diagram")).not.toBeNull();
    expect(mermaidMocks.initialize).toHaveBeenCalledWith(
      expect.objectContaining({ startOnLoad: false, securityLevel: "loose" }),
    );
    expect(mermaidMocks.render).toHaveBeenCalledWith(
      expect.stringMatching(/^handout-mermaid-/),
      "flowchart LR\n  A[Input] --> B[Output]",
    );
  });

  it("renders trusted inline SVG from handout Markdown", () => {
    render(
      <HandoutMarkdownRenderer
        markdown={'<svg data-testid="inline-handout-svg" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" /></svg>'}
      />,
    );

    expect(screen.getByTestId("inline-handout-svg")).toBeInTheDocument();
  });

  it("keeps non-Mermaid fenced code as a normal code block", () => {
    render(<HandoutMarkdownRenderer markdown={["```ts", "const answer = 42;", "```"].join("\n")} />);

    const code = screen.getByText("const answer = 42;").closest("code");
    expect(code).toHaveClass("language-ts");
    expect(code?.closest("pre")).not.toBeNull();
  });

  it("shows Mermaid source when diagram rendering fails", async () => {
    mermaidMocks.render.mockRejectedValueOnce(new Error("Parse error"));

    render(
      <HandoutMarkdownRenderer
        markdown={["```mermaid", "flowchart LR", "  A -->", "```"].join("\n")}
      />,
    );

    const fallback = await screen.findByRole("alert");
    expect(fallback).toHaveTextContent("Mermaid \u56fe\u8868\u6e32\u67d3\u5931\u8d25");
    expect(within(fallback).getByText(/flowchart LR/).closest("code")).toBeInTheDocument();
  });

  it("uses a unique Mermaid render ID for overlapping renders", async () => {
    let resolveFirst: ((value: { svg: string }) => void) | undefined;
    const firstRender = new Promise<{ svg: string }>((resolve) => {
      resolveFirst = resolve;
    });
    mermaidMocks.render
      .mockImplementationOnce(() => firstRender)
      .mockResolvedValueOnce({ svg: '<svg data-testid="latest-mermaid-svg" />' });

    const { rerender } = render(
      <HandoutMarkdownRenderer markdown={["```mermaid", "flowchart LR", "A --> B", "```"].join("\n")} />,
    );
    await waitFor(() => expect(mermaidMocks.render).toHaveBeenCalledTimes(1));

    rerender(
      <HandoutMarkdownRenderer markdown={["```mermaid", "flowchart LR", "B --> C", "```"].join("\n")} />,
    );
    await waitFor(() => expect(mermaidMocks.render).toHaveBeenCalledTimes(2));

    const firstRenderId = mermaidMocks.render.mock.calls[0]?.[0];
    const secondRenderId = mermaidMocks.render.mock.calls[1]?.[0];
    expect(firstRenderId).not.toBe(secondRenderId);

    resolveFirst?.({ svg: '<svg data-testid="stale-mermaid-svg" />' });
    expect(await screen.findByTestId("latest-mermaid-svg")).toBeInTheDocument();
  });
});
