export type TodayTaskStatus = "no_study_plan" | "no_task_today" | "has_task_today";

export interface Course {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  teacher: string | null;
  term: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  material_count?: number;
  today_task_status?: TodayTaskStatus;
}
