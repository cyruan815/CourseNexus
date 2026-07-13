import type { MaterialScope } from "../materials/types";

export type DailyMinutesSource = "user_text" | "system_estimated" | "user_modified";
export type PlanPreference = "balanced" | "fast_track" | "mastery" | "sprint";
export type StudyPlanClientFlow = "legacy" | "wizard_v1";
export type StudySubtaskType = "learn" | "review" | "quiz" | "test";
export type StudyTaskStatus = "not_started" | "in_progress" | "completed";
export type DiagnosticQuestionType = "topic_mastery" | "weak_area" | "diagnostic_note";
export type MasteryLevel = "none" | "heard" | "some" | "familiar";
export type WeakArea = "concept" | "calculation" | "application" | "memorization" | "other";
export type PriorKnowledgeLevel = "none" | "little" | "some" | "solid";
export type ExplanationStyle = "plain_language" | "step_by_step" | "example_first" | "exam_focused";

export type StudyPlanDateRange =
  | {
      end_date: string;
      duration_days?: number | null;
    }
  | {
      duration_days: number;
      end_date?: string | null;
    };

export interface StudyPlanBuildRequestBase {
  goal_text: string;
  start_date: string;
  daily_available_minutes?: number | null;
  recommended_daily_minutes?: number | null;
  daily_minutes_source?: DailyMinutesSource | null;
  preference: PlanPreference;
  diagnostic_profile?: StudyPlanDiagnosticProfile | Record<string, unknown>;
  material_snapshot?: Record<string, unknown>;
  coverage?: Record<string, unknown>;
  capacity?: Record<string, unknown>;
  generation_metadata?: Record<string, unknown>;
  material_scope: MaterialScope;
}

export type StudyPlanPreviewRequest = StudyPlanBuildRequestBase & StudyPlanDateRange;

export interface StudyPlanConfigParseRequest {
  goal_text: string;
  material_scope: MaterialScope;
}

export interface StudyPlanConfigParseResponse {
  goal_text?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  duration_days?: number | null;
  daily_available_minutes?: number | null;
  recommended_daily_minutes?: number | null;
  daily_minutes_source?: DailyMinutesSource | null;
  preference?: PlanPreference | null;
  diagnostic_profile?: Record<string, unknown>;
  material_snapshot?: Record<string, unknown>;
  coverage?: Record<string, unknown>;
  capacity?: Record<string, unknown>;
  generation_metadata?: Record<string, unknown>;
  material_scope: MaterialScope;
  unresolved_fields: string[];
}

export interface StudyPlanDiagnosticQuestionRequest {
  goal_text: string;
  material_scope: MaterialScope;
}

export interface StudyPlanDiagnosticQuestionOption {
  value: string;
  label: string;
}

export interface StudyPlanDiagnosticQuestion {
  question_id: string;
  question_type: DiagnosticQuestionType;
  question_text: string;
  sort_order: number;
  required: boolean;
  topic_id: string | null;
  topic_title: string | null;
  options: StudyPlanDiagnosticQuestionOption[];
  placeholder: string | null;
}

export interface StudyPlanDiagnosticQuestionsResponse {
  question_version: "study_plan_diagnostic_v1";
  questions: StudyPlanDiagnosticQuestion[];
}

export interface StudyPlanTopicMasteryAnswer {
  topic_id: string;
  topic_title: string;
  mastery_level: MasteryLevel;
}

export interface StudyPlanDiagnosticProfileRequest {
  question_version: "study_plan_diagnostic_v1";
  topic_mastery: StudyPlanTopicMasteryAnswer[];
  weak_area: WeakArea;
  diagnostic_note?: string | null;
  material_scope: MaterialScope;
}

export interface StudyPlanDiagnosticProfile {
  question_version: "study_plan_diagnostic_v1";
  prior_knowledge_level: PriorKnowledgeLevel;
  foundation_needed: boolean;
  weak_topics: string[];
  weak_area: WeakArea;
  explanation_style: ExplanationStyle;
  diagnostic_note?: string | null;
}

export interface StudyPlanPreviewSubtask {
  title: string;
  subtask_type: StudySubtaskType;
  description: string | null;
  related_material_ids: string[];
  estimated_minutes: number;
  citation_chunk_ids: string[];
  generation_parameters: Record<string, unknown>;
  sort_order: number;
}

export interface StudyPlanPreviewTask {
  title: string;
  task_date: string;
  sort_order: number;
  subtasks: StudyPlanPreviewSubtask[];
}

export interface StudyPlanCoverage {
  expected_material_ids: string[];
  processed_material_ids: string[];
  batch_count: number;
}

export interface StudyPlanPreview {
  course_id: string;
  title: string;
  goal_text: string;
  start_date: string;
  end_date: string;
  duration_days?: number | null;
  daily_available_minutes: number;
  recommended_daily_minutes?: number | null;
  daily_minutes_source?: DailyMinutesSource | null;
  preference?: PlanPreference;
  diagnostic_profile?: StudyPlanDiagnosticProfile | Record<string, unknown>;
  material_snapshot?: Record<string, unknown>;
  material_scope: MaterialScope;
  coverage?: StudyPlanCoverage;
  capacity?: Record<string, unknown>;
  generation_metadata?: Record<string, unknown>;
  tasks: StudyPlanPreviewTask[];
}

export type StudyPlanSaveRequest = StudyPlanPreviewRequest & {
  client_flow: StudyPlanClientFlow;
  title?: string;
  tasks: StudyPlanPreviewTask[];
};

export interface StudyPlanRegenerationPreviewRequest {
  goal_text?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  duration_days?: number | null;
  daily_available_minutes?: number | null;
  preference?: PlanPreference | null;
  diagnostic_profile?: StudyPlanDiagnosticProfile | Record<string, unknown> | null;
  material_scope?: MaterialScope | null;
}

export type StudyPlanReplaceRequest = StudyPlanSaveRequest & {
  expected_updated_at: string;
  title: string;
  tasks: StudyPlanPreviewTask[];
};

export interface StudyPlanRead {
  id: string;
  user_id: string;
  course_id: string;
  title: string;
  goal_text: string;
  parsed_config_json: unknown;
  start_date: string;
  end_date: string;
  daily_available_minutes: number;
  status: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface StudyTaskRead {
  id: string;
  plan_id: string;
  course_id: string;
  title: string;
  task_date: string;
  status: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface StudySubtaskRead {
  id: string;
  task_id: string;
  plan_id: string;
  course_id: string;
  title: string;
  subtask_type: StudySubtaskType;
  description: string | null;
  related_material_ids_json?: string[];
  related_material_ids?: string[];
  status: string;
  completed_at: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface StudyPlanDetail {
  plan: StudyPlanRead;
  tasks: StudyTaskRead[];
  subtasks: StudySubtaskRead[];
}

export interface StudyCalendarTaskSummary {
  task_id: string;
  plan_id: string;
  course_id: string;
  course_name: string;
  title: string;
  status: StudyTaskStatus;
  derived_status: StudyTaskStatus;
  sort_order: number;
}

export interface StudyCalendarDaySummary {
  date: string;
  course_count: number;
  task_count: number;
  subtask_count: number;
  completed_subtask_count: number;
  status: StudyTaskStatus;
  task_summaries: StudyCalendarTaskSummary[];
  hidden_task_count: number;
}

export interface CourseStudyCalendarMonth {
  course_id: string;
  course_name: string;
  month: string;
  days: StudyCalendarDaySummary[];
}

export interface StudyCalendarSubtaskTodo {
  subtask_id: string;
  title: string;
  subtask_type: string;
  description: string | null;
  status: StudyTaskStatus;
  sort_order: number;
  execution_url: string | null;
}

export interface StudyCalendarTaskTodo {
  task_id: string;
  plan_id: string;
  course_id: string;
  course_name: string;
  title: string;
  task_date: string;
  status: StudyTaskStatus;
  derived_status: StudyTaskStatus;
  completed_subtask_count: number;
  total_subtask_count: number;
  first_incomplete_subtask_id: string | null;
  subtasks: StudyCalendarSubtaskTodo[];
}

export interface CourseStudyCalendarDay {
  course_id: string;
  course_name: string;
  date: string;
  tasks: StudyCalendarTaskTodo[];
}
