import { Badge, Paper, Stack, Text } from "@mantine/core";

import type { TaskTestQuestion } from "../types";

function answerLabel(answer: string | boolean | string[]) {
  if (typeof answer === "boolean") return answer ? "正确" : "错误";
  return Array.isArray(answer) ? answer.join("、") : answer;
}

export function TaskTestResult({ questions }: { questions: TaskTestQuestion[] }) {
  const ordered = [...questions].sort((left, right) => left.sort_order - right.sort_order);

  return (
    <Stack gap="md">
      <Text c="dimmed" size="sm">
        当前为任务测试题只读视图，可查看题目、答案和解析；作答、判分和记录保存后续接入。
      </Text>
      {ordered.map((question, index) => (
        <Paper className="gc-task-test-question" key={question.id} radius="md" withBorder>
          <Stack gap="xs">
            <Stack gap={4}>
              <div>
                <Badge variant="light">第 {index + 1} 题</Badge>{" "}
                <Badge color="gray" variant="light">{question.question_type}</Badge>
              </div>
              <Text fw={750}>{question.question_text}</Text>
            </Stack>
            {question.options?.length ? (
              <Stack gap={4}>
                {question.options.map((option) => (
                  <Text key={option.id} size="sm">
                    {option.id}. {option.text}
                  </Text>
                ))}
              </Stack>
            ) : null}
            <Text fw={700} size="sm">正确答案：{answerLabel(question.correct_answer)}</Text>
            {question.explanation ? (
              <Text c="dimmed" size="sm">解析：{question.explanation}</Text>
            ) : null}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}
