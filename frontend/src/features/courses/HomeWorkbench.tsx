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
  Paper,
  Select,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconClipboardList,
  IconDotsVertical,
  IconMoon,
  IconPlus,
  IconSun,
  IconUser,
} from "@tabler/icons-react";
import { Link } from "react-router-dom";

import { ApiError } from "../../api/errors";
import type { Course } from "../../types/course";
import { listCourses } from "./api";
import "./home-workbench.css";

interface HomeCourse {
  id: string;
  name: string;
  teacher: string | null;
  term: string | null;
  materialLabel: string;
  taskLabel: string;
  recentActivity: string;
  progress: string;
}

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

function mapCourseToHomeCourse(course: Course): HomeCourse {
  return {
    id: course.id,
    name: course.name,
    teacher: course.teacher,
    term: course.term,
    materialLabel: "资料待接入",
    taskLabel: "今日任务待接入",
    recentActivity: course.description?.trim() || "课程资料待上传",
    progress: course.status === "active" ? "课程已创建" : course.status,
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

function CourseCard({ course, toneClass }: { course: HomeCourse; toneClass: string }) {
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
          <ActionIcon aria-label={`${course.name} 更多操作`} className="home-card-menu" variant="subtle">
            <IconDotsVertical size={22} />
          </ActionIcon>
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

function AddCourseCard() {
  return (
    <Paper className="home-add-course" component={Link} radius="md" to="/" withBorder>
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

function CourseOverview({
  courses,
  error,
  isLoading,
  onRetry,
}: {
  courses: HomeCourse[];
  error: string | null;
  isLoading: boolean;
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
                <CourseCard course={course} toneClass={getCourseToneClass(index)} />
              </Grid.Col>
            ))
          : null}
        <Grid.Col span={{ base: 12, md: 6, xl: 4 }}>
          <AddCourseCard />
        </Grid.Col>
      </Grid>
    </Paper>
  );
}

export function HomeWorkbench() {
  const [courses, setCourses] = useState<HomeCourse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

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
            onRetry={() => setReloadKey((currentKey) => currentKey + 1)}
          />
        </Box>
      </Container>
    </Box>
  );
}
