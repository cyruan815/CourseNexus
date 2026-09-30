import { Alert, Text } from "@mantine/core";
import type { GeneratedContent } from "../course-workspace/types";
import { flashcards, knowledgeItems, mindmapContent, outlineSections, quizQuestions, taskTestQuestions } from "./guards";
import { FlashcardResult } from "./renderers/FlashcardResult";
import { HandoutMarkdownRenderer } from "./renderers/handout/HandoutMarkdownRenderer";
import { KnowledgeListResult } from "./renderers/KnowledgeListResult";
import { MindmapResult } from "./renderers/MindmapResult";
import { OutlineResult } from "./renderers/OutlineResult";
import { QuizResult } from "./renderers/QuizResult";
import { TaskTestResult } from "./renderers/TaskTestResult";

export function GeneratedContentRenderer({ content }: { content: GeneratedContent }) {
  if (content.generation_status === "failed") return <Alert color="red" role="alert" title="生成失败">{content.error_code ?? "生成内容失败，请重新生成。"}</Alert>;
  const invalid = <Alert color="yellow" title="内容结构不可读取">当前记录缺少必要字段，无法使用交互视图。</Alert>;
  if (content.content_type === "quiz") { const value = quizQuestions(content.content_json); return value ? <QuizResult questions={value} /> : invalid; }
  if (content.content_type === "task_test") { const value = taskTestQuestions(content.content_json); return value ? <TaskTestResult attemptKey={content.id} citations={content.source_citations} questions={value} /> : invalid; }
  if (content.content_type === "flashcard") { const value = flashcards(content.content_json); return value ? <FlashcardResult cards={value} generatedContentId={content.id} /> : invalid; }
  if (content.content_type === "mindmap") { const value = mindmapContent(content.content_json); return value ? <MindmapResult content={value} /> : invalid; }
  if (content.content_type === "outline") { const value = outlineSections(content.content_json); return value ? <OutlineResult sections={value} /> : invalid; }
  if (content.content_type === "knowledge_list") { const value = knowledgeItems(content.content_json); return value ? <KnowledgeListResult generatedContentId={content.id} items={value} /> : invalid; }
  if (content.content_type === "handout") {
    const markdown = content.content?.trim();
    return markdown ? <HandoutMarkdownRenderer markdown={markdown} /> : invalid;
  }
  return content.content ? <Text className="gc-text-fallback">{content.content}</Text> : <Alert color="gray">暂无可展示内容</Alert>;
}
