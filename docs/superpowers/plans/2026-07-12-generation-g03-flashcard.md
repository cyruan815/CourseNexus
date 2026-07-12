# G03 Flashcard Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Do not dispatch subagents.

**Goal:** Replace the Flashcard placeholder with a full-material, validated, cited card generator.

**Architecture:** Map every material batch through the existing structured model provider, then deterministically validate, deduplicate, rank, limit, identify, and bind only retained cards. G01 remains responsible for persistence and citation ID allocation.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, FastAPI, G01 contracts and material coverage.

---

## Task 1: Schemas

- Create strict parameters and candidate/final card schemas.
- Test count 1..100, style enum, front/back bounds, tag normalization and maximum, non-empty citations, stable IDs/order, and fixed `mastery_status="unknown"`.
- Commit `feat(flashcard): 定义卡片参数与结构`.

## Task 2: Generator

- Build batch prompts containing chunk metadata and candidate budget `min(30,max(3,ceil(card_count/batch_count)+2))`.
- Map every batch with `FlashcardMapResult` and run material coverage.
- Filter fabricated citations, deduplicate normalized fronts, merge tags/citations, rank by focus/material support/source order, apply count, and assign `card_001...`.
- Add registry-discovered `build_generator`.
- Test all batches, styles, deduplication, limits, IDs, citations, and empty-result failure.
- Commit `feat(flashcard): 实现全材料记忆卡片生成`.

## Task 3: API and Docs

- Test POST/history/detail, citations, invalid parameters without persistence, and stable failed records.
- Add `docs/domains/generated-content/flashcard.md` and update API/frontend contracts.
- Run focused, generation regression, and complete backend suites plus `git diff --check`.
- Commit tests and docs separately.
- Keep local until preceding PRs merge; then rebase and publish as an independent fixed-branch PR.
