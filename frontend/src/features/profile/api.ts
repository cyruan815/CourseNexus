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

export function fetchCheckinDay(date: string): Promise<CheckinRead> {
  return apiRequest<CheckinRead>(`/api/v1/checkins/${date}`, { method: "GET" });
}

export function fetchCheckinRange(startDate: string, endDate: string): Promise<CheckinRangeRead> {
  return apiRequest<CheckinRangeRead>(`/api/v1/checkins?start_date=${startDate}&end_date=${endDate}`, {
    method: "GET",
  });
}
