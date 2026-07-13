import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Paper,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconArrowLeft,
  IconDownload,
  IconPlayerPlay,
  IconRotateClockwise,
} from "@tabler/icons-react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { fetchCourse } from "../features/courses/api";
import { fetchStudyPlan } from "../features/study-plans/api";
import type { StudyPlanDetail, StudySubtaskRead } from "../features/study-plans/types";
import type { Course } from "../types/course";
import "./study-plan.css";

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: "已启用",
    archived: "已归档",
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
    not_started: "blue",
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

function subtaskTypeColor(type: string): string {
  const colors: Record<string, string> = {
    learn: "violet",
    quiz: "blue",
    review: "grape",
    test: "orange",
  };
  return colors[type] ?? "gray";
}

function relatedMaterialIds(subtask: StudySubtaskRead): string[] {
  return subtask.related_material_ids_json ?? subtask.related_material_ids ?? [];
}

export function StudyPlanDetailPage() {
  const { courseId, planId } = useParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [detail, setDetail] = useState<StudyPlanDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    if (!planId) {
      setError("学习计划不存在");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    const coursePromise = courseId ? fetchCourse(courseId).catch(() => null) : Promise.resolve(null);
    Promise.all([fetchStudyPlan(planId), coursePromise])
      .then(([nextDetail, nextCourse]) => {
        if (!ignore) {
          setDetail(nextDetail);
          setCourse(nextCourse);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(errorMessage(nextError, "学习计划加载失败"));
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
  }, [courseId, planId]);

  const subtasksByTaskId = useMemo(() => {
    const grouped = new Map<string, StudySubtaskRead[]>();
    for (const subtask of detail?.subtasks ?? []) {
      const current = grouped.get(subtask.task_id) ?? [];
      current.push(subtask);
      grouped.set(subtask.task_id, current);
    }
    for (const subtasks of grouped.values()) {
      subtasks.sort((left, right) => left.sort_order - right.sort_order);
    }
    return grouped;
  }, [detail?.subtasks]);

  if (isLoading) {
    return (
      <Box className="study-plan-page">
        <Box className="study-plan-shell">
          <Skeleton height={36} width={280} />
          <Skeleton height={520} radius="md" />
        </Box>
      </Box>
    );
  }

  if (error || !detail) {
    return (
      <Box className="study-plan-page">
        <Box className="study-plan-shell">
          <Alert color="red" role="alert" title="学习计划加载失败" variant="light">
            {error ?? "学习计划不存在"}
          </Alert>
        </Box>
      </Box>
    );
  }

  const sortedTasks = [...detail.tasks].sort((left, right) => left.sort_order - right.sort_order);
  const firstRunnableSubtask = sortedTasks
    .flatMap((task) => subtasksByTaskId.get(task.id) ?? [])
    .find((subtask) => subtask.status !== "completed")
    ?? sortedTasks.flatMap((task) => subtasksByTaskId.get(task.id) ?? [])[0];

  return (
    <Box className="study-plan-page">
      <Box className="study-plan-shell" component="main">
        <Group className="study-plan-nav" justify="space-between" wrap="nowrap">
          <Button
            component={Link}
            leftSection={<IconArrowLeft size={16} />}
            to={courseId ? `/courses/${courseId}` : "/"}
            variant="subtle"
          >
            返回课程
          </Button>
          <Group gap="xs">
            <Button disabled leftSection={<IconRotateClockwise size={16} />} variant="light">
              重新生成（待接入）
            </Button>
            <Button disabled leftSection={<IconDownload size={16} />} variant="light">
              导出计划（待接入）
            </Button>
          </Group>
        </Group>

        <Paper className="study-plan-detail-hero" radius="md" withBorder>
          <Group align="flex-start" justify="space-between">
            <Stack gap={6}>
              <Text c="dimmed" size="sm">{course?.name ?? "课程学习计划"}</Text>
              <Title order={1}>{detail.plan.title}</Title>
              <Text className="study-plan-goal">{detail.plan.goal_text}</Text>
              <Group gap="xs">
                <Badge color={statusColor(detail.plan.status)} variant="light">
                  {statusLabel(detail.plan.status)}
                </Badge>
                <Badge color="gray" variant="light">
                  {detail.plan.start_date} - {detail.plan.end_date}
                </Badge>
                <Badge color="gray" variant="light">
                  每日 {detail.plan.daily_available_minutes} 分钟
                </Badge>
              </Group>
            </Stack>
            {firstRunnableSubtask ? (
              <Button
                component={Link}
                leftSection={<IconPlayerPlay size={16} />}
                to={`/study-subtasks/${firstRunnableSubtask.id}`}
              >
                开始学习
              </Button>
            ) : (
              <Button disabled leftSection={<IconPlayerPlay size={16} />}>
                暂无任务
              </Button>
            )}
          </Group>
        </Paper>

        <Box className="study-plan-detail-layout">
          <Paper className="study-plan-panel" radius="md" withBorder>
            <Group justify="space-between" wrap="nowrap">
              <Stack gap={2}>
                <Title order={2}>任务结构</Title>
                <Text c="dimmed" size="sm">只读展示后端已保存的计划、任务和子任务。</Text>
              </Stack>
              <Badge color="violet" variant="light">任务结构</Badge>
            </Group>

            <Stack gap="sm">
              {sortedTasks.map((task) => (
                <Paper className="study-plan-task" key={task.id} radius="md" withBorder>
                  <Group justify="space-between" wrap="nowrap">
                    <Stack gap={2}>
                      <Text fw={750}>{task.title}</Text>
                      <Text c="dimmed" size="sm">{task.task_date}</Text>
                    </Stack>
                    <Badge color={statusColor(task.status)} variant="light">
                      {statusLabel(task.status)}
                    </Badge>
                  </Group>
                  <Stack gap="xs" mt="sm">
                    {(subtasksByTaskId.get(task.id) ?? []).map((subtask) => (
                      <Paper className="study-plan-subtask" key={subtask.id} radius="md" withBorder>
                        <Group align="flex-start" justify="space-between" wrap="nowrap">
                          <Stack gap={4}>
                            <Text fw={700}>{subtask.title}</Text>
                            {subtask.description ? (
                              <Text c="dimmed" size="sm">{subtask.description}</Text>
                            ) : null}
                            {relatedMaterialIds(subtask).length > 0 ? (
                              <Text c="dimmed" size="xs">
                                关联资料：{relatedMaterialIds(subtask).join(", ")}
                              </Text>
                            ) : null}
                          </Stack>
                          <Stack align="flex-end" gap="xs">
                            <Badge color={subtaskTypeColor(subtask.subtask_type)} variant="light">
                              {subtaskTypeLabel(subtask.subtask_type)}
                            </Badge>
                            <Button
                              aria-label={`进入学习：${subtask.title}`}
                              component={Link}
                              leftSection={<IconPlayerPlay size={14} />}
                              size="xs"
                              to={`/study-subtasks/${subtask.id}`}
                              variant="light"
                            >
                              进入学习
                            </Button>
                          </Stack>
                        </Group>
                      </Paper>
                    ))}
                  </Stack>
                </Paper>
              ))}
            </Stack>
          </Paper>

          <Paper className="study-plan-panel" radius="md" withBorder>
            <Title order={2}>后续能力</Title>
            <Stack gap="xs">
              <Paper className="study-plan-disabled-row" radius="md" withBorder>
                <Text fw={700}>日历同步</Text>
                <Badge color="gray" variant="light">待接入</Badge>
              </Paper>
              <Paper className="study-plan-disabled-row" radius="md" withBorder>
                <Text fw={700}>完成打卡</Text>
                <Badge color="teal" variant="light">执行页已接入</Badge>
              </Paper>
              <Paper className="study-plan-disabled-row" radius="md" withBorder>
                <Text fw={700}>资料讲义 / 小测闭环</Text>
                <Badge color="gray" variant="light">待接入</Badge>
              </Paper>
            </Stack>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}
