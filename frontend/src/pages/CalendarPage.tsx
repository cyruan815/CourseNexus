import { useEffect, useMemo, useState } from "react";
import { ActionIcon, Alert, Badge, Box, Button, Group, Paper, Select, Skeleton, Stack, Text, Title } from "@mantine/core";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import { Link, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { WorkbenchTopbar } from "../components/WorkbenchTopbar";
import { listCourses } from "../features/courses/api";
import "../features/courses/home-workbench.css";
import {
  fetchCourseStudyCalendar,
  fetchCourseStudyCalendarDay,
  fetchGlobalCalendarDayTodos,
  fetchGlobalCalendarMonth,
} from "../features/study-plans/api";
import type {
  CourseStudyCalendarDay,
  CourseStudyCalendarMonth,
  GlobalDayTodos,
  StudyCalendarDaySummary,
  StudyCalendarTaskTodo,
} from "../features/study-plans/types";
import type { Course } from "../types/course";

interface CalendarCell {
  dateKey: string | null;
  day: number | null;
  isToday: boolean;
}

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

function formatMonth(date: Date): string {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}`;
}

function formatDateKey(year: number, month: number, day: number): string {
  return `${year}-${padDatePart(month + 1)}-${padDatePart(day)}`;
}

function isDateKey(value: string | null): value is string {
  return Boolean(value && /^\d{4}-\d{2}-\d{2}$/.test(value));
}

function todayDateKey(today = new Date()): string {
  return formatDateKey(today.getFullYear(), today.getMonth(), today.getDate());
}

function monthFromDateQuery(dateQuery: string | null): Date {
  if (isDateKey(dateQuery)) {
    const [year, month] = dateQuery.split("-").map(Number);
    return new Date(year, month - 1, 1);
  }

  const today = new Date();
  return new Date(today.getFullYear(), today.getMonth(), 1);
}

function buildCalendarCells(referenceDate: Date, today = new Date()): CalendarCell[] {
  const year = referenceDate.getFullYear();
  const month = referenceDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDate = new Date(year, month + 1, 0).getDate();
  const leadingEmptyCells = firstDay.getDay();
  const totalCells = Math.ceil((leadingEmptyCells + lastDate) / 7) * 7;

  return Array.from({ length: totalCells }, (_, index) => {
    const day = index - leadingEmptyCells + 1;

    if (day < 1 || day > lastDate) {
      return { dateKey: null, day: null, isToday: false };
    }

    return {
      dateKey: formatDateKey(year, month, day),
      day,
      isToday: year === today.getFullYear() && month === today.getMonth() && day === today.getDate(),
    };
  });
}

function calendarSummaryTaskLines(summary: StudyCalendarDaySummary, maxLines: number): string[] {
  const taskTitles = summary.task_summaries
    .map((task) => `${task.plan_title} · ${task.title}`)
    .filter((title) => title.trim().length > 0);
  const fallback = taskTitles.length > 0 ? taskTitles : [`${summary.task_count} 个任务`];
  const hasMore = summary.hidden_task_count > 0 || fallback.length > maxLines;
  const visibleCount = hasMore ? Math.max(maxLines - 1, 1) : maxLines;
  const visibleLines = fallback.slice(0, visibleCount);

  return hasMore ? [...visibleLines, "..."] : visibleLines;
}

function CalendarCellSummary({ maxTaskLines = 3, summary }: { maxTaskLines?: number; summary: StudyCalendarDaySummary }) {
  const taskLines = calendarSummaryTaskLines(summary, maxTaskLines);

  return (
    <span className="calendar-cell-summary">
      <span className="calendar-cell-task-list" aria-label={`${summary.task_count} 个一级任务`}>
        {taskLines.map((line, index) => (
          <span
            className={line === "..." ? "calendar-cell-task-more" : "calendar-cell-task-title"}
            key={`${line}-${index}`}
            title={line === "..." ? undefined : line}
          >
            {line}
          </span>
        ))}
      </span>
      <span className="calendar-cell-task-progress">
        {summary.completed_subtask_count}/{summary.subtask_count} 完成
      </span>
    </span>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "日历加载失败";
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

function getTaskPrimaryHref(task: StudyCalendarTaskTodo, fallbackCourseId: string): string {
  return getTaskExecutionHref(task) ?? `/courses/${fallbackCourseId}/study-plans/${task.plan_id}`;
}

function getTaskPrimaryActionLabel(task: StudyCalendarTaskTodo): string {
  return getTaskExecutionHref(task) ? "继续学习" : "查看计划";
}

function subtaskTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    learn: "学习",
    quiz: "小测",
    review: "复习",
    test: "测试",
  };

  return labels[type] ?? type;
}

function courseDayToGlobalTodos(dayTodos: CourseStudyCalendarDay): GlobalDayTodos {
  return {
    date: dayTodos.date,
    courses: [
      {
        course_id: dayTodos.course_id,
        course_name: dayTodos.course_name,
        plan_ids: Array.from(new Set(dayTodos.tasks.map((task) => task.plan_id))),
        tasks: dayTodos.tasks,
      },
    ],
  };
}

function CourseCalendarDayPanel({
  courseId,
  dayTodos,
  error,
  isLoading,
  selectedDate,
}: {
  courseId: string;
  dayTodos: CourseStudyCalendarDay | null;
  error: string | null;
  isLoading: boolean;
  selectedDate: string | null;
}) {
  if (!selectedDate) {
    return (
      <Paper className="calendar-day-panel" radius="md" withBorder>
        <Stack gap="xs">
          <Title order={2}>选择日期</Title>
          <Text c="dimmed" size="sm">点击月历中的日期查看本课程当天任务。</Text>
        </Stack>
      </Paper>
    );
  }

  return (
    <Paper className="calendar-day-panel" radius="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between" wrap="nowrap">
          <Title order={2}>{selectedDate} 任务</Title>
          {dayTodos ? <Badge color="blue" variant="light">{dayTodos.tasks.length} 个一级任务</Badge> : null}
        </Group>
        {isLoading ? (
          <Stack gap="sm" role="status">
            <Text c="dimmed">正在加载当天任务...</Text>
            <Skeleton height={80} radius="md" />
            <Skeleton height={80} radius="md" />
          </Stack>
        ) : null}
        {!isLoading && error ? (
          <Alert color="red" role="alert" title="当天任务加载失败" variant="light">
            {error}
          </Alert>
        ) : null}
        {!isLoading && !error && dayTodos && dayTodos.tasks.length === 0 ? (
          <Stack className="calendar-empty-state" gap="xs">
            <Text fw={700}>当天没有学习任务</Text>
            <Text c="dimmed" size="sm">该课程在这一天没有一级任务。</Text>
          </Stack>
        ) : null}
        {!isLoading && !error && dayTodos && dayTodos.tasks.length > 0 ? (
          <Stack gap="sm">
            {dayTodos.tasks.map((task) => (
              <CourseCalendarTaskCard courseId={courseId} key={task.task_id} task={task} />
            ))}
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}

function CourseCalendarTaskCard({ courseId, task }: { courseId: string; task: StudyCalendarTaskTodo }) {
  const actionLabel = getTaskPrimaryActionLabel(task);

  return (
    <Paper className="calendar-task-card" radius="md" withBorder>
      <Stack gap="sm">
        <Group justify="space-between" wrap="nowrap">
          <Stack gap={2}>
            <Text className="calendar-primary-task-title" fw={750}>{task.title}</Text>
            <Text c="dimmed" size="xs">所属计划：{task.plan_title}</Text>
            <Text className="calendar-task-progress-count" c="dimmed" size="sm">
              {task.completed_subtask_count}/{task.total_subtask_count}
            </Text>
          </Stack>
          <Badge color={statusColor(task.derived_status)} variant="light">
            {statusLabel(task.derived_status)}
          </Badge>
        </Group>
        <Stack className="calendar-subtask-list" gap={0}>
          {task.subtasks.map((subtask) => (
            <Box className="calendar-subtask-row" key={subtask.subtask_id}>
              <Group justify="space-between" wrap="nowrap">
                <Stack gap={2}>
                  <Text className="calendar-subtask-title" fw={650} size="sm">{subtask.title}</Text>
                  <Text c="dimmed" size="xs">{subtaskTypeLabel(subtask.subtask_type)}</Text>
                </Stack>
                <Badge color={statusColor(subtask.status)} size="xs" variant="light">
                  {statusLabel(subtask.status)}
                </Badge>
              </Group>
            </Box>
          ))}
        </Stack>
        <Group aria-label={`${task.title}操作`} className="calendar-task-actions" justify="flex-end" role="group">
          <Button
            aria-label={`查看计划详情 ${task.title}`}
            component={Link}
            size="xs"
            to={`/courses/${courseId}/study-plans/${task.plan_id}`}
            variant="subtle"
          >
            查看计划详情
          </Button>
          <Button
            aria-label={`${actionLabel} ${task.title}`}
            component={Link}
            size="xs"
            to={getTaskPrimaryHref(task, courseId)}
            variant="light"
          >
            {actionLabel}
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}

function CourseCalendarPage({ courseId }: { courseId: string }) {
  const [searchParams] = useSearchParams();
  const initialDate = searchParams.get("date");
  const [referenceDate, setReferenceDate] = useState(() => monthFromDateQuery(initialDate));
  const [monthData, setMonthData] = useState<CourseStudyCalendarMonth | null>(null);
  const [monthError, setMonthError] = useState<string | null>(null);
  const [isMonthLoading, setIsMonthLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(() => (isDateKey(initialDate) ? initialDate : todayDateKey()));
  const [dayTodos, setDayTodos] = useState<CourseStudyCalendarDay | null>(null);
  const [dayError, setDayError] = useState<string | null>(null);
  const [isDayLoading, setIsDayLoading] = useState(false);
  const month = formatMonth(referenceDate);
  const calendarCells = useMemo(() => buildCalendarCells(referenceDate), [referenceDate]);
  const summariesByDate = useMemo(() => {
    const summaries = new Map<string, StudyCalendarDaySummary>();
    monthData?.days.forEach((day) => summaries.set(day.date, day));
    return summaries;
  }, [monthData]);

  useEffect(() => {
    let ignore = false;

    setIsMonthLoading(true);
    setMonthError(null);

    fetchCourseStudyCalendar(courseId, month)
      .then((nextMonthData) => {
        if (!ignore) {
          setMonthData(nextMonthData);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setMonthError(errorMessage(nextError));
          setMonthData(null);
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
  }, [courseId, month]);

  useEffect(() => {
    if (!selectedDate) {
      return undefined;
    }

    let ignore = false;
    setIsDayLoading(true);
    setDayError(null);
    setDayTodos(null);

    fetchCourseStudyCalendarDay(courseId, selectedDate)
      .then((nextDayTodos) => {
        if (!ignore) {
          setDayTodos(nextDayTodos);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setDayError(errorMessage(nextError));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsDayLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [courseId, selectedDate]);

  function moveMonth(offset: number) {
    setReferenceDate((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1));
    setSelectedDate(null);
    setDayTodos(null);
    setDayError(null);
  }

  function loadDay(dateKey: string) {
    setSelectedDate(dateKey);
  }

  const courseName = monthData?.course_name ?? "课程";

  return (
    <Box className="home-workbench calendar-placeholder-page workbench-page">
      <WorkbenchTopbar
        backFallbackTo={`/courses/${courseId}`}
        contextName={courseName}
        meta={<Badge color="blue" variant="light">{month}</Badge>}
        pageName="学习日历"
      />
      <Box className="calendar-course-shell" component="main" data-workbench-scroll="locked">
        <Paper className="calendar-month-panel" radius="md" withBorder>
          <Stack gap="md">
            <Group justify="space-between" wrap="nowrap">
              <ActionIcon aria-label="上个月" onClick={() => moveMonth(-1)} variant="subtle">
                <IconChevronLeft size={22} />
              </ActionIcon>
              <Title order={2}>{referenceDate.getFullYear()} 年 {referenceDate.getMonth() + 1} 月</Title>
              <ActionIcon aria-label="下个月" onClick={() => moveMonth(1)} variant="subtle">
                <IconChevronRight size={22} />
              </ActionIcon>
            </Group>

            {isMonthLoading ? (
              <Stack gap="sm" role="status">
                <Text c="dimmed">正在加载课程日历...</Text>
                <Skeleton height={320} radius="md" />
              </Stack>
            ) : null}
            {!isMonthLoading && monthError ? (
              <Alert color="red" role="alert" title="课程日历加载失败" variant="light">
                {monthError}
              </Alert>
            ) : null}
            {!isMonthLoading && !monthError ? (
              <>
                <Box className="home-calendar-weekdays" aria-hidden>
                  {["日", "一", "二", "三", "四", "五", "六"].map((day) => (
                    <Text c="dimmed" fw={500} key={day} size="sm" ta="center">
                      {day}
                    </Text>
                  ))}
                </Box>
                <Box aria-label="课程月历" className="home-calendar-grid calendar-course-grid" role="grid">
                  {calendarCells.map((cell, index) => {
                    const summary = cell.dateKey ? summariesByDate.get(cell.dateKey) : undefined;
                    return (
                      <Box
                        aria-label={cell.dateKey ? `查看 ${cell.dateKey} 的课程任务` : "空白日期"}
                        className={`home-calendar-cell calendar-course-cell${cell.isToday ? " is-today" : ""}${cell.dateKey && cell.dateKey === selectedDate ? " is-selected" : ""}${summary ? " has-tasks" : ""}`}
                        component={cell.dateKey ? "button" : "div"}
                        key={`${cell.dateKey ?? "empty"}-${index}`}
                        onClick={cell.dateKey ? () => loadDay(cell.dateKey as string) : undefined}
                        role="gridcell"
                        type={cell.dateKey ? "button" : undefined}
                      >
                        {cell.day ? <span className="home-calendar-day">{cell.day}</span> : null}
                        {summary ? <CalendarCellSummary summary={summary} /> : null}
                      </Box>
                    );
                  })}
                </Box>
                {monthData && monthData.days.length === 0 ? (
                  <Stack className="calendar-empty-state" gap="xs">
                    <Text fw={700}>本月没有学习任务</Text>
                    <Text c="dimmed" size="sm">该课程当前月份没有计划任务。</Text>
                  </Stack>
                ) : null}
              </>
            ) : null}
          </Stack>
        </Paper>
        <CourseCalendarDayPanel
          courseId={courseId}
          dayTodos={dayTodos}
          error={dayError}
          isLoading={isDayLoading}
          selectedDate={selectedDate}
        />
      </Box>
    </Box>
  );
}

function GlobalCalendarDayPanel({
  dayTodos,
  error,
  filteredCourseName,
  isLoading,
  selectedDate,
}: {
  dayTodos: GlobalDayTodos | null;
  error: string | null;
  filteredCourseName: string | null;
  isLoading: boolean;
  selectedDate: string | null;
}) {
  if (!selectedDate) {
    return (
      <Paper className="calendar-day-panel" radius="md" withBorder>
        <Stack gap="xs">
          <Title order={2}>选择日期</Title>
          <Text c="dimmed" size="sm">点击月历中的日期查看全局当天待办。</Text>
        </Stack>
      </Paper>
    );
  }

  return (
    <Paper className="calendar-day-panel" radius="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between" wrap="nowrap">
          <Title order={2}>{selectedDate} {filteredCourseName ? "任务" : "待办"}</Title>
          {dayTodos ? <Badge color="blue" variant="light">{dayTodos.courses.length} 门课程</Badge> : null}
        </Group>
        {isLoading ? (
          <Stack gap="sm" role="status">
            <Text c="dimmed">正在加载当天待办...</Text>
            <Skeleton height={80} radius="md" />
            <Skeleton height={80} radius="md" />
          </Stack>
        ) : null}
        {!isLoading && error ? (
          <Alert color="red" role="alert" title="当天待办加载失败" variant="light">
            {error}
          </Alert>
        ) : null}
        {!isLoading && !error && dayTodos && dayTodos.courses.length === 0 ? (
          <Stack className="calendar-empty-state" gap="xs">
            <Text fw={700}>当天没有学习任务</Text>
            <Text c="dimmed" size="sm">
              {filteredCourseName ? `${filteredCourseName} 在这一天没有一级任务。` : "所有课程在这一天都没有一级任务。"}
            </Text>
          </Stack>
        ) : null}
        {!isLoading && !error && dayTodos && dayTodos.courses.length > 0 ? (
          <Stack gap="md">
            {dayTodos.courses.map((course, courseIndex) => (
              <Stack gap="sm" key={course.course_id}>
                <Title className={`calendar-course-name calendar-course-name-${courseIndex % 5}`} order={3}>
                  {course.course_name}
                </Title>
                {course.tasks.map((task) => (
                  <CourseCalendarTaskCard courseId={course.course_id} key={task.task_id} task={task} />
                ))}
              </Stack>
            ))}
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}

function GlobalCalendarPage() {
  const [searchParams] = useSearchParams();
  const initialDate = searchParams.get("date");
  const initialCourseId = searchParams.get("courseId");
  const [referenceDate, setReferenceDate] = useState(() => monthFromDateQuery(initialDate));
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseError, setCourseError] = useState<string | null>(null);
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(initialCourseId);
  const [monthDays, setMonthDays] = useState<StudyCalendarDaySummary[]>([]);
  const [monthError, setMonthError] = useState<string | null>(null);
  const [isMonthLoading, setIsMonthLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(() => (isDateKey(initialDate) ? initialDate : todayDateKey()));
  const [dayTodos, setDayTodos] = useState<GlobalDayTodos | null>(null);
  const [dayError, setDayError] = useState<string | null>(null);
  const [isDayLoading, setIsDayLoading] = useState(false);
  const month = formatMonth(referenceDate);
  const selectedCourse = useMemo(
    () => courses.find((course) => course.id === selectedCourseId) ?? null,
    [courses, selectedCourseId],
  );
  const selectedCourseName = selectedCourse?.name ?? null;
  const courseOptions = useMemo(
    () => [
      { value: "__all__", label: "全部课程" },
      ...courses.map((course) => ({ value: course.id, label: course.name })),
    ],
    [courses],
  );
  const calendarCells = useMemo(() => buildCalendarCells(referenceDate), [referenceDate]);
  const summariesByDate = useMemo(() => {
    const summaries = new Map<string, StudyCalendarDaySummary>();
    monthDays.forEach((day) => summaries.set(day.date, day));
    return summaries;
  }, [monthDays]);

  useEffect(() => {
    let ignore = false;

    setCourseError(null);
    listCourses()
      .then((nextCourses) => {
        if (!ignore) {
          setCourses(nextCourses);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setCourseError(errorMessage(nextError));
          setCourses([]);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    let ignore = false;

    setIsMonthLoading(true);
    setMonthError(null);

    const monthRequest = selectedCourseId
      ? fetchCourseStudyCalendar(selectedCourseId, month).then((monthData) => monthData.days)
      : fetchGlobalCalendarMonth(month).then((monthData) => monthData.days);

    monthRequest
      .then((days) => {
        if (!ignore) {
          setMonthDays(days);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setMonthError(errorMessage(nextError));
          setMonthDays([]);
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
  }, [month, selectedCourseId]);

  useEffect(() => {
    if (!selectedDate) {
      return undefined;
    }

    let ignore = false;
    setIsDayLoading(true);
    setDayError(null);
    setDayTodos(null);

    const dayRequest = selectedCourseId
      ? fetchCourseStudyCalendarDay(selectedCourseId, selectedDate).then(courseDayToGlobalTodos)
      : fetchGlobalCalendarDayTodos(selectedDate);

    dayRequest
      .then((todos) => {
        if (!ignore) {
          setDayTodos(todos);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setDayError(errorMessage(nextError));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsDayLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [selectedCourseId, selectedDate]);

  function moveMonth(offset: number) {
    setReferenceDate((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1));
    setSelectedDate(null);
    setDayTodos(null);
    setDayError(null);
  }

  function handleCourseFilterChange(value: string | null) {
    setSelectedCourseId(value && value !== "__all__" ? value : null);
    setDayTodos(null);
    setDayError(null);
  }

  return (
    <Box className="home-workbench calendar-placeholder-page workbench-page">
      <WorkbenchTopbar
        contextName={selectedCourseName ?? "全局"}
        meta={<Badge color="blue" variant="light">{month}</Badge>}
        pageName="学习日历"
      />
      <Box className="calendar-course-shell" component="main" data-workbench-scroll="locked">
        <Paper className="calendar-month-panel" radius="md" withBorder>
          <Stack gap="md">
            <Group justify="space-between" wrap="nowrap">
              <ActionIcon aria-label="上个月" onClick={() => moveMonth(-1)} variant="subtle">
                <IconChevronLeft size={22} />
              </ActionIcon>
              <Title order={2}>{referenceDate.getFullYear()} 年 {referenceDate.getMonth() + 1} 月</Title>
              <ActionIcon aria-label="下个月" onClick={() => moveMonth(1)} variant="subtle">
                <IconChevronRight size={22} />
              </ActionIcon>
            </Group>
            <Group align="flex-end" className="calendar-filter-row" justify="space-between" wrap="nowrap">
              <Select
                aria-label="课程筛选"
                className="calendar-course-filter"
                data={courseOptions}
                onChange={handleCourseFilterChange}
                value={selectedCourseId ?? "__all__"}
              />
              <Button
                aria-label="清除课程筛选"
                className="calendar-clear-filter-button"
                disabled={!selectedCourseId}
                onClick={() => handleCourseFilterChange("__all__")}
                variant="subtle"
              >
                清除筛选
              </Button>
            </Group>
            {courseError ? (
              <Alert color="yellow" role="status" title="课程筛选加载失败" variant="light">
                {courseError}
              </Alert>
            ) : null}

            {isMonthLoading ? (
              <Stack gap="sm" role="status">
                <Text c="dimmed">正在加载全局日历...</Text>
                <Skeleton height={320} radius="md" />
              </Stack>
            ) : null}
            {!isMonthLoading && monthError ? (
              <Alert color="red" role="alert" title="全局日历加载失败" variant="light">
                {monthError}
              </Alert>
            ) : null}
            {!isMonthLoading && !monthError ? (
              <>
                <Box className="home-calendar-weekdays" aria-hidden>
                  {["日", "一", "二", "三", "四", "五", "六"].map((day) => (
                    <Text c="dimmed" fw={500} key={day} size="sm" ta="center">
                      {day}
                    </Text>
                  ))}
                </Box>
                <Box aria-label="全局月历" className="home-calendar-grid calendar-course-grid" role="grid">
                  {calendarCells.map((cell, index) => {
                    const summary = cell.dateKey ? summariesByDate.get(cell.dateKey) : undefined;
                    return (
                      <Box
                        aria-label={cell.dateKey ? `查看 ${cell.dateKey} 的${selectedCourseId ? "课程任务" : "全局待办"}` : "空白日期"}
                        className={`home-calendar-cell calendar-course-cell${cell.isToday ? " is-today" : ""}${cell.dateKey && cell.dateKey === selectedDate ? " is-selected" : ""}${summary ? " has-tasks" : ""}`}
                        component={cell.dateKey ? "button" : "div"}
                        key={`${cell.dateKey ?? "empty"}-${index}`}
                        onClick={cell.dateKey ? () => setSelectedDate(cell.dateKey as string) : undefined}
                        role="gridcell"
                        type={cell.dateKey ? "button" : undefined}
                      >
                        {cell.day ? <span className="home-calendar-day">{cell.day}</span> : null}
                        {summary ? <CalendarCellSummary summary={summary} /> : null}
                      </Box>
                    );
                  })}
                </Box>
                {monthDays.length === 0 ? (
                  <Stack className="calendar-empty-state" gap="xs">
                    <Text fw={700}>本月没有学习任务</Text>
                    <Text c="dimmed" size="sm">所有课程当前月份都没有计划任务。</Text>
                  </Stack>
                ) : null}
              </>
            ) : null}
          </Stack>
        </Paper>
        <GlobalCalendarDayPanel
          dayTodos={dayTodos}
          error={dayError}
          filteredCourseName={selectedCourseName}
          isLoading={isDayLoading}
          selectedDate={selectedDate}
        />
      </Box>
    </Box>
  );
}

export function CalendarPage() {
  return <GlobalCalendarPage />;
}
