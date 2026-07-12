# G02 Quiz Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Do not dispatch subagents because the user explicitly prohibited them.

**Goal:** Replace the Quiz placeholder with a full-material, validated, cited course self-test generator.

**Architecture:** Each material batch is mapped once through `ModelProvider.generate_structured` into strict quiz candidates. Local Python validates question-type invariants, deduplicates and ranks candidates, balances requested types and difficulty, assigns stable IDs, and returns retained chunk bindings through G01 for atomic citation persistence.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, SQLAlchemy 2, pytest, G01 contracts, material-context coverage, existing `ModelProvider`.

---

## Task 1: Parameters and Schemas

**Files:**
- Create `backend/app/modules/generation/generators/quiz/schemas.py`
- Create `backend/tests/modules/generation/generators/quiz/test_quiz_schemas.py`

- [ ] Test strict parameters, defaults, duplicate type removal, empty types, count 1..50, focus length, four question types, option IDs, answer shapes, explanation, difficulty, and citations.
- [ ] Run the focused schema suite and verify RED.
- [ ] Implement `QuizParameters`, `QuizOption`, `QuizCandidate`, `QuizMapResult`, `QuizQuestion`, and `QuizContent` with `extra="forbid"` and model validators.
- [ ] Run focused tests and verify GREEN.
- [ ] Commit `feat(quiz): 定义自测参数与题型结构`.

## Task 2: Prompt and Full-Material Generator

**Files:**
- Create `backend/app/modules/generation/generators/quiz/prompts.py`
- Create `backend/app/modules/generation/generators/quiz/generator.py`
- Modify `backend/app/modules/generation/generators/quiz/__init__.py`
- Create `backend/tests/modules/generation/generators/quiz/test_quiz_generator.py`

- [ ] Test invalid parameters before model calls, one structured call per batch, chunk metadata in prompts, batch candidate budget, full material coverage, deduplication, stable `q_001...`, continuous order, requested type/difficulty filtering, count limit, retained-only bindings, and empty-result failure.
- [ ] Run generator tests and verify RED.
- [ ] Implement grounded prompt construction and `QuizMapResult` mapping for every batch.
- [ ] Implement deterministic reduce using normalized question text, requested type order, requested difficulty, focus occurrence, material support, and first source order.
- [ ] Build final `QuizContent`, verify every retained question has a real allowed chunk ID, and return `GeneratorOutput(content=None)`.
- [ ] Add `build_generator(model_provider)` for existing registry discovery.
- [ ] Run focused tests and verify GREEN.
- [ ] Commit `feat(quiz): 实现全材料课程自测生成`.

## Task 3: API and Failure Regression

**Files:**
- Create `backend/tests/modules/generation/generators/quiz/test_quiz_api.py`

- [ ] Test success POST, history, detail, citation ID resolution, 401, 404, 400, invalid parameters without persistence, provider failure, invalid schema, empty legal result, and repeated request IDs.
- [ ] Run Quiz API tests and fix only Quiz-owned defects.
- [ ] Run G01, generated-content, and material-context regression suites.
- [ ] Commit `test(quiz): 覆盖接口引用和失败路径`.

## Task 4: Documentation and Delivery

**Files:**
- Create `docs/domains/generated-content/quiz.md`
- Modify `docs/api-data/contracts.md`
- Modify `docs/api-data/frontend-integration.md`
- Update current-state/runtime-flow documents only where the implemented status is recorded.

- [ ] Document exact parameters, output, algorithms, complexity, model-call budget, citations, errors, and tested API behavior.
- [ ] Run Quiz tests, generation regressions, complete backend suite, `git diff --check`, and audit changed files.
- [ ] Commit `docs(quiz): 记录生成算法与接口契约`.
- [ ] Keep `work/g02-quiz` local while PR #4 is open. After PR #4 merges, rebase G02 onto latest `main`, fast-forward fixed `feature/generation`, verify again, push, and create an independent G02 PR.
