import { type KeyboardEvent, type MouseEvent, useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Grid,
  Group,
  Menu,
  Modal,
  Paper,
  Popover,
  Select,
  Skeleton,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import {
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconClipboardList,
  IconDotsVertical,
  IconEdit,
  IconMoon,
  IconPlus,
  IconSun,
  IconTrash,
  IconUser,
} from "@tabler/icons-react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../../api/errors";
import { useCourseNexusTheme } from "../../app/theme";
import { fetchGlobalCalendarMonth, fetchTodayTodos } from "../study-plans/api";
import type { StudyCalendarDaySummary, StudyCalendarTaskTodo } from "../study-plans/types";
import type { Course } from "../../types/course";
import { createCourse, deleteCourse, listCourses, listCourseTermOptions, updateCourse } from "./api";
import type { CourseTermOption } from "./api";
import "./home-workbench.css";

interface HomeCourse {
  id: string;
  name: string;
  description: string | null;
  teacher: string | null;
  term: string | null;
  materialLabel: string;
  taskLabel: string;
  recentActivity: string;
  progress: string;
  status: string;
}

interface CourseFormValues {
  name: string;
  description: string;
  teacher: string;
  term: string;
}

type CourseModalMode = "create" | "edit";

const COURSE_NAME_MAX_LENGTH = 20;
const COURSE_DESCRIPTION_MAX_LENGTH = 50;
const COURSE_TEACHER_MAX_LENGTH = 10;

interface CalendarDay {
  day: number | null;
  dateKey: string | null;
  isToday: boolean;
}

const ALL_TERMS_VALUE = "__all_terms__";
const UNSELECTED_TERM_VALUE = "__unselected_term__";
const courseToneClasses = ["blue", "mint", "indigo", "violet", "orange"];

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

function getDateKey(year: number, month: number, day: number): string {
  return `${year}-${padDatePart(month + 1)}-${padDatePart(day)}`;
}

function homeCalendarTaskTitle(summary: StudyCalendarDaySummary): string {
  const taskTitles = summary.task_summaries
    .map((task) => task.title)
    .filter((title) => title.trim().length > 0);
  return taskTitles[0] ?? `${summary.task_count} 个任务`;
}

function HomeCalendarCellSummary({ summary }: { summary: StudyCalendarDaySummary }) {
  const taskTitle = homeCalendarTaskTitle(summary);

  return (
    <span className="home-calendar-cell-summary">
      <span className="home-calendar-task-title" title={taskTitle}>
        {taskTitle}
      </span>
      <span className="home-calendar-task-progress">
        {summary.completed_subtask_count}/{summary.subtask_count} 完成
      </span>
    </span>
  );
}

function getCalendarDays(referenceDate = new Date(), today = new Date()): CalendarDay[] {
  const year = referenceDate.getFullYear();
  const month = referenceDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDate = new Date(year, month + 1, 0).getDate();
  const leadingEmptyCells = firstDay.getDay();
  const totalCells = Math.ceil((leadingEmptyCells + lastDate) / 7) * 7;

  return Array.from({ length: totalCells }, (_, index) => {
    const day = index - leadingEmptyCells + 1;

    if (day < 1 || day > lastDate) {
      return { day: null, dateKey: null, isToday: false };
    }

    return {
      day,
      dateKey: getDateKey(year, month, day),
      isToday: year === today.getFullYear() && month === today.getMonth() && day === today.getDate(),
    };
  });
}

function getCourseToneClass(index: number): string {
  return courseToneClasses[index % courseToneClasses.length];
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "课程列表加载失败";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: "已完成",
    in_progress: "进行中",
    not_started: "未开始",
  };

  return labels[status] ?? status;
}

function statusColor(status: string): string {
  if (status === "completed") {
    return "teal";
  }

  if (status === "in_progress") {
    return "blue";
  }

  return "gray";
}

function getTaskExecutionHref(task: StudyCalendarTaskTodo): string | null {
  const matchedSubtask = task.first_incomplete_subtask_id
    ? task.subtasks.find((subtask) => subtask.subtask_id === task.first_incomplete_subtask_id)
    : null;
  const executionUrl = matchedSubtask?.execution_url ?? task.subtasks.find((subtask) => subtask.execution_url)?.execution_url;

  if (executionUrl) {
    return executionUrl;
  }

  return task.first_incomplete_subtask_id ? `/study-subtasks/${task.first_incomplete_subtask_id}` : null;
}

function getTodayTodoHref(task: StudyCalendarTaskTodo): string {
  return getTaskExecutionHref(task) ?? `/courses/${task.course_id}/study-plans/${task.plan_id}`;
}

function getTodayTodoActionLabel(task: StudyCalendarTaskTodo): string {
  return getTaskExecutionHref(task) ? "继续学习" : "查看计划";
}

function createEmptyCourseForm(): CourseFormValues {
  return {
    name: "",
    description: "",
    teacher: "",
    term: "",
  };
}

function createCourseFormFromCourse(course: HomeCourse): CourseFormValues {
  return {
    name: course.name,
    description: course.description ?? "",
    teacher: course.teacher ?? "",
    term: course.term ?? "",
  };
}

function optionalText(value: string): string | null {
  const trimmed = value.trim();

  return trimmed ? trimmed : null;
}

function buildCoursePayload(values: CourseFormValues) {
  return {
    name: values.name.trim(),
    description: optionalText(values.description),
    teacher: optionalText(values.teacher),
    term: optionalText(values.term),
  };
}

function shouldPreserveLegacyTerm(
  course: HomeCourse | null,
  values: CourseFormValues,
  termOptions: CourseTermOption[],
): boolean {
  return Boolean(
    course?.term
      && course.term === values.term
      && !termOptions.some((option) => option.value === course.term),
  );
}

function buildCourseUpdatePayload(
  values: CourseFormValues,
  preserveLegacyTerm: boolean,
) {
  const payload = buildCoursePayload(values);
  if (!preserveLegacyTerm) {
    return payload;
  }

  const { term: _term, ...payloadWithoutTerm } = payload;
  return payloadWithoutTerm;
}

function getTermLabel(term: string | null, termOptions: CourseTermOption[]): string {
  if (!term) {
    return "未填写学期";
  }

  return termOptions.find((option) => option.value === term)?.label ?? `${term}（旧学期值）`;
}

function getTermSummaryLabel(selectedTerm: string, termOptions: CourseTermOption[]): string {
  if (selectedTerm === ALL_TERMS_VALUE) {
    return "全部学期";
  }

  if (selectedTerm === UNSELECTED_TERM_VALUE) {
    return "未选择";
  }

  return getTermLabel(selectedTerm, termOptions);
}

function buildTermSelectData(courses: HomeCourse[], termOptions: CourseTermOption[]) {
  const optionValues = new Set(termOptions.map((option) => option.value));
  const legacyTermOptions = Array.from(
    new Set(
      courses
        .map((course) => course.term)
        .filter((term): term is string => typeof term === "string" && term.length > 0 && !optionValues.has(term)),
    ),
  ).map((term) => ({ value: term, label: `${term}（旧学期值）` }));

  return [
    { value: ALL_TERMS_VALUE, label: "全部学期" },
    { value: UNSELECTED_TERM_VALUE, label: "未选择" },
    ...termOptions,
    ...legacyTermOptions,
  ];
}

function mapCourseToHomeCourse(course: Course): HomeCourse {
  const taskStatusLabel: Record<NonNullable<Course["today_task_status"]>, string> = {
    has_task_today: "今日有任务",
    no_study_plan: "无学习计划",
    no_task_today: "今日无任务",
  };

  return {
    id: course.id,
    name: course.name,
    description: course.description,
    teacher: course.teacher,
    term: course.term,
    materialLabel: typeof course.material_count === "number" ? `资料 ${course.material_count} 份` : "资料状态待同步",
    taskLabel: course.today_task_status ? taskStatusLabel[course.today_task_status] : "今日任务待同步",
    recentActivity: course.description?.trim() || "课程资料待上传",
    progress: course.status === "active" ? "课程已创建" : course.status,
    status: course.status,
  };
}

function Header() {
  const { isDarkMode, toggleTheme } = useCourseNexusTheme();
  const ThemeIcon = isDarkMode ? IconSun : IconMoon;
  const themeLabel = isDarkMode ? "切换为日间模式" : "切换为夜间模式";

  return (
    <Paper className="home-header" component="header" radius={0}>
      <Group justify="space-between" wrap="nowrap">
        <Group gap="lg" wrap="nowrap">
          <Title className="home-brand-title" order={1}>
            课枢 <span>CourseNexus</span>
          </Title>
        </Group>

        <Group gap="sm" wrap="nowrap">
          <ActionIcon
            aria-label={themeLabel}
            className="home-theme-single-button"
            onClick={toggleTheme}
            radius="md"
            size={44}
            variant="default"
          >
            <ThemeIcon size={22} stroke={1.8} />
          </ActionIcon>
          <ActionIcon
            aria-label="打开个人中心"
            className="home-user-button"
            component={Link}
            radius="xl"
            size={48}
            to="/profile"
            variant="default"
          >
            <IconUser size={24} stroke={1.8} />
          </ActionIcon>
        </Group>
      </Group>
    </Paper>
  );
}

function TodayTodoPanel() {
  const today = new Date();
  const todayKey = getDateKey(today.getFullYear(), today.getMonth(), today.getDate());
  const [tasks, setTasks] = useState<StudyCalendarTaskTodo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    setIsLoading(true);
    setError(null);

    fetchTodayTodos(todayKey)
      .then((todos) => {
        if (!ignore) {
          setTasks(Array.isArray(todos.tasks) ? todos.tasks : []);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(getErrorMessage(nextError));
          setTasks([]);
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
  }, [todayKey]);

  return (
    <Paper className="home-focus-panel" radius="md" withBorder>
      <Stack gap="lg" h="100%" justify="space-between">
        <Group justify="space-between">
          <Stack gap={2}>
            <Title order={2}>今日待办</Title>
            <Text c="dimmed" size="sm">{todayKey}</Text>
          </Stack>
          {!isLoading && !error && tasks.length > 0 ? (
            <Badge className="home-urgent-badge" variant="light">
              {tasks.length} 个任务
            </Badge>
          ) : null}
        </Group>

        {isLoading ? (
          <Stack className="home-todo-list" gap="sm" role="status">
            <Text c="dimmed" size="sm">正在加载今日待办...</Text>
            <Skeleton height={72} radius="md" />
            <Skeleton height={72} radius="md" />
          </Stack>
        ) : null}

        {!isLoading && error ? (
          <Alert color="red" role="alert" title="今日待办加载失败" variant="light">
            {error}
          </Alert>
        ) : null}

        {!isLoading && !error && tasks.length === 0 ? (
          <Stack align="center" className="home-plan-empty" gap="md">
            <IconClipboardList aria-hidden className="home-empty-icon" size={48} stroke={1.6} />
            <Stack gap={4}>
              <Title order={3}>今天还没有学习计划</Title>
              <Text c="dimmed" ta="center">
                进入课程详情制定学习计划后，这里会展示当天任务
              </Text>
            </Stack>
          </Stack>
        ) : null}

        {!isLoading && !error && tasks.length > 0 ? (
          <Stack className="home-todo-list" gap="sm">
            {tasks.map((task) => (
              <Paper
                aria-label={`${getTodayTodoActionLabel(task)} ${task.title}`}
                className="home-todo-item"
                component={Link}
                key={task.task_id}
                radius="md"
                to={getTodayTodoHref(task)}
                withBorder
              >
                <Group justify="space-between" wrap="nowrap">
                  <Stack gap={2}>
                    <Text fw={750} size="sm">{task.title}</Text>
                    <Text c="dimmed" size="xs">{task.course_name}</Text>
                    <Text c="dimmed" size="xs">
                      {task.completed_subtask_count}/{task.total_subtask_count}
                    </Text>
                  </Stack>
                  <Badge color={statusColor(task.derived_status)} size="xs" variant="light">
                    {statusLabel(task.derived_status)}
                  </Badge>
                </Group>
              </Paper>
            ))}
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}

function CalendarPanel() {
  const navigate = useNavigate();
  const today = new Date();
  const [referenceDate, setReferenceDate] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [isMonthPickerOpen, setIsMonthPickerOpen] = useState(false);
  const [draftYear, setDraftYear] = useState(String(referenceDate.getFullYear()));
  const [draftMonth, setDraftMonth] = useState(String(referenceDate.getMonth()));
  const [monthSummaries, setMonthSummaries] = useState<StudyCalendarDaySummary[]>([]);
  const [monthError, setMonthError] = useState<string | null>(null);
  const [isMonthLoading, setIsMonthLoading] = useState(true);
  const monthLabel = `${referenceDate.getMonth() + 1} 月`;
  const calendarTitle = `${referenceDate.getFullYear()} 年 ${monthLabel}`;
  const calendarDays = getCalendarDays(referenceDate, today);
  const monthKey = `${referenceDate.getFullYear()}-${padDatePart(referenceDate.getMonth() + 1)}`;
  const summariesByDate = useMemo(() => {
    const summaries = new Map<string, StudyCalendarDaySummary>();
    monthSummaries.forEach((summary) => summaries.set(summary.date, summary));
    return summaries;
  }, [monthSummaries]);
  const yearOptions = Array.from({ length: 5 }, (_, index) => {
    const year = today.getFullYear() - 2 + index;
    return { value: String(year), label: `${year} 年` };
  });
  const monthOptions = Array.from({ length: 12 }, (_, index) => ({ value: String(index), label: `${index + 1} 月` }));

  useEffect(() => {
    let ignore = false;

    setIsMonthLoading(true);
    setMonthError(null);

    fetchGlobalCalendarMonth(monthKey)
      .then((monthData) => {
        if (!ignore) {
          setMonthSummaries(Array.isArray(monthData.days) ? monthData.days : []);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setMonthError(getErrorMessage(nextError));
          setMonthSummaries([]);
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsMonthLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [monthKey]);

  function moveMonth(offset: number) {
    setReferenceDate((currentDate) => new Date(currentDate.getFullYear(), currentDate.getMonth() + offset, 1));
  }

  function openMonthPicker() {
    setDraftYear(String(referenceDate.getFullYear()));
    setDraftMonth(String(referenceDate.getMonth()));
    setIsMonthPickerOpen(true);
  }

  function applyMonthPicker() {
    setReferenceDate(new Date(Number(draftYear), Number(draftMonth), 1));
    setIsMonthPickerOpen(false);
  }

  return (
    <>
      <Paper className="home-calendar-panel" radius="md" withBorder>
        <Stack gap="md" h="100%">
          <Paper className="home-calendar-card" radius="md" withBorder>
            <Group justify="space-between">
              <ActionIcon aria-label="上个月" onClick={() => moveMonth(-1)} variant="subtle">
                <IconChevronLeft size={22} />
              </ActionIcon>
              <Popover
                onChange={(opened) => {
                  if (opened) {
                    openMonthPicker();
                  } else {
                    setIsMonthPickerOpen(false);
                  }
                }}
                opened={isMonthPickerOpen}
                position="bottom"
                shadow="md"
                trapFocus
                withArrow
                withinPortal
              >
                <Popover.Target>
                  <Button className="home-calendar-title-button" onClick={openMonthPicker} size="compact-sm" variant="subtle">
                    {calendarTitle}
                  </Button>
                </Popover.Target>
                <Popover.Dropdown aria-label="选择年月" className="home-month-picker" role="region">
                  <Box className="home-month-picker-controls">
                    <Select aria-label="选择年份" data={yearOptions} onChange={(value) => setDraftYear(value ?? draftYear)} value={draftYear} />
                    <Select aria-label="选择月份" data={monthOptions} onChange={(value) => setDraftMonth(value ?? draftMonth)} value={draftMonth} />
                    <Button aria-label="关闭年月选择" className="home-month-picker-action" onClick={() => setIsMonthPickerOpen(false)} variant="default">
                      取消
                    </Button>
                    <Button className="home-month-picker-action" onClick={applyMonthPicker}>应用</Button>
                  </Box>
                </Popover.Dropdown>
              </Popover>
              <ActionIcon aria-label="下个月" onClick={() => moveMonth(1)} variant="subtle">
                <IconChevronRight size={22} />
              </ActionIcon>
            </Group>

            <Divider />

            {isMonthLoading ? (
              <Text c="dimmed" role="status" size="sm">正在加载月历任务...</Text>
            ) : null}
            {!isMonthLoading && monthError ? (
              <Alert color="red" role="alert" title="月历加载失败" variant="light">
                {monthError}
              </Alert>
            ) : null}

            <Box className="home-calendar-weekdays" aria-hidden>
              {["日", "一", "二", "三", "四", "五", "六"].map((day) => (
                <Text c="dimmed" fw={500} key={day} size="sm" ta="center">
                  {day}
                </Text>
              ))}
            </Box>

            <Box aria-label="月历" className="home-calendar-grid home-calendar-compact-grid home-calendar-roomy-grid" role="grid">
              {calendarDays.map((calendarDay, index) => (
                (() => {
                  const summary = calendarDay.dateKey ? summariesByDate.get(calendarDay.dateKey) : undefined;
                  return (
                    <Box
                      aria-label={calendarDay.dateKey ? `打开 ${calendarDay.dateKey} 的日历` : "空白日期"}
                      className={`home-calendar-cell${calendarDay.isToday ? " is-today" : ""}${summary ? " has-tasks" : ""}`}
                      component={calendarDay.dateKey ? "button" : "div"}
                      key={`${calendarDay.day ?? "empty"}-${index}`}
                      onClick={calendarDay.dateKey ? () => navigate(`/calendar?date=${calendarDay.dateKey}`) : undefined}
                      role="gridcell"
                      type={calendarDay.dateKey ? "button" : undefined}
                    >
                      {calendarDay.day ? <span className="home-calendar-day">{calendarDay.day}</span> : null}
                      {summary ? <HomeCalendarCellSummary summary={summary} /> : calendarDay.day ? <span aria-hidden className="home-calendar-task-dots" /> : null}
                    </Box>
                  );
                })()
              ))}
            </Box>
          </Paper>
        </Stack>
      </Paper>
    </>
  );
}

function CourseCard({
  course,
  onDelete,
  onEdit,
  onOpen,
  termLabel,
  toneClass,
}: {
  course: HomeCourse;
  onDelete: (course: HomeCourse) => void;
  onEdit: (course: HomeCourse) => void;
  onOpen: (course: HomeCourse) => void;
  termLabel: string;
  toneClass: string;
}) {
  function stopCardNavigation(event: MouseEvent<HTMLElement>) {
    event.stopPropagation();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(course);
    }
  }

  return (
    <Card
      aria-label={`打开课程 ${course.name}`}
      className={`home-course-card home-course-card-${toneClass}`}
      onClick={() => onOpen(course)}
      onKeyDown={handleKeyDown}
      padding="lg"
      radius="md"
      role="link"
      tabIndex={0}
      withBorder
    >
      <Stack gap="lg" h="100%" justify="space-between">
        <Group align="flex-start" justify="space-between" wrap="nowrap">
          <Stack gap="xs">
            <Title order={3}>
              <Link className="home-course-link" title={course.name} to={`/courses/${course.id}`}>
                {course.name}
              </Link>
            </Title>
            <Text c="dimmed" size="sm">
              {course.teacher ?? "未填写教师"} · {termLabel}
            </Text>
          </Stack>
          <Menu position="bottom-end" shadow="sm" width={160} withinPortal>
            <Menu.Target>
              <ActionIcon
                aria-label={`${course.name} 更多操作`}
                className="home-card-menu"
                onClick={stopCardNavigation}
                variant="subtle"
              >
                <IconDotsVertical size={22} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown onClick={stopCardNavigation}>
              <Menu.Item
                leftSection={<IconEdit size={16} />}
                onClick={(event) => {
                  event.stopPropagation();
                  onEdit(course);
                }}
              >
                编辑课程
              </Menu.Item>
              <Menu.Item
                color="red"
                leftSection={<IconTrash size={16} />}
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(course);
                }}
              >
                删除课程
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>

        <Text className="home-course-activity" title={course.recentActivity}>{course.recentActivity}</Text>

        <Group gap="sm">
          <Badge className="home-material-badge" variant="light">
            {course.materialLabel}
          </Badge>
          <Badge className="home-task-badge" variant="light">
            {course.taskLabel}
          </Badge>
        </Group>
      </Stack>
    </Card>
  );
}

function AddCourseCard({ onClick }: { onClick: () => void }) {
  return (
    <Paper
      aria-label="添加课程"
      className="home-add-course"
      component="button"
      onClick={onClick}
      radius="md"
      type="button"
      withBorder
    >
      <Stack align="center" gap="sm">
        <Group gap="sm">
          <IconPlus size={28} stroke={1.7} />
          <Text fw={650} size="lg">
            添加课程
          </Text>
        </Group>
        <Text c="dimmed" ta="center">
          创建后进入课程详情上传资料
        </Text>
      </Stack>
    </Paper>
  );
}

function CourseLoadingCards() {
  return (
    <>
      <Grid.Col span={12}>
        <Text c="dimmed" role="status" size="sm">
          正在加载课程...
        </Text>
      </Grid.Col>
      {Array.from({ length: 3 }, (_, index) => (
        <Grid.Col key={index} span={{ base: 12, md: 6, xl: 4 }}>
          <Card className="home-course-card" padding="lg" radius="md" withBorder>
            <Stack gap="lg">
              <Skeleton height={24} width="62%" />
              <Skeleton height={14} width="46%" />
              <Skeleton height={42} />
              <Group gap="sm">
                <Skeleton height={22} width={86} />
                <Skeleton height={22} width={112} />
              </Group>
            </Stack>
          </Card>
        </Grid.Col>
      ))}
    </>
  );
}

function CourseEmptyState() {
  return null;
}

function CourseErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Grid.Col span={{ base: 12 }}>
      <Alert className="home-course-alert" color="red" role="alert" title="课程加载失败" variant="light">
        <Stack align="flex-start" gap="sm">
          <Text>{message}</Text>
          <Button onClick={onRetry} size="xs" variant="light">
            重试加载课程
          </Button>
        </Stack>
      </Alert>
    </Grid.Col>
  );
}

function CourseFormModal({
  error,
  mode,
  onChange,
  onClose,
  onSubmit,
  opened,
  termError,
  termOptions,
  isTermLoading,
  values,
  isSubmitting,
}: {
  error: string | null;
  mode: CourseModalMode;
  onChange: (field: keyof CourseFormValues, value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  opened: boolean;
  termError: string | null;
  termOptions: CourseTermOption[];
  isTermLoading: boolean;
  values: CourseFormValues;
  isSubmitting: boolean;
}) {
  const isCreate = mode === "create";
  const hasSelectedLegacyTerm = Boolean(
    values.term && !termOptions.some((option) => option.value === values.term),
  );
  const canSubmit = values.name.trim().length > 0 && !isSubmitting;
  const termData = hasSelectedLegacyTerm
    ? [...termOptions, { value: values.term, label: `${values.term}（旧学期值，保存其他修改时会保留）` }]
    : termOptions;

  return (
    <Modal
      centered
      onClose={onClose}
      opened={opened}
      title={isCreate ? "创建课程" : "编辑课程"}
      transitionProps={{ duration: 0 }}
    >
      <Stack gap="md">
        {error ? (
          <Alert color="red" role="alert" title={isCreate ? "课程创建失败" : "课程保存失败"} variant="light">
            {error}
          </Alert>
        ) : null}
        <TextInput
          aria-label="课程名称"
          data-autofocus
          description={`最多 ${COURSE_NAME_MAX_LENGTH} 个字符`}
          label="课程名称"
          maxLength={COURSE_NAME_MAX_LENGTH}
          onChange={(event) => onChange("name", event.currentTarget.value)}
          required
          value={values.name}
        />
        <Textarea
          aria-label="课程简介"
          description={`最多 ${COURSE_DESCRIPTION_MAX_LENGTH} 个字符`}
          label="课程简介"
          maxLength={COURSE_DESCRIPTION_MAX_LENGTH}
          minRows={3}
          onChange={(event) => onChange("description", event.currentTarget.value)}
          value={values.description}
        />
        <TextInput
          aria-label="教师"
          description={`最多 ${COURSE_TEACHER_MAX_LENGTH} 个字符`}
          label="教师"
          maxLength={COURSE_TEACHER_MAX_LENGTH}
          onChange={(event) => onChange("teacher", event.currentTarget.value)}
          value={values.teacher}
        />
        <Select
          aria-label="学期"
          clearable
          data={termData}
          description={hasSelectedLegacyTerm ? "如需修改学期，请重新选择标准选项或清空。" : undefined}
          disabled={isTermLoading || Boolean(termError)}
          error={termError}
          label="学期"
          nothingFoundMessage={isTermLoading ? "正在加载学期" : "暂无学期选项"}
          onChange={(value) => onChange("term", value ?? "")}
          placeholder="请选择学期"
          searchable
          value={values.term}
        />
        {isCreate ? (
          <Text c="dimmed" size="sm">
            资料可在课程创建后进入课程详情页继续上传。
          </Text>
        ) : null}
        <Group justify="flex-end">
          <Button disabled={isSubmitting} onClick={onClose} variant="default">
            取消
          </Button>
          <Button disabled={!canSubmit} loading={isSubmitting} onClick={onSubmit}>
            {isCreate ? "创建课程" : "保存修改"}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function DeleteCourseModal({
  course,
  error,
  isSubmitting,
  onClose,
  onConfirm,
}: {
  course: HomeCourse | null;
  error: string | null;
  isSubmitting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Modal centered onClose={onClose} opened={Boolean(course)} title="删除课程" transitionProps={{ duration: 0 }}>
      <Stack gap="md">
        {error ? (
          <Alert color="red" role="alert" title="删除失败" variant="light">
            {error}
          </Alert>
        ) : null}
        <Text>
          确认删除“{course?.name}”吗？删除后该课程及其资料、对话、生成内容、学习计划会按后端策略隐藏。
        </Text>
        <Group justify="flex-end">
          <Button disabled={isSubmitting} onClick={onClose} variant="default">
            取消
          </Button>
          <Button color="red" loading={isSubmitting} onClick={onConfirm}>
            确认删除
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function CourseOverview({
  courses,
  error,
  isLoading,
  onAddCourse,
  onDeleteCourse,
  onEditCourse,
  onOpenCourse,
  onRetry,
  termError,
  termOptions,
}: {
  courses: HomeCourse[];
  error: string | null;
  isLoading: boolean;
  onAddCourse: () => void;
  onDeleteCourse: (course: HomeCourse) => void;
  onEditCourse: (course: HomeCourse) => void;
  onOpenCourse: (course: HomeCourse) => void;
  onRetry: () => void;
  termError: string | null;
  termOptions: CourseTermOption[];
}) {
  const [selectedTerm, setSelectedTerm] = useState(ALL_TERMS_VALUE);
  const termData = useMemo(() => buildTermSelectData(courses, termOptions), [courses, termOptions]);
  const filteredCourses = selectedTerm === ALL_TERMS_VALUE
    ? courses
    : selectedTerm === UNSELECTED_TERM_VALUE
      ? courses.filter((course) => !course.term)
      : courses.filter((course) => course.term === selectedTerm);
  const termSummary = getTermSummaryLabel(selectedTerm, termOptions);

  return (
    <Paper className="home-main-panel" radius="md" withBorder>
      <Group align="flex-start" justify="space-between">
        <Stack gap={4}>
          <Group align="baseline" gap="sm" wrap="wrap">
            <Title order={2}>我的课程</Title>
            <Text c="dimmed" size="sm">
              {termSummary} {filteredCourses.length} 门课程
            </Text>
          </Group>
        </Stack>
        <Select
          aria-label="选择学期"
          className="home-term-select"
          data={termData}
          error={termError}
          onChange={(value) => setSelectedTerm(value ?? ALL_TERMS_VALUE)}
          rightSection={<IconChevronDown size={18} />}
          value={selectedTerm}
        />
      </Group>

      <Box className="home-course-scroll">
      <Grid className="home-course-grid" gap="lg">
        {isLoading ? <CourseLoadingCards /> : null}
        {!isLoading && error ? <CourseErrorState message={error} onRetry={onRetry} /> : null}
        {!isLoading && !error && filteredCourses.length === 0 ? <CourseEmptyState /> : null}
        {!isLoading && !error
          ? filteredCourses.map((course, index) => (
              <Grid.Col key={course.id} span={{ base: 12, md: 6, xl: 4 }}>
                <CourseCard
                  course={course}
                  onDelete={onDeleteCourse}
                  onEdit={onEditCourse}
                  onOpen={onOpenCourse}
                  termLabel={getTermLabel(course.term, termOptions)}
                  toneClass={getCourseToneClass(index)}
                />
              </Grid.Col>
            ))
          : null}
        <Grid.Col span={{ base: 12, md: 6, xl: 4 }}>
          <AddCourseCard onClick={onAddCourse} />
        </Grid.Col>
      </Grid>
      </Box>
    </Paper>
  );
}

export function HomeWorkbench() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<HomeCourse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [termOptions, setTermOptions] = useState<CourseTermOption[]>([]);
  const [termOptionsError, setTermOptionsError] = useState<string | null>(null);
  const [isTermOptionsLoading, setIsTermOptionsLoading] = useState(true);
  const [courseModalMode, setCourseModalMode] = useState<CourseModalMode>("create");
  const [isCourseModalOpen, setIsCourseModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<HomeCourse | null>(null);
  const [courseFormValues, setCourseFormValues] = useState<CourseFormValues>(createEmptyCourseForm);
  const [courseFormError, setCourseFormError] = useState<string | null>(null);
  const [isCourseFormSubmitting, setIsCourseFormSubmitting] = useState(false);
  const [deletingCourse, setDeletingCourse] = useState<HomeCourse | null>(null);
  const [deleteCourseError, setDeleteCourseError] = useState<string | null>(null);
  const [isDeletingCourse, setIsDeletingCourse] = useState(false);

  useEffect(() => {
    let ignore = false;

    setIsLoading(true);
    setError(null);

    listCourses()
      .then((nextCourses) => {
        if (!ignore) {
          setCourses(nextCourses.map(mapCourseToHomeCourse));
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(getErrorMessage(nextError));
          setCourses([]);
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
  }, [reloadKey]);

  useEffect(() => {
    let ignore = false;

    setIsTermOptionsLoading(true);
    setTermOptionsError(null);

    listCourseTermOptions()
      .then((options) => {
        if (!ignore) {
          setTermOptions(options);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setTermOptions([]);
          setTermOptionsError(getErrorMessage(nextError));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsTermOptionsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  function openCreateCourseModal() {
    setCourseModalMode("create");
    setEditingCourse(null);
    setCourseFormValues(createEmptyCourseForm());
    setCourseFormError(null);
    setIsCourseModalOpen(true);
  }

  function openEditCourseModal(course: HomeCourse) {
    setCourseModalMode("edit");
    setEditingCourse(course);
    setCourseFormValues(createCourseFormFromCourse(course));
    setCourseFormError(null);
    setIsCourseModalOpen(true);
  }

  function closeCourseModal() {
    if (isCourseFormSubmitting) {
      return;
    }

    setIsCourseModalOpen(false);
    setCourseFormError(null);
  }

  function updateCourseFormValue(field: keyof CourseFormValues, value: string) {
    setCourseFormValues((currentValues) => ({
      ...currentValues,
      [field]: value,
    }));
  }

  async function submitCourseForm() {
    const payload = buildCoursePayload(courseFormValues);

    if (!payload.name) {
      setCourseFormError("课程名称不能为空");
      return;
    }

    setIsCourseFormSubmitting(true);
    setCourseFormError(null);

    try {
      if (courseModalMode === "create") {
        const createdCourse = await createCourse(payload);
        setCourses((currentCourses) => [...currentCourses, mapCourseToHomeCourse(createdCourse)]);
        setIsCourseModalOpen(false);
        navigate(`/courses/${createdCourse.id}`, { state: { openUploadPrompt: true } });
      } else if (editingCourse) {
        const nextCourse = await updateCourse(
          editingCourse.id,
          buildCourseUpdatePayload(
            courseFormValues,
            shouldPreserveLegacyTerm(editingCourse, courseFormValues, termOptions),
          ),
        );
        setCourses((currentCourses) =>
          currentCourses.map((course) => (course.id === nextCourse.id ? mapCourseToHomeCourse(nextCourse) : course)),
        );
        setIsCourseModalOpen(false);
      }
    } catch (nextError: unknown) {
      setCourseFormError(getErrorMessage(nextError));
    } finally {
      setIsCourseFormSubmitting(false);
    }
  }

  function openDeleteCourseModal(course: HomeCourse) {
    setDeletingCourse(course);
    setDeleteCourseError(null);
  }

  function closeDeleteCourseModal() {
    if (isDeletingCourse) {
      return;
    }

    setDeletingCourse(null);
    setDeleteCourseError(null);
  }

  async function confirmDeleteCourse() {
    if (!deletingCourse) {
      return;
    }

    setIsDeletingCourse(true);
    setDeleteCourseError(null);

    try {
      await deleteCourse(deletingCourse.id);
      setCourses((currentCourses) => currentCourses.filter((course) => course.id !== deletingCourse.id));
      setDeletingCourse(null);
    } catch (nextError: unknown) {
      setDeleteCourseError(getErrorMessage(nextError));
    } finally {
      setIsDeletingCourse(false);
    }
  }

  return (
    <Box className="home-workbench">
      <Header />
      <Container className="home-shell" fluid>
        <Box className="home-layout">
          <Box className="home-side-panel">
            <TodayTodoPanel />
            <CalendarPanel />
          </Box>
          <CourseOverview
            courses={courses}
            error={error}
            isLoading={isLoading}
            onAddCourse={openCreateCourseModal}
            onDeleteCourse={openDeleteCourseModal}
            onEditCourse={openEditCourseModal}
            onOpenCourse={(course) => navigate(`/courses/${course.id}`)}
            onRetry={() => setReloadKey((currentKey) => currentKey + 1)}
            termError={termOptionsError}
            termOptions={termOptions}
          />
        </Box>
      </Container>
      <CourseFormModal
        error={courseFormError}
        isSubmitting={isCourseFormSubmitting}
        mode={courseModalMode}
        onChange={updateCourseFormValue}
        onClose={closeCourseModal}
        onSubmit={submitCourseForm}
        opened={isCourseModalOpen}
        termError={termOptionsError}
        termOptions={termOptions}
        isTermLoading={isTermOptionsLoading}
        values={courseFormValues}
      />
      <DeleteCourseModal
        course={deletingCourse}
        error={deleteCourseError}
        isSubmitting={isDeletingCourse}
        onClose={closeDeleteCourseModal}
        onConfirm={confirmDeleteCourse}
      />
    </Box>
  );
}
