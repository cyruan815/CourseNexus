# S06 任务讲义与任务测试题验收记录

## 范围

本次完成后端 S06：为学习 / 复习二级任务按需生成 `handout` 今日讲义，为 quiz / test 二级任务按需生成 `task_test` 任务测试题。生成内容复用 `ai_generated_contents` 并绑定 `study_subtask_id`。

## 已验证能力

- `learn` / `review` 只允许生成 `handout`。
- `quiz` / `test` 只允许生成 `task_test`。
- 材料范围严格来自 `StudySubTask.related_material_ids_json`。
- 空资料或无解析上下文返回 `NO_PARSED_MATERIAL`。
- S06 使用 `iter_material_context_batches()` 和 `run_material_coverage()`，不走 Top-K 或 `resolve_context()`。
- 成功生成会保存 `AIGeneratedContent(generation_status=success)` 和 `SourceCitation`。
- 进入生成流程后的失败会保存 `AIGeneratedContent(generation_status=failed, error_code=...)`。
- 引用必须来自本次材料上下文，不允许伪造 fallback。
- 默认重复生成请求返回同一二级任务同一内容类型最近一次未删除成功内容，不新增成功记录、不调用模型。
- `force_regenerate=true` 时允许在已有 success 后重新生成并创建新的成功内容。
- failed 记录不参与幂等命中，不阻止下一次请求重新尝试生成。
- `GET /api/v1/study-subtasks/{subtask_id}/execution-context` 返回最近一次成功的 `handout_content_id` / `task_test_content_id`，不返回 failed id。
- 生成内容不改变二级任务完成状态、一级任务汇总状态或打卡记录。
- 不新增业务表，不修改 baseline migration，不修改前端。

## 验证命令

```powershell
uv run python -m pytest tests/modules/generation/test_handout_generator.py -q
uv run python -m pytest tests/modules/generation/test_task_test_generator.py -q
uv run python -m pytest tests/modules/learning_execution/test_task_content_api.py -q
uv run python -m pytest tests/modules/learning_execution -q
uv run python -m pytest tests/integration/test_task_content_generation_flow.py tests/modules/learning_execution tests/modules/checkins -q
uv run python -m pytest tests/modules/generation/test_orchestrator_contract.py tests/modules/generation/test_orchestrator_service.py -q
```

## 最近结果

- S06 task content API：`18 passed`。
- S06 集成流：`2 passed`。
- Handout / task-test generator 回归：`12 passed`。

## 未涉及范围

- 未实现学生作答保存，已拆到 S08。
- 未实现 PDF 导出，仍由 S07 负责。
- 未修改前端。
- 未新增 migration 或业务表。