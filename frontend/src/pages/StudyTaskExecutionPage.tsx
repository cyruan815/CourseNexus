import { useEffect, useMemo, useRef, useState } from "react";
import type {
  CSSProperties,
  FormEvent,
  KeyboardEvent as ReactKeyboardEvent,
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
} from "react";
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

import { ApiError } from "../api/errors";
import { WorkbenchTopbar } from "../components/WorkbenchTopbar";
import { InlineCitationAnswer } from "../features/course-qa/InlineCitationAnswer";
import { HandoutMarkdownRenderer } from "../features/generated-content/renderers/handout/HandoutMarkdownRenderer";
import { taskTestQuestions } from "../features/generated-content/guards";
import { TaskTestResult } from "../features/generated-content/renderers/TaskTestResult";
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
import "../features/generated-content/generated-content.css";
import "./study-plan.css";

interface ExecutionColumnWidths {
  left: number;
  main: number;
  right: number;
}

type ExecutionResizeHandle = "left" | "right";

interface ExecutionResizeDrag {
  handle: ExecutionResizeHandle;
  startX: number;
  startWidths: ExecutionColumnWidths;
}

type GenerationState = {
  status: "generating" | "error";
  error?: string;
};

const EXECUTION_COLUMN_STORAGE_KEY = "course-nexus:study-plan-execution-columns";
const EXECUTION_COLUMN_MIN_WIDTHS: ExecutionColumnWidths = {
  left: 230,
  main: 440,
  right: 280,
};
const EXECUTION_COLUMN_DEFAULT_RATIOS: ExecutionColumnWidths = {
  left: 0.72,
  main: 1.45,
  right: 0.85,
};
const EXECUTION_COLUMN_FALLBACK_GRID_WIDTH = 1280;
const EXECUTION_RESIZE_GUTTER_WIDTH = 10;
const EXECUTION_RESIZE_KEYBOARD_STEP = 32;

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

function displayStatusForGeneratedContent(status: string, hasGeneratedContent: boolean): string {
  return status === "not_started" && hasGeneratedContent ? "in_progress" : status;
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

function clampNumber(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function normalizeExecutionColumnWidths(widths: ExecutionColumnWidths): ExecutionColumnWidths {
  return {
    left: Math.round(widths.left),
    main: Math.round(widths.main),
    right: Math.round(widths.right),
  };
}

function sameExecutionColumnWidths(
  left: ExecutionColumnWidths | null,
  right: ExecutionColumnWidths,
): boolean {
  return Boolean(
    left
    && left.left === right.left
    && left.main === right.main
    && left.right === right.right,
  );
}

function fitExecutionColumnWidths(
  widths: ExecutionColumnWidths,
  gridWidth: number,
): ExecutionColumnWidths {
  const minimumTotal = (
    EXECUTION_COLUMN_MIN_WIDTHS.left
    + EXECUTION_COLUMN_MIN_WIDTHS.main
    + EXECUTION_COLUMN_MIN_WIDTHS.right
  );
  const availableWidth = Math.round(gridWidth - EXECUTION_RESIZE_GUTTER_WIDTH * 2);
  const normalizedWidths = normalizeExecutionColumnWidths({
    left: Math.max(widths.left, EXECUTION_COLUMN_MIN_WIDTHS.left),
    main: Math.max(widths.main, EXECUTION_COLUMN_MIN_WIDTHS.main),
    right: Math.max(widths.right, EXECUTION_COLUMN_MIN_WIDTHS.right),
  });
  const currentTotal = normalizedWidths.left + normalizedWidths.main + normalizedWidths.right;

  if (!Number.isFinite(availableWidth) || availableWidth < minimumTotal || currentTotal <= availableWidth) {
    return normalizedWidths;
  }

  const targetFlexibleWidth = availableWidth - minimumTotal;
  const currentFlexibleWidths = {
    left: normalizedWidths.left - EXECUTION_COLUMN_MIN_WIDTHS.left,
    main: normalizedWidths.main - EXECUTION_COLUMN_MIN_WIDTHS.main,
    right: normalizedWidths.right - EXECUTION_COLUMN_MIN_WIDTHS.right,
  };
  const currentFlexibleTotal = (
    currentFlexibleWidths.left
    + currentFlexibleWidths.main
    + currentFlexibleWidths.right
  );
  if (currentFlexibleTotal <= 0) {
    return EXECUTION_COLUMN_MIN_WIDTHS;
  }

  const left = EXECUTION_COLUMN_MIN_WIDTHS.left + Math.round(
    targetFlexibleWidth * (currentFlexibleWidths.left / currentFlexibleTotal),
  );
  const right = EXECUTION_COLUMN_MIN_WIDTHS.right + Math.round(
    targetFlexibleWidth * (currentFlexibleWidths.right / currentFlexibleTotal),
  );

  return normalizeExecutionColumnWidths({
    left,
    main: availableWidth - left - right,
    right,
  });
}

function isExecutionColumnWidths(value: unknown): value is ExecutionColumnWidths {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.left === "number"
    && typeof candidate.main === "number"
    && typeof candidate.right === "number"
    && candidate.left >= EXECUTION_COLUMN_MIN_WIDTHS.left
    && candidate.main >= EXECUTION_COLUMN_MIN_WIDTHS.main
    && candidate.right >= EXECUTION_COLUMN_MIN_WIDTHS.right
  );
}

function readStoredExecutionColumnWidths(): ExecutionColumnWidths | null {
  try {
    const stored = window.localStorage.getItem(EXECUTION_COLUMN_STORAGE_KEY);
    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored) as unknown;
    return isExecutionColumnWidths(parsed) ? normalizeExecutionColumnWidths(parsed) : null;
  } catch {
    return null;
  }
}

function persistExecutionColumnWidths(widths: ExecutionColumnWidths): void {
  try {
    window.localStorage.setItem(EXECUTION_COLUMN_STORAGE_KEY, JSON.stringify(normalizeExecutionColumnWidths(widths)));
  } catch {
    // Column resizing is a local preference; storage failures should not block the study task.
  }
}

function defaultExecutionColumnWidths(gridWidth: number): ExecutionColumnWidths {
  const availableWidth = Math.max(
    gridWidth - EXECUTION_RESIZE_GUTTER_WIDTH * 2,
    EXECUTION_COLUMN_MIN_WIDTHS.left + EXECUTION_COLUMN_MIN_WIDTHS.main + EXECUTION_COLUMN_MIN_WIDTHS.right,
  );
  const ratioTotal = (
    EXECUTION_COLUMN_DEFAULT_RATIOS.left
    + EXECUTION_COLUMN_DEFAULT_RATIOS.main
    + EXECUTION_COLUMN_DEFAULT_RATIOS.right
  );
  const left = Math.round(availableWidth * (EXECUTION_COLUMN_DEFAULT_RATIOS.left / ratioTotal));
  const right = Math.round(availableWidth * (EXECUTION_COLUMN_DEFAULT_RATIOS.right / ratioTotal));

  return fitExecutionColumnWidths({
    left,
    main: availableWidth - left - right,
    right,
  }, gridWidth);
}

function resizeExecutionColumns(
  widths: ExecutionColumnWidths,
  handle: ExecutionResizeHandle,
  deltaX: number,
): ExecutionColumnWidths {
  if (handle === "left") {
    const pairTotal = widths.left + widths.main;
    const left = clampNumber(
      widths.left + deltaX,
      EXECUTION_COLUMN_MIN_WIDTHS.left,
      pairTotal - EXECUTION_COLUMN_MIN_WIDTHS.main,
    );

    return normalizeExecutionColumnWidths({
      left,
      main: pairTotal - left,
      right: widths.right,
    });
  }

  const pairTotal = widths.main + widths.right;
  const main = clampNumber(
    widths.main + deltaX,
    EXECUTION_COLUMN_MIN_WIDTHS.main,
    pairTotal - EXECUTION_COLUMN_MIN_WIDTHS.right,
  );

  return normalizeExecutionColumnWidths({
    left: widths.left,
    main,
    right: pairTotal - main,
  });
}

export function StudyTaskExecutionPage() {
  const { subtaskId } = useParams();
  const [selectedSubtaskId, setSelectedSubtaskId] = useState<string | null>(subtaskId ?? null);
  const selectedSubtaskIdRef = useRef<string | null>(subtaskId ?? null);
  const [context, setContext] = useState<ExecutionContextRead | null>(null);
  const [completionResult, setCompletionResult] = useState<SubtaskCompletionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [generationStateBySubtask, setGenerationStateBySubtask] = useState<Record<string, GenerationState>>({});
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
  const generatingSubtaskIdsRef = useRef<Set<string>>(new Set());
  const contentEpochBySubtaskRef = useRef<Record<string, number>>({});
  const [isContentLoading, setIsContentLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [generationNotice, setGenerationNotice] = useState<string | null>(null);
  const [executionColumnWidths, setExecutionColumnWidths] = useState<ExecutionColumnWidths | null>(() => (
    readStoredExecutionColumnWidths()
  ));
  const executionGridRef = useRef<HTMLDivElement | null>(null);
  const executionResizeDragRef = useRef<ExecutionResizeDrag | null>(null);

  const bumpContentEpoch = (targetSubtaskId: string): number => {
    const nextEpoch = (contentEpochBySubtaskRef.current[targetSubtaskId] ?? 0) + 1;
    contentEpochBySubtaskRef.current[targetSubtaskId] = nextEpoch;
    return nextEpoch;
  };

  const resolveExecutionColumnWidths = (): ExecutionColumnWidths => {
    if (executionColumnWidths) {
      return executionColumnWidths;
    }

    const gridWidth = executionGridRef.current?.getBoundingClientRect().width ?? 0;
    return defaultExecutionColumnWidths(gridWidth > 0 ? gridWidth : EXECUTION_COLUMN_FALLBACK_GRID_WIDTH);
  };

  const applyExecutionColumnWidths = (nextWidths: ExecutionColumnWidths): void => {
    const normalizedWidths = normalizeExecutionColumnWidths(nextWidths);
    setExecutionColumnWidths(normalizedWidths);
    persistExecutionColumnWidths(normalizedWidths);
  };

  const fitExecutionColumnsToGrid = (): void => {
    const gridWidth = executionGridRef.current?.getBoundingClientRect().width ?? 0;
    if (gridWidth <= 0) {
      return;
    }

    setExecutionColumnWidths((currentWidths) => {
      const fittedWidths = fitExecutionColumnWidths(
        currentWidths ?? defaultExecutionColumnWidths(gridWidth),
        gridWidth,
      );
      if (sameExecutionColumnWidths(currentWidths, fittedWidths)) {
        return currentWidths;
      }

      persistExecutionColumnWidths(fittedWidths);
      return fittedWidths;
    });
  };

  const updateExecutionColumnResize = (clientX: number): void => {
    const drag = executionResizeDragRef.current;
    if (!drag || !Number.isFinite(clientX)) {
      return;
    }

    applyExecutionColumnWidths(resizeExecutionColumns(drag.startWidths, drag.handle, clientX - drag.startX));
  };

  const stopExecutionColumnResize = (): void => {
    executionResizeDragRef.current = null;
  };

  const startExecutionColumnResize = (
    handle: ExecutionResizeHandle,
    event: ReactPointerEvent<HTMLDivElement>,
  ): void => {
    event.preventDefault();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    executionResizeDragRef.current = {
      handle,
      startX: event.clientX,
      startWidths: resolveExecutionColumnWidths(),
    };
  };

  const startExecutionColumnMouseResize = (
    handle: ExecutionResizeHandle,
    event: ReactMouseEvent<HTMLDivElement>,
  ): void => {
    event.preventDefault();
    executionResizeDragRef.current = {
      handle,
      startX: event.clientX,
      startWidths: resolveExecutionColumnWidths(),
    };
  };

  const handleExecutionResizeKeyDown = (
    handle: ExecutionResizeHandle,
    event: ReactKeyboardEvent<HTMLDivElement>,
  ): void => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
      return;
    }

    event.preventDefault();
    const direction = event.key === "ArrowRight" ? 1 : -1;
    applyExecutionColumnWidths(resizeExecutionColumns(
      resolveExecutionColumnWidths(),
      handle,
      direction * EXECUTION_RESIZE_KEYBOARD_STEP,
    ));
  };

  const executionGridStyle = executionColumnWidths
    ? ({
        "--study-plan-execution-left": `${executionColumnWidths.left}px`,
        "--study-plan-execution-main": `${executionColumnWidths.main}px`,
        "--study-plan-execution-right": `${executionColumnWidths.right}px`,
      } as CSSProperties)
    : undefined;

  useEffect(() => {
    setSelectedSubtaskId(subtaskId ?? null);
  }, [subtaskId]);

  useEffect(() => {
    selectedSubtaskIdRef.current = selectedSubtaskId;
  }, [selectedSubtaskId]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      updateExecutionColumnResize(event.clientX);
    };
    const handlePointerUp = () => {
      stopExecutionColumnResize();
    };
    const handleMouseMove = (event: MouseEvent) => {
      updateExecutionColumnResize(event.clientX);
    };
    const handleMouseUp = () => {
      stopExecutionColumnResize();
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [executionColumnWidths]);

  useEffect(() => {
    const executionGrid = executionGridRef.current;
    if (!executionGrid) {
      return undefined;
    }

    fitExecutionColumnsToGrid();
    const resizeObserver = typeof ResizeObserver === "undefined"
      ? null
      : new ResizeObserver(() => fitExecutionColumnsToGrid());
    resizeObserver?.observe(executionGrid);
    window.addEventListener("resize", fitExecutionColumnsToGrid);

    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("resize", fitExecutionColumnsToGrid);
    };
  }, [context]);

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
  const currentGenerationState = currentSubtask
    ? generationStateBySubtask[currentSubtask.subtask_id]
    : undefined;
  const generationError = currentGenerationState?.status === "error"
    ? currentGenerationState.error ?? "内容生成失败"
    : null;
  const activeContentId = generationError ? null : currentGeneratedContent?.id ?? existingContentId ?? null;
  const activeContentTitle = currentGeneratedContent?.title ?? null;
  const currentDisplayStatus = currentSubtask
    ? displayStatusForGeneratedContent(currentSubtask.status, Boolean(activeContentId))
    : null;
  const isGeneratingCurrentSubtask = currentGenerationState?.status === "generating";
  const isGeneratingOtherSubtask = Boolean(
    currentSubtask
      && Object.entries(generationStateBySubtask).some(
        ([subtaskId, state]) => subtaskId !== currentSubtask.subtask_id && state.status === "generating",
      ),
  );
  const readonlyHandoutMarkdown = useMemo(() => handoutMarkdown(currentGeneratedContent), [currentGeneratedContent]);
  const taskTestPreviewQuestions = useMemo(
    () => taskTestQuestions(currentGeneratedContent?.content_json) ?? [],
    [currentGeneratedContent?.content_json],
  );
  const taskTestAttemptKey = currentGeneratedContent?.id ?? activeContentId ?? currentSubtask?.subtask_id ?? null;
  const completedCount = sortedTasks.reduce(
    (total, task) => total + task.subtasks.filter((subtask) => subtask.status === "completed").length,
    0,
  );
  const totalCount = sortedTasks.reduce((total, task) => total + task.subtasks.length, 0);
  const progressValue = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  useEffect(() => {
    let ignore = false;
    const targetSubtaskId = currentSubtask?.subtask_id;
    const requestEpoch = targetSubtaskId
      ? (contentEpochBySubtaskRef.current[targetSubtaskId] ?? 0)
      : 0;

    if (!targetSubtaskId || !existingContentId || generationError) {
      setIsContentLoading(false);
      if (generatedContent && generatedContent.study_subtask_id !== targetSubtaskId) {
        setGeneratedContent(null);
      }
      return;
    }

    if (
      currentGeneratedContent?.study_subtask_id === targetSubtaskId
      && currentGeneratedContent.id
    ) {
      setIsContentLoading(false);
      return;
    }

    // 写回捕获到的 epoch，保证 ref 中始终有数值记录：否则从未生成过的子任务
    // 在详情解析完成时会以 undefined === requestEpoch 误判为过期请求而丢弃结果。
    contentEpochBySubtaskRef.current[targetSubtaskId] = requestEpoch;
    setIsContentLoading(true);
    getGeneratedContentDetail(existingContentId)
      .then((content) => {
        if (!ignore && contentEpochBySubtaskRef.current[targetSubtaskId] === requestEpoch) {
          setGeneratedContent(content);
          if (content.study_subtask_id) {
            setGeneratedContentBySubtask((current) => ({
              ...current,
              [content.study_subtask_id as string]: content,
            }));
          }
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore && contentEpochBySubtaskRef.current[targetSubtaskId] === requestEpoch) {
          setGenerationStateBySubtask((current) => ({
            ...current,
            [targetSubtaskId]: {
              status: "error",
              error: generationErrorMessage(nextError),
            },
          }));
        }
      })
      .finally(() => {
        if (!ignore && contentEpochBySubtaskRef.current[targetSubtaskId] === requestEpoch) {
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

    if (generatingSubtaskIdsRef.current.has(targetSubtaskId)) {
      return;
    }

    const generationEpoch = bumpContentEpoch(targetSubtaskId);
    generatingSubtaskIdsRef.current.add(targetSubtaskId);
    setGenerationStateBySubtask((current) => ({
      ...current,
      [targetSubtaskId]: { status: "generating" },
    }));
    setGenerationNotice(null);

    try {
      const content = targetContentType === "handout"
        ? await generateSubtaskHandout(targetSubtaskId, { force_regenerate: forceRegenerate })
        : await generateSubtaskTaskTest(targetSubtaskId, { force_regenerate: forceRegenerate });
      if (contentEpochBySubtaskRef.current[targetSubtaskId] === generationEpoch) {
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
      }
    } catch (nextError) {
      const message = generationErrorMessage(nextError);
      if (contentEpochBySubtaskRef.current[targetSubtaskId] === generationEpoch) {
        setGenerationStateBySubtask((current) => ({
          ...current,
          [targetSubtaskId]: { status: "error", error: message },
        }));
        if (selectedSubtaskIdRef.current === targetSubtaskId) {
          setGenerationNotice(null);
        } else {
          setGenerationNotice(`刚才那个任务的内容生成失败：${message}`);
        }
      }
    } finally {
      generatingSubtaskIdsRef.current.delete(targetSubtaskId);
      if (contentEpochBySubtaskRef.current[targetSubtaskId] === generationEpoch) {
        setGenerationStateBySubtask((current) => {
          if (current[targetSubtaskId]?.status !== "generating") {
            return current;
          }

          const next = { ...current };
          delete next[targetSubtaskId];
          return next;
        });
        bumpContentEpoch(targetSubtaskId);
      }
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

    if (Object.entries(generationStateBySubtask).some(
      ([subtaskId, state]) => subtaskId !== nextSubtaskId && state.status === "generating",
    )) {
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

        <Box className="study-plan-execution-grid" ref={executionGridRef} style={executionGridStyle}>
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
                          className={`study-plan-execution-step${isCurrent ? " is-current" : ""}${isCompleted ? " is-complete" : ""}`}
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
                              {subtask.subtask_id === currentSubtask?.subtask_id ? (
                                <Badge color={statusColor(currentDisplayStatus ?? subtask.status)} size="xs" variant="light">
                                  {statusLabel(currentDisplayStatus ?? subtask.status)}
                                </Badge>
                              ) : (
                                <Badge color={statusColor(subtask.status)} size="xs" variant="light">
                                  {statusLabel(subtask.status)}
                                </Badge>
                              )}
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

          <Box
            aria-label="调整任务列表宽度"
            aria-orientation="vertical"
            className="study-plan-execution-resizer"
            onKeyDown={(event) => handleExecutionResizeKeyDown("left", event)}
            onMouseDown={(event) => startExecutionColumnMouseResize("left", event)}
            onPointerDown={(event) => startExecutionColumnResize("left", event)}
            onPointerMove={(event) => updateExecutionColumnResize(event.clientX)}
            onPointerUp={stopExecutionColumnResize}
            role="separator"
            tabIndex={0}
          />

          <Paper
            aria-busy={isSwitchingSubtask || undefined}
            className="study-plan-execution-main has-pinned-completion"
            radius="md"
            withBorder
          >
            <Stack className="study-plan-execution-main-stack" gap="lg">
              <Stack gap={8}>
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
                          其他任务的内容也在后台生成中，完成后会自动保存到对应任务。
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
                                  loading={isGeneratingCurrentSubtask}
                                  onClick={() => void handleGenerateContent(true)}
                                  size="xs"
                                  variant="subtle"
                                >
                                  重新生成
                                </Button>
                              </Group>
                            </Group>
                          </Paper>
                          {contentType === "handout" && readonlyHandoutMarkdown ? (
                            <Paper className="study-plan-handout-preview" radius="md" withBorder>
                              <HandoutMarkdownRenderer markdown={readonlyHandoutMarkdown} />
                            </Paper>
                          ) : null}
                          {contentType === "task_test" && taskTestPreviewQuestions.length > 0 ? (
                            <Box className="study-plan-task-test-preview">
                              <TaskTestResult
                                attemptKey={taskTestAttemptKey}
                                citations={currentGeneratedContent?.source_citations ?? []}
                                questions={taskTestPreviewQuestions}
                              />
                            </Box>
                          ) : null}
                        </>
                      ) : (
                        <Group justify="space-between" wrap="nowrap">
                          <Badge color="gray" variant="light">{contentLabel}待生成</Badge>
                          <Button
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

          <Box
            aria-label="调整 AI 助教宽度"
            aria-orientation="vertical"
            className="study-plan-execution-resizer"
            onKeyDown={(event) => handleExecutionResizeKeyDown("right", event)}
            onMouseDown={(event) => startExecutionColumnMouseResize("right", event)}
            onPointerDown={(event) => startExecutionColumnResize("right", event)}
            onPointerMove={(event) => updateExecutionColumnResize(event.clientX)}
            onPointerUp={stopExecutionColumnResize}
            role="separator"
            tabIndex={0}
          />

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
                            {material.material_type ?? "未知类型"}
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
