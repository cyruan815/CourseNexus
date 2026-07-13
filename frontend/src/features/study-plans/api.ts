import { apiRequest } from "../../api/client";
import type {
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
