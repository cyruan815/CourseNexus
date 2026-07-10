# G02 Quiz 生成器

## 0. 业务功能说明

- **业务场景**：学生完成一章或一组课件学习后，希望立刻用课程资料生成自测题检查理解情况。
- **用户能力**：选择资料、题量、题型和难度，生成课程自测；查看题干、选项、正确答案、答案解析和每道题的资料来源。
- **业务结果**：生成的题目覆盖所选资料中的核心知识点，并作为课程生成内容保存，学生之后可以重新打开复习。
- **业务边界**：本任务不记录学生作答、得分、错题或考试历史，也不等同于计划执行模式中的任务测试题。

## 1. 任务信息
- **负责人**：独立生成功能后端开发者。
- **目标**：基于全部选定资料生成可作答、可查看答案解析、逐题可追溯的课程自测，保存为 `content_type=quiz`。
- **前置依赖**：G01 公共 contracts、registry、coverage、引用和 fixtures。
- **范围外**：答题记录、判分、错题本、题库、前端状态、计划 `task_test` 和独立业务表。
- **当前已实现 API**：通用 generation POST、历史、详情。
- **本任务新增 API**：无新路径；实现 `content_type=quiz` 的真实参数和输出。
- **后端未实现仅占位**：提交答案和得分接口，不得返回假作答结果。

## 2. 实现范围
### 2.1 文件边界
- 创建 / 修改 `backend/app/modules/generation/generators/quiz/{__init__,schemas,prompts,generator}.py`。
- 创建 `backend/tests/modules/generation/generators/quiz/test_{quiz_schemas,quiz_generator,quiz_api}.py`。
- 只读 G01、material-context、ModelProvider、generated-content 和 table-schema。
- 禁止修改 registry、contracts、其他 generator、task_test、计划子系统、DB model、migration、API 总 router 和前端。

### 2.2 参数与 schema
```python
class QuizParameters(BaseModel):
    question_count: int = Field(default=10, ge=1, le=50)
    question_types: list[Literal["single_choice","multiple_choice","true_false","short_answer"]]
    difficulty: Literal["easy","medium","hard","mixed"] = "mixed"
    focus: str | None = Field(default=None, min_length=1, max_length=200)
```
- 默认 question types 为 single choice、true/false、short answer；去重后不能为空。
- map schema：`QuizCandidate(question_type, question_text, options, correct_answer, explanation, difficulty, source_chunk_ids)` 和 `QuizMapResult(candidates, citation_chunk_ids)`。
- single choice 固定 A-D 四项、答案为单个 ID；multiple choice 固定四项、答案为 2-3 个有序 ID。
- true/false 的 options 为空、答案为 boolean；short answer 的 options 为空、答案为非空字符串。
- 所有题 explanation 非空、至少一个真实 chunk；同次 question text trim + casefold 后唯一。

最终 `content_json`：
```json
{"questions":[{"id":"q_001","question_type":"single_choice","question_text":"题干","options":[{"id":"A","text":"选项"}],"correct_answer":"A","explanation":"解析","difficulty":"medium","source_citation_ids":["cit_1"],"sort_order":1}]}
```
- ID 为 `q_001..q_N`，sort order 连续；`content=null`；标题为 `课程自测（N 题）`。

### 2.3 Prompt / map / reduce / 持久化
- map prompt 逐 chunk 提供 chunk ID、资料名、定位、heading、正文，只生成资料可直接判定的题。
- 每个 batch 均调用一次 `ModelProvider.generate_structured(..., QuizMapResult)`；达到题量后也不能跳过后续 batch。
- 每批候选 `min(20, max(2, ceil(question_count / batch_count)+1))`。
- reduce 只接收 map 候选，按题型、难度、focus、去重和材料覆盖选最多 question_count 题；不再读原文或外部事实。
- 本地代码复核题型不变量、稳定编号和引用 binding；1..requested 道合法题可成功，0 题为 `GENERATION_SCHEMA_INVALID`。
- `run_material_coverage()` 必须在 reduce 前验证全部 batches；只保存最终题目的引用。
- `build_generator(model_provider)` 返回 QuizGenerator，由 G01 自动发现；不得调用 Task Test 或其他 generator。

## 3. 字段与接口
请求：
```json
{"content_type":"quiz","material_scope":{"include_all_parsed_materials":false,"folder_ids":[],"material_ids":["mat_1","mat_2"]},"parameters":{"question_count":8,"question_types":["single_choice","multiple_choice","short_answer"],"difficulty":"mixed","focus":"特征值"}}
```
- 成功 HTTP 200：`generation_status=success`，questions 符合上述结构，每个 citation ID 可在顶层 citations 解析。
- 参数非法：422 `VALIDATION_ERROR` 且不落库；无资料：400 `NO_PARSED_MATERIAL`；跨用户：404 `NOT_FOUND`。
- 模型 / schema / coverage 错误：返回可查询 failed 记录和对应稳定 error code，无部分 questions / citations。

## 4. 测试计划
- `test_quiz_schemas.py`：四题型合法 / 非法答案与 options；题量 0/51；空类型；重复选项；focus 长度。
- `test_quiz_generator.py`：两资料多 batch 全 map、一次 reduce、题目去重、稳定 ID、题量裁剪、只留最终引用、三类失败。
- `test_quiz_api.py`：401、404、400、422、成功 POST / 详情 / 历史、非法参数不落库、failed 可重读、重复请求不同 ID。
```powershell
cd backend
conda run -n course-nexus pytest tests/modules/generation/generators/quiz -q
conda run -n course-nexus pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context -q
```
- 预期全部 PASS；默认 registry 创建 QuizGenerator；无 live network。

## 5. 验收标准
### 自动化验收
- [ ] 所有资料 batches 均 map，题量上限不截断覆盖。
- [ ] 四题型不变量、稳定 ID、逐题真实引用均通过。
- [ ] 参数、权限、空材料、模型、schema、coverage 失败均覆盖。
- [ ] Quiz 测试不 import / 执行 task_test。
### 人工验收
- [ ] 两份资料生成 8 题，题目能覆盖两份资料且引用可追溯。
- [ ] short-answer-only 请求全部 options 为空、答案为字符串。
- [ ] question_count=51 返回 422，历史数量不变。

## 6. 交付物
- Quiz 参数、map / reduce / final schema、prompt、generator、factory。
- schema / generator / API 测试和中文验收记录。
- 建议提交：`feat(quiz): 实现全材料课程自测生成`、`test(quiz): 覆盖结构引用和失败路径`。

## 7. 文档同步
- 更新 `docs/api-data/contracts.md` 的 Quiz parameters 和响应示例。
- 核对现有 `table-schema.md` questions 契约；字段不变不修改。
- 更新 `runtime-flows.md`、`current-state.md`，只标 Quiz 完成。
- 不修改 PRD 原意；题型规则变化先提产品契约。

## 8. 冲突与注意事项
- **冲突点**：G01 公共文件只读；Quiz 与 Task Test 只共享 JSON 形状，内部完全独立；table-schema 变更交唯一负责人。
- **严格遵循**：全材料 batch + coverage、ModelProvider、最终题目真实引用、统一内容表。
- **一定不能做**：新增 quiz 表 / migration；调用 task_test / 其他 generator；直接查 chunk / Chroma 或 OpenAI；无引用或空 questions 标 success。

## 9. 完成检查表
- [ ] 实现范围、测试、人工验收和 docs 全部完成。
- [ ] G01、generated-content、material-context 回归通过。
- [ ] `git diff --check` 通过，自动化无网络，修改未越权。
- [ ] 未新增表、migration、依赖；小功能已独立提交。
