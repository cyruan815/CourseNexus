import { Box, Paper, Text, Title } from "@mantine/core";

import "../features/courses/home-workbench.css";

export function CalendarPage() {
  return (
    <Box className="home-workbench calendar-placeholder-page">
      <Paper className="home-header" component="header" radius={0}>
        <Title className="home-brand-title" order={1}>日历</Title>
      </Paper>
      <Box className="calendar-placeholder-shell">
        <Paper className="home-main-panel" radius="md" withBorder>
          <Title order={2}>大日历</Title>
          <Text c="dimmed">学习计划聚合接口落地后，这里会展示真实任务日历。</Text>
        </Paper>
      </Box>
    </Box>
  );
}
