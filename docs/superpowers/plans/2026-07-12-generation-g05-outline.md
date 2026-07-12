# G05 Outline Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Do not dispatch subagents.

**Goal:** Implement a full-material, cited review outline generator with deterministic sections and ordering.

**Architecture:** Map every material batch to grounded section candidates, then locally deduplicate, merge citations, apply the requested organization and detail limit, assign stable section IDs, and return retained bindings through G01. Do not create study plans, tasks, hierarchy fields, or new persistence models.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, FastAPI, G01 contracts and material coverage.

---

## Task 1: Schemas

- Implement strict `OutlineParameters`, candidate/map schemas, final section/content schemas.
- Test organization/detail enums, section count 1..30, text bounds, non-empty citations, unknown fields, stable IDs/order, and absence of parent/level fields.
- Commit `feat(outline): 定义提纲参数与章节结构`.

## Task 2: Generator

- Map every batch with chunk metadata and `OutlineMapResult`.
- Merge normalized duplicate titles, complementary summaries/suggestions, and real citations.
- Order by source order, topic, or deterministic review path; enforce summary limits 300/800/2000.
- Assign `sec_001...`, numbered titles, continuous sort order, retained-only bindings, and add `build_generator`.
- Test all batches, three organizations, detail limits, deduplication, stable IDs, citations, limits, and empty failure.
- Commit `feat(outline): 实现全材料复习提纲生成`.

## Task 3: API, Docs, and Verification

- Test POST/history/detail, citations, invalid parameters without persistence, permissions, empty material, and stable failed records.
- Add `docs/domains/generated-content/outline.md`; update API/frontend contracts without adding plan/task behavior.
- Run focused, generation regression, complete backend, and `git diff --check`.
- Commit tests and docs separately.
- Keep local until preceding PRs merge, then rebase and publish through fixed `feature/generation` as an independent PR.
