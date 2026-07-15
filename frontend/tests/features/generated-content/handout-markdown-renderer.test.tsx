import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HandoutMarkdownRenderer } from "../../../src/features/generated-content/renderers/handout/HandoutMarkdownRenderer";

describe("HandoutMarkdownRenderer", () => {
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
});
