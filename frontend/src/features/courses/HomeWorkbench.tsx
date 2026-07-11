import {
  ActionIcon,
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
  tone: "blue" | "mint" | "indigo" | "violet";
}

const homeCourses: HomeCourse[] = [
  {
    id: "computer-network",
    name: "计算机网络",
    teacher: "王老师",
    term: "2025-2026 春",
    materialCount: 12,
    todayTaskCount: 1,
    tone: "blue",
  },
  {
    id: "advanced-math",
    name: "高等数学",
    teacher: "李老师",
    term: "2025-2026 春",
    materialCount: 8,
    todayTaskCount: 0,
    tone: "indigo",
  },
  {
    id: "large-programming",
    name: "大型程序设计",
    teacher: "陈老师",
    term: "2025-2026 春",
    materialCount: 5,
    todayTaskCount: 0,
    tone: "mint",
  },
  {
    id: "college-physics",
    name: "大学物理",
    teacher: "赵老师",
    term: "2025-2026 春",
    materialCount: 6,
    todayTaskCount: 0,
    tone: "violet",
  },
];

const calendarDays = Array.from({ length: 35 }, (_, index) => index + 1);

function Header() {
  return (
    <Paper className="home-header" component="header" radius={0}>
      <Group justify="space-between" wrap="nowrap">
        <Group gap="lg" wrap="nowrap">
          <Box aria-hidden className="home-brand-mark">
            课
          </Box>
          <Title className="home-brand-title" order={1}>
            课枢 CourseNexus
          </Title>
        </Group>

        <Group gap="md" wrap="nowrap">
          <Group className="home-theme-toggle" gap={4} wrap="nowrap">
            <ActionIcon aria-label="切换为日间模式" className="home-theme-button home-theme-button-active" radius="sm" size="lg" variant="subtle">
              <IconSun size={22} stroke={1.8} />
            </ActionIcon>
            <ActionIcon aria-label="切换为夜间模式" className="home-theme-button" radius="sm" size="lg" variant="subtle">
              <IconMoon size={22} stroke={1.8} />
            </ActionIcon>
          </Group>
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
    <Stack gap="md">
      <Title order={2}>今日待办</Title>
      <Paper className="home-empty-card" radius="md" withBorder>
        <Stack align="center" gap="sm">
          <IconClipboardList aria-hidden className="home-empty-icon" size={54} stroke={1.4} />
          <Title order={3}>还没有学习计划</Title>
          <Text c="dimmed" ta="center">
            生成计划后，这里显示今天要学的任务
          </Text>
          <Button className="home-plan-button" component={Link} to="/" variant="filled">
            生成一个计划吧
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}

function CalendarPanel() {
  return (
    <Stack gap="md">
      <Title order={2}>日历</Title>
      <Paper className="home-calendar-card" radius="md" withBorder>
        <Group justify="space-between">
          <ActionIcon aria-label="上个月" variant="subtle">
            <IconChevronLeft size={22} />
          </ActionIcon>
          <Text fw={600}>2026 年 7 月</Text>
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
            <Box className="home-calendar-cell" key={day} role="gridcell" />
          ))}
          <Paper className="home-calendar-empty" radius="md" withBorder>
            <Text fw={600}>无计划</Text>
          </Paper>
        </Box>
      </Paper>
    </Stack>
  );
}

function CourseCard({ course }: { course: HomeCourse }) {
  return (
    <Card className={`home-course-card home-course-card-${course.tone}`} padding="xl" radius="md" withBorder>
      <Group align="flex-start" justify="space-between" wrap="nowrap">
        <Stack gap="md">
          <Title order={3}>
            <Link className="home-course-link" to={`/courses/${course.id}`}>
              {course.name}
            </Link>
          </Title>
          <Text>教师： {course.teacher}</Text>
          <Text>学期： {course.term}</Text>
          <Text>
            资料 {course.materialCount} · 今日任务 {course.todayTaskCount}
          </Text>
        </Stack>
        <ActionIcon aria-label={`${course.name} 更多操作`} className="home-card-menu" variant="subtle">
          <IconDotsVertical size={24} />
        </ActionIcon>
      </Group>
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
          <Text fw={600}>我的课程</Text>
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
        {homeCourses.map((course) => (
          <Grid.Col key={course.id} span={{ base: 12, md: 6, xl: 4 }}>
            <CourseCard course={course} />
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
        <Grid gap="lg">
          <Grid.Col span={{ base: 12, lg: 4 }}>
            <Paper className="home-side-panel" radius="md" withBorder>
              <TodayTodoPanel />
              <CalendarPanel />
            </Paper>
          </Grid.Col>
          <Grid.Col span={{ base: 12, lg: 8 }}>
            <CourseOverview />
          </Grid.Col>
        </Grid>
      </Container>
    </Box>
  );
}
