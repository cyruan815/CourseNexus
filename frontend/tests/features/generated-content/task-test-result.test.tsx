import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TaskTestResult } from "../../../src/features/generated-content/renderers/TaskTestResult";
import type { TaskTestQuestion } from "../../../src/features/generated-content/types";

const questions: TaskTestQuestion[] = [
  {
    id: "q_1",
    sort_order: 1,
    question_type: "single_choice",
    question_text: "向量空间必须满足哪类结构？",
    options: [
      { id: "A", text: "加法和数乘封闭" },
      { id: "B", text: "只包含零向量" },
      { id: "C", text: "只能做减法" },
      { id: "D", text: "没有运算" },
    ],
    correct_answer: "A",
    explanation: "向量空间需要对加法和数乘封闭。",
  },
  {
    id: "q_2",
    sort_order: 2,
    question_type: "multiple_choice",
    question_text: "哪些协议是传输层协议？",
    options: [
      { id: "A", text: "TCP" },
      { id: "B", text: "UDP" },
      { id: "C", text: "IP" },
      { id: "D", text: "ARP" },
    ],
    correct_answer: ["A", "B"],
    explanation: "TCP 和 UDP 都属于传输层。",
  },
  {
    id: "q_3",
    sort_order: 3,
    question_type: "true_false",
    question_text: "TCP 是面向连接的协议。",
    options: [],
    correct_answer: true,
    explanation: "TCP 会在传输数据前建立连接。",
  },
  {
    id: "q_4",
    sort_order: 4,
    question_type: "short_answer",
    question_text: "简述 Nyquist 公式的用途。",
    options: [],
    correct_answer: "用于估算无噪声信道的最大码元速率。",
    explanation: "Nyquist 公式用于理想低通信道容量估算。",
  },
];

function renderResult() {
  render(
    <MantineProvider>
      <TaskTestResult questions={questions} />
    </MantineProvider>,
  );
}

describe("TaskTestResult", () => {
  it("hides answers until each question is submitted and scores single choice locally", () => {
    renderResult();

    const firstCard = screen.getByLabelText("第 1 题：向量空间必须满足哪类结构？");
    expect(within(firstCard).queryByText("正确答案：A")).not.toBeInTheDocument();

    fireEvent.click(within(firstCard).getByRole("button", { name: "B. 只包含零向量" }));
    fireEvent.click(within(firstCard).getByRole("button", { name: "提交答案" }));

    expect(within(firstCard).getByText("回答错误")).toBeInTheDocument();
    expect(within(firstCard).getByText("正确答案：A")).toBeInTheDocument();
    expect(within(firstCard).getByText("解析：向量空间需要对加法和数乘封闭。")).toBeInTheDocument();
    expect(screen.queryByText("正确答案：A、B")).not.toBeInTheDocument();
  });

  it("requires exact option sets for multiple choice", () => {
    renderResult();

    const secondCard = screen.getByLabelText("第 2 题：哪些协议是传输层协议？");
    fireEvent.click(within(secondCard).getByRole("checkbox", { name: "A. TCP" }));
    fireEvent.click(within(secondCard).getByRole("checkbox", { name: "B. UDP" }));
    fireEvent.click(within(secondCard).getByRole("button", { name: "提交答案" }));

    expect(within(secondCard).getByText("回答正确")).toBeInTheDocument();
    expect(within(secondCard).getByText("正确答案：A、B")).toBeInTheDocument();
  });

  it("supports true/false questions", () => {
    renderResult();

    const thirdCard = screen.getByLabelText("第 3 题：TCP 是面向连接的协议。");
    fireEvent.click(within(thirdCard).getByRole("button", { name: "正确" }));
    fireEvent.click(within(thirdCard).getByRole("button", { name: "提交答案" }));

    expect(within(thirdCard).getByText("回答正确")).toBeInTheDocument();
    expect(within(thirdCard).getByText("正确答案：正确")).toBeInTheDocument();
  });

  it("reveals reference answer for short answer without auto-grading", () => {
    renderResult();

    const fourthCard = screen.getByLabelText("第 4 题：简述 Nyquist 公式的用途。");
    fireEvent.change(within(fourthCard).getByRole("textbox", { name: "填写简答题答案" }), {
      target: { value: "估算信道最大传输能力" },
    });
    fireEvent.click(within(fourthCard).getByRole("button", { name: "提交答案" }));

    expect(within(fourthCard).getByText("已提交，下面是参考答案")).toBeInTheDocument();
    expect(within(fourthCard).getByText("参考答案：用于估算无噪声信道的最大码元速率。")).toBeInTheDocument();
    expect(within(fourthCard).queryByText("回答正确")).not.toBeInTheDocument();
    expect(within(fourthCard).queryByText("回答错误")).not.toBeInTheDocument();
  });
});
