# Flashcard 生成模块

## 能力边界

G03 将全部选定材料转换为带真实引用的结构化记忆卡片。后端不实现间隔重复、掌握度更新、复习提醒、卡片编辑或 Anki 导出；生成时 `mastery_status` 固定为 `unknown`。

## 参数与结构

- `card_count`: 默认 20，范围 1..100。
- `card_style`: `term_definition|question_answer|mixed`。
- `include_formulas`: 默认 `true`；为 `false` 时仅降低公式卡排序，不跳过材料。
- `focus`: 可选，长度 1..200。
- `front`: 1..300 字符；`back`: 1..1200 字符。
- `tags`: 最多 5 个，每个 1..40 字符，trim 后 casefold 去重。

成功记录保存到 `ai_generated_contents.content_json.cards`，卡片 ID 为 `card_001...`，`sort_order` 连续，每张卡通过 `source_citation_ids` 关联顶层 `source_citations`。

## 算法

每个材料批次调用一次结构化模型，候选预算为 `min(30,max(3,ceil(card_count/batch_count)+2))`。reduce 按 front 空白归一和 casefold 去重，合并标签与真实 chunk 引用，再按 focus 命中、公式偏好、跨材料支持数和首次出现顺序排序。

时间复杂度为 `O(C log C)`，空间复杂度为 `O(C)`，模型调用数等于材料批次数。0 张合法卡片产生 `GENERATION_SCHEMA_INVALID`；参数非法不落库，模型和覆盖失败保存稳定 failed 记录，不保存部分 cards 或 citations。

## 代码与测试

```text
backend/app/modules/generation/generators/flashcard/schemas.py
backend/app/modules/generation/generators/flashcard/prompts.py
backend/app/modules/generation/generators/flashcard/generator.py
backend/tests/modules/generation/generators/flashcard/
```

```powershell
python -m pytest tests/modules/generation/generators/flashcard -q
python -m pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context tests/contracts/test_material_context_consumers.py -q
```
