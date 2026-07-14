import { Alert, Badge, Box, Button, Group, Paper, Skeleton, Stack, Text, Title } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import { getGeneratedContent } from "../features/course-workspace/api";
import type { GeneratedContent } from "../features/course-workspace/types";
import { GeneratedContentRenderer } from "../features/generated-content/GeneratedContentRenderer";
import "../features/generated-content/generated-content.css";
import "./generated-content-detail.css";

const labels: Record<string, string> = { quiz: "Quiz", flashcard: "Flashcards", mindmap: "Mind Map", outline: "复习提纲", knowledge_list: "知识点清单", handout: "今日讲义", task_test: "任务测试题" };
const statusColor = (status: string) => status === "success" ? "teal" : status === "failed" ? "red" : "yellow";
const errorMessage = (error: unknown) => error instanceof ApiError || error instanceof Error ? error.message : "生成内容加载失败";

export function GeneratedContentDetailPage() {
  const { generatedContentId } = useParams();
  const [content, setContent] = useState<GeneratedContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let ignore = false;
    if (!generatedContentId) { setError("生成内容不存在"); setLoading(false); return; }
    setLoading(true); setError(null);
    getGeneratedContent(generatedContentId).then((value) => { if (!ignore) setContent(value); }).catch((reason: unknown) => { if (!ignore) setError(errorMessage(reason)); }).finally(() => { if (!ignore) setLoading(false); });
    return () => { ignore = true; };
  }, [generatedContentId]);

  if (loading) return <Box className="generated-content-page"><Stack className="generated-content-loading" role="status"><Skeleton height={34} width={260} /><Skeleton height={96} /><Skeleton height={420} /></Stack></Box>;
  if (error || !content) return <Box className="generated-content-page"><Alert className="generated-content-error" color="red" role="alert" title="生成内容加载失败">{error ?? "生成内容不存在"}</Alert></Box>;

  return <Box className="generated-content-page"><Box className="generated-content-shell" component="main"><Stack gap="md">
    <Group justify="space-between"><Button component={Link} leftSection={<IconArrowLeft size={16} />} to={`/courses/${content.course_id}`} variant="subtle">返回课程详情</Button><Badge color={statusColor(content.generation_status)} variant="light">{content.generation_status}</Badge></Group>
    <header className="generated-content-header"><Group gap="xs"><Badge variant="light">{labels[content.content_type] ?? content.content_type}</Badge><Text c="dimmed" size="sm">{content.created_at}</Text></Group><Title order={1}>{content.title}</Title></header>
    <Paper className="generated-content-main" withBorder><GeneratedContentRenderer content={content} /></Paper>
  </Stack></Box></Box>;
}
