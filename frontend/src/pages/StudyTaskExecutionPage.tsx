import { useEffect, useMemo, useState } from "react";
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
  Title,
} from "@mantine/core";
import {
  IconArrowLeft,
  IconBook2,
  IconCheck,
  IconCircle,
  IconPlayerPlay,
  IconX,
} from "@tabler/icons-react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { fetchSubtaskExecutionContext, updateSubtaskCompletion } from "../features/study-plans/api";
import type {
  ExecutionContextRead,
  ExecutionMaterialRead,
  ExecutionSubtaskRead,
  ExecutionTaskRead,
  SubtaskCompletionResult,
} from "../features/study-plans/types";
import "./study-plan.css";

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

export function StudyTaskExecutionPage() {
  const { subtaskId } = useParams();
  const [context, setContext] = useState<ExecutionContextRead | null>(null);
  const [completionResult, setCompletionResult] = useState<SubtaskCompletionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

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
    setCompletionResult(null);

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

  if (isLoading) {
    return (
      <Box className="study-plan-page">
        <Box className="study-plan-shell">
          <Skeleton height={36} width={280} />
          <Skeleton height={620} radius="md" />
        </Box>
      </Box>
    );
  }

  if (error || !context || !currentSubtask) {
    return (
      <Box className="study-plan-page">
        <Box className="study-plan-shell">
          <Alert color="red" role="alert" title="执行页加载失败" variant="light">
            {error ?? "未找到当前二级任务"}
          </Alert>
        </Box>
      </Box>
    );
  }

  return (
    <Box className="study-plan-page">
      <Box className="study-plan-execution-shell" component="main">
        <Group className="study-plan-nav" justify="space-between" wrap="nowrap">
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
              <Stack gap={4}>
                <Text c="dimmed" size="sm">{context.course.name}</Text>
                <Title order={2}>今日学习任务</Title>
              </Stack>
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

          <Paper className="study-plan-execution-main" radius="md" withBorder>
            <Stack gap="lg">
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
                    <IconBook2 size={18} />
                    <Text fw={750}>执行说明</Text>
                  </Group>
                  <Text c="dimmed" size="sm">
                    当前版本先接入任务上下文与完成状态。今日讲义、任务测试题和执行页问答会在后续上下文按真实接口继续接入。
                  </Text>
                  <Group gap="xs">
                    {context.handout_content_id ? (
                      <Badge color="teal" variant="light">已有今日讲义</Badge>
                    ) : (
                      <Badge color="gray" variant="light">今日讲义待生成</Badge>
                    )}
                    {context.task_test_content_id ? (
                      <Badge color="teal" variant="light">已有任务测试题</Badge>
                    ) : (
                      <Badge color="gray" variant="light">任务测试题待生成</Badge>
                    )}
                  </Group>
                </Stack>
              </Paper>

              <Group justify="flex-end">
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
                <Title order={2}>资料与打卡</Title>
                <Text c="dimmed" size="sm">
                  资料范围来自当前二级任务，前端不自行改写。
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
