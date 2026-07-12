# Quiz 生成模块

## 能力边界

G02 根据全部选定的已解析课程材料生成可追溯的课程自测，支持单选、多选、判断和简答。模块不记录用户答案、分数、错题或考试历史，也不调用 `task_test`。

## 代码入口

```text
backend/app/modules/generation/generators/quiz/schemas.py
backend/app/modules/generation/generators/quiz/prompts.py
backend/app/modules/generation/generators/quiz/generator.py
```

`generator.py:build_generator` 由 G01 registry 自动发现。生成器只通过 `ModelProvider.generate_structured` 调用模型。

## 参数

- `question_count`: 默认 10，范围 1..50。
- `question_types`: 默认 `single_choice`、`true_false`、`short_answer`，保持请求顺序并去重，不能为空。
- `difficulty`: `easy|medium|hard|mixed`，默认 `mixed`。
- `focus`: 可选，长度 1..200。

## 题型不变量

- `single_choice`: 固定 A-D 四项，`correct_answer` 是一个有效选项 ID。
- `multiple_choice`: 固定 A-D 四项，`correct_answer` 是按选项顺序排列的 2-3 个唯一 ID。
- `true_false`: `options=[]`，`correct_answer` 是 boolean。
- `short_answer`: `options=[]`，`correct_answer` 是非空字符串。
- 所有题目必须有非空解析、合法难度和至少一个范围内真实 chunk 引用。

## 生成算法

每个 material-context batch 都执行一次 map，候选预算为：

```text
min(20, max(2, ceil(question_count / batch_count) + 1))
```

reduce 不重新读取原文。它先过滤未请求题型和难度，再按题干 trim、空白归一和 casefold 去重；重复题合并引用。候选在每个题型桶内按 focus 命中、跨材料支持数和首次出现顺序排序，然后按请求题型顺序轮询选择，最多保留 `question_count` 道题。

最终题目稳定编号为 `q_001...q_N`，`sort_order` 从 1 连续递增。时间复杂度为 `O(C log C)`，空间复杂度为 `O(C)`，其中 C 为全部 map 候选数量。模型调用次数等于材料批次数。

## 持久化结构

```json
{
  "questions": [
    {
      "id": "q_001",
      "question_type": "single_choice",
      "question_text": "题干",
      "options": [
        {"id": "A", "text": "选项 A"},
        {"id": "B", "text": "选项 B"},
        {"id": "C", "text": "选项 C"},
        {"id": "D", "text": "选项 D"}
      ],
      "correct_answer": "A",
      "explanation": "答案解析",
      "difficulty": "medium",
      "source_citation_ids": ["cit_001"],
      "sort_order": 1
    }
  ]
}
```

数据保存于 `ai_generated_contents.content_json`，`content_type="quiz"`，`content=null`。逐题 `source_citation_ids` 对应响应顶层 `source_citations[].id`。

## 失败策略

- 参数非法：HTTP 422 `VALIDATION_ERROR`，不创建记录。
- 无已解析材料：HTTP 400 `NO_PARSED_MATERIAL`。
- 模型失败：保存 `GENERATION_FAILED` 失败记录。
- 无合法题目或题型结构非法：保存 `GENERATION_SCHEMA_INVALID` 失败记录。
- 材料覆盖不完整：保存 `MATERIAL_COVERAGE_INCOMPLETE` 失败记录。

失败记录没有部分 questions 或 citations。

## 测试

```powershell
python -m pytest tests/modules/generation/generators/quiz -q
python -m pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context tests/contracts/test_material_context_consumers.py -q
```

测试覆盖参数、四种题型、全批次调用、去重、稳定 ID、引用合并、POST、历史、详情和非法参数不落库。
