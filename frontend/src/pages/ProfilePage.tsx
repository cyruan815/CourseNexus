import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Badge,
  Box,
  Button,
  Group,
  Modal,
  Paper,
  PasswordInput,
  Progress,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconKey, IconLogout, IconSettings, IconUserCircle } from "@tabler/icons-react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/errors";
import { changePassword, fetchCurrentUser, logout } from "../features/auth/api";
import type { AuthUser } from "../features/auth/api";
import { clearSessionToken } from "../features/auth/session";
import { fetchCheckinDay, fetchCheckinRange } from "../features/profile/api";
import type { CheckinRangeRead, CheckinRead } from "../features/profile/api";
import { ModelConfigModal } from "../features/profile/ModelConfigModal";
import "./profile.css";

const DAY_MS = 24 * 60 * 60 * 1000;
const weekdayLabels = ["", "Mon", "", "Wed", "", "Fri", ""];
const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
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

function buildYearBounds(date: Date): { startDate: string; endDate: string; year: number } {
  const year = date.getFullYear();
  return {
    endDate: formatDate(new Date(year, 11, 31)),
    startDate: formatDate(new Date(year, 0, 1)),
    year,
  };
}

function dateKeyToDate(date: string): Date {
  return new Date(`${date}T00:00:00`);
}

function buildHeatmapWeeks(dates: string[]): Array<Array<string | null>> {
  const weeks: Array<Array<string | null>> = [];
  let week: Array<string | null> = Array(7).fill(null);

  for (const date of dates) {
    const day = dateKeyToDate(date).getDay();
    if (day === 0 && week.some(Boolean)) {
      weeks.push(week);
      week = Array(7).fill(null);
    }
    week[day] = date;
  }

  if (week.some(Boolean)) {
    weeks.push(week);
  }

  return weeks;
}

function buildMonthMarkers(weeks: Array<Array<string | null>>): Array<{ label: string; weekIndex: number }> {
  return monthLabels.map((label, monthIndex) => {
    const monthPrefix = `-${String(monthIndex + 1).padStart(2, "0")}-`;
    const weekIndex = weeks.findIndex((week) => week.some((date) => date?.includes(monthPrefix)));
    return { label, weekIndex: Math.max(0, weekIndex) };
  });
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
  const [isModelConfigOpen, setIsModelConfigOpen] = useState(false);
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changePasswordError, setChangePasswordError] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isPasswordChanged, setIsPasswordChanged] = useState(false);

  const todayDate = useMemo(() => new Date(), []);
  const todayDateKey = useMemo(() => formatDate(todayDate), [todayDate]);
  const { endDate, startDate, year } = useMemo(() => buildYearBounds(todayDate), [todayDate]);
  const rangeDates = useMemo(() => buildDateRange(startDate, endDate), [endDate, startDate]);
  const heatmapWeeks = useMemo(() => buildHeatmapWeeks(rangeDates), [rangeDates]);
  const monthMarkers = useMemo(() => buildMonthMarkers(heatmapWeeks), [heatmapWeeks]);
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
      fetchCheckinDay(todayDateKey),
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
  }, [endDate, startDate, todayDateKey]);

  async function handleLogout() {
    setIsLoggingOut(true);

    try {
      await logout();
      navigate("/welcome", { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  }

  function openChangePasswordModal() {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setChangePasswordError(null);
    setIsPasswordChanged(false);
    setIsChangePasswordOpen(true);
  }

  function closeChangePasswordModal() {
    if (isChangingPassword) {
      return;
    }
    setIsChangePasswordOpen(false);
    if (isPasswordChanged) {
      // 服务端已撤销全部登录态，清理本地 token 并回到登录页。
      clearSessionToken();
      navigate("/login", { state: { reason: "password_changed" } });
    }
  }

  function submitChangePassword() {
    setChangePasswordError(null);
    if (!currentPassword || !newPassword || !confirmPassword) {
      setChangePasswordError("请填写全部密码字段");
      return;
    }
    if (newPassword.length < 8) {
      setChangePasswordError("新密码长度至少 8 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      setChangePasswordError("两次输入的新密码不一致");
      return;
    }
    if (newPassword === currentPassword) {
      setChangePasswordError("新密码不能与当前密码相同");
      return;
    }

    setIsChangingPassword(true);
    changePassword({ current_password: currentPassword, new_password: newPassword })
      .then(() => {
        setIsPasswordChanged(true);
      })
      .catch((nextError: unknown) => {
        setChangePasswordError(errorMessage(nextError, "修改密码失败"));
      })
      .finally(() => {
        setIsChangingPassword(false);
      });
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
          <Group className="profile-nav-actions" gap="sm">
            <Button
              leftSection={<IconSettings size={16} />}
              onClick={() => setIsModelConfigOpen(true)}
              variant="light"
            >
              模型配置
            </Button>
            <Button leftSection={<IconKey size={16} />} onClick={openChangePasswordModal} variant="light">
              修改密码
            </Button>
            <Button
              className="cn-danger-button"
              color="red"
              leftSection={<IconLogout size={16} />}
              loading={isLoggingOut}
              onClick={() => void handleLogout()}
              variant="light"
            >
              退出登录
            </Button>
          </Group>
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
                  <Text c="dimmed" size="sm">{todayDateKey}</Text>
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
              <Title order={2}>{year} 年打卡颜色</Title>
              <Text c="dimmed" size="sm">{startDate} 至 {endDate}</Text>
            </Group>
            <Box className="profile-year-heatmap">
              <Box
                className="profile-heatmap-months"
                style={{ gridTemplateColumns: `32px repeat(${heatmapWeeks.length}, 12px)` }}
              >
                <span aria-hidden="true" />
                {monthMarkers.map((marker) => (
                  <span key={marker.label} style={{ gridColumn: marker.weekIndex + 2 }}>
                    {marker.label}
                  </span>
                ))}
              </Box>
              <Box className="profile-heatmap-body">
                <Box className="profile-heatmap-weekdays" aria-hidden="true">
                  {weekdayLabels.map((label, index) => (
                    <span key={`${label}-${index}`}>{label}</span>
                  ))}
                </Box>
                <Box
                  className="profile-heatmap-grid"
                  style={{ gridTemplateColumns: `repeat(${heatmapWeeks.length}, 12px)` }}
                >
                  {heatmapWeeks.flatMap((week, weekIndex) =>
                    week.map((date, dayIndex) => {
                      if (!date) {
                        return (
                          <span
                            aria-hidden="true"
                            className="profile-checkin-cell is-empty"
                            key={`empty-${weekIndex}-${dayIndex}`}
                            style={{ gridColumn: weekIndex + 1, gridRow: dayIndex + 1 }}
                          />
                        );
                      }

                      const checkin = checkinsByDate.get(date);
                      const level = checkin?.color_level ?? 0;
                      return (
                        <Box
                          aria-label={`${date} 打卡颜色等级 ${level}`}
                          className={`profile-checkin-cell level-${level}`}
                          key={date}
                          style={{ gridColumn: weekIndex + 1, gridRow: dayIndex + 1 }}
                          title={`${date} · ${colorLevelLabel(level)}`}
                        />
                      );
                    }),
                  )}
                </Box>
              </Box>
              <Group className="profile-heatmap-legend" gap={6} justify="flex-end">
                <Text c="dimmed" size="xs">Less</Text>
                {[0, 2, 3, 4, 5].map((level) => (
                  <span className={`profile-checkin-cell level-${level}`} key={level} />
                ))}
                <Text c="dimmed" size="xs">More</Text>
              </Group>
            </Box>
          </Stack>
        </Paper>

        <Modal
          centered
          closeOnClickOutside={!isPasswordChanged}
          closeOnEscape={!isPasswordChanged}
          closeButtonProps={{ "aria-label": "关闭修改密码弹窗" }}
          onClose={closeChangePasswordModal}
          opened={isChangePasswordOpen}
          title="修改密码"
          transitionProps={{ duration: 0 }}
        >
          <Stack gap="md">
            {isPasswordChanged ? (
              <>
                <Alert color="green" title="密码已修改">
                  密码已修改，当前登录已全部失效，请使用新密码重新登录。
                </Alert>
                <Group justify="flex-end">
                  <Button onClick={closeChangePasswordModal}>重新登录</Button>
                </Group>
              </>
            ) : (
              <>
                {changePasswordError ? (
                  <Alert color="red" role="alert" title="修改失败" variant="light">
                    {changePasswordError}
                  </Alert>
                ) : null}
                <PasswordInput
                  autoComplete="current-password"
                  label="当前密码"
                  onChange={(event) => setCurrentPassword(event.currentTarget.value)}
                  required
                  value={currentPassword}
                />
                <PasswordInput
                  autoComplete="new-password"
                  description="至少 8 位"
                  label="新密码"
                  onChange={(event) => setNewPassword(event.currentTarget.value)}
                  required
                  value={newPassword}
                />
                <PasswordInput
                  autoComplete="new-password"
                  label="确认新密码"
                  onChange={(event) => setConfirmPassword(event.currentTarget.value)}
                  required
                  value={confirmPassword}
                />
                <Group justify="flex-end">
                  <Button disabled={isChangingPassword} onClick={closeChangePasswordModal} variant="default">
                    取消
                  </Button>
                  <Button loading={isChangingPassword} onClick={() => void submitChangePassword()}>
                    确认修改
                  </Button>
                </Group>
              </>
            )}
          </Stack>
        </Modal>
        <ModelConfigModal
          onClose={() => setIsModelConfigOpen(false)}
          opened={isModelConfigOpen}
        />
      </Box>
    </Box>
  );
}
