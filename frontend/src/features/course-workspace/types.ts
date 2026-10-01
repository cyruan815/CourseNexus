import type { MaterialScope } from "../materials/types";

export interface SourceCitation {
  id?: string;
  material_id: string | null;
  material_version_id?: string | null;
  chunk_id: string | null;
  material_name: string;
  page: string | number | null;
  page_index: number | null;
  hit_text: string;
  sort_order?: number | null;
}

export interface CourseQuestionCreate {
  conversation_id: string | null;
  question: string;
  material_scope: MaterialScope;
  source_page: "course_detail";
}

export interface CourseAnswer {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  answer_text: string;
  answer_type: string;
  source_citations: SourceCitation[];
}

export interface Conversation {
  id: string;
  user_id: string;
  course_id: string;
  title: string | null;
  source_page: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  course_id: string;
  role: string;
  content: string;
  answer_type: string | null;
  generation_status: string | null;
  error_code: string | null;
  material_scope_json: unknown;
  source_citations: SourceCitation[];
  created_at: string;
}

export interface GeneratedContent {
  id: string;
  user_id: string;
  course_id: string;
  study_subtask_id: string | null;
  source_message_id: string | null;
  content_type: string;
  title: string;
  content: string | null;
  content_json: unknown;
  generation_status: string;
  material_scope_json: unknown;
  error_code: string | null;
  source_citations: SourceCitation[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface GenerateContentRequest {
  content_type: string;
  material_scope: MaterialScope;
  parameters: Record<string, unknown>;
}

export interface StudyPlan {
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
