import { apiRequest } from "../../api/client";
import { ApiError } from "../../api/errors";
import type { ApiErrorResponse } from "../../api/types";
import { clearSessionToken, getSessionToken } from "../auth/session";
import type {
  CourseStudyCalendarDay,
  CourseStudyCalendarMonth,
  ExecutionContextRead,
  GeneratedContentRead,
  GlobalCalendarMonth,
  GlobalDayTodos,
  HandoutGenerationRequest,
  SubtaskCompletionResult,
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
  StudySubtaskQuestionAnswer,
  StudySubtaskQuestionRequest,
  TaskTestGenerationRequest,
  TodayTodos,
} from "./types";

function buildApiPath(path: string): string {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${apiBaseUrl}${path}`;
}

function isApiErrorResponse(payload: unknown): payload is ApiErrorResponse {
  return (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof (payload as ApiErrorResponse).error?.code === "string"
  );
}

function filenameFromDisposition(disposition: string | null, fallback: string): string {
  if (!disposition) {
    return fallback;
  }

  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].trim().replace(/^"|"$/g, ""));
  }

  const asciiMatch = /filename="?([^";]+)"?/i.exec(disposition);
  return asciiMatch?.[1]?.trim() || fallback;
}

async function apiFileRequest(path: string, fallbackFilename: string): Promise<DownloadedFile> {
  const headers: Record<string, string> = {};
  const token = getSessionToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(buildApiPath(path), {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearSessionToken();
    }

    const payload = await response.json().catch(() => undefined);
    if (isApiErrorResponse(payload)) {
      throw new ApiError(payload.error, response.status);
    }

    throw new ApiError(
      {
        code: "HTTP_ERROR",
        message: `Request failed with status ${response.status}`,
      },
      response.status,
    );
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get("Content-Disposition"), fallbackFilename),
  };
}

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

export function fetchSubtaskExecutionContext(subtaskId: string): Promise<ExecutionContextRead> {
  return apiRequest<ExecutionContextRead>(`/api/v1/study-subtasks/${subtaskId}/execution-context`, {
    method: "GET",
  });
}

export function askStudySubtaskQuestion(
  subtaskId: string,
  payload: StudySubtaskQuestionRequest,
): Promise<StudySubtaskQuestionAnswer> {
  return apiRequest<StudySubtaskQuestionAnswer>(`/api/v1/study-subtasks/${subtaskId}/qa/questions`, {
    method: "POST",
    body: payload,
  });
}

export function updateSubtaskCompletion(
  subtaskId: string,
  completed: boolean,
): Promise<SubtaskCompletionResult> {
  return apiRequest<SubtaskCompletionResult>(`/api/v1/study-subtasks/${subtaskId}/completion`, {
    method: "PUT",
    body: { completed },
  });
}

export function generateSubtaskHandout(
  subtaskId: string,
  payload: HandoutGenerationRequest = { force_regenerate: false },
): Promise<GeneratedContentRead> {
  return apiRequest<GeneratedContentRead>(`/api/v1/study-subtasks/${subtaskId}/handouts`, {
    method: "POST",
    body: payload,
  });
}

export function generateSubtaskTaskTest(
  subtaskId: string,
  payload: TaskTestGenerationRequest = { force_regenerate: false },
): Promise<GeneratedContentRead> {
  return apiRequest<GeneratedContentRead>(`/api/v1/study-subtasks/${subtaskId}/task-tests`, {
    method: "POST",
    body: payload,
  });
}

export interface DownloadedFile {
  blob: Blob;
  filename: string;
}

export function exportGeneratedContentMarkdown(generatedContentId: string): Promise<DownloadedFile> {
  return apiFileRequest(
    `/api/v1/generated-contents/${generatedContentId}/exports/markdown`,
    `task-test-${generatedContentId}.md`,
  );
}

export function exportGeneratedContentPdf(generatedContentId: string): Promise<DownloadedFile> {
  return apiFileRequest(
    `/api/v1/generated-contents/${generatedContentId}/exports/pdf`,
    `handout-${generatedContentId}.pdf`,
  );
}
