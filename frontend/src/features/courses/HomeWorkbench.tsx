import { useEffect, useMemo, useState } from "react";
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
import type { Course } from "../../types/course";
import { createCourse, deleteCourse, listCourses, updateCourse } from "./api";
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
  isToday: boolean;
}

const ALL_TERMS_VALUE = "全部学期";
const isDarkMode = false;
const courseToneClasses = ["blue", "mint", "indigo", "violet", "orange"];

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
      return { day: null, isToday: false };
    }

    return {
      day,
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
          <ActionIcon aria-label={themeLabel} className="home-theme-single-button" radius="md" size={44} variant="default">
            <ThemeIcon size={22} stroke={1.8} />
          </ActionIcon>
          <ActionIcon aria-label="打开个人中心" className="home-user-button" radius="xl" size={48} variant="default">
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
  const referenceDate = new Date();
  const monthLabel = `${referenceDate.getMonth() + 1} 月`;
  const calendarTitle = `${referenceDate.getFullYear()} 年 ${monthLabel}`;
  const calendarDays = getCalendarDays(referenceDate);

  return (
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
            <ActionIcon aria-label="上个月" variant="subtle">
              <IconChevronLeft size={22} />
            </ActionIcon>
            <Text fw={700}>{calendarTitle}</Text>
            <ActionIcon aria-label="下个月" variant="subtle">
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

          <Box aria-label="月历，无学习计划" className="home-calendar-grid" role="grid">
            {calendarDays.map((calendarDay, index) => (
              <Box
                aria-label={calendarDay.day ? String(calendarDay.day) : "空白日期"}
                className="home-calendar-cell"
                key={`${calendarDay.day ?? "empty"}-${index}`}
                role="gridcell"
              >
                {calendarDay.day ? <span className="home-calendar-day">{calendarDay.day}</span> : null}
                {calendarDay.isToday ? <span className="home-calendar-today">今</span> : null}
              </Box>
            ))}
            <Paper className="home-calendar-empty" radius="md" withBorder>
              <Text fw={700}>暂无计划</Text>
            </Paper>
          </Box>
        </Paper>
      </Stack>
    </Paper>
  );
}

function CourseCard({
  course,
  onDelete,
  onEdit,
  toneClass,
}: {
  course: HomeCourse;
  onDelete: (course: HomeCourse) => void;
  onEdit: (course: HomeCourse) => void;
  toneClass: string;
}) {
  return (
    <Card className={`home-course-card home-course-card-${toneClass}`} padding="lg" radius="md" withBorder>
      <Stack gap="lg" h="100%" justify="space-between">
        <Group align="flex-start" justify="space-between" wrap="nowrap">
          <Stack gap="xs">
            <Title order={3}>
              <Link className="home-course-link" to={`/courses/${course.id}`}>
                {course.name}
              </Link>
            </Title>
            <Text c="dimmed" size="sm">
              {course.teacher ?? "未填写教师"} · {course.term ?? "未填写学期"}
            </Text>
          </Stack>
          <Menu position="bottom-end" shadow="sm" width={160} withinPortal>
            <Menu.Target>
              <ActionIcon aria-label={`${course.name} 更多操作`} className="home-card-menu" variant="subtle">
                <IconDotsVertical size={22} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item leftSection={<IconEdit size={16} />} onClick={() => onEdit(course)}>
                编辑课程
              </Menu.Item>
              <Menu.Item color="red" leftSection={<IconTrash size={16} />} onClick={() => onDelete(course)}>
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
          可在创建时同步上传资料
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
  return (
    <Grid.Col span={{ base: 12, md: 6, xl: 4 }}>
      <Paper className="home-course-state-card" radius="md" withBorder>
        <Stack gap="sm">
          <Title order={3}>还没有课程</Title>
          <Text c="dimmed">创建第一门课程后，这里会展示课程资料和学习入口。</Text>
        </Stack>
      </Paper>
    </Grid.Col>
  );
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
  values,
  isSubmitting,
}: {
  error: string | null;
  mode: CourseModalMode;
  onChange: (field: keyof CourseFormValues, value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  opened: boolean;
  values: CourseFormValues;
  isSubmitting: boolean;
}) {
  const isCreate = mode === "create";
  const canSubmit = values.name.trim().length > 0 && !isSubmitting;

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
        <TextInput
          aria-label="学期"
          label="学期"
          onChange={(event) => onChange("term", event.currentTarget.value)}
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
  onRetry,
}: {
  courses: HomeCourse[];
  error: string | null;
  isLoading: boolean;
  onAddCourse: () => void;
  onDeleteCourse: (course: HomeCourse) => void;
  onEditCourse: (course: HomeCourse) => void;
  onRetry: () => void;
}) {
  const [selectedTerm, setSelectedTerm] = useState(ALL_TERMS_VALUE);
  const termOptions = useMemo(() => {
    const terms = courses
      .map((course) => course.term)
      .filter((term): term is string => Boolean(term));

    return Array.from(new Set(terms));
  }, [courses]);
  const termData = [ALL_TERMS_VALUE, ...termOptions];
  const filteredCourses = selectedTerm === ALL_TERMS_VALUE
    ? courses
    : courses.filter((course) => course.term === selectedTerm);
  const termSummary = selectedTerm === ALL_TERMS_VALUE ? ALL_TERMS_VALUE : selectedTerm;

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
          onChange={(value) => setSelectedTerm(value ?? ALL_TERMS_VALUE)}
          rightSection={<IconChevronDown size={18} />}
          value={selectedTerm}
        />
      </Group>

      <Grid gap="lg">
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
                  toneClass={getCourseToneClass(index)}
                />
              </Grid.Col>
            ))
          : null}
        <Grid.Col span={{ base: 12, md: 6, xl: 4 }}>
          <AddCourseCard onClick={onAddCourse} />
        </Grid.Col>
      </Grid>
    </Paper>
  );
}

export function HomeWorkbench() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<HomeCourse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
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
        navigate(`/courses/${createdCourse.id}`);
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
            onRetry={() => setReloadKey((currentKey) => currentKey + 1)}
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
