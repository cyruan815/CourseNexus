# G04 Mindmap Markmap Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not dispatch subagents because the user explicitly prohibited them.

**Goal:** Implement the real G04 backend generator that builds a validated, cited mindmap graph from all selected materials and stores a deterministic Markmap Markdown projection in `content_json.markmap_markdown`.

**Architecture:** The model extracts batch-local concept candidates only. Local Python code merges candidates, constructs and validates the child tree, adds optional related edges, assigns stable BFS IDs, serializes the legal tree to Markmap Markdown, and returns node chunk bindings through the frozen G01 contract. Existing orchestration persists `content_json` and `SourceCitation` rows atomically.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, pytest, existing CourseNexus `ModelProvider`, G01 generator contract, and material-context batches. No Markmap package is installed in the backend.

---

## Delivery Preconditions

- Do not start implementation until the preceding independent generation PR has been rebase-merged and `feature/generation` has been updated from the latest `main` without a merge commit.
- Work in an isolated G04 worktree created with `superpowers:using-git-worktrees`.
- Push only to `feature/generation`, only after explicit authorization. Never force-push without explicit authorization.
- Open one independent G04 PR after verification; the project owner performs rebase merge.

## File Map

- Modify `backend/app/modules/generation/generators/mindmap/__init__.py`: expose no unstable implementation details.
- Create `backend/app/modules/generation/generators/mindmap/schemas.py`: parameters, map candidates, final nodes/edges/content, and graph invariants.
- Create `backend/app/modules/generation/generators/mindmap/prompts.py`: batch-grounded structured extraction prompt.
- Create `backend/app/modules/generation/generators/mindmap/markdown.py`: deterministic child-tree to Markmap Markdown serializer.
- Create `backend/app/modules/generation/generators/mindmap/generator.py`: map, coverage, reduce, citation bindings, and `build_generator`.
- Create `backend/tests/modules/generation/generators/mindmap/test_mindmap_schemas.py`.
- Create `backend/tests/modules/generation/generators/mindmap/test_mindmap_markdown.py`.
- Create `backend/tests/modules/generation/generators/mindmap/test_mindmap_generator.py`.
- Create `backend/tests/modules/generation/generators/mindmap/test_mindmap_api.py`.
- Create `docs/domains/generated-content/mindmap.md` and update the generated-content, API, runtime-flow, current-state, and frontend integration documents after implementation.

## Task 1: Freeze Parameters and Candidate Schemas

**Files:**
- Create: `backend/app/modules/generation/generators/mindmap/schemas.py`
- Test: `backend/tests/modules/generation/generators/mindmap/test_mindmap_schemas.py`

- [ ] **Step 1: Write failing parameter and candidate tests**

Cover defaults and boundaries for `center_topic`, `max_depth`, `max_nodes`, and `include_cross_links`; reject unknown fields, blank topics, depth outside 2..6, and node count outside 3..200. Verify `ConceptCandidate` rejects blank keys/labels and `RelationCandidate` accepts only `child|related`.

```python
def test_parameters_use_documented_defaults() -> None:
    params = MindmapParameters.model_validate({})
    assert params.max_depth == 4
    assert params.max_nodes == 80
    assert params.include_cross_links is True


@pytest.mark.parametrize("value", [1, 7])
def test_parameters_reject_depth_outside_contract(value: int) -> None:
    with pytest.raises(ValidationError):
        MindmapParameters(max_depth=value)
```

- [ ] **Step 2: Run the schema tests and verify RED**

```powershell
cd E:\小学期工作\CourseNexus\backend
.\.venv\Scripts\python.exe -m pytest tests/modules/generation/generators/mindmap/test_mindmap_schemas.py -q
```

Expected: collection fails because the mindmap schema classes do not exist.

- [ ] **Step 3: Implement strict Pydantic schemas**

Define `MindmapParameters`, `ConceptCandidate`, `RelationCandidate`, and `MindmapMapResult` with `ConfigDict(extra="forbid")`. Candidate source chunk IDs use `list[str]`; final graph types are added in Task 2.

- [ ] **Step 4: Run tests and verify GREEN**

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/generation/generators/mindmap/schemas.py backend/tests/modules/generation/generators/mindmap/test_mindmap_schemas.py
git commit -m "feat(mindmap): 定义导图参数与候选结构"
```

## Task 2: Validate the Final Graph Contract

**Files:**
- Modify: `backend/app/modules/generation/generators/mindmap/schemas.py`
- Modify: `backend/tests/modules/generation/generators/mindmap/test_mindmap_schemas.py`

- [ ] **Step 1: Add failing final-graph tests**

Create helpers for a valid root and child, then test: exactly one level-1 root; `root_node_id` exists and matches it; every edge endpoint exists; every non-root has exactly one child parent; all nodes are reachable; no self-loop or child cycle; child level equals parent level plus one; sibling labels are casefold-unique; related edges have valid endpoints and no duplicate direction; depth and node limits are enforced.

```python
def test_final_graph_rejects_child_cycle() -> None:
    with pytest.raises(ValidationError):
        MindmapContent.model_validate(
            graph_payload(edges=[
                {"from": "node_001", "to": "node_002", "relation": "child"},
                {"from": "node_002", "to": "node_001", "relation": "child"},
            ])
        )
```

- [ ] **Step 2: Run the focused tests and verify RED**

Expected: failures because final graph schemas and validation are absent.

- [ ] **Step 3: Implement final schemas and graph validation**

Add `MindmapNode`, `MindmapEdge`, and `MindmapContent`. Use adjacency dictionaries and DFS color states for cycle detection, then BFS for reachability and level verification. Include `schema_version="1.0"`, `renderer="markmap"`, and `markmap_markdown`; accept `max_depth` and `max_nodes` as validation context or validate them in a dedicated `validate_graph_limits` function called by the generator.

- [ ] **Step 4: Run tests and verify GREEN**

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/generation/generators/mindmap/schemas.py backend/tests/modules/generation/generators/mindmap/test_mindmap_schemas.py
git commit -m "feat(mindmap): 校验导图结构不变量"
```

## Task 3: Serialize the Child Tree to Markmap Markdown

**Files:**
- Create: `backend/app/modules/generation/generators/mindmap/markdown.py`
- Test: `backend/tests/modules/generation/generators/mindmap/test_mindmap_markdown.py`

- [ ] **Step 1: Write failing serializer tests**

Test a three-level tree, stable sibling order, related-edge exclusion, whitespace normalization, and escaping of leading list markers and Markdown control characters.

```python
def test_serialize_markmap_markdown_uses_two_space_nested_lists() -> None:
    markdown = serialize_markmap_markdown(
        root_node_id="node_001",
        nodes=nodes_fixture(),
        edges=edges_fixture(),
    )
    assert markdown == "- 操作系统\n  - 进程管理\n    - 进程状态\n  - 内存管理"
```

- [ ] **Step 2: Run serializer tests and verify RED**

Expected: import failure for `markdown.py`.

- [ ] **Step 3: Implement deterministic serialization**

Build `children_by_parent` from child edges, preserve final node order for siblings, normalize all whitespace to one space, escape backslash and Markdown structural characters, and recursively emit `"  " * depth + "- " + label`. Raise the generator schema error type if the root or child endpoint is missing; do not silently skip invalid data.

- [ ] **Step 4: Run serializer and schema tests**

Expected: both suites pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/generation/generators/mindmap/markdown.py backend/tests/modules/generation/generators/mindmap/test_mindmap_markdown.py
git commit -m "feat(mindmap): 生成Markmap兼容Markdown"
```

## Task 4: Implement Batch Mapping and Deterministic Reduction

**Files:**
- Create: `backend/app/modules/generation/generators/mindmap/prompts.py`
- Create: `backend/app/modules/generation/generators/mindmap/generator.py`
- Modify: `backend/app/modules/generation/generators/mindmap/__init__.py`
- Test: `backend/tests/modules/generation/generators/mindmap/test_mindmap_generator.py`

- [ ] **Step 1: Write failing map tests with the shared recording provider**

Assert that invalid parameters fail before the first provider call; every delivered batch is mapped exactly once; prompts contain chunk IDs, material names, locations, headings, and text; `MindmapMapResult` is the requested response schema; and no direct OpenAI or retrieval call is made.

- [ ] **Step 2: Write failing reduce tests**

Use deterministic candidates across two materials to verify normalized label merging, center-topic root selection, stable child construction, `include_cross_links=false`, BFS IDs, depth and node pruning, no dangling descendants, non-root retained citations, fabricated chunk filtering through G01, and Markdown generated from final IDs.

- [ ] **Step 3: Run generator tests and verify RED**

Expected: import or behavior failures because the real generator is absent.

- [ ] **Step 4: Implement prompt construction and map calls**

`MindmapGenerator.generate` validates `MindmapParameters`, calls `generate_structured(prompt, MindmapMapResult)` once per batch, records even empty map results for coverage, and invokes the existing `run_material_coverage` before reduce. Prompt instructions forbid external facts and require source chunk IDs from the presented allow-list.

- [ ] **Step 5: Implement deterministic reduce**

Normalize labels with Unicode casefold and collapsed whitespace; merge exact normalized concepts; select the explicit `center_topic` match when present, otherwise rank by cross-material support then first source order. Construct one child parent per concept, attach unresolved concepts to the root, remove self-relations and duplicate edges, prune beyond `max_depth`, rank to `max_nodes`, and reconnect retained descendants only to the nearest retained ancestor. Add related edges only when enabled.

- [ ] **Step 6: Assign IDs, serialize, and return the G01 output**

Assign `node_001...node_N` in BFS order, calculate levels locally, produce `MindmapContent`, call `serialize_markmap_markdown`, and return:

```python
GeneratorOutput(
    title=f"知识导图：{root.label}",
    content=None,
    content_json=content.model_dump(mode="json"),
    item_citation_chunk_ids={node.id: retained_chunk_ids[node.id] for node in nodes},
)
```

The root binding may be empty; every non-root binding must be non-empty after allow-list filtering or generation fails with the existing schema-invalid exception path.

- [ ] **Step 7: Add factory discovery**

```python
def build_generator(model_provider: ModelProvider) -> MindmapGenerator:
    return MindmapGenerator(model_provider=model_provider)
```

Do not modify the G01 registry; its existing module discovery must load this factory automatically.

- [ ] **Step 8: Run focused tests and verify GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/modules/generation/generators/mindmap/test_mindmap_generator.py tests/modules/generation/generators/mindmap/test_mindmap_markdown.py tests/modules/generation/generators/mindmap/test_mindmap_schemas.py -q
```

- [ ] **Step 9: Commit**

```powershell
git add backend/app/modules/generation/generators/mindmap backend/tests/modules/generation/generators/mindmap
git commit -m "feat(mindmap): 实现全材料知识导图生成"
```

## Task 5: Verify POST, History, Detail, and Failure Persistence

**Files:**
- Create: `backend/tests/modules/generation/generators/mindmap/test_mindmap_api.py`
- Do not modify G01 router, service, contracts, registry, database models, or migrations unless an independently demonstrated G01 defect blocks the approved contract.

- [ ] **Step 1: Write failing API tests**

Cover authentication 401, foreign course/material 404, no parsed material 400, invalid parameter 422 without a record, successful POST 200, history and detail round-trip, `content_json.markmap_markdown`, citation ID resolution, all edge endpoints, failed model record, invalid graph record, coverage failure, and distinct IDs for repeated requests.

- [ ] **Step 2: Run API tests and verify RED**

Expected: failures until Task 4 factory discovery and final behavior are correct.

- [ ] **Step 3: Fix only G04-owned integration defects**

Adjust G04 output, exception translation inputs, or fixtures. Preserve the frozen G01 API and persistence behavior.

- [ ] **Step 4: Run G04 and G01 regression suites**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/modules/generation/generators/mindmap -q
.\.venv\Scripts\python.exe -m pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context tests/contracts/test_material_context_consumers.py -q
```

Expected: all pass with no live network calls.

- [ ] **Step 5: Commit**

```powershell
git add backend/tests/modules/generation/generators/mindmap
git commit -m "test(mindmap): 覆盖接口引用和失败路径"
```

## Task 6: Synchronize Domain and Frontend Handoff Documentation

**Files:**
- Create: `docs/domains/generated-content/mindmap.md`
- Modify: `docs/domains/generated-content/index.md`
- Modify: `docs/domains/generated-content/architecture.md`
- Modify: `docs/api-data/contracts.md`
- Modify: `docs/api-data/frontend-integration.md`
- Modify: `docs/architecture/runtime-flows.md`
- Modify: `docs/planning/current-state.md`
- Verify: `docs/api-data/mindmap-frontend-handoff.md`
- Verify: `docs/planning/phase-1-task-books/backend-generation/G04-mindmap.md`

- [ ] **Step 1: Document the implemented code rather than the proposal**

Record exact module entry points, schema fields, map/reduce responsibilities, normalization and pruning rules, graph validation, Markdown escaping rules, time/space complexity, model-call and token budgets, errors, and actual test commands/results.

- [ ] **Step 2: Reconcile the frontend handoff with the real response**

Confirm all route paths, wrapper fields, `schema_version`, `renderer`, Markdown JSON path, citation semantics, failed states, and Markmap limitations match tested behavior. Remove any example field not present in the actual schema.

- [ ] **Step 3: Scan for contradictions**

```powershell
rg -n "renderer-neutral|只生成结构化|禁止.*Markdown|markmap_markdown|Mindmap" docs
rg -n "TBD|TODO|待定" docs/domains/generated-content/mindmap.md docs/api-data/mindmap-frontend-handoff.md
git diff --check
```

Expected: no unresolved contradiction, placeholder, or whitespace error.

- [ ] **Step 4: Commit**

```powershell
git add docs
git commit -m "docs(mindmap): 记录生成算法与前端交接"
```

## Task 7: Final Verification and G04 Delivery

**Files:**
- Verify all G04 files and commits.

- [ ] **Step 1: Run complete backend verification**

```powershell
cd E:\小学期工作\CourseNexus\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: complete backend suite passes.

- [ ] **Step 2: Run frontend regression and build**

```powershell
$nodeDir='E:\小学期工作\.tools\node-v22.14.0-win-x64'
$env:PATH="$nodeDir;$env:PATH"
corepack pnpm --dir ..\frontend test -- --run
corepack pnpm --dir ..\frontend build
```

Expected: frontend tests and production build pass despite no frontend source change.

- [ ] **Step 3: Audit repository state**

```powershell
git diff --check
git status --short
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```

Expected: clean worktree, only scoped G04 commits, no database migration, dependency, frontend, or unrelated generator change.

- [ ] **Step 4: Request explicit authorization before remote operations**

Report exact test totals, build result, commit list, and changed files. Do not push or create the PR until the user explicitly authorizes those operations.

- [ ] **Step 5: Push and open the independent PR after authorization**

Fast-forward the fixed `feature/generation` branch to the verified G04 worktree commit, push `feature/generation`, and open a PR targeting `main`. Do not merge the PR and retain the worktree for review feedback.
