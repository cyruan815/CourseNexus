import { Alert, Button } from "@mantine/core";
import { useState } from "react";
import type { ChoiceId, QuizQuestion } from "../types";

const difficultyLabel: Record<string, string> = { easy: "简单", medium: "中等", hard: "困难" };

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
  const choose = (value: ChoiceId) => { if (!selected) { setAnswers((current) => ({ ...current, [question.id]: value })); setShowHint(false); } };
  const optionReason = (option: QuizQuestion["options"][number]) => {
    if (option.explanation) return option.explanation;
    if (option.id === question.correct_answer) return question.explanation;
    return null;
  };
  if (finished) return <div className="gc-quiz-completion"><span>测验完成</span><h2>正确率 {Math.round(correct / ordered.length * 100)}%</h2><p>{correct} / {ordered.length} 题正确</p><Button onClick={() => { setAnswers({}); setIndex(0); setShowHint(false); setFinished(false); }}>重新开始</Button></div>;
  return <section className="gc-quiz-shell">
    <div className="gc-quiz-meta"><span>第 {index + 1} / {ordered.length} 题</span><span className="gc-quiz-level">{difficultyLabel[question.difficulty] ?? question.difficulty}</span></div>
    <div className="gc-quiz-progress"><span style={{ width: `${((index + 1) / ordered.length) * 100}%` }} /></div>
    <h2 className="gc-quiz-question">{question.question_text}</h2>
    {question.hint && !selected ? <><button className="gc-quiz-hint-button" onClick={() => setShowHint((value) => !value)} type="button">{showHint ? "收起提示" : "查看提示"}</button>{showHint ? <div className="gc-quiz-hint">{question.hint}</div> : null}</> : null}
    <div className={`gc-quiz-options ${selected ? "gc-quiz-answered" : ""}`} role="radiogroup">
      {question.options.map((option) => {
        const isCorrect = option.id === question.correct_answer;
        const isWrongSelected = selected === option.id && !isCorrect;
        const reason = selected ? optionReason(option) : null;
        return <button aria-checked={selected === option.id} aria-label={`${option.id}. ${option.text}`} className={`gc-quiz-option ${selected && isCorrect ? "gc-quiz-option-correct" : ""} ${isWrongSelected ? "gc-quiz-option-wrong" : ""}`} disabled={Boolean(selected)} key={option.id} onClick={() => choose(option.id)} role="radio" type="button"><span className="gc-quiz-option-head"><span className="gc-quiz-letter">{option.id}</span><span>{option.text}</span>{selected && isCorrect ? <span className="gc-quiz-mark">✓</span> : null}{isWrongSelected ? <span className="gc-quiz-mark">×</span> : null}</span>{reason ? <span className="gc-quiz-reason">{reason}</span> : null}</button>;
      })}
    </div>
    <div className="gc-quiz-navigation"><Button disabled={index === 0} onClick={() => { setIndex(index - 1); setShowHint(false); }} variant="default">上一题</Button><Button disabled={!selected} onClick={() => { if (index === ordered.length - 1) setFinished(true); else setIndex(index + 1); setShowHint(false); }}>{index === ordered.length - 1 ? "完成测验" : "下一题"}</Button></div>
  </section>;
}
