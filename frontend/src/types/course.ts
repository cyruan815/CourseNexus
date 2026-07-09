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
}
