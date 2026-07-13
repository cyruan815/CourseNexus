import { Alert, Badge, Button, Group, Progress, Radio, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import type { ChoiceId, QuizQuestion } from "../types";

export function QuizResult({ questions }: { questions: QuizQuestion[] }) {
  const ordered = [...questions].sort((a, b) => a.sort_order - b.sort_order);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, ChoiceId>>({});
  const [showHint, setShowHint] = useState(false);
  const [finished, setFinished] = useState(false);
  if (!ordered.length) return <Alert color="gray">暂无可作答题目</Alert>;
  const question = ordered[index];
  const selected = answers[question.id];
  const correct = ordered.filter((item) => answers[item.id] === item.correct_answer).length;
  const choose = (value: string) => {
    if (!selected) setAnswers((current) => ({ ...current, [question.id]: value as ChoiceId }));
  };
  if (finished) return <Stack align="center" className="gc-completion"><Title order={2}>小测完成</Title><Text fw={700}>正确率 {Math.round(correct / ordered.length * 100)}%</Text><Text>{correct} / {ordered.length} 题正确</Text><Button onClick={() => { setAnswers({}); setIndex(0); setShowHint(false); setFinished(false); }}>重新开始</Button></Stack>;
  return <Stack gap="md">
    <Group justify="space-between"><Text size="sm">第 {index + 1} / {ordered.length} 题</Text><Badge variant="light">{question.difficulty}</Badge></Group>
    <Progress value={(index + 1) / ordered.length * 100} />
    <Title order={3}>{question.question_text}</Title>
    {question.hint && !selected ? <><Button onClick={() => setShowHint((v) => !v)} variant="subtle">查看提示</Button>{showHint && <Alert>{question.hint}</Alert>}</> : null}
    <Radio.Group onChange={choose} value={selected ?? ""}><Stack>{question.options.map((option) => <Radio disabled={Boolean(selected)} key={option.id} label={`${option.id}. ${option.text}`} value={option.id} />)}</Stack></Radio.Group>
    {selected ? <Alert color={selected === question.correct_answer ? "teal" : "red"} title={selected === question.correct_answer ? "回答正确" : `回答错误，正确答案是 ${question.correct_answer}`}>{question.explanation}</Alert> : null}
    <Group justify="space-between"><Button disabled={index === 0} onClick={() => { setIndex(index - 1); setShowHint(false); }} variant="default">上一题</Button><Button disabled={!selected} onClick={() => { if (index === ordered.length - 1) setFinished(true); else setIndex(index + 1); setShowHint(false); }}>{index === ordered.length - 1 ? "完成测验" : "下一题"}</Button></Group>
  </Stack>;
}
