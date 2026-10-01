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
    source_citation_ids: ["cit_1", "cit_2"],
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
  return render(
    <MantineProvider>
      <TaskTestResult
        citations={[
          {
            id: "cit_1",
            chunk_id: "chk_1",
            hit_text: "向量空间对加法和数乘封闭。",
            material_id: "mat_1",
            material_name: "线性代数.md",
            page: null,
            page_index: 0,
          },
          {
            id: "cit_2",
            chunk_id: "chk_2",
            hit_text: "向量空间的八条公理。",
            material_id: "mat_2",
            material_name: "课程习题.pdf",
            page: "18",
            page_index: 17,
          },
          {
            id: "cit_other",
            chunk_id: "chk_3",
            hit_text: "不属于当前题目的来源。",
            material_id: "mat_3",
            material_name: "网络协议.md",
            page: null,
            page_index: 0,
          },
        ]}
        questions={questions}
      />
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
    expect(within(firstCard).getByText("题目来源")).toBeInTheDocument();
    expect(within(firstCard).getByRole("button", { name: "查看第 1 题来源 1：线性代数.md" })).toBeInTheDocument();
    expect(within(firstCard).getByRole("button", { name: "查看第 1 题来源 2：课程习题.pdf" })).toBeInTheDocument();
    expect(within(firstCard).queryByText("网络协议.md")).not.toBeInTheDocument();
    expect(screen.queryByText("正确答案：A、B")).not.toBeInTheDocument();
  });

  it("requires exact option sets for multiple choice", () => {
    renderResult();

    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    const secondCard = screen.getByLabelText("第 2 题：哪些协议是传输层协议？");
    fireEvent.click(within(secondCard).getByRole("checkbox", { name: "A. TCP" }));
    fireEvent.click(within(secondCard).getByRole("checkbox", { name: "B. UDP" }));
    fireEvent.click(within(secondCard).getByRole("button", { name: "提交答案" }));

    expect(within(secondCard).getByText("回答正确")).toBeInTheDocument();
    expect(within(secondCard).getByText("正确答案：A、B")).toBeInTheDocument();
  });

  it("supports true/false questions", () => {
    renderResult();

    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    const thirdCard = screen.getByLabelText("第 3 题：TCP 是面向连接的协议。");
    fireEvent.click(within(thirdCard).getByRole("button", { name: "正确" }));
    fireEvent.click(within(thirdCard).getByRole("button", { name: "提交答案" }));

    expect(within(thirdCard).getByText("回答正确")).toBeInTheDocument();
    expect(within(thirdCard).getByText("正确答案：正确")).toBeInTheDocument();
  });

  it("reveals reference answer for short answer without auto-grading", () => {
    renderResult();

    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
    fireEvent.click(screen.getByRole("button", { name: "下一题" }));
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
  it("clears submitted answers when the attempt key changes even if question ids are reused", () => {
    const firstAttemptQuestions: TaskTestQuestion[] = [
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
    ];
    const secondAttemptQuestions: TaskTestQuestion[] = [
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
    ];

    const { rerender } = render(
      <MantineProvider>
        <TaskTestResult attemptKey="gen_old" questions={firstAttemptQuestions} />
      </MantineProvider>,
    );

    const oldCard = screen.getByLabelText("第 1 题：旧题：向量空间必须满足哪类结构？");
    fireEvent.click(within(oldCard).getByRole("button", { name: "B. 只包含零向量" }));
    fireEvent.click(within(oldCard).getByRole("button", { name: "提交答案" }));
    expect(within(oldCard).getByText("回答错误")).toBeInTheDocument();

    rerender(
      <MantineProvider>
        <TaskTestResult attemptKey="gen_new" questions={secondAttemptQuestions} />
      </MantineProvider>,
    );

    const newCard = screen.getByLabelText("第 1 题：新题：线性相关说明什么？");
    expect(within(newCard).getByRole("button", { name: "A. 存在非零系数使线性组合为零" })).not.toBeDisabled();
    expect(within(newCard).getByRole("button", { name: "B. 所有向量都为零" })).not.toBeDisabled();
    expect(within(newCard).getByRole("button", { name: "提交答案" })).toBeDisabled();
    expect(within(newCard).queryByText("回答错误")).not.toBeInTheDocument();
    expect(within(newCard).queryByText("正确答案：A")).not.toBeInTheDocument();
    expect(within(newCard).queryByText("解析：新解析。")).not.toBeInTheDocument();
  });
});
