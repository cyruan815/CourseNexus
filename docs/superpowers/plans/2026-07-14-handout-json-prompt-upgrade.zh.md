# 讲义 JSON 与 Prompt 升级实施计划

> **给后续 Agent / 开发者：** 实施本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，并逐任务执行。所有步骤使用 checkbox（`- [ ]`）跟踪。

**目标：** 升级 Study Mode 的讲义生成能力，让模型输出结构化 JSON 教学讲义，使公式、图表、思维导图、关系图、例题和引用都能被前端组件稳定、美观地渲染，并能安全导出。

**架构：** 继续以 `ai_generated_contents.content_json` 作为讲义的权威持久化内容。模型输出经过 Pydantic 校验的结构化 schema，内容由 typed blocks 表达；Markdown 只允许出现在受控文本字段中，公式、表格、图表、思维导图和关系图都使用专门结构化块。Prompt 规则吸收用户提供的参考 prompt，但要适配 CourseNexus 当前字段、任务模式、诊断结果、planner 策略和引用约束。

**技术栈：** Python + FastAPI + Pydantic structured outputs、SQLAlchemy JSON 持久化、React + TypeScript 前端渲染、KaTeX 兼容 LaTeX 字符串、Mermaid/Markmap-ready 结构化图数据、pytest/Vitest。

---

## 必读上下文

实施前必须按顺序阅读这些文件：

1. `docs/index.md`
2. `C:\Users\50754\.codex\attachments\0ec10419-7ce0-463e-990d-fddb5429b83d\pasted-text.txt`
3. `docs/domains/study-mode/task-content.md`
4. `docs/domains/study-mode/diagnostic-questions.md`
5. `backend/app/modules/generation/generators/handout/schemas.py`
6. `backend/app/modules/generation/generators/handout/generator.py`
7. `backend/app/modules/learning_execution/service.py`
8. `backend/app/modules/exports/renderer.py`
9. `frontend/src/pages/GeneratedContentDetailPage.tsx`

用户提供的参考 prompt 是高质量教学设计参考，尤其值得吸收其中的教学结构、公式规范、图表规范、引用规范和自测题规则。但不能照搬成“只输出整篇 Markdown”的 prompt。CourseNexus 应该保留结构化 JSON 契约，同时吸收其中的教学要求。

当前重要不一致点：

- `diagnostic_explanation_style` 仍存在于 `HandoutGenerationParameters`，并由 `learning_execution.service` 注入。
- Study Mode 诊断 v2 已明确：用户不再选择“讲课风格”，前端只询问 `weak_area`。
- `explanation_style` 可以继续作为后端内部派生提示存在，但 handout prompt 不能把它当作用户侧字段。优先改为 `teaching_strategy_hint`，或直接从 `weak_area` 派生规则。

## 目标结果

生成出的讲义应该支持以下内容的稳定渲染：

- 公式：通过结构化 `formula` block 和 KaTeX 兼容 LaTeX；
- 对比表：通过有边界限制的 `table` block；
- 知识关系图：通过 `mermaid` 或 `mindmap` block；
- 数值图表：只有资料中存在真实数值数据时，才通过 `chart` block 输出；
- 例题：通过 `example` block；
- 易错点：通过 `mistake` 或 `callout` block；
- 引用：section/block 的 `source_citation_ids` 在持久化前只能引用输入 chunk id，持久化后绑定为 `SourceCitation.id`。

模型应该收到明确的任务模式、学习目标、时间 / 深度控制、诊断结果和资料 chunks。Prompt 应根据 `subtask_type`、`content_depth`、`example_intensity`、`assessment_intensity`、`review_intensity` 和 `weak_area` 切换教学侧重点。

## 文件结构

### 后端契约

- 修改：`backend/app/modules/generation/generators/handout/schemas.py`
  - 负责 `HandoutContent` v2 Pydantic schema。
  - 定义 typed block model，例如 `ParagraphBlock`、`FormulaBlock`、`ExampleBlock`、`TableBlock`、`MermaidBlock`、`MindmapBlock`、`ChartBlock`、`CalloutBlock`、`SelfCheckBlock`。
  - 约束 block 数量、非空文本、表格尺寸、允许的 block 类型和引用列表。

- 修改：`backend/app/modules/generation/generators/handout/generator.py`
  - 构建升级后的 prompt。
  - 将 CourseNexus 的输入映射到参考 prompt 中的概念。
  - 调用 `ModelProvider.generate_structured(..., output_schema=HandoutContent)`。
  - 校验引用 chunk id 和内容质量约束。

- 修改：`backend/app/modules/learning_execution/service.py`
  - 从 course/task/plan/subtask 上下文丰富 handout 参数。
  - 将用户侧 `diagnostic_explanation_style` 命名替换为内部策略字段。
  - 如果 `parsed_config_json` 中存在 planner strategy，则传入相关策略值。

- 修改：`backend/app/modules/exports/renderer.py`
  - 将 v2 handout JSON 渲染为 Markdown/HTML/PDF。
  - 即使交互式图表暂时没有 PDF renderer，也要通过可读 fallback 保持 PDF 导出可用。

### 前端渲染

- 修改：`frontend/src/pages/GeneratedContentDetailPage.tsx`
  - 增加真正的 `handout` 展示分支。
  - 将结构化 block 渲染委托给专门组件。

- 新建：`frontend/src/features/generated-content/handout-renderer.tsx`
  - 渲染讲义 overview、objectives、sections 和 typed blocks。

- 新建：`frontend/src/features/generated-content/handout-renderer.css`
  - 提供稳定间距、公式 / 例题 / 表格 / 思维导图卡片布局、响应式行为和溢出处理。

- 修改：`frontend/src/features/course-workspace/types.ts`
  - 增加 v2 handout payload 的 TypeScript 类型。

### 测试

- 修改：`backend/tests/modules/generation/test_handout_generator.py`
  - 测试 prompt 输入映射、v2 schema 校验、公式 / 表格 / 思维导图 blocks、引用校验。

- 修改：`backend/tests/modules/learning_execution/test_task_content_api.py`
  - 测试 handout 生成能收到 course/task/subtask/diagnostic strategy 输入。

- 修改：`backend/tests/modules/exports/test_exports_api.py`
  - 测试 v2 handout PDF/Markdown 渲染路径和安全引用展示。

- 新建或修改：`frontend/tests/pages/generated-content-detail.test.tsx`
  - 测试详情页结构化 handout 渲染。

### 文档

- 修改：`docs/domains/study-mode/task-content.md`
  - 记录 v2 handout JSON、输入映射、prompt 切换规则、渲染策略和失败行为。

- 修改：`docs/api-data/frontend-integration.md`
  - 记录前端 handout blocks 契约和展示规则。

- 修改：`docs/architecture/adr/index.md`
  - 仅当引入新的前端渲染依赖时，新增 ADR。

- 如有需要新建 ADR：`docs/architecture/adr/0007-structured-handout-rendering.md`
  - 如果引入 KaTeX、Mermaid、Markmap、React Flow 或类似渲染依赖，则必须新增。

---

## 任务 1：冻结 Handout v2 契约

**文件：**
- 修改：`docs/domains/study-mode/task-content.md`
- 修改：`docs/api-data/frontend-integration.md`

- [ ] **步骤 1：先写契约文档，再写代码**

新增 `HandoutContent v2` 小节，定义 JSON 形状，并说明 `content_json` 仍是权威数据。

第一版契约使用：

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

- [ ] **步骤 2：记录 block 展示规则**

记录以下展示规则：

- `formula` 使用 KaTeX 兼容 LaTeX，前端负责控制溢出。
- `table` 使用结构化 `columns` 和 `rows`，不使用 Markdown 表格文本作为权威数据。
- `mindmap` 使用树结构，可由 Markmap 或自定义树组件渲染。
- `mermaid` 只允许用于流程、顺序或关系图，必须有标题和解释。
- `chart` 只有在资料中存在可支持的真实数值数据时才允许输出。
- 第一阶段不要引入 `svg`，除非渲染和安全策略已经明确。
- 禁止模型输出 HTML。

- [ ] **步骤 3：提交契约文档**

运行：

```powershell
git status --short
git diff -- docs/domains/study-mode/task-content.md docs/api-data/frontend-integration.md
```

预期：只有这两个文档文件发生变化。

提交：

```powershell
git add docs/domains/study-mode/task-content.md docs/api-data/frontend-integration.md
git commit -m "docs: 明确讲义结构化内容契约"
```

## 任务 2：先补后端 schema 测试

**文件：**
- 修改：`backend/tests/modules/generation/test_handout_generator.py`

- [ ] **步骤 1：新增失败的 schema 测试**

先写测试描述期望的 v2 结构：

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

- [ ] **步骤 2：新增坏排版数据校验测试**

增加非法表格尺寸、空 LaTeX、伪造引用等测试：

```python
def test_handout_content_v2_rejects_empty_formula_latex() -> None:
    payload = _valid_handout_v2_payload()
    payload["sections"][0]["blocks"][0]["latex"] = ""

    with pytest.raises(ValidationError):
        HandoutContent.model_validate(payload)
```

- [ ] **步骤 3：运行测试确认失败**

运行：

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py -q
```

预期：测试失败，因为当前 schema 还没有 v2 字段和 typed blocks。

## 任务 3：实现 Handout v2 Pydantic Schema

**文件：**
- 修改：`backend/app/modules/generation/generators/handout/schemas.py`
- 修改：`backend/tests/modules/generation/test_handout_generator.py`

- [ ] **步骤 1：新增 block models**

实现类似下面的聚焦模型：

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

- [ ] **步骤 2：新增非公式 block models**

添加以下 `extra="forbid"` 的模型：

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

- [ ] **步骤 3：新增图示和测验模型**

添加 `MindmapBlock`、`MermaidBlock`、`ChartBlock`、`MistakeBlock`、`CalloutBlock` 和 `SelfCheckItem`。除非 ADR 明确允许，否则 v2 不加入 SVG。

- [ ] **步骤 4：替换 `HandoutSection` 和 `HandoutContent`**

为 `blocks` 使用 discriminated union：

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

- [ ] **步骤 5：运行 schema 测试**

运行：

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py -q
```

预期：schema 测试通过，generator 测试可能仍会失败，直到 prompt 和输出 fixture 被更新。

- [ ] **步骤 6：提交 schema 和测试**

```powershell
git add backend/app/modules/generation/generators/handout/schemas.py backend/tests/modules/generation/test_handout_generator.py
git commit -m "feat: 定义结构化讲义内容契约"
```

## 任务 4：丰富讲义模型输入

**文件：**
- 修改：`backend/app/modules/generation/generators/handout/schemas.py`
- 修改：`backend/app/modules/learning_execution/service.py`
- 修改：`backend/tests/modules/learning_execution/test_task_content_api.py`
- 修改：`backend/tests/modules/generation/test_handout_generator.py`

- [ ] **步骤 1：重命名并扩展生成参数**

将用户侧风格字段替换为更清晰的内部输入：

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

- [ ] **步骤 2：将现有 planner 字段映射到 handout 输入**

更新 `_handout_task_context_parameters()`：

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

- [ ] **步骤 3：新增 helper 函数**

新增 helper，从 `parsed_config_json.generation_metadata.planner_strategy`、`confirmed_config` 和 `task_snapshot` 读取信息。

```python
def _teaching_strategy_hint(weak_area: object) -> str:
    return {
        "concept": "加强概念边界、直觉解释和相似概念对比。",
        "calculation": "加强公式变量、单位、适用条件、代入步骤和计算例题。",
        "application": "加强场景例子、输入输出、实际应用和迁移题。",
        "memorization": "加强核心结论、易错判断、口诀式总结和快速自测。",
    }.get(str(weak_area), "保持清晰、专业、耐心的一对一讲解风格。")
```

- [ ] **步骤 4：测试输入映射**

添加一个会捕获 prompt 的 test provider，并断言 prompt 包含：

- 课程名称；
- 一级任务标题；
- 二级任务类型；
- 有值时的预计分钟数；
- `weak_area`，但不出现用户侧 `diagnostic_explanation_style`；
- content/example/assessment/review 强度。

- [ ] **步骤 5：运行目标测试**

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py tests/modules/learning_execution/test_task_content_api.py -q
```

预期：通过。

- [ ] **步骤 6：提交输入增强**

```powershell
git add backend/app/modules/generation/generators/handout/schemas.py backend/app/modules/learning_execution/service.py backend/tests/modules/generation/test_handout_generator.py backend/tests/modules/learning_execution/test_task_content_api.py
git commit -m "feat: 丰富讲义生成模型输入"
```

## 任务 5：围绕参考 prompt 重写讲义 prompt

**文件：**
- 修改：`backend/app/modules/generation/generators/handout/generator.py`
- 修改：`backend/tests/modules/generation/test_handout_generator.py`

- [ ] **步骤 1：用结构化段落替换当前短 prompt**

更新 `_build_prompt()`，使它包含这些部分：

1. 角色和任务；
2. 输入上下文；
3. 模式切换规则；
4. 来自参考 prompt 的内部规划要求；
5. 输出 schema 要求；
6. 公式 / 表格 / 思维导图 / 图表 block 规则；
7. 引用规则；
8. 资料 chunks。

Prompt 应包含这段话：

```text
你的任务不是简单总结资料，而是根据课程资料、学习目标、二级任务类型、学习时间和学生诊断，生成可在网页中稳定渲染的结构化个性化讲义。

不要输出完整 Markdown 文档。
不要输出 HTML。
只输出符合 HandoutContent schema 的 JSON 对象。
```

- [ ] **步骤 2：加入模式切换规则**

包含：

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

- [ ] **步骤 3：加入 block 规则**

包含：

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

- [ ] **步骤 4：更新 prompt 测试**

断言 prompt 包含：

- 来自参考 prompt 的教学规则；
- 公式 / 表格 / 思维导图 / chart 规则；
- 禁止 HTML 输出；
- 只允许 JSON 输出；
- 引用约束。

- [ ] **步骤 5：运行 prompt 测试**

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py -q
```

预期：通过。

- [ ] **步骤 6：提交 prompt 重写**

```powershell
git add backend/app/modules/generation/generators/handout/generator.py backend/tests/modules/generation/test_handout_generator.py
git commit -m "feat: 升级讲义生成提示词"
```

## 任务 6：保留引用绑定和多批次归并能力

**文件：**
- 修改：`backend/app/modules/learning_execution/service.py`
- 修改：`backend/tests/modules/learning_execution/test_task_content_api.py`
- 修改：`backend/tests/integration/test_task_content_generation_flow.py`

- [ ] **步骤 1：更新嵌套 block 的引用收集**

确保 `_collect_content_item_ids()` 和 `_bind_source_citation_ids()` 仍会遍历嵌套 blocks、formula cards、knowledge maps 和 self-check items。

如果 block 有 `id`，按 block id 绑定；如果没有，则按父 section 绑定。section 级引用保留为 fallback。

- [ ] **步骤 2：更新 handout reducer**

当多个 batch 产生多个 v2 handout 时：

- 保留 `schema_version=2`；
- 合并唯一 learning objectives；
- 按稳定顺序追加 sections；
- 将 section id 重写为 `sec_N`；
- 保留嵌套 blocks；
- 按 `latex` 去重收集 formula cards；
- 保留第一个合法 `knowledge_map`，或根据最终 sections 合成浅层 map；
- 使用最后一个输出的 summary，或确定性生成短 summary。

- [ ] **步骤 3：新增 section/block 引用绑定测试**

测试持久化后：

- section `source_citation_ids` 变成 `cit_...`；
- block `source_citation_ids` 变成 `cit_...`；
- 输出中不再残留原始 `chunk_...` 引用 id。

- [ ] **步骤 4：运行集成测试**

```powershell
cd backend
uv run pytest tests/modules/learning_execution/test_task_content_api.py tests/integration/test_task_content_generation_flow.py -q
```

预期：通过。

- [ ] **步骤 5：提交引用 / reducer 工作**

```powershell
git add backend/app/modules/learning_execution/service.py backend/tests/modules/learning_execution/test_task_content_api.py backend/tests/integration/test_task_content_generation_flow.py
git commit -m "feat: 支持结构化讲义引用绑定"
```

## 任务 7：更新 v2 讲义导出渲染

**文件：**
- 修改：`backend/app/modules/exports/renderer.py`
- 修改：`backend/tests/modules/exports/test_exports_api.py`

- [ ] **步骤 1：新增 v2 到 Markdown 的渲染函数**

实现类似：

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

- [ ] **步骤 2：渲染公式、例题、表格和图示**

使用这些 fallback 规则：

- `formula`：渲染标题、`$$latex$$`、变量、适用条件、限制条件。
- `example`：渲染题目、顺序步骤、答案、解释。
- `table`：渲染 Markdown table。
- `mindmap`：PDF fallback 渲染为嵌套 bullet tree。
- `mermaid`：Markdown/HTML 中渲染 fenced `mermaid` block；PDF 中显示代码和解释，除非已实现 Mermaid 渲染。
- `chart`：除非加入 chart renderer，否则渲染为紧凑表格 fallback。

- [ ] **步骤 3：保持引用摘录安全**

继续使用 `renderer.py` 已有的安全引用展示规则；不要在用户可见 PDF 中暴露 parser 残留。

- [ ] **步骤 4：新增导出测试**

测试：

- 公式以 `$$...$$` 出现；
- 表格列正确；
- mindmap fallback 渲染为嵌套 bullets；
- 不安全 citation snippet 被隐藏；
- 畸形 v2 内容返回 `EXPORT_CONTENT_INVALID`。

- [ ] **步骤 5：运行导出测试**

```powershell
cd backend
uv run pytest tests/modules/exports/test_exports_api.py -q
```

预期：通过。

- [ ] **步骤 6：提交导出支持**

```powershell
git add backend/app/modules/exports/renderer.py backend/tests/modules/exports/test_exports_api.py
git commit -m "feat: 支持结构化讲义导出"
```

## 任务 8：构建前端结构化讲义 renderer

**文件：**
- 新建：`frontend/src/features/generated-content/handout-renderer.tsx`
- 新建：`frontend/src/features/generated-content/handout-renderer.css`
- 修改：`frontend/src/pages/GeneratedContentDetailPage.tsx`
- 修改：`frontend/src/features/course-workspace/types.ts`
- 修改：`frontend/tests/pages/generated-content-detail.test.tsx`
- 如果新增依赖，可选修改：`docs/architecture/adr/0007-structured-handout-rendering.md`

- [ ] **步骤 1：决定依赖范围**

尽量使用现有依赖。如果新增 `katex`、`mermaid`、`markmap-lib`、`markmap-view` 或 chart 库，先写 ADR，并在执行时申请安装依赖。

最小无新增依赖实现：

- 公式：先在样式化公式卡片中展示 LaTeX 文本；如果后续获准安装依赖，再加 KaTeX。
- 思维导图：先渲染为样式化可折叠树。
- Mermaid：先渲染为代码 fallback。

- [ ] **步骤 2：新增 TypeScript 类型**

添加 handout v2 类型：

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

- [ ] **步骤 3：创建 renderer 组件**

实现：

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

- [ ] **步骤 4：实现 block renderer**

实现 switch：

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

- [ ] **步骤 5：增加视觉 CSS 约束**

CSS 中需要：

- 公式卡片横向 overflow，不撑破布局；
- 表格使用 `overflow-x: auto`；
- 思维导图树使用嵌套缩进和连接线；
- 例题和易错点使用不同视觉强调；
- 移动端单列布局。

- [ ] **步骤 6：接入详情页**

在 `GeneratedContentDetailPage.tsx` 中检测：

```tsx
if (content.content_type === "handout" && isHandoutContentV2(content.content_json)) {
  return <HandoutRenderer content={content.content_json} />;
}
```

- [ ] **步骤 7：新增前端测试**

测试：

- handout overview 渲染；
- formula block 渲染标题和 LaTeX；
- table block 渲染 rows；
- mindmap block 渲染嵌套 label；
- 未知或旧版 handout 能安全 fallback。

- [ ] **步骤 8：运行前端测试**

```powershell
cd frontend
pnpm test -- --run generated-content-detail
pnpm build
```

预期：测试通过，构建成功。

- [ ] **步骤 9：提交前端 renderer**

```powershell
git add frontend/src/features/generated-content/handout-renderer.tsx frontend/src/features/generated-content/handout-renderer.css frontend/src/pages/GeneratedContentDetailPage.tsx frontend/src/features/course-workspace/types.ts frontend/tests/pages/generated-content-detail.test.tsx
git commit -m "feat: 展示结构化讲义内容"
```

## 任务 9：完整 prompt 与渲染验证

**文件：**
- 修改：`backend/tests/integration/test_task_content_generation_flow.py`
- 如需要，修改：`backend/scripts/validate_study_mode_real_fixes.py`

- [ ] **步骤 1：新增端到端 mock 生成 fixture**

创建一个 mock handout v2 输出，包含：

- 一个 formula block；
- 一个 table block；
- 一个 mindmap block；
- 一个 example block；
- 一个 mistake block；
- 合法引用。

- [ ] **步骤 2：测试 API 响应**

断言 `POST /study-subtasks/{id}/handouts` 返回：

- `content_type=handout`；
- `content_json.schema_version=2`；
- 结构化 blocks；
- `source_citations` 非空；
- 持久化后没有原始 `chunk_...` 引用 id。

- [ ] **步骤 3：测试 execution context 仍然可用**

断言 `GET /study-subtasks/{id}/execution-context` 返回最近成功的 `handout_content_id`。

- [ ] **步骤 4：测试导出仍然可用**

断言 `GET /generated-contents/{id}/exports/pdf` 返回 `application/pdf`。

- [ ] **步骤 5：运行后端目标套件**

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py tests/modules/learning_execution/test_task_content_api.py tests/modules/exports/test_exports_api.py tests/integration/test_task_content_generation_flow.py -q
```

预期：通过。

- [ ] **步骤 6：提交验证覆盖**

```powershell
git add backend/tests/integration/test_task_content_generation_flow.py backend/scripts/validate_study_mode_real_fixes.py
git commit -m "test: 覆盖结构化讲义生成链路"
```

## 任务 10：文档与最终验证

**文件：**
- 修改：`docs/domains/study-mode/task-content.md`
- 修改：`docs/api-data/frontend-integration.md`
- 修改：`docs/planning/current-state.md`
- 如果新增依赖，修改：`docs/architecture/adr/index.md` 和对应 ADR 文件

- [ ] **步骤 1：更新领域文档**

记录：

- v2 schema；
- 模型输入；
- prompt 切换规则；
- 渲染责任划分；
- 引用校验与回绑；
- PDF fallback 行为。

- [ ] **步骤 2：更新前端集成文档**

记录：

- block 类型列表；
- 前端展示规则；
- 安全 fallback 行为；
- 公式 / 表格 / 思维导图渲染预期。

- [ ] **步骤 3：运行最终验证**

运行：

```powershell
cd backend
uv run pytest tests/modules/generation/test_handout_generator.py tests/modules/learning_execution/test_task_content_api.py tests/modules/exports/test_exports_api.py tests/integration/test_task_content_generation_flow.py -q
cd ../frontend
pnpm test -- --run generated-content-detail
pnpm build
cd ..
git diff --check
```

预期：

- 后端目标测试通过；
- 前端目标测试通过；
- 前端 build 通过；
- `git diff --check` 没有空白错误。

- [ ] **步骤 4：提交文档和最终修复**

```powershell
git add docs/domains/study-mode/task-content.md docs/api-data/frontend-integration.md docs/planning/current-state.md docs/architecture/adr/index.md docs/architecture/adr/0007-structured-handout-rendering.md
git commit -m "docs: 更新结构化讲义实现说明"
```

## 完成标准

- 模型输出经过校验的结构化 JSON，而不是自由 Markdown 文档。
- 公式、表格、思维导图、图表、例题、易错点和自测内容都使用 typed blocks。
- 前端渲染负责控制布局、间距、溢出和响应式行为。
- 模型输入和 prompt 规则会根据 `subtask_type`、内容深度、强度字段和 `weak_area` 明确切换。
- 参考 prompt 中的教学设计要求被落入 prompt 规则和 schema 字段。
- `diagnostic_explanation_style` 不再被当作用户侧 handout 输入。
- 现有讲义生成、详情响应、execution context 和 PDF 导出保持可用。
- 测试覆盖 schema、prompt、引用绑定、导出和前端渲染。

## 执行注意事项

- 未经用户明确指令，不要 push。
- 如需安装前端依赖，先申请用户批准。
- 如果某个依赖成为公式 / 图示渲染核心依赖，先写 ADR，再写依赖代码。
- 每个任务通过对应验证命令后单独提交。
- 如果模型无法稳定一次性满足完整 v2 schema，先收集失败输出，再增加 retry/repair 任务；不要静默接受部分畸形讲义。
