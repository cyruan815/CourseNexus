import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Paper,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconFileText, IconQuote } from "@tabler/icons-react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { getGeneratedContent } from "../features/course-workspace/api";
import type { GeneratedContent, SourceCitation } from "../features/course-workspace/types";
import "./generated-content-detail.css";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "生成内容加载失败";
}

function contentTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    flashcard: "Flashcards",
    knowledge_list: "知识点清单",
    mindmap: "Mind Map",
    note: "学习笔记",
    outline: "复习提纲",
    quiz: "Quiz",
    task_test: "任务测试题",
    handout: "今日讲义",
  };
  return labels[type] ?? type;
}

function statusColor(status: string): string {
  if (status === "success") {
    return "teal";
  }

  if (status === "failed") {
    return "red";
  }

  return "yellow";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asRecordArray(value: unknown, key: string): Record<string, unknown>[] {
  if (!isRecord(value) || !Array.isArray(value[key])) {
    return [];
  }

  return value[key].filter(isRecord);
}

function asText(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function formatCitationLocation(citation: SourceCitation): string {
  if (citation.page !== null && citation.page !== undefined && String(citation.page).trim()) {
    return String(citation.page);
  }

  if (typeof citation.page_index === "number" && citation.page_index > 0) {
    return `第 ${citation.page_index + 1} 页`;
  }

  return "页码未知";
}

function ResultItem({ children }: { children: ReactNode }) {
  return (
    <Paper className="generated-content-result-item" radius="md" withBorder>
      {children}
    </Paper>
  );
}

function StructuredResult({ content }: { content: GeneratedContent }) {
  if (content.generation_status === "failed") {
    return (
      <Alert color="red" role="alert" title="生成失败" variant="light">
        {content.error_code ?? "生成内容失败，请稍后重试。"}
      </Alert>
    );
  }

  const json = content.content_json;

  if (content.content_type === "outline") {
    const sections = asRecordArray(json, "sections");
    if (sections.length > 0) {
      return (
        <Stack gap="sm">
          {sections.map((section, index) => (
            <ResultItem key={asText(section.id, `section-${index}`)}>
              <Stack gap="xs">
                <Title order={3}>{asText(section.title, `第 ${index + 1} 部分`)}</Title>
                <Text>{asText(section.summary, "暂无章节说明")}</Text>
                {section.review_suggestion ? (
                  <Text c="dimmed" size="sm">
                    {asText(section.review_suggestion)}
                  </Text>
                ) : null}
              </Stack>
            </ResultItem>
          ))}
        </Stack>
      );
    }
  }

  if (content.content_type === "knowledge_list") {
    const items = asRecordArray(json, "items");
    if (items.length > 0) {
      return (
        <Stack gap="sm">
          {items.map((item, index) => (
            <ResultItem key={asText(item.id, `item-${index}`)}>
              <Group align="flex-start" justify="space-between">
                <Stack gap={4}>
                  <Title order={3}>{asText(item.name, `知识点 ${index + 1}`)}</Title>
                  <Text>{asText(item.definition, "暂无定义说明")}</Text>
                  {item.related_section ? <Text c="dimmed" size="sm">{asText(item.related_section)}</Text> : null}
                </Stack>
                {item.importance ? <Badge variant="light">{asText(item.importance)}</Badge> : null}
              </Group>
            </ResultItem>
          ))}
        </Stack>
      );
    }
  }

  if (content.content_type === "flashcard") {
    const cards = asRecordArray(json, "cards");
    if (cards.length > 0) {
      return (
        <Stack gap="sm">
          {cards.map((card, index) => (
            <ResultItem key={asText(card.id, `card-${index}`)}>
              <Stack gap="xs">
                <Badge variant="light">卡片 {index + 1}</Badge>
                <Title order={3}>{asText(card.front, "卡片正面待生成")}</Title>
                <Text>{asText(card.back, "卡片背面待生成")}</Text>
              </Stack>
            </ResultItem>
          ))}
        </Stack>
      );
    }
  }

  if (content.content_type === "quiz" || content.content_type === "task_test") {
    const questions = asRecordArray(json, "questions");
    if (questions.length > 0) {
      return (
        <Stack gap="sm">
          {questions.map((question, index) => (
            <ResultItem key={asText(question.id, `question-${index}`)}>
              <Stack gap="xs">
                <Badge variant="light">题目 {index + 1}</Badge>
                <Title order={3}>{asText(question.question_text, "题干待生成")}</Title>
                {question.explanation ? <Text c="dimmed" size="sm">{asText(question.explanation)}</Text> : null}
              </Stack>
            </ResultItem>
          ))}
        </Stack>
      );
    }
  }

  if (content.content_type === "mindmap") {
    const nodes = asRecordArray(json, "nodes");
    if (nodes.length > 0) {
      return (
        <Stack gap="sm">
          {nodes.map((node, index) => (
            <ResultItem key={asText(node.id, `node-${index}`)}>
              <Stack gap={4}>
                <Title order={3}>{asText(node.label, `节点 ${index + 1}`)}</Title>
                {node.summary ? <Text>{asText(node.summary)}</Text> : null}
              </Stack>
            </ResultItem>
          ))}
        </Stack>
      );
    }
  }

  if (content.content) {
    return (
      <Paper className="generated-content-text-result" radius="md" withBorder>
        <Text>{content.content}</Text>
      </Paper>
    );
  }

  return (
    <Stack className="generated-content-empty" gap="xs">
      <IconFileText size={34} stroke={1.7} />
      <Text fw={700}>暂无可展示内容</Text>
      <Text c="dimmed" size="sm">
        当前生成记录没有可渲染的结构化结果。
      </Text>
    </Stack>
  );
}

function CitationPanel({ citations }: { citations: SourceCitation[] }) {
  if (citations.length === 0) {
    return (
      <Stack className="generated-content-citation-empty" gap="xs">
        <IconQuote size={30} stroke={1.7} />
        <Text fw={700}>当前没有可展示的引用来源</Text>
        <Text c="dimmed" size="sm">
          后端返回空引用时，前端不会补造来源。
        </Text>
      </Stack>
    );
  }

  return (
    <Stack gap="sm">
      {citations.map((citation, index) => (
        <Paper className="generated-content-citation" key={citation.id ?? `${citation.material_id}-${index}`} radius="md" withBorder>
          <Stack gap={6}>
            <Text fw={700} size="sm">
              {citation.material_name} · {formatCitationLocation(citation)}
            </Text>
            <Text c="dimmed" size="sm">
              {citation.hit_text}
            </Text>
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

export function GeneratedContentDetailPage() {
  const { generatedContentId } = useParams();
  const [content, setContent] = useState<GeneratedContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    if (!generatedContentId) {
      setError("生成内容不存在");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    getGeneratedContent(generatedContentId)
      .then((nextContent) => {
        if (!ignore) {
          setContent(nextContent);
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
  }, [generatedContentId]);

  if (isLoading) {
    return (
      <Box className="generated-content-page">
        <Stack className="generated-content-loading" role="status">
          <Skeleton height={34} width={260} />
          <Skeleton height={96} radius="md" />
          <Skeleton height={360} radius="md" />
        </Stack>
      </Box>
    );
  }

  if (error || !content) {
    return (
      <Box className="generated-content-page">
        <Alert className="generated-content-error" color="red" role="alert" title="生成内容加载失败" variant="light">
          {error ?? "生成内容不存在"}
        </Alert>
      </Box>
    );
  }

  return (
    <Box className="generated-content-page">
      <Box className="generated-content-shell" component="main">
        <Stack gap="md">
          <Group justify="space-between">
            <Button component={Link} leftSection={<IconArrowLeft size={16} />} to={`/courses/${content.course_id}`} variant="subtle">
              返回课程详情
            </Button>
            <Badge color={statusColor(content.generation_status)} variant="light">
              {content.generation_status}
            </Badge>
          </Group>

          <Paper className="generated-content-hero" radius="md" withBorder>
            <Stack gap="xs">
              <Group gap="xs">
                <Badge color="blue" variant="light">
                  {contentTypeLabel(content.content_type)}
                </Badge>
                <Text c="dimmed" size="sm">
                  {content.created_at}
                </Text>
              </Group>
              <Title order={1}>{content.title}</Title>
              <Text c="dimmed" size="sm">
                当前详情只展示后端已返回的生成结果和引用来源；生成器仍处于基础占位阶段时，页面不会补造最终学习产品内容。
              </Text>
            </Stack>
          </Paper>

          <Box className="generated-content-layout">
            <Paper className="generated-content-main" radius="md" withBorder>
              <Stack gap="md">
                <Title order={2}>生成结果</Title>
                <StructuredResult content={content} />
              </Stack>
            </Paper>

            <Paper className="generated-content-side" radius="md" withBorder>
              <Stack gap="md">
                <Title order={2}>引用来源</Title>
                <CitationPanel citations={content.source_citations ?? []} />
              </Stack>
            </Paper>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
}
