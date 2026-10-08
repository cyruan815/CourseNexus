import { apiRequest } from "../../api/client";

export interface CheckinRead {
  id: string | null;
  checkin_date: string;
  total_subtask_count: number;
  completed_subtask_count: number;
  completion_ratio: string | number;
  color_level: number;
  has_tasks: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CheckinRangeSummaryRead {
  task_days: number;
  completed_days: number;
  current_streak_days: number;
  longest_streak_days: number;
}

export interface CheckinRangeRead {
  start_date: string;
  end_date: string;
  items: CheckinRead[];
  summary: CheckinRangeSummaryRead;
}

export interface ModelEndpointConfigRead {
  model: string;
  base_url: string | null;
  api_key_configured: boolean;
  api_key_hint: string | null;
}

export interface ModelRuntimeConfigRead {
  embedding: ModelEndpointConfigRead;
  general: ModelEndpointConfigRead;
  general_config_consistent: boolean;
}

export interface ModelEndpointConfigUpdate {
  model: string;
  base_url: string;
  api_key?: string;
}

export interface ModelRuntimeConfigUpdate {
  embedding: ModelEndpointConfigUpdate;
  general: ModelEndpointConfigUpdate;
}

export function fetchCheckinDay(date: string): Promise<CheckinRead> {
  return apiRequest<CheckinRead>(`/api/v1/checkins/${date}`, { method: "GET" });
}

export function fetchCheckinRange(startDate: string, endDate: string): Promise<CheckinRangeRead> {
  return apiRequest<CheckinRangeRead>(`/api/v1/checkins?start_date=${startDate}&end_date=${endDate}`, {
    method: "GET",
  });
}

export function fetchModelRuntimeConfig(): Promise<ModelRuntimeConfigRead> {
  return apiRequest<ModelRuntimeConfigRead>("/api/v1/model-runtime/config", { method: "GET" });
}

export function updateModelRuntimeConfig(
  payload: ModelRuntimeConfigUpdate,
): Promise<ModelRuntimeConfigRead> {
  return apiRequest<ModelRuntimeConfigRead>("/api/v1/model-runtime/config", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
