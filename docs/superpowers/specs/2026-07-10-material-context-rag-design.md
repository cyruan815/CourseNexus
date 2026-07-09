# CourseNexus Material Context and RAG Design

## Status

Approved infrastructure-only revision, documented 2026-07-10.

The selected approach is mode 1: CourseNexus owns material parsing, indexing, retrieval, context assembly, citations, and generation orchestration. RAGFlow is a future option only.

## Goals

- Embed real document parsing and RAG into the existing FastAPI modular monolith.
- Use FastAPI + LlamaIndex + Docling + Chroma + OpenAI API.
- Run all infrastructure locally without Docker or a separate Chroma / RAG server.
- Support two distinct business semantics: scoped RAG Q&A and selected-material generation.
- Preserve current CourseNexus ownership of users, courses, material scope, generated content, citations, and study plans.
- Deliver stable context APIs, provider contracts, test doubles, and reference consumers for later feature teams.
- Prove both context semantics without implementing downstream learning features.

## Non-Goals

- Global or cross-course retrieval.
- Agent-driven automatic material selection.
- Shared multi-user knowledge bases.
- Local LLM serving.
- RAGFlow deployment or integration.
- A production task queue in this phase.
- Production Flashcard, Quiz, Mindmap, Outline, Knowledge List, Handout, or Task Test generation.
- AI study-plan algorithms or changes to current study-plan behavior.
- Feature-specific prompts, Pydantic output schemas, API endpoints, persistence flows, or frontend pages.
- Migrating existing `course-qa`, generator, or `study-plans` services to the new contracts in this infrastructure phase.

## Chosen Architecture

Docling parses local files and emits ordered, source-grounded chunks. LlamaIndex converts project chunks into nodes, calls OpenAI embeddings, writes them through a Chroma vector-store integration, and performs filtered retrieval. Chroma runs through `PersistentClient` inside the FastAPI Python process and stores its files under a configured local path.

SQLite remains authoritative for `CourseMaterial` and `MaterialChunk`; Chroma is a rebuildable derivative index. Third-party types stay inside `app/integrations/`. Business services consume project-owned DTOs such as `ContextChunk` and do not import Docling, LlamaIndex, Chroma, or OpenAI.

```mermaid
flowchart LR
    UP["Upload"] --> MAT["materials"]
    MAT --> DOC["Docling parser"]
    DOC --> SQL[("SQLite MaterialChunk")]
    SQL --> LI["LlamaIndex RAG adapter"]
    LI --> CH[("Chroma PersistentClient")]
    LI --> EMB["OpenAI Embeddings"]

    QA["course-qa"] --> RET["retrieve_relevant_context"]
    RET --> LI
    GEN["generators / study-plans"] --> ALL["iter_material_context_batches"]
    ALL --> SQL
```

## Two Context Contracts

### Scoped RAG Q&A

`retrieve_relevant_context(query, material_scope, top_k)` validates user and course ownership, converts the scope to Chroma metadata filters, performs semantic retrieval, and returns authoritative SQLite-backed `ContextChunk` values. Filters always include `user_id` and `course_id`, plus selected material or folder ids.

The answer provider receives only retrieved chunks. A citation is valid only when its chunk id belongs to that result set. Empty scope or no reliable hit produces `answer_type = no_source`.

### Selected-Material Generation

`iter_material_context_batches(material_scope, max_tokens)` loads every eligible selected chunk from SQLite in stable material and chunk order. It never substitutes a Top-K query for complete material coverage.

The infrastructure stage returns complete, ordered batches and provides a generic coverage runner that records processed material and source chunk ids. A reference consumer demonstrates map/reduce control flow, but it does not define a product feature schema or call a production feature prompt. Every selected parsed material must enter at least one batch; a partial batch failure fails the reference run rather than presenting an incomplete result as full coverage.

Future Flashcard, Quiz, Mindmap, Outline, Knowledge List, Handout, and Task Test teams will consume this contract and persist to `AIGeneratedContent` plus `SourceCitation`. A future study-plan generation task will consume the same coverage contract and persist to `StudyPlan`, `StudyTask`, and `StudySubTask`. Those consumers are explicitly outside the current implementation scope.

## Ingestion and Consistency

1. Mark the material `parsing`.
2. Parse with Docling and build ordered chunks with deterministic ids.
3. Replace SQLite `MaterialChunk` records.
4. Delete previous Chroma records for the material, embed, and upsert the new nodes.
5. Mark the material `parsed` only after both stores succeed.

On indexing failure, remove partial new vector records, record `INDEXING_FAILED`, and leave the material unavailable. Reparse and delete operations remove old records by `material_id`. A rebuild command can recreate the Chroma collection from SQLite.

## Local Runtime

- Python 3.12 in the existing `course-nexus` Conda environment.
- No Docker.
- No Chroma server process or port.
- `CHROMA_PERSIST_PATH=./data/chroma` for local vector files.
- OpenAI API for embeddings and structured generation.
- Unit tests use temporary Chroma paths, fake embeddings, fake retrieval, and the existing mock model provider.

## Error Handling

- `PARSING_FAILED`: Docling cannot parse a supported input.
- `INDEXING_FAILED`: embedding or Chroma upsert fails.
- `RETRIEVAL_FAILED`: the local vector index cannot be queried.
- `NO_PARSED_MATERIAL`: selected scope has no eligible material.
- `GENERATION_SCHEMA_INVALID`: model output cannot be repaired into the required schema.
- `GENERATION_FAILED`: a batch or model request fails for another reason.

Errors remain stable CourseNexus errors; raw third-party exceptions do not cross integration boundaries.

## Acceptance Criteria

- PDF, DOCX, PPTX, Markdown, and text fixtures produce ordered chunks with useful source metadata.
- Chroma persists across client recreation and enforces user, course, and material filters.
- A reference Q&A consumer receives query-dependent Top-K results and cannot cite chunks outside those results.
- A reference selected-material consumer records coverage of every selected material, including when input spans multiple batches.
- Deletion and reparse remove stale vector hits.
- Business modules contain no third-party RAG imports.
- The complete test suite runs without Docker and without live OpenAI calls.
- No production learning-feature generator, AI study-plan algorithm, or feature UI is added by this plan.

## Formal Documentation

- [AI material business](../../product/ai-material-business.md)
- [Material context and RAG architecture](../../architecture/material-context-rag.md)
- [ADR 0003](../../architecture/adr/0003-local-rag-stack.md)
