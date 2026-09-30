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

export interface StudyPlanBuildRequestBase {
  goal_text: string;
  start_date?: string | null;
  end_date?: string | null;
  duration_days?: number | null;
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

export type StudyPlanPreviewRequest = StudyPlanBuildRequestBase;

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
  confirmed_config?: {
    start_date?: string | null;
    duration_days?: number | null;
    preference?: PlanPreference | null;
    daily_available_minutes?: number | null;
    daily_minutes_source?: DailyMinutesSource | null;
  };
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
  question_version: "study_plan_diagnostic_v2";
  questions: StudyPlanDiagnosticQuestion[];
}

export interface StudyPlanTopicMasteryAnswer {
  topic_id: string;
  topic_title: string;
  mastery_level: MasteryLevel;
}

export interface StudyPlanDiagnosticProfileRequest {
  question_version: "study_plan_diagnostic_v2";
  topic_mastery: StudyPlanTopicMasteryAnswer[];
  weak_area: WeakArea;
  diagnostic_note?: string | null;
  material_scope: MaterialScope;
}

export interface StudyPlanDiagnosticProfile {
  question_version: "study_plan_diagnostic_v2";
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

export interface TodayTodos {
  date: string;
  tasks: StudyCalendarTaskTodo[];
}

export interface GlobalCalendarMonth {
  month: string;
  days: StudyCalendarDaySummary[];
}

export interface GlobalDayTodoCourseGroup {
  course_id: string;
  course_name: string;
  plan_ids: string[];
  tasks: StudyCalendarTaskTodo[];
}

export interface GlobalDayTodos {
  date: string;
  courses: GlobalDayTodoCourseGroup[];
}

export interface ExecutionCourseRead {
  course_id: string;
  name: string;
}

export interface ExecutionPlanRead {
  plan_id: string;
  title: string;
  status: string;
}

export interface ExecutionMaterialRead {
  material_id: string;
  name: string | null;
  material_type: string | null;
  parse_status: string | null;
  availability: string;
}

export interface ExecutionSubtaskRead {
  subtask_id: string;
  title: string;
  subtask_type: string;
  description: string | null;
  status: StudyTaskStatus;
  completed_at: string | null;
  sort_order: number;
}

export interface ExecutionTaskRead {
  task_id: string;
  title: string;
  task_date: string;
  status: StudyTaskStatus;
  sort_order: number;
  subtasks: ExecutionSubtaskRead[];
}

export interface ExecutionContextRead {
  course: ExecutionCourseRead;
  plan: ExecutionPlanRead;
  execution_date: string;
  tasks: ExecutionTaskRead[];
  current_subtask_id: string;
  related_materials: ExecutionMaterialRead[];
  handout_content_id: string | null;
  task_test_content_id: string | null;
}

export interface StudySubtaskQuestionRequest {
  conversation_id: string | null;
  question: string;
}

export interface StudySubtaskQaSourceCitation {
  id?: string;
  material_id: string | null;
  chunk_id: string | null;
  material_name: string;
  page: string | number | null;
  page_index: number | null;
  hit_text: string;
  sort_order?: number | null;
}

export interface StudySubtaskQuestionAnswer {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  answer_text: string;
  answer_type: string;
  source_citations: StudySubtaskQaSourceCitation[];
  used_material_ids?: string[];
}

export interface CompletionSubtaskRead {
  subtask_id: string;
  status: StudyTaskStatus;
  completed_at: string | null;
}

export interface CompletionTaskRead {
  task_id: string;
  status: StudyTaskStatus;
  completed_subtask_count: number;
  total_subtask_count: number;
}

export interface CompletionPlanRead {
  plan_id: string;
  status: string;
}

export interface CompletionCheckinRead {
  date: string;
  planned_task_count: number;
  completed_task_count: number;
  planned_subtask_count: number;
  completed_subtask_count: number;
  completed: boolean;
  first_completed_at: string | null;
  last_completed_at: string | null;
}

export interface SubtaskCompletionResult {
  changed: boolean;
  subtask: CompletionSubtaskRead;
  task: CompletionTaskRead;
  plan: CompletionPlanRead;
  checkin: CompletionCheckinRead;
}

export type TaskContentType = "handout" | "task_test";

export interface GeneratedContentRead {
  id: string;
  user_id: string;
  course_id: string;
  study_subtask_id: string | null;
  source_message_id: string | null;
  content_type: TaskContentType | string;
  title: string;
  content?: string | null;
  content_json: unknown;
  generation_status: string;
  material_scope_json: unknown;
  error_code: string | null;
  source_citations: StudySubtaskQaSourceCitation[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface HandoutGenerationRequest {
  force_regenerate?: boolean;
  parameters?: {
    language?: string;
    detail_level?: "brief" | "standard" | "deep";
  };
}

export interface TaskTestGenerationRequest {
  force_regenerate?: boolean;
  parameters?: {
    question_count?: number;
    question_types?: Array<"single_choice" | "multiple_choice" | "true_false" | "short_answer">;
    difficulty?: "easy" | "medium" | "hard";
  } | Record<string, unknown>;
}
