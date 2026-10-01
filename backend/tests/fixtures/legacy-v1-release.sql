PRAGMA foreign_keys = ON;

INSERT INTO users (id, username, password_hash, nickname)
VALUES ('usr_release_legacy', 'release-legacy', 'synthetic-hash', 'Release Fixture');

INSERT INTO courses (id, user_id, name, description, status)
VALUES (
  'crs_release_legacy',
  'usr_release_legacy',
  'Calculus Release Fixture',
  'Synthetic migration acceptance data',
  'active'
);

INSERT INTO course_materials (
  id,
  course_id,
  user_id,
  name,
  material_type,
  source_type,
  file_url,
  file_size,
  mime_type,
  parse_status,
  parse_quality,
  parse_diagnostics_json,
  page_count
)
VALUES (
  'mat_release_legacy',
  'crs_release_legacy',
  'usr_release_legacy',
  'limits-and-continuity.pdf',
  'pdf',
  'file',
  'usr_release_legacy/crs_release_legacy/mat_release_legacy/limits-and-continuity.pdf',
  2249,
  'application/pdf',
  'parsed',
  'complete',
  '{"parser":"docling","profile":"pdf_text_first","conversion_status":"success"}',
  1
);

INSERT INTO material_chunks (
  id,
  material_id,
  course_id,
  chunk_index,
  page,
  page_index,
  heading,
  content_text,
  embedding_id
)
VALUES (
  'chk_release_legacy',
  'mat_release_legacy',
  'crs_release_legacy',
  0,
  '1',
  0,
  'Limits and Continuity',
  'A limit describes the value a function approaches near an input.',
  'emb_release_legacy'
);

INSERT INTO conversations (id, user_id, course_id, title, source_page, status)
VALUES (
  'conv_release_legacy',
  'usr_release_legacy',
  'crs_release_legacy',
  'Legacy limits question',
  'course_detail',
  'active'
);

INSERT INTO messages (
  id,
  conversation_id,
  course_id,
  role,
  content,
  answer_type,
  generation_status,
  material_scope_json
)
VALUES (
  'msg_release_legacy',
  'conv_release_legacy',
  'crs_release_legacy',
  'assistant',
  'A limit describes an approached value. [[cite:1]]',
  'grounded',
  'success',
  '{"include_all_parsed_materials":false,"material_ids":["mat_release_legacy"]}'
);

INSERT INTO source_citations (
  id,
  message_id,
  material_id,
  chunk_id,
  material_name,
  page,
  page_index,
  hit_text,
  sort_order
)
VALUES (
  'cite_release_legacy',
  'msg_release_legacy',
  'mat_release_legacy',
  'chk_release_legacy',
  'limits-and-continuity.pdf',
  '1',
  0,
  'A limit describes the value a function approaches near an input.',
  1
);

INSERT INTO study_plans (
  id,
  user_id,
  course_id,
  title,
  goal_text,
  parsed_config_json,
  start_date,
  end_date,
  daily_available_minutes,
  status,
  idempotency_key_hash
)
VALUES (
  'sp_release_legacy',
  'usr_release_legacy',
  'crs_release_legacy',
  'Limits Review 2026-10-01',
  'Review limits and continuity',
  '{"material_scope":{"include_all_parsed_materials":false,"material_ids":["mat_release_legacy"]},"tasks_source":"confirmed"}',
  '2026-10-01',
  '2026-10-01',
  45,
  'active',
  NULL
);

INSERT INTO study_tasks (
  id,
  plan_id,
  course_id,
  title,
  task_date,
  status,
  sort_order
)
VALUES (
  'task_release_legacy',
  'sp_release_legacy',
  'crs_release_legacy',
  'Limits and continuity review',
  '2026-10-01',
  'not_started',
  1
);

INSERT INTO study_subtasks (
  id,
  task_id,
  plan_id,
  course_id,
  title,
  subtask_type,
  description,
  related_material_ids_json,
  status,
  sort_order
)
VALUES
  (
    'sub_release_legacy_learn',
    'task_release_legacy',
    'sp_release_legacy',
    'crs_release_legacy',
    'Read the core concept',
    'learn',
    'Review the definition and three continuity conditions.',
    '["mat_release_legacy"]',
    'not_started',
    1
  ),
  (
    'sub_release_legacy_test',
    'task_release_legacy',
    'sp_release_legacy',
    'crs_release_legacy',
    'Check understanding',
    'test',
    'Answer one grounded question.',
    '["mat_release_legacy"]',
    'not_started',
    2
  );
