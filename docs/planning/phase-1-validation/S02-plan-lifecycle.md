# S02 学习计划生命周期验收记录

## 验收日期

2026-07-11

## 验收结论

S02 已完成后端生命周期实现：自然语言配置回填、全材料预览、用户调整后保存、保存幂等、重生成预览、原子替换和软删除。实现不新增业务表、不新增字段、不修改 migration，不接入前端，不实现 S03-S07 的待办、日历、执行页、打卡、讲义、任务测试题或 PDF 导出。

## 覆盖范围

- 配置回填：`POST /api/v1/courses/{course_id}/study-plan-config-parses` 只调用结构化模型，不写数据库。
- 全材料预览：`POST /api/v1/courses/{course_id}/study-plans/preview` 通过 `iter_material_context_batches()` 和 `run_material_coverage()` 覆盖范围内已解析资料。
- 保存：`POST /api/v1/courses/{course_id}/study-plans` 接收用户确认后的任务树，支持旧请求省略 `tasks` 时兼容生成 preview。
- 幂等：`Idempotency-Key` 同键同请求返回既有 bundle，同键不同请求返回 `IDEMPOTENCY_CONFLICT`。
- 重生成：`POST /api/v1/study-plans/{plan_id}/regeneration-previews` 只返回 preview，不写数据库。
- 替换：`PUT /api/v1/study-plans/{plan_id}` 校验 `expected_updated_at`、无进度、无绑定生成内容后，在一次事务中替换任务树。
- 删除：`DELETE /api/v1/study-plans/{plan_id}` 软删除计划，默认列表和详情隐藏。

## 数据和边界确认

- 未新增业务表、列或 Alembic revision。
- 未修改 `backend/migrations/**` 和 `backend/app/db/models.py`。
- 保存计划只写 `study_plans`、`study_tasks`、`study_subtasks`。
- 保存计划不生成 `handout`、`task_test`，不写 `ai_generated_contents`；测试中只人工创建绑定记录用于验证替换冲突。
- preview 使用测试 fake provider，不访问 live network。
- 前端集成需等待 `docs/api-data/contracts.md` 里的 S02 契约评审。

## 验证命令

```powershell
cd D:\Projects\CourseNexus\backend
uv run python -m alembic upgrade head
uv run python -m pytest tests/modules/study_plans tests/modules/material_context tests/integration/test_full_material_plan_flow.py tests/integration/test_material_context_to_plan_flow.py -q
```

结果：

- Alembic `upgrade head` 成功。
- `49 passed in 16.80s`。

## 相关文档

- [../../domains/study-mode/plan-lifecycle.md](../../domains/study-mode/plan-lifecycle.md)
- [../../api-data/contracts.md](../../api-data/contracts.md)
- [../../api-data/api-conventions.md](../../api-data/api-conventions.md)
- [../../api-data/data-model.md](../../api-data/data-model.md)
- [../../api-data/table-schema.md](../../api-data/table-schema.md)
- [../../architecture/runtime-flows.md](../../architecture/runtime-flows.md)