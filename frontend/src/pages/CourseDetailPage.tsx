import { type ReactNode, useEffect, useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Divider,
  Group,
  Paper,
  Skeleton,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import {
  IconBrain,
  IconCards,
  IconChecklist,
  IconCube,
  IconHome2,
  IconMap,
  IconMessageCircle2,
  IconMoon,
  IconPlus,
  IconSearch,
  IconSend2,
  IconSparkles,
  IconUser,
} from "@tabler/icons-react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import {
  askCourseQuestion,
  generateCourseContent,
  listCourseConversations,
  listGeneratedContents,
  listStudyPlans,
} from "../features/course-workspace/api";
import type { CourseAnswer, GeneratedContent, StudyPlan } from "../features/course-workspace/types";
import { fetchCourse } from "../features/courses/api";
import { MaterialWorkspace } from "../features/materials/MaterialWorkspace";
import type { MaterialScope } from "../features/materials/types";
import type { Course } from "../types/course";
import "./course-detail.css";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "课程加载失败";
}

const toolItems = [
  {
    description: "基于选定资料生成自测题",
    icon: IconSearch,
    label: "Quiz",
    status: "生成入口",
    tone: "blue",
    type: "quiz",
  },
  {
    description: "把概念和定义转成记忆卡片",
    icon: IconCards,
    label: "Flashcards",
    status: "生成入口",
    tone: "mint",
    type: "flashcard",
  },
  {
    description: "整理章节、概念和关系",
    icon: IconMap,
    label: "Mind Map",
    status: "生成入口",
    tone: "indigo",
    type: "mindmap",
  },
  {
    description: "生成章节化复习路径",
    icon: IconChecklist,
    label: "复习提纲",
    status: "生成入口",
    tone: "violet",
    type: "outline",
  },
  {
    description: "提取重点概念和易错点",
    icon: IconBrain,
    label: "知识点清单",
    status: "生成入口",
    tone: "orange",
    type: "knowledge_list",
  },
  {
    description: "保存问答回答后形成笔记",
    icon: IconCube,
    label: "学习笔记",
    status: "保存入口",
    tone: "indigo",
    type: null,
  },
];

function CourseTopBar({ course }: { course: Course }) {
  return (
    <Paper className="course-detail-topbar" component="header" radius={0}>
      <Group justify="space-between" wrap="nowrap">
        <Group gap="md" wrap="nowrap">
          <ActionIcon aria-label="返回首页" className="course-detail-nav-icon" component={Link} radius="xl" size={42} to="/" variant="default">
            <IconHome2 size={20} stroke={1.8} />
          </ActionIcon>
          <Stack className="course-detail-heading" gap={2}>
            <Group gap="sm" wrap="nowrap">
              <Text className="course-detail-title" fw={760}>
                课程详情页
              </Text>
              <Text c="dimmed" fw={650} size="xl">
                /
              </Text>
              <Title className="course-detail-course-name" order={1}>
                {course.name}
              </Title>
            </Group>
            <Text className="course-detail-description" c="dimmed" size="sm">
              {course.description?.trim() || "课程简介待补充"}
            </Text>
          </Stack>
          <Group className="course-detail-topbar-meta" gap="xs" wrap="nowrap">
            <Badge color="blue" variant="light">
              {course.status === "active" ? "课程已创建" : course.status}
            </Badge>
            {course.term ? <Badge color="gray" variant="light">{course.term}</Badge> : null}
            <Text c="dimmed" size="sm">
              {course.teacher ?? "未填写教师"}
            </Text>
          </Group>
        </Group>

        <Group gap="sm" wrap="nowrap">
          <ActionIcon aria-label="切换为夜间模式" className="course-detail-theme-single-button" radius="md" size={44} variant="default">
            <IconMoon size={22} stroke={1.8} />
          </ActionIcon>
          <ActionIcon aria-label="打开个人中心" className="course-detail-user-button" radius="xl" size={48} variant="default">
            <IconUser size={24} stroke={1.8} />
          </ActionIcon>
        </Group>
      </Group>
    </Paper>
  );
}

function TodayTodoCard({ plans }: { plans: StudyPlan[] }) {
  const activePlan = plans[0];

  return (
    <Paper className="course-detail-card course-detail-todo-card" radius="md" withBorder>
      <Group justify="space-between" wrap="nowrap">
        <Title order={2}>今日待办</Title>
        <ActionIcon aria-label="查看今日待办" variant="subtle">
          <IconChecklist size={20} stroke={1.8} />
        </ActionIcon>
      </Group>
      <Stack gap="xs">
        {activePlan ? (
          <>
            <Text fw={700} size="sm">{activePlan.title}</Text>
            <Text c="dimmed" size="sm">
              {activePlan.start_date} - {activePlan.end_date} · {activePlan.status}
            </Text>
          </>
        ) : (
          <>
            <Text c="dimmed" size="sm">
              当前课程还没有学习计划
            </Text>
            <Button className="course-detail-plan-button" leftSection={<IconPlus size={16} />} size="sm" variant="light">
              制定学习计划
            </Button>
          </>
        )}
      </Stack>
    </Paper>
  );
}

function formatCitation(citation: CourseAnswer["source_citations"][number]): string {
  const location = citation.page ?? (citation.page_index !== null ? `第 ${citation.page_index + 1} 页` : "位置待定位");
  return `${citation.material_name} · ${location}`;
}

function QaWorkspace({
  answer,
  isPending,
  onQuestionChange,
  onSendQuestion,
  question,
}: {
  answer: CourseAnswer | null;
  isPending: boolean;
  onQuestionChange: (value: string) => void;
  onSendQuestion: () => void;
  question: string;
}) {
  const canSend = question.trim().length > 0 && !isPending;

  return (
    <Paper aria-label="问答区" className="course-detail-card course-detail-qa" component="section" radius="md" withBorder>
      <Group align="flex-start" justify="space-between">
        <Stack gap={4}>
          <Title order={2}>问答交互</Title>
          <Text c="dimmed" size="sm">
            基于左侧已解析资料范围提问
          </Text>
        </Stack>
        <Badge color="teal" variant="light">
          默认资料范围
        </Badge>
      </Group>

      {answer ? (
        <Box className="course-detail-answer">
          <Stack gap="sm">
            <Group gap="xs">
              <Badge color={answer.answer_type === "grounded" ? "teal" : "gray"} variant="light">
                {answer.answer_type === "grounded" ? "基于资料" : "无直接来源"}
              </Badge>
              <Text c="dimmed" size="sm">AI 助教</Text>
            </Group>
            <Text className="course-detail-answer-text">{answer.answer_text}</Text>
            {answer.source_citations.length > 0 ? (
              <Stack className="course-detail-citations" gap="xs">
                <Text fw={700} size="sm">引用来源</Text>
                {answer.source_citations.map((citation) => (
                  <Text c="dimmed" key={`${citation.material_id}-${citation.chunk_id ?? citation.hit_text}`} size="sm">
                    {formatCitation(citation)}
                  </Text>
                ))}
              </Stack>
            ) : null}
          </Stack>
        </Box>
      ) : (
        <Box className="course-detail-qa-empty">
          <IconMessageCircle2 size={42} stroke={1.6} />
          <Stack gap={4}>
            <Text fw={700}>选择资料后开始提问</Text>
            <Text c="dimmed" size="sm">
              上传并解析资料后，可围绕选定资料提问；回答会展示可追溯引用。
            </Text>
          </Stack>
        </Box>
      )}

      <Divider />

      <Stack gap="xs">
        <Text c="dimmed" size="sm">
          资料范围：当前课程全部已解析资料
        </Text>
        <Group align="flex-end" className="course-detail-question-row" wrap="nowrap">
          <Textarea
            aria-label="输入你的问题"
            className="course-detail-question-input"
            onChange={(event) => onQuestionChange(event.currentTarget.value)}
            placeholder="输入你的问题..."
            rows={2}
            value={question}
          />
          <ActionIcon aria-label="发送问题" className="course-detail-send-button" disabled={!canSend} loading={isPending} onClick={onSendQuestion} radius="xl" size={54} variant="filled">
            <IconSend2 size={24} stroke={1.8} />
          </ActionIcon>
        </Group>
        <Text c="dimmed" size="xs">
          内容由 AI 生成，仅供学习参考；引用来源用于回到原资料核对。
        </Text>
      </Stack>
    </Paper>
  );
}

function ToolCard({
  isGenerating,
  item,
  onGenerate,
}: {
  isGenerating: boolean;
  item: (typeof toolItems)[number];
  onGenerate: (contentType: string) => void;
}) {
  const ToolIcon = item.icon;
  const canGenerate = Boolean(item.type);
  return (
    <Card className={`course-detail-tool-card course-detail-tool-card-${item.tone}`} padding="md" radius="md" withBorder>
      <Group className="course-detail-tool-head" justify="space-between" wrap="nowrap">
        <Box className="course-detail-tool-icon">
          <ToolIcon size={30} stroke={1.65} />
        </Box>
        <Badge className="course-detail-tool-status" size="xs" variant="light">
          {item.status}
        </Badge>
      </Group>
      <Stack gap={3}>
        <Text fw={750}>{item.label}</Text>
        <Text c="dimmed" size="sm">{item.description}</Text>
      </Stack>
      {canGenerate ? (
        <Button loading={isGenerating} onClick={() => item.type && onGenerate(item.type)} size="xs" variant="light">
          生成
        </Button>
      ) : null}
    </Card>
  );
}

function ToolsPanel({
  generatingType,
  onGenerate,
}: {
  generatingType: string | null;
  onGenerate: (contentType: string) => void;
}) {
  return (
    <Paper aria-label="生成内容区" className="course-detail-card course-detail-tools" component="section" radius="md" withBorder>
      <Title order={2}>功能模块</Title>
      <Box className="course-detail-tool-grid">
        {toolItems.map((item) => (
          <ToolCard isGenerating={generatingType === item.type} item={item} key={item.label} onGenerate={onGenerate} />
        ))}
      </Box>
    </Paper>
  );
}

function contentTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    flashcard: "Flashcards",
    knowledge_list: "知识点",
    mindmap: "Mind Map",
    note: "学习笔记",
    outline: "复习提纲",
    quiz: "Quiz",
  };
  return labels[type] ?? type;
}

function GeneratedContentPanel({ contents }: { contents: GeneratedContent[] }) {
  return (
    <Paper aria-label="AI 生成内容" className="course-detail-card course-detail-generated" component="section" radius="md" withBorder>
      <Group justify="space-between">
        <Title order={2}>AI 生成内容</Title>
        <Button size="xs" variant="default">查看全部</Button>
      </Group>
      {contents.length > 0 ? (
        <Stack gap="xs">
          {contents.map((content) => (
            <Paper className="course-detail-generated-item" key={content.id} radius="md" withBorder>
              <Group justify="space-between" wrap="nowrap">
                <Stack gap={2}>
                  <Text fw={700} size="sm">{content.title}</Text>
                  <Text c="dimmed" size="xs">{contentTypeLabel(content.content_type)} · {content.generation_status}</Text>
                </Stack>
                <Badge color={content.generation_status === "success" ? "teal" : "yellow"} size="xs" variant="light">
                  {content.generation_status}
                </Badge>
              </Group>
            </Paper>
          ))}
        </Stack>
      ) : (
        <Stack className="course-detail-generated-empty" gap="xs">
          <IconSparkles size={34} stroke={1.6} />
          <Text fw={700}>还没有生成内容</Text>
          <Text c="dimmed" size="sm">
            使用右侧工具生成内容，或将问答回答保存为笔记后，会在这里形成记录。
          </Text>
        </Stack>
      )}
    </Paper>
  );
}

interface CourseDetailWorkbenchProps {
  answer?: CourseAnswer | null;
  course: Course;
  generatedContents?: GeneratedContent[];
  generatingType?: string | null;
  isQuestionPending?: boolean;
  materialPanel: ReactNode;
  onGenerate?: (contentType: string) => void;
  onQuestionChange?: (value: string) => void;
  onSendQuestion?: () => void;
  question?: string;
  studyPlans?: StudyPlan[];
}

export function CourseDetailWorkbench({
  answer = null,
  course,
  generatedContents = [],
  generatingType = null,
  isQuestionPending = false,
  materialPanel,
  onGenerate = () => undefined,
  onQuestionChange = () => undefined,
  onSendQuestion = () => undefined,
  question = "",
  studyPlans = [],
}: CourseDetailWorkbenchProps) {
  return (
    <Box className="course-detail-page">
      <CourseTopBar course={course} />
      <Box className="course-detail-shell" component="main">
        <Box className="course-detail-layout">
          <Stack className="course-detail-left" gap="sm">
            <TodayTodoCard plans={studyPlans} />
            <Paper className="course-detail-card course-detail-material-card" radius="md" withBorder>
              {materialPanel}
            </Paper>
          </Stack>

          <Stack className="course-detail-center" gap="sm">
            <QaWorkspace
              answer={answer}
              isPending={isQuestionPending}
              onQuestionChange={onQuestionChange}
              onSendQuestion={onSendQuestion}
              question={question}
            />
          </Stack>

          <Stack className="course-detail-right" gap="sm">
            <ToolsPanel generatingType={generatingType} onGenerate={onGenerate} />
            <GeneratedContentPanel contents={generatedContents} />
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

export function CourseDetailPage() {
  const { courseId } = useParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [generatedContents, setGeneratedContents] = useState<GeneratedContent[]>([]);
  const [studyPlans, setStudyPlans] = useState<StudyPlan[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<CourseAnswer | null>(null);
  const [isQuestionPending, setIsQuestionPending] = useState(false);
  const [generatingType, setGeneratingType] = useState<string | null>(null);
  const [materialScope, setMaterialScope] = useState<MaterialScope>({
    include_all_parsed_materials: true,
    material_ids: [],
  });

  useEffect(() => {
    let ignore = false;

    if (!courseId) {
      setError("课程不存在");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    fetchCourse(courseId)
      .then((nextCourse) => {
        if (!ignore) {
          setCourse(nextCourse);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(errorMessage(nextError));
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
  }, [courseId]);

  useEffect(() => {
    let ignore = false;

    if (!course?.id) {
      return undefined;
    }

    setWorkspaceError(null);

    Promise.all([
      listGeneratedContents(course.id),
      listStudyPlans(course.id),
      listCourseConversations(course.id),
    ])
      .then(([nextGeneratedContents, nextStudyPlans, conversations]) => {
        if (!ignore) {
          setGeneratedContents(nextGeneratedContents);
          setStudyPlans(nextStudyPlans);
          setConversationId(conversations[0]?.id ?? null);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setWorkspaceError(errorMessage(nextError));
        }
      });

    return () => {
      ignore = true;
    };
  }, [course?.id]);

  async function handleSendQuestion() {
    if (!course || !question.trim()) {
      return;
    }

    setIsQuestionPending(true);
    setWorkspaceError(null);

    try {
      const nextAnswer = await askCourseQuestion(course.id, {
        conversation_id: conversationId,
        material_scope: materialScope,
        question: question.trim(),
        source_page: "course_detail",
      });
      setAnswer(nextAnswer);
      setConversationId(nextAnswer.conversation_id);
      setQuestion("");
    } catch (nextError) {
      setWorkspaceError(errorMessage(nextError));
    } finally {
      setIsQuestionPending(false);
    }
  }

  async function handleGenerateContent(contentType: string) {
    if (!course) {
      return;
    }

    setGeneratingType(contentType);
    setWorkspaceError(null);

    try {
      const content = await generateCourseContent(course.id, {
        content_type: contentType,
        material_scope: materialScope,
        parameters: {},
      });
      setGeneratedContents((current) => [content, ...current]);
    } catch (nextError) {
      setWorkspaceError(errorMessage(nextError));
    } finally {
      setGeneratingType(null);
    }
  }

  if (isLoading) {
    return (
      <Box className="course-detail-page">
        <Paper className="course-detail-topbar" component="header" radius={0}>
          <Skeleton height={34} width={280} />
        </Paper>
        <Box className="course-detail-loading" role="status">
          <Text c="dimmed">正在加载课程...</Text>
          <Skeleton height={120} radius="md" />
          <Skeleton height={420} radius="md" />
        </Box>
      </Box>
    );
  }

  if (error || !course) {
    return (
      <Box className="course-detail-page">
        <Paper className="course-detail-topbar" component="header" radius={0}>
          <Title className="course-detail-title" order={1}>课程详情页</Title>
        </Paper>
        <Alert className="course-detail-error" color="red" role="alert" title="课程加载失败" variant="light">
          {error ?? "课程不存在"}
        </Alert>
      </Box>
    );
  }

  return (
    <>
      {workspaceError ? (
        <Alert className="course-detail-workspace-error" color="red" role="alert" title="课程工作区加载失败" variant="light">
          {workspaceError}
        </Alert>
      ) : null}
      <CourseDetailWorkbench
        answer={answer}
        course={course}
        generatedContents={generatedContents}
        generatingType={generatingType}
        isQuestionPending={isQuestionPending}
        materialPanel={(
          <MaterialWorkspace
            courseId={course.id}
            materialScope={materialScope}
            onMaterialScopeChange={setMaterialScope}
          />
        )}
        onGenerate={handleGenerateContent}
        onQuestionChange={setQuestion}
        onSendQuestion={handleSendQuestion}
        question={question}
        studyPlans={studyPlans}
      />
    </>
  );
}
