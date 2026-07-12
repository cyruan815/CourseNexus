import { Badge, Box, Button, Checkbox, Group, Stack, Text, Title } from "@mantine/core";
import { IconChevronDown, IconFileText, IconFolder, IconPlus, IconSearch } from "@tabler/icons-react";

import type { Course } from "../types/course";
import { CourseDetailWorkbench } from "./CourseDetailPage";
import "./course-detail.css";

const previewCourse: Course = {
  id: "preview-course",
  user_id: "preview-user",
  name: "理论模型与框架",
  description: "围绕理论模型概述、模型构建方法和案例分析组织课程资料。",
  teacher: "王老师",
  term: "2026 Spring",
  status: "active",
  created_at: "2026-07-09T12:00:00+00:00",
  updated_at: "2026-07-09T12:00:00+00:00",
  deleted_at: null,
};

interface PreviewMaterial {
  name: string;
  status: string;
  time: string;
}

interface PreviewFolder {
  materials?: PreviewMaterial[];
  name: string;
  open: boolean;
}

const folders: PreviewFolder[] = [
  {
    name: "01. 课程导论",
    open: false,
  },
  {
    name: "02. 核心概念：基础知识",
    open: false,
  },
  {
    materials: [
      { name: "03.1 理论模型概述", status: "parsed", time: "20:31" },
      { name: "03.2 模型构建方法", status: "parsed", time: "18:45" },
      { name: "03.3 案例分析：行业应用", status: "uploaded", time: "22:10" },
      { name: "03.4 模型评估与优化", status: "parse_failed", time: "16:32" },
    ],
    name: "03. 理论模型与框架",
    open: true,
  },
  {
    name: "04. 案例分析：实践应用",
    open: false,
  },
  {
    name: "05. 总结与复盘回顾",
    open: false,
  },
];

function statusBadge(status: string) {
  const statusMap: Record<string, { color: string; label: string }> = {
    parse_failed: { color: "red", label: "解析失败" },
    parsed: { color: "teal", label: "可用" },
    uploaded: { color: "yellow", label: "待解析" },
  };
  const current = statusMap[status] ?? { color: "gray", label: status };

  return (
    <Badge color={current.color} size="xs" variant="light">
      {current.label}
    </Badge>
  );
}

function PreviewMaterialPanel() {
  const parsedCount = folders
    .flatMap((folder) => folder.materials ?? [])
    .filter((material) => material.status === "parsed").length;

  return (
    <section aria-label="资料区" className="course-preview-materials">
      <Group justify="space-between">
        <Stack gap={2}>
          <Title order={2}>课程材料</Title>
          <Text c="dimmed" size="sm">{parsedCount} 份资料可用于问答和生成</Text>
        </Stack>
        <Button leftSection={<IconPlus size={15} />} size="xs" variant="default">
          新增资料
        </Button>
      </Group>

      <Box className="course-preview-scope">
        <Group justify="space-between" wrap="nowrap">
          <Stack gap={2}>
            <Text fw={700} size="sm">当前资料范围</Text>
            <Text c="dimmed" size="xs">默认使用全部已解析资料</Text>
          </Stack>
          <Badge color="teal" variant="light">2 份已选</Badge>
        </Group>
      </Box>

      <Box className="course-preview-search">
        <IconSearch size={16} stroke={1.7} />
        <Text c="dimmed" size="sm">搜索资料</Text>
      </Box>

      <Stack gap={0}>
        {folders.map((folder) => (
          <Box className="course-preview-folder" key={folder.name}>
            <Group className="course-preview-folder-title" justify="space-between" wrap="nowrap">
              <Group gap="sm" wrap="nowrap">
                <IconFolder size={22} stroke={1.5} />
                <Text fw={650}>{folder.name}</Text>
              </Group>
              <IconChevronDown className={folder.open ? "is-open" : ""} size={18} stroke={1.8} />
            </Group>

            {folder.open && folder.materials ? (
              <Stack gap={0}>
                {folder.materials.map((material) => (
                  <Group className="course-preview-material-row" justify="space-between" key={material.name} wrap="nowrap">
                    <Group gap="sm" wrap="nowrap">
                      <Checkbox
                        aria-label={`选择资料 ${material.name}`}
                        checked={material.status === "parsed"}
                        disabled={material.status !== "parsed"}
                        readOnly
                      />
                      <IconFileText size={20} stroke={1.5} />
                      <Stack gap={0}>
                        <Text fw={600}>{material.name}</Text>
                        <Text c="dimmed" size="xs">{material.time}</Text>
                      </Stack>
                    </Group>
                    {statusBadge(material.status)}
                  </Group>
                ))}
              </Stack>
            ) : null}
          </Box>
        ))}
      </Stack>
    </section>
  );
}

export function CourseDetailPreviewPage() {
  return <CourseDetailWorkbench course={previewCourse} materialPanel={<PreviewMaterialPanel />} />;
}
