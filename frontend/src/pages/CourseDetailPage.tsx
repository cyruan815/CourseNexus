import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Divider,
  Group,
  Menu,
  Modal,
  Paper,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import {
  IconBrain,
  IconCalendarStats,
  IconCards,
  IconChecklist,
  IconDotsVertical,
  IconEdit,
  IconHome2,
  IconMap,
  IconMessageCircle2,
  IconMoon,
  IconPlus,
  IconSearch,
  IconSend2,
  IconSparkles,
  IconSun,
  IconTrash,
  IconUser,
} from "@tabler/icons-react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { useCourseNexusTheme } from "../app/theme";
import { InlineCitationAnswer } from "../features/course-qa/InlineCitationAnswer";
import {
  askCourseQuestion,
  deleteGeneratedContent,
  generateCourseContent,
  listCourseConversations,
  listConversationMessages,
  listGeneratedContents,
  renameGeneratedContent,
} from "../features/course-workspace/api";
import type { GeneratedContent, Message, SourceCitation, StudyPlan } from "../features/course-workspace/types";
import { fetchCourse } from "../features/courses/api";
import { MaterialWorkspace } from "../features/materials/MaterialWorkspace";
import type { Material, MaterialScope } from "../features/materials/types";
import { listStudyPlans } from "../features/study-plans/api";
import type { Course } from "../types/course";
import "./course-detail.css";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "课程加载失败";
}

function readableCourseTerm(term: string | null | undefined): string | null {
  if (!term) {
    return null;
  }

  return term
    .replace(/[-_\s]?AUTUMN$/i, " 秋季")
    .replace(/[-_\s]?SPRING$/i, " 春季")
    .trim();
}

function resizeQuestionTextarea(textarea: HTMLTextAreaElement) {
  const maxHeight = 124;
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
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
];

function CourseTopBar({ course }: { course: Course }) {
  const { isDarkMode, toggleTheme } = useCourseNexusTheme();
  const ThemeIcon = isDarkMode ? IconSun : IconMoon;
  const themeLabel = isDarkMode ? "切换为日间模式" : "切换为夜间模式";
  const termLabel = readableCourseTerm(course.term);

  return (
    <Paper className="course-detail-topbar" component="header" radius={0}>
      <Group justify="space-between" wrap="nowrap">
        <Group gap="md" wrap="nowrap">
          <ActionIcon aria-label="返回首页" className="course-detail-nav-icon" component={Link} radius="xl" size={42} to="/" variant="default">
            <IconHome2 size={20} stroke={1.8} />
          </ActionIcon>
          <Stack className="course-detail-heading" gap={2}>
            <Group gap="sm" wrap="nowrap">
              <Text className="course-detail-title" fw={760}>{"课程详情"}</Text>
              <Text c="dimmed" fw={650} size="xl">/</Text>
              <Title className="course-detail-course-name" order={1}>{course.name}</Title>
            </Group>
          </Stack>
          <Group className="course-detail-topbar-meta" gap="xs" wrap="nowrap">
            {termLabel ? <Badge color="gray" variant="light">{termLabel}</Badge> : null}
            <Text c="dimmed" size="sm">{course.teacher ?? "未填写教师"}</Text>
          </Group>
        </Group>
        <Group gap="sm" wrap="nowrap">
          <ActionIcon aria-label={themeLabel} className="course-detail-theme-single-button" onClick={toggleTheme} radius="md" size={44} variant="default">
            <ThemeIcon size={22} stroke={1.8} />
          </ActionIcon>
          <ActionIcon
            aria-label="打开个人中心"
            className="course-detail-user-button"
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

function TodayTodoCard({ courseId, plans }: { courseId: string; plans: StudyPlan[] }) {
  const activePlan = [...plans].sort((left, right) => {
    const leftTime = Date.parse(left.updated_at || left.created_at);
    const rightTime = Date.parse(right.updated_at || right.created_at);
    return rightTime - leftTime;
  })[0];

  return (
    <Paper className="course-detail-card course-detail-todo-card" radius="md" withBorder>
      <Group justify="space-between" wrap="nowrap">
        <Title order={2}>{"学习计划"}</Title>
      </Group>
      <Stack className="course-detail-plan-content" gap="sm">
        {activePlan ? (
          <Box aria-label={`查看学习计划 ${activePlan.title}`} className="course-detail-plan-summary" component={Link} to={`/courses/${courseId}/study-plans/${activePlan.id}`}>
            <Text className="course-detail-plan-title" fw={700} size="sm">{activePlan.title}</Text>
            <Text c="dimmed" size="sm">{activePlan.start_date} - {activePlan.end_date} · {activePlan.status}</Text>
          </Box>
        ) : (
          <Text c="dimmed" size="sm">{"当前课程还没有学习计划"}</Text>
        )}
        <Group className="course-detail-plan-actions" gap="xs" justify="flex-end">
          <Button className="course-detail-plan-button" component={Link} leftSection={<IconPlus size={16} />} size="sm" to={`/courses/${courseId}/study-plans/new`} variant="light">
            {activePlan ? "新建学习计划" : "制定学习计划"}
          </Button>
          <Button className="course-detail-plan-more-button" component={Link} leftSection={<IconCalendarStats size={16} />} size="sm" to={`/calendar?courseId=${courseId}`} variant="filled">
            {"查看更多"}
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}

interface QaMessage {
  answerType?: string | null;
  citations?: SourceCitation[];
  content: string;
  id: string;
  role: "assistant" | "user";
  status?: "done" | "error";
}

function qaMessageFromBackend(message: Message): QaMessage {
  return {
    answerType: message.answer_type,
    citations: message.source_citations,
    content: message.content,
    id: message.id,
    role: message.role === "assistant" ? "assistant" : "user",
    status: "done",
  };
}

function materialScopeNames(scope: MaterialScope, parsedMaterials: Material[]): string[] {
  if (scope.include_all_parsed_materials) {
    return parsedMaterials.map((material) => material.name);
  }

  const selected = new Set(scope.material_ids);
  return parsedMaterials.filter((material) => selected.has(material.id)).map((material) => material.name);
}

function materialScopeForRequest(scope: MaterialScope): MaterialScope {
  if (scope.include_all_parsed_materials) {
    return { include_all_parsed_materials: true, material_ids: [] };
  }

  return scope;
}

function QaWorkspace({
  isPending,
  materialScope,
  materialScopeNames: selectedMaterialNames,
  messages,
  onQuestionChange,
  onSendQuestion,
  question,
}: {
  isPending: boolean;
  materialScope: MaterialScope;
  materialScopeNames: string[];
  messages: QaMessage[];
  onQuestionChange: (value: string) => void;
  onSendQuestion: () => void;
  question: string;
}) {
  const canSend = question.trim().length > 0 && !isPending;

  return (
    <Paper aria-label="问答区" className="course-detail-card course-detail-qa" component="section" radius="md" withBorder>
      <Group align="flex-start" justify="space-between">
        <Stack gap={4}>
          <Title order={2}>{"问答交互"}</Title>
          <Text c="dimmed" size="sm">{"基于左侧已解析资料范围提问"}</Text>
        </Stack>
        <Badge color="teal" variant="light">{"默认资料范围"}</Badge>
      </Group>
      <Stack className="course-detail-conversation" gap="sm">
        {messages.length > 0 || isPending ? messages.map((message) => (
          <Box className={`course-detail-message course-detail-message-${message.role}${message.status === "error" ? " course-detail-message-error" : ""}`} key={message.id}>
            <Stack gap="xs">
              <Group gap="xs">
                {message.role === "assistant" ? <Badge color={message.status === "error" ? "red" : message.answerType === "grounded" ? "teal" : "gray"} variant="light">{message.status === "error" ? "回答失败" : message.answerType === "grounded" ? "基于资料" : "AI 助教"}</Badge> : <Badge color="blue" variant="light">{"你的问题"}</Badge>}
              </Group>
              <Box className="course-detail-answer-text">{message.role === "assistant" ? <InlineCitationAnswer citations={message.citations ?? []} content={message.content} /> : <p>{message.content}</p>}</Box>
            </Stack>
          </Box>
        )) : <Box className="course-detail-qa-empty"><IconMessageCircle2 size={42} stroke={1.6} /><Stack gap={4}><Text fw={700}>{"选择资料后开始提问"}</Text><Text c="dimmed" size="sm">{"上传并解析资料后，可围绕选定资料提问。"}</Text></Stack></Box>}
      </Stack>
      <Stack className="course-detail-qa-input-area" gap="xs">
        <Divider />
        <Text c="dimmed" size="sm">{materialScope.include_all_parsed_materials ? "资料范围：当前课程全部已解析资料" : <span className="course-detail-scope-line"><span className="course-detail-scope-prefix">{"资料范围：已选择"}</span><span className="course-detail-scope-names" title={selectedMaterialNames.join(" / ")}>{selectedMaterialNames.join(" / ")}</span><span className="course-detail-scope-count">{"共 "}{materialScope.material_ids.length}{" 份资料"}</span></span>}</Text>
        <Group align="flex-end" className="course-detail-question-row" wrap="nowrap"><Textarea aria-label="输入你的问题" className="course-detail-question-input" onChange={(event) => { resizeQuestionTextarea(event.currentTarget); onQuestionChange(event.currentTarget.value); }} placeholder="输入你的问题..." rows={2} value={question} /><ActionIcon aria-label="发送问题" className="course-detail-send-button" disabled={!canSend} loading={isPending} onClick={onSendQuestion} radius="xl" size={54} variant="filled"><IconSend2 size={24} stroke={1.8} /></ActionIcon></Group>
        <Text c="dimmed" size="xs">{"内容由 AI 生成，仅供学习参考。"}</Text>
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
    <Card aria-label={canGenerate ? `生成 ${item.label}` : `${item.label} 暂未接入`} className={`course-detail-tool-card course-detail-tool-card-${item.tone}${item.type === "knowledge_list" ? " is-wide" : ""}`} component="button" disabled={!canGenerate || isGenerating} onClick={() => item.type && onGenerate(item.type)} padding="md" radius="md" type="button" withBorder>
      <Group className="course-detail-tool-head" justify="space-between" wrap="nowrap">
        <Box className="course-detail-tool-icon"><ToolIcon size={30} stroke={1.65} /></Box>
        <Stack gap={3}><Text fw={750}>{item.label}</Text><Text c="dimmed" size="sm">{item.description}</Text></Stack>
      </Group>
    </Card>
  );
}

function ToolsPanel({ generatingType, onGenerate }: { generatingType: string | null; onGenerate: (contentType: string) => void }) {
  return (
    <Paper aria-label="学习工具区" className="course-detail-card course-detail-tools" component="section" radius="md" withBorder>
      <Title order={2}>{"学习工具"}</Title>
      <Box className="course-detail-tool-grid">{toolItems.map((item) => <ToolCard isGenerating={generatingType === item.type} item={item} key={item.label} onGenerate={onGenerate} />)}</Box>
    </Paper>
  );
}

function contentTypeLabel(type: string): string {
  const labels: Record<string, string> = { flashcard: "Flashcards", knowledge_list: "知识点清单", mindmap: "Mind Map", note: "学习笔记", outline: "复习提纲", quiz: "Quiz" };
  return labels[type] ?? type;
}

function GeneratedContentPanel({
  contents,
  onDelete,
  onRename,
}: {
  contents: GeneratedContent[];
  onDelete: (content: GeneratedContent) => Promise<void>;
  onRename: (content: GeneratedContent, title: string) => Promise<void>;
}) {
  const [renameTarget, setRenameTarget] = useState<GeneratedContent | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<GeneratedContent | null>(null);
  const [title, setTitle] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function openRename(content: GeneratedContent) {
    setRenameTarget(content);
    setTitle(content.title);
    setActionError(null);
  }

  function openDelete(content: GeneratedContent) {
    setDeleteTarget(content);
    setActionError(null);
  }

  function closeActions() {
    if (isSubmitting) {
      return;
    }
    setRenameTarget(null);
    setDeleteTarget(null);
    setActionError(null);
  }

  async function submitRename() {
    const normalizedTitle = title.trim();
    if (!renameTarget || !normalizedTitle || normalizedTitle === renameTarget.title) {
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      await onRename(renameTarget, normalizedTitle);
      setRenameTarget(null);
    } catch (nextError) {
      setActionError(errorMessage(nextError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitDelete() {
    if (!deleteTarget) {
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      await onDelete(deleteTarget);
      setDeleteTarget(null);
    } catch (nextError) {
      setActionError(errorMessage(nextError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <Paper aria-label="AI 生成内容区" className="course-detail-card course-detail-generated" component="section" radius="md" withBorder>
        <Title order={2}>{"AI 生成内容"}</Title>
        {contents.length > 0 ? (
          <Stack className="course-detail-generated-list" gap="xs">
            {contents.map((content) => (
              <Paper className="course-detail-generated-item" key={content.id} radius="md" withBorder>
                <Box
                  aria-label={`查看生成内容 ${content.title}`}
                  className="course-detail-generated-link"
                  component={Link}
                  to={`/generated-contents/${content.id}`}
                >
                  <Stack gap={2}>
                    <Text fw={700} lineClamp={2} size="sm">{content.title}</Text>
                    <Text c="dimmed" size="xs">{contentTypeLabel(content.content_type)} · {content.generation_status}</Text>
                  </Stack>
                </Box>
                <Group className="course-detail-generated-actions" gap={4} wrap="nowrap">
                  <Badge color={content.generation_status === "success" ? "teal" : "yellow"} size="xs" variant="light">{content.generation_status}</Badge>
                  <Menu position="bottom-end" shadow="md" transitionProps={{ duration: 0 }} width={150} withinPortal>
                    <Menu.Target>
                      <ActionIcon aria-label={`${content.title} 更多操作`} size="sm" variant="subtle">
                        <IconDotsVertical size={18} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item leftSection={<IconEdit size={16} />} onClick={() => openRename(content)}>
                        重命名
                      </Menu.Item>
                      <Menu.Item color="red" leftSection={<IconTrash size={16} />} onClick={() => openDelete(content)}>
                        删除
                      </Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Group>
              </Paper>
            ))}
          </Stack>
        ) : (
          <Stack className="course-detail-generated-empty" gap="xs"><IconSparkles size={34} stroke={1.6} /><Text fw={700}>{"还没有生成内容"}</Text><Text c="dimmed" size="sm">{"选择左侧资料范围后，可使用学习工具生成内容。"}</Text></Stack>
        )}
      </Paper>
      <Modal centered onClose={closeActions} opened={Boolean(renameTarget)} title="重命名生成内容" transitionProps={{ duration: 0 }}>
        <Stack gap="md">
          {actionError ? <Alert color="red" role="alert" title="重命名失败" variant="light">{actionError}</Alert> : null}
          <TextInput
            data-autofocus
            label="生成内容名称"
            maxLength={255}
            onChange={(event) => setTitle(event.currentTarget.value)}
            value={title}
          />
          <Group justify="flex-end">
            <Button disabled={isSubmitting} onClick={closeActions} variant="default">取消</Button>
            <Button
              disabled={!title.trim() || title.trim() === renameTarget?.title}
              loading={isSubmitting}
              onClick={submitRename}
            >
              保存
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Modal centered onClose={closeActions} opened={Boolean(deleteTarget)} title="删除生成内容" transitionProps={{ duration: 0 }}>
        <Stack gap="md">
          {actionError ? <Alert color="red" role="alert" title="删除失败" variant="light">{actionError}</Alert> : null}
          <Text>确认删除“{deleteTarget?.title}”吗？删除后该内容将从课程页面中移除。</Text>
          <Group justify="flex-end">
            <Button disabled={isSubmitting} onClick={closeActions} variant="default">取消</Button>
            <Button color="red" loading={isSubmitting} onClick={submitDelete}>确认删除</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

interface CourseDetailWorkbenchProps {
  course: Course;
  generatedContents?: GeneratedContent[];
  generatingType?: string | null;
  isQuestionPending?: boolean;
  materialPanel: ReactNode;
  materialScope?: MaterialScope;
  materialScopeNames?: string[];
  onGenerate?: (contentType: string) => void;
  onDeleteGeneratedContent?: (content: GeneratedContent) => Promise<void>;
  onRenameGeneratedContent?: (content: GeneratedContent, title: string) => Promise<void>;
  onQuestionChange?: (value: string) => void;
  onSendQuestion?: () => void;
  qaMessages?: QaMessage[];
  question?: string;
  studyPlans?: StudyPlan[];
}

export function CourseDetailWorkbench({
  course,
  generatedContents = [],
  generatingType = null,
  isQuestionPending = false,
  materialPanel,
  materialScope = { include_all_parsed_materials: true, material_ids: [] },
  materialScopeNames = [],
  onGenerate = () => undefined,
  onDeleteGeneratedContent = async () => undefined,
  onRenameGeneratedContent = async () => undefined,
  onQuestionChange = () => undefined,
  onSendQuestion = () => undefined,
  qaMessages = [],
  question = "",
  studyPlans = [],
}: CourseDetailWorkbenchProps) {
  return (
    <Box className="course-detail-page">
      <CourseTopBar course={course} />
      <Box className="course-detail-shell" component="main">
        <Box className="course-detail-layout">
          <Stack className="course-detail-left" gap="sm">
            <TodayTodoCard courseId={course.id} plans={studyPlans} />
            <Paper className="course-detail-card course-detail-material-card" radius="md" withBorder>
              {materialPanel}
            </Paper>
          </Stack>

          <Stack className="course-detail-center" gap="sm">
            <QaWorkspace
              isPending={isQuestionPending}
              materialScope={materialScope}
              materialScopeNames={materialScopeNames}
              messages={qaMessages}
              onQuestionChange={onQuestionChange}
              onSendQuestion={onSendQuestion}
              question={question}
            />
          </Stack>

          <Stack className="course-detail-right" gap="sm">
            <ToolsPanel generatingType={generatingType} onGenerate={onGenerate} />
            <GeneratedContentPanel contents={generatedContents} onDelete={onDeleteGeneratedContent} onRename={onRenameGeneratedContent} />
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

export function CourseDetailPage() {
  const { courseId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const shouldOpenUploadPrompt = Boolean((location.state as { openUploadPrompt?: boolean } | null)?.openUploadPrompt);
  const [shouldOpenUploadPromptOnce] = useState(shouldOpenUploadPrompt);
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [generatedContents, setGeneratedContents] = useState<GeneratedContent[]>([]);
  const [studyPlans, setStudyPlans] = useState<StudyPlan[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [qaMessages, setQaMessages] = useState<QaMessage[]>([]);
  const [isQuestionPending, setIsQuestionPending] = useState(false);
  const [generatingType, setGeneratingType] = useState<string | null>(null);
  const [materialScope, setMaterialScope] = useState<MaterialScope>({
    include_all_parsed_materials: true,
    material_ids: [],
  });
  const [parsedMaterials, setParsedMaterials] = useState<Material[]>([]);
  const selectedMaterialNames = useMemo(
    () => materialScopeNames(materialScope, parsedMaterials),
    [materialScope, parsedMaterials],
  );

  useEffect(() => {
    if (shouldOpenUploadPrompt) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, navigate, shouldOpenUploadPrompt]);

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
          const nextConversationId = conversations[0]?.id ?? null;
          setConversationId(nextConversationId);
          if (nextConversationId) {
            listConversationMessages(nextConversationId)
              .then((messages) => {
                if (!ignore) {
                  setQaMessages(messages.map(qaMessageFromBackend));
                }
              })
              .catch(() => {
                if (!ignore) {
                  setQaMessages([]);
                }
              });
          } else {
            setQaMessages([]);
          }
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
    const trimmedQuestion = question.trim();
    const pendingUserMessage: QaMessage = {
      content: trimmedQuestion,
      id: `pending-${Date.now()}`,
      role: "user",
    };
    setQaMessages((current) => [...current, pendingUserMessage]);

    try {
      const nextAnswer = await askCourseQuestion(course.id, {
        conversation_id: conversationId,
        material_scope: materialScopeForRequest(materialScope),
        question: trimmedQuestion,
        source_page: "course_detail",
      });
      setQaMessages((current) => [
        ...current.map((message) =>
          message.id === pendingUserMessage.id ? { ...message, id: nextAnswer.user_message_id } : message,
        ),
        {
          answerType: nextAnswer.answer_type,
          citations: nextAnswer.source_citations,
          content: nextAnswer.answer_text,
          id: nextAnswer.assistant_message_id,
          role: "assistant",
          status: "done",
        },
      ]);
      setConversationId(nextAnswer.conversation_id);
      setQuestion("");
    } catch {
      setQaMessages((current) => [
        ...current,
        {
          answerType: "error",
          content: "回答生成失败，请稍后重试。",
          id: `error-${Date.now()}`,
          role: "assistant",
          status: "error",
        },
      ]);
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
        material_scope: materialScopeForRequest(materialScope),
        parameters: {},
      });
      setGeneratedContents((current) => [content, ...current]);
    } catch (nextError) {
      setWorkspaceError(errorMessage(nextError));
    } finally {
      setGeneratingType(null);
    }
  }

  async function handleRenameGeneratedContent(content: GeneratedContent, title: string) {
    const renamed = await renameGeneratedContent(content.id, title);
    setGeneratedContents((current) => current.map((item) => item.id === renamed.id ? renamed : item));
  }

  async function handleDeleteGeneratedContent(content: GeneratedContent) {
    await deleteGeneratedContent(content.id);
    setGeneratedContents((current) => current.filter((item) => item.id !== content.id));
  }

  if (isLoading) {
    return (
      <Box className="course-detail-page">
        <Paper className="course-detail-topbar" component="header" radius={0}>
          <Skeleton height={34} width={280} />
        </Paper>
        <Box className="course-detail-loading" role="status">
          <Text c="dimmed">{"正在加载课程工作台..."}</Text>
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
          <Title className="course-detail-title" order={1}>{"课程详情加载失败"}</Title>
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
        <Alert className="course-detail-workspace-error" color="red" role="alert" title="课程工作台操作失败" variant="light">
          {workspaceError}
        </Alert>
      ) : null}
      <CourseDetailWorkbench
        course={course}
        generatedContents={generatedContents}
        generatingType={generatingType}
        isQuestionPending={isQuestionPending}
        materialPanel={(
          <MaterialWorkspace
            courseId={course.id}
            materialScope={materialScope}
            onMaterialScopeChange={setMaterialScope}
            onParsedMaterialsChange={setParsedMaterials}
            openUploadPrompt={shouldOpenUploadPromptOnce}
          />
        )}
        materialScope={materialScope}
        materialScopeNames={selectedMaterialNames}
        onGenerate={handleGenerateContent}
        onDeleteGeneratedContent={handleDeleteGeneratedContent}
        onQuestionChange={setQuestion}
        onRenameGeneratedContent={handleRenameGeneratedContent}
        onSendQuestion={handleSendQuestion}
        qaMessages={qaMessages}
        question={question}
        studyPlans={studyPlans}
      />
    </>
  );
}
