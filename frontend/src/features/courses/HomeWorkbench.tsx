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

interface CalendarDay {
  day: number | null;
  dateKey: string | null;
  isToday: boolean;
}

const ALL_TERMS_VALUE = "__all_terms__";
const courseToneClasses = ["blue", "mint", "indigo", "violet", "orange"];

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

function getDateKey(year: number, month: number, day: number): string {
  return `${year}-${padDatePart(month + 1)}-${padDatePart(day)}`;
}

function getCalendarDays(referenceDate = new Date()): CalendarDay[] {
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
      isToday: day === referenceDate.getDate(),
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

  return [{ value: ALL_TERMS_VALUE, label: "全部学期" }, ...termOptions, ...legacyTermOptions];
}

function mapCourseToHomeCourse(course: Course): HomeCourse {
  return {
    id: course.id,
    name: course.name,
    description: course.description,
    teacher: course.teacher,
    term: course.term,
    materialLabel: "资料待接入",
    taskLabel: "今日任务待接入",
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

        <Group gap="md" wrap="nowrap">
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
            aria-label="打开个人中心（待接入）"
            className="home-user-button"
            disabled
            radius="xl"
            size={48}
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
  return (
    <Paper className="home-focus-panel" radius="md" withBorder>
      <Stack gap="lg" h="100%" justify="space-between">
        <Group justify="space-between">
          <Stack gap={2}>
            <Title order={2}>今日待办</Title>
          </Stack>
        </Group>

        <Stack align="center" className="home-plan-empty" gap="md">
          <IconClipboardList aria-hidden className="home-empty-icon" size={48} stroke={1.6} />
          <Stack gap={4}>
            <Title order={3}>今天还没有学习计划</Title>
            <Text c="dimmed" ta="center">
              进入课程详情制定学习计划后，这里会展示当天任务
            </Text>
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  );
}

function CalendarPanel() {
  const navigate = useNavigate();
  const today = new Date();
  const [referenceDate, setReferenceDate] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [isMonthModalOpen, setIsMonthModalOpen] = useState(false);
  const [draftYear, setDraftYear] = useState(String(referenceDate.getFullYear()));
  const [draftMonth, setDraftMonth] = useState(String(referenceDate.getMonth()));
  const monthLabel = `${referenceDate.getMonth() + 1} 月`;
  const calendarTitle = `${referenceDate.getFullYear()} 年 ${monthLabel}`;
  const calendarDays = getCalendarDays(referenceDate);
  const yearOptions = Array.from({ length: 5 }, (_, index) => {
    const year = today.getFullYear() - 2 + index;
    return { value: String(year), label: `${year} 年` };
  });
  const monthOptions = Array.from({ length: 12 }, (_, index) => ({ value: String(index), label: `${index + 1} 月` }));

  function moveMonth(offset: number) {
    setReferenceDate((currentDate) => new Date(currentDate.getFullYear(), currentDate.getMonth() + offset, 1));
  }

  function openMonthPicker() {
    setDraftYear(String(referenceDate.getFullYear()));
    setDraftMonth(String(referenceDate.getMonth()));
    setIsMonthModalOpen(true);
  }

  function applyMonthPicker() {
    setReferenceDate(new Date(Number(draftYear), Number(draftMonth), 1));
    setIsMonthModalOpen(false);
  }

  return (
    <>
      <Paper className="home-calendar-panel" radius="md" withBorder>
        <Stack gap="md" h="100%">
          <Group justify="space-between">
            <Title order={2}>日历</Title>
            <Badge color="blue" variant="light">
              {monthLabel}
            </Badge>
          </Group>

          <Paper className="home-calendar-card" radius="md" withBorder>
            <Group justify="space-between">
              <ActionIcon aria-label="上个月" onClick={() => moveMonth(-1)} variant="subtle">
                <IconChevronLeft size={22} />
              </ActionIcon>
              <Button className="home-calendar-title-button" onClick={openMonthPicker} size="compact-sm" variant="subtle">
                {calendarTitle}
              </Button>
              <ActionIcon aria-label="下个月" onClick={() => moveMonth(1)} variant="subtle">
                <IconChevronRight size={22} />
              </ActionIcon>
            </Group>

            <Divider />

            <Box className="home-calendar-weekdays" aria-hidden>
              {["日", "一", "二", "三", "四", "五", "六"].map((day) => (
                <Text c="dimmed" fw={500} key={day} size="sm" ta="center">
                  {day}
                </Text>
              ))}
            </Box>

            <Box aria-label="月历" className="home-calendar-grid" role="grid">
              {calendarDays.map((calendarDay, index) => (
                <Box
                  aria-label={calendarDay.dateKey ? `打开 ${calendarDay.dateKey} 的日历` : "空白日期"}
                  className={`home-calendar-cell${calendarDay.isToday ? " is-today" : ""}`}
                  component={calendarDay.dateKey ? "button" : "div"}
                  key={`${calendarDay.day ?? "empty"}-${index}`}
                  onClick={calendarDay.dateKey ? () => navigate(`/calendar?date=${calendarDay.dateKey}`) : undefined}
                  role="gridcell"
                  type={calendarDay.dateKey ? "button" : undefined}
                >
                  {calendarDay.day ? <span className="home-calendar-day">{calendarDay.day}</span> : null}
                  {calendarDay.day ? <span aria-hidden className="home-calendar-task-dots" /> : null}
                </Box>
              ))}
            </Box>
          </Paper>
        </Stack>
      </Paper>
      <Modal centered onClose={() => setIsMonthModalOpen(false)} opened={isMonthModalOpen} title="选择年月" transitionProps={{ duration: 0 }}>
        <Stack gap="md">
          <Group grow>
            <Select aria-label="选择年份" data={yearOptions} onChange={(value) => setDraftYear(value ?? draftYear)} value={draftYear} />
            <Select aria-label="选择月份" data={monthOptions} onChange={(value) => setDraftMonth(value ?? draftMonth)} value={draftMonth} />
          </Group>
          <Group justify="flex-end">
            <Button aria-label="关闭年月选择" onClick={() => setIsMonthModalOpen(false)} variant="default">
              取消
            </Button>
            <Button onClick={applyMonthPicker}>应用</Button>
          </Group>
        </Stack>
      </Modal>
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
              <Link className="home-course-link" to={`/courses/${course.id}`}>
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

        <Text className="home-course-activity">{course.recentActivity}</Text>

        <Group gap="sm">
          <Badge className="home-material-badge" variant="light">
            {course.materialLabel}
          </Badge>
          <Badge className="home-task-badge" variant="light">
            {course.taskLabel}
          </Badge>
          <Text c="dimmed" ml="auto" size="sm">
            {course.progress}
          </Text>
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
  const canSubmit = values.name.trim().length > 0 && !isSubmitting && !hasSelectedLegacyTerm;
  const termData = hasSelectedLegacyTerm
    ? [...termOptions, { value: values.term, label: `${values.term}（旧学期值，请重新选择或清空）` }]
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
          label="课程名称"
          onChange={(event) => onChange("name", event.currentTarget.value)}
          required
          value={values.name}
        />
        <Textarea
          aria-label="课程简介"
          label="课程简介"
          minRows={3}
          onChange={(event) => onChange("description", event.currentTarget.value)}
          value={values.description}
        />
        <TextInput
          aria-label="教师"
          label="教师"
          onChange={(event) => onChange("teacher", event.currentTarget.value)}
          value={values.teacher}
        />
        <Select
          aria-label="学期"
          clearable
          data={termData}
          disabled={isTermLoading || Boolean(termError)}
          error={hasSelectedLegacyTerm ? "旧学期值不能直接保存，请重新选择或清空" : termError}
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
    : courses.filter((course) => course.term === selectedTerm);
  const termSummary = getTermSummaryLabel(selectedTerm, termOptions);

  return (
    <Paper className="home-main-panel" radius="md" withBorder>
      <Group align="flex-start" justify="space-between">
        <Stack gap={4}>
          <Title order={2}>课程概览</Title>
          <Text c="dimmed" size="sm">
            {termSummary} {filteredCourses.length} 门课程 · 资料统计待接入
          </Text>
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
    setCourseFormValues({
      ...createCourseFormFromCourse(course),
      term: course.term && termOptions.some((option) => option.value === course.term) ? course.term : "",
    });
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
        const nextCourse = await updateCourse(editingCourse.id, payload);
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
