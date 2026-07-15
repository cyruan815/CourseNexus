# Generation Topic Titles and Chinese Quiz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a concise Chinese topic for all five generated content types, show it after the canonical list label, and automatically retry Quiz generation when English questions are returned.

**Architecture:** Add a shared generator topic utility for the `topic_title` type and Chinese-character checks, then extend each model result schema and prompt. Every generator persists the model-produced topic as its title; Quiz performs one correction retry when the topic or any question text lacks Chinese. The frontend treats new titles as semantic topics while extracting or suppressing known legacy title formats.

**Tech Stack:** Python, FastAPI generator services, Pydantic v2, React 19, TypeScript, Vitest, pytest.

---

### Task 1: Shared topic-title contract

**Files:**
- Create: `backend/app/modules/generation/generators/topic.py`
- Create: `backend/tests/modules/generation/generators/test_topic.py`
- Modify: each of the five generator `schemas.py` files
- Modify: corresponding schema tests and model-output fixtures

- [ ] Write failing tests for trimmed topic titles and Chinese detection.
- [ ] Run `python -m pytest tests/modules/generation/generators/test_topic.py -q` and verify failure because the topic module is absent.
- [ ] Add `TopicTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]`, `contains_chinese(text)`, and `ensure_chinese_topic(text)` that raises `CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Generated topic title must be Chinese")`.
- [ ] Add required `topic_title: TopicTitle` to `QuizGenerationResult`, `FlashcardGenerationResult`, `MindmapGenerationResult`, `OutlineGenerationResult`, and `KnowledgeGenerationResult`.
- [ ] Update test model outputs to include `topic_title="第七章 物理层"` and run all five schema suites.

### Task 2: Persist Chinese topic titles for five generators

**Files:**
- Modify: all five generator `prompts.py` files
- Modify: all five generator `generator.py` files
- Modify: all five generator tests and API fixtures

- [ ] Add failing assertions that prompts require a concise Simplified Chinese `topic_title`, prohibit function names/counts/parentheses, and describe single-section versus multi-section aggregation.
- [ ] Add failing assertions that every `GeneratorOutput.title` equals the model result topic rather than a generic counted title.
- [ ] Update prompts with the approved topic rules.
- [ ] Call `ensure_chinese_topic(result.topic_title)` in flashcard, mindmap, outline, and knowledge-list generators; persist `title=result.topic_title` in all five generators.
- [ ] Run the five generator and API test groups and verify pass.

### Task 3: Chinese Quiz correction retry

**Files:**
- Modify: `backend/app/modules/generation/generators/quiz/generator.py`
- Modify: `backend/app/modules/generation/generators/quiz/prompts.py`
- Modify: `backend/tests/modules/generation/generators/quiz/test_quiz_generator.py`

- [ ] Write a failing test with queued outputs: first output has English `question_text`, second output is Chinese; assert two provider calls and successful Chinese content.
- [ ] Write a failing test where both outputs remain English; assert `CourseNexusError.code == "GENERATION_SCHEMA_INVALID"`.
- [ ] Add `quiz_result_is_chinese` checking `topic_title` and every `question_text` with `contains_chinese`.
- [ ] Generate once with the base prompt; when invalid, call the provider once more with an appended correction instruction requiring all user-visible text in Simplified Chinese while permitting formulas and professional abbreviations.
- [ ] Reject the second invalid result without persisting it and run the Quiz test group.

### Task 4: Frontend semantic title compatibility

**Files:**
- Modify: `frontend/src/features/course-workspace/generated-content-list.ts`
- Modify: `frontend/src/pages/CourseDetailPage.tsx`
- Modify: `frontend/src/pages/course-detail.css`
- Modify: `frontend/tests/features/course-workspace/generated-content-list.test.ts`
- Modify: `frontend/tests/pages/course-detail.test.tsx`

- [ ] Write failing tests for `generatedContentTitle(type, storedTitle)`: new Chinese topic, legacy `Knowledge Mindmap: 物理层`, generic counted English/Chinese titles, and semantic legacy suffixes.
- [ ] Implement legacy topic extraction and return `功能名 · 主题`; return only the function name when the legacy title carries no reliable topic.
- [ ] Pass `content.title` to the helper for persisted rows, leave pending rows canonical-only, and add the full combined title as the HTML `title` attribute.
- [ ] Add a single-line ellipsis class for long titles and run focused frontend tests.

### Task 5: Full verification and commit

**Files:**
- Verify all changed files only.

- [ ] Run the relevant backend generator suites with `python -m pytest`.
- [ ] Run the complete frontend suite with bundled Node: `pnpm exec vitest run`.
- [ ] Run `pnpm run build`.
- [ ] Run `git diff --check` and review that unrelated logs and `.superpowers/` are not staged.
- [ ] Commit implementation as `feat(generation): add Chinese topic titles`.
