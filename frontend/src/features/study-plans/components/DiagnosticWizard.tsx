import { useMemo, useState } from "react";
import { Alert, Badge, Button, Group, Paper, Radio, Stack, Text, Textarea } from "@mantine/core";
import { IconClipboardText, IconRefresh, IconSparkles } from "@tabler/icons-react";

import { ApiError } from "../../../api/errors";
import {
  createDiagnosticProfile,
  fetchDiagnosticQuestions,
} from "../api";
import type { MaterialScope } from "../../materials/types";
import type {
  MasteryLevel,
  StudyPlanDiagnosticProfile,
  StudyPlanDiagnosticQuestion,
  StudyPlanTopicMasteryAnswer,
  WeakArea,
} from "../types";

interface DiagnosticWizardProps {
  courseId: string | undefined;
  goalText: string;
  materialScope: MaterialScope;
  profile: StudyPlanDiagnosticProfile | null;
  onProfileReady: (profile: StudyPlanDiagnosticProfile) => void;
  onProfileCleared: () => void;
}

function diagnosticErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "NO_PARSED_MATERIAL") {
      return "当前资料还没有可用解析结果，请先上传并等待解析完成。";
    }
    if (error.code === "DIAGNOSTIC_STALE") {
      return "诊断问题已过期，请重新获取问题并作答。";
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "学情诊断处理失败，请稍后重试。";
}

function isMasteryLevel(value: string): value is MasteryLevel {
  return ["none", "heard", "some", "familiar"].includes(value);
}

function isWeakArea(value: string): value is WeakArea {
  return ["concept", "calculation", "application", "memorization", "other"].includes(value);
}

function sortQuestions(questions: StudyPlanDiagnosticQuestion[]) {
  return [...questions].sort((left, right) => left.sort_order - right.sort_order);
}

export function DiagnosticWizard({
  courseId,
  goalText,
  materialScope,
  profile,
  onProfileReady,
  onProfileCleared,
}: DiagnosticWizardProps) {
  const [questionVersion, setQuestionVersion] = useState<"study_plan_diagnostic_v1" | null>(null);
  const [questions, setQuestions] = useState<StudyPlanDiagnosticQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [diagnosticNote, setDiagnosticNote] = useState("");
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const orderedQuestions = useMemo(() => sortQuestions(questions), [questions]);
  const hasQuestions = orderedQuestions.length > 0;

  const canSubmit = useMemo(() => {
    if (!questionVersion || !hasQuestions) {
      return false;
    }

    return orderedQuestions.every((question) => {
      if (!question.required || question.question_type === "diagnostic_note") {
        return true;
      }
      return Boolean(answers[question.question_id]);
    });
  }, [answers, hasQuestions, orderedQuestions, questionVersion]);

  async function loadQuestions() {
    if (!courseId || !goalText.trim()) {
      setError("请先填写学习目标，再开始学情诊断。");
      return;
    }

    setIsLoadingQuestions(true);
    setError(null);

    try {
      const response = await fetchDiagnosticQuestions(courseId, {
        goal_text: goalText.trim(),
        material_scope: materialScope,
      });
      setQuestionVersion(response.question_version);
      setQuestions(response.questions);
      setAnswers({});
      setDiagnosticNote("");
      onProfileCleared();
    } catch (nextError) {
      setError(diagnosticErrorMessage(nextError));
    } finally {
      setIsLoadingQuestions(false);
    }
  }

  async function submitProfile() {
    if (!courseId || !questionVersion || !canSubmit) {
      return;
    }

    const topicMastery: StudyPlanTopicMasteryAnswer[] = orderedQuestions
      .filter((question) => question.question_type === "topic_mastery")
      .flatMap((question) => {
        const answer = answers[question.question_id];
        if (!question.topic_id || !question.topic_title || !answer || !isMasteryLevel(answer)) {
          return [];
        }
        return [{
          topic_id: question.topic_id,
          topic_title: question.topic_title,
          mastery_level: answer,
        }];
      });
    const weakAreaAnswer = orderedQuestions
      .filter((question) => question.question_type === "weak_area")
      .map((question) => answers[question.question_id])
      .find((answer): answer is WeakArea => Boolean(answer) && isWeakArea(answer));

    if (!weakAreaAnswer) {
      setError("请选择最担心的学习薄弱点。");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const nextProfile = await createDiagnosticProfile(courseId, {
        question_version: questionVersion,
        topic_mastery: topicMastery,
        weak_area: weakAreaAnswer,
        diagnostic_note: diagnosticNote.trim() || null,
        material_scope: materialScope,
      });
      onProfileReady(nextProfile);
    } catch (nextError) {
      setError(diagnosticErrorMessage(nextError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Paper className="study-plan-diagnosis" radius="md" withBorder>
      <Group justify="space-between" wrap="nowrap">
        <Stack gap={2}>
          <Text fw={750}>学情诊断</Text>
          <Text c="dimmed" size="sm">根据资料与目标生成诊断题，并把后端画像用于计划预览。</Text>
        </Stack>
        <Badge color={profile ? "teal" : "blue"} variant="light">
          {profile ? "画像已生成" : "可选"}
        </Badge>
      </Group>

      {error ? (
        <Alert color="red" role="alert" variant="light">
          {error}
        </Alert>
      ) : null}

      {profile ? (
        <Alert color="teal" icon={<IconSparkles size={16} />} role="status" variant="light">
          诊断已完成
        </Alert>
      ) : null}

      {hasQuestions ? (
        <Stack gap="sm">
          {orderedQuestions.map((question) => {
            if (question.question_type === "diagnostic_note") {
              return (
                <Textarea
                  key={question.question_id}
                  label={question.question_text}
                  minRows={3}
                  onChange={(event) => setDiagnosticNote(event.currentTarget.value)}
                  placeholder={question.placeholder ?? undefined}
                  value={diagnosticNote}
                />
              );
            }

            return (
              <Radio.Group
                key={question.question_id}
                label={question.question_text}
                onChange={(value) => setAnswers((current) => ({ ...current, [question.question_id]: value }))}
                value={answers[question.question_id] ?? ""}
              >
                <Stack gap={6} mt={6}>
                  {question.options.map((option) => (
                    <Radio key={option.value} label={option.label} value={option.value} />
                  ))}
                </Stack>
              </Radio.Group>
            );
          })}
        </Stack>
      ) : null}

      <Group justify="space-between">
        <Button
          leftSection={hasQuestions ? <IconRefresh size={16} /> : <IconClipboardText size={16} />}
          loading={isLoadingQuestions}
          onClick={loadQuestions}
          variant="light"
        >
          {hasQuestions ? "重新获取诊断题" : "开始学情诊断"}
        </Button>
        {hasQuestions ? (
          <Button disabled={!canSubmit} loading={isSubmitting} onClick={submitProfile}>
            提交诊断
          </Button>
        ) : null}
      </Group>
    </Paper>
  );
}
