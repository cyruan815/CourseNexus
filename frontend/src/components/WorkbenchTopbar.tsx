import type { ReactNode } from "react";
import { ActionIcon, Button, Group, Paper, Text, Title } from "@mantine/core";
import { IconArrowLeft, IconHome2, IconMoon, IconSun, IconUser } from "@tabler/icons-react";
import { Link, useNavigate } from "react-router-dom";

import { useCourseNexusTheme } from "../app/theme";

interface WorkbenchTopbarProps {
  actions?: ReactNode;
  backFallbackTo?: string;
  contextName?: ReactNode;
  meta?: ReactNode;
  pageName: string;
  showBack?: boolean;
}

export function WorkbenchTopbar({
  actions,
  backFallbackTo = "/",
  contextName,
  meta,
  pageName,
  showBack = true,
}: WorkbenchTopbarProps) {
  const navigate = useNavigate();
  const { isDarkMode, toggleTheme } = useCourseNexusTheme();
  const ThemeIcon = isDarkMode ? IconSun : IconMoon;
  const themeLabel = isDarkMode ? "切换为日间模式" : "切换为夜间模式";

  function goBack() {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate(backFallbackTo);
  }

  return (
    <Paper className="workbench-topbar" component="header" radius={0}>
      <Group className="workbench-topbar-inner" justify="space-between" wrap="nowrap">
        <Group className="workbench-topbar-left" gap="md" wrap="nowrap">
          <ActionIcon aria-label="返回首页" className="workbench-home-button" component={Link} radius="xl" size={42} to="/" variant="default">
            <IconHome2 size={20} stroke={1.8} />
          </ActionIcon>
          {showBack ? (
            <Button
              className="workbench-back-button"
              leftSection={<IconArrowLeft size={16} />}
              onClick={goBack}
              type="button"
              variant="subtle"
            >
              返回
            </Button>
          ) : null}
          <Group className="workbench-heading" gap="xs" wrap="nowrap">
            <Title className="workbench-page-name" order={1}>{pageName}</Title>
            {contextName ? (
              <>
                <Text aria-hidden c="dimmed" fw={650} size="xl">/</Text>
                <Text className="workbench-context-name" component="span">{contextName}</Text>
              </>
            ) : null}
          </Group>
          {meta ? (
            <Group className="workbench-meta" gap="xs" wrap="nowrap">
              {meta}
            </Group>
          ) : null}
        </Group>

        <Group className="workbench-topbar-right" gap="sm" wrap="nowrap">
          {actions ? (
            <Group className="workbench-actions" gap="xs" wrap="nowrap">
              {actions}
            </Group>
          ) : null}
          <ActionIcon
            aria-label={themeLabel}
            className="workbench-theme-button"
            onClick={toggleTheme}
            radius="md"
            size={44}
            variant="default"
          >
            <ThemeIcon size={22} stroke={1.8} />
          </ActionIcon>
          <ActionIcon
            aria-label="打开个人中心"
            className="workbench-user-button"
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
