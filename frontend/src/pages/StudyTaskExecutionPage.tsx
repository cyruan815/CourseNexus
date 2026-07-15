import { useEffect, useMemo, useRef, useState } from "react";
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
  IconFileText,
  IconMessageCircle,
  IconPlayerPlay,
  IconRefresh,
  IconSend,
  IconX,
} from "@tabler/icons-react";
import { Link, useParams } from "react-router-dom";
import rehypeKatex from "rehype-katex";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

import { ApiError } from "../api/errors";
import { WorkbenchTopbar } from "../components/WorkbenchTopbar";
import { InlineCitationAnswer } from "../features/course-qa/InlineCitationAnswer";
import {
  askStudySubtaskQuestion,
  exportGeneratedContentMarkdown,
  exportGeneratedContentPdf,
  fetchSubtaskExecutionContext,
  generateSubtaskHandout,
  generateSubtaskTaskTest,
  getGeneratedContentDetail,
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

interface ContentSourceSummary {
  key: string;
  text: string;
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

function formatGeneratedContentSource(citation: unknown, index: number): ContentSourceSummary | null {
  if (!isRecord(citation)) {
    return null;
  }

  const materialName = toText(citation.material_name);
  if (!materialName) {
    return null;
  }

  const page = toText(citation.page);
  const pageIndex = typeof citation.page_index === "number" ? citation.page_index : null;
  const pageLabel = page
    ? `第 ${page} 页`
    : pageIndex !== null && pageIndex >= 0
      ? `第 ${pageIndex + 1} 页`
      : null;
  const key = toText(citation.id) ?? `${toText(citation.material_id) ?? "source"}-${index}`;

  return {
    key,
    text: pageLabel ? `${materialName} · ${pageLabel}` : materialName,
  };
}

function generatedContentSourceSummary(content: GeneratedContentRead | null): {
  sources: ContentSourceSummary[];
  total: number;
} {
  if (!content) {
    return { sources: [], total: 0 };
  }

  const allSources = content.source_citations
    .map((citation, index) => formatGeneratedContentSource(citation, index))
    .filter((source): source is ContentSourceSummary => Boolean(source));

  return {
    sources: allSources.slice(0, 2),
    total: allSources.length,
  };
}

function handoutMarkdown(content: GeneratedContentRead | null): string | null {
  if (!content || content.content_type !== "handout") {
    return null;
  }

  const markdown = content.content?.trim();
  return markdown ? markdown : null;
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
  const [selectedSubtaskId, setSelectedSubtaskId] = useState<string | null>(subtaskId ?? null);
  const selectedSubtaskIdRef = useRef<string | null>(subtaskId ?? null);
  const [context, setContext] = useState<ExecutionContextRead | null>(null);
  const [completionResult, setCompletionResult] = useState<SubtaskCompletionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [qaError, setQaError] = useState<string | null>(null);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContentRead | null>(null);
  const [generatedContentBySubtask, setGeneratedContentBySubtask] = useState<Record<string, GeneratedContentRead>>({});
  const [qaAnswer, setQaAnswer] = useState<StudySubtaskQuestionAnswer | null>(null);
  const [qaConversationId, setQaConversationId] = useState<string | null>(null);
  const [qaQuestion, setQaQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSwitchingSubtask, setIsSwitchingSubtask] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [generatingSubtaskId, setGeneratingSubtaskId] = useState<string | null>(null);
  const [isContentLoading, setIsContentLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [generationNotice, setGenerationNotice] = useState<string | null>(null);

  useEffect(() => {
    setSelectedSubtaskId(subtaskId ?? null);
  }, [subtaskId]);

  useEffect(() => {
    selectedSubtaskIdRef.current = selectedSubtaskId;
  }, [selectedSubtaskId]);

  useEffect(() => {
    if (!generationNotice) {
      return undefined;
    }

    const noticeTimer = window.setTimeout(() => {
      setGenerationNotice(null);
    }, 3200);

    return () => {
      window.clearTimeout(noticeTimer);
    };
  }, [generationNotice]);

  useEffect(() => {
    let ignore = false;

    if (!selectedSubtaskId) {
      setError("学习任务不存在");
      setIsLoading(false);
      setIsSwitchingSubtask(false);
      return;
    }

    const shouldShowPageSkeleton = context === null;
    if (shouldShowPageSkeleton) {
      setIsLoading(true);
    } else {
      setIsSwitchingSubtask(true);
    }
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

    fetchSubtaskExecutionContext(selectedSubtaskId)
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
          if (shouldShowPageSkeleton) {
            setIsLoading(false);
          }
          setIsSwitchingSubtask(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [selectedSubtaskId]);

  const sortedTasks = useMemo(() => sortTasks(context?.tasks ?? []), [context?.tasks]);
  const currentSubtask = useMemo(() => findCurrentSubtask(context), [context]);
  const contentType = currentSubtask ? taskContentType(currentSubtask.subtask_type) : null;
  const contentLabel = contentType ? taskContentLabel(contentType) : null;
  const existingContentId = contentType === "handout" ? context?.handout_content_id : context?.task_test_content_id;
  const currentGeneratedContent = currentSubtask
    ? generatedContentBySubtask[currentSubtask.subtask_id]
      ?? (generatedContent?.study_subtask_id === currentSubtask.subtask_id ? generatedContent : null)
    : null;
  const activeContentId = generationError ? null : currentGeneratedContent?.id ?? existingContentId ?? null;
  const activeContentTitle = currentGeneratedContent?.title ?? null;
  const isGeneratingCurrentSubtask = Boolean(currentSubtask && generatingSubtaskId === currentSubtask.subtask_id);
  const isGeneratingOtherSubtask = Boolean(currentSubtask && generatingSubtaskId && generatingSubtaskId !== currentSubtask.subtask_id);
  const readonlyTaskTestQuestions = useMemo(() => parseTaskTestQuestions(currentGeneratedContent), [currentGeneratedContent]);
  const readonlyHandoutMarkdown = useMemo(() => handoutMarkdown(currentGeneratedContent), [currentGeneratedContent]);
  const contentSourceSummary = useMemo(
    () => generatedContentSourceSummary(currentGeneratedContent),
    [currentGeneratedContent],
  );
  const completedCount = sortedTasks.reduce(
    (total, task) => total + task.subtasks.filter((subtask) => subtask.status === "completed").length,
    0,
  );
  const totalCount = sortedTasks.reduce((total, task) => total + task.subtasks.length, 0);
  const progressValue = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  useEffect(() => {
    let ignore = false;

    if (!existingContentId || generationError) {
      setIsContentLoading(false);
      if (generatedContent && generatedContent.study_subtask_id !== currentSubtask?.subtask_id) {
        setGeneratedContent(null);
      }
      return;
    }

    if (currentGeneratedContent?.id === existingContentId) {
      setIsContentLoading(false);
      return;
    }

    setIsContentLoading(true);
    getGeneratedContentDetail(existingContentId)
      .then((content) => {
        if (!ignore) {
          setGeneratedContent(content);
          if (content.study_subtask_id) {
            setGeneratedContentBySubtask((current) => ({
              ...current,
              [content.study_subtask_id as string]: content,
            }));
          }
          setGenerationError(null);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setGenerationError(generationErrorMessage(nextError));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsContentLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [
    currentGeneratedContent?.id,
    currentSubtask?.subtask_id,
    existingContentId,
    generationError,
    generatedContent,
    generatedContentBySubtask,
  ]);

  const handleCompletion = async (completed: boolean) => {
    const activeSubtaskId = currentSubtask?.subtask_id;
    if (!activeSubtaskId || !context) {
      return;
    }

    setIsUpdating(true);
    setCompletionError(null);

    try {
      const result = await updateSubtaskCompletion(activeSubtaskId, completed);
      setCompletionResult(result);
      setContext((current) => (current ? applyCompletionResult(current, result) : current));
    } catch (nextError) {
      setCompletionError(completionErrorMessage(nextError));
    } finally {
      setIsUpdating(false);
    }
  };

  const handleGenerateContent = async (forceRegenerate: boolean) => {
    const targetSubtaskId = currentSubtask?.subtask_id;
    const targetContentType = contentType;
    if (!targetSubtaskId || !targetContentType) {
      return;
    }

    if (generatingSubtaskId && generatingSubtaskId !== targetSubtaskId) {
      setGenerationNotice("另一个任务的内容仍在后台生成中，完成前暂不能同时发起新的生成。");
      return;
    }

    setGeneratingSubtaskId(targetSubtaskId);
    setGenerationNotice(null);
    setGenerationError(null);

    try {
      const content = targetContentType === "handout"
        ? await generateSubtaskHandout(targetSubtaskId, { force_regenerate: forceRegenerate })
        : await generateSubtaskTaskTest(targetSubtaskId, { force_regenerate: forceRegenerate });
      setGeneratedContentBySubtask((current) => ({
        ...current,
        [targetSubtaskId]: content,
      }));
      if (selectedSubtaskIdRef.current === targetSubtaskId) {
        setGeneratedContent(content);
      } else {
        setGenerationNotice(null);
      }
      setExportError(null);
    } catch (nextError) {
      const message = generationErrorMessage(nextError);
      if (selectedSubtaskIdRef.current === targetSubtaskId) {
        setGenerationError(message);
      } else {
        setGenerationNotice(`刚才那个任务的内容生成失败：${message}`);
      }
    } finally {
      setGeneratingSubtaskId((current) => (current === targetSubtaskId ? null : current));
      setGenerationNotice((current) => (
        current && (current.includes("已切换任务") || current.includes("后台生成"))
          ? null
          : current
      ));
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
    const activeSubtaskId = currentSubtask?.subtask_id;

    if (!activeSubtaskId || !question) {
      return;
    }

    setIsAsking(true);
    setQaError(null);

    try {
      const answer = await askStudySubtaskQuestion(activeSubtaskId, {
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

  function handleSelectSubtask(nextSubtaskId: string) {
    if (nextSubtaskId === selectedSubtaskId || isSwitchingSubtask) {
      return;
    }

    if (generatingSubtaskId && generatingSubtaskId !== nextSubtaskId) {
      setGenerationNotice("已切换任务；原任务内容仍在后台生成，不会影响当前页面。");
    }

    setSelectedSubtaskId(nextSubtaskId);
  }

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
                      const isCurrent = subtask.subtask_id === selectedSubtaskId;
                      const isCompleted = subtask.status === "completed";
                      return (
                        <Paper
                          aria-current={isCurrent ? "step" : undefined}
                          aria-label={`切换到任务 ${subtask.title}`}
                          className={isCurrent ? "study-plan-execution-step is-current" : "study-plan-execution-step"}
                          component="button"
                          disabled={isSwitchingSubtask}
                          key={subtask.subtask_id}
                          onClick={() => handleSelectSubtask(subtask.subtask_id)}
                          radius="md"
                          type="button"
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

          <Paper
            aria-busy={isSwitchingSubtask || undefined}
            className="study-plan-execution-main has-pinned-completion"
            radius="md"
            withBorder
          >
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
                      {generationNotice ? (
                        <Alert color="blue" role="status" title="生成状态" variant="light">
                          {generationNotice}
                        </Alert>
                      ) : null}
                      {isGeneratingOtherSubtask ? (
                        <Alert color="yellow" role="status" title="后台生成中" variant="light">
                          另一个任务的内容仍在后台生成中，当前页面可以继续查看；完成前暂不能同时发起新的生成。
                        </Alert>
                      ) : null}
                      {exportError ? (
                        <Alert color="red" role="alert" title="文件导出失败" variant="light">
                          {exportError}
                        </Alert>
                      ) : null}
                      {isContentLoading ? (
                        <Stack gap="sm" role="status">
                          <Text c="dimmed" size="sm">正在加载已生成内容...</Text>
                          <Skeleton height={72} radius="md" />
                        </Stack>
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
                                  disabled={isGeneratingOtherSubtask}
                                  loading={isGeneratingCurrentSubtask}
                                  onClick={() => void handleGenerateContent(true)}
                                  size="xs"
                                  variant="subtle"
                                >
                                  重新生成
                                </Button>
                              </Group>
                            </Group>
                            {contentSourceSummary.sources.length > 0 ? (
                              <Text c="dimmed" className="study-plan-generated-sources" size="xs">
                                来源：{contentSourceSummary.sources.map((source) => source.text).join("、")}
                                {contentSourceSummary.total > contentSourceSummary.sources.length
                                  ? `，等 ${contentSourceSummary.total} 处来源`
                                  : ""}
                              </Text>
                            ) : null}
                          </Paper>
                          {contentType === "handout" && readonlyHandoutMarkdown ? (
                            <Paper className="study-plan-handout-preview" radius="md" withBorder>
                              <ReactMarkdown
                                rehypePlugins={[rehypeKatex]}
                                remarkPlugins={[remarkGfm, remarkMath]}
                              >
                                {readonlyHandoutMarkdown}
                              </ReactMarkdown>
                            </Paper>
                          ) : null}
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
                            disabled={isGeneratingOtherSubtask}
                            leftSection={<IconBook2 size={16} />}
                            loading={isGeneratingCurrentSubtask}
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
                    disabled={isSwitchingSubtask}
                    leftSection={<IconX size={16} />}
                    loading={isUpdating}
                    onClick={() => void handleCompletion(false)}
                    variant="light"
                  >
                    取消完成
                  </Button>
                ) : (
                  <Button
                    disabled={isSwitchingSubtask}
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
            <Stack className="study-plan-execution-aside-layout" gap="md">
              <Stack className="study-plan-execution-ai" gap="md">
                <Stack gap={4}>
                  <Title order={2}>AI 助教</Title>
                  <Text c="dimmed" size="sm">
                    只围绕当前任务的关联资料回答，资料范围由后端按任务锁定。
                  </Text>
                </Stack>

                <Paper className="study-plan-task-qa" radius="md" withBorder>
                  <Stack className="study-plan-task-qa-form" component="form" gap="sm" onSubmit={(event) => void handleAskQuestion(event)}>
                    <Stack className="study-plan-task-qa-response" gap="sm">
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
                            <InlineCitationAnswer citations={qaAnswer.source_citations} content={qaAnswer.answer_text} />
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
                    </Stack>

                    <Stack className="study-plan-task-qa-composer" gap="sm">
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
                  </Stack>
                </Paper>
              </Stack>

              <Stack className="study-plan-execution-summary" gap="sm">
                <Group className="study-plan-summary-header" justify="space-between" wrap="nowrap">
                  <Title order={3}>任务摘要</Title>
                  <Badge color="blue" variant="light">{context.related_materials.length} 份资料</Badge>
                </Group>

                <Paper className="study-plan-checkin-card" radius="md" withBorder>
                  <Group justify="space-between" wrap="nowrap">
                    <Text c="dimmed" size="sm">打卡进度</Text>
                    <Text fw={750}>{completionResult?.checkin.completed_subtask_count ?? completedCount}/{completionResult?.checkin.planned_subtask_count ?? totalCount}</Text>
                  </Group>
                </Paper>

                <Stack className="study-plan-material-summary-list" gap={6}>
                  {context.related_materials.length > 0 ? (
                    context.related_materials.map((material) => (
                      <Paper className="study-plan-material-row" key={material.material_id} radius="md" withBorder>
                        <Stack gap={4}>
                          <Group justify="space-between" wrap="nowrap">
                            <Text className="study-plan-material-name" fw={700} lineClamp={1}>
                              {material.name ?? material.material_id}
                            </Text>
                            <Badge
                              color={material.availability === "available" ? "teal" : "gray"}
                              className="study-plan-material-badge"
                              size="xs"
                              variant="light"
                            >
                              {materialAvailabilityLabel(material)}
                            </Badge>
                          </Group>
                          <Text c="dimmed" className="study-plan-material-meta" size="xs">
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
            </Stack>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}
