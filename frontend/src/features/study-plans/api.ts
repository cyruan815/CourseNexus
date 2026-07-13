import { apiRequest } from "../../api/client";
import type {
  StudyPlanDetail,
  StudyPlanDraftRequest,
  StudyPlanPreview,
  StudyPlanRead,
} from "./types";

export function listStudyPlans(courseId: string): Promise<StudyPlanRead[]> {
  return apiRequest<StudyPlanRead[]>(`/api/v1/courses/${courseId}/study-plans`, { method: "GET" });
}

export function previewStudyPlan(
  courseId: string,
  payload: StudyPlanDraftRequest,
): Promise<StudyPlanPreview> {
  return apiRequest<StudyPlanPreview>(`/api/v1/courses/${courseId}/study-plans/preview`, {
    method: "POST",
    body: payload,
  });
}

export function saveStudyPlan(
  courseId: string,
  payload: StudyPlanDraftRequest,
): Promise<StudyPlanDetail> {
  return apiRequest<StudyPlanDetail>(`/api/v1/courses/${courseId}/study-plans`, {
    method: "POST",
    body: payload,
  });
}

export function fetchStudyPlan(planId: string): Promise<StudyPlanDetail> {
  return apiRequest<StudyPlanDetail>(`/api/v1/study-plans/${planId}`, { method: "GET" });
}
