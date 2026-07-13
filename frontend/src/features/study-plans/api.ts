import { apiRequest } from "../../api/client";
import type {
  CourseStudyCalendarDay,
  CourseStudyCalendarMonth,
  GlobalCalendarMonth,
  GlobalDayTodos,
  StudyPlanConfigParseRequest,
  StudyPlanConfigParseResponse,
  StudyPlanDetail,
  StudyPlanDiagnosticProfile,
  StudyPlanDiagnosticProfileRequest,
  StudyPlanDiagnosticQuestionRequest,
  StudyPlanDiagnosticQuestionsResponse,
  StudyPlanPreview,
  StudyPlanPreviewRequest,
  StudyPlanRead,
  StudyPlanRegenerationPreviewRequest,
  StudyPlanReplaceRequest,
  StudyPlanSaveRequest,
  TodayTodos,
} from "./types";

export function parseStudyPlanConfig(
  courseId: string,
  payload: StudyPlanConfigParseRequest,
): Promise<StudyPlanConfigParseResponse> {
  return apiRequest<StudyPlanConfigParseResponse>(`/api/v1/courses/${courseId}/study-plan-config-parses`, {
    method: "POST",
    body: payload,
  });
}

export function fetchDiagnosticQuestions(
  courseId: string,
  payload: StudyPlanDiagnosticQuestionRequest,
): Promise<StudyPlanDiagnosticQuestionsResponse> {
  return apiRequest<StudyPlanDiagnosticQuestionsResponse>(
    `/api/v1/courses/${courseId}/study-plan-diagnostic-questions`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export function createDiagnosticProfile(
  courseId: string,
  payload: StudyPlanDiagnosticProfileRequest,
): Promise<StudyPlanDiagnosticProfile> {
  return apiRequest<StudyPlanDiagnosticProfile>(`/api/v1/courses/${courseId}/study-plan-diagnostic-profiles`, {
    method: "POST",
    body: payload,
  });
}

export function listStudyPlans(courseId: string): Promise<StudyPlanRead[]> {
  return apiRequest<StudyPlanRead[]>(`/api/v1/courses/${courseId}/study-plans`, { method: "GET" });
}

export function previewStudyPlan(
  courseId: string,
  payload: StudyPlanPreviewRequest,
): Promise<StudyPlanPreview> {
  return apiRequest<StudyPlanPreview>(`/api/v1/courses/${courseId}/study-plans/preview`, {
    method: "POST",
    body: payload,
  });
}

export function saveStudyPlan(
  courseId: string,
  payload: StudyPlanSaveRequest,
  idempotencyKey: string,
): Promise<StudyPlanDetail> {
  return apiRequest<StudyPlanDetail>(`/api/v1/courses/${courseId}/study-plans`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey,
    },
    body: payload,
  });
}

export function fetchStudyPlan(planId: string): Promise<StudyPlanDetail> {
  return apiRequest<StudyPlanDetail>(`/api/v1/study-plans/${planId}`, { method: "GET" });
}

export function previewStudyPlanRegeneration(
  planId: string,
  payload: StudyPlanRegenerationPreviewRequest,
): Promise<StudyPlanPreview> {
  return apiRequest<StudyPlanPreview>(`/api/v1/study-plans/${planId}/regeneration-previews`, {
    method: "POST",
    body: payload,
  });
}

export function replaceStudyPlan(
  planId: string,
  payload: StudyPlanReplaceRequest,
): Promise<StudyPlanDetail> {
  return apiRequest<StudyPlanDetail>(`/api/v1/study-plans/${planId}`, {
    method: "PUT",
    body: payload,
  });
}

export function deleteStudyPlan(planId: string): Promise<StudyPlanRead> {
  return apiRequest<StudyPlanRead>(`/api/v1/study-plans/${planId}`, { method: "DELETE" });
}

export function fetchCourseStudyCalendar(
  courseId: string,
  month: string,
): Promise<CourseStudyCalendarMonth> {
  return apiRequest<CourseStudyCalendarMonth>(`/api/v1/courses/${courseId}/study-calendar?month=${month}`, {
    method: "GET",
  });
}

export function fetchCourseStudyCalendarDay(
  courseId: string,
  date: string,
): Promise<CourseStudyCalendarDay> {
  return apiRequest<CourseStudyCalendarDay>(`/api/v1/courses/${courseId}/study-calendar/days/${date}`, {
    method: "GET",
  });
}

export function fetchTodayTodos(date: string): Promise<TodayTodos> {
  return apiRequest<TodayTodos>(`/api/v1/todos/today?date=${date}`, { method: "GET" });
}

export function fetchGlobalCalendarMonth(month: string): Promise<GlobalCalendarMonth> {
  return apiRequest<GlobalCalendarMonth>(`/api/v1/calendar/month?month=${month}`, { method: "GET" });
}

export function fetchGlobalCalendarDayTodos(date: string): Promise<GlobalDayTodos> {
  return apiRequest<GlobalDayTodos>(`/api/v1/calendar/days/${date}/todos`, { method: "GET" });
}
