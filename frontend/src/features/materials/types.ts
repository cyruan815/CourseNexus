export interface MaterialFolder {
  id: string;
  user_id: string;
  course_id: string;
  name: string;
  sort_order: number | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Material {
  id: string;
  course_id: string;
  user_id: string;
  folder_id: string | null;
  name: string;
  material_type: string;
  source_type: string;
  file_url: string | null;
  source_url: string | null;
  file_size: number | null;
  mime_type: string | null;
  parse_status: string;
  parse_error: string | null;
  page_count: number | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface MaterialScope {
  include_all_parsed_materials: boolean;
  material_ids: string[];
}

export interface MaterialFolderCreate {
  name: string;
  sort_order?: number;
}

export interface MaterialFolderUpdate {
  name?: string;
  sort_order?: number;
}
