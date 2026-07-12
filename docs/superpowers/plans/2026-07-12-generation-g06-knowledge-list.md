# G06 Knowledge List Backend Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. Do not dispatch subagents.

**Goal:** Generate a deduplicated, importance-ranked, cited knowledge list from all selected materials.

**Architecture:** Map every batch to strict grounded candidates, then locally merge normalized names, definitions and citations, take the highest supported importance, filter by minimum importance, assign stable IDs, and persist through G01.

## Tasks

1. Implement strict parameters, candidate/map, final item/content schemas and boundary tests.
2. Implement prompts, all-batch mapping, coverage, deduplication, importance filtering/order, count limit, citations and `build_generator`.
3. Test POST/history/detail, invalid parameters, empty filtered result and stable failures.
4. Document API, algorithm, complexity and boundaries; run focused, regression and full backend tests.
5. Integrate G02-G06 onto fixed `feature/generation`, run combined verification, then perform the single deferred remote update and PR handling.
