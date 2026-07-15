import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Divider,
  Group,
  Modal,
  Paper,
  Skeleton,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import {
  IconCalendarStats,
  IconClipboardCheck,
  IconRefresh,
  IconRotateClockwise,
  IconSend,
} from "@tabler/icons-react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { WorkbenchTopbar } from "../components/WorkbenchTopbar";
import { fetchCourse } from "../features/courses/api";
import { listMaterials } from "../features/materials/api";
import type { Material, MaterialScope } from "../features/materials/types";
import { StudyPlanTaskDescription } from "../features/study-plans/components/StudyPlanTaskDescription";
import {
  parseStudyPlanConfig,
  previewStudyPlan,
  saveStudyPlan,
} from "../features/study-plans/api";
import { DiagnosticWizard } from "../features/study-plans/components/DiagnosticWizard";
import { StudyPlanMaterialScopeSelector } from "../features/study-plans/components/StudyPlanMaterialScopeSelector";
import type {
  PlanPreference,
  StudyPlanDiagnosticProfile,
  StudyPlanPreview,
  StudyPlanPreviewRequest,
  StudyPlanPreviewSubtask,
} from "../features/study-plans/types";
import type { Course } from "../types/course";
import "./study-plan.css";

const defaultScope: MaterialScope = {
  include_all_parsed_materials: true,
  material_ids: [],
};
const defaultPreference = "balanced" as const;
const minimumDailyMinutes = 30;

interface StudyPlanCreateDraftStorage {
  goalText?: string;
  startDate?: string;
  endDate?: string;
  durationDays?: string;
  dailyMinutes?: string;
  preference?: PlanPreference;
  materialScope?: MaterialScope;
  diagnosticProfile?: StudyPlanDiagnosticProfile | null;
}

function createStudyPlanIdempotencyKey(courseId: string): string {
  const randomPart = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `study-plan-${courseId}-${randomPart}`;
}

function createDraftStorageKey(courseId: string): string {
  return `course-nexus:study-plan-create:${courseId}`;
}

function readCreateDraft(courseId: string): StudyPlanCreateDraftStorage | null {
  try {
    const rawDraft = window.localStorage.getItem(createDraftStorageKey(courseId));
    if (!rawDraft) {
      return null;
    }
    return JSON.parse(rawDraft) as StudyPlanCreateDraftStorage;
  } catch {
    window.localStorage.removeItem(createDraftStorageKey(courseId));
    return null;
  }
}

function writeCreateDraft(courseId: string, draft: StudyPlanCreateDraftStorage) {
  window.localStorage.setItem(createDraftStorageKey(courseId), JSON.stringify(draft));
}

function clearCreateDraft(courseId: string) {
  window.localStorage.removeItem(createDraftStorageKey(courseId));
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
}

const preferenceOptions: Array<{ value: PlanPreference; label: string }> = [
  { value: "fast_track", label: "快速通关" },
  { value: "balanced", label: "均衡学习" },
  { value: "mastery", label: "深入掌握" },
  { value: "sprint", label: "冲刺强化" },
];

const preferenceLabels: Record<PlanPreference, string> = {
  fast_track: "快速通关",
  balanced: "均衡学习",
  mastery: "深入掌握",
  sprint: "冲刺强化",
};

const durationDayOptions = [
  { label: "A. 2 天", value: "2" },
  { label: "B. 3 天", value: "3" },
  { label: "C. 7 天", value: "7" },
];

const unresolvedFieldLabels: Record<string, string> = {
  goal_text: "学习目标",
  start_date: "开始日期",
  duration_days: "学习天数",
  end_date: "结束日期",
};

const userEditableParseFields = new Set(Object.keys(unresolvedFieldLabels));

function resolveEndDate(startDate: string | null | undefined, durationDays: number | null | undefined): string | null {
  if (!startDate || !durationDays) {
    return null;
  }

  const [year, month, day] = startDate.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const parsedStartTime = Date.UTC(year, month - 1, day);
  if (Number.isNaN(parsedStartTime)) {
    return null;
  }

  const endTime = parsedStartTime + (durationDays - 1) * 86_400_000;
  return new Date(endTime).toISOString().slice(0, 10);
}

function resolveDurationDays(startDate: string, endDate: string): number | null {
  if (!startDate || !endDate) {
    return null;
  }

  const [startYear, startMonth, startDay] = startDate.split("-").map(Number);
  const [endYear, endMonth, endDay] = endDate.split("-").map(Number);
  if (!startYear || !startMonth || !startDay || !endYear || !endMonth || !endDay) {
    return null;
  }

  const startTime = Date.UTC(startYear, startMonth - 1, startDay);
  const endTime = Date.UTC(endYear, endMonth - 1, endDay);
  if (Number.isNaN(startTime) || Number.isNaN(endTime)) {
    return null;
  }

  return Math.floor((endTime - startTime) / 86_400_000) + 1;
}

function formatCalendarDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addCalendarDays(date: Date, days: number): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

function nextMonday(date: Date): Date {
  const dayOfWeek = date.getDay();
  if (dayOfWeek === 0) {
    return addCalendarDays(date, 8);
  }
  const daysUntilNextMonday = ((8 - dayOfWeek) % 7) || 7;
  return addCalendarDays(date, daysUntilNextMonday);
}

function buildStartDateOptions(today = new Date()) {
  const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const tomorrow = addCalendarDays(todayDate, 1);
  const monday = nextMonday(todayDate);

  return [
    { label: `A. 今天（${formatCalendarDate(todayDate)}）`, value: formatCalendarDate(todayDate) },
    { label: `B. 明天（${formatCalendarDate(tomorrow)}）`, value: formatCalendarDate(tomorrow) },
    { label: `C. 下周一（${formatCalendarDate(monday)}）`, value: formatCalendarDate(monday) },
  ];
}

function studyPlanActionErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      NO_PARSED_MATERIAL: "当前资料还没有可用解析结果，请先上传或等待至少一份资料解析完成。",
      MATERIAL_COVERAGE_INCOMPLETE: "资料覆盖还不完整，请调整资料范围或稍后重新生成预览。",
      PREVIEW_TASKS_REQUIRED: "预览任务已失效，请重新生成预览后再保存。",
      IDEMPOTENCY_CONFLICT: "本次保存请求与之前的预览不一致，请重新生成预览后再保存。",
      STATE_CONFLICT: "学习计划状态已变化，请刷新后再试。",
      UNAUTHORIZED: "登录已过期，请重新登录。",
    };
    return messages[error.code] ?? error.message;
  }

  return errorMessage(error, fallback);
}

function hasResolvedEditableValue(fieldName: string, values: {
  goalText: string;
  startDate: string;
  endDate: string;
  dailyMinutes: string;
  preference: PlanPreference;
}) {
  switch (fieldName) {
    case "goal_text":
      return values.goalText.trim().length > 0;
    case "start_date":
      return values.startDate.length > 0;
    case "duration_days":
      return Boolean(resolveDurationDays(values.startDate, values.endDate));
    case "end_date":
      return values.endDate.length > 0;
    case "daily_available_minutes": {
      const minutes = Number.parseInt(values.dailyMinutes, 10);
      return !Number.isNaN(minutes) && minutes >= minimumDailyMinutes;
    }
    case "preference":
      return values.preference.length > 0;
    default:
      return false;
  }
}

function visibleUnresolvedFields(fields: string[], values: {
  goalText: string;
  startDate: string;
  endDate: string;
  dailyMinutes: string;
  preference: PlanPreference;
}) {
  return fields.filter((fieldName) => (
    userEditableParseFields.has(fieldName) && !hasResolvedEditableValue(fieldName, values)
  ));
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
      <Stack gap={8}>
        <Group align="flex-start" className="study-plan-subtask-header" justify="space-between" wrap="nowrap">
          <Text fw={700}>{subtask.title}</Text>
          <Badge className="study-plan-type-badge" color={subtaskTone(subtask.subtask_type)} variant="light">
            {subtaskTypeLabel(subtask.subtask_type)}
          </Badge>
        </Group>
        <StudyPlanTaskDescription description={subtask.description} />
      </Stack>
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
            输入目标、选择资料并完成诊断后，再生成可确认的学习任务安排。
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
            {preview.start_date} - {preview.end_date} / 每日建议 {preview.daily_available_minutes} 分钟
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
  const [durationDaysText, setDurationDaysText] = useState("");
  const [dailyMinutes, setDailyMinutes] = useState("");
  const [preference, setPreference] = useState<PlanPreference>(defaultPreference);
  const [materialScope, setMaterialScope] = useState<MaterialScope>(defaultScope);
  const [isCustomStartDateOpen, setIsCustomStartDateOpen] = useState(false);
  const [isCustomDurationDaysOpen, setIsCustomDurationDaysOpen] = useState(false);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [diagnosticProfile, setDiagnosticProfile] = useState<StudyPlanDiagnosticProfile | null>(null);
  const [preview, setPreview] = useState<StudyPlanPreview | null>(null);
  const [previewSnapshot, setPreviewSnapshot] = useState<StudyPlanPreviewRequest | null>(null);
  const [previewSaveIdempotencyKey, setPreviewSaveIdempotencyKey] = useState<string | null>(null);
  const [unresolvedFields, setUnresolvedFields] = useState<string[]>([]);
  const [isParsingConfig, setIsParsingConfig] = useState(false);
  const [isPreviewStale, setIsPreviewStale] = useState(false);
  const [isLoadingCourse, setIsLoadingCourse] = useState(true);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingMaterials, setIsLoadingMaterials] = useState(false);
  const [hasLoadedMaterials, setHasLoadedMaterials] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [isDraftHydrated, setIsDraftHydrated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materialsError, setMaterialsError] = useState<string | null>(null);
  const startDateRef = useRef("");
  const startDateOptions = useMemo(() => buildStartDateOptions(), []);

  useEffect(() => {
    if (!courseId) {
      setIsDraftHydrated(true);
      return;
    }

    const storedDraft = readCreateDraft(courseId);
    setGoalText(storedDraft?.goalText ?? "");
    setStartDate(storedDraft?.startDate ?? "");
    startDateRef.current = storedDraft?.startDate ?? "";
    setEndDate(storedDraft?.endDate ?? "");
    setDurationDaysText(
      storedDraft?.durationDays ??
      (
        storedDraft?.startDate && storedDraft?.endDate
          ? String(resolveDurationDays(storedDraft.startDate, storedDraft.endDate) ?? "")
          : ""
      ),
    );
    setDailyMinutes(storedDraft?.dailyMinutes ?? "");
    setPreference(storedDraft?.preference ?? defaultPreference);
    setMaterialScope(storedDraft?.materialScope ?? defaultScope);
    setDiagnosticProfile(storedDraft?.diagnosticProfile ?? null);
    setPreview(null);
    setPreviewSnapshot(null);
    setPreviewSaveIdempotencyKey(null);
    setUnresolvedFields([]);
    setIsPreviewStale(false);
    setIsDraftHydrated(true);
  }, [courseId]);

  useEffect(() => {
    if (!courseId || !isDraftHydrated) {
      return;
    }

    writeCreateDraft(courseId, {
      goalText,
      startDate,
      endDate,
      durationDays: durationDaysText,
      dailyMinutes,
      preference,
      materialScope,
      diagnosticProfile,
    });
  }, [
    courseId,
    dailyMinutes,
    diagnosticProfile,
    durationDaysText,
    endDate,
    goalText,
    isDraftHydrated,
    materialScope,
    preference,
    startDate,
  ]);

  useEffect(() => {
    const durationDays = Number.parseInt(durationDaysText, 10);
    const nextEndDate = startDate && !Number.isNaN(durationDays) && durationDays > 0
      ? resolveEndDate(startDate, durationDays) ?? ""
      : "";

    if (nextEndDate !== endDate) {
      setEndDate(nextEndDate);
    }
  }, [durationDaysText, endDate, startDate]);

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

  useEffect(() => {
    let ignore = false;

    if (!courseId) {
      setMaterials([]);
      setMaterialsError(null);
      setIsLoadingMaterials(false);
      setHasLoadedMaterials(false);
      return;
    }

    setIsLoadingMaterials(true);
    setHasLoadedMaterials(false);
    setMaterialsError(null);
    listMaterials(courseId)
      .then((nextMaterials) => {
        if (!ignore) {
          setMaterials(Array.isArray(nextMaterials) ? nextMaterials : []);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setMaterials([]);
          setMaterialsError(errorMessage(nextError, "资料加载失败"));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsLoadingMaterials(false);
          setHasLoadedMaterials(true);
        }
      });

    return () => {
      ignore = true;
    };
  }, [courseId]);

  useEffect(() => {
    if (!hasLoadedMaterials || isLoadingMaterials || materialScope.include_all_parsed_materials) {
      return;
    }

    const parsedMaterialIds = materials
      .filter((material) => material.parse_status === "parsed")
      .map((material) => material.id);
    const nextMaterialIds = materialScope.material_ids.filter((id) => parsedMaterialIds.includes(id));

    if (nextMaterialIds.length === materialScope.material_ids.length) {
      return;
    }

    setMaterialScope(
      nextMaterialIds.length > 0
        ? { include_all_parsed_materials: false, material_ids: nextMaterialIds }
        : defaultScope,
    );
    setUnresolvedFields([]);
    setDiagnosticProfile(null);
    if (preview) {
      setIsPreviewStale(true);
    }
  }, [hasLoadedMaterials, isLoadingMaterials, materialScope, materials, preview]);

  const draft = useMemo<StudyPlanPreviewRequest | null>(() => {
    const minutes = Number.parseInt(dailyMinutes, 10);
    if (!goalText.trim()) {
      return null;
    }

    const baseDraft: StudyPlanPreviewRequest = {
      goal_text: goalText.trim(),
      preference,
      material_scope: materialScope,
    };

    if (startDate) {
      baseDraft.start_date = startDate;
    }
    if (endDate) {
      baseDraft.end_date = endDate;
    }
    if (!Number.isNaN(minutes) && minutes >= minimumDailyMinutes) {
      baseDraft.daily_available_minutes = minutes;
      baseDraft.daily_minutes_source = "user_text";
    }

    if (diagnosticProfile) {
      return {
        ...baseDraft,
        diagnostic_profile: diagnosticProfile,
      };
    }

    return baseDraft;
  }, [dailyMinutes, diagnosticProfile, endDate, goalText, materialScope, preference, startDate]);

  const confirmedConfig = useMemo(() => {
    const durationDays = resolveDurationDays(startDate, endDate);
    const minutes = Number.parseInt(dailyMinutes, 10);

    return {
      start_date: startDate || null,
      duration_days: durationDays && durationDays > 0 ? durationDays : null,
      preference,
      daily_available_minutes: !Number.isNaN(minutes) && minutes >= minimumDailyMinutes ? minutes : null,
      daily_minutes_source: !Number.isNaN(minutes) && minutes >= minimumDailyMinutes ? "user_text" as const : null,
    };
  }, [dailyMinutes, endDate, preference, startDate]);

  const parsedMaterialCount = materials.filter((material) => material.parse_status === "parsed").length;
  const hasUsableMaterialScope = materialScope.include_all_parsed_materials
    ? parsedMaterialCount > 0
    : materialScope.material_ids.length > 0;

  function validationMessage(): string | null {
    if (!goalText.trim()) {
      return "请先填写学习目标。";
    }
    if (!hasUsableMaterialScope) {
      return materialScope.include_all_parsed_materials
        ? "资料范围内没有可解析资料，请先上传或解析至少一份资料。"
        : "请选择至少一份已解析资料。";
    }
    if (!startDate || !endDate) {
      return "请先补齐学习时间。";
    }
    if (startDate > endDate) {
      return "结束日期不能早于开始日期。";
    }
    if (!diagnosticProfile) {
      return "请先完成学情诊断。";
    }
    return null;
  }

  function markFieldResolved(fieldName: string) {
    setUnresolvedFields((currentFields) => currentFields.filter((field) => field !== fieldName));
  }

  function updateField(next: () => void, resolvedField?: string) {
    next();
    if (resolvedField) {
      markFieldResolved(resolvedField);
    }
    if (preview) {
      setIsPreviewStale(true);
    }
  }

  function updateGoalText(nextGoalText: string) {
    updateField(() => {
      setGoalText(nextGoalText);
      setDiagnosticProfile(null);
    }, "goal_text");
  }

  function updateStartDate(nextStartDate: string) {
    updateField(() => {
      startDateRef.current = nextStartDate;
      setStartDate(nextStartDate);
      const currentDurationDays = Number.parseInt(durationDaysText, 10);
      setEndDate(
        nextStartDate && !Number.isNaN(currentDurationDays) && currentDurationDays > 0
          ? resolveEndDate(nextStartDate, currentDurationDays) ?? ""
          : "",
      );
    }, "start_date");
  }

  function updateDurationDays(nextDurationDaysText: string) {
    updateField(() => {
      setDurationDaysText(nextDurationDaysText);
      const nextDurationDays = Number.parseInt(nextDurationDaysText, 10);
      setEndDate(
        startDateRef.current && !Number.isNaN(nextDurationDays) && nextDurationDays > 0
          ? resolveEndDate(startDateRef.current, nextDurationDays) ?? ""
          : "",
      );
    }, "duration_days");
  }

  async function handleParseConfig() {
    if (!courseId) {
      return;
    }

    const trimmedGoalText = goalText.trim();
    if (!trimmedGoalText) {
      setError("请先输入一句学习目标，再解析配置。");
      return;
    }

    setIsParsingConfig(true);
    setError(null);

    try {
      const parsedConfig = await parseStudyPlanConfig(courseId, {
        goal_text: trimmedGoalText,
        material_scope: materialScope,
      });
      const nextEndDate = parsedConfig.end_date ?? resolveEndDate(parsedConfig.start_date, parsedConfig.duration_days);

      const nextGoalText = parsedConfig.goal_text ?? goalText;
      const nextStartDate = parsedConfig.start_date ?? startDate;
      const nextEndDateValue = nextEndDate ?? endDate;
      const nextDailyMinutes = parsedConfig.daily_available_minutes
        ? String(parsedConfig.daily_available_minutes)
        : dailyMinutes;
      const nextPreference = parsedConfig.preference ?? preference;
      const nextDurationDays = nextStartDate && nextEndDateValue
        ? resolveDurationDays(nextStartDate, nextEndDateValue)
        : parsedConfig.duration_days;

      if (parsedConfig.goal_text) {
        setGoalText(parsedConfig.goal_text);
        if (parsedConfig.goal_text.trim() !== goalText.trim()) {
          setDiagnosticProfile(null);
        }
      }
      if (parsedConfig.start_date) {
        startDateRef.current = parsedConfig.start_date;
        setStartDate(parsedConfig.start_date);
      }
      if (nextEndDate) {
        setEndDate(nextEndDate);
      }
      setDurationDaysText(nextDurationDays && nextDurationDays > 0 ? String(nextDurationDays) : "");
      if (parsedConfig.daily_available_minutes) {
        setDailyMinutes(String(parsedConfig.daily_available_minutes));
      }
      if (parsedConfig.preference) {
        setPreference(parsedConfig.preference);
      }
      setUnresolvedFields(visibleUnresolvedFields(parsedConfig.unresolved_fields, {
        goalText: nextGoalText,
        startDate: nextStartDate,
        endDate: nextEndDateValue,
        dailyMinutes: nextDailyMinutes,
        preference: nextPreference,
      }));
      if (preview) {
        setIsPreviewStale(true);
      }
    } catch (nextError) {
      setError(errorMessage(nextError, "解析配置失败"));
    } finally {
      setIsParsingConfig(false);
    }
  }

  function handleMaterialScopeChange(nextScope: MaterialScope) {
    setMaterialScope(nextScope);
    setUnresolvedFields([]);
    setDiagnosticProfile(null);
    if (preview) {
      setIsPreviewStale(true);
    }
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
      setIsPreviewModalOpen(true);
    } catch (nextError) {
      setError(studyPlanActionErrorMessage(nextError, "生成预览失败"));
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
      clearCreateDraft(courseId);
      navigate(`/courses/${courseId}/study-plans/${result.plan.id}`, { replace: true });
    } catch (nextError) {
      setError(studyPlanActionErrorMessage(nextError, "保存计划失败"));
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoadingCourse) {
    return (
      <Box className="study-plan-page workbench-page">
        <WorkbenchTopbar backFallbackTo={courseId ? `/courses/${courseId}` : "/"} pageName="创建学习计划" />
        <Box className="study-plan-shell" data-workbench-scroll="locked">
          <Skeleton height={36} width={280} />
          <Skeleton height={520} radius="md" />
        </Box>
      </Box>
    );
  }

  return (
    <Box className="study-plan-page workbench-page">
      <WorkbenchTopbar
        backFallbackTo={courseId ? `/courses/${courseId}` : "/"}
        contextName={course?.name ?? "课程"}
        meta={<Badge color="teal" variant="light">智能回填</Badge>}
        pageName="创建学习计划"
      />

      <Box className="study-plan-shell study-plan-create-shell" component="main" data-workbench-scroll="locked">
        {isPreviewStale ? (
          <Alert color="yellow" role="status" title="预览已过期" variant="light">
            配置已修改，请重新生成预览后保存。
          </Alert>
        ) : null}

        <Box className="study-plan-create-flow">
          <Paper className="study-plan-panel" radius="md" withBorder>
            <Group justify="space-between" wrap="nowrap">
              <Stack gap={2}>
                <Title order={2}>目标与资料</Title>
                <Text c="dimmed" size="sm">
                  写下你想完成的学习目标，再选择本次计划要参考的资料。
                </Text>
              </Stack>
              <Badge color="teal" variant="outline">目标输入</Badge>
            </Group>

            <Textarea
              label="学习目标"
              minRows={5}
              onChange={(event) => updateGoalText(event.currentTarget.value)}
              placeholder="例如：三天完成线性代数第一章复习，重点理解向量空间和矩阵秩。"
              value={goalText}
            />
            <Group justify="space-between" wrap="nowrap">
              <Text c="dimmed" size="sm">发送后会先识别目标信息，接着完成学情诊断。</Text>
              <Button
                data-testid="study-plan-parse-config"
                leftSection={<IconSend size={16} />}
                loading={isParsingConfig}
                onClick={handleParseConfig}
                variant="light"
              >
                发送目标
              </Button>
            </Group>

            {startDate || endDate || dailyMinutes || preference !== defaultPreference ? (
              <Paper className="study-plan-config-summary" radius="md" withBorder>
                <Group justify="space-between" wrap="nowrap">
                  <Stack gap={2}>
                    <Text fw={750}>已识别目标信息</Text>
                    <Text c="dimmed" size="sm">
                      {startDate && endDate ? `${startDate} - ${endDate}` : "时间将通过诊断继续确认"}
                      {" / "}
                      学习方式：{preferenceLabels[preference]}
                      {dailyMinutes ? ` / 每日 ${dailyMinutes} 分钟` : " / 每日时长由后端估算"}
                    </Text>
                  </Stack>
                </Group>
              </Paper>
            ) : null}

            {goalText.trim() && (!startDate || !endDate) ? (
              <Paper className="study-plan-config-summary" radius="md" withBorder>
                <Stack gap="sm">
                  <Stack gap={2}>
                    <Title order={3}>补齐学习时间</Title>
                    <Text c="dimmed" size="sm">
                      自然语言里没有识别出完整日期时，请按问题补齐缺失项，再生成计划预览。
                    </Text>
                  </Stack>
                  {!startDate ? (
                    <Box className="study-plan-date-question">
                      <Text fw={700}>你想从哪天开始学习？</Text>
                      <Group gap="xs" mt="xs">
                        {startDateOptions.map((option) => (
                          <Button
                            key={option.value}
                            onClick={() => updateStartDate(option.value)}
                            variant="light"
                          >
                            {option.label}
                          </Button>
                        ))}
                        <Button
                          onClick={() => setIsCustomStartDateOpen(true)}
                          variant={isCustomStartDateOpen ? "filled" : "light"}
                        >
                          D. 自定义开始日期
                        </Button>
                      </Group>
                      {isCustomStartDateOpen ? (
                        <TextInput
                          className="study-plan-date-custom-input"
                          label="自定义开始日期"
                          mt="sm"
                          onChange={(event) => updateStartDate(event.currentTarget.value)}
                          type="date"
                          value={startDate}
                        />
                      ) : null}
                    </Box>
                  ) : null}
                  {startDate && !endDate ? (
                    <Box className="study-plan-date-question">
                      <Text fw={700}>这次计划准备学几天？</Text>
                      <Group gap="xs" mt="xs">
                        {durationDayOptions.map((option) => (
                          <Button
                            key={option.value}
                            onClick={() => updateDurationDays(option.value)}
                            variant="light"
                          >
                            {option.label}
                          </Button>
                        ))}
                        <Button
                          onClick={() => setIsCustomDurationDaysOpen(true)}
                          variant={isCustomDurationDaysOpen ? "filled" : "light"}
                        >
                          D. 自定义学习天数
                        </Button>
                      </Group>
                      {isCustomDurationDaysOpen ? (
                        <Box className="study-plan-date-input study-plan-date-custom-input">
                          <Text component="label" htmlFor="study-plan-duration-days" size="sm">
                            自定义学习天数
                          </Text>
                          <input
                            data-testid="study-plan-duration-days"
                            id="study-plan-duration-days"
                            min={1}
                            onChange={(event) => updateDurationDays(event.currentTarget.value)}
                            placeholder="例如：5"
                            type="number"
                            value={durationDaysText}
                          />
                        </Box>
                      ) : null}
                    </Box>
                  ) : null}
                  {startDate && endDate ? (
                    <Text c="dimmed" size="sm">
                      已确认：{startDate} - {endDate}
                    </Text>
                  ) : null}
                </Stack>
              </Paper>
            ) : null}

            {unresolvedFields.length > 0 ? (
              <Alert color="yellow" role="status" title="仍需手动补齐" variant="light">
                <Stack gap={4}>
                  {unresolvedFields.map((fieldName) => (
                    <Text key={fieldName} size="sm">
                      {(unresolvedFieldLabels[fieldName] ?? fieldName)}：需手动补齐
                    </Text>
                  ))}
                </Stack>
              </Alert>
            ) : null}

            <StudyPlanMaterialScopeSelector
              error={materialsError}
              isLoading={isLoadingMaterials}
              materialScope={materialScope}
              materials={materials}
              onMaterialScopeChange={handleMaterialScopeChange}
            />

            <DiagnosticWizard
              confirmedConfig={confirmedConfig}
              courseId={courseId}
              goalText={goalText}
              materialScope={materialScope}
              onProfileCleared={handleDiagnosticProfileCleared}
              onProfileReady={handleDiagnosticProfileReady}
              profile={diagnosticProfile}
            />

            <Divider />

            <Group justify="space-between">
              <Button
                data-testid="study-plan-preview"
                leftSection={<IconRefresh size={16} />}
                loading={isPreviewing}
                onClick={handlePreview}
                variant="light"
              >
                生成计划预览
              </Button>
            </Group>

            {error ? (
              <Alert color="red" role="alert" title="学习计划处理失败" variant="light">
                {error}
              </Alert>
            ) : null}
          </Paper>
        </Box>

        <Modal
          centered
          className="study-plan-preview-modal"
          opened={isPreviewModalOpen}
          onClose={() => setIsPreviewModalOpen(false)}
          size="min(1080px, 94vw)"
          title="计划预览"
        >
          <Stack gap="md">
            {isPreviewStale ? (
              <Alert color="yellow" role="status" title="预览已过期" variant="light">
                配置已修改，请重新生成预览后保存。
              </Alert>
            ) : null}
            <StudyPlanPreviewPanel preview={preview} />
            <Divider />
            <Group justify="space-between">
              <Button
                data-testid="study-plan-regenerate-preview"
                leftSection={<IconRotateClockwise size={16} />}
                loading={isPreviewing}
                onClick={handlePreview}
                variant="light"
              >
                重新生成
              </Button>
              <Button
                data-testid="study-plan-save"
                disabled={!previewSnapshot || !previewSaveIdempotencyKey || isPreviewStale}
                leftSection={<IconClipboardCheck size={16} />}
                loading={isSaving}
                onClick={handleSave}
              >
                保存计划
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Box>
    </Box>
  );
}
