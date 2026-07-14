import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Group,
  NativeSelect,
  NumberInput,
  Paper,
  Skeleton,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import {
  IconArrowLeft,
  IconCheck,
  IconTrash,
  IconDownload,
  IconPlayerPlay,
  IconRotateClockwise,
} from "@tabler/icons-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { WorkbenchTopbar } from "../components/WorkbenchTopbar";
import { fetchCourse } from "../features/courses/api";
import { StudyPlanTaskDescription } from "../features/study-plans/components/StudyPlanTaskDescription";
import {
  deleteStudyPlan,
  fetchStudyPlan,
  listStudyPlans,
  previewStudyPlanRegeneration,
  replaceStudyPlan,
} from "../features/study-plans/api";
import type {
  PlanPreference,
  StudyPlanDetail,
  StudyPlanRead,
  StudyPlanPreview,
  StudySubtaskRead,
} from "../features/study-plans/types";
import type { Course } from "../types/course";
import "./study-plan.css";

const minimumDailyMinutes = 30;

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function lifecycleErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      STATE_CONFLICT: "计划已有学习进度、生成内容，或已被更新。请刷新后查看当前计划；如需大改，可新建计划。",
      NOT_FOUND: "学习计划不存在或你没有权限访问。",
      VALIDATION_ERROR: "计划配置不合法，请检查日期、每日时长和任务范围。",
      NO_PARSED_MATERIAL: "当前资料范围没有可用的已解析资料。",
      MATERIAL_COVERAGE_INCOMPLETE: "资料覆盖不完整，请调整资料范围后重试。",
      PREVIEW_TASKS_REQUIRED: "替换必须基于刚刚生成并确认的任务预览。",
    };
    return messages[error.code] ?? error.message;
  }

  return errorMessage(error, fallback);
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function planConfig(detail: StudyPlanDetail | null): Record<string, unknown> {
  return isRecord(detail?.plan.parsed_config_json) ? detail.plan.parsed_config_json : {};
}

function confirmedConfig(detail: StudyPlanDetail | null): Record<string, unknown> {
  const config = planConfig(detail);
  return isRecord(config.confirmed_config) ? config.confirmed_config : config;
}

function preferenceFromDetail(detail: StudyPlanDetail | null): PlanPreference {
  const preference = confirmedConfig(detail).preference;
  if (preference === "fast_track" || preference === "balanced" || preference === "mastery" || preference === "sprint") {
    return preference;
  }
  return "balanced";
}

function preferenceLabel(preference: PlanPreference): string {
  const labels: Record<PlanPreference, string> = {
    fast_track: "快速通关",
    balanced: "均衡学习",
    mastery: "深入掌握",
    sprint: "冲刺强化",
  };
  return labels[preference];
}

function sortedPreviewTasks(preview: StudyPlanPreview): StudyPlanPreview["tasks"] {
  return [...preview.tasks].sort((left, right) => left.sort_order - right.sort_order);
}

function optionalRecord(value: unknown): Record<string, unknown> | undefined {
  return isRecord(value) ? value : undefined;
}

function sortPlansByRecent(plans: StudyPlanRead[]): StudyPlanRead[] {
  return [...plans].sort((left, right) => {
    const leftTime = Date.parse(left.updated_at || left.created_at);
    const rightTime = Date.parse(right.updated_at || right.created_at);
    return rightTime - leftTime;
  });
}

export function StudyPlanDetailPage() {
  const { courseId, planId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [detail, setDetail] = useState<StudyPlanDetail | null>(null);
  const [coursePlans, setCoursePlans] = useState<StudyPlanRead[]>([]);
  const [coursePlansError, setCoursePlansError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLifecycleOpen, setIsLifecycleOpen] = useState(false);
  const [regenerationGoal, setRegenerationGoal] = useState("");
  const [regenerationStartDate, setRegenerationStartDate] = useState("");
  const [regenerationEndDate, setRegenerationEndDate] = useState("");
  const [regenerationDailyMinutes, setRegenerationDailyMinutes] = useState<number | "">("");
  const [regenerationPreference, setRegenerationPreference] = useState<PlanPreference>("balanced");
  const [regenerationPreview, setRegenerationPreview] = useState<StudyPlanPreview | null>(null);
  const [lifecycleError, setLifecycleError] = useState<string | null>(null);
  const [isPreviewingRegeneration, setIsPreviewingRegeneration] = useState(false);
  const [isReplacingPlan, setIsReplacingPlan] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeletingPlan, setIsDeletingPlan] = useState(false);

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

  useEffect(() => {
    let ignore = false;

    if (!courseId) {
      setCoursePlans([]);
      setCoursePlansError(null);
      return;
    }

    setCoursePlansError(null);
    listStudyPlans(courseId)
      .then((plans) => {
        if (!ignore) {
          setCoursePlans(sortPlansByRecent(plans));
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setCoursePlansError(errorMessage(nextError, "课程学习计划列表加载失败"));
          setCoursePlans([]);
        }
      });

    return () => {
      ignore = true;
    };
  }, [courseId]);

  useEffect(() => {
    if (!detail) {
      return;
    }

    setRegenerationGoal(detail.plan.goal_text);
    setRegenerationStartDate(detail.plan.start_date);
    setRegenerationEndDate(detail.plan.end_date);
    setRegenerationDailyMinutes(detail.plan.daily_available_minutes);
    setRegenerationPreference(preferenceFromDetail(detail));
    setRegenerationPreview(null);
    setLifecycleError(null);
  }, [detail]);

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
      <Box className="study-plan-page workbench-page">
        <WorkbenchTopbar backFallbackTo={courseId ? `/courses/${courseId}` : "/"} pageName="学习计划" />
        <Box className="study-plan-shell" data-workbench-scroll="locked">
          <Skeleton height={36} width={280} />
          <Skeleton height={520} radius="md" />
        </Box>
      </Box>
    );
  }

  if (error || !detail) {
    return (
      <Box className="study-plan-page workbench-page">
        <WorkbenchTopbar backFallbackTo={courseId ? `/courses/${courseId}` : "/"} pageName="学习计划" />
        <Box className="study-plan-shell" data-workbench-scroll="locked">
          <Alert color="red" role="alert" title="学习计划加载失败" variant="light">
            {error ?? "学习计划不存在"}
          </Alert>
        </Box>
      </Box>
    );
  }

  const sortedTasks = [...detail.tasks].sort((left, right) => left.sort_order - right.sort_order);
  const displayPlans = coursePlans.length > 0
    ? coursePlans
    : detail.plan.course_id === courseId
      ? [detail.plan]
      : [];
  const firstRunnableSubtask = sortedTasks
    .flatMap((task) => subtasksByTaskId.get(task.id) ?? [])
    .find((subtask) => subtask.status !== "completed")
    ?? sortedTasks.flatMap((task) => subtasksByTaskId.get(task.id) ?? [])[0];

  const lifecycleValidationError = (() => {
    if (!regenerationGoal.trim()) {
      return "请输入调整后的学习目标。";
    }
    if (!regenerationStartDate || !regenerationEndDate) {
      return "请选择调整后的学习日期。";
    }
    if (regenerationStartDate > regenerationEndDate) {
      return "开始日期不能晚于结束日期。";
    }
    if (regenerationDailyMinutes === "" || regenerationDailyMinutes < minimumDailyMinutes) {
      return `每日学习时长不能少于 ${minimumDailyMinutes} 分钟。`;
    }
    return null;
  })();

  async function handleRegenerationPreview() {
    if (!planId || lifecycleValidationError) {
      setLifecycleError(lifecycleValidationError);
      return;
    }

    setIsPreviewingRegeneration(true);
    setLifecycleError(null);
    setRegenerationPreview(null);

    try {
      const nextPreview = await previewStudyPlanRegeneration(planId, {
        goal_text: regenerationGoal.trim(),
        start_date: regenerationStartDate,
        end_date: regenerationEndDate,
        daily_available_minutes: Number(regenerationDailyMinutes),
        preference: regenerationPreference,
      });
      setRegenerationPreview(nextPreview);
    } catch (nextError) {
      setLifecycleError(lifecycleErrorMessage(nextError, "重新生成预览失败"));
    } finally {
      setIsPreviewingRegeneration(false);
    }
  }

  async function handleReplacePlan() {
    const currentDetail = detail;
    if (!planId || !regenerationPreview || !currentDetail) {
      return;
    }

    setIsReplacingPlan(true);
    setLifecycleError(null);

    try {
      const nextDetail = await replaceStudyPlan(planId, {
        goal_text: regenerationPreview.goal_text,
        start_date: regenerationPreview.start_date,
        end_date: regenerationPreview.end_date,
        daily_available_minutes: regenerationPreview.daily_available_minutes,
        preference: regenerationPreview.preference ?? regenerationPreference,
        material_scope: regenerationPreview.material_scope,
        diagnostic_profile: regenerationPreview.diagnostic_profile,
        material_snapshot: optionalRecord(regenerationPreview.material_snapshot),
        coverage: optionalRecord(regenerationPreview.coverage),
        capacity: optionalRecord(regenerationPreview.capacity),
        generation_metadata: optionalRecord(regenerationPreview.generation_metadata),
        title: regenerationPreview.title,
        client_flow: "wizard_v1",
        tasks: regenerationPreview.tasks,
        expected_updated_at: currentDetail.plan.updated_at,
      });
      setDetail(nextDetail);
      setCoursePlans((current) => sortPlansByRecent(current.map((plan) => (
        plan.id === nextDetail.plan.id ? nextDetail.plan : plan
      ))));
      setIsLifecycleOpen(false);
      setRegenerationPreview(null);
    } catch (nextError) {
      setLifecycleError(lifecycleErrorMessage(nextError, "替换学习计划失败"));
    } finally {
      setIsReplacingPlan(false);
    }
  }

  async function handleDeletePlan() {
    if (!planId) {
      return;
    }

    setIsDeletingPlan(true);
    setDeleteError(null);

    try {
      await deleteStudyPlan(planId);
      navigate(courseId ? `/courses/${courseId}` : "/");
    } catch (nextError) {
      setDeleteError(lifecycleErrorMessage(nextError, "删除学习计划失败"));
    } finally {
      setIsDeletingPlan(false);
    }
  }

  return (
    <Box className="study-plan-page workbench-page">
      <WorkbenchTopbar
        backFallbackTo={courseId ? `/courses/${courseId}` : "/"}
        contextName={detail.plan.title}
        meta={(
          <>
            <Badge color={statusColor(detail.plan.status)} variant="light">
              {statusLabel(detail.plan.status)}
            </Badge>
            <Badge color="gray" variant="light">
              {detail.plan.start_date} - {detail.plan.end_date}
            </Badge>
            <Badge color="gray" variant="light">
              每日 {detail.plan.daily_available_minutes} 分钟
            </Badge>
          </>
        )}
        pageName="学习计划"
      />
      <Box className="study-plan-shell" component="main" data-workbench-scroll="locked">
        <Group className="study-plan-nav" hidden aria-hidden="true" justify="space-between" wrap="nowrap">
          <Button
            component={Link}
            leftSection={<IconArrowLeft size={16} />}
            to={courseId ? `/courses/${courseId}` : "/"}
            variant="subtle"
          >
            返回课程
          </Button>
          <Group gap="xs">
            <Button
              leftSection={<IconRotateClockwise size={16} />}
              onClick={() => setIsLifecycleOpen((current) => !current)}
              variant="light"
            >
              重新生成
            </Button>
            <Button color="red" leftSection={<IconTrash size={16} />} onClick={() => setIsDeleteConfirmOpen(true)} variant="light">
              删除计划
            </Button>
            <Button disabled leftSection={<IconDownload size={16} />} variant="light">
              导出计划（待接入）
            </Button>
          </Group>
        </Group>

        <Box className="study-plan-course-layout">
          <Paper className="study-plan-panel study-plan-plan-switcher" radius="md" withBorder>
            <Group justify="space-between" wrap="nowrap">
              <Stack gap={2}>
                <Title order={2}>本课程计划</Title>
                <Text c="dimmed" size="sm">切换左侧计划，右侧查看具体计划详情。</Text>
              </Stack>
              <Badge color="blue" variant="light">{displayPlans.length} 个</Badge>
            </Group>
            {coursePlansError ? (
              <Alert color="yellow" role="status" title="计划列表加载失败" variant="light">
                {coursePlansError}
              </Alert>
            ) : null}
            <Stack gap="xs">
              {displayPlans.map((plan) => {
                const isCurrent = plan.id === detail.plan.id;
                return (
                  <Paper
                    aria-current={isCurrent ? "page" : undefined}
                    className={isCurrent ? "study-plan-switcher-item is-current" : "study-plan-switcher-item"}
                    component={Link}
                    key={plan.id}
                    radius="md"
                    to={`/courses/${plan.course_id}/study-plans/${plan.id}`}
                    withBorder
                  >
                    <Stack gap={6}>
                      <Group justify="space-between" wrap="nowrap">
                        <Text fw={760} lineClamp={2}>{plan.title}</Text>
                        <Badge color={statusColor(plan.status)} size="xs" variant="light">
                          {statusLabel(plan.status)}
                        </Badge>
                      </Group>
                      <Text c="dimmed" size="xs">{plan.start_date} - {plan.end_date}</Text>
                      <Text c="dimmed" lineClamp={2} size="sm">{plan.goal_text}</Text>
                    </Stack>
                  </Paper>
                );
              })}
            </Stack>
          </Paper>

          <Box className="study-plan-course-detail-pane">
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
              <Stack align="flex-end" gap="sm">
                <Group gap="xs" justify="flex-end" wrap="nowrap">
                  <Button
                    leftSection={<IconRotateClockwise size={16} />}
                    onClick={() => setIsLifecycleOpen((current) => !current)}
                    variant="light"
                  >
                    重新生成
                  </Button>
                  <Button color="red" leftSection={<IconTrash size={16} />} onClick={() => setIsDeleteConfirmOpen(true)} variant="light">
                    删除计划
                  </Button>
                  <Button disabled leftSection={<IconDownload size={16} />} variant="light">
                    导出计划（待接入）
                  </Button>
                </Group>
                <Button
                  component={Link}
                  leftSection={<IconPlayerPlay size={16} />}
                  to={`/study-subtasks/${firstRunnableSubtask.id}`}
                >
                  开始学习
                </Button>
              </Stack>
            ) : (
              <Stack align="flex-end" gap="sm">
                <Group gap="xs" justify="flex-end" wrap="nowrap">
                  <Button
                    leftSection={<IconRotateClockwise size={16} />}
                    onClick={() => setIsLifecycleOpen((current) => !current)}
                    variant="light"
                  >
                    重新生成
                  </Button>
                  <Button color="red" leftSection={<IconTrash size={16} />} onClick={() => setIsDeleteConfirmOpen(true)} variant="light">
                    删除计划
                  </Button>
                  <Button disabled leftSection={<IconDownload size={16} />} variant="light">
                    导出计划（待接入）
                  </Button>
                </Group>
                <Button disabled leftSection={<IconPlayerPlay size={16} />}>
                  暂无任务
                </Button>
              </Stack>
            )}
          </Group>
        </Paper>

        {isLifecycleOpen ? (
          <Paper className="study-plan-panel study-plan-lifecycle-panel" radius="md" withBorder>
            <Group align="flex-start" justify="space-between" wrap="nowrap">
              <Stack gap={2}>
                <Title order={2}>调整并重新生成</Title>
                <Text c="dimmed" size="sm">
                  新预览不会写入数据库；确认替换时会带上当前计划更新时间，后端会拒绝有进度或已生成内容的替换。
                </Text>
              </Stack>
              <Badge color="blue" variant="light">生命周期</Badge>
            </Group>

            {lifecycleError ? (
              <Alert color="red" role="alert" title="计划生命周期操作失败" variant="light">
                {lifecycleError}
              </Alert>
            ) : null}

            <Box className="study-plan-lifecycle-form">
              <Textarea
                label="调整目标"
                minRows={2}
                onChange={(event) => {
                  setRegenerationGoal(event.currentTarget.value);
                  setRegenerationPreview(null);
                }}
                value={regenerationGoal}
              />
              <Box className="study-plan-lifecycle-fields">
                <Text component="label" size="sm">
                  调整开始日期
                  <input
                    aria-label="调整开始日期"
                    className="study-plan-native-input"
                    onChange={(event) => {
                      setRegenerationStartDate(event.currentTarget.value);
                      setRegenerationPreview(null);
                    }}
                    type="date"
                    value={regenerationStartDate}
                  />
                </Text>
                <Text component="label" size="sm">
                  调整结束日期
                  <input
                    aria-label="调整结束日期"
                    className="study-plan-native-input"
                    onChange={(event) => {
                      setRegenerationEndDate(event.currentTarget.value);
                      setRegenerationPreview(null);
                    }}
                    type="date"
                    value={regenerationEndDate}
                  />
                </Text>
                <NumberInput
                  label="调整每日学习时长"
                  min={minimumDailyMinutes}
                  onChange={(value) => {
                    setRegenerationDailyMinutes(typeof value === "number" ? value : "");
                    setRegenerationPreview(null);
                  }}
                  rightSection={<Text c="dimmed" size="xs">分钟</Text>}
                  value={regenerationDailyMinutes}
                />
                <NativeSelect
                  data={[
                    { label: "快速通关", value: "fast_track" },
                    { label: "均衡学习", value: "balanced" },
                    { label: "深入掌握", value: "mastery" },
                    { label: "冲刺强化", value: "sprint" },
                  ]}
                  label="调整学习方式"
                  onChange={(event) => {
                    setRegenerationPreference(event.currentTarget.value as PlanPreference);
                    setRegenerationPreview(null);
                  }}
                  value={regenerationPreference}
                />
              </Box>
              <Group justify="space-between">
                <Text c={lifecycleValidationError ? "red" : "dimmed"} size="sm">
                  {lifecycleValidationError ?? `当前方式：${preferenceLabel(regenerationPreference)}`}
                </Text>
                <Button
                  disabled={Boolean(lifecycleValidationError)}
                  leftSection={<IconRotateClockwise size={16} />}
                  loading={isPreviewingRegeneration}
                  onClick={handleRegenerationPreview}
                  variant="light"
                >
                  生成替换预览
                </Button>
              </Group>
            </Box>

            {regenerationPreview ? (
              <Paper className="study-plan-regeneration-preview" radius="md" withBorder>
                <Group justify="space-between" wrap="nowrap">
                  <Stack gap={2}>
                    <Text fw={760}>{regenerationPreview.title}</Text>
                    <Text c="dimmed" size="sm">
                      {regenerationPreview.start_date} - {regenerationPreview.end_date} / 每日{" "}
                      {regenerationPreview.daily_available_minutes} 分钟
                    </Text>
                  </Stack>
                  <Button
                    leftSection={<IconCheck size={16} />}
                    loading={isReplacingPlan}
                    onClick={handleReplacePlan}
                  >
                    确认替换计划
                  </Button>
                </Group>
                <Stack gap="xs" mt="sm">
                  {sortedPreviewTasks(regenerationPreview).map((task) => (
                    <Paper className="study-plan-subtask" key={`${task.task_date}-${task.sort_order}`} radius="md" withBorder>
                      <Text fw={700}>{task.title}</Text>
                      <Text c="dimmed" size="sm">{task.task_date}</Text>
                      <Text c="dimmed" size="xs">
                        {task.subtasks.length} 个子任务 / {task.subtasks.reduce((sum, subtask) => sum + subtask.estimated_minutes, 0)} 分钟
                      </Text>
                    </Paper>
                  ))}
                </Stack>
              </Paper>
            ) : null}
          </Paper>
        ) : null}

        {isDeleteConfirmOpen ? (
          <Paper className="study-plan-panel study-plan-delete-panel" radius="md" withBorder>
            <Title order={2}>确认删除计划</Title>
            <Text c="dimmed" size="sm">
              删除后该计划会被软删除，课程详情和日历默认不再展示它。此操作不会删除课程资料或已存在的生成内容。
            </Text>
            {deleteError ? (
              <Alert color="red" role="alert" title="删除学习计划失败" variant="light">
                {deleteError}
              </Alert>
            ) : null}
            <Group justify="flex-end">
              <Button disabled={isDeletingPlan} onClick={() => setIsDeleteConfirmOpen(false)} variant="subtle">
                取消
              </Button>
              <Button color="red" loading={isDeletingPlan} onClick={handleDeletePlan}>
                确认删除
              </Button>
            </Group>
          </Paper>
        ) : null}

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
                        <Stack gap={8}>
                          <Group align="flex-start" className="study-plan-subtask-header" justify="space-between" wrap="nowrap">
                            <Text fw={700}>{subtask.title}</Text>
                            <Badge className="study-plan-type-badge" color={subtaskTypeColor(subtask.subtask_type)} variant="light">
                              {subtaskTypeLabel(subtask.subtask_type)}
                            </Badge>
                          </Group>
                          <StudyPlanTaskDescription description={subtask.description} />
                          <Group justify="flex-end">
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
                          </Group>
                        </Stack>
                      </Paper>
                    ))}
                  </Stack>
                </Paper>
              ))}
            </Stack>
          </Paper>
        </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
