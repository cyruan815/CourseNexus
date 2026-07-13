# Handout JSON Prompt Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade study-mode handout generation so model output is a structured JSON teaching document whose formulas, charts, mindmaps, diagrams, examples, and citations can be rendered cleanly by frontend components and exported safely.

**Architecture:** Keep `ai_generated_contents.content_json` as the authoritative persisted handout payload. The model outputs a validated Pydantic schema with typed content blocks; Markdown remains allowed only inside controlled text fields, while formulas, tables, charts, mindmaps, and diagrams use dedicated structured blocks. Prompt rules are derived from the attached reference prompt, but adapted to CourseNexus fields, task mode, diagnosis, planner strategy, and citation constraints.

**Tech Stack:** Python + FastAPI + Pydantic structured outputs, SQLAlchemy JSON persistence, React + TypeScript frontend rendering, KaTeX-compatible LaTeX strings, Mermaid/Markmap-ready structured graph data, pytest/Vitest.

---

## Non-Negotiable Context

Before implementation, read these files in this order:

1. `docs/index.md`
2. `C:\Users\50754\.codex\attachments\0ec10419-7ce0-463e-990d-fddb5429b83d\pasted-text.txt`
3. `docs/domains/study-mode/task-content.md`
4. `docs/domains/study-mode/diagnostic-questions.md`
5. `backend/app/modules/generation/generators/handout/schemas.py`
6. `backend/app/modules/generation/generators/handout/generator.py`
7. `backend/app/modules/learning_execution/service.py`
8. `backend/app/modules/exports/renderer.py`
9. `frontend/src/pages/GeneratedContentDetailPage.tsx`

The attached prompt is a high-quality reference for teaching design, formula rules, diagram rules, citation rules, and self-check behavior. It must not be copied as a Markdown-only output prompt. CourseNexus should use its teaching requirements while preserving a structured JSON contract.

Current important mismatch:

- `diagnostic_explanation_style` is still present in `HandoutGenerationParameters` and injected by `learning_execution.service`.
- Study-mode diagnostic v2 says the user no longer chooses teaching style; frontend only asks `weak_area`.
- `explanation_style` may remain as an internal derived hint, but the handout prompt should not treat it as a user-facing field. Prefer `teaching_strategy_hint` or derive rules directly from `weak_area`.

## Target Outcome

The generated handout should support clean rendering of:

- formulas through structured `formula` blocks and KaTeX-compatible LaTeX;
- comparison tables through bounded `table` blocks;
- relationship diagrams through `mermaid` or `mindmap` blocks;
- numeric charts through structured `chart` blocks only when source data exists;
- examples through structured `example` blocks;
- mistakes through structured `mistake` or `callout` blocks;
- citations through section/block `source_citation_ids` that refer only to provided chunk IDs before persistence and to `SourceCitation.id` after persistence.

The model should receive explicit inputs for task mode, learning goal, time/depth controls, diagnosis, and material chunks. The prompt should switch teaching emphasis by `subtask_type`, `content_depth`, `example_intensity`, `assessment_intensity`, `review_intensity`, and `weak_area`.

## File Structure

### Backend Contract

- Modify: `backend/app/modules/generation/generators/handout/schemas.py`
  - Owns `HandoutContent` v2 Pydantic schema.
  - Defines typed block models such as `ParagraphBlock`, `FormulaBlock`, `ExampleBlock`, `TableBlock`, `MermaidBlock`, `MindmapBlock`, `ChartBlock`, `CalloutBlock`, and `SelfCheckBlock`.
  - Enforces bounded block counts, non-empty text, table dimensions, allowed block types, and source citation lists.

- Modify: `backend/app/modules/generation/generators/handout/generator.py`
  - Builds the upgraded prompt.
  - Maps CourseNexus inputs to the reference prompt concepts.
  - Calls `ModelProvider.generate_structured(..., output_schema=HandoutContent)`.
  - Validates citation chunk IDs and quality constraints.

- Modify: `backend/app/modules/learning_execution/service.py`
  - Enriches handout parameters from course/task/plan/subtask context.
  - Replaces user-facing `diagnostic_explanation_style` naming with internal strategy fields.
  - Passes planner strategy values if present in `parsed_config_json`.

- Modify: `backend/app/modules/exports/renderer.py`
  - Renders v2 handout JSON to Markdown/HTML/PDF.
  - Keeps PDF export usable even when interactive diagrams have no PDF renderer by using a readable fallback.

### Frontend Rendering

- Modify: `frontend/src/pages/GeneratedContentDetailPage.tsx`
  - Adds a real `handout` branch.
  - Delegates structured block rendering to focused components.

- Create: `frontend/src/features/generated-content/handout-renderer.tsx`
  - Renders handout overview, objectives, sections, and typed blocks.

- Create: `frontend/src/features/generated-content/handout-renderer.css`
  - Provides stable spacing, card-like formula/example/table/mindmap layout, responsive behavior, and overflow handling.

- Modify: `frontend/src/features/course-workspace/types.ts`
  - Adds TypeScript types for the v2 handout payload.

### Tests

- Modify: `backend/tests/modules/generation/test_handout_generator.py`
  - Tests prompt input mapping, v2 schema validation, formula/table/mindmap blocks, and citation validation.

- Modify: `backend/tests/modules/learning_execution/test_task_content_api.py`
  - Tests handout generation receives course/task/subtask/diagnostic strategy inputs.

- Modify: `backend/tests/modules/exports/test_exports_api.py`
  - Tests v2 handout PDF/Markdown rendering paths and safe citation display.

- Create or modify: `frontend/tests/pages/generated-content-detail.test.tsx`
  - Tests structured handout rendering on the details page.

### Documentation

- Modify: `docs/domains/study-mode/task-content.md`
  - Records v2 handout JSON, input mapping, prompt switching rules, render strategy, and failure behavior.

- Modify: `docs/api-data/frontend-integration.md`
  - Documents frontend contract for handout blocks and display rules.

- Modify: `docs/architecture/adr/index.md`
  - Add an ADR only if new frontend rendering dependencies are introduced.

- Create ADR if needed: `docs/architecture/adr/0007-structured-handout-rendering.md`
  - Required if adding KaTeX, Mermaid, Markmap, React Flow, or similar rendering dependencies.

---

## Task 1: Freeze The Handout v2 Contract

**Files:**
- Modify: `docs/domains/study-mode/task-content.md`
- Modify: `docs/api-data/frontend-integration.md`

- [ ] **Step 1: Write the contract section before code**

Add a `HandoutContent v2` section that defines the JSON shape and states that `content_json` remains authoritative.

Use this contract as the first draft:

```json
{
  "schema_version": 2,
  "title": "Nyquist 与 Shannon 公式讲义",
  "overview": "本讲义解决什么问题、适合什么学习目标。",
  "difficulty": "medium",
  "estimated_minutes": 40,
  "learning_objectives": [
    "区分带宽、码元速率和数据率",
    "计算 Nyquist 和 Shannon 公式题"
  ],
  "prerequisites": [
    {
      "id": "pre_1",
      "title": "对数基础",
      "explanation": "只补足 log2 在公式中的含义。",
      "example": "log2(8)=3 表示 2 的 3 次方等于 8。",
      "source_citation_ids": ["chunk_1"],
      "sort_order": 1
    }
  ],
  "sections": [
    {
      "id": "sec_1",
      "title": "信道容量与带宽",
      "lead": "先说结论：带宽限制信号能携带的信息变化速度。",
      "source_citation_ids": ["chunk_2"],
      "blocks": [
        {
          "type": "paragraph",
          "role": "definition",
          "text": "带宽是信道可通过的频率范围，单位是 Hz。",
          "source_citation_ids": ["chunk_2"]
        },
        {
          "type": "formula",
          "title": "Shannon 公式",
          "latex": "C = W \\log_2(1 + S/N)",
          "purpose": "估算有噪声信道的理论最大数据率。",
          "variables": [
            {"symbol": "C", "meaning": "最大数据率", "unit": "bps"},
            {"symbol": "W", "meaning": "信道带宽", "unit": "Hz"},
            {"symbol": "S/N", "meaning": "信噪比倍数，不是 dB", "unit": null}
          ],
          "conditions": ["有噪声信道"],
          "limitations": ["这是理论上限，不等于实际吞吐率"],
          "source_citation_ids": ["chunk_3"]
        }
      ],
      "key_points": ["Shannon 公式关注噪声，Nyquist 公式关注电平级数。"],
      "sort_order": 1
    }
  ],
  "knowledge_map": {
    "type": "mindmap",
    "title": "物理层知识关系",
    "root": {
      "label": "物理层",
      "children": [
        {"label": "信号与码元", "children": [{"label": "波特率", "children": []}]},
        {"label": "信道容量", "children": [{"label": "Nyquist", "children": []}, {"label": "Shannon", "children": []}]}
      ]
    },
    "source_citation_ids": ["chunk_2", "chunk_3"]
  },
  "formula_cards": [],
  "exam_focus": [],
  "self_check": [],
  "summary": "本节的核心是区分不同通信速率概念，并能按条件选公式。"
}
```

- [ ] **Step 2: Document block display rules**

Document these display rules:

- `formula` uses KaTeX-compatible LaTeX and frontend controls overflow.
- `table` uses structured `columns` and `rows`, not Markdown table text.
- `mindmap` uses a tree structure and can be rendered by Markmap or a custom tree component.
- `mermaid` is allowed only for flow or relationship diagrams and must have a title and explanation.
- `chart` is allowed only with source-supported numeric data.
- `svg` should not be introduced in the first implementation unless the rendering and security policy is explicit.
- HTML from model output is forbidden.

- [ ] **Step 3: Commit the contract docs**

Run:

```powershell
git status --short
git diff -- docs/domains/study-mode/task-content.md docs/api-data/frontend-integration.md
```

Expected: only the two documentation files changed.

Commit:

```powershell
git add docs/domains/study-mode/task-content.md docs/api-data/frontend-integration.md
git commit -m "docs: 明确讲义结构化内容契约"
```

## Task 2: Add Backend Schema Tests First

**Files:**
- Modify: `backend/tests/modules/generation/test_handout_generator.py`

- [ ] **Step 1: Add failing schema tests**

Add tests that describe the desired v2 structure before implementation:

```python
def test_handout_content_v2_accepts_structured_formula_and_mindmap_blocks() -> None:
    content = HandoutContent.model_validate(
        {
            "schema_version": 2,
            "title": "信道容量讲义",
            "overview": "围绕信道容量建立公式和直觉。",
            "difficulty": "medium",
            "estimated_minutes": 40,
            "learning_objectives": ["区分 Nyquist 和 Shannon 公式"],
            "prerequisites": [],
            "sections": [
                {
                    "id": "sec_1",
                    "title": "Shannon 公式",
                    "lead": "有噪声信道的容量由带宽和信噪比共同限制。",
                    "source_citation_ids": ["chunk_1"],
                    "blocks": [
                        {
                            "type": "formula",
                            "title": "Shannon 公式",
                            "latex": "C = W \\\\log_2(1 + S/N)",
                            "purpose": "计算理论最大数据率。",
                            "variables": [
                                {"symbol": "C", "meaning": "最大数据率", "unit": "bps"},
                                {"symbol": "W", "meaning": "带宽", "unit": "Hz"},
                            ],
                            "conditions": ["有噪声信道"],
                            "limitations": ["理论上限"],
                            "source_citation_ids": ["chunk_1"],
                        }
                    ],
                    "key_points": ["不要把 dB 直接代入 S/N。"],
                    "sort_order": 1,
                }
            ],
            "knowledge_map": {
                "type": "mindmap",
                "title": "关系图",
                "root": {"label": "信道容量", "children": []},
                "source_citation_ids": ["chunk_1"],
            },
            "formula_cards": [],
            "exam_focus": [],
            "self_check": [],
            "summary": "按条件选公式。",
        }
    )

    assert content.schema_version == 2
    assert content.sections[0].blocks[0].type == "formula"
```

- [ ] **Step 2: Add validation tests for bad layout data**

Add tests for invalid table size, empty LaTeX, and forged citations:

```python
def test_handout_content_v2_rejects_empty_formula_latex() -> None:
    payload = _valid_handout_v2_payload()
    payload["sections"][0]["blocks"][0]["latex"] = ""

    with pytest.raises(ValidationError):
        HandoutContent.model_validate(payload)
```

- [ ] **Step 3: Run tests to confirm failure**

Run:

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py -q
```

Expected: tests fail because current schema has no v2 fields or typed blocks.

## Task 3: Implement Handout v2 Pydantic Schema

**Files:**
- Modify: `backend/app/modules/generation/generators/handout/schemas.py`
- Modify: `backend/tests/modules/generation/test_handout_generator.py`

- [ ] **Step 1: Add block models**

Implement focused models like this:

```python
class CitationBoundModel(BaseModel):
    source_citation_ids: list[str] = Field(min_length=1, max_length=4)

    @field_validator("source_citation_ids")
    @classmethod
    def _citation_ids_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("source_citation_ids must contain non-empty strings")
        return list(dict.fromkeys(value))


class FormulaVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    meaning: str = Field(min_length=1)
    unit: str | None = None


class FormulaBlock(CitationBoundModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["formula"] = "formula"
    title: str = Field(min_length=1)
    latex: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    variables: list[FormulaVariable] = Field(min_length=1)
    conditions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Add non-formula block models**

Add these models with `extra="forbid"`:

```python
class ParagraphBlock(CitationBoundModel):
    type: Literal["paragraph"] = "paragraph"
    role: Literal["lead", "definition", "intuition", "why", "process", "summary"] = "definition"
    text: str = Field(min_length=1)


class ExampleBlock(CitationBoundModel):
    type: Literal["example"] = "example"
    title: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class TableBlock(CitationBoundModel):
    type: Literal["table"] = "table"
    title: str = Field(min_length=1)
    columns: list[str] = Field(min_length=2, max_length=6)
    rows: list[list[str]] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _row_width_matches_columns(self) -> "TableBlock":
        width = len(self.columns)
        if any(len(row) != width for row in self.rows):
            raise ValueError("table rows must match column count")
        return self
```

- [ ] **Step 3: Add diagram and assessment models**

Add `MindmapBlock`, `MermaidBlock`, `ChartBlock`, `MistakeBlock`, `CalloutBlock`, and `SelfCheckItem`. Keep SVG out of v2 unless an ADR explicitly adds it.

- [ ] **Step 4: Replace `HandoutSection` and `HandoutContent`**

Use a discriminated union for `blocks`:

```python
HandoutBlock = Annotated[
    ParagraphBlock | FormulaBlock | ExampleBlock | TableBlock | MindmapBlock | MermaidBlock | ChartBlock | MistakeBlock | CalloutBlock,
    Field(discriminator="type"),
]


class HandoutSection(CitationBoundModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    lead: str = Field(min_length=1)
    blocks: list[HandoutBlock] = Field(min_length=1, max_length=16)
    key_points: list[str] = Field(min_length=1, max_length=8)
    sort_order: int = Field(ge=1)


class HandoutContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2] = 2
    title: str = Field(min_length=1, max_length=255)
    overview: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    estimated_minutes: int | None = Field(default=None, ge=1, le=480)
    learning_objectives: list[str] = Field(min_length=1, max_length=8)
    prerequisites: list[PrerequisiteItem] = Field(default_factory=list)
    sections: list[HandoutSection] = Field(min_length=1, max_length=12)
    knowledge_map: MindmapBlock | MermaidBlock | None = None
    formula_cards: list[FormulaBlock] = Field(default_factory=list, max_length=12)
    exam_focus: list[ExamFocusItem] = Field(default_factory=list)
    self_check: list[SelfCheckItem] = Field(default_factory=list, max_length=20)
    summary: str = Field(min_length=1)
```

- [ ] **Step 5: Run schema tests**

Run:

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py -q
```

Expected: schema tests pass, generator tests may still fail until prompt/output fixtures are updated.

- [ ] **Step 6: Commit schema and tests**

```powershell
git add backend/app/modules/generation/generators/handout/schemas.py backend/tests/modules/generation/test_handout_generator.py
git commit -m "feat: 定义结构化讲义内容契约"
```

## Task 4: Enrich Handout Model Inputs

**Files:**
- Modify: `backend/app/modules/generation/generators/handout/schemas.py`
- Modify: `backend/app/modules/learning_execution/service.py`
- Modify: `backend/tests/modules/learning_execution/test_task_content_api.py`
- Modify: `backend/tests/modules/generation/test_handout_generator.py`

- [ ] **Step 1: Rename and expand generation parameters**

Replace the user-facing style field with clearer internal inputs:

```python
class HandoutGenerationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = "zh-CN"
    content_depth: Literal["concise", "standard", "detailed"] = "standard"
    example_intensity: Literal["low", "standard", "high"] = "standard"
    assessment_intensity: Literal["low", "standard", "high"] = "standard"
    review_intensity: Literal["low", "standard", "high"] = "standard"
    course_name: str | None = None
    plan_goal: str | None = None
    task_title: str | None = None
    subtask_title: str | None = None
    subtask_type: Literal["learn", "review"] | None = None
    subtask_description: str | None = None
    estimated_minutes: int | None = None
    diagnostic_foundation_needed: bool | None = None
    diagnostic_weak_area: Literal["concept", "calculation", "application", "memorization", "other"] | None = None
    diagnostic_weak_topics: list[str] = Field(default_factory=list)
    diagnostic_note: str | None = None
    teaching_strategy_hint: str | None = None
```

- [ ] **Step 2: Map existing planner fields into handout inputs**

Update `_handout_task_context_parameters()`:

```python
def _handout_task_context_parameters(target: repository.ExecutionTarget) -> dict[str, object]:
    diagnostic_profile = _stored_diagnostic_profile(target)
    planner_strategy = _stored_planner_strategy(target)
    return {
        "course_name": target.course.name,
        "plan_goal": target.plan.goal_text or "",
        "task_title": target.task.title,
        "subtask_title": target.subtask.title,
        "subtask_type": target.subtask.subtask_type,
        "subtask_description": target.subtask.description or "",
        "estimated_minutes": _stored_subtask_estimated_minutes(target),
        "content_depth": _content_depth_for_handout(planner_strategy),
        "example_intensity": _intensity_for_handout(planner_strategy, "example_intensity"),
        "assessment_intensity": _intensity_for_handout(planner_strategy, "assessment_intensity"),
        "review_intensity": _intensity_for_handout(planner_strategy, "review_intensity"),
        "diagnostic_foundation_needed": diagnostic_profile.get("foundation_needed"),
        "diagnostic_weak_area": diagnostic_profile.get("weak_area"),
        "diagnostic_weak_topics": diagnostic_profile.get("weak_topics") if isinstance(diagnostic_profile.get("weak_topics"), list) else [],
        "diagnostic_note": diagnostic_profile.get("diagnostic_note") if isinstance(diagnostic_profile.get("diagnostic_note"), str) else None,
        "teaching_strategy_hint": _teaching_strategy_hint(diagnostic_profile.get("weak_area")),
    }
```

- [ ] **Step 3: Add helper functions**

Add helpers that read from `parsed_config_json.generation_metadata.planner_strategy`, `confirmed_config`, and `task_snapshot`.

```python
def _teaching_strategy_hint(weak_area: object) -> str:
    return {
        "concept": "加强概念边界、直觉解释和相似概念对比。",
        "calculation": "加强公式变量、单位、适用条件、代入步骤和计算例题。",
        "application": "加强场景例子、输入输出、实际应用和迁移题。",
        "memorization": "加强核心结论、易错判断、口诀式总结和快速自测。",
    }.get(str(weak_area), "保持清晰、专业、耐心的一对一讲解风格。")
```

- [ ] **Step 4: Test input mapping**

Add a test provider that captures the prompt and assert it includes:

- course name;
- task title;
- subtask type;
- estimated minutes when present;
- `weak_area` but not user-facing `diagnostic_explanation_style`;
- content/example/assessment/review intensities.

- [ ] **Step 5: Run targeted tests**

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py tests/modules/learning_execution/test_task_content_api.py -q
```

Expected: pass.

- [ ] **Step 6: Commit input enrichment**

```powershell
git add backend/app/modules/generation/generators/handout/schemas.py backend/app/modules/learning_execution/service.py backend/tests/modules/generation/test_handout_generator.py backend/tests/modules/learning_execution/test_task_content_api.py
git commit -m "feat: 丰富讲义生成模型输入"
```

## Task 5: Rewrite The Handout Prompt Around The Reference Prompt

**Files:**
- Modify: `backend/app/modules/generation/generators/handout/generator.py`
- Modify: `backend/tests/modules/generation/test_handout_generator.py`

- [ ] **Step 1: Replace the short prompt with structured sections**

Update `_build_prompt()` so it has these sections:

1. role and task;
2. input context;
3. mode switching rules;
4. internal planning requirements from the reference prompt;
5. output schema requirements;
6. block rules for formulas/tables/mindmaps/charts;
7. citation rules;
8. material chunks.

The prompt should include this wording:

```text
你的任务不是简单总结资料，而是根据课程资料、学习目标、二级任务类型、学习时间和学生诊断，生成可在网页中稳定渲染的结构化个性化讲义。

不要输出完整 Markdown 文档。
不要输出 HTML。
只输出符合 HandoutContent schema 的 JSON 对象。
```

- [ ] **Step 2: Add mode switching rules**

Include:

```text
模式规则：
- subtask_type=learn：优先讲清新知识，顺序为先说结论 -> 精确定义 -> 直觉理解 -> 为什么需要 -> 公式/步骤 -> 例子 -> 易错点。
- subtask_type=review：优先帮助回顾和查漏，增加对比表、公式卡片、易错点、知识关系图和自测。
- content_depth=concise：减少背景扩展，每个核心知识点保留定义、核心原理和至多 1 个基础例子。
- content_depth=standard：完整解释定义、原理、例子、易错点，对核心公式给出必要推导。
- content_depth=detailed：增加边界条件、反例、综合应用和容易被教材省略的中间步骤。
- weak_area=calculation：公式必须说明用途、变量、单位、适用条件、限制条件，并给出代入步骤。
- weak_area=concept：加强概念边界、直觉解释和相似概念对比。
- weak_area=application：加强场景、输入输出、系统作用和迁移例题。
- weak_area=memorization：加强核心结论卡片、易错判断和快速自测。
```

- [ ] **Step 3: Add block rules**

Include:

```text
排版与块规则：
- 数学公式必须放入 type=formula block，latex 必须是 KaTeX 兼容字符串。
- 对比内容必须放入 type=table block，最多 6 列、12 行。
- 知识关系优先使用 knowledge_map 的 mindmap tree，不要把思维导图写成普通段落。
- Mermaid 只用于流程、顺序或关系图；必须提供 title、code、explanation。
- Chart 只在资料提供真实数值时生成，不得编造数据。
- 不生成 SVG，除非输入资料明确要求且系统 schema 支持。
- 每个 block 需要 source_citation_ids，必须来自输入 chunk_id。
```

- [ ] **Step 4: Update prompt tests**

Assert the prompt contains:

- reference-derived teaching rules;
- formula/table/mindmap/chart rules;
- no HTML output;
- JSON-only output;
- citation constraints.

- [ ] **Step 5: Run prompt tests**

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py -q
```

Expected: pass.

- [ ] **Step 6: Commit prompt rewrite**

```powershell
git add backend/app/modules/generation/generators/handout/generator.py backend/tests/modules/generation/test_handout_generator.py
git commit -m "feat: 升级讲义生成提示词"
```

## Task 6: Preserve Citation Binding And Multi-Batch Reduction

**Files:**
- Modify: `backend/app/modules/learning_execution/service.py`
- Modify: `backend/tests/modules/learning_execution/test_task_content_api.py`
- Modify: `backend/tests/integration/test_task_content_generation_flow.py`

- [ ] **Step 1: Update citation collection for nested blocks**

Ensure `_collect_content_item_ids()` and `_bind_source_citation_ids()` still walk nested blocks, formula cards, knowledge maps, and self-check items.

If a block has an `id`, bind by block id. If it does not, bind by its parent section. Keep section-level citations as fallback.

- [ ] **Step 2: Update handout reducer**

When multiple batches produce multiple v2 handouts:

- preserve `schema_version=2`;
- merge unique learning objectives;
- append sections in stable order;
- rewrite section ids to `sec_N`;
- preserve nested blocks;
- collect formula cards without duplicates by `latex`;
- keep the first valid `knowledge_map` or synthesize a shallow map from final sections;
- keep summary from the last output or compose a short deterministic summary.

- [ ] **Step 3: Add tests for section/block citation binding**

Test that after persistence:

- section `source_citation_ids` become `cit_...`;
- block `source_citation_ids` become `cit_...`;
- no output still contains raw `chunk_...` citation ids.

- [ ] **Step 4: Run integration tests**

```powershell
cd backend
uv run pytest tests/modules/learning_execution/test_task_content_api.py tests/integration/test_task_content_generation_flow.py -q
```

Expected: pass.

- [ ] **Step 5: Commit citation/reducer work**

```powershell
git add backend/app/modules/learning_execution/service.py backend/tests/modules/learning_execution/test_task_content_api.py backend/tests/integration/test_task_content_generation_flow.py
git commit -m "feat: 支持结构化讲义引用绑定"
```

## Task 7: Update Export Rendering For v2 Handouts

**Files:**
- Modify: `backend/app/modules/exports/renderer.py`
- Modify: `backend/tests/modules/exports/test_exports_api.py`

- [ ] **Step 1: Add a v2-to-Markdown rendering function**

Implement a function like:

```python
def _render_handout_v2_markdown(
    title: str,
    handout: HandoutContent,
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> str:
    lines = [f"# {title}", "", handout.overview, ""]
    lines.extend(["## 学习目标", ""])
    for objective in handout.learning_objectives:
        lines.append(f"- {objective}")
    for section in sorted(handout.sections, key=lambda item: item.sort_order):
        lines.extend(["", f"## {section.title}", "", section.lead, ""])
        for block in section.blocks:
            lines.extend(_render_handout_block_markdown(block, citations_by_id))
    lines.extend(["", "## 总结", "", handout.summary])
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 2: Render formulas, examples, tables, and diagrams**

Use these fallback rules:

- `formula`: render title, `$$latex$$`, variables, conditions, limitations.
- `example`: render problem, ordered steps, answer, explanation.
- `table`: render Markdown table.
- `mindmap`: render a nested bullet tree for PDF fallback.
- `mermaid`: render a fenced `mermaid` block for Markdown/HTML; for PDF, show code plus explanation unless Mermaid rendering is implemented.
- `chart`: render a compact table fallback unless a chart renderer is added.

- [ ] **Step 3: Keep citation snippets safe**

Continue using the safe citation display rules already present in `renderer.py`; do not expose parser residue in user-visible PDF.

- [ ] **Step 4: Add export tests**

Test:

- formula appears as `$$...$$`;
- table renders with correct columns;
- mindmap fallback renders nested bullets;
- unsafe citation snippets are hidden;
- malformed v2 content returns `EXPORT_CONTENT_INVALID`.

- [ ] **Step 5: Run export tests**

```powershell
cd backend
uv run pytest tests/modules/exports/test_exports_api.py -q
```

Expected: pass.

- [ ] **Step 6: Commit export support**

```powershell
git add backend/app/modules/exports/renderer.py backend/tests/modules/exports/test_exports_api.py
git commit -m "feat: 支持结构化讲义导出"
```

## Task 8: Build Frontend Structured Handout Renderer

**Files:**
- Create: `frontend/src/features/generated-content/handout-renderer.tsx`
- Create: `frontend/src/features/generated-content/handout-renderer.css`
- Modify: `frontend/src/pages/GeneratedContentDetailPage.tsx`
- Modify: `frontend/src/features/course-workspace/types.ts`
- Modify: `frontend/tests/pages/generated-content-detail.test.tsx`
- Optional if adding dependencies: `docs/architecture/adr/0007-structured-handout-rendering.md`

- [ ] **Step 1: Decide dependency scope**

Use existing dependencies where possible. If adding `katex`, `mermaid`, `markmap-lib`, `markmap-view`, or chart libraries, write an ADR first and get dependency installation approved when executing.

Minimum dependency-light implementation:

- formulas: render LaTeX text in a styled formula card first, then add KaTeX in a later task if dependency approval is needed;
- mindmap: render as a styled collapsible tree first;
- Mermaid: render as code fallback first.

- [ ] **Step 2: Add TypeScript types**

Add handout v2 types:

```ts
export interface HandoutContentV2 {
  schema_version: 2;
  title: string;
  overview: string;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number | null;
  learning_objectives: string[];
  prerequisites: HandoutPrerequisite[];
  sections: HandoutSectionV2[];
  knowledge_map: HandoutMindmapBlock | HandoutMermaidBlock | null;
  formula_cards: HandoutFormulaBlock[];
  exam_focus: unknown[];
  self_check: HandoutSelfCheckItem[];
  summary: string;
}
```

- [ ] **Step 3: Create renderer components**

Implement:

```tsx
export function HandoutRenderer({ content }: { content: HandoutContentV2 }) {
  return (
    <Stack className="handout-renderer" gap="lg">
      <HandoutHeader content={content} />
      <HandoutObjectives objectives={content.learning_objectives} />
      {content.knowledge_map ? <HandoutBlock block={content.knowledge_map} /> : null}
      {content.sections.map((section) => (
        <HandoutSectionView key={section.id} section={section} />
      ))}
      <HandoutSummary summary={content.summary} />
    </Stack>
  );
}
```

- [ ] **Step 4: Implement block renderer**

Implement a switch:

```tsx
function HandoutBlock({ block }: { block: HandoutBlock }) {
  switch (block.type) {
    case "paragraph":
      return <Text className={`handout-paragraph handout-paragraph-${block.role}`}>{block.text}</Text>;
    case "formula":
      return <FormulaCard block={block} />;
    case "example":
      return <ExampleCard block={block} />;
    case "table":
      return <ComparisonTable block={block} />;
    case "mindmap":
      return <MindmapTree block={block} />;
    case "mermaid":
      return <DiagramFallback block={block} />;
    case "chart":
      return <ChartFallback block={block} />;
    case "mistake":
      return <MistakeCard block={block} />;
    case "callout":
      return <CalloutCard block={block} />;
    default:
      return null;
  }
}
```

- [ ] **Step 5: Add visual CSS constraints**

In CSS:

- formula cards have horizontal overflow rather than breaking layout;
- tables use `overflow-x: auto`;
- mindmap tree has nested indentation and connecting borders;
- examples and mistakes use different visual emphasis;
- mobile layout is single-column.

- [ ] **Step 6: Connect details page**

In `GeneratedContentDetailPage.tsx`, detect:

```tsx
if (content.content_type === "handout" && isHandoutContentV2(content.content_json)) {
  return <HandoutRenderer content={content.content_json} />;
}
```

- [ ] **Step 7: Add frontend tests**

Test:

- handout overview renders;
- formula block renders title and LaTeX;
- table block renders rows;
- mindmap block renders nested labels;
- unknown or old handout falls back safely.

- [ ] **Step 8: Run frontend tests**

```powershell
cd frontend
pnpm test -- --run generated-content-detail
pnpm build
```

Expected: tests pass and build succeeds.

- [ ] **Step 9: Commit frontend renderer**

```powershell
git add frontend/src/features/generated-content/handout-renderer.tsx frontend/src/features/generated-content/handout-renderer.css frontend/src/pages/GeneratedContentDetailPage.tsx frontend/src/features/course-workspace/types.ts frontend/tests/pages/generated-content-detail.test.tsx
git commit -m "feat: 展示结构化讲义内容"
```

## Task 9: Full Prompt And Rendering Validation

**Files:**
- Modify: `backend/tests/integration/test_task_content_generation_flow.py`
- Modify if needed: `backend/scripts/validate_study_mode_real_fixes.py`

- [ ] **Step 1: Add an end-to-end mock generation fixture**

Create a mock handout v2 output that includes:

- one formula block;
- one table block;
- one mindmap block;
- one example block;
- one mistake block;
- valid citations.

- [ ] **Step 2: Test API response**

Assert `POST /study-subtasks/{id}/handouts` returns:

- `content_type=handout`;
- `content_json.schema_version=2`;
- structured blocks;
- `source_citations` not empty;
- no raw `chunk_...` citation IDs after persistence.

- [ ] **Step 3: Test execution context still works**

Assert `GET /study-subtasks/{id}/execution-context` returns the latest successful `handout_content_id`.

- [ ] **Step 4: Test export still works**

Assert `GET /generated-contents/{id}/exports/pdf` returns `application/pdf`.

- [ ] **Step 5: Run backend targeted suite**

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py tests/modules/learning_execution/test_task_content_api.py tests/modules/exports/test_exports_api.py tests/integration/test_task_content_generation_flow.py -q
```

Expected: pass.

- [ ] **Step 6: Commit validation coverage**

```powershell
git add backend/tests/integration/test_task_content_generation_flow.py backend/scripts/validate_study_mode_real_fixes.py
git commit -m "test: 覆盖结构化讲义生成链路"
```

## Task 10: Documentation And Final Verification

**Files:**
- Modify: `docs/domains/study-mode/task-content.md`
- Modify: `docs/api-data/frontend-integration.md`
- Modify: `docs/planning/current-state.md`
- Modify: `docs/architecture/adr/index.md` and ADR file if dependencies were added

- [ ] **Step 1: Update domain docs**

Record:

- v2 schema;
- model inputs;
- prompt switching rules;
- rendering responsibility split;
- citation validation and rebinding;
- PDF fallback behavior.

- [ ] **Step 2: Update frontend integration docs**

Record:

- block type list;
- frontend display rules;
- safe fallback behavior;
- formula/table/mindmap rendering expectations.

- [ ] **Step 3: Run final verification**

Run:

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py tests/modules/learning_execution/test_task_content_api.py tests/modules/exports/test_exports_api.py tests/integration/test_task_content_generation_flow.py -q
cd ../frontend
pnpm test -- --run generated-content-detail
pnpm build
cd ..
git diff --check
```

Expected:

- backend targeted tests pass;
- frontend targeted tests pass;
- frontend build passes;
- `git diff --check` reports no whitespace errors.

- [ ] **Step 4: Commit docs and final fixes**

```powershell
git add docs/domains/study-mode/task-content.md docs/api-data/frontend-integration.md docs/planning/current-state.md docs/architecture/adr/index.md docs/architecture/adr/0007-structured-handout-rendering.md
git commit -m "docs: 更新结构化讲义实现说明"
```

## Completion Criteria

- The model outputs validated structured JSON, not a free-form Markdown document.
- Formula, table, mindmap, chart, example, mistake, and self-check content use typed blocks.
- Frontend rendering controls layout, spacing, overflow, and responsive behavior.
- Model inputs and prompt rules explicitly switch by `subtask_type`, content depth, intensity fields, and `weak_area`.
- The reference prompt's teaching design requirements are represented in prompt rules and schema fields.
- `diagnostic_explanation_style` is no longer treated as a user-facing handout input.
- Existing handout generation, detail response, execution context, and PDF export remain functional.
- Tests cover schema, prompt, citation binding, export, and frontend rendering.

## Execution Notes

- Do not push without explicit user instruction.
- If frontend dependencies are needed, request approval before installing packages.
- If a dependency becomes core to formula/diagram rendering, write an ADR before code that relies on it.
- Each task should be committed separately after its verification command passes.
- If the model cannot reliably satisfy the full v2 schema in one call, add a retry/repair task only after collecting failing outputs; do not silently accept partial malformed handouts.
