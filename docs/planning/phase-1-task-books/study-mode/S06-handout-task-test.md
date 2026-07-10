# S06 今日讲义与任务测试题

## 0. 业务功能说明

- **业务场景**：学生进入具体二级任务后，需要围绕该任务关联资料获得当天要学的讲义，或在测试类任务中完成针对性练习。
- **用户能力**：学习或复习任务按需生成今日讲义；Quiz 或 Test 类型任务按需生成任务测试题，并查看答案、解析和资料来源。
- **业务结果**：内容只在学生真正进入任务时生成，绑定当前二级任务并保存在生成历史中，不增加计划保存等待时间。
- **业务边界**：S06 必须等待 G01 公共生成协议，但不等待 G02-G06；它不修改五类课程学习工具，也不更新任务完成或打卡状态。

## 1. 任务信息
- 编号与名称：`S06` 今日讲义与任务测试题。
- 负责人角色：计划学习模式后端开发者。
- 目标：通过 G01 公共生成协议为二级任务按需生成 `handout` 和 `task_test`，统一保存到 `ai_generated_contents`。
- 硬前置：G01 已合并 `contracts.py`、`registry.py`、全材料覆盖、引用保存公共协议及 contract tests。未合并时不得开始改高冲突文件。
- 范围外：不修改 Quiz/Flashcard/Mindmap/Outline/Knowledge List；不生成计划；不保存作答记录；不导出 PDF。

## 2. 实现范围
### 2.1 公共协议接入
- `HandoutGenerator`、`TaskTestGenerator` 只实现 G01 公开 `Generator` 协议，输出 `GeneratorOutput`。
- 通过 G01 的扩展注册入口注册 `handout`、`task_test`；不得直接编辑默认五类生成器列表。若 G01 未暴露外部注册函数，先提交最小契约提案，由 G01 负责人合并。
- 调用方传 `user_id`、`course_id`、`study_subtask_id`、严格 `MaterialScope` 和参数。
- 材料范围固定来自 `StudySubTask.related_material_ids_json`，转换为 `include_all_parsed_materials=false`、空 `folder_ids`、对应 `material_ids`；空数组返回 `NO_PARSED_MATERIAL`。
- 生成使用 `iter_material_context_batches()` + `run_material_coverage()`；不能使用 Top-K 或 `resolve_context()`。
- `learn|review` 允许生成 handout；`quiz|test` 允许生成 task_test；类型不符返回 `STATE_CONFLICT`。
- 成功/失败都保存 `AIGeneratedContent`，绑定当前用户、课程和 `study_subtask_id`；失败记录保存稳定 `error_code`。
- 当前表结构无法可靠保存生成请求幂等键，本任务不得伪装提供 durable idempotency。前端只在单次请求进行中禁用重复点击；显式重新生成会创建新记录并保留历史。若后续要求跨进程幂等，必须先单独评审技术表和 migration。
- 引用只保存本次覆盖结果允许的 chunk ID，禁止无引用时回退首个 chunk。

### 2.2 内容 schema
`HandoutContent`：
```json
{
  "overview": "本任务概览",
  "learning_objectives": ["目标"],
  "sections": [{"id":"sec_1","title":"主题","body":"正文","key_points":["重点"],"source_citation_ids":["cit_1"],"sort_order":1}],
  "summary": "总结"
}
```

`TaskTestContent`：
```json
{
  "instructions": "作答说明",
  "questions": [{"id":"q_1","question_type":"single_choice","question_text":"题干","options":[{"id":"A","text":"选项"}],"correct_answer":"A","explanation":"解析","source_citation_ids":["cit_1"],"sort_order":1}]
}
```
- 题型只允许 `single_choice|multiple_choice|true_false|short_answer`；选择题 options 非空；所有题必须有答案和解析。

### 2.3 精确文件边界
创建：
- `backend/app/modules/generation/generators/handout/schemas.py`
- `backend/app/modules/generation/generators/handout/generator.py`
- `backend/app/modules/generation/generators/task_test/schemas.py`
- `backend/app/modules/generation/generators/task_test/generator.py`
- `backend/tests/modules/generation/test_handout_generator.py`
- `backend/tests/modules/generation/test_task_test_generator.py`
- `backend/tests/modules/learning_execution/test_task_content_api.py`
- `backend/tests/integration/test_task_content_generation_flow.py`

修改：两个 generator `__init__.py`；`learning_execution/schemas.py`、`service.py`、`router.py`；仅消费 G01 暴露的注册扩展点。

禁止修改：五类生成器目录、G01 的 `contracts.py`/`registry.py` 签名、migration、models、前端、PDF 模块。

## 3. 字段与接口
### 3.1 当前 API
- 当前 `/courses/{course_id}/generations` 只注册五类占位/业务生成器；handout/task_test 包为空。
- 当前 generated-content list/detail 可读取最终记录，但没有任务专用生成入口。

### 3.2 新增 API
`POST /api/v1/study-subtasks/{subtask_id}/handouts`：
```json
{"parameters":{"language":"zh-CN","detail_level":"standard"}}
```
响应为现有 `GeneratedContentRead`，其中 `content_type=handout`、`study_subtask_id` 匹配、`generation_status=success|failed`、结构写 `content_json`。

`POST /api/v1/study-subtasks/{subtask_id}/task-tests`：
```json
{"parameters":{"question_count":5,"question_types":["single_choice","short_answer"],"difficulty":"medium"}}
```
- `question_count` 范围 1-20；`difficulty=easy|medium|hard`。
- 响应同上，`content_type=task_test`。

两接口错误：401 `UNAUTHORIZED`；404 `NOT_FOUND`；409 `STATE_CONFLICT`、`MATERIAL_COVERAGE_INCOMPLETE`；400 `NO_PARSED_MATERIAL`；422 `VALIDATION_ERROR`；500 `GENERATION_SCHEMA_INVALID`；502 `GENERATION_FAILED`。

S06 合并后，S04 execution context 查询最近一条成功记录填充两个 content ID。接口合并前前端只能显示生成入口占位。

## 4. 测试计划
### 4.1 精确场景
- handout：多 batch 全覆盖、章节 schema、引用子集、模型失败、schema 失败、空资料、错误任务类型。
- task_test：四种题型校验、题数上下界、答案解析必填、引用子集、错误任务类型。
- API：401/404/409/422/500/502、跨用户、请求进行中防重复、显式重新生成产生新记录、成功/失败记录落库。
- 集成：保存计划时生成内容数为 0；进入任务后按需生成；两类内容均绑定 subtask；不改变任务完成状态；五类生成器 contract tests 全通过。

### 4.2 命令与预期
```powershell
cd backend
conda run -n course-nexus python -m pytest tests/modules/generation/test_handout_generator.py tests/modules/generation/test_task_test_generator.py -q
conda run -n course-nexus python -m pytest tests/modules/learning_execution/test_task_content_api.py -q
conda run -n course-nexus python -m pytest tests/integration/test_task_content_generation_flow.py tests/modules/generation/test_orchestrator_contract.py -q
```
预期：退出码 0；Fake provider 覆盖全部模型调用；五类生成器回归不变；失败记录可重试且无伪引用。

## 5. 验收标准
### 自动化
- [ ] 两类生成均处理全部关联资料并保存 content_json 与引用。
- [ ] 类型限制、权限、失败、重复点击保护和 schema 测试通过。
- [ ] 生成不更新任何任务/打卡状态。
- [ ] 五类独立生成器文件和行为无变化。

### 人工
- [ ] 学习任务首次点击生成讲义，刷新后复用历史内容。
- [ ] 测试任务进入后生成 5 题并展示答案解析。
- [ ] 显式重新生成会创建新记录，旧内容仍可查看；界面不声称支持跨进程幂等。
- [ ] 任一生成失败不影响执行页和完成按钮。

## 6. 交付物
- 两个 generator、schema、任务 API 与四组测试。
- API/架构/内容 JSON/当前状态文档。
- `docs/planning/phase-1-validation/S06-task-content.md` 中文验收记录。
- 建议提交：`feat(handout): 接入任务讲义生成器`；`feat(task-test): 接入任务测试题生成器`；`feat(execution): 新增任务内容按需生成接口`。

## 7. 文档同步
- 新建或更新 `docs/domains/study-mode/task-content.md`：记录 Handout/Task Test 生成器分层和代码入口、任务上下文构造与统一存储数据流、prompt/schema、全材料 map/reduce 与覆盖算法、内容去重和引用映射、输出校验、复杂度与批次/token 预算、模型失败/重试/补偿策略和测试证据。
- 更新 `docs/architecture/module-boundaries.md`、`runtime-flows.md`。
- 更新 `docs/api-data/contracts.md`、`table-schema.md` 的两类 content_json 契约。
- 更新 `docs/planning/current-state.md`；不改 PRD原意。
- 不直接改 `frontend-integration.md`，前端等契约与 G01 合并后接入。

## 8. 冲突与注意事项
### 严格遵循
- G01 是唯一公共生成协议权威；S06 只注册和消费。
- `study_subtask_id`、课程、用户和材料范围必须一致。
- 引用必须是真实覆盖 chunk 的子集。

### 一定不能做
- 不能碰五类生成器、直接调用 OpenAI、直接查 Chroma或新增表。
- 不能把 task_test 当课程 Quiz 保存或在计划保存时提前生成。
- 不能用首 chunk 回退伪造引用、修改任务完成状态或写前端。

## 9. 完成检查表
- [ ] G01 前置、实现、测试、验收、docs 全部完成。
- [ ] content_json 与错误码契约稳定。
- [ ] 五类生成器回归、`git diff --check` 通过。
- [ ] 未越权修改且每个小功能独立提交。
