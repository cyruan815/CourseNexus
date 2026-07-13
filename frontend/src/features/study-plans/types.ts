import type { MaterialScope } from "../materials/types";

export interface StudyPlanDraftRequest {
  goal_text: string;
  start_date: string;
  end_date: string;
  daily_available_minutes: number;
  material_scope: MaterialScope;
}

export interface StudyPlanPreviewSubtask {
  title: string;
  subtask_type: string;
  description: string | null;
  related_material_ids: string[];
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
  daily_available_minutes: number;
  material_scope: MaterialScope;
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
  start_time: string | null;
  end_time: string | null;
  created_at: string;
  updated_at: string;
}

export interface StudySubtaskRead {
  id: string;
  task_id: string;
  plan_id: string;
  course_id: string;
  title: string;
  subtask_type: string;
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
