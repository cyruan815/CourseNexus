import {
  ActionIcon,
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
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
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

import "./home-workbench.css";

interface HomeCourse {
  id: string;
  name: string;
  teacher: string;
  term: string;
  materialCount: number;
  todayTaskCount: number;
  recentActivity: string;
  progress: string;
}

const homeCourses: HomeCourse[] = [
  {
    id: "computer-network",
    name: "计算机网络",
    teacher: "王老师",
    term: "2025-2026 春",
    materialCount: 12,
    todayTaskCount: 1,
    recentActivity: "课件 12 已归档",
    progress: "本周待整理",
  },
  {
    id: "advanced-math",
    name: "高等数学",
    teacher: "李老师",
    term: "2025-2026 春",
    materialCount: 8,
    todayTaskCount: 0,
    recentActivity: "极限章节已复习",
    progress: "进度稳定",
  },
  {
    id: "large-programming",
    name: "大型程序设计",
    teacher: "陈老师",
    term: "2025-2026 春",
    materialCount: 5,
    todayTaskCount: 0,
    recentActivity: "项目说明已上传",
    progress: "等待拆解",
  },
  {
    id: "college-physics",
    name: "大学物理",
    teacher: "赵老师",
    term: "2025-2026 春",
    materialCount: 6,
    todayTaskCount: 0,
    recentActivity: "实验报告待补充",
    progress: "资料完整",
  },
];

const calendarDays = Array.from({ length: 35 }, (_, index) => index + 1);
const isDarkMode = false;
const courseToneClasses = ["blue", "mint", "indigo", "violet", "orange"];

function getCourseToneClass(index: number): string {
  return courseToneClasses[index % courseToneClasses.length];
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
          <Badge className="home-urgent-badge" leftSection={<IconAlertCircle size={14} />}>
            1 项待安排
          </Badge>
        </Group>

        <Stack align="center" className="home-plan-empty" gap="md">
          <IconClipboardList aria-hidden className="home-empty-icon" size={48} stroke={1.6} />
          <Stack gap={4}>
            <Title order={3}>今天还没有学习计划</Title>
            <Text c="dimmed" ta="center">
              先把计算机网络的 1 项任务排进今天
            </Text>
          </Stack>
          <Button className="home-plan-button" component={Link} leftSection={<IconPlus size={16} />} to="/" variant="filled">
            生成今日计划
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
}

function CalendarPanel() {
  return (
    <Paper className="home-calendar-panel" radius="md" withBorder>
      <Stack gap="md" h="100%">
        <Group justify="space-between">
          <Title order={2}>日历</Title>
          <Badge color="blue" variant="light">
            7 月
          </Badge>
        </Group>

        <Paper className="home-calendar-card" radius="md" withBorder>
          <Group justify="space-between">
            <ActionIcon aria-label="上个月" variant="subtle">
              <IconChevronLeft size={22} />
            </ActionIcon>
            <Text fw={700}>2026 年 7 月</Text>
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
            {calendarDays.map((day) => (
              <Box className="home-calendar-cell" key={day} role="gridcell">
                {day === 17 ? <span className="home-calendar-today">今</span> : null}
                {day === 18 ? <span className="home-calendar-dot" /> : null}
              </Box>
            ))}
            <Paper className="home-calendar-empty" radius="md" withBorder>
              <Text fw={700}>待排计划</Text>
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
              {course.teacher} · {course.term}
            </Text>
          </Stack>
          <ActionIcon aria-label={`${course.name} 更多操作`} className="home-card-menu" variant="subtle">
            <IconDotsVertical size={22} />
          </ActionIcon>
        </Group>

        <Text className="home-course-activity">{course.recentActivity}</Text>

        <Group gap="sm">
          <Badge className="home-material-badge" variant="light">
            资料 {course.materialCount}
          </Badge>
          <Badge className={course.todayTaskCount > 0 ? "home-task-badge-active" : "home-task-badge"} variant="light">
            今日任务 {course.todayTaskCount}
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

function CourseOverview() {
  return (
    <Paper className="home-main-panel" radius="md" withBorder>
      <Group align="flex-start" justify="space-between">
        <Stack gap={4}>
          <Title order={2}>课程概览</Title>
          <Text c="dimmed" size="sm">
            本学期 4 门课程 · 32 份资料
          </Text>
        </Stack>
        <Select
          aria-label="选择学期"
          className="home-term-select"
          data={["2025-2026 春", "2025-2026 秋", "2024-2025 春"]}
          defaultValue="2025-2026 春"
          rightSection={<IconChevronDown size={18} />}
        />
      </Group>

      <Grid gap="lg">
        {homeCourses.map((course, index) => (
          <Grid.Col key={course.id} span={{ base: 12, md: 6, xl: 4 }}>
            <CourseCard course={course} toneClass={getCourseToneClass(index)} />
          </Grid.Col>
        ))}
        <Grid.Col span={{ base: 12, md: 6, xl: 4 }}>
          <AddCourseCard />
        </Grid.Col>
      </Grid>
    </Paper>
  );
}

export function HomeWorkbench() {
  return (
    <Box className="home-workbench">
      <Header />
      <Container className="home-shell" fluid>
        <Box className="home-layout">
          <Box className="home-side-panel">
            <TodayTodoPanel />
            <CalendarPanel />
          </Box>
          <CourseOverview />
        </Box>
      </Container>
    </Box>
  );
}
