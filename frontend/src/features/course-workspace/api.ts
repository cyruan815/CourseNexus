import { apiRequest } from "../../api/client";
import type {
  Conversation,
  CourseAnswer,
  CourseQuestionCreate,
  GeneratedContent,
  GenerateContentRequest,
  Message,
  StudyPlan,
} from "./types";

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

export function generateCourseContent(courseId: string, payload: GenerateContentRequest): Promise<GeneratedContent> {
  return apiRequest<GeneratedContent>(`/api/v1/courses/${courseId}/generations`, {
    method: "POST",
    body: payload,
  });
}

export function listStudyPlans(courseId: string): Promise<StudyPlan[]> {
  return apiRequest<StudyPlan[]>(`/api/v1/courses/${courseId}/study-plans`, { method: "GET" });
}
