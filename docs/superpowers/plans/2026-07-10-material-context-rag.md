# CourseNexus Local Material Context and RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed a no-Docker, locally persisted Docling + LlamaIndex + Chroma RAG pipeline into the existing FastAPI monolith, with filtered Top-K retrieval for course Q&A and complete selected-material coverage for learning-content and study-plan generation.

**Architecture:** SQLite remains authoritative for materials and chunks, while an in-process Chroma `PersistentClient` stores a rebuildable vector index. Docling parses and structurally chunks complex documents; a LlamaIndex adapter owns embedding, indexing, and retrieval. Business modules consume only CourseNexus DTOs through `material-context`, using separate contracts for relevant retrieval and complete material batches.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite, Docling, LlamaIndex Core, LlamaIndex Chroma integration, LlamaIndex OpenAI embeddings, Chroma PersistentClient, OpenAI Responses API, Pydantic, pytest, Conda.

## Global Constraints

- Run in the existing `course-nexus` Conda environment; do not use Docker.
- Do not start Chroma Server or any separate RAG service; use `chromadb.PersistentClient` in the FastAPI process.
- Use OpenAI API for embeddings and generation; unit and integration tests must not make live OpenAI calls.
- Keep `CourseMaterial` and `MaterialChunk` in SQLite as authoritative data; Chroma is a rebuildable derived index.
- Keep Docling, LlamaIndex, Chroma, and OpenAI types inside `backend/app/integrations/`; business modules use CourseNexus-owned DTOs.
- Every retrieval filter includes `user_id` and `course_id`; selected material and folder ids are hard metadata filters.
- Q&A uses query-dependent Top-K retrieval; selected-material generation never substitutes one Top-K query for complete material coverage.
- Every selected parsed material must enter at least one generation batch, or the whole generation fails.
- Mark a material `parsed` only after both SQLite chunks and Chroma records are ready.
- Preserve stable CourseNexus errors and real `MaterialChunk` citation ids.
- Implement each task test-first and commit it separately using the commit message shown in that task.

---

## File Structure

New integration files:

```text
backend/app/integrations/
├── parsers/
│   ├── docling_parser.py        # Docling conversion and HybridChunker mapping
│   └── routing.py               # extension-based plain-text/Docling selection
└── rag/
    ├── __init__.py
    ├── base.py                  # CourseNexus RAG DTOs and protocol
    ├── fake.py                  # deterministic tests and local no-key behavior
    └── llama_index_chroma.py    # only LlamaIndex/Chroma embedding implementation
```

New generation files:

```text
backend/app/modules/generation/
├── coverage.py                  # shared map/reduce coverage runner
└── generators/
    ├── schemas.py               # typed final output models
    └── structured.py            # OpenAI-backed feature generators
```

New maintenance files:

```text
backend/app/commands/
├── __init__.py
└── rebuild_rag_index.py         # local Chroma rebuild command
```

Existing ownership remains unchanged: `materials` coordinates parse/index state, `material_context` supplies context, `course_qa` owns conversations, `generation` owns generated learning content, and `study_plans` owns plan/task persistence.

### Task 1: Lock Local RAG Dependencies and Configuration

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`
- Modify: `.gitignore`
- Create: `backend/tests/core/test_rag_config.py`

**Interfaces:**
- Produces: `Settings.chroma_persist_path`, `chroma_collection`, `openai_embedding_model`, `rag_similarity_top_k`, `rag_chunk_max_tokens`, and `generation_context_max_tokens`.
- Produces: a local ignored `data/chroma/` persistence location.

- [ ] **Step 1: Write the failing configuration test**

```python
from app.core.config import Settings


def test_rag_settings_have_no_docker_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.chroma_persist_path == "./data/chroma"
    assert settings.chroma_collection == "course_nexus_material_chunks"
    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.rag_similarity_top_k == 8
    assert settings.rag_chunk_max_tokens == 800
    assert settings.generation_context_max_tokens == 12_000
```

- [ ] **Step 2: Run the test and verify the missing settings fail**

Run from `backend/`:

```powershell
conda run -n course-nexus python -m pytest tests/core/test_rag_config.py -q
```

Expected: FAIL with an `AttributeError` for `chroma_persist_path`.

- [ ] **Step 3: Add narrowly scoped dependencies**

Add these production dependencies to `backend/pyproject.toml`:

```toml
"chromadb>=1.5.9,<2.0",
"docling>=2.111.0,<3.0",
"llama-index-core>=0.14.23,<0.15",
"llama-index-embeddings-openai>=0.6.0,<0.7",
"llama-index-vector-stores-chroma>=0.5.5,<0.6",
"tiktoken>=0.9,<1.0",
```

Do not add the broad `llama-index` starter package or `llama-index-llms-openai`; generation continues through the existing OpenAI provider.

- [ ] **Step 4: Add settings and environment examples**

Add to `Settings`:

```python
chroma_persist_path: str = "./data/chroma"
chroma_collection: str = "course_nexus_material_chunks"
openai_embedding_model: str = "text-embedding-3-small"
rag_similarity_top_k: int = 8
rag_chunk_max_tokens: int = 800
generation_context_max_tokens: int = 12_000
```

Add matching uppercase keys to `.env.example`, and add `/data/chroma/` to `.gitignore`.

- [ ] **Step 5: Install and verify imports in the Conda environment**

Run from `backend/`:

```powershell
conda run -n course-nexus python -m pip install -e ".[dev]"
conda run -n course-nexus python -c "import chromadb, docling, llama_index.core; print('rag dependencies ok')"
conda run -n course-nexus python -m pytest tests/core/test_rag_config.py -q
```

Expected: import command prints `rag dependencies ok`; test passes.

- [ ] **Step 6: Commit**

```powershell
git add backend/pyproject.toml backend/app/core/config.py backend/tests/core/test_rag_config.py .env.example .gitignore
git commit -m "build(rag): 配置本地 RAG 依赖和运行参数"
```

### Task 2: Accept Complex Course Material Files Safely

**Files:**
- Modify: `backend/app/integrations/file_storage/local.py`
- Modify: `backend/app/modules/materials/service.py`
- Modify: `backend/tests/integrations/test_local_file_storage.py`
- Modify: `backend/tests/modules/materials/test_materials_service.py`

**Interfaces:**
- Produces: upload support for `.pdf`, `.docx`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.md`, and `.txt`.
- Preserves: file-size limit, filename traversal protection, and content-based validation.

- [ ] **Step 1: Add failing binary validation tests**

Use minimal signatures and ZIP members rather than trusting request `Content-Type`:

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

Add a DOCX ZIP fixture in the test with `zipfile.ZipFile` and member `word/document.xml`; add the equivalent PPTX member `ppt/presentation.xml`.

- [ ] **Step 2: Run focused tests and verify failure**

Run from `backend/`:

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_local_file_storage.py tests/modules/materials/test_materials_service.py -q
```

Expected: FAIL because only UTF-8 `.txt` and `.md` are accepted.

- [ ] **Step 3: Implement extension-to-type and signature validation**

Add a format table shared by the storage implementation:

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

Validate text with UTF-8 decoding, PDF with `%PDF-`, PNG/JPEG with their magic bytes, and DOCX/PPTX with `zipfile.is_zipfile()` plus the required member. Update `_material_type_for_filename()` to use the same supported extension semantics.

- [ ] **Step 4: Run focused tests**

Run the Step 2 command.

Expected: all storage and material upload tests pass, including fake-extension rejection.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/integrations/file_storage/local.py backend/app/modules/materials/service.py backend/tests/integrations/test_local_file_storage.py backend/tests/modules/materials/test_materials_service.py
git commit -m "feat(materials): 支持复杂课程资料安全上传"
```

### Task 3: Implement the Docling Parser Adapter

**Files:**
- Create: `backend/app/integrations/parsers/docling_parser.py`
- Create: `backend/app/integrations/parsers/routing.py`
- Modify: `backend/app/integrations/parsers/base.py`
- Modify: `backend/app/modules/materials/router.py`
- Create: `backend/tests/integrations/test_docling_parser.py`

**Interfaces:**
- Consumes: local `Path`, `rag_chunk_max_tokens`.
- Produces: existing `ParsedDocument(chunks: list[ParsedChunk])` with stable order, heading, page, and page index.

- [ ] **Step 1: Write failing adapter tests using an injected converter**

Keep unit tests fast by injecting a fake Docling converter and chunker while asserting the mapping contract:

```python
def test_docling_parser_maps_chunk_text_and_grounding() -> None:
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
    assert parsed.chunks[1].content_text == "Diagonalization"
```

Also test empty conversion maps to `CourseNexusError(code="PARSE_FAILED")` and converter exceptions do not leak raw Docling exceptions.

- [ ] **Step 2: Run and verify import failure**

Run from `backend/`:

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_docling_parser.py -q
```

Expected: FAIL because `DoclingParser` does not exist.

- [ ] **Step 3: Implement Docling conversion and HybridChunker mapping**

Core implementation shape:

```python
class DoclingParser:
    def __init__(self, *, max_tokens: int = 800, converter=None, chunker=None) -> None:
        tokenizer = OpenAITokenizer(
            tokenizer=tiktoken.get_encoding("cl100k_base"),
            max_tokens=max_tokens,
        )
        self.converter = converter or DocumentConverter()
        self.chunker = chunker or HybridChunker(tokenizer=tokenizer, merge_peers=True)

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            document = self.converter.convert(file_path).document
            chunks = [
                self._map_chunk(index, chunk)
                for index, chunk in enumerate(self.chunker.chunk(dl_doc=document))
            ]
        except Exception as exc:
            raise CourseNexusError(code="PARSE_FAILED", message="文档解析失败", status_code=422) from exc
        chunks = [chunk for chunk in chunks if chunk.content_text.strip()]
        if not chunks:
            raise CourseNexusError(code="PARSE_FAILED", message="文档没有可解析内容", status_code=422)
        return ParsedDocument(chunks=chunks)
```

Derive page data from Docling provenance. Use the first page for a chunk spanning multiple source items, and join heading labels with ` / `.

- [ ] **Step 4: Select parser by extension in one routing adapter**

Implement a `RoutingParser` that still satisfies the existing `Parser` protocol and chooses from `file_path.suffix`:

```python
class RoutingParser:
    def __init__(self, *, plain_text: Parser, docling: Parser) -> None:
        self.plain_text = plain_text
        self.docling = docling

    def parse(self, file_path: Path) -> ParsedDocument:
        if file_path.suffix.lower() in {".txt", ".md"}:
            return self.plain_text.parse(file_path)
        if file_path.suffix.lower() in {".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg"}:
            return self.docling.parse(file_path)
        raise CourseNexusError(code="UNSUPPORTED_FILE_TYPE", message="文件类型不支持", status_code=415)
```

Make `get_material_parser()` return `RoutingParser(plain_text=PlainTextParser(), docling=DoclingParser(max_tokens=settings.rag_chunk_max_tokens))`. Construct it only when FastAPI resolves the dependency, not during module import.

- [ ] **Step 5: Run focused parser tests and current material tests**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_docling_parser.py tests/integrations/test_plain_text_parser.py tests/modules/materials -q
```

Expected: all tests pass without OpenAI access.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/integrations/parsers backend/app/modules/materials/router.py backend/tests/integrations/test_docling_parser.py
git commit -m "feat(materials): 接入 Docling 文档解析器"
```

### Task 4: Define the Internal RAG Protocol and Deterministic Fake

**Files:**
- Create: `backend/app/integrations/rag/__init__.py`
- Create: `backend/app/integrations/rag/base.py`
- Create: `backend/app/integrations/rag/fake.py`
- Create: `backend/tests/integrations/test_fake_rag_index.py`

**Interfaces:**
- Produces: `RagChunk`, `RagScopeFilter`, `RetrievalHit`, and `RagIndex`.
- Produces: `FakeRagIndex` for all business tests without Chroma or OpenAI.

- [ ] **Step 1: Write the protocol behavior tests**

```python
def test_fake_rag_index_filters_and_ranks_query_terms() -> None:
    index = FakeRagIndex()
    index.index_chunks([
        RagChunk(chunk_id="c1", user_id="u1", course_id="math", material_id="m1", folder_id=None,
                 chunk_index=0, text="matrix eigenvalue", page="1", page_index=0, heading="A"),
        RagChunk(chunk_id="c2", user_id="u1", course_id="history", material_id="m2", folder_id=None,
                 chunk_index=0, text="industrial revolution", page="1", page_index=0, heading="B"),
    ])

    hits = index.retrieve(
        query="eigenvalue",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c1"]
```

Also test `delete_material("m1")` and material-id filtering.

- [ ] **Step 2: Run and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_fake_rag_index.py -q
```

Expected: FAIL because the `rag` package does not exist.

- [ ] **Step 3: Implement project-owned immutable DTOs and protocol**

```python
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

The fake keeps records in a dictionary and ranks by deterministic token overlap. It is a test double, not the production retrieval algorithm.

- [ ] **Step 4: Run tests and commit**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_fake_rag_index.py -q
git add backend/app/integrations/rag backend/tests/integrations/test_fake_rag_index.py
git commit -m "feat(rag): 定义内部索引协议和测试替身"
```

### Task 5: Implement LlamaIndex + Chroma Persistent Index

**Files:**
- Create: `backend/app/integrations/rag/llama_index_chroma.py`
- Create: `backend/tests/integrations/test_llama_index_chroma.py`

**Interfaces:**
- Implements: `RagIndex`.
- Consumes: `persist_path`, `collection_name`, OpenAI-compatible embedding object.
- Produces: idempotent upsert/delete and filtered semantic retrieval without exposing third-party nodes.

- [ ] **Step 1: Write Chroma persistence and filter tests with a deterministic embedding**

Use a small `BaseEmbedding` test implementation that maps known words to fixed vectors; do not call OpenAI.

```python
def test_chroma_index_persists_and_filters_by_course(tmp_path: Path) -> None:
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

Add tests for `$in` material filters, folder filters, user isolation, re-upsert without duplicate ids, and `delete_material()`.

- [ ] **Step 2: Run and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py -q
```

Expected: FAIL because `LlamaIndexChromaRagIndex` does not exist.

- [ ] **Step 3: Implement PersistentClient, ChromaVectorStore, and metadata mapping**

Initialization shape:

```python
client = chromadb.PersistentClient(path=str(persist_path))
collection = client.get_or_create_collection(collection_name)
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
```

Convert each `RagChunk` to a LlamaIndex `TextNode(id_=chunk.chunk_id, text=chunk.text, metadata=...)`. Use `VectorStoreIndex(nodes, storage_context=..., embed_model=...)` for upsert. Build metadata filters with mandatory user/course equality and optional material/folder inclusion filters. Convert retrieval results back to `RetrievalHit` only.

- [ ] **Step 4: Map third-party failures to stable errors**

Wrap embedding/upsert failures as `CourseNexusError(code="INDEXING_FAILED", status_code=502)` and query failures as `CourseNexusError(code="RETRIEVAL_FAILED", status_code=502)`. Do not catch `CourseNexusError` and remap it again.

- [ ] **Step 5: Run tests twice to catch persistence leakage**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py -q
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py -q
```

Expected: both runs pass; each test uses its own `tmp_path` collection.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/integrations/rag/llama_index_chroma.py backend/tests/integrations/test_llama_index_chroma.py
git commit -m "feat(rag): 实现本地 Chroma 持久化索引"
```

### Task 6: Make Material Parsing and Indexing One Usable Lifecycle

**Files:**
- Modify: `backend/app/modules/materials/service.py`
- Modify: `backend/app/modules/materials/repository.py`
- Modify: `backend/app/modules/materials/router.py`
- Modify: `backend/tests/modules/materials/test_parse_material.py`
- Modify: `backend/tests/modules/materials/test_materials_service.py`

**Interfaces:**
- Changes: `parse_material(..., rag_index: RagIndex)`.
- Changes: `delete_material(..., rag_index: RagIndex)`.
- Produces: deterministic `MaterialChunk.id` values and Chroma records for every parsed chunk.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_parse_material_indexes_all_saved_chunks(db, tmp_path) -> None:
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
    assert {item.material_id for item in rag_index.records.values()} == {material.id}
    assert {item.course_id for item in rag_index.records.values()} == {course.id}
```

Add tests proving indexing failure sets `parse_failed/INDEXING_FAILED`, reparse replaces old vector records, and delete removes vector records.

- [ ] **Step 2: Run material tests and verify signature failures**

```powershell
conda run -n course-nexus python -m pytest tests/modules/materials -q
```

Expected: FAIL because services do not accept `rag_index` and do not write vectors.

- [ ] **Step 3: Create deterministic chunk ids and RagChunk mapping**

Use the current material id and chunk index:

```python
def _chunk_id(material_id: str, chunk_index: int) -> str:
    return f"chk_{material_id.removeprefix('mat_')}_{chunk_index:06d}"
```

Map every saved chunk with user, course, material, folder, order, page, heading, and text metadata. Assign `MaterialChunk.embedding_id = chunk.id` after a successful index upsert.

- [ ] **Step 4: Implement compensation and state rules**

The service sequence is:

1. mark `parsing`;
2. parse into memory;
3. replace SQLite chunks while material remains `parsing`;
4. delete existing material vectors and index new chunks;
5. set `embedding_id`, then mark `parsed`;
6. on indexing failure, delete partial new vectors, clear SQLite chunks, and set `parse_failed/INDEXING_FAILED`.

Update router dependencies to construct `LlamaIndexChromaRagIndex` when `OPENAI_API_KEY` exists and a `FakeRagIndex` only under explicit test dependency override. Do not silently use fake retrieval in normal local runtime.

- [ ] **Step 5: Run material and integration tests**

```powershell
conda run -n course-nexus python -m pytest tests/modules/materials tests/integrations/test_fake_rag_index.py tests/integrations/test_llama_index_chroma.py -q
```

Expected: all pass; no live network calls.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/modules/materials backend/tests/modules/materials
git commit -m "feat(materials): 统一资料解析和向量索引生命周期"
```

### Task 7: Split Material Context into Retrieval and Complete-Coverage APIs

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
- Temporarily preserves: `resolve_context()` as a deprecated ordered-read compatibility function.

- [ ] **Step 1: Write failing filtered retrieval tests**

```python
def test_relevant_context_uses_query_hits_and_scope(db, seeded_materials) -> None:
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
    assert all(chunk.material_id == seeded_materials.math_material.id for chunk in result.chunks)
```

Also test cross-user material ids return `NOT_FOUND`, missing Chroma ids are ignored, and no hits returns `no_parsed_material=True`.

- [ ] **Step 2: Write failing complete-coverage batch tests**

```python
def test_batches_cover_every_selected_material_in_order(db, seeded_materials) -> None:
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
    assert [(chunk.material_id, chunk.chunk_index) for chunk in flattened] == sorted(
        (chunk.material_id, chunk.chunk_index) for chunk in flattened
    )
```

Extend `ContextChunk` with `chunk_index` and `score: float | None`; define `MaterialContextBatch(chunks, material_ids, estimated_tokens)`.

- [ ] **Step 3: Run and verify missing APIs**

```powershell
conda run -n course-nexus python -m pytest tests/modules/material_context -q
```

Expected: FAIL because the two APIs and batch schema do not exist.

- [ ] **Step 4: Implement one shared scope validator**

Extract current owner/material validation into a private `resolve_scope_filter()` that returns eligible material ids and folder ids. Both public APIs must call it. `retrieve_relevant_context()` sends that filter to `RagIndex`, then fetches authoritative SQLite chunks by hit ids while preserving hit order and score.

- [ ] **Step 5: Implement ordered batching**

Query all eligible chunks ordered by material id and `chunk_index`. Estimate tokens with `max(1, len(text) // 4)` for deterministic local batching. Never split a `ContextChunk`; a single oversized chunk forms its own batch. Assert after batching that the set of eligible material ids equals the set represented by batches, otherwise raise `CourseNexusError(code="MATERIAL_COVERAGE_INCOMPLETE")`.

- [ ] **Step 6: Run all material-context tests and commit**

```powershell
conda run -n course-nexus python -m pytest tests/modules/material_context -q
git add backend/app/modules/material_context backend/tests/modules/material_context
git commit -m "feat(context): 分离问答检索和全材料上下文"
```

### Task 8: Migrate Course Q&A to Filtered Semantic Retrieval

**Files:**
- Modify: `backend/app/modules/course_qa/service.py`
- Modify: `backend/app/modules/course_qa/router.py`
- Modify: `backend/tests/modules/course_qa/test_course_qa_service.py`
- Modify: `backend/tests/modules/course_qa/test_course_qa_api.py`
- Modify: `backend/tests/integration/test_course_workspace_flow.py`

**Interfaces:**
- Changes: `ask_course_question(..., model_provider, rag_index, top_k)`.
- Consumes: `retrieve_relevant_context(query=payload.question, material_scope=...)`.
- Preserves: conversations, answer types, message persistence, and `SourceCitation` schema.

- [ ] **Step 1: Add a query-dependent service test**

```python
def test_question_passes_only_retrieved_chunks_to_model(db, seeded_course) -> None:
    rag_index = FakeRagIndex.from_chunks(seeded_course.rag_chunks)
    provider = RecordingModelProvider()

    ask_course_question(
        db,
        user_id=seeded_course.user.id,
        course_id=seeded_course.course.id,
        payload=CourseQuestionCreate(question="What is Beta?", material_scope=MaterialScope()),
        model_provider=provider,
        rag_index=rag_index,
        top_k=8,
    )

    assert [chunk.content_text for chunk in provider.received_chunks] == ["Beta definition"]
```

Add a test that provider citation ids outside the retrieved set are discarded and no-source creates no citation.

- [ ] **Step 2: Run Q&A tests and verify signature failure**

```powershell
conda run -n course-nexus python -m pytest tests/modules/course_qa -q
```

Expected: FAIL because Q&A still calls `resolve_context()`.

- [ ] **Step 3: Inject the RAG index and call relevant retrieval**

Update the service call:

```python
context = retrieve_relevant_context(
    db,
    user_id=user_id,
    course_id=course_id,
    query=payload.question,
    material_scope=payload.material_scope,
    rag_index=rag_index,
    top_k=top_k,
)
```

Move the shared production `get_rag_index()` FastAPI dependency to `app/api/dependencies.py` so materials and Q&A use the same configured Chroma path and embedding model factory.

- [ ] **Step 4: Verify service, API, and workspace flow**

```powershell
conda run -n course-nexus python -m pytest tests/modules/course_qa tests/integration/test_course_workspace_flow.py -q
```

Expected: all pass with dependency overrides using `FakeRagIndex`.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/dependencies.py backend/app/modules/course_qa backend/tests/modules/course_qa backend/tests/integration/test_course_workspace_flow.py
git commit -m "feat(course-qa): 使用材料范围语义检索回答"
```

### Task 9: Add Structured Model Output and Coverage Runner

**Files:**
- Modify: `backend/app/integrations/model_provider/base.py`
- Modify: `backend/app/integrations/model_provider/openai.py`
- Modify: `backend/app/integrations/model_provider/mock.py`
- Create: `backend/app/modules/generation/coverage.py`
- Create: `backend/tests/integrations/test_openai_structured_output.py`
- Create: `backend/tests/modules/generation/test_coverage_runner.py`

**Interfaces:**
- Produces: `ModelProvider.generate_structured(prompt, output_schema) -> BaseModel`.
- Produces: `run_coverage_generation(batches, map_batch, reduce_results)` with explicit material coverage validation.

- [ ] **Step 1: Write failing structured-output provider tests**

```python
class Summary(BaseModel):
    points: list[str]
    citation_chunk_ids: list[str]


def test_openai_provider_parses_structured_response() -> None:
    client = FakeResponsesClient(parsed=Summary(points=["A"], citation_chunk_ids=["c1"]))
    provider = OpenAIModelProvider(api_key="test", model="test-model", client=client)

    result = provider.generate_structured(prompt="summarize", output_schema=Summary)

    assert result == Summary(points=["A"], citation_chunk_ids=["c1"])
```

Assert SDK failures map to `GENERATION_FAILED` and invalid parsed output maps to `GENERATION_SCHEMA_INVALID`.

- [ ] **Step 2: Write a failing coverage invariant test**

```python
def test_coverage_runner_rejects_missing_selected_material() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        run_coverage_generation(
            batches=[batch_for("m1")],
            expected_material_ids={"m1", "m2"},
            map_batch=lambda batch: mapped(batch),
            reduce_results=lambda items: items,
        )
    assert exc_info.value.code == "MATERIAL_COVERAGE_INCOMPLETE"
```

- [ ] **Step 3: Run and verify missing methods**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_openai_structured_output.py tests/modules/generation/test_coverage_runner.py -q
```

Expected: FAIL because structured output and the coverage runner do not exist.

- [ ] **Step 4: Implement provider parsing through the Responses API**

Use the SDK structured parsing entry point supported by the installed OpenAI SDK, passing a Pydantic model as the response format. Return the parsed Pydantic object, never the SDK response. Keep existing `answer_question()` intact.

- [ ] **Step 5: Implement map/reduce coverage accounting**

The runner records `material_ids` from every processed batch before invoking `reduce_results`. It raises `MATERIAL_COVERAGE_INCOMPLETE` if processed ids differ from expected ids, and propagates `GENERATION_FAILED` if any map call fails. It unions only citation ids returned by successful typed intermediate results.

- [ ] **Step 6: Run tests and commit**

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_openai_model_provider.py tests/integrations/test_openai_structured_output.py tests/modules/generation/test_coverage_runner.py -q
git add backend/app/integrations/model_provider backend/app/modules/generation/coverage.py backend/tests/integrations backend/tests/modules/generation/test_coverage_runner.py
git commit -m "feat(generation): 建立结构化输出和材料覆盖执行器"
```

### Task 10: Implement Selected-Material Learning Content Generators

**Files:**
- Create: `backend/app/modules/generation/generators/schemas.py`
- Create: `backend/app/modules/generation/generators/structured.py`
- Modify: `backend/app/modules/generation/orchestrator/contracts.py`
- Modify: `backend/app/modules/generation/orchestrator/registry.py`
- Modify: `backend/app/modules/generation/orchestrator/service.py`
- Modify: `backend/app/modules/generation/orchestrator/router.py`
- Create: `backend/tests/modules/generation/test_structured_generators.py`
- Modify: `backend/tests/modules/generation/test_orchestrator_service.py`
- Modify: `backend/tests/modules/generation/test_generation_api.py`

**Interfaces:**
- Produces typed schemas: `FlashcardSet`, `QuizSet`, `Mindmap`, `Outline`, `KnowledgeList`.
- Changes generator contract to consume `list[MaterialContextBatch]` and `expected_material_ids`.
- Preserves `GeneratorOutput` and `AIGeneratedContent` persistence.

- [ ] **Step 1: Write schema and multi-batch generator tests**

Minimum final schemas:

```python
class Flashcard(BaseModel):
    front: str
    back: str
    tags: list[str] = Field(default_factory=list)
    citation_chunk_ids: list[str] = Field(min_length=1)


class FlashcardSet(BaseModel):
    cards: list[Flashcard] = Field(min_length=1)
```

Define equivalent strict models for quiz questions/options/answer/explanation, mindmap nodes/edges, outline sections, and knowledge points. Tests must reject empty citations, invalid quiz answer ids, and mindmap edges referencing missing nodes.

Add a recording provider test proving two materials produce two map calls and one reduce call.

- [ ] **Step 2: Run and verify missing schemas**

```powershell
conda run -n course-nexus python -m pytest tests/modules/generation/test_structured_generators.py tests/modules/generation/test_orchestrator_service.py -q
```

Expected: FAIL because typed generators do not exist and orchestrator still calls `resolve_context()`.

- [ ] **Step 3: Implement feature-specific prompts over a shared structured generator**

`StructuredCoverageGenerator` receives content type, map schema, final schema, and prompt templates. Map prompts include chunk ids inline and instruct the model to cite only those ids. Reduce prompts receive typed intermediate JSON, deduplicate equivalent items, preserve citations, and enforce the final schema.

Register five separate configured instances for `flashcard`, `quiz`, `mindmap`, `outline`, and `knowledge_list`. Keep feature schemas and prompts independent even though the map/reduce runner is shared.

- [ ] **Step 4: Migrate orchestrator to complete batches**

Replace `resolve_context()` with:

```python
batches = list(iter_material_context_batches(
    db,
    user_id=user_id,
    course_id=course_id,
    material_scope=payload.material_scope,
    max_tokens=settings.generation_context_max_tokens,
))
if not batches:
    raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前范围没有已解析资料", status_code=400)
expected_material_ids = {material_id for batch in batches for material_id in batch.material_ids}
output = generator.generate(
    batches=batches,
    expected_material_ids=expected_material_ids,
    parameters=payload.parameters,
)
```

Build citations from the union of valid output chunk ids. Remove the current fallback that silently cites `chunks[:1]`; empty or invalid citation output must produce `GENERATION_SCHEMA_INVALID`.

- [ ] **Step 5: Run generation service and API tests**

```powershell
conda run -n course-nexus python -m pytest tests/modules/generation tests/modules/generated_content -q
```

Expected: all content types save schema-valid `content_json`; every citation belongs to a selected chunk.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/modules/generation backend/tests/modules/generation
git commit -m "feat(generation): 实现指定材料结构化内容生成"
```

### Task 11: Use Complete Material Coverage for Study Plans

**Files:**
- Modify: `backend/app/modules/study_plans/schemas.py`
- Modify: `backend/app/modules/study_plans/service.py`
- Modify: `backend/app/modules/study_plans/router.py`
- Modify: `backend/tests/modules/study_plans/test_study_plan_foundation.py`
- Modify: `backend/tests/modules/study_plans/test_study_plan_api.py`
- Modify: `backend/tests/integration/test_material_context_to_plan_flow.py`

**Interfaces:**
- Consumes: `iter_material_context_batches()` and `ModelProvider.generate_structured()`.
- Produces: a schema-valid `StudyPlanPreview` whose tasks reference all selected material ids across the plan.
- Preserves: single-course plan, preview/save API, and delayed handout/task-test generation.

- [ ] **Step 1: Write a multi-material plan coverage test**

```python
def test_plan_preview_uses_every_selected_material(db, seeded_plan_materials) -> None:
    provider = RecordingPlanProvider()

    preview = preview_study_plan(
        db,
        user_id=seeded_plan_materials.user.id,
        course_id=seeded_plan_materials.course.id,
        payload=build_request(MaterialScope()),
        model_provider=provider,
        max_context_tokens=20,
    )

    assert provider.mapped_material_ids == {
        seeded_plan_materials.first.id,
        seeded_plan_materials.second.id,
    }
    assert {material_id for task in preview.tasks for subtask in task.subtasks
            for material_id in subtask.related_material_ids} == provider.mapped_material_ids
```

- [ ] **Step 2: Run and verify failure**

```powershell
conda run -n course-nexus python -m pytest tests/modules/study_plans tests/integration/test_material_context_to_plan_flow.py -q
```

Expected: FAIL because study plans still use the first 20 resolved chunks and deterministic titles.

- [ ] **Step 3: Add a typed plan draft and coverage prompt**

Define `StudyPlanDraft`, `StudyTaskDraft`, and `StudySubTaskDraft` with date, duration, type, description, and non-empty `related_material_ids`. Map each batch to chapter/difficulty/task candidates; reduce candidates into dates bounded by request start/end dates and `daily_available_minutes`.

Validate that every related material id belongs to the selected scope and every selected material appears in at least one subtask. Reject invalid output with `GENERATION_SCHEMA_INVALID`.

- [ ] **Step 4: Preserve save semantics and on-demand generation**

Keep `StudyPlan`, `StudyTask`, and `StudySubTask` persistence unchanged. Saving a plan must not create `AIGeneratedContent`, handouts, or task tests. Inject the configured model provider in both preview and save endpoints; tests override it with a deterministic provider.

- [ ] **Step 5: Run plan and integration tests**

Run the Step 2 command.

Expected: all tests pass; cross-user material scope remains `NOT_FOUND`; each selected material is assigned to at least one subtask.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/modules/study_plans backend/tests/modules/study_plans backend/tests/integration/test_material_context_to_plan_flow.py
git commit -m "feat(study-plans): 基于全材料上下文生成学习计划"
```

### Task 12: Add Reindex Maintenance, End-to-End Proof, and Documentation Status

**Files:**
- Create: `backend/app/commands/__init__.py`
- Create: `backend/app/commands/rebuild_rag_index.py`
- Create: `backend/tests/commands/test_rebuild_rag_index.py`
- Modify: `backend/tests/integration/test_course_workspace_flow.py`
- Create: `backend/tests/integration/test_selected_material_generation_flow.py`
- Modify: `README.md`
- Modify: `docs/planning/current-state.md`
- Modify: `docs/planning/tech-debt-tracker.md`
- Modify: `docs/architecture/material-context-rag.md`
- Modify: `docs/api-data/contracts.md`

**Interfaces:**
- Produces CLI: `python -m app.commands.rebuild_rag_index --all` and `--material-id <id>`.
- Proves: parse/index/query/cite flow and all-material generate/cite flow.

- [ ] **Step 1: Write a failing rebuild command test**

```python
def test_rebuild_all_deletes_collection_and_indexes_parsed_chunks(db, tmp_path) -> None:
    rag_index = FakeRagIndex()
    seeded = seed_two_parsed_materials(db)

    result = rebuild_all(db=db, rag_index=rag_index)

    assert result.material_count == 2
    assert result.chunk_count == len(seeded.chunks)
    assert set(rag_index.records) == {chunk.id for chunk in seeded.chunks}
```

Also test a missing/deleted material id returns `NOT_FOUND` and unparsed materials are skipped.

- [ ] **Step 2: Run and verify missing command**

```powershell
conda run -n course-nexus python -m pytest tests/commands/test_rebuild_rag_index.py -q
```

Expected: FAIL because the command module does not exist.

- [ ] **Step 3: Implement rebuild service and CLI**

The command reads parsed materials and authoritative SQLite chunks, maps them to `RagChunk`, and upserts them. `--all` recreates only the configured CourseNexus collection; it must not delete SQLite, uploads, or other Chroma collections. Print material and chunk counts and return a nonzero process status on failure.

- [ ] **Step 4: Add two end-to-end integration tests**

Q&A flow:

```text
register -> create course -> upload two materials -> parse/index -> ask scoped question
-> assert only relevant selected chunk reaches model -> assert stored citation
```

Generation flow:

```text
select two materials -> force multiple batches -> generate outline
-> assert both material ids mapped -> assert schema-valid content_json
-> assert citations include source chunks from both materials
```

Use `FakeRagIndex` and deterministic structured model provider; no network and no Docker.

- [ ] **Step 5: Run the complete backend suite**

From repository root:

```powershell
pnpm backend:test
```

Expected: all backend tests pass.

- [ ] **Step 6: Run migration and local persistence smoke checks**

From repository root:

```powershell
pnpm backend:migrate
```

From `backend/`, with a temporary path and deterministic embedding test helper:

```powershell
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py::test_chroma_index_persists_and_filters_by_course -q
```

Expected: migration succeeds; persistence smoke test passes.

- [ ] **Step 7: Update authoritative docs with implemented evidence**

Document exact completed formats, commands, error codes, test count, and any deliberately deferred image OCR behavior. Mark TD-011 and TD-012 closed only if the end-to-end tests prove them; mark TD-013 closed only if all five structured generators and study-plan coverage tests pass. Do not modify PRD files.

- [ ] **Step 8: Verify docs and commit**

```powershell
git diff --check
git add backend/app/commands backend/tests/commands backend/tests/integration README.md docs/planning/current-state.md docs/planning/tech-debt-tracker.md docs/architecture/material-context-rag.md docs/api-data/contracts.md
git commit -m "test(rag): 覆盖资料索引问答和全材料生成链路"
```

## Final Acceptance

- [ ] `pnpm backend:test` passes without Docker and without live OpenAI calls.
- [ ] FastAPI is the only application service process; Chroma uses `PersistentClient` and a local ignored directory.
- [ ] PDF, DOCX, PPTX, Markdown, and text parsing produce ordered source-grounded chunks; image support is either tested or explicitly recorded as deferred.
- [ ] Parse/reparse/delete keep SQLite and Chroma behavior consistent and stale vectors are not retrievable.
- [ ] Q&A results vary by query and never escape user/course/material scope.
- [ ] Q&A citations are real retrieved `MaterialChunk` ids.
- [ ] Flashcard, Quiz, Mindmap, Outline, and Knowledge List use typed structured outputs.
- [ ] Selected-material generation processes every selected parsed material across one or more batches.
- [ ] Study-plan generation covers every selected material and still saves only plan/task structures.
- [ ] Business modules do not import Docling, LlamaIndex, Chroma, or OpenAI SDK types.
- [ ] Rebuild command can recreate the derived Chroma index from SQLite.
- [ ] Formal docs reflect implemented behavior; PRD remains unchanged; RAGFlow remains a future option only.
