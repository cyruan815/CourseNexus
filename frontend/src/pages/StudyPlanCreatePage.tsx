import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  ActionIcon,
  Badge,
  Box,
  Button,
  Divider,
  Group,
  Paper,
  Radio,
  Skeleton,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconCalendarStats, IconChevronLeft, IconChevronRight, IconSend } from "@tabler/icons-react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { fetchCourse } from "../features/courses/api";
import { listMaterials } from "../features/materials/api";
import { isMaterialLearningReady, type Material, type MaterialScope } from "../features/materials/types";
import { StudyPlanMaterialScopeSelector } from "../features/study-plans/components/StudyPlanMaterialScopeSelector";
import {
  createDiagnosticProfile,
  fetchDiagnosticQuestions,
  parseStudyPlanConfig,
  previewStudyPlan,
  saveStudyPlan,
} from "../features/study-plans/api";
import type {
  MasteryLevel,
  PlanPreference,
  StudyPlanDiagnosticQuestion,
  StudyPlanPreview,
  StudyPlanPreviewRequest,
  StudyPlanSaveRequest,
  StudyPlanTopicMasteryAnswer,
  WeakArea,
} from "../features/study-plans/types";
import type { Course } from "../types/course";
import "./study-plan.css";

const defaultScope: MaterialScope = {
  include_all_parsed_materials: false,
  material_ids: [],
};
const defaultPreference = "balanced" as const;
const minimumDailyMinutes = 30;
const maximumPlanTitleLength = 255;
type StudyPlanCreatePhase = "goal" | "preparing" | "questionnaire" | "generating";

interface StudyPlanCreateDraftStorage {
  version?: 2;
  userId?: string;
  courseId?: string;
  goalText?: string;
  startDate?: string;
  endDate?: string;
  durationDays?: string;
  dailyMinutes?: string;
  preference?: PlanPreference;
  materialScope?: MaterialScope;
  materialSelection?: StudyPlanMaterialSelection[];
  pendingSaveAttempt?: StudyPlanPendingSaveAttempt;
}

interface StudyPlanMaterialSelection {
  id: string;
  name: string;
}

interface StudyPlanCreateLocationState {
  studyPlanMaterialSelection?: StudyPlanMaterialSelection[];
}

interface StudyPlanPendingSaveAttempt {
  idempotencyKey: string;
  payload: StudyPlanSaveRequest;
  preview: StudyPlanPreview;
  signature: string;
}

function createStudyPlanIdempotencyKey(courseId: string): string {
  const randomPart = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `study-plan-${courseId}-${randomPart}`;
}

function createLegacyDraftStorageKey(courseId: string): string {
  return `course-nexus:study-plan-create:${courseId}`;
}

function createDraftStorageKey(userId: string, courseId: string): string {
  return `course-nexus:study-plan-create:v2:${userId}:${courseId}`;
}

function readStoredDraft(storageKey: string): StudyPlanCreateDraftStorage | null {
  try {
    const rawDraft = window.localStorage.getItem(storageKey);
    if (!rawDraft) {
      return null;
    }
    return JSON.parse(rawDraft) as StudyPlanCreateDraftStorage;
  } catch {
    window.localStorage.removeItem(storageKey);
    return null;
  }
}

function isStudyPlanPendingSaveAttempt(value: unknown): value is StudyPlanPendingSaveAttempt {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.idempotencyKey === "string"
    && typeof candidate.signature === "string"
    && Boolean(candidate.payload)
    && typeof candidate.payload === "object"
    && Boolean(candidate.preview)
    && typeof candidate.preview === "object"
  );
}

function writeCreateDraft(userId: string, courseId: string, draft: StudyPlanCreateDraftStorage) {
  try {
    window.localStorage.setItem(createDraftStorageKey(userId, courseId), JSON.stringify({
      ...draft,
      version: 2,
      userId,
      courseId,
    }));
  } catch {
    // Draft persistence is best effort; storage limits must not block plan creation or retry in this session.
  }
}

function clearCreateDraft(userId: string, courseId: string) {
  window.localStorage.removeItem(createDraftStorageKey(userId, courseId));
  window.localStorage.removeItem(createLegacyDraftStorageKey(courseId));
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
}

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

const weekDayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const completionFlushMs = 520;

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

function monthTitle(date: Date): string {
  return date.toLocaleString("en-US", { month: "long", year: "numeric" });
}

function dateFromDateKey(dateKey: string | null | undefined): Date {
  if (!dateKey) {
    return new Date();
  }
  const [year, month, day] = dateKey.split("-").map(Number);
  if (!year || !month || !day) {
    return new Date();
  }
  return new Date(year, month - 1, day);
}

function buildMonthCells(referenceDate: Date) {
  const year = referenceDate.getFullYear();
  const month = referenceDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const leadingDays = firstDay.getDay();
  const lastDate = new Date(year, month + 1, 0).getDate();
  const previousMonthLastDate = new Date(year, month, 0).getDate();

  return Array.from({ length: 35 }, (_, index) => {
    const dayOffset = index - leadingDays + 1;
    if (dayOffset < 1) {
      return {
        day: previousMonthLastDate + dayOffset,
        dateKey: null,
        isCurrentMonth: false,
      };
    }
    if (dayOffset > lastDate) {
      return {
        day: dayOffset - lastDate,
        dateKey: null,
        isCurrentMonth: false,
      };
    }
    return {
      day: dayOffset,
      dateKey: formatCalendarDate(new Date(year, month, dayOffset)),
      isCurrentMonth: true,
    };
  });
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

function isMasteryLevel(value: string): value is MasteryLevel {
  return ["none", "heard", "some", "familiar"].includes(value);
}

function isWeakArea(value: string): value is WeakArea {
  return ["concept", "calculation", "application", "memorization", "other"].includes(value);
}

function sortDiagnosticQuestions(questions: StudyPlanDiagnosticQuestion[]) {
  return [...questions].sort((left, right) => left.sort_order - right.sort_order);
}

function StudyPlanQuestionnairePreparing() {
  return (
    <Box className="study-plan-preparing-card" role="status">
      <Stack className="study-plan-preparing-content" gap="lg">
        <Stack align="center" gap={6}>
          <Text c="teal" fw={800} size="sm">正在整理问卷</Text>
          <Title order={2} ta="center">把你的目标变成几个关键问题</Title>
          <Text c="dimmed" maw={520} size="sm" ta="center">正在读取课程资料和目标语义，很快进入问卷。</Text>
        </Stack>
      </Stack>
    </Box>
  );
}

function StudyPlanCalendarGeneration({
  endDate,
  generatedPreview,
  isComplete,
  onEnterPlan,
  onPlanTitleChange,
  onSavePlan,
  isSaving,
  planTitle,
  startDate,
}: {
  endDate: string;
  generatedPreview: StudyPlanPreview | null;
  isComplete: boolean;
  onEnterPlan: () => void;
  onPlanTitleChange: (title: string) => void;
  onSavePlan: () => void;
  isSaving: boolean;
  planTitle: string;
  startDate: string;
}) {
  const [referenceDate, setReferenceDate] = useState(() => dateFromDateKey(startDate));
  const monthCells = useMemo(() => buildMonthCells(referenceDate), [referenceDate]);
  const plannedDateSummaries = useMemo(() => {
    const summaries = new Map<string, { count: number; title: string }>();
    if (!generatedPreview) {
      return summaries;
    }
    for (const task of generatedPreview.tasks) {
      const current = summaries.get(task.task_date);
      summaries.set(task.task_date, {
        count: (current?.count ?? 0) + 1,
        title: current?.title ?? task.title,
      });
    }
    return summaries;
  }, [generatedPreview]);
  const normalizedTitle = planTitle.trim();
  const titleError = !normalizedTitle
    ? "计划名称不能为空"
    : normalizedTitle.length > maximumPlanTitleLength
      ? `计划名称不能超过 ${maximumPlanTitleLength} 个字符`
      : null;

  return (
    <Box className="study-plan-calendar-generation" role="status">
      <Stack gap="md">
        <Group align="flex-start" justify="space-between" wrap="nowrap">
          <Stack gap={4}>
            <Text c="teal" fw={800} size="sm">生成学习计划</Text>
            <Title order={2}>{generatedPreview ? (isComplete ? "学习计划已保存" : "确认计划名称") : "正在拆分每日任务"}</Title>
            <Text c="dimmed" size="sm">
              {generatedPreview ? "确认名称后再保存；日历中的任务将使用这次预览结果。" : "把诊断结果、资料范围和学习日期安排到日历里。"}
            </Text>
          </Stack>
          <IconCalendarStats className="study-plan-calendar-generation-icon" size={34} stroke={1.7} />
        </Group>

        <Box className="study-plan-calendar-card">
          <Group className="study-plan-calendar-card-header" justify="space-between" wrap="nowrap">
            <Text fw={800}>{monthTitle(referenceDate)}</Text>
            <Group gap={4} wrap="nowrap">
              <Button
                aria-label="上个月"
                className="study-plan-calendar-nav-button"
                onClick={() => setReferenceDate((current) => new Date(current.getFullYear(), current.getMonth() - 1, 1))}
                size="compact-sm"
                variant="subtle"
              >
                <IconChevronLeft size={16} />
              </Button>
              <Button
                aria-label="下个月"
                className="study-plan-calendar-nav-button"
                onClick={() => setReferenceDate((current) => new Date(current.getFullYear(), current.getMonth() + 1, 1))}
                size="compact-sm"
                variant="subtle"
              >
                <IconChevronRight size={16} />
              </Button>
            </Group>
          </Group>
          <Box className="study-plan-calendar-weekdays" aria-hidden="true">
            {weekDayLabels.map((label) => (
              <Text c="dimmed" component="span" key={label} size="xs">{label}</Text>
            ))}
          </Box>
          <Box aria-label="生成中的计划日历" className="study-plan-calendar-grid" role="grid">
            {monthCells.map((cell, index) => (
              (() => {
                const plannedSummary = cell.dateKey ? plannedDateSummaries.get(cell.dateKey) : undefined;
                return (
                  <Box
                    className={`study-plan-calendar-cell${cell.isCurrentMonth ? "" : " is-muted"}${plannedSummary ? " is-planned" : ""}`}
                    key={`${cell.dateKey ?? "muted"}-${cell.day}-${index}`}
                    role="gridcell"
                    style={{ animationDelay: `${index * 24}ms` }}
                  >
                    <span className="study-plan-calendar-day">{cell.day}</span>
                    <span className="study-plan-calendar-tags">
                      {plannedSummary ? (
                        <span className="study-plan-calendar-task is-planned">
                          {plannedSummary.title}
                          {plannedSummary.count > 1 ? ` +${plannedSummary.count - 1}` : ""}
                        </span>
                      ) : null}
                    </span>
                  </Box>
                );
              })()
            ))}
          </Box>
        </Box>

        {generatedPreview && !isComplete ? (
          <Stack gap="xs">
            <TextInput
              error={titleError}
              label="计划名称"
              maxLength={maximumPlanTitleLength + 1}
              onChange={(event) => onPlanTitleChange(event.currentTarget.value)}
              value={planTitle}
            />
            <Group justify="center">
              <Button disabled={Boolean(titleError)} loading={isSaving} onClick={onSavePlan}>保存学习计划</Button>
            </Group>
          </Stack>
        ) : null}

        {isComplete ? (
          <Group justify="center">
            <Button onClick={onEnterPlan}>进入计划</Button>
          </Group>
        ) : null}
      </Stack>
    </Box>
  );
}

function StudyPlanCreateNav({
  courseId,
  courseName,
  isBackDisabled,
  onBack,
}: {
  courseId: string | undefined;
  courseName: string;
  isBackDisabled: boolean;
  onBack: () => void;
}) {
  return (
    <Group className="study-plan-create-nav" justify="space-between" wrap="nowrap">
      <Group gap="sm" wrap="nowrap">
        <Button
          disabled={isBackDisabled}
          leftSection={<IconArrowLeft size={16} />}
          onClick={onBack}
          variant="subtle"
        >
          返回上一步
        </Button>
        <Text c="dimmed" size="sm">创建学习计划 / {courseName}</Text>
      </Group>
      <Button
        component={Link}
        to={courseId ? `/courses/${courseId}` : "/"}
        variant="default"
      >
        回到课程详情
      </Button>
    </Group>
  );
}

export function StudyPlanCreatePage() {
  const { courseId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [goalText, setGoalText] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [durationDaysText, setDurationDaysText] = useState("");
  const [dailyMinutes, setDailyMinutes] = useState("");
  const [preference, setPreference] = useState<PlanPreference>(defaultPreference);
  const [materialScope, setMaterialScope] = useState<MaterialScope>(defaultScope);
  const [materialSelection, setMaterialSelection] = useState<StudyPlanMaterialSelection[]>([]);
  const [isMaterialScopeOpen, setIsMaterialScopeOpen] = useState(false);
  const [requiresMaterialConfirmation, setRequiresMaterialConfirmation] = useState(false);
  const [isCustomStartDateOpen, setIsCustomStartDateOpen] = useState(false);
  const [isCustomDurationDaysOpen, setIsCustomDurationDaysOpen] = useState(false);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [phase, setPhase] = useState<StudyPlanCreatePhase>("goal");
  const [questionVersion, setQuestionVersion] = useState<"study_plan_diagnostic_v2" | null>(null);
  const [diagnosticQuestions, setDiagnosticQuestions] = useState<StudyPlanDiagnosticQuestion[]>([]);
  const [diagnosticAnswers, setDiagnosticAnswers] = useState<Record<string, string>>({});
  const [diagnosticNote, setDiagnosticNote] = useState("");
  const [unresolvedFields, setUnresolvedFields] = useState<string[]>([]);
  const [shouldShowDateFollowups, setShouldShowDateFollowups] = useState(false);
  const [isLoadingCourse, setIsLoadingCourse] = useState(true);
  const [isLoadingMaterials, setIsLoadingMaterials] = useState(false);
  const [hasLoadedMaterials, setHasLoadedMaterials] = useState(false);
  const [isDraftHydrated, setIsDraftHydrated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materialsError, setMaterialsError] = useState<string | null>(null);
  const [isGenerationComplete, setIsGenerationComplete] = useState(false);
  const [savedPlanId, setSavedPlanId] = useState<string | null>(null);
  const [generatedPlanPreview, setGeneratedPlanPreview] = useState<StudyPlanPreview | null>(null);
  const [pendingSaveAttempt, setPendingSaveAttempt] = useState<StudyPlanPendingSaveAttempt | null>(null);
  const [planTitle, setPlanTitle] = useState("");
  const [isSavingPlan, setIsSavingPlan] = useState(false);
  const startDateRef = useRef("");
  const isDraftPersistenceDisabledRef = useRef(false);
  const incomingMaterialSelectionRef = useRef(
    (location.state as StudyPlanCreateLocationState | null)?.studyPlanMaterialSelection,
  );
  const startDateOptions = useMemo(() => buildStartDateOptions(), []);

  useEffect(() => {
    if (!courseId || !course || !hasLoadedMaterials || isDraftHydrated) {
      return;
    }

    const storedDraft = readStoredDraft(createDraftStorageKey(course.user_id, courseId));
    const legacyDraft = storedDraft ? null : readStoredDraft(createLegacyDraftStorageKey(courseId));
    const draftToRestore = storedDraft ?? legacyDraft;
    const incomingSelection = incomingMaterialSelectionRef.current;
    const parsedMaterialsById = new Map(
      materials
        .filter(isMaterialLearningReady)
        .map((material) => [material.id, material]),
    );
    let nextSelection: StudyPlanMaterialSelection[];
    let needsConfirmation = false;

    if (Array.isArray(incomingSelection)) {
      nextSelection = incomingSelection.filter((item) => item && typeof item.id === "string" && typeof item.name === "string");
    } else if (draftToRestore?.materialSelection) {
      nextSelection = draftToRestore.materialSelection;
    } else if (legacyDraft?.materialScope?.include_all_parsed_materials) {
      nextSelection = [...parsedMaterialsById.values()].map((material) => ({ id: material.id, name: material.name }));
      needsConfirmation = true;
    } else {
      nextSelection = (draftToRestore?.materialScope?.material_ids ?? []).map((id) => ({
        id,
        name: parsedMaterialsById.get(id)?.name ?? "已失效资料",
      }));
    }

    isDraftPersistenceDisabledRef.current = false;
    setGoalText(draftToRestore?.goalText ?? "");
    setStartDate(draftToRestore?.startDate ?? "");
    startDateRef.current = draftToRestore?.startDate ?? "";
    setEndDate(draftToRestore?.endDate ?? "");
    setDurationDaysText(
      draftToRestore?.durationDays ??
      (
        draftToRestore?.startDate && draftToRestore?.endDate
          ? String(resolveDurationDays(draftToRestore.startDate, draftToRestore.endDate) ?? "")
          : ""
      ),
    );
    setDailyMinutes(draftToRestore?.dailyMinutes ?? "");
    setPreference(draftToRestore?.preference ?? defaultPreference);
    setMaterialSelection(nextSelection);
    setMaterialScope({ include_all_parsed_materials: false, material_ids: nextSelection.map((item) => item.id) });
    setRequiresMaterialConfirmation(needsConfirmation);
    setPendingSaveAttempt(
      isStudyPlanPendingSaveAttempt(draftToRestore?.pendingSaveAttempt)
        ? draftToRestore.pendingSaveAttempt
        : null,
    );
    setPhase("goal");
    setQuestionVersion(null);
    setDiagnosticQuestions([]);
    setDiagnosticAnswers({});
    setDiagnosticNote("");
    setUnresolvedFields([]);
    setShouldShowDateFollowups(false);
    setIsDraftHydrated(true);
  }, [course, courseId, hasLoadedMaterials, isDraftHydrated, materials]);

  useEffect(() => {
    if (!courseId || !course || !isDraftHydrated || isDraftPersistenceDisabledRef.current) {
      return;
    }

    writeCreateDraft(course.user_id, courseId, {
      goalText,
      startDate,
      endDate,
      durationDays: durationDaysText,
      dailyMinutes,
      preference,
      materialScope,
      materialSelection,
      pendingSaveAttempt: pendingSaveAttempt ?? undefined,
    });
    window.localStorage.removeItem(createLegacyDraftStorageKey(courseId));
  }, [
    course,
    courseId,
    dailyMinutes,
    durationDaysText,
    endDate,
    goalText,
    isDraftHydrated,
    materialScope,
    materialSelection,
    pendingSaveAttempt,
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

    return baseDraft;
  }, [dailyMinutes, endDate, goalText, materialScope, preference, startDate]);

  const parsedMaterialIds = useMemo(
    () => new Set(materials.filter(isMaterialLearningReady).map((material) => material.id)),
    [materials],
  );
  const invalidMaterialIds = materialScope.material_ids.filter((id) => !parsedMaterialIds.has(id));
  const hasUsableMaterialScope = materialScope.material_ids.length > 0
    && invalidMaterialIds.length === 0
    && !requiresMaterialConfirmation;
  const selectedMaterialNames = materialSelection.map((item) => item.name);
  const orderedDiagnosticQuestions = useMemo(
    () => sortDiagnosticQuestions(diagnosticQuestions),
    [diagnosticQuestions],
  );
  const startDateChoiceValue = useMemo(() => {
    if (isCustomStartDateOpen) {
      return "custom";
    }
    if (!startDate) {
      return "";
    }
    return startDateOptions.some((option) => option.value === startDate) ? startDate : "custom";
  }, [isCustomStartDateOpen, startDate, startDateOptions]);
  const durationDaysChoiceValue = useMemo(() => {
    if (isCustomDurationDaysOpen) {
      return "custom";
    }
    if (!durationDaysText) {
      return "";
    }
    return durationDayOptions.some((option) => option.value === durationDaysText) ? durationDaysText : "custom";
  }, [durationDaysText, isCustomDurationDaysOpen]);
  const canSubmitQuestionnaire = useMemo(() => {
    if (!questionVersion || orderedDiagnosticQuestions.length === 0 || !startDate || !endDate) {
      return false;
    }

    return orderedDiagnosticQuestions.every((question) => {
      if (!question.required || question.question_type === "diagnostic_note") {
        return true;
      }
      return Boolean(diagnosticAnswers[question.question_id]);
    });
  }, [diagnosticAnswers, endDate, orderedDiagnosticQuestions, questionVersion, startDate]);

  function markFieldResolved(fieldName: string) {
    setUnresolvedFields((currentFields) => currentFields.filter((field) => field !== fieldName));
  }

  function updateField(next: () => void, resolvedField?: string) {
    next();
    if (resolvedField) {
      markFieldResolved(resolvedField);
    }
  }

  function updateGoalText(nextGoalText: string) {
    updateField(() => {
      if (nextGoalText !== goalText) {
        startDateRef.current = "";
        setStartDate("");
        setEndDate("");
        setDurationDaysText("");
        setDailyMinutes("");
        setPreference(defaultPreference);
        setShouldShowDateFollowups(false);
      }
      setGoalText(nextGoalText);
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

  function updateMaterialScope(nextScope: MaterialScope) {
    const nextIds = nextScope.material_ids;
    const nextSelection = nextIds.flatMap((id) => {
      const material = materials.find((item) => item.id === id && isMaterialLearningReady(item));
      return material ? [{ id: material.id, name: material.name }] : [];
    });
    setMaterialScope({ include_all_parsed_materials: false, material_ids: nextSelection.map((item) => item.id) });
    setMaterialSelection(nextSelection);
    setRequiresMaterialConfirmation(false);
    setPendingSaveAttempt(null);
    setUnresolvedFields([]);
    setShouldShowDateFollowups(false);
  }

  function confirmMaterialScope() {
    updateMaterialScope(materialScope);
    setIsMaterialScopeOpen(false);
  }

  async function handleGoalSubmit() {
    if (!courseId) {
      return;
    }

    const trimmedGoalText = goalText.trim();
    if (!trimmedGoalText) {
      setError("请先输入一句学习目标。");
      return;
    }
    if (!hasUsableMaterialScope) {
      if (invalidMaterialIds.length > 0) {
        setError("所选资料已被删除、失效或尚未解析，请调整并重新确认资料范围。");
      } else if (requiresMaterialConfirmation) {
        setError("旧草稿的“全部资料”没有历史快照，请确认本次实际使用的资料。");
      } else {
        setError("请选择至少一份已解析资料。");
      }
      return;
    }

    setPhase("preparing");
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
      const nextUnresolvedFields = visibleUnresolvedFields(parsedConfig.unresolved_fields, {
        goalText: nextGoalText,
        startDate: nextStartDate,
        endDate: nextEndDateValue,
        dailyMinutes: nextDailyMinutes,
        preference: nextPreference,
      });
      setUnresolvedFields(nextUnresolvedFields);
      setShouldShowDateFollowups(nextUnresolvedFields.some((fieldName) => (
        fieldName === "start_date" || fieldName === "duration_days" || fieldName === "end_date"
      )));

      const nextConfirmedConfig = {
        start_date: nextStartDate || null,
        duration_days: nextDurationDays && nextDurationDays > 0 ? nextDurationDays : null,
        preference: nextPreference,
        daily_available_minutes: (() => {
          const minutes = Number.parseInt(nextDailyMinutes, 10);
          return !Number.isNaN(minutes) && minutes >= minimumDailyMinutes ? minutes : null;
        })(),
        daily_minutes_source: (() => {
          const minutes = Number.parseInt(nextDailyMinutes, 10);
          return !Number.isNaN(minutes) && minutes >= minimumDailyMinutes ? "user_text" as const : null;
        })(),
      };
      const questionsResponse = await fetchDiagnosticQuestions(courseId, {
        goal_text: (parsedConfig.goal_text ?? trimmedGoalText).trim(),
        material_scope: materialScope,
        confirmed_config: nextConfirmedConfig,
      });
      setQuestionVersion(questionsResponse.question_version);
      setDiagnosticQuestions(questionsResponse.questions);
      setDiagnosticAnswers({});
      setDiagnosticNote("");
      window.setTimeout(() => {
        setPhase("questionnaire");
      }, completionFlushMs);
    } catch (nextError) {
      setError(studyPlanActionErrorMessage(nextError, "生成问卷失败"));
      setPhase("goal");
    }
  }

  async function handleQuestionnaireSubmit() {
    if (!courseId || !questionVersion || !canSubmitQuestionnaire) {
      return;
    }

    const topicMastery: StudyPlanTopicMasteryAnswer[] = orderedDiagnosticQuestions
      .filter((question) => question.question_type === "topic_mastery")
      .flatMap((question) => {
        const answer = diagnosticAnswers[question.question_id];
        if (!question.topic_id || !question.topic_title || !answer || !isMasteryLevel(answer)) {
          return [];
        }
        return [{
          topic_id: question.topic_id,
          topic_title: question.topic_title,
          mastery_level: answer,
        }];
      });
    const weakAreaAnswer = orderedDiagnosticQuestions
      .filter((question) => question.question_type === "weak_area")
      .map((question) => diagnosticAnswers[question.question_id])
      .find((answer): answer is WeakArea => Boolean(answer) && isWeakArea(answer));

    if (!weakAreaAnswer) {
      setError("请选择最担心的学习薄弱点。");
      return;
    }

    if (!draft || !goalText.trim() || !hasUsableMaterialScope || !startDate || !endDate || startDate > endDate) {
      setError("问卷信息不完整，请补齐后再提交。");
      return;
    }

    setPhase("generating");
    setError(null);
    setIsGenerationComplete(false);
    setSavedPlanId(null);
    setGeneratedPlanPreview(null);
    setPlanTitle("");
    setPendingSaveAttempt(null);

    try {
      const nextProfile = await createDiagnosticProfile(courseId, {
        question_version: questionVersion,
        topic_mastery: topicMastery,
        weak_area: weakAreaAnswer,
        diagnostic_note: diagnosticNote.trim() || null,
        material_scope: materialScope,
      });
      const previewRequest: StudyPlanPreviewRequest = {
        ...draft,
        diagnostic_profile: nextProfile,
      };
      const nextPreview = await previewStudyPlan(courseId, previewRequest);
      setGeneratedPlanPreview(nextPreview);
      setPlanTitle(nextPreview.title);
    } catch (nextError) {
      setError(studyPlanActionErrorMessage(nextError, "生成学习计划失败"));
      setPhase("questionnaire");
      setIsGenerationComplete(false);
      setSavedPlanId(null);
      setGeneratedPlanPreview(null);
    }
  }

  async function handleSaveGeneratedPlan() {
    if (!courseId || !course || !draft || !generatedPlanPreview) {
      return;
    }

    const normalizedTitle = planTitle.trim();
    if (!normalizedTitle) {
      setError("计划名称不能为空。");
      return;
    }
    if (normalizedTitle.length > maximumPlanTitleLength) {
      setError(`计划名称不能超过 ${maximumPlanTitleLength} 个字符。`);
      return;
    }

    const payload: StudyPlanSaveRequest = {
      ...draft,
      diagnostic_profile: generatedPlanPreview.diagnostic_profile,
      title: normalizedTitle,
      client_flow: "wizard_v1",
      tasks: generatedPlanPreview.tasks,
    };
    const signature = JSON.stringify(payload);
    const saveAttempt = pendingSaveAttempt?.signature === signature
      ? pendingSaveAttempt
      : {
          idempotencyKey: createStudyPlanIdempotencyKey(courseId),
          payload,
          preview: generatedPlanPreview,
          signature,
        };
    setPendingSaveAttempt(saveAttempt);
    setIsSavingPlan(true);
    setError(null);

    try {
      const result = await saveStudyPlan(courseId, saveAttempt.payload, saveAttempt.idempotencyKey);
      isDraftPersistenceDisabledRef.current = true;
      clearCreateDraft(course.user_id, courseId);
      setSavedPlanId(result.plan.id);
      setIsGenerationComplete(true);
    } catch (nextError) {
      if (nextError instanceof ApiError && nextError.code === "IDEMPOTENCY_CONFLICT") {
        setPendingSaveAttempt(null);
      }
      setError(studyPlanActionErrorMessage(nextError, "保存学习计划失败"));
    } finally {
      setIsSavingPlan(false);
    }
  }

  function handleEnterGeneratedPlan() {
    if (!courseId || !savedPlanId) {
      return;
    }

    if (course) {
      clearCreateDraft(course.user_id, courseId);
    }
    navigate(`/courses/${courseId}/study-plans/${savedPlanId}`, { replace: true });
  }

  function handleStepBack() {
    if (phase === "questionnaire") {
      setPhase("goal");
      setQuestionVersion(null);
      setDiagnosticQuestions([]);
      setDiagnosticAnswers({});
      setDiagnosticNote("");
      setShouldShowDateFollowups(false);
      setError(null);
      setIsGenerationComplete(false);
      setSavedPlanId(null);
      setGeneratedPlanPreview(null);
      setPendingSaveAttempt(null);
      setPlanTitle("");
    }
  }

  if (isLoadingCourse) {
    return (
      <Box className="study-plan-page workbench-page">
        <Box className="study-plan-shell" data-workbench-scroll="locked">
          <StudyPlanCreateNav
            courseId={courseId}
            courseName="课程"
            isBackDisabled
            onBack={handleStepBack}
          />
          <Skeleton height={36} width={280} />
          <Skeleton height={520} radius="md" />
        </Box>
      </Box>
    );
  }

  return (
    <Box className="study-plan-page workbench-page">
      <Box className="study-plan-shell study-plan-create-shell is-centered-flow" component="main" data-workbench-scroll="locked">
        <StudyPlanCreateNav
          courseId={courseId}
          courseName={course?.name ?? "课程"}
          isBackDisabled={phase !== "questionnaire"}
          onBack={handleStepBack}
        />
        <Box className="study-plan-create-flow">
          <Paper
            className={`study-plan-panel${phase === "goal" ? " study-plan-goal-card" : ""}${phase === "questionnaire" ? " study-plan-questionnaire-card" : ""}${phase === "preparing" || phase === "generating" ? " study-plan-process-panel" : ""}${phase === "preparing" ? " study-plan-preparing-panel" : ""}${phase === "generating" ? " study-plan-generating-panel" : ""}`}
            radius="md"
            withBorder
          >
            {phase === "goal" ? (
              <Stack className="study-plan-goal-content" gap="lg">
                <Stack align="center" gap={6}>
                  <Title order={2} ta="center">想生成什么学习计划？</Title>
                  <Text c="dimmed" maw={520} size="sm" ta="center">
                    用一句话告诉我目标，后面会自动生成问卷和学习计划。
                  </Text>
                </Stack>
                <Textarea
                  aria-label="学习目标"
                  className="study-plan-goal-input"
                  minRows={8}
                  onChange={(event) => updateGoalText(event.currentTarget.value)}
                  placeholder="例如：三天完成线性代数第一章复习，重点理解向量空间和矩阵秩。"
                  value={goalText}
                />
                <Paper className="study-plan-material-summary" p="md" radius="md" withBorder>
                  <Stack gap="sm">
                    <Group justify="space-between" wrap="nowrap">
                      <Stack gap={2}>
                        <Text fw={750}>本次使用的课程资料</Text>
                        <Text c="dimmed" size="sm">
                          {selectedMaterialNames.length > 0
                            ? `已选 ${selectedMaterialNames.length} 份：${selectedMaterialNames.join("、")}`
                            : "尚未选择资料"}
                        </Text>
                      </Stack>
                      <Button onClick={() => setIsMaterialScopeOpen((open) => !open)} size="xs" variant="light">
                        {isMaterialScopeOpen ? "收起" : "调整资料"}
                      </Button>
                    </Group>
                    {invalidMaterialIds.length > 0 ? (
                      <Alert color="red" role="alert" variant="light">
                        有 {invalidMaterialIds.length} 份资料已被删除、失效或尚未解析，请重新选择并确认。
                      </Alert>
                    ) : null}
                    {requiresMaterialConfirmation ? (
                      <Alert color="yellow" role="status" variant="light">
                        这是旧版草稿迁移出的当前资料列表。旧版未保存“全选”的历史快照，请确认后继续。
                      </Alert>
                    ) : null}
                    {isMaterialScopeOpen ? (
                      <Stack gap="sm">
                        <StudyPlanMaterialScopeSelector
                          error={materialsError}
                          isLoading={isLoadingMaterials}
                          materialScope={materialScope}
                          materials={materials}
                          onMaterialScopeChange={updateMaterialScope}
                        />
                        <Group justify="flex-end">
                          <Button
                            disabled={materialScope.material_ids.length === 0 || invalidMaterialIds.length > 0}
                            onClick={confirmMaterialScope}
                            size="xs"
                          >
                            确认资料范围
                          </Button>
                        </Group>
                      </Stack>
                    ) : null}
                  </Stack>
                </Paper>
                {materialsError ? (
                  <Alert color="red" role="alert" variant="light">{materialsError}</Alert>
                ) : null}
                <Group className="study-plan-goal-actions" justify="flex-end" wrap="nowrap">
                  <ActionIcon
                    aria-label="提交"
                    className="study-plan-goal-submit-button"
                    data-testid="study-plan-goal-submit"
                    disabled={isLoadingMaterials}
                    onClick={handleGoalSubmit}
                    radius="md"
                    size={38}
                    variant="filled"
                  >
                    <IconSend size={17} />
                  </ActionIcon>
                </Group>
              </Stack>
            ) : null}

            {phase === "preparing" ? (
              <StudyPlanQuestionnairePreparing />
            ) : null}

            {phase === "questionnaire" ? (
              <Stack gap="md">
                <Group justify="space-between" wrap="nowrap">
                  <Stack gap={2}>
                    <Title order={2}>开始前确认一下</Title>
                    <Text c="dimmed" size="sm">
                      这些问题会一起用于生成你的正式学习计划。
                    </Text>
                  </Stack>
                </Group>

                {shouldShowDateFollowups ? (
                  <Box className="study-plan-date-question">
                    <Radio.Group
                      className="study-plan-question-group"
                      label="你想从哪天开始学习？"
                      onChange={(value) => {
                        if (value === "custom") {
                          setIsCustomStartDateOpen(true);
                          return;
                        }
                        setIsCustomStartDateOpen(false);
                        updateStartDate(value);
                      }}
                      value={startDateChoiceValue}
                    >
                      <Stack className="study-plan-option-list" gap={8} mt={8}>
                        {startDateOptions.map((option) => (
                          <Radio key={option.value} label={option.label} value={option.value} />
                        ))}
                        <Radio label="D. 自定义开始日期" value="custom" />
                      </Stack>
                    </Radio.Group>
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

                    <Radio.Group
                      className="study-plan-question-group"
                      label="这次计划准备学几天？"
                      onChange={(value) => {
                        if (value === "custom") {
                          setIsCustomDurationDaysOpen(true);
                          return;
                        }
                        setIsCustomDurationDaysOpen(false);
                        updateDurationDays(value);
                      }}
                      value={durationDaysChoiceValue}
                    >
                      <Stack className="study-plan-option-list" gap={8} mt={8}>
                        {durationDayOptions.map((option) => (
                          <Radio key={option.value} label={option.label} value={option.value} />
                        ))}
                        <Radio label="D. 自定义学习天数" value="custom" />
                      </Stack>
                    </Radio.Group>
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

                {orderedDiagnosticQuestions.map((question) => (
                  question.question_type === "diagnostic_note" ? (
                    <Textarea
                      className="study-plan-question-note"
                      key={question.question_id}
                      label={question.question_text}
                      minRows={3}
                      onChange={(event) => setDiagnosticNote(event.currentTarget.value)}
                      placeholder={question.placeholder ?? undefined}
                      value={diagnosticNote}
                    />
                  ) : (
                    <Radio.Group
                      className="study-plan-question-group"
                      key={question.question_id}
                      label={question.question_text}
                      onChange={(value) => setDiagnosticAnswers((current) => ({
                        ...current,
                        [question.question_id]: value,
                      }))}
                      value={diagnosticAnswers[question.question_id] ?? ""}
                    >
                      <Stack gap={6} mt={6}>
                        {question.options.map((option) => (
                          <Radio key={option.value} label={option.label} value={option.value} />
                        ))}
                      </Stack>
                    </Radio.Group>
                  )
                ))}

                {unresolvedFields.length > 0 ? (
                  <Alert color="yellow" role="status" variant="light">
                    还有问题需要回答后才能生成计划。
                  </Alert>
                ) : null}

                <Divider />
                <Group className="study-plan-questionnaire-actions" justify="space-between">
                  <Text c="dimmed" size="sm">提交后会生成预览，确认名称后再保存。</Text>
                  <Button
                    data-testid="study-plan-questionnaire-submit"
                    disabled={!canSubmitQuestionnaire}
                    onClick={handleQuestionnaireSubmit}
                  >
                    提交问卷
                  </Button>
                </Group>
              </Stack>
            ) : null}

            {phase === "generating" ? (
              <StudyPlanCalendarGeneration
                endDate={endDate}
                generatedPreview={generatedPlanPreview}
                isComplete={isGenerationComplete}
                isSaving={isSavingPlan}
                onEnterPlan={handleEnterGeneratedPlan}
                onPlanTitleChange={(title) => {
                  setPlanTitle(title);
                  setError(null);
                }}
                onSavePlan={handleSaveGeneratedPlan}
                planTitle={planTitle}
                startDate={startDate}
              />
            ) : null}

            {error ? (
              <Alert color="red" role="alert" title="学习计划处理失败" variant="light">
                {error}
              </Alert>
            ) : null}
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}
