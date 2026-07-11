# G01 Generation Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder-only generation path with a stable full-material generator contract, registry, provider injection, real citation binding, atomic persistence, and shared test fixtures for G02-G06.

**Architecture:** The orchestrator loads all selected material batches, creates a concrete generator from a factory and purpose-specific `ModelProvider`, and accepts only a validated `GeneratorOutput`. It filters item citation chunk IDs against delivered chunks, allocates citation IDs, injects them into final item objects, and commits content plus citations in one transaction.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, pytest, existing CourseNexus `ModelProvider` and material-context contracts.

---

## File Map

- Modify `backend/app/modules/generation/orchestrator/contracts.py`: frozen G01 request, output, protocol, and factory types.
- Modify `backend/app/modules/generation/orchestrator/registry.py`: factory registry, conflict behavior, supported types, built-in discovery, placeholder fallback.
- Modify `backend/app/modules/generation/orchestrator/router.py`: provider-factory dependency and citation-bearing response.
- Modify `backend/app/modules/generation/orchestrator/service.py`: full-batch orchestration, error classification, citation binding, transaction boundary.
- Modify `backend/app/modules/generation/generators/placeholder_generators.py`: adapt incremental fallback to the frozen contract.
- Modify `backend/app/modules/generated_content/schemas.py`: generated-content citation response DTO.
- Modify `backend/app/modules/generated_content/repository.py`: non-committing add/query helpers for content and citations.
- Modify `backend/app/modules/generated_content/service.py`: list/detail DTO assembly with citations.
- Modify `backend/app/modules/generated_content/router.py`: serialize DTOs instead of ORM rows.
- Create `backend/tests/modules/generation/conftest.py`: shared database, users, materials, client, and provider fixtures.
- Modify G01 generation and generated-content tests listed in the task book.
- Create `docs/domains/generated-content/index.md` and `architecture.md`; update the shared API, architecture, and planning documents required by G01.

## Task 1: Establish a Runnable Python 3.12 Test Environment

**Files:**
- Verify: `backend/pyproject.toml`
- Verify: `backend/environment.yml`
- Do not modify dependency manifests unless installation proves they are inconsistent.

- [ ] **Step 1: Search for the intended Conda executable**

Run:

```powershell
where.exe conda
Get-ChildItem "$env:USERPROFILE\miniconda3","$env:USERPROFILE\anaconda3","C:\ProgramData\miniconda3","C:\ProgramData\anaconda3" -Filter conda.exe -Recurse -ErrorAction SilentlyContinue
```

Expected: an executable path, or no result confirming that Conda is unavailable.

- [ ] **Step 2: Create a repository-local fallback environment only if Conda is unavailable**

Run:

```powershell
cd E:\小学期工作\CourseNexus\backend
C:\Users\lingod\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Expected: editable backend and test dependencies install without changing `pyproject.toml` or lock files. `.venv/` remains ignored.

- [ ] **Step 3: Record the Python command used by every remaining task**

Use one of:

```powershell
conda run -n course-nexus python
```

or:

```powershell
E:\小学期工作\CourseNexus\backend\.venv\Scripts\python.exe
```

Expected: Python 3.12.x.

- [ ] **Step 4: Run the current G01 baseline**

Run with the selected Python command:

```powershell
python -m pytest tests/modules/generation tests/modules/generated_content tests/contracts/test_material_context_consumers.py -q
```

Expected: the pre-change baseline passes. If it fails, record the existing failure before editing code.

## Task 2: Freeze the Generator Contract and Factory Registry

**Files:**
- Modify: `backend/app/modules/generation/orchestrator/contracts.py`
- Modify: `backend/app/modules/generation/orchestrator/registry.py`
- Modify: `backend/app/modules/generation/generators/placeholder_generators.py`
- Test: `backend/tests/modules/generation/test_orchestrator_contract.py`

- [ ] **Step 1: Replace contract tests with failing factory and protocol tests**

Add these tests and imports (`Mock` from `unittest.mock`, plus `MockModelProvider`):

```python
def test_registry_creates_generator_with_injected_provider() -> None:
    provider = MockModelProvider()
    factory = Mock(return_value=PlaceholderGenerator(content_type="outline", model_provider=provider))
    registry = GeneratorRegistry()
    registry.register("outline", factory)

    generator = registry.create("outline", provider)

    factory.assert_called_once_with(provider)
    assert generator.content_type == "outline"


def test_registry_rejects_duplicate_without_replace() -> None:
    provider_factory = lambda provider: PlaceholderGenerator(
        content_type="outline",
        model_provider=provider,
    )
    registry = GeneratorRegistry()
    registry.register("outline", provider_factory)

    with pytest.raises(CourseNexusError) as exc_info:
        registry.register("outline", provider_factory)

    assert exc_info.value.code == "CONFLICT"


def test_registry_reports_supported_types_in_stable_order() -> None:
    quiz_factory = lambda provider: PlaceholderGenerator(
        content_type="quiz",
        model_provider=provider,
    )
    outline_factory = lambda provider: PlaceholderGenerator(
        content_type="outline",
        model_provider=provider,
    )
    registry = GeneratorRegistry()
    registry.register("quiz", quiz_factory)
    registry.register("outline", outline_factory)

    assert registry.supported_content_types() == ("outline", "quiz")
```

Keep the existing request-default and unknown-type assertions, updated from `get()` to `create()`.

- [ ] **Step 2: Run contract tests and verify failure**

Run:

```powershell
python -m pytest tests/modules/generation/test_orchestrator_contract.py -q
```

Expected: FAIL because `GeneratorFactory`, `create`, replacement rules, and the new generator signature do not exist.

- [ ] **Step 3: Implement the frozen contract**

Replace the contract definitions with:

```python
from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.model_provider.base import ModelProvider
from app.modules.material_context.schemas import MaterialContextBatch, MaterialScope


class GenerateContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: str = Field(min_length=1, max_length=32)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    parameters: dict[str, Any] = Field(default_factory=dict)


class GeneratorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content: str | None = None
    content_json: dict[str, Any]
    item_citation_chunk_ids: dict[str, list[str]] = Field(default_factory=dict)


class Generator(Protocol):
    content_type: str

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput: ...


GeneratorFactory = Callable[[ModelProvider], Generator]
```

- [ ] **Step 4: Implement factory registration and built-in discovery**

Implement these public behaviors in `registry.py`:

```python
BUILTIN_GENERATOR_MODULES = {
    "flashcard": "app.modules.generation.generators.flashcard.generator",
    "knowledge_list": "app.modules.generation.generators.knowledge_list.generator",
    "mindmap": "app.modules.generation.generators.mindmap.generator",
    "outline": "app.modules.generation.generators.outline.generator",
    "quiz": "app.modules.generation.generators.quiz.generator",
}


class GeneratorRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, GeneratorFactory] = {}

    def register(self, content_type: str, factory: GeneratorFactory, *, replace: bool = False) -> None:
        if content_type in self._factories and not replace:
            raise CourseNexusError(code="CONFLICT", message="生成器已注册", status_code=409)
        self._factories[content_type] = factory

    def create(self, content_type: str, model_provider: ModelProvider) -> Generator:
        factory = self._factories.get(content_type)
        if factory is None:
            raise CourseNexusError(
                code="VALIDATION_ERROR",
                message="生成类型不支持",
                status_code=422,
                details={"content_type": content_type},
            )
        return factory(model_provider)

    def supported_content_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))
```

Use `importlib.import_module` to load `build_generator`. When a concrete `generator.py` is not yet present, register a closure that constructs the adapted `PlaceholderGenerator`; do not swallow import errors raised from inside an existing concrete module.

- [ ] **Step 5: Adapt the placeholder to the frozen contract**

The fallback constructor stores `content_type` and the injected provider. Its `generate()` accepts batches and returns a deterministic item with a stable ID and `item_citation_chunk_ids`. It must use the first delivered chunk only as an incremental fallback, not as orchestration behavior.

- [ ] **Step 6: Run the contract tests**

Run:

```powershell
python -m pytest tests/modules/generation/test_orchestrator_contract.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the frozen public contract**

```powershell
git add backend/app/modules/generation/orchestrator/contracts.py backend/app/modules/generation/orchestrator/registry.py backend/app/modules/generation/generators/placeholder_generators.py backend/tests/modules/generation/test_orchestrator_contract.py
git diff --cached --check
git commit -m "feat(generation): 冻结生成器公共合同与注册机制"
```

## Task 3: Add Purpose-Specific Provider Injection

**Files:**
- Modify: `backend/app/modules/generation/orchestrator/router.py`
- Test: `backend/tests/modules/generation/test_generation_api.py`

- [ ] **Step 1: Write failing provider selection tests**

Test the dependency directly with monkeypatched settings and provider classes:

```python
def test_generation_provider_factory_uses_content_type_endpoint(monkeypatch) -> None:
    settings = Settings(quiz_api_key="key", quiz_base_url="https://models.test", quiz_model="quiz-model")
    monkeypatch.setattr(generation_router, "get_settings", lambda: settings)
    monkeypatch.setattr(generation_router, "OpenAIModelProvider", FakeProvider)

    provider = generation_router.get_generation_model_provider("quiz")

    assert provider.model == "quiz-model"
    assert provider.base_url == "https://models.test"
    assert provider.api_key_env_name == "QUIZ_API_KEY"


def test_generation_provider_factory_uses_mock_without_key(monkeypatch) -> None:
    monkeypatch.setattr(generation_router, "get_settings", lambda: Settings())

    assert isinstance(generation_router.get_generation_model_provider("outline"), MockModelProvider)
```

- [ ] **Step 2: Run tests and verify failure**

```powershell
python -m pytest tests/modules/generation/test_generation_api.py -k provider -q
```

Expected: FAIL because the generation provider function does not exist.

- [ ] **Step 3: Implement provider selection**

Add:

```python
GenerationModelProviderFactory = Callable[[str], ModelProvider]


def get_generation_model_provider(content_type: str) -> ModelProvider:
    settings = get_settings()
    endpoint = settings.model_endpoint(cast(ModelPurpose, content_type))
    if endpoint.api_key:
        return OpenAIModelProvider(
            api_key=endpoint.api_key,
            model=endpoint.model,
            base_url=endpoint.base_url,
            api_key_env_name=f"{content_type.upper()}_API_KEY",
        )
    return MockModelProvider()


def get_generation_model_provider_factory() -> GenerationModelProviderFactory:
    return get_generation_model_provider
```

The endpoint receives the factory through `Depends`, then calls it only after registry type validation. Tests override `get_generation_model_provider_factory` with a lambda returning their recording provider.

- [ ] **Step 4: Run provider tests**

```powershell
python -m pytest tests/modules/generation/test_generation_api.py -k provider -q
```

Expected: PASS.

- [ ] **Step 5: Commit provider injection**

```powershell
git add backend/app/modules/generation/orchestrator/router.py backend/tests/modules/generation/test_generation_api.py
git diff --cached --check
git commit -m "feat(generation): 按内容类型注入模型提供器"
```

## Task 4: Replace Top-K Context with Full-Material Batch Orchestration

**Files:**
- Modify: `backend/app/modules/generation/orchestrator/service.py`
- Test: `backend/tests/modules/generation/test_orchestrator_service.py`

- [ ] **Step 1: Write a failing all-batch delivery test**

Create a recording generator with the frozen signature:

```python
class RecordingGenerator:
    content_type = "outline"

    def __init__(self) -> None:
        self.batches = ()
        self.expected_material_ids = frozenset()

    def generate(self, *, batches, expected_material_ids, parameters):
        self.batches = batches
        self.expected_material_ids = expected_material_ids
        first = batches[0].chunks[0]
        return GeneratorOutput(
            title="Outline",
            content_json={"items": [{"id": "item_001", "text": "Alpha", "source_citation_ids": []}]},
            item_citation_chunk_ids={"item_001": [first.chunk_id]},
        )
```

Seed two parsed materials and force multiple batches with a small `max_tokens`. Assert that all source material IDs appear in the generator batches and expected set.

- [ ] **Step 2: Run the test and verify failure**

```powershell
python -m pytest tests/modules/generation/test_orchestrator_service.py -k all_batches -q
```

Expected: FAIL because the service still calls `resolve_context()` and uses the old signature.

- [ ] **Step 3: Implement full-batch orchestration**

Change `generate_content()` to accept `model_provider` and `max_batch_tokens`. Perform operations in this order:

```python
assert_course_owner(db, user_id, course_id)
generator = registry.create(payload.content_type, model_provider)
batches = tuple(iter_material_context_batches(
    db,
    user_id=user_id,
    course_id=course_id,
    material_scope=payload.material_scope,
    max_tokens=max_batch_tokens,
))
if not batches:
    raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前范围没有已解析资料", status_code=400)
expected_material_ids = frozenset(
    material_id for batch in batches for material_id in batch.material_ids
)
output = generator.generate(
    batches=batches,
    expected_material_ids=expected_material_ids,
    parameters=payload.parameters,
)
```

Remove production imports and calls to `resolve_context()`.

- [ ] **Step 4: Run service and material-context contract tests**

```powershell
python -m pytest tests/modules/generation/test_orchestrator_service.py tests/contracts/test_material_context_consumers.py -q
```

Expected: PASS for the new all-batch test and existing material-context contract tests; later citation tests may still fail until Task 5.

- [ ] **Step 5: Commit full-batch delivery**

```powershell
git add backend/app/modules/generation/orchestrator/service.py backend/tests/modules/generation/test_orchestrator_service.py
git diff --cached --check
git commit -m "feat(generation): 使用全材料批次执行生成"
```

## Task 5: Bind Real Item Citations Without Fallback

**Files:**
- Modify: `backend/app/modules/generation/orchestrator/service.py`
- Modify: `backend/app/modules/generated_content/repository.py`
- Test: `backend/tests/modules/generation/test_orchestrator_service.py`

- [ ] **Step 1: Write failing citation filtering and binding tests**

Cover these assertions in separate tests:

```python
assert content.content_json["items"][0]["source_citation_ids"] == [citations[0].id]
assert {citation.chunk_id for citation in citations} == {allowed_chunk.id}
assert fabricated_chunk_id not in {citation.chunk_id for citation in citations}
assert unselected_chunk.id not in {citation.chunk_id for citation in citations}
```

Add an empty-binding test asserting zero `SourceCitation` rows and an unchanged empty `source_citation_ids` list. Add a duplicated-chunk test asserting one citation row and continuous `sort_order` beginning at 1.

- [ ] **Step 2: Run citation tests and verify failure**

```powershell
python -m pytest tests/modules/generation/test_orchestrator_service.py -k citation -q
```

Expected: FAIL because the current service uses global `citation_chunk_ids`, falls back to the first chunk, and cannot inject generated citation IDs.

- [ ] **Step 3: Implement stable citation selection**

Build `chunk_by_id` and source-order position from all delivered batches. For each final item binding, retain unique allowed chunk IDs only. Compute the union ordered by original chunk position. Allocate citation IDs once, then build:

```python
citation_id_by_chunk_id = {
    chunk.chunk_id: _new_citation_id()
    for chunk in selected_chunks
}
```

Build `SourceCitation` values with `sort_order` starting at 1. Preserve real page metadata; when both source location fields are null, store `page=null,page_index=0` as the user-approved compatibility sentinel. Never substitute a chunk when no valid binding exists.

- [ ] **Step 4: Implement generic item-ID injection**

Use a recursive copy function:

```python
def _bind_item_citations(value: object, citation_ids_by_item_id: dict[str, list[str]]) -> object:
    if isinstance(value, list):
        return [_bind_item_citations(item, citation_ids_by_item_id) for item in value]
    if isinstance(value, dict):
        bound = {key: _bind_item_citations(item, citation_ids_by_item_id) for key, item in value.items()}
        item_id = bound.get("id")
        if isinstance(item_id, str) and item_id in citation_ids_by_item_id:
            bound["source_citation_ids"] = citation_ids_by_item_id[item_id]
        return bound
    return value
```

Validate that the returned root is a dictionary before persistence.

- [ ] **Step 5: Add non-committing persistence helpers**

Add repository functions that call `db.add()` / `db.add_all()` and `db.flush()` without committing:

```python
def add_generated_content(db: Session, content: AIGeneratedContent) -> AIGeneratedContent:
    db.add(content)
    db.flush()
    return content


def add_generated_content_citations(db: Session, citations: list[SourceCitation]) -> None:
    db.add_all(citations)
    db.flush()
```

Keep the existing `save_generated_content()` behavior for callers outside G01.

- [ ] **Step 6: Run citation tests**

```powershell
python -m pytest tests/modules/generation/test_orchestrator_service.py -k citation -q
```

Expected: PASS.

- [ ] **Step 7: Commit citation binding**

```powershell
git add backend/app/modules/generation/orchestrator/service.py backend/app/modules/generated_content/repository.py backend/tests/modules/generation/test_orchestrator_service.py
git diff --cached --check
git commit -m "feat(generation): 绑定真实条目引用并移除回退"
```

## Task 6: Make Success and Failure Persistence Atomic

**Files:**
- Modify: `backend/app/modules/generation/orchestrator/service.py`
- Test: `backend/tests/modules/generation/test_orchestrator_service.py`

- [ ] **Step 1: Write failing error and rollback tests**

Add tests for:

```python
with pytest.raises(CourseNexusError) as exc_info:
    generate_content(... invalid_parameter_generator ...)
assert exc_info.value.code == "VALIDATION_ERROR"
assert _generated_contents(db) == []

failed = generate_content(... failing_generator ...)
assert failed.generation_status == "failed"
assert failed.content_json is None
assert _citations(db, failed.id) == []

with pytest.raises(IntegrityError):
    generate_content(... repository_failure ...)
assert _generated_contents(db) == []
assert _all_citations(db) == []
```

Cover `GENERATION_FAILED`, `GENERATION_SCHEMA_INVALID`, and `MATERIAL_COVERAGE_INCOMPLETE` separately.

- [ ] **Step 2: Run the error tests and verify failure**

```powershell
python -m pytest tests/modules/generation/test_orchestrator_service.py -k "failure or rollback or invalid_parameters" -q
```

Expected: FAIL because the current repository commits content before citations and treats all generator errors alike.

- [ ] **Step 3: Implement error classification**

Re-raise `CourseNexusError(code="VALIDATION_ERROR")` without persistence. For all other `CourseNexusError` values, create a failed record with its stable code. Translate unexpected exceptions to `GENERATION_FAILED`.

Successful and failed writes use explicit transaction handling:

```python
try:
    add_generated_content(db, content)
    add_generated_content_citations(db, citations)
    db.commit()
except Exception:
    db.rollback()
    raise
db.refresh(content)
```

Failed records do not call the citation helper.

- [ ] **Step 4: Run all orchestrator service tests**

```powershell
python -m pytest tests/modules/generation/test_orchestrator_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit atomic persistence and errors**

```powershell
git add backend/app/modules/generation/orchestrator/service.py backend/tests/modules/generation/test_orchestrator_service.py
git diff --cached --check
git commit -m "feat(generation): 原子保存生成内容与失败状态"
```

## Task 7: Return Citations from Generation, History, and Detail

**Files:**
- Modify: `backend/app/modules/generated_content/schemas.py`
- Modify: `backend/app/modules/generated_content/repository.py`
- Modify: `backend/app/modules/generated_content/service.py`
- Modify: `backend/app/modules/generated_content/router.py`
- Modify: `backend/app/modules/generation/orchestrator/router.py`
- Test: `backend/tests/modules/generated_content/test_generated_content_service.py`
- Test: `backend/tests/modules/generation/test_generation_api.py`

- [ ] **Step 1: Write failing response tests**

Assert all three endpoints contain a stable citation array:

```python
assert generation.json()["data"]["source_citations"][0]["chunk_id"] == expected_chunk_id
assert listed.json()["data"][0]["source_citations"][0]["material_name"] == "notes.md"
assert detail.json()["data"]["source_citations"][0]["hit_text"] == "Alpha"
```

Add failed and citation-free records asserting `source_citations == []`. Add user-isolation tests for citation retrieval.

- [ ] **Step 2: Run response tests and verify failure**

```powershell
python -m pytest tests/modules/generated_content/test_generated_content_service.py tests/modules/generation/test_generation_api.py -k citation -q
```

Expected: FAIL because `GeneratedContentRead` has no citation field and services return ORM rows only.

- [ ] **Step 3: Add generated-content citation DTOs**

Define:

```python
class GeneratedContentCitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    material_id: str
    chunk_id: str | None
    material_name: str
    page: str | None
    page_index: int | None
    hit_text: str
    sort_order: int


class GeneratedContentRead(BaseModel):
    # existing fields
    source_citations: list[GeneratedContentCitationRead] = Field(default_factory=list)
```

- [ ] **Step 4: Query citations in stable order and assemble DTOs**

Add repository functions to list citations for one or many generated-content IDs, ordered by `generated_content_id`, `sort_order`, and `id`. Service functions convert each ORM content row with `model_validate`, then copy in the matching citation DTO list.

- [ ] **Step 5: Update routers to serialize service DTOs**

Generation service returns a `GeneratedContentRead`, or the router calls a single DTO assembler after persistence. Generated-content list and detail routers call `.model_dump(mode="json")` directly on DTOs.

- [ ] **Step 6: Run generated-content and API tests**

```powershell
python -m pytest tests/modules/generated_content/test_generated_content_service.py tests/modules/generation/test_generation_api.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit citation responses**

```powershell
git add backend/app/modules/generated_content backend/app/modules/generation/orchestrator/router.py backend/tests/modules/generated_content/test_generated_content_service.py backend/tests/modules/generation/test_generation_api.py
git diff --cached --check
git commit -m "feat(generated-content): 在生成记录中返回引用"
```

## Task 8: Consolidate Shared G01 Fixtures and Regression Coverage

**Files:**
- Create: `backend/tests/modules/generation/conftest.py`
- Modify: `backend/tests/modules/generation/test_orchestrator_contract.py`
- Modify: `backend/tests/modules/generation/test_orchestrator_service.py`
- Modify: `backend/tests/modules/generation/test_generation_api.py`

- [ ] **Step 1: Move repeated database and seed setup into fixtures**

Create fixtures named `db`, `client`, `alice`, `bob`, `course`, `parsed_materials`, `recording_model_provider`, and `failing_model_provider`. The parsed-material fixture creates two different material names with multiple chunks and includes at least one chunk where both page fields are null.

- [ ] **Step 2: Add missing API matrix tests**

Add explicit tests for:

```python
assert unauthorized.status_code == 401
assert other_users_course.status_code == 404
assert empty_scope.status_code == 400
assert invalid_parameters.status_code == 422
assert first_generation_id != second_generation_id
assert failed_detail.json()["data"]["generation_status"] == "failed"
```

- [ ] **Step 3: Run the G01 suite**

```powershell
python -m pytest tests/modules/generation tests/modules/generated_content -q
python -m pytest tests/modules/material_context tests/contracts/test_material_context_consumers.py -q
```

Expected: all tests PASS without live network access.

- [ ] **Step 4: Commit shared fixtures and regression tests**

```powershell
git add backend/tests/modules/generation backend/tests/modules/generated_content
git diff --cached --check
git commit -m "test(generation): 完善公共生成链路回归覆盖"
```

## Task 9: Document and Verify the Frozen G01 Contract

**Files:**
- Create: `docs/domains/generated-content/index.md`
- Create: `docs/domains/generated-content/architecture.md`
- Modify: `docs/architecture/module-boundaries.md`
- Modify: `docs/architecture/runtime-flows.md`
- Modify: `docs/api-data/contracts.md`
- Modify: `docs/api-data/frontend-integration.md`
- Modify: `docs/api-data/table-schema.md`
- Modify: `docs/api-data/data-model.md`
- Modify: `docs/planning/current-state.md`

- [ ] **Step 1: Write the implemented architecture document**

Record exact code entry points, the registry extension protocol, full-material sequence, provider injection, generic item citation binding, transaction boundary, error matrix, `O(C + J)` citation processing cost where `C` is delivered chunks and `J` is item citation references, the configured material batch token limit, and the G01 test commands and current results.

- [ ] **Step 2: Update shared API and citation semantics**

Document `source_citations` on generation, list, and detail responses. State that the existing location constraint is retained and unpaginated sources use `page=null,page_index=0` as an unknown-location sentinel. Document the five supported content types as registered but still placeholder-backed until their corresponding G02-G06 commit lands.

- [ ] **Step 3: Run documentation consistency searches**

```powershell
rg -n "resolve_context\(|citation_chunk_ids|PlaceholderGenerator" backend/app/modules/generation docs -S
rg -n "source_citations" docs/api-data docs/domains/generated-content -S
```

Expected: no production generation call to `resolve_context`, no old public `citation_chunk_ids` contract, and all response documentation includes citations.

- [ ] **Step 4: Run final G01 verification**

```powershell
python -m pytest tests/modules/generation tests/modules/generated_content -q
python -m pytest tests/modules/material_context tests/contracts/test_material_context_consumers.py -q
python -m pytest -q
cd ..
pnpm frontend:test
pnpm frontend:build
git diff --check
```

Expected: every command exits 0. No live OpenAI or Chroma request occurs.

- [ ] **Step 5: Review scope and sensitive files**

```powershell
git status --short
git diff --stat
git diff
git ls-files --others --exclude-standard
```

Expected: only G01-owned backend files, tests, and required documentation are changed; no `.env`, key, database, upload, or generated asset is present.

- [ ] **Step 6: Commit G01 documentation**

```powershell
git add docs/domains/generated-content docs/architecture/module-boundaries.md docs/architecture/runtime-flows.md docs/api-data/contracts.md docs/api-data/frontend-integration.md docs/api-data/table-schema.md docs/api-data/data-model.md docs/planning/current-state.md
git diff --cached --check
git commit -m "docs(generation): 记录公共生成架构与引用契约"
```

- [ ] **Step 7: Freeze G01 before planning G02**

Record the final commit IDs and verify:

```powershell
git status --short
git log --oneline 5878ab3..HEAD
```

Expected: clean worktree and a sequence of scoped local G01 commits. Do not edit `contracts.py` or `registry.py` in G02-G06 plans unless a separately approved contract defect is discovered.
