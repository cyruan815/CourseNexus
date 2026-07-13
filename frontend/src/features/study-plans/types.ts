import type { MaterialScope } from "../materials/types";

export type PlanPreference = "balanced" | "fast_track" | "mastery" | "sprint";
export type StudyPlanClientFlow = "legacy" | "wizard_v1";
export type StudySubtaskType = "learn" | "review" | "quiz" | "test";

export interface StudyPlanPreviewRequest {
  goal_text: string;
  start_date: string;
  end_date: string;
  daily_available_minutes: number;
  preference: PlanPreference;
  diagnostic_profile?: Record<string, unknown>;
  material_scope: MaterialScope;
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

export interface StudyPlanPreview {
  course_id: string;
  title: string;
  goal_text: string;
  start_date: string;
  end_date: string;
  duration_days?: number | null;
  daily_available_minutes: number;
  recommended_daily_minutes?: number | null;
  daily_minutes_source?: string | null;
  preference?: PlanPreference;
  diagnostic_profile?: Record<string, unknown>;
  material_snapshot?: Record<string, unknown>;
  material_scope: MaterialScope;
  coverage?: Record<string, unknown>;
  capacity?: Record<string, unknown>;
  generation_metadata?: Record<string, unknown>;
  tasks: StudyPlanPreviewTask[];
}

export interface StudyPlanSaveRequest extends StudyPlanPreviewRequest {
  client_flow: StudyPlanClientFlow;
  title?: string;
  tasks: StudyPlanPreviewTask[];
}

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
