import { apiRequest } from "../../api/client";
import type {
  Conversation,
  CourseAnswer,
  CourseQuestionCreate,
  GeneratedContent,
  GenerateContentRequest,
  Message,
} from "./types";
export { listStudyPlans } from "../study-plans/api";

export function listCourseConversations(courseId: string): Promise<Conversation[]> {
  return apiRequest<Conversation[]>(`/api/v1/courses/${courseId}/conversations`, { method: "GET" });
}

export function listConversationMessages(conversationId: string): Promise<Message[]> {
  return apiRequest<Message[]>(`/api/v1/conversations/${conversationId}/messages`, { method: "GET" });
}

export function askCourseQuestion(courseId: string, payload: CourseQuestionCreate): Promise<CourseAnswer> {
  return apiRequest<CourseAnswer>(`/api/v1/courses/${courseId}/qa/questions`, {
    method: "POST",
    body: payload,
  });
}

export function listGeneratedContents(courseId: string): Promise<GeneratedContent[]> {
  return apiRequest<GeneratedContent[]>(`/api/v1/courses/${courseId}/generated-contents`, { method: "GET" });
}

export function getGeneratedContent(generatedContentId: string): Promise<GeneratedContent> {
  return apiRequest<GeneratedContent>(`/api/v1/generated-contents/${generatedContentId}`, { method: "GET" });
}

export function renameGeneratedContent(generatedContentId: string, title: string): Promise<GeneratedContent> {
  return apiRequest<GeneratedContent>(`/api/v1/generated-contents/${generatedContentId}`, {
    method: "PATCH",
    body: { title },
  });
}

export function deleteGeneratedContent(generatedContentId: string): Promise<GeneratedContent> {
  return apiRequest<GeneratedContent>(`/api/v1/generated-contents/${generatedContentId}`, { method: "DELETE" });
}

export function updateFlashcards(generatedContentId: string, cards: Array<{ front: string; back: string; tags: string[]; explanation?: string | null }>): Promise<GeneratedContent> {
  return apiRequest<GeneratedContent>(`/api/v1/generated-contents/${generatedContentId}/flashcards`, {
    method: "PATCH",
    body: { cards },
  });
}

export function updateKnowledgeItemLearningState(
  generatedContentId: string,
  knowledgeItemId: string,
  learned: boolean,
): Promise<GeneratedContent> {
  return apiRequest<GeneratedContent>(
    `/api/v1/generated-contents/${generatedContentId}/knowledge-items/${knowledgeItemId}/learning-state`,
    {
      method: "PATCH",
      body: { learned },
    },
  );
}

export function generateCourseContent(courseId: string, payload: GenerateContentRequest): Promise<GeneratedContent> {
  return apiRequest<GeneratedContent>(`/api/v1/courses/${courseId}/generations`, {
    method: "POST",
    body: payload,
  });
}

