import { Badge, Button, Checkbox, Group, Paper, Stack, Text, Textarea } from "@mantine/core";
import { useState } from "react";

import type { TaskTestAnswer, TaskTestQuestion } from "../types";

type DraftAnswer = TaskTestAnswer | undefined;
type AnswerState = Record<string, DraftAnswer>;
type SubmittedState = Record<string, boolean>;

interface InteractionState {
  answers: AnswerState;
  attemptKey?: string | null;
  submitted: SubmittedState;
}

interface TaskTestResultProps {
  attemptKey?: string | null;
  questions: TaskTestQuestion[];
}

function typeLabel(type: TaskTestQuestion["question_type"]) {
  const labels = {
    single_choice: "单选",
    multiple_choice: "多选",
    true_false: "判断",
    short_answer: "简答",
  } satisfies Record<TaskTestQuestion["question_type"], string>;
  return labels[type];
}

function answerLabel(answer: TaskTestQuestion["correct_answer"]) {
  if (typeof answer === "boolean") return answer ? "正确" : "错误";
  return Array.isArray(answer) ? answer.join("、") : answer;
}

function sameChoiceSet(left: string[], right: string[]) {
  if (left.length !== right.length) return false;
  const normalizedLeft = [...left].sort();
  const normalizedRight = [...right].sort();
  return normalizedLeft.every((value, index) => value === normalizedRight[index]);
}

function selectedValues(answer: DraftAnswer): string[] {
  return Array.isArray(answer) ? answer : [];
}

function hasAnswer(question: TaskTestQuestion, answer: DraftAnswer) {
  if (question.question_type === "multiple_choice") return Array.isArray(answer) && answer.length > 0;
  if (question.question_type === "short_answer") return typeof answer === "string" && answer.trim().length > 0;
  return answer !== undefined;
}

function isCorrect(question: TaskTestQuestion, answer: DraftAnswer): boolean | null {
  if (question.question_type === "short_answer") return null;
  if (question.question_type === "multiple_choice") {
    return Array.isArray(answer) && Array.isArray(question.correct_answer)
      ? sameChoiceSet(answer, question.correct_answer)
      : false;
  }
  return answer === question.correct_answer;
}

export function TaskTestResult({ attemptKey, questions }: TaskTestResultProps) {
  const ordered = [...questions].sort((left, right) => left.sort_order - right.sort_order);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [interaction, setInteraction] = useState<InteractionState>(() => ({
    answers: {},
    attemptKey,
    submitted: {},
  }));
  const answers = interaction.attemptKey === attemptKey ? interaction.answers : {};
  const submitted = interaction.attemptKey === attemptKey ? interaction.submitted : {};
  const activeIndex = Math.min(currentIndex, Math.max(ordered.length - 1, 0));

  const setAnswer = (questionId: string, answer: DraftAnswer) => {
    setInteraction((current) => {
      const currentAnswers = current.attemptKey === attemptKey ? current.answers : {};
      const currentSubmitted = current.attemptKey === attemptKey ? current.submitted : {};
      return {
        answers: { ...currentAnswers, [questionId]: answer },
        attemptKey,
        submitted: currentSubmitted,
      };
    });
  };

  const toggleMultipleChoice = (questionId: string, optionId: string) => {
    setInteraction((current) => {
      const currentAnswers = current.attemptKey === attemptKey ? current.answers : {};
      const currentSubmitted = current.attemptKey === attemptKey ? current.submitted : {};
      const currentValues = selectedValues(currentAnswers[questionId]);
      const nextValues = currentValues.includes(optionId)
        ? currentValues.filter((value) => value !== optionId)
        : [...currentValues, optionId];
      return {
        answers: { ...currentAnswers, [questionId]: nextValues },
        attemptKey,
        submitted: currentSubmitted,
      };
    });
  };

  return (
    <Stack gap="md">
      <Text className="gc-task-test-intro" size="sm">
        先完成作答，再逐题提交查看反馈。作答结果仅保存在当前页面，不会写入学习记录。
      </Text>
      {ordered.map((question, index) => {
        if (index !== activeIndex) return null;

        const answer = answers[question.id];
        const isSubmitted = Boolean(submitted[question.id]);
        const correct = isSubmitted ? isCorrect(question, answer) : null;
        const canSubmit = hasAnswer(question, answer);

        return (
          <Paper
            aria-label={`第 ${index + 1} 题：${question.question_text}`}
            className="gc-task-test-question"
            key={question.id}
            radius="md"
            withBorder
          >
            <Stack gap="sm">
              <Stack gap={4}>
                <Group gap="xs">
                  <Badge variant="light">第 {index + 1} 题</Badge>
                  <Badge color="gray" variant="light">{typeLabel(question.question_type)}</Badge>
                </Group>
                <Text fw={750}>{question.question_text}</Text>
              </Stack>

              {question.question_type === "single_choice" ? (
                <Stack className="gc-task-test-options" gap="xs">
                  {question.options.map((option) => {
                    const selected = answer === option.id;
                    return (
                      <Button
                        className={selected ? "gc-task-test-option is-selected" : "gc-task-test-option"}
                        disabled={isSubmitted}
                        key={option.id}
                        onClick={() => setAnswer(question.id, option.id)}
                        variant={selected ? "light" : "default"}
                      >
                        {option.id}. {option.text}
                      </Button>
                    );
                  })}
                </Stack>
              ) : null}

              {question.question_type === "multiple_choice" ? (
                <Stack className="gc-task-test-options" gap="xs">
                  {question.options.map((option) => {
                    const selected = selectedValues(answer).includes(option.id);
                    return (
                      <Checkbox
                        checked={selected}
                        className="gc-task-test-checkbox"
                        disabled={isSubmitted}
                        key={option.id}
                        label={`${option.id}. ${option.text}`}
                        onChange={() => toggleMultipleChoice(question.id, option.id)}
                      />
                    );
                  })}
                </Stack>
              ) : null}

              {question.question_type === "true_false" ? (
                <Group gap="xs">
                  <Button
                    className={answer === true ? "gc-task-test-option is-selected" : "gc-task-test-option"}
                    disabled={isSubmitted}
                    onClick={() => setAnswer(question.id, true)}
                    variant={answer === true ? "light" : "default"}
                  >
                    正确
                  </Button>
                  <Button
                    className={answer === false ? "gc-task-test-option is-selected" : "gc-task-test-option"}
                    disabled={isSubmitted}
                    onClick={() => setAnswer(question.id, false)}
                    variant={answer === false ? "light" : "default"}
                  >
                    错误
                  </Button>
                </Group>
              ) : null}

              {question.question_type === "short_answer" ? (
                <Textarea
                  aria-label="填写简答题答案"
                  disabled={isSubmitted}
                  minRows={3}
                  onChange={(event) => setAnswer(question.id, event.currentTarget.value)}
                  placeholder="写下你的答案"
                  value={typeof answer === "string" ? answer : ""}
                />
              ) : null}

              <Group justify="space-between">
                <Group gap="xs">
                  <Button
                    disabled={activeIndex === 0}
                    onClick={() => setCurrentIndex((value) => Math.max(value - 1, 0))}
                    size="xs"
                    variant="default"
                  >
                    上一题
                  </Button>
                  <Button
                    disabled={activeIndex >= ordered.length - 1}
                    onClick={() => setCurrentIndex((value) => Math.min(value + 1, ordered.length - 1))}
                    size="xs"
                    variant="default"
                  >
                    下一题
                  </Button>
                </Group>
                <Button
                  disabled={!canSubmit || isSubmitted}
                  onClick={() => setInteraction((current) => ({
                    answers: current.attemptKey === attemptKey ? current.answers : {},
                    attemptKey,
                    submitted: { ...(current.attemptKey === attemptKey ? current.submitted : {}), [question.id]: true },
                  }))}
                  size="xs"
                  variant="light"
                >
                  提交答案
                </Button>
              </Group>

              {isSubmitted ? (
                <Stack
                  className={correct === true ? "gc-task-test-feedback is-correct" : correct === false ? "gc-task-test-feedback is-wrong" : "gc-task-test-feedback"}
                  gap={6}
                >
                  {correct === null ? (
                    <Text fw={700} size="sm">已提交，下面是参考答案</Text>
                  ) : (
                    <Text fw={700} size="sm">{correct ? "回答正确" : "回答错误"}</Text>
                  )}
                  <Text className="gc-task-test-answer" size="sm">
                    {question.question_type === "short_answer" ? "参考答案" : "正确答案"}：{answerLabel(question.correct_answer)}
                  </Text>
                  {question.explanation ? (
                    <Text size="sm">解析：{question.explanation}</Text>
                  ) : null}
                </Stack>
              ) : null}
            </Stack>
          </Paper>
        );
      })}
    </Stack>
  );
}
