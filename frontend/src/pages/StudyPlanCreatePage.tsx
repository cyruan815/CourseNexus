import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Divider,
  Group,
  Paper,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import {
  IconArrowLeft,
  IconCalendarStats,
  IconClipboardCheck,
  IconLock,
  IconRefresh,
} from "@tabler/icons-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { fetchCourse } from "../features/courses/api";
import {
  previewStudyPlan,
  saveStudyPlan,
} from "../features/study-plans/api";
import { DiagnosticWizard } from "../features/study-plans/components/DiagnosticWizard";
import type {
  StudyPlanDiagnosticProfile,
  StudyPlanPreview,
  StudyPlanPreviewRequest,
  StudyPlanPreviewSubtask,
} from "../features/study-plans/types";
import type { Course } from "../types/course";
import "./study-plan.css";

const defaultScope = {
  include_all_parsed_materials: true,
  material_ids: [],
};
const defaultPreference = "balanced" as const;
const minimumDailyMinutes = 30;

function createStudyPlanIdempotencyKey(courseId: string): string {
  const randomPart = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `study-plan-${courseId}-${randomPart}`;
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
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

function subtaskTone(type: string): string {
  const tones: Record<string, string> = {
    learn: "violet",
    quiz: "blue",
    review: "grape",
    test: "orange",
  };
  return tones[type] ?? "gray";
}

function StudyPlanPreviewSubtaskItem({ subtask }: { subtask: StudyPlanPreviewSubtask }) {
  return (
    <Paper className="study-plan-subtask" radius="md" withBorder>
      <Group align="flex-start" justify="space-between" wrap="nowrap">
        <Stack gap={4}>
          <Text fw={700}>{subtask.title}</Text>
          {subtask.description ? (
            <Text c="dimmed" size="sm">{subtask.description}</Text>
          ) : null}
        </Stack>
        <Badge color={subtaskTone(subtask.subtask_type)} variant="light">
          {subtaskTypeLabel(subtask.subtask_type)}
        </Badge>
      </Group>
    </Paper>
  );
}

function StudyPlanPreviewPanel({ preview }: { preview: StudyPlanPreview | null }) {
  if (!preview) {
    return (
      <Paper className="study-plan-preview-empty" radius="md" withBorder>
        <IconCalendarStats size={44} stroke={1.6} />
        <Stack gap={4}>
          <Text fw={750}>等待生成预览</Text>
          <Text c="dimmed" size="sm">
            先填写基础配置，再调用真实 preview。自动解析配置只展示为待接入，不制造假结果。
          </Text>
        </Stack>
      </Paper>
    );
  }

  return (
    <Stack gap="sm">
      <Group justify="space-between" wrap="nowrap">
        <Stack gap={2}>
          <Text fw={750}>{preview.title}</Text>
          <Text c="dimmed" size="sm">
            {preview.start_date} - {preview.end_date} / 每日 {preview.daily_available_minutes} 分钟
          </Text>
        </Stack>
        <Badge color="teal" variant="light">预览已生成</Badge>
      </Group>
      {preview.tasks.map((task) => (
        <Paper className="study-plan-task" key={`${task.task_date}-${task.sort_order}`} radius="md" withBorder>
          <Group justify="space-between" wrap="nowrap">
            <Stack gap={2}>
              <Text fw={750}>{task.title}</Text>
              <Text c="dimmed" size="sm">{task.task_date}</Text>
            </Stack>
            <Badge color="blue" variant="light">未开始</Badge>
          </Group>
          <Stack gap="xs" mt="sm">
            {task.subtasks.map((subtask) => (
              <StudyPlanPreviewSubtaskItem
                key={`${task.task_date}-${subtask.sort_order}-${subtask.title}`}
                subtask={subtask}
              />
            ))}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

export function StudyPlanCreatePage() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [goalText, setGoalText] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [dailyMinutes, setDailyMinutes] = useState("");
  const [diagnosticProfile, setDiagnosticProfile] = useState<StudyPlanDiagnosticProfile | null>(null);
  const [preview, setPreview] = useState<StudyPlanPreview | null>(null);
  const [previewSnapshot, setPreviewSnapshot] = useState<StudyPlanPreviewRequest | null>(null);
  const [previewSaveIdempotencyKey, setPreviewSaveIdempotencyKey] = useState<string | null>(null);
  const [isPreviewStale, setIsPreviewStale] = useState(false);
  const [isLoadingCourse, setIsLoadingCourse] = useState(true);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    if (!courseId) {
      setError("课程不存在");
      setIsLoadingCourse(false);
      return;
    }

    setIsLoadingCourse(true);
    setError(null);
    fetchCourse(courseId)
      .then((nextCourse) => {
        if (!ignore) {
          setCourse(nextCourse);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(errorMessage(nextError, "课程加载失败"));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsLoadingCourse(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [courseId]);

  const draft = useMemo<StudyPlanPreviewRequest | null>(() => {
    const minutes = Number.parseInt(dailyMinutes, 10);
    if (!goalText.trim() || !startDate || !endDate || Number.isNaN(minutes)) {
      return null;
    }

    const baseDraft: StudyPlanPreviewRequest = {
      goal_text: goalText.trim(),
      start_date: startDate,
      end_date: endDate,
      daily_available_minutes: minutes,
      preference: defaultPreference,
      material_scope: defaultScope,
    };

    if (diagnosticProfile) {
      return {
        ...baseDraft,
        diagnostic_profile: diagnosticProfile,
      };
    }

    return baseDraft;
  }, [dailyMinutes, diagnosticProfile, endDate, goalText, startDate]);

  function validationMessage(): string | null {
    if (!goalText.trim()) {
      return "请先填写学习目标。";
    }
    if (!startDate || !endDate) {
      return "请填写开始日期和结束日期。";
    }
    if (startDate > endDate) {
      return "结束日期不能早于开始日期。";
    }
    const minutes = Number.parseInt(dailyMinutes, 10);
    if (Number.isNaN(minutes) || minutes < minimumDailyMinutes) {
      return `每日时长至少需要 ${minimumDailyMinutes} 分钟。`;
    }
    return null;
  }

  function updateField(next: () => void) {
    next();
    if (preview) {
      setIsPreviewStale(true);
    }
  }

  function updateGoalText(nextGoalText: string) {
    updateField(() => {
      setGoalText(nextGoalText);
      setDiagnosticProfile(null);
    });
  }

  function handleDiagnosticProfileReady(nextProfile: StudyPlanDiagnosticProfile) {
    setDiagnosticProfile(nextProfile);
    if (preview) {
      setIsPreviewStale(true);
    }
  }

  function handleDiagnosticProfileCleared() {
    setDiagnosticProfile(null);
    if (preview) {
      setIsPreviewStale(true);
    }
  }

  async function handlePreview() {
    if (!courseId) {
      return;
    }

    const message = validationMessage();
    if (message || !draft) {
      setError(message ?? "计划配置不完整");
      return;
    }

    setIsPreviewing(true);
    setError(null);

    try {
      const nextPreview = await previewStudyPlan(courseId, draft);
      setPreview(nextPreview);
      setPreviewSnapshot(draft);
      setPreviewSaveIdempotencyKey(createStudyPlanIdempotencyKey(courseId));
      setIsPreviewStale(false);
    } catch (nextError) {
      setError(errorMessage(nextError, "生成预览失败"));
    } finally {
      setIsPreviewing(false);
    }
  }

  async function handleSave() {
    if (!courseId || !previewSnapshot || !preview || !previewSaveIdempotencyKey || isPreviewStale) {
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const result = await saveStudyPlan(
        courseId,
        {
          ...previewSnapshot,
          title: preview.title,
          client_flow: "wizard_v1",
          tasks: preview.tasks,
        },
        previewSaveIdempotencyKey,
      );
      navigate(`/courses/${courseId}/study-plans/${result.plan.id}`, { replace: true });
    } catch (nextError) {
      setError(errorMessage(nextError, "保存计划失败"));
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoadingCourse) {
    return (
      <Box className="study-plan-page">
        <Box className="study-plan-shell">
          <Skeleton height={36} width={280} />
          <Skeleton height={520} radius="md" />
        </Box>
      </Box>
    );
  }

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
          <Badge color="orange" variant="light">自动解析后续接入</Badge>
        </Group>

        <Group align="flex-start" className="study-plan-header" justify="space-between">
          <Stack gap={4}>
            <Text c="dimmed" size="sm">{course?.name ?? "课程"}</Text>
            <Title order={1}>创建学习计划</Title>
            <Text c="dimmed">
              先由用户手动填写基础配置，再调用真实 preview。保存会提交已确认的预览任务树。
            </Text>
          </Stack>
          <Badge color="teal" size="lg" variant="light">契约稳定版</Badge>
        </Group>

        {error ? (
          <Alert color="red" role="alert" title="学习计划处理失败" variant="light">
            {error}
          </Alert>
        ) : null}

        {isPreviewStale ? (
          <Alert color="yellow" role="status" title="预览已过期" variant="light">
            配置已修改，请重新生成预览后保存。
          </Alert>
        ) : null}

        <Box className="study-plan-grid">
          <Paper className="study-plan-panel" radius="md" withBorder>
            <Group justify="space-between" wrap="nowrap">
              <Stack gap={2}>
                <Title order={2}>计划配置</Title>
                <Text c="dimmed" size="sm">当前使用“均衡学习”策略，保存会提交已确认的预览任务树。</Text>
              </Stack>
              <Badge color="orange" variant="outline">学情诊断后续接入</Badge>
            </Group>

            <Textarea
              label="学习目标"
              minRows={5}
              onChange={(event) => updateGoalText(event.currentTarget.value)}
              placeholder="例如：三天完成线性代数第一章复习，重点理解向量空间和矩阵秩。"
              value={goalText}
            />
            <Text c="dimmed" size="sm">保存为学习目标，并随请求发送默认“均衡学习”策略。</Text>

            <Group align="flex-start" grow>
              <TextInput
                label="开始日期"
                onChange={(event) => updateField(() => setStartDate(event.currentTarget.value))}
                type="date"
                value={startDate}
              />
              <TextInput
                label="结束日期"
                onChange={(event) => updateField(() => setEndDate(event.currentTarget.value))}
                type="date"
                value={endDate}
              />
            </Group>

            <TextInput
              label="每日可用学习时长"
              min={minimumDailyMinutes}
              onChange={(event) => updateField(() => setDailyMinutes(event.currentTarget.value))}
              placeholder="60"
              rightSection={<Text c="dimmed" size="xs">分钟</Text>}
              type="number"
              value={dailyMinutes}
            />

            <Paper className="study-plan-scope" radius="md" withBorder>
              <Group justify="space-between" wrap="nowrap">
                <Stack gap={2}>
                  <Text fw={750}>资料范围</Text>
                  <Text c="dimmed" size="sm">当前固定为全部已解析资料。</Text>
                </Stack>
                <Badge color="teal" variant="light">全部已解析资料</Badge>
              </Group>
              <Button disabled leftSection={<IconLock size={16} />} variant="light">
                选择具体资料（待接入）
              </Button>
            </Paper>

            <DiagnosticWizard
              courseId={courseId}
              goalText={goalText}
              materialScope={defaultScope}
              onProfileCleared={handleDiagnosticProfileCleared}
              onProfileReady={handleDiagnosticProfileReady}
              profile={diagnosticProfile}
            />

            <Divider />

            <Group justify="space-between">
              <Button
                leftSection={<IconRefresh size={16} />}
                loading={isPreviewing}
                onClick={handlePreview}
                variant="light"
              >
                生成预览
              </Button>
              <Button
                disabled={!previewSnapshot || !previewSaveIdempotencyKey || isPreviewStale}
                leftSection={<IconClipboardCheck size={16} />}
                loading={isSaving}
                onClick={handleSave}
              >
                保存计划
              </Button>
            </Group>
          </Paper>

          <Paper className="study-plan-panel" radius="md" withBorder>
            <Group justify="space-between" wrap="nowrap">
              <Stack gap={2}>
                <Title order={2}>计划预览</Title>
                <Text c="dimmed" size="sm">保存成功后进入计划详情页。</Text>
              </Stack>
            </Group>
            <StudyPlanPreviewPanel preview={preview} />
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}
