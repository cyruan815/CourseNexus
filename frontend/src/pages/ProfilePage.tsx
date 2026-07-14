import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Badge,
  Box,
  Button,
  Group,
  Paper,
  Progress,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconLogout, IconUserCircle } from "@tabler/icons-react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/errors";
import { fetchCurrentUser, logout } from "../features/auth/api";
import type { AuthUser } from "../features/auth/api";
import { fetchCheckinDay, fetchCheckinRange } from "../features/profile/api";
import type { CheckinRangeRead, CheckinRead } from "../features/profile/api";
import "./profile.css";

const DAY_MS = 24 * 60 * 60 * 1000;

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dateDaysAgo(days: number): Date {
  const today = new Date();
  return new Date(today.getFullYear(), today.getMonth(), today.getDate() - days);
}

function buildDateRange(startDate: string, endDate: string): string[] {
  const dates: string[] = [];
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);

  for (let time = start.getTime(); time <= end.getTime(); time += DAY_MS) {
    dates.push(formatDate(new Date(time)));
  }

  return dates;
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function completionPercent(checkin: CheckinRead | null): number {
  if (!checkin || checkin.total_subtask_count === 0) {
    return 0;
  }

  return Math.round((Number(checkin.completion_ratio) || 0) * 100);
}

function colorLevelLabel(level: number): string {
  if (level >= 5) return "全部完成";
  if (level >= 4) return "接近完成";
  if (level >= 2) return "学习中";
  if (level === 1) return "未开始";
  return "无任务";
}

export function ProfilePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [todayCheckin, setTodayCheckin] = useState<CheckinRead | null>(null);
  const [rangeCheckins, setRangeCheckins] = useState<CheckinRangeRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const endDate = useMemo(() => formatDate(dateDaysAgo(0)), []);
  const startDate = useMemo(() => formatDate(dateDaysAgo(13)), []);
  const rangeDates = useMemo(() => buildDateRange(startDate, endDate), [endDate, startDate]);
  const checkinsByDate = useMemo(() => {
    const map = new Map<string, CheckinRead>();
    for (const item of rangeCheckins?.items ?? []) {
      map.set(item.checkin_date, item);
    }
    return map;
  }, [rangeCheckins?.items]);

  useEffect(() => {
    let ignore = false;

    setIsLoading(true);
    setError(null);

    Promise.all([
      fetchCurrentUser(),
      fetchCheckinDay(endDate),
      fetchCheckinRange(startDate, endDate),
    ])
      .then(([nextUser, nextTodayCheckin, nextRangeCheckins]) => {
        if (!ignore) {
          setUser(nextUser);
          setTodayCheckin(nextTodayCheckin);
          setRangeCheckins(nextRangeCheckins);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(errorMessage(nextError, "个人中心加载失败"));
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
  }, [endDate, startDate]);

  async function handleLogout() {
    setIsLoggingOut(true);

    try {
      await logout();
      navigate("/welcome", { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  }

  if (isLoading) {
    return (
      <Box className="profile-page">
        <Box className="profile-shell">
          <Skeleton height={36} width={240} />
          <Skeleton height={420} radius="md" />
        </Box>
      </Box>
    );
  }

  if (error || !user) {
    return (
      <Box className="profile-page">
        <Box className="profile-shell">
          <Alert color="red" role="alert" title="个人中心加载失败" variant="light">
            {error ?? "用户信息不存在"}
          </Alert>
        </Box>
      </Box>
    );
  }

  const percent = completionPercent(todayCheckin);
  const summary = rangeCheckins?.summary;

  return (
    <Box className="profile-page">
      <Box className="profile-shell" component="main">
        <Group className="profile-nav" justify="space-between">
          <Button component={Link} leftSection={<IconArrowLeft size={16} />} to="/" variant="subtle">
            返回首页
          </Button>
          <Button
            color="red"
            leftSection={<IconLogout size={16} />}
            loading={isLoggingOut}
            onClick={() => void handleLogout()}
            variant="light"
          >
            退出登录
          </Button>
        </Group>

        <Paper className="profile-hero" radius="md" withBorder>
          <Group align="center" gap="lg" wrap="nowrap">
            <Avatar className="profile-avatar" radius="xl" size={72} src={user.avatar_url}>
              <IconUserCircle size={42} />
            </Avatar>
            <Stack gap={4}>
              <Title order={1}>个人中心</Title>
              <Text fw={750}>{user.nickname || user.username}</Text>
              <Text c="dimmed" size="sm">{user.username}</Text>
            </Stack>
          </Group>
          <Badge color={user.status === "active" ? "teal" : "gray"} variant="light">
            {user.status === "active" ? "账号正常" : user.status}
          </Badge>
        </Paper>

        <Box className="profile-grid">
          <Paper className="profile-card" radius="md" withBorder>
            <Stack gap="md">
              <Group justify="space-between">
                <Stack gap={2}>
                  <Title order={2}>今日打卡</Title>
                  <Text c="dimmed" size="sm">{endDate}</Text>
                </Stack>
                <Badge color={todayCheckin?.has_tasks ? "blue" : "gray"} variant="light">
                  {colorLevelLabel(todayCheckin?.color_level ?? 0)}
                </Badge>
              </Group>
              <Stack gap={6}>
                <Group justify="space-between">
                  <Text fw={750}>
                    今日完成 {todayCheckin?.completed_subtask_count ?? 0}/{todayCheckin?.total_subtask_count ?? 0}
                  </Text>
                  <Text fw={750}>{percent}%</Text>
                </Group>
                <Progress value={percent} />
              </Stack>
              <Text c="dimmed" size="sm">
                完成二级任务后，后端会同步重算当日打卡颜色。
              </Text>
            </Stack>
          </Paper>

          <Paper className="profile-card" radius="md" withBorder>
            <Stack gap="md">
              <Title order={2}>连续学习</Title>
              <Group grow>
                <Stack gap={2}>
                  <Text className="profile-metric">{summary?.current_streak_days ?? 0}</Text>
                  <Text c="dimmed" size="sm">连续 {summary?.current_streak_days ?? 0} 天</Text>
                </Stack>
                <Stack gap={2}>
                  <Text className="profile-metric">{summary?.longest_streak_days ?? 0}</Text>
                  <Text c="dimmed" size="sm">最长连续</Text>
                </Stack>
              </Group>
              <Text c="dimmed" size="sm">
                只统计已有打卡记录；无任务日和未开始日会中断连续段。
              </Text>
            </Stack>
          </Paper>
        </Box>

        <Paper className="profile-card" radius="md" withBorder>
          <Stack gap="md">
            <Group justify="space-between">
              <Title order={2}>近 14 天打卡颜色</Title>
              <Text c="dimmed" size="sm">{startDate} 至 {endDate}</Text>
            </Group>
            <Box className="profile-checkin-strip">
              {rangeDates.map((date) => {
                const checkin = checkinsByDate.get(date);
                const level = checkin?.color_level ?? 0;
                return (
                  <Box
                    aria-label={`${date} 打卡颜色等级 ${level}`}
                    className={`profile-checkin-cell level-${level}`}
                    key={date}
                    title={`${date} · ${colorLevelLabel(level)}`}
                  >
                    <span>{date.slice(8)}</span>
                  </Box>
                );
              })}
            </Box>
          </Stack>
        </Paper>
      </Box>
    </Box>
  );
}
