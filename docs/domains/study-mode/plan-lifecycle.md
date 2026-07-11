# S02 学习计划生命周期实现说明

## 状态

- 日期：2026-07-11
- 状态：已实现并通过自动化验证。
- 范围：单课程学习计划生成、配置解析、确认保存、幂等、重生成预览、原子替换和软删除。

## 代码入口

| 层 | 文件 | 责任 |
| --- | --- | --- |
| Router | `backend/app/modules/study_plans/router.py` | 注册学习计划 API，按用途注入配置解析 / 计划生成 `ModelProvider`，读取 `Idempotency-Key`。 |
| Service | `backend/app/modules/study_plans/service.py` | 权限、全材料预览、保存事务、幂等、替换、重生成和软删除。 |
| Planner | `backend/app/modules/study_plans/planner.py` | map/reduce prompt、结构化生成调用、coverage 和预览校验。 |
| Repository | `backend/app/modules/study_plans/repository.py` | active 查询、幂等查询、任务树查询、flush-only 写入和替换辅助。 |
| Schemas | `backend/app/modules/study_plans/schemas.py` | 配置解析、预览、保存、替换和重生成请求/响应结构。 |

## 数据流

1. 自然语言配置回填：`POST /courses/{course_id}/study-plan-config-parses` 使用 `study_plan_parser` 模型配置调用 `ModelProvider.generate_structured()` 输出可编辑字段，不写数据库。
2. 预览：`preview_study_plan()` 调用 `iter_material_context_batches()` 读取范围内所有已解析资料批次，再用 `run_material_coverage()` 包住 planner map/reduce，并使用 `study_plan_generator` 模型配置生成计划。
3. 确认保存：新客户端提交调整后的 `tasks`；旧客户端不传 `tasks` 时后端先生成真实 preview 再保存。
4. 幂等：保存接口读取 `Idempotency-Key`，在 `StudyPlan.parsed_config_json.idempotency` 保存 `key_hash` 与 `request_hash`；同键同请求返回既有 bundle，同键不同请求返回 `IDEMPOTENCY_CONFLICT`。
5. 替换：`PUT /study-plans/{plan_id}` 校验 `expected_updated_at`、无进度、无绑定生成内容后，在一次事务中删除旧任务树并写入新任务树。
6. 重生成：`POST /study-plans/{plan_id}/regeneration-previews` 使用 `study_plan_generator` 模型配置，合并已保存配置和请求覆盖项，只返回 preview，不写数据库。
7. 删除：`DELETE /study-plans/{plan_id}` 写 `status = deleted`、`deleted_at`、`updated_at`，默认 list/detail 隐藏。

## 不变量

- S02 不新增表、不新增列、不修改 migration。
- 计划保存只写 `study_plans`、`study_tasks`、`study_subtasks`。
- 计划保存不生成 `handout`、`task_test` 或任何 `ai_generated_contents`。
- 已完成/进行中的二级任务，或已绑定 `ai_generated_contents` 的二级任务，会阻止替换并返回 `STATE_CONFLICT`。
- 每份范围内已解析资料必须进入至少一个 batch；coverage 返回 `expected_material_ids`、`processed_material_ids` 和 `batch_count`。

## 验证

- `uv run python -m alembic upgrade head`：通过。
- `uv run python -m pytest tests/modules/study_plans tests/modules/material_context tests/integration/test_full_material_plan_flow.py tests/integration/test_material_context_to_plan_flow.py -q`：`49 passed in 16.80s`。
- `uv run python -m pytest tests/modules/study_plans tests/integration/test_full_material_plan_flow.py tests/integration/test_material_context_to_plan_flow.py -q`：`27 passed in 15.91s`，覆盖 parser / generator provider 拆分。