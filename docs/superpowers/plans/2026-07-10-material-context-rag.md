# CourseNexus RAG Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a no-Docker local material parsing, indexing, retrieval, and complete-coverage context infrastructure that later CourseNexus feature teams can consume without implementing Flashcard, Quiz, Mindmap, AI study-plan, or other learning business features in this phase.

**Architecture:** SQLite remains authoritative for `CourseMaterial` and `MaterialChunk`; an in-process Chroma `PersistentClient` stores a rebuildable vector index. Docling parses complex files, LlamaIndex owns embedding/index/retrieval integration, and `material-context` exposes separate relevant-retrieval and complete-material batch contracts. Infrastructure acceptance uses fake providers and reference consumers rather than production business modules.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite, Docling, LlamaIndex Core, LlamaIndex Chroma integration, LlamaIndex OpenAI embeddings, Chroma PersistentClient, OpenAI Responses API, Pydantic, pytest, Conda.

## Global Constraints

- Run in the existing `course-nexus` Conda environment; do not use Docker.
- Do not start Chroma Server or any separate RAG service; use `chromadb.PersistentClient` inside the FastAPI process.
- OpenAI API may provide embeddings and generic structured output; automated tests must not make live OpenAI calls.
- Keep SQLite `CourseMaterial` and `MaterialChunk` as authoritative data; Chroma is a rebuildable derived index.
- Third-party Docling, LlamaIndex, Chroma, and OpenAI types stay under `backend/app/integrations/`.
- Every retrieval filter includes `user_id` and `course_id`; selected material and folder ids are hard metadata filters.
- Expose `retrieve_relevant_context()` for query-dependent Top-K retrieval.
- Expose `iter_material_context_batches()` for complete selected-material coverage; never replace it with one Top-K query.
- Provide generic structured-provider and coverage-runner contracts, test doubles, reference-consumer tests, and an integration guide.
- Do not migrate production `course-qa`, `generation`, or `study_plans` services in this plan.
- Do not implement feature-specific prompts, schemas, endpoints, persistence flows, or frontend pages.
- Do not implement Flashcard, Quiz, Mindmap, Outline, Knowledge List, Handout, Task Test, or AI study-plan behavior.
- Implement every task test-first and commit it separately.

---

## File Structure

```text
backend/app/integrations/
├── parsers/
│   ├── docling_parser.py        # Docling conversion and structured chunk mapping
│   └── routing.py               # plain-text versus Docling parser selection
└── rag/
    ├── __init__.py
    ├── base.py                  # CourseNexus-owned RAG DTOs and protocol
    ├── fake.py                  # deterministic test double
    └── llama_index_chroma.py    # only LlamaIndex/Chroma implementation

backend/app/modules/material_context/
├── schemas.py                   # ContextChunk, result, batch, material scope
├── repository.py                # authoritative SQLite chunk queries
├── service.py                   # two public context APIs
└── coverage.py                  # generic material-coverage runner

backend/app/commands/
└── rebuild_rag_index.py         # rebuild derived Chroma data from SQLite

backend/tests/contracts/
└── test_material_context_consumers.py  # reference Q&A and generation consumers

docs/engineering/
└── rag-consumer-guide.md        # stable handoff for feature teams
```

Production business modules remain unchanged in this infrastructure plan. Reference consumers live in tests and documentation only.

### Task 1: Lock Local RAG Dependencies and Configuration

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`
- Modify: `.gitignore`
- Create: `backend/tests/core/test_rag_config.py`

**Interfaces:**
- Produces: local Chroma path, collection name, embedding model, Top-K, chunk token budget, and batch token budget settings.
- Produces: an ignored local persistence directory; no server URL or Docker configuration.

- [ ] **Step 1: Write the failing settings test**

```python
from app.core.config import Settings


def test_rag_settings_use_local_persistent_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.chroma_persist_path == "./data/chroma"
    assert settings.chroma_collection == "course_nexus_material_chunks"
    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.rag_similarity_top_k == 8
    assert settings.rag_chunk_max_tokens == 800
    assert settings.material_batch_max_tokens == 12_000
```

- [ ] **Step 2: Run the test and verify it fails**

Run from `backend/`:

```powershell
conda run -n course-nexus python -m pytest tests/core/test_rag_config.py -q
```

Expected: FAIL because `Settings` does not define `chroma_persist_path`.

- [ ] **Step 3: Add only the required production packages**

Add to `backend/pyproject.toml`:

```toml
"chromadb>=1.5.9,<2.0",
"docling>=2.111.0,<3.0",
"llama-index-core>=0.14.23,<0.15",
"llama-index-embeddings-openai>=0.6.0,<0.7",
"llama-index-vector-stores-chroma>=0.5.5,<0.6",
"tiktoken>=0.9,<1.0",
```

Do not add the broad `llama-index` starter package or `llama-index-llms-openai`.

- [ ] **Step 4: Add settings and local environment examples**

Add to `Settings`:

```python
chroma_persist_path: str = "./data/chroma"
chroma_collection: str = "course_nexus_material_chunks"
openai_embedding_model: str = "text-embedding-3-small"
rag_similarity_top_k: int = 8
rag_chunk_max_tokens: int = 800
material_batch_max_tokens: int = 12_000
```

Add corresponding uppercase entries to `.env.example`, and add `/data/chroma/` to `.gitignore`.

- [ ] **Step 5: Install dependencies and rerun the test**

```powershell
conda run -n course-nexus python -m pip install -e ".[dev]"
conda run -n course-nexus python -c "import chromadb, docling, llama_index.core; print('rag infrastructure imports ok')"
conda run -n course-nexus python -m pytest tests/core/test_rag_config.py -q
```

Expected: import command prints `rag infrastructure imports ok`; test passes.

- [ ] **Step 6: Commit**

```powershell
git add backend/pyproject.toml backend/app/core/config.py backend/tests/core/test_rag_config.py .env.example .gitignore
git commit -m "build(rag): 配置本地 RAG 基础依赖"
```

### Task 2: Accept Complex Course Files Safely

**Files:**
- Modify: `backend/app/integrations/file_storage/local.py`
- Modify: `backend/app/modules/materials/service.py`
- Modify: `backend/tests/integrations/test_local_file_storage.py`
- Modify: `backend/tests/modules/materials/test_materials_service.py`

**Interfaces:**
- Produces: upload acceptance for `.pdf`, `.docx`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.md`, and `.txt`.
- Preserves: filename traversal protection, size limits, and content-based format checks.

- [ ] **Step 1: Write failing binary-format tests**

```python
def test_storage_accepts_pdf_signature(tmp_path: Path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)
    saved = storage.save_file(
        user_id="usr_1",
        course_id="crs_1",
        material_id="mat_1",
        filename="slides.pdf",
        stream=BytesIO(b"%PDF-1.7\n%%EOF"),
        content_type="application/octet-stream",
    )
    assert saved.mime_type == "application/pdf"


def test_storage_rejects_fake_docx(tmp_path: Path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)
    with pytest.raises(CourseNexusError) as exc_info:
        storage.save_file(
            user_id="usr_1",
            course_id="crs_1",
            material_id="mat_1",
            filename="notes.docx",
            stream=BytesIO(b"not-a-zip"),
        )
    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"
```

Create valid DOCX and PPTX test streams with `zipfile.ZipFile`, using `word/document.xml` and `ppt/presentation.xml` members. Add PNG and JPEG magic-byte tests.

- [ ] **Step 2: Run focused tests and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_local_file_storage.py tests/modules/materials/test_materials_service.py -q
```

Expected: FAIL because current storage accepts only UTF-8 `.txt` and `.md`.

- [ ] **Step 3: Implement explicit format definitions and validation**

```python
SUPPORTED_FILE_TYPES = {
    ".md": ("text/markdown", "markdown"),
    ".txt": ("text/plain", "text"),
    ".pdf": ("application/pdf", "pdf"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "word"),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "ppt"),
    ".png": ("image/png", "image"),
    ".jpg": ("image/jpeg", "image"),
    ".jpeg": ("image/jpeg", "image"),
}
```

Validate text by UTF-8 decoding, PDF by `%PDF-`, PNG/JPEG by magic bytes, and Office files by ZIP structure. Update `_material_type_for_filename()` to use the same mapping.

- [ ] **Step 4: Run focused tests**

Run the Step 2 command.

Expected: all storage and material service tests pass; extension spoofing remains rejected.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/integrations/file_storage/local.py backend/app/modules/materials/service.py backend/tests/integrations/test_local_file_storage.py backend/tests/modules/materials/test_materials_service.py
git commit -m "feat(materials): 支持复杂资料安全上传"
```

### Task 3: Implement Docling Parsing Behind the Existing Parser Protocol

**Files:**
- Create: `backend/app/integrations/parsers/docling_parser.py`
- Create: `backend/app/integrations/parsers/routing.py`
- Modify: `backend/app/modules/materials/router.py`
- Create: `backend/tests/integrations/test_docling_parser.py`
- Create: `backend/tests/integrations/test_routing_parser.py`

**Interfaces:**
- Consumes: local file path and `rag_chunk_max_tokens`.
- Produces: existing `ParsedDocument` and ordered `ParsedChunk` values with heading/page metadata.

- [ ] **Step 1: Write failing Docling mapping tests**

```python
def test_docling_parser_maps_order_heading_and_page() -> None:
    converter = FakeConverter(document=FakeDoclingDocument())
    chunker = FakeChunker([
        FakeChunk(text="Eigenvectors", headings=["Week 2"], page_no=3),
        FakeChunk(text="Diagonalization", headings=["Week 2"], page_no=4),
    ])

    parsed = DoclingParser(converter=converter, chunker=chunker).parse(Path("slides.pdf"))

    assert [chunk.chunk_index for chunk in parsed.chunks] == [0, 1]
    assert parsed.chunks[0].heading == "Week 2"
    assert parsed.chunks[0].page == "3"
    assert parsed.chunks[0].page_index == 2
```

Add tests for empty conversion and exception mapping to `PARSE_FAILED`.

- [ ] **Step 2: Write the failing routing test**

```python
def test_routing_parser_selects_docling_for_pdf(tmp_path: Path) -> None:
    plain = RecordingParser("plain")
    docling = RecordingParser("docling")
    parser = RoutingParser(plain_text=plain, docling=docling)

    parser.parse(tmp_path / "slides.pdf")

    assert docling.called is True
    assert plain.called is False
```

- [ ] **Step 3: Run tests and verify imports fail**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_docling_parser.py tests/integrations/test_routing_parser.py -q
```

Expected: FAIL because neither adapter exists.

- [ ] **Step 4: Implement token-aware Docling chunking**

```python
tokenizer = OpenAITokenizer(
    tokenizer=tiktoken.get_encoding("cl100k_base"),
    max_tokens=max_tokens,
)
self.converter = converter or DocumentConverter()
self.chunker = chunker or HybridChunker(tokenizer=tokenizer, merge_peers=True)
```

Call `self.chunker.chunk(dl_doc=document)`, discard empty text, preserve order, and map the first provenance page to one-based `page` and zero-based `page_index`.

- [ ] **Step 5: Implement explicit extension routing**

```python
class RoutingParser:
    def parse(self, file_path: Path) -> ParsedDocument:
        suffix = file_path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return self.plain_text.parse(file_path)
        if suffix in {".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg"}:
            return self.docling.parse(file_path)
        raise CourseNexusError(code="UNSUPPORTED_FILE_TYPE", message="文件类型不支持", status_code=415)
```

Make `get_material_parser()` construct `RoutingParser` only when FastAPI resolves the dependency.

- [ ] **Step 6: Run parser and materials tests**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_docling_parser.py tests/integrations/test_routing_parser.py tests/integrations/test_plain_text_parser.py tests/modules/materials -q
```

Expected: all tests pass without OpenAI access.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/integrations/parsers backend/app/modules/materials/router.py backend/tests/integrations/test_docling_parser.py backend/tests/integrations/test_routing_parser.py
git commit -m "feat(materials): 接入 Docling 解析适配器"
```

### Task 4: Define the Internal RAG Contract and Test Double

**Files:**
- Create: `backend/app/integrations/rag/__init__.py`
- Create: `backend/app/integrations/rag/base.py`
- Create: `backend/app/integrations/rag/fake.py`
- Create: `backend/tests/integrations/test_fake_rag_index.py`

**Interfaces:**
- Produces: `RagChunk`, `RagScopeFilter`, `RetrievalHit`, and `RagIndex`.
- Produces: deterministic `FakeRagIndex` for service and consumer-contract tests.

- [ ] **Step 1: Write the failing contract behavior test**

```python
def test_fake_rag_index_filters_and_ranks() -> None:
    index = FakeRagIndex()
    index.index_chunks([
        RagChunk("c1", "u1", "math", "m1", None, 0, "matrix eigenvalue", "1", 0, "A"),
        RagChunk("c2", "u1", "history", "m2", None, 0, "industrial revolution", "1", 0, "B"),
    ])

    hits = index.retrieve(
        query="eigenvalue",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c1"]
```

Add tests for selected material ids, folder ids, user isolation, and `delete_material()`.

- [ ] **Step 2: Run and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_fake_rag_index.py -q
```

Expected: FAIL because the `rag` package does not exist.

- [ ] **Step 3: Implement CourseNexus-owned DTOs and protocol**

```python
@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    user_id: str
    course_id: str
    material_id: str
    folder_id: str | None
    chunk_index: int
    text: str
    page: str | None
    page_index: int | None
    heading: str | None


@dataclass(frozen=True)
class RagScopeFilter:
    user_id: str
    course_id: str
    material_ids: tuple[str, ...] = ()
    folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    score: float


class RagIndex(Protocol):
    def index_chunks(self, chunks: Sequence[RagChunk]) -> None: ...
    def delete_material(self, material_id: str) -> None: ...
    def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]: ...
```

The fake stores records in memory and ranks by deterministic token overlap. Add `FakeRagIndex.from_chunks(chunks: Sequence[RagChunk]) -> FakeRagIndex` as a convenience constructor used by later context tests. It must never be selected silently in a normal production dependency.

- [ ] **Step 4: Run tests and commit**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_fake_rag_index.py -q
git add backend/app/integrations/rag backend/tests/integrations/test_fake_rag_index.py
git commit -m "feat(rag): 定义索引契约和测试替身"
```

### Task 5: Implement LlamaIndex + Chroma Persistent Retrieval

**Files:**
- Create: `backend/app/integrations/rag/llama_index_chroma.py`
- Create: `backend/tests/integrations/test_llama_index_chroma.py`

**Interfaces:**
- Implements: `RagIndex`.
- Consumes: local persistence path, collection name, and injected embedding model.
- Produces: idempotent index/delete and metadata-filtered retrieval.

- [ ] **Step 1: Write failing persistence and isolation tests**

```python
def test_chroma_persists_and_filters_course(tmp_path: Path) -> None:
    first = LlamaIndexChromaRagIndex(
        persist_path=tmp_path,
        collection_name="test_chunks",
        embed_model=KeywordEmbedding(),
    )
    first.index_chunks([math_chunk(), history_chunk()])

    reopened = LlamaIndexChromaRagIndex(
        persist_path=tmp_path,
        collection_name="test_chunks",
        embed_model=KeywordEmbedding(),
    )
    hits = reopened.retrieve(
        query="matrix",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["math-c1"]
```

Use a deterministic `BaseEmbedding` implementation. Add material/folder filters, user isolation, repeat upsert, and delete tests.

- [ ] **Step 2: Run and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py -q
```

Expected: FAIL because `LlamaIndexChromaRagIndex` does not exist.

- [ ] **Step 3: Implement PersistentClient and ChromaVectorStore**

```python
client = chromadb.PersistentClient(path=str(persist_path))
collection = client.get_or_create_collection(collection_name)
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
```

Convert each `RagChunk` to `TextNode(id_=chunk.chunk_id, text=chunk.text, metadata=...)`. Mandatory filters are user and course equality; material/folder filters are additional inclusion filters. Return only internal `RetrievalHit` values.

- [ ] **Step 4: Map third-party errors**

Map embedding/upsert failures to `INDEXING_FAILED` and query failures to `RETRIEVAL_FAILED`, both with HTTP status 502. Raw third-party exceptions must not leave the adapter.

- [ ] **Step 5: Run the tests twice**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py -q
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py -q
```

Expected: both runs pass and use isolated temporary paths.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/integrations/rag/llama_index_chroma.py backend/tests/integrations/test_llama_index_chroma.py
git commit -m "feat(rag): 实现本地 Chroma 持久化检索"
```

### Task 6: Join Material Parsing and Indexing into One Lifecycle

**Files:**
- Modify: `backend/app/modules/materials/service.py`
- Modify: `backend/app/modules/materials/repository.py`
- Modify: `backend/app/modules/materials/router.py`
- Modify: `backend/tests/modules/materials/test_parse_material.py`
- Modify: `backend/tests/modules/materials/test_materials_service.py`

**Interfaces:**
- Changes: `parse_material(..., rag_index: RagIndex)`.
- Changes: `delete_material(..., rag_index: RagIndex)`.
- Produces: deterministic chunk ids and synchronized derived vector records.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_parse_indexes_every_saved_chunk(db, tmp_path) -> None:
    rag_index = FakeRagIndex()
    user, course, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parsed"
    assert {record.material_id for record in rag_index.records.values()} == {material.id}
    assert {record.course_id for record in rag_index.records.values()} == {course.id}
```

Add tests proving indexing failure records `INDEXING_FAILED`, reparse replaces old vectors, and delete removes vectors.

- [ ] **Step 2: Run material tests and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/modules/materials -q
```

Expected: FAIL because material services do not accept `rag_index`.

- [ ] **Step 3: Use deterministic chunk ids and complete metadata**

```python
def _chunk_id(material_id: str, chunk_index: int) -> str:
    return f"chk_{material_id.removeprefix('mat_')}_{chunk_index:06d}"
```

Map user, course, material, folder, order, page, page index, heading, and text into every `RagChunk`. Set `MaterialChunk.embedding_id = chunk.id` after successful index insertion.

- [ ] **Step 4: Implement state and compensation rules**

Use this exact order:

1. mark material `parsing`;
2. parse into memory;
3. replace SQLite chunks while status remains `parsing`;
4. delete previous vectors and index new chunks;
5. set embedding ids and mark `parsed`;
6. on index failure, delete partial vectors, clear SQLite chunks, and mark `parse_failed/INDEXING_FAILED`.

The production dependency requires an OpenAI API key for real embeddings. Tests override it with `FakeRagIndex`; do not silently fall back to fake indexing.

- [ ] **Step 5: Run material and adapter tests**

```powershell
conda run -n course-nexus python -m pytest tests/modules/materials tests/integrations/test_fake_rag_index.py tests/integrations/test_llama_index_chroma.py -q
```

Expected: all tests pass without network access.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/modules/materials backend/tests/modules/materials
git commit -m "feat(materials): 统一解析和索引生命周期"
```

### Task 7: Expose the Two Material Context APIs

**Files:**
- Modify: `backend/app/modules/material_context/schemas.py`
- Modify: `backend/app/modules/material_context/repository.py`
- Modify: `backend/app/modules/material_context/service.py`
- Create: `backend/tests/modules/material_context/test_retrieve_relevant_context.py`
- Create: `backend/tests/modules/material_context/test_material_context_batches.py`
- Modify: `backend/tests/modules/material_context/test_resolve_context.py`

**Interfaces:**
- Produces: `retrieve_relevant_context(..., rag_index, top_k) -> MaterialContextResult`.
- Produces: `iter_material_context_batches(..., max_tokens) -> Iterator[MaterialContextBatch]`.
- Temporarily preserves: current `resolve_context()` for existing consumers; this plan does not migrate them.

- [ ] **Step 1: Write failing relevant-retrieval tests**

```python
def test_relevant_context_preserves_hit_order_and_scope(db, seeded_materials) -> None:
    rag_index = FakeRagIndex.from_chunks(seeded_materials.rag_chunks)

    result = retrieve_relevant_context(
        db,
        user_id=seeded_materials.user.id,
        course_id=seeded_materials.course.id,
        query="eigenvalue",
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[seeded_materials.math_material.id],
        ),
        rag_index=rag_index,
        top_k=8,
    )

    assert [chunk.chunk_id for chunk in result.chunks] == [seeded_materials.eigen_chunk.id]
    assert result.chunks[0].score is not None
```

Add cross-user rejection, no-hit, and stale-vector-id tests.

- [ ] **Step 2: Write failing complete-batch tests**

```python
def test_batches_cover_every_selected_material(db, seeded_materials) -> None:
    batches = list(iter_material_context_batches(
        db,
        user_id=seeded_materials.user.id,
        course_id=seeded_materials.course.id,
        material_scope=MaterialScope(),
        max_tokens=20,
    ))

    flattened = [chunk for batch in batches for chunk in batch.chunks]
    assert {chunk.material_id for chunk in flattened} == {
        seeded_materials.first_material.id,
        seeded_materials.second_material.id,
    }
```

Extend `ContextChunk` with `chunk_index` and `score`; define `MaterialContextBatch(chunks, material_ids, estimated_tokens)`.

- [ ] **Step 3: Run and verify missing APIs**

```powershell
conda run -n course-nexus python -m pytest tests/modules/material_context -q
```

Expected: FAIL because the new functions and batch schema do not exist.

- [ ] **Step 4: Implement one shared scope validator**

Extract current ownership and eligible-material checks into `_resolve_scope()`. Relevant retrieval sends the resulting hard filter to `RagIndex`, then reloads authoritative SQLite chunks by hit ids while preserving hit order and score.

- [ ] **Step 5: Implement deterministic complete batching**

Load eligible chunks ordered by `material_id` and `chunk_index`. Estimate tokens with `max(1, len(content_text) // 4)`. Never split one `ContextChunk`; one oversized chunk forms its own batch. Raise `MATERIAL_COVERAGE_INCOMPLETE` if eligible material ids differ from represented material ids.

- [ ] **Step 6: Run context tests and commit**

```powershell
conda run -n course-nexus python -m pytest tests/modules/material_context -q
git add backend/app/modules/material_context backend/tests/modules/material_context
git commit -m "feat(context): 提供检索和全材料上下文接口"
```

### Task 8: Provide Generic Structured Output and Coverage Contracts

**Files:**
- Modify: `backend/app/integrations/model_provider/base.py`
- Modify: `backend/app/integrations/model_provider/openai.py`
- Modify: `backend/app/integrations/model_provider/mock.py`
- Create: `backend/app/modules/material_context/coverage.py`
- Create: `backend/tests/integrations/test_openai_structured_output.py`
- Create: `backend/tests/modules/material_context/test_coverage_runner.py`

**Interfaces:**
- Produces: `ModelProvider.generate_structured(prompt, output_schema) -> BaseModel`.
- Produces: `run_material_coverage(batches, expected_material_ids, map_batch, reduce_results)`.
- Does not produce: a Flashcard, Quiz, Mindmap, or study-plan schema.

- [ ] **Step 1: Write the failing generic structured-output test**

```python
class ReferenceExtraction(BaseModel):
    facts: list[str]
    citation_chunk_ids: list[str]


def test_openai_provider_returns_project_schema() -> None:
    parsed = ReferenceExtraction(facts=["A"], citation_chunk_ids=["c1"])
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeResponsesClient(parsed=parsed),
    )

    result = provider.generate_structured(
        prompt="reference extraction",
        output_schema=ReferenceExtraction,
    )

    assert result == parsed
```

Test SDK errors as `GENERATION_FAILED` and invalid parsed data as `GENERATION_SCHEMA_INVALID`.

- [ ] **Step 2: Write failing coverage-runner tests**

```python
def test_coverage_runner_rejects_missing_material() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        run_material_coverage(
            batches=[batch_for("m1")],
            expected_material_ids={"m1", "m2"},
            map_batch=lambda batch: mapped_reference(batch),
            reduce_results=lambda items: items,
        )

    assert exc_info.value.code == "MATERIAL_COVERAGE_INCOMPLETE"
```

Add tests for multiple batches, map failure, processed-material accounting, and citation-id union.

- [ ] **Step 3: Run and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_openai_structured_output.py tests/modules/material_context/test_coverage_runner.py -q
```

Expected: FAIL because the provider method and runner do not exist.

- [ ] **Step 4: Implement generic provider parsing**

Use the installed OpenAI SDK structured Responses API, pass a caller-provided Pydantic class, and return only the parsed Pydantic value. Do not add feature prompts or feature schemas.

- [ ] **Step 5: Implement coverage accounting**

The runner records every batch's `material_ids` before reduction. It raises `MATERIAL_COVERAGE_INCOMPLETE` when processed ids differ from expected ids, propagates stable generation errors, and returns a `CoverageRunResult(value, processed_material_ids, citation_chunk_ids)`.

- [ ] **Step 6: Run tests and commit**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_openai_model_provider.py tests/integrations/test_openai_structured_output.py tests/modules/material_context/test_coverage_runner.py -q
git add backend/app/integrations/model_provider backend/app/modules/material_context/coverage.py backend/tests/integrations/test_openai_structured_output.py backend/tests/modules/material_context/test_coverage_runner.py
git commit -m "feat(context): 提供结构化输出和材料覆盖契约"
```

### Task 9: Add Reference Consumers and the Feature-Team Integration Guide

**Files:**
- Create: `backend/tests/contracts/test_material_context_consumers.py`
- Create: `docs/engineering/rag-consumer-guide.md`
- Modify: `docs/engineering/index.md`

**Interfaces:**
- Demonstrates: a Q&A-style consumer of `retrieve_relevant_context()`.
- Demonstrates: a generation-style consumer of `iter_material_context_batches()` and `run_material_coverage()`.
- Documents: imports, ownership rules, errors, testing overrides, citation constraints, and forbidden direct dependencies.

- [ ] **Step 1: Write the reference Q&A consumer test**

Keep the reference consumer inside the contract test so it cannot become accidental production business code:

```python
def reference_question_consumer(db, *, user_id, course_id, question, scope, rag_index):
    context = retrieve_relevant_context(
        db,
        user_id=user_id,
        course_id=course_id,
        query=question,
        material_scope=scope,
        rag_index=rag_index,
        top_k=8,
    )
    return {
        "context": context,
        "allowed_citation_ids": {chunk.chunk_id for chunk in context.chunks},
    }


def test_reference_question_consumer_cannot_cite_outside_hits(db, seeded_materials) -> None:
    result = reference_question_consumer(...)
    assert "unselected-chunk" not in result["allowed_citation_ids"]
```

- [ ] **Step 2: Write the reference complete-material consumer test**

```python
def reference_generation_consumer(db, *, user_id, course_id, scope):
    batches = list(iter_material_context_batches(
        db,
        user_id=user_id,
        course_id=course_id,
        material_scope=scope,
        max_tokens=20,
    ))
    expected = {material_id for batch in batches for material_id in batch.material_ids}
    return run_material_coverage(
        batches=batches,
        expected_material_ids=expected,
        map_batch=reference_map,
        reduce_results=reference_reduce,
    )


def test_reference_generation_consumer_processes_all_materials(db, seeded_materials) -> None:
    result = reference_generation_consumer(...)
    assert result.processed_material_ids == {
        seeded_materials.first_material.id,
        seeded_materials.second_material.id,
    }
```

The reference map/reduce returns plain test DTOs; it must not define a product feature.

- [ ] **Step 3: Run contract tests**

```powershell
conda run -n course-nexus python -m pytest tests/contracts/test_material_context_consumers.py -q
```

Expected: PASS after Tasks 7 and 8; no production business module is imported or changed.

- [ ] **Step 4: Write the integration guide with exact call sequences**

The guide must include:

```text
问答类：业务权限 -> retrieve_relevant_context -> ModelProvider -> 限定引用 -> 业务保存
指定材料生成类：业务权限 -> iter_material_context_batches -> run_material_coverage
                   -> 功能自有 schema/prompt -> 业务保存
```

Document these rules explicitly:

- feature teams own prompts, output schemas, API endpoints, persistence, and UI;
- infrastructure owns parsing, indexing, filters, batching, coverage accounting, and test doubles;
- feature modules never import `docling`, `llama_index`, or `chromadb`;
- Q&A citations are a subset of retrieved ids;
- selected-material features must compare expected and processed material ids;
- tests override `RagIndex` and `ModelProvider` without live network calls.

- [ ] **Step 5: Verify docs and commit**

```powershell
git diff --check
git add backend/tests/contracts/test_material_context_consumers.py docs/engineering/rag-consumer-guide.md docs/engineering/index.md
git commit -m "docs(rag): 提供业务接入契约和参考验证"
```

### Task 10: Add Reindex Maintenance and Infrastructure End-to-End Proof

**Files:**
- Create: `backend/app/commands/__init__.py`
- Create: `backend/app/commands/rebuild_rag_index.py`
- Create: `backend/tests/commands/test_rebuild_rag_index.py`
- Create: `backend/tests/integration/test_rag_infrastructure_flow.py`
- Modify: `README.md`
- Modify: `docs/planning/current-state.md`
- Modify: `docs/planning/tech-debt-tracker.md`
- Modify: `docs/architecture/material-context-rag.md`

**Interfaces:**
- Produces CLI: `python -m app.commands.rebuild_rag_index --all` and `--material-id <id>`.
- Proves: upload/parse/index/retrieve and full-material batch/coverage contracts.
- Does not call: production `course-qa`, feature generators, or `study_plans`.

- [ ] **Step 1: Write the failing rebuild test**

```python
def test_rebuild_all_indexes_only_parsed_materials(db) -> None:
    rag_index = FakeRagIndex()
    seeded = seed_parsed_and_uploaded_materials(db)

    result = rebuild_all(db=db, rag_index=rag_index)

    assert result.material_count == 2
    assert result.chunk_count == len(seeded.parsed_chunks)
    assert set(rag_index.records) == {chunk.id for chunk in seeded.parsed_chunks}
```

Add tests for single-material rebuild, missing/deleted material, and skipping unparsed materials.

- [ ] **Step 2: Run and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/commands/test_rebuild_rag_index.py -q
```

Expected: FAIL because the command module does not exist.

- [ ] **Step 3: Implement safe collection rebuild**

The command reads parsed SQLite chunks, maps them to `RagChunk`, and upserts them. `--all` recreates only the configured CourseNexus collection; it must not delete SQLite, uploads, or unrelated Chroma collections. Print material/chunk counts and return a nonzero process status on failure.

- [ ] **Step 4: Add one infrastructure integration flow**

```text
create user/course/materials
-> parse and index with deterministic embedding
-> retrieve one scoped Top-K result
-> build complete batches for two selected materials
-> execute reference coverage runner
-> assert no cross-course result, complete material ids, and source chunk ids
```

Use real SQLite and temporary Chroma persistence with deterministic embeddings. Do not invoke OpenAI, course Q&A, feature generators, study plans, or frontend code.

- [ ] **Step 5: Run the full backend suite**

From repository root:

```powershell
pnpm backend:test
```

Expected: all backend tests pass without Docker or live OpenAI calls.

- [ ] **Step 6: Run migration and persistence smoke checks**

```powershell
pnpm backend:migrate
```

From `backend/`:

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py::test_chroma_persists_and_filters_course -q
```

Expected: migration succeeds; persistence test passes.

- [ ] **Step 7: Update implemented-status documentation**

Record exact supported formats, commands, error codes, test count, and any explicitly deferred image OCR behavior. Mark TD-011 and TD-012 closed only when their integration evidence passes. Keep TD-013 in the later business stage. Do not modify PRD files.

- [ ] **Step 8: Verify and commit**

```powershell
git diff --check
git add backend/app/commands backend/tests/commands backend/tests/integration/test_rag_infrastructure_flow.py README.md docs/planning/current-state.md docs/planning/tech-debt-tracker.md docs/architecture/material-context-rag.md
git commit -m "test(rag): 验证本地 RAG 基础设施闭环"
```

## Final Acceptance

- [ ] `pnpm backend:test` passes without Docker and without live OpenAI calls.
- [ ] FastAPI remains the only application service process; Chroma uses local `PersistentClient` storage.
- [ ] PDF, DOCX, PPTX, Markdown, and text produce ordered source-grounded chunks; image OCR is tested or explicitly deferred in status docs.
- [ ] Parse, reparse, delete, and rebuild operations do not leave stale retrievable vectors.
- [ ] `retrieve_relevant_context()` enforces user, course, and material scope and preserves retrieval scores/order.
- [ ] `iter_material_context_batches()` represents every selected parsed material in stable order.
- [ ] The generic coverage runner detects missing materials and exposes processed material and citation ids.
- [ ] Reference Q&A and selected-material consumers pass contract tests without becoming production business code.
- [ ] Feature-team integration documentation includes exact imports, call sequences, errors, citations, and test overrides.
- [ ] Production `course-qa`, feature generator, study-plan, and frontend behavior are unchanged by this plan.
- [ ] No Flashcard, Quiz, Mindmap, Outline, Knowledge List, Handout, Task Test, or AI study-plan implementation is added.
- [ ] Business modules do not import Docling, LlamaIndex, Chroma, or OpenAI SDK types.
- [ ] The derived Chroma index can be rebuilt from authoritative SQLite chunks.
- [ ] PRD files remain unchanged and RAGFlow remains a future option only.
