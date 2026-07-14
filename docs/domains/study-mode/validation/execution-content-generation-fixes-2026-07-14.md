# Execution Content Generation Fixes - 2026-07-14

## Scope

This note records the 2026-07-14 fixes for task execution generated content:

- generated content detail page back navigation
- restoring existing task-test content in the execution page
- preventing cross-subtask loading state leakage while content is generated
- handout citation rebinding for typed table rows

## Frontend Behavior

`StudyTaskExecutionPage` treats `execution-context` as the source of task and status metadata. When the context contains `handout_content_id` or `task_test_content_id`, the page must call:

```text
GET /api/v1/generated-contents/{generated_content_id}
```

The content ID alone is enough for a detail or export link, but it is not enough to render the inline preview for task tests.

When a user starts handout or task-test generation, the frontend binds the loading state to the subtask that started the request. If the user switches to another subtask before the request finishes, the original request continues in the background and the new subtask does not inherit its spinner. The page shows a notice and blocks starting another generation until the in-flight request finishes.

`GeneratedContentDetailPage` uses a generic `返回` action. It calls browser history back when available, and only falls back to the course page or home page when there is no useful previous entry.

## Backend Root Cause

Handout generation failed with `GENERATION_SCHEMA_INVALID` after citation binding because `_bind_source_citation_ids()` treated every key named `source_citation_ids` as a semantic citation field.

That is correct for handout sections and citation-aware blocks, but invalid inside typed table `rows`. Table rows are plain cell dictionaries, so a column can legitimately be named `source_citation_ids` and contain a string or number value. Rewriting that cell to a list of source citation IDs violates the `HandoutContent` table row schema.

The fix suppresses semantic citation rebinding below table `rows`, preserving row cell values while still rebinding citation fields elsewhere.

## Verification

Commands run:

```text
frontend/node_modules/.bin/tsc -p frontend/tsconfig.app.json --noEmit
corepack pnpm@11.7.0 --dir frontend test --run tests/pages/generated-content-detail.test.tsx tests/pages/study-plan-pages.test.tsx
python -m pytest tests/modules/learning_execution/test_task_content_api.py -k "citation_binding or handout"
git diff --check
```

Regression tests:

- `backend/tests/modules/learning_execution/test_task_content_api.py::test_handout_citation_binding_does_not_rewrite_table_row_fields`
- `frontend/tests/pages/generated-content-detail.test.tsx`
- `frontend/tests/pages/study-plan-pages.test.tsx`
