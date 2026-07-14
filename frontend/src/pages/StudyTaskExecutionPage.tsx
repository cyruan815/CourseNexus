import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Paper,
  Progress,
  Skeleton,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import {
  IconArrowLeft,
  IconBook2,
  IconCheck,
  IconCircle,
  IconDownload,
  IconExternalLink,
  IconFileText,
  IconMessageCircle,
  IconPlayerPlay,
  IconRefresh,
  IconSend,
  IconX,
} from "@tabler/icons-react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { WorkbenchTopbar } from "../components/WorkbenchTopbar";
import {
  askStudySubtaskQuestion,
  exportGeneratedContentMarkdown,
  exportGeneratedContentPdf,
  fetchSubtaskExecutionContext,
  generateSubtaskHandout,
  generateSubtaskTaskTest,
  updateSubtaskCompletion,
} from "../features/study-plans/api";
import type {
  ExecutionContextRead,
  ExecutionMaterialRead,
  ExecutionSubtaskRead,
  ExecutionTaskRead,
  GeneratedContentRead,
  StudySubtaskQuestionAnswer,
  SubtaskCompletionResult,
  TaskContentType,
} from "../features/study-plans/types";
import "./study-plan.css";

interface ReadonlyTaskTestQuestion {
  id: string;
  question_text: string;
  question_type: string;
  options: Array<{ id: string; text: string }>;
  correct_answer: string | string[] | null;
  explanation: string | null;
  sort_order: number;
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function completionErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      NOT_FOUND: "任务不存在，或你没有访问权限。",
      STATE_CONFLICT: "任务状态已变化，请刷新后再试。",
      UNAUTHORIZED: "登录已过期，请重新登录。",
      VALIDATION_ERROR: "任务状态请求不合法。",
    };
    return messages[error.code] ?? error.message;
  }

  return errorMessage(error, "任务状态更新失败");
}

function generationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      GENERATION_FAILED: "内容生成失败，可以稍后重试。",
      GENERATION_SCHEMA_INVALID: "生成结果结构不符合要求，已记录失败，可重新生成。",
      MATERIAL_COVERAGE_INCOMPLETE: "资料覆盖不完整，暂时无法生成完整内容。",
      NO_PARSED_MATERIAL: "当前任务没有可用的已解析资料。",
      NOT_FOUND: "任务不存在，或你没有访问权限。",
      STATE_CONFLICT: "当前任务类型不支持这个生成入口。",
      UNAUTHORIZED: "登录已过期，请重新登录。",
      VALIDATION_ERROR: "生成参数不合法。",
    };
    return messages[error.code] ?? error.message;
  }

  return errorMessage(error, "内容生成失败");
}

function exportErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      EXPORT_CONTENT_INVALID: "导出内容结构异常，暂时不能生成文件。",
      EXPORT_CONTENT_NOT_READY: "内容还没有成功生成，暂时不能导出。",
      EXPORT_FAILED: "文件导出失败，请稍后重试。",
      EXPORT_UNSUPPORTED_CONTENT_TYPE: "当前内容类型不支持这个导出格式。",
      NOT_FOUND: "生成内容不存在，或你没有访问权限。",
      UNAUTHORIZED: "登录已过期，请重新登录。",
    };
    return messages[error.code] ?? error.message;
  }

  return errorMessage(error, "文件导出失败");
}

function qaErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      MATERIAL_COVERAGE_INCOMPLETE: "当前任务资料覆盖不足，暂时无法回答。",
      NO_PARSED_MATERIAL: "当前任务没有可用于问答的已解析资料。",
      NOT_FOUND: "任务不存在，或你没有访问权限。",
      STATE_CONFLICT: "任务资料状态已变化，请刷新后再试。",
      UNAUTHORIZED: "登录已过期，请重新登录。",
      VALIDATION_ERROR: "问题内容不合法，请换一种问法。",
    };
    return messages[error.code] ?? error.message;
  }

  return errorMessage(error, "AI 助教暂时无法回答");
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: "已启用",
    completed: "已完成",
    in_progress: "进行中",
    not_started: "未开始",
  };
  return labels[status] ?? status;
}

function statusColor(status: string): string {
  const colors: Record<string, string> = {
    active: "teal",
    completed: "teal",
    in_progress: "blue",
    not_started: "gray",
  };
  return colors[status] ?? "gray";
}

function subtaskTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    learn: "学习",
    quiz: "练习",
    review: "复习",
    test: "测试",
  };
  return labels[type] ?? type;
}

function taskContentType(type: string): TaskContentType | null {
  if (type === "learn" || type === "review") {
    return "handout";
  }
  if (type === "quiz" || type === "test") {
    return "task_test";
  }
  return null;
}

function taskContentLabel(contentType: TaskContentType): string {
  return contentType === "handout" ? "任务讲义" : "任务测试题";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function parseTaskTestQuestions(content: GeneratedContentRead | null): ReadonlyTaskTestQuestion[] {
  if (!content || content.content_type !== "task_test" || !isRecord(content.content_json)) {
    return [];
  }

  const questions = content.content_json.questions;
  if (!Array.isArray(questions)) {
    return [];
  }

  return questions
    .map((question, index): ReadonlyTaskTestQuestion | null => {
      if (!isRecord(question)) {
        return null;
      }

      const questionText = toText(question.question_text) ?? toText(question.prompt) ?? toText(question.stem);
      if (!questionText) {
        return null;
      }

      const rawOptions = Array.isArray(question.options) ? question.options : [];
      const options = rawOptions.flatMap((option, optionIndex) => {
        if (!isRecord(option)) {
          return [];
        }

        const id = toText(option.id) ?? toText(option.label) ?? String.fromCharCode(65 + optionIndex);
        const text = toText(option.text) ?? toText(option.content);
        return text ? [{ id, text }] : [];
      });

      const correctAnswer = question.correct_answer;
      const normalizedAnswer = typeof correctAnswer === "string" || Array.isArray(correctAnswer)
        ? correctAnswer
        : null;

      return {
        id: toText(question.id) ?? `q_${index + 1}`,
        question_text: questionText,
        question_type: toText(question.question_type) ?? "question",
        options,
        correct_answer: normalizedAnswer,
        explanation: toText(question.explanation) ?? toText(question.analysis),
        sort_order: typeof question.sort_order === "number" ? question.sort_order : index + 1,
      };
    })
    .filter((question): question is ReadonlyTaskTestQuestion => Boolean(question))
    .sort((left, right) => left.sort_order - right.sort_order);
}

function answerLabel(answer: string | string[] | null): string {
  if (!answer) {
    return "未提供";
  }

  return Array.isArray(answer) ? answer.join("、") : answer;
}

function materialAvailabilityLabel(material: ExecutionMaterialRead): string {
  if (material.availability === "available") {
    return material.parse_status === "parsed" ? "可用资料" : material.parse_status ?? "可用";
  }

  return "资料不可用";
}

function sortTasks(tasks: ExecutionTaskRead[]): ExecutionTaskRead[] {
  return [...tasks]
    .sort((left, right) => left.sort_order - right.sort_order)
    .map((task) => ({
      ...task,
      subtasks: [...task.subtasks].sort((left, right) => left.sort_order - right.sort_order),
    }));
}

function findCurrentSubtask(context: ExecutionContextRead | null): ExecutionSubtaskRead | null {
  if (!context) {
    return null;
  }

  for (const task of context.tasks) {
    const subtask = task.subtasks.find((item) => item.subtask_id === context.current_subtask_id);
    if (subtask) {
      return subtask;
    }
  }

  return null;
}

function applyCompletionResult(
  context: ExecutionContextRead,
  result: SubtaskCompletionResult,
): ExecutionContextRead {
  return {
    ...context,
    plan: {
      ...context.plan,
      status: result.plan.status,
    },
    tasks: context.tasks.map((task) => {
      if (task.task_id !== result.task.task_id) {
        return task;
      }

      return {
        ...task,
        status: result.task.status,
        subtasks: task.subtasks.map((subtask) => (
          subtask.subtask_id === result.subtask.subtask_id
            ? {
                ...subtask,
                status: result.subtask.status,
                completed_at: result.subtask.completed_at,
              }
            : subtask
        )),
      };
    }),
  };
}

function saveDownloadedFile(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export function StudyTaskExecutionPage() {
  const { subtaskId } = useParams();
  const [context, setContext] = useState<ExecutionContextRead | null>(null);
  const [completionResult, setCompletionResult] = useState<SubtaskCompletionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [qaError, setQaError] = useState<string | null>(null);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContentRead | null>(null);
  const [qaAnswer, setQaAnswer] = useState<StudySubtaskQuestionAnswer | null>(null);
  const [qaConversationId, setQaConversationId] = useState<string | null>(null);
  const [qaQuestion, setQaQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isAsking, setIsAsking] = useState(false);

  useEffect(() => {
    let ignore = false;

    if (!subtaskId) {
      setError("学习任务不存在");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    setCompletionError(null);
    setGenerationError(null);
    setExportError(null);
    setQaError(null);
    setCompletionResult(null);
    setGeneratedContent(null);
    setQaAnswer(null);
    setQaConversationId(null);
    setQaQuestion("");

    fetchSubtaskExecutionContext(subtaskId)
      .then((nextContext) => {
        if (!ignore) {
          setContext(nextContext);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(errorMessage(nextError, "执行上下文加载失败"));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [subtaskId]);

  const sortedTasks = useMemo(() => sortTasks(context?.tasks ?? []), [context?.tasks]);
  const currentSubtask = useMemo(() => findCurrentSubtask(context), [context]);
  const contentType = currentSubtask ? taskContentType(currentSubtask.subtask_type) : null;
  const contentLabel = contentType ? taskContentLabel(contentType) : null;
  const existingContentId = contentType === "handout" ? context?.handout_content_id : context?.task_test_content_id;
  const activeContentId = generatedContent?.id ?? existingContentId ?? null;
  const activeContentTitle = generatedContent?.title ?? null;
  const readonlyTaskTestQuestions = useMemo(() => parseTaskTestQuestions(generatedContent), [generatedContent]);
  const completedCount = sortedTasks.reduce(
    (total, task) => total + task.subtasks.filter((subtask) => subtask.status === "completed").length,
    0,
  );
  const totalCount = sortedTasks.reduce((total, task) => total + task.subtasks.length, 0);
  const progressValue = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const handleCompletion = async (completed: boolean) => {
    if (!subtaskId || !context) {
      return;
    }

    setIsUpdating(true);
    setCompletionError(null);

    try {
      const result = await updateSubtaskCompletion(subtaskId, completed);
      setCompletionResult(result);
      setContext((current) => (current ? applyCompletionResult(current, result) : current));
    } catch (nextError) {
      setCompletionError(completionErrorMessage(nextError));
    } finally {
      setIsUpdating(false);
    }
  };

  const handleGenerateContent = async (forceRegenerate: boolean) => {
    if (!subtaskId || !contentType) {
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);

    try {
      const content = contentType === "handout"
        ? await generateSubtaskHandout(subtaskId, { force_regenerate: forceRegenerate })
        : await generateSubtaskTaskTest(subtaskId, { force_regenerate: forceRegenerate });
      setGeneratedContent(content);
      setExportError(null);
    } catch (nextError) {
      setGenerationError(generationErrorMessage(nextError));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportContent = async () => {
    if (!activeContentId || !contentType) {
      return;
    }

    setIsExporting(true);
    setExportError(null);

    try {
      const file = contentType === "handout"
        ? await exportGeneratedContentPdf(activeContentId)
        : await exportGeneratedContentMarkdown(activeContentId);
      saveDownloadedFile(file.blob, file.filename);
    } catch (nextError) {
      setExportError(exportErrorMessage(nextError));
    } finally {
      setIsExporting(false);
    }
  };

  const handleAskQuestion = async (event: FormEvent) => {
    event.preventDefault();
    const question = qaQuestion.trim();

    if (!subtaskId || !question) {
      return;
    }

    setIsAsking(true);
    setQaError(null);

    try {
      const answer = await askStudySubtaskQuestion(subtaskId, {
        conversation_id: qaConversationId,
        question,
      });
      setQaAnswer(answer);
      setQaConversationId(answer.conversation_id);
      setQaQuestion("");
    } catch (nextError) {
      setQaError(qaErrorMessage(nextError));
    } finally {
      setIsAsking(false);
    }
  };

  if (isLoading) {
    return (
      <Box className="study-plan-page workbench-page">
        <WorkbenchTopbar pageName="任务执行" />
        <Box className="study-plan-shell" data-workbench-scroll="locked">
          <Skeleton height={36} width={280} />
          <Skeleton height={620} radius="md" />
        </Box>
      </Box>
    );
  }

  if (error || !context || !currentSubtask) {
    return (
      <Box className="study-plan-page workbench-page">
        <WorkbenchTopbar pageName="任务执行" />
        <Box className="study-plan-shell" data-workbench-scroll="locked">
          <Alert color="red" role="alert" title="执行页加载失败" variant="light">
            {error ?? "未找到当前二级任务"}
          </Alert>
        </Box>
      </Box>
    );
  }

  return (
    <Box className="study-plan-page workbench-page">
      <WorkbenchTopbar
        backFallbackTo={`/courses/${context.course.course_id}/study-plans/${context.plan.plan_id}`}
        contextName={currentSubtask.title}
        meta={(
          <>
            <Badge color="blue" variant="light">{context.execution_date}</Badge>
            <Badge color={statusColor(context.plan.status)} variant="light">
              {statusLabel(context.plan.status)}
            </Badge>
          </>
        )}
        pageName="任务执行"
      />
      <Box className="study-plan-execution-shell" component="main" data-workbench-scroll="locked">
        <Group className="study-plan-nav" hidden aria-hidden="true" justify="space-between" wrap="nowrap">
          <Button
            component={Link}
            leftSection={<IconArrowLeft size={16} />}
            to={`/courses/${context.course.course_id}/study-plans/${context.plan.plan_id}`}
            variant="subtle"
          >
            返回计划
          </Button>
          <Group gap="xs">
            <Badge color="blue" variant="light">{context.execution_date}</Badge>
            <Badge color={statusColor(context.plan.status)} variant="light">
              {statusLabel(context.plan.status)}
            </Badge>
          </Group>
        </Group>

        <Box className="study-plan-execution-grid">
          <Paper className="study-plan-execution-sidebar" radius="md" withBorder>
            <Stack gap="md">
              <Group align="flex-start" className="study-plan-execution-sidebar-header" justify="space-between" wrap="nowrap">
                <Stack gap={4}>
                  <Text c="dimmed" size="sm">{context.course.name}</Text>
                  <Title order={2}>今日学习任务</Title>
                </Stack>
                <Button
                  className="study-plan-plan-detail-link"
                  component={Link}
                  size="xs"
                  to={`/courses/${context.course.course_id}/study-plans/${context.plan.plan_id}`}
                  variant="subtle"
                >
                  查看计划详情
                </Button>
              </Group>
              <Stack gap={6}>
                <Group justify="space-between">
                  <Text size="sm">进度</Text>
                  <Text c="dimmed" size="sm">{completedCount}/{totalCount}</Text>
                </Group>
                <Progress value={progressValue} />
              </Stack>

              <Stack gap="sm">
                {sortedTasks.map((task) => (
                  <Stack className="study-plan-execution-taskrail" gap="xs" key={task.task_id}>
                    <Text fw={750} size="sm">{task.title}</Text>
                    {task.subtasks.map((subtask) => {
                      const isCurrent = subtask.subtask_id === context.current_subtask_id;
                      const isCompleted = subtask.status === "completed";
                      return (
                        <Paper
                          className={isCurrent ? "study-plan-execution-step is-current" : "study-plan-execution-step"}
                          key={subtask.subtask_id}
                          radius="md"
                          withBorder
                        >
                          <Group align="flex-start" gap="sm" wrap="nowrap">
                            {isCompleted ? (
                              <IconCheck className="study-plan-step-icon is-complete" size={18} />
                            ) : isCurrent ? (
                              <IconPlayerPlay className="study-plan-step-icon is-current" size={18} />
                            ) : (
                              <IconCircle className="study-plan-step-icon" size={18} />
                            )}
                            <Stack gap={2}>
                              <Text fw={isCurrent ? 750 : 650} size="sm">{subtask.title}</Text>
                              <Badge color={statusColor(subtask.status)} size="xs" variant="light">
                                {statusLabel(subtask.status)}
                              </Badge>
                            </Stack>
                          </Group>
                        </Paper>
                      );
                    })}
                  </Stack>
                ))}
              </Stack>
            </Stack>
          </Paper>

          <Paper className="study-plan-execution-main has-pinned-completion" radius="md" withBorder>
            <Stack className="study-plan-execution-main-stack" gap="lg">
              <Stack gap={8}>
                <Group gap="xs">
                  <Badge color="violet" variant="light">{subtaskTypeLabel(currentSubtask.subtask_type)}</Badge>
                  <Badge color={statusColor(currentSubtask.status)} variant="light">
                    {statusLabel(currentSubtask.status)}
                  </Badge>
                </Group>
                <Title order={1}>{currentSubtask.title}</Title>
                {currentSubtask.description ? (
                  <Text className="study-plan-goal">{currentSubtask.description}</Text>
                ) : (
                  <Text c="dimmed">这个任务没有额外说明。</Text>
                )}
              </Stack>

              {completionError ? (
                <Alert color="red" role="alert" title="状态更新失败" variant="light">
                  {completionError}
                </Alert>
              ) : null}

              <Paper className="study-plan-execution-content" radius="md" withBorder>
                <Stack gap="sm">
                  <Group gap="xs">
                    <IconFileText size={18} />
                    <Text fw={750}>{contentLabel ?? "任务内容"}</Text>
                  </Group>
                  {contentType ? (
                    <>
                      <Text c="dimmed" size="sm">
                        {contentType === "handout"
                          ? "为当前学习 / 复习任务按需生成讲义。默认复用最近一次成功内容。"
                          : "为当前练习 / 测试任务按需生成测试题。默认复用最近一次成功内容。"}
                      </Text>
                      {generationError ? (
                        <Alert color="red" role="alert" title="内容生成失败" variant="light">
                          {generationError}
                        </Alert>
                      ) : null}
                      {exportError ? (
                        <Alert color="red" role="alert" title="文件导出失败" variant="light">
                          {exportError}
                        </Alert>
                      ) : null}
                      {activeContentId ? (
                        <>
                          <Paper className="study-plan-generated-content" radius="md" withBorder>
                            <Group align="center" justify="space-between" wrap="nowrap">
                              <Stack gap={2}>
                                <Badge color="teal" variant="light">已生成</Badge>
                                <Text fw={750}>{activeContentTitle ?? `${contentLabel}已可查看`}</Text>
                              </Stack>
                              <Group gap="xs" wrap="nowrap">
                                <Button
                                  component={Link}
                                  leftSection={<IconExternalLink size={15} />}
                                  size="xs"
                                  to={`/generated-contents/${activeContentId}`}
                                  variant="light"
                                >
                                  查看{contentLabel}
                                </Button>
                                <Button
                                  leftSection={<IconDownload size={15} />}
                                  loading={isExporting}
                                  onClick={() => void handleExportContent()}
                                  size="xs"
                                  variant="light"
                                >
                                  {contentType === "handout" ? "导出PDF" : "导出Markdown"}
                                </Button>
                                <Button
                                  leftSection={<IconRefresh size={15} />}
                                  loading={isGenerating}
                                  onClick={() => void handleGenerateContent(true)}
                                  size="xs"
                                  variant="subtle"
                                >
                                  重新生成
                                </Button>
                              </Group>
                            </Group>
                          </Paper>
                          {contentType === "task_test" && readonlyTaskTestQuestions.length > 0 ? (
                            <Stack className="study-plan-task-test-preview" gap="sm">
                              <Group gap="xs">
                                <Badge color="blue" variant="light">只读预览</Badge>
                                <Text c="dimmed" size="sm">当前只展示题目、答案和解析，不保存作答。</Text>
                              </Group>
                              {readonlyTaskTestQuestions.map((question, index) => (
                                <Paper className="study-plan-task-test-question" key={question.id} radius="md" withBorder>
                                  <Stack gap="xs">
                                    <Group gap="xs">
                                      <Badge variant="light">第 {index + 1} 题</Badge>
                                      <Badge color="gray" variant="light">{question.question_type}</Badge>
                                    </Group>
                                    <Text fw={750}>{question.question_text}</Text>
                                    {question.options.length > 0 ? (
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
                          ) : null}
                        </>
                      ) : (
                        <Group justify="space-between" wrap="nowrap">
                          <Badge color="gray" variant="light">{contentLabel}待生成</Badge>
                          <Button
                            leftSection={<IconBook2 size={16} />}
                            loading={isGenerating}
                            onClick={() => void handleGenerateContent(false)}
                            variant="light"
                          >
                            生成{contentLabel}
                          </Button>
                        </Group>
                      )}
                    </>
                  ) : (
                    <Alert color="yellow" variant="light">
                      该任务类型暂不支持生成内容。
                    </Alert>
                  )}
                </Stack>
              </Paper>

              <Group className="study-plan-completion-actions is-pinned-bottom" justify="flex-end">
                {currentSubtask.status === "completed" ? (
                  <Button
                    color="gray"
                    leftSection={<IconX size={16} />}
                    loading={isUpdating}
                    onClick={() => void handleCompletion(false)}
                    variant="light"
                  >
                    取消完成
                  </Button>
                ) : (
                  <Button
                    leftSection={<IconCheck size={16} />}
                    loading={isUpdating}
                    onClick={() => void handleCompletion(true)}
                  >
                    完成任务
                  </Button>
                )}
              </Group>
            </Stack>
          </Paper>

          <Paper className="study-plan-execution-aside" radius="md" withBorder>
            <Stack gap="md">
              <Stack gap={4}>
                <Title order={2}>AI 助教</Title>
                <Text c="dimmed" size="sm">
                  只围绕当前任务的关联资料回答，资料范围由后端按任务锁定。
                </Text>
              </Stack>

              <Paper className="study-plan-task-qa" radius="md" withBorder>
                <Stack component="form" gap="sm" onSubmit={(event) => void handleAskQuestion(event)}>
                  {qaAnswer ? (
                    <Paper className="study-plan-task-qa-answer" radius="md">
                      <Stack gap={6}>
                        <Group gap="xs">
                          <IconMessageCircle size={16} />
                          <Text fw={750} size="sm">助教回答</Text>
                          <Badge color={qaAnswer.answer_type === "no_source" ? "gray" : "teal"} size="xs" variant="light">
                            {qaAnswer.answer_type === "no_source" ? "无引用" : "已引用资料"}
                          </Badge>
                        </Group>
                        <Text size="sm">{qaAnswer.answer_text}</Text>
                        {qaAnswer.source_citations.length > 0 ? (
                          <Stack gap={4}>
                            {qaAnswer.source_citations.slice(0, 2).map((citation, index) => (
                              <Text c="dimmed" key={citation.id ?? `${citation.material_id}-${index}`} size="xs">
                                {citation.material_name}
                                {citation.page ? ` · p.${citation.page}` : ""}
                              </Text>
                            ))}
                          </Stack>
                        ) : null}
                      </Stack>
                    </Paper>
                  ) : (
                    <Text c="dimmed" size="sm">
                      可以问“这一步先看哪份资料？”或“这个概念怎么理解？”。
                    </Text>
                  )}

                  {qaError ? (
                    <Alert color="red" role="alert" title="提问失败" variant="light">
                      {qaError}
                    </Alert>
                  ) : null}

                  <Textarea
                    aria-label="向 AI 助教提问"
                    minRows={3}
                    onChange={(event) => setQaQuestion(event.currentTarget.value)}
                    placeholder="围绕当前任务提问"
                    value={qaQuestion}
                  />
                  <Button
                    disabled={!qaQuestion.trim()}
                    leftSection={<IconSend size={15} />}
                    loading={isAsking}
                    type="submit"
                    variant="light"
                  >
                    提问
                  </Button>
                </Stack>
              </Paper>

              <Stack gap={4}>
                <Title order={2}>任务摘要</Title>
                <Text c="dimmed" size="sm">
                  完成状态和资料范围都以当前二级任务为准。
                </Text>
              </Stack>

              <Paper className="study-plan-checkin-card" radius="md" withBorder>
                <Stack gap={4}>
                  <Text fw={750}>打卡进度：{completionResult?.checkin.completed_subtask_count ?? completedCount}/{completionResult?.checkin.planned_subtask_count ?? totalCount}</Text>
                  <Text c="dimmed" size="sm">
                    完成状态会由后端同步汇总一级任务、计划和当日打卡。
                  </Text>
                </Stack>
              </Paper>

              <Stack gap="xs">
                {context.related_materials.length > 0 ? (
                  context.related_materials.map((material) => (
                    <Paper className="study-plan-material-row" key={material.material_id} radius="md" withBorder>
                      <Stack gap={4}>
                        <Group justify="space-between" wrap="nowrap">
                          <Text fw={700}>{material.name ?? material.material_id}</Text>
                          <Badge
                            color={material.availability === "available" ? "teal" : "gray"}
                            size="sm"
                            variant="light"
                          >
                            {materialAvailabilityLabel(material)}
                          </Badge>
                        </Group>
                        <Text c="dimmed" size="xs">
                          {material.material_type ?? "未知类型"} · {material.material_id}
                        </Text>
                      </Stack>
                    </Paper>
                  ))
                ) : (
                  <Alert color="yellow" variant="light">
                    当前任务没有返回关联资料。
                  </Alert>
                )}
              </Stack>
            </Stack>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}
