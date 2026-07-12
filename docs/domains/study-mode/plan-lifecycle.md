# S02 学习计划生命周期实现说明

## 状态

- 日期：2026-07-12
- 状态：已实现并通过自动化验证。
- 范围：单课程学习计划生成、配置解析、诊断后 capacity 统计、确认保存、幂等、重生成预览、原子替换和软删除。

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
2. 预览：`preview_study_plan()` 调用 `iter_material_context_batches()` 读取范围内所有已解析资料批次，再用 `run_material_coverage()` 包住 planner map/reduce，并使用 `study_plan_generator` 模型配置生成计划。`planner.derive_planner_strategy()` 会先把英文 `preference` 和可选 `diagnostic_profile` 合并为 `planner_strategy`，写入 reduce prompt 和 `generation_metadata`。`recommended_daily_minutes` 基于 map 阶段材料单元估算；`capacity.estimated_total_minutes` 在 reduce 后基于最终 `tasks[].subtasks[].estimated_minutes` 重新统计。
3. 确认保存：新客户端提交调整后的 `tasks`；旧客户端不传 `tasks` 时后端先生成真实 preview 再保存。显式 `tasks` 会在写库前校验一级/二级任务结构、日期范围、排序连续性，以及所有关联资料是否属于当前用户、当前课程、本次 `material_scope` 且已解析可用；保存追溯中的 `parsed_config_json.planner_strategy` 由当前 `preference + diagnostic_profile` 重新派生，`parsed_config_json.capacity` 始终按最终 `tasks` 重新计算。
4. 幂等：保存接口读取 `Idempotency-Key`，将 `key_hash` 写入 `StudyPlan.idempotency_key_hash`，并在 `StudyPlan.parsed_config_json.idempotency` 保存 `key_hash` 与 `request_hash`；同键同请求返回既有 bundle，同键不同请求返回 `IDEMPOTENCY_CONFLICT`。数据库唯一索引 `(user_id, course_id, idempotency_key_hash)` 负责兜底并发重复提交；软删除计划仍占用原 key，不允许复用。
5. 替换：`PUT /study-plans/{plan_id}` 先校验无进度、无绑定生成内容和确认任务树完整性，再用 `id + user_id + expected_updated_at + active/deleted` 条件 UPDATE 获取替换权；影响 0 行返回 `STATE_CONFLICT`，影响 1 行后才在同一事务中删除旧任务树、写入新任务树并重算打卡。
6. 重生成：`POST /study-plans/{plan_id}/regeneration-previews` 使用 `study_plan_generator` 模型配置，合并已保存配置和请求覆盖项，只返回 preview，不写数据库。
7. 删除：`DELETE /study-plans/{plan_id}` 写 `status = deleted`、`deleted_at`、`updated_at`，默认 list/detail 隐藏。

## 计划质量约束

- 配置解析 prompt 会说明相对日期规则：用户写明“今天是 YYYY年M月D日”且使用“两天学完 / N 天学完”时，可推导 `start_date` 与 `end_date`。`parse_study_plan_config()` 在模型返回后还会用 `_normalize_relative_config()` 做确定性补全，避免明确日期语义被模型漏填。
- planner map prompt 负责把资料 chunk 按章节/页码顺序抽成细粒度知识单元，要求保留公式、例子、接口、设备、调制/编码/复用、安全隐患等可学习细节，并要求每个知识单元携带 `citation_chunk_ids`。
- planner reduce prompt 负责把知识单元排成可执行计划。生成标题时必须使用课程名称原文；完成型目标需要尽量利用每日可用时间，并通过复习、练习、输出任务和最终 quiz/test 补足学习闭环。
- planner reduce prompt 现在会读取 `StudyPlanBuildRequest.preference` 派生出的 `planner_strategy`，并显式使用 `content_depth`、`example_intensity`、`assessment_intensity`、`review_intensity` 控制讲解深度、例题、测评和 review 强度。映射为：`fast_track=concise/low/low/low`、`balanced=standard/standard/standard/standard`、`mastery=detailed/high/high/high`、`sprint=focused/standard/high/high`；`advanced` 兼容为 `sprint`，未知或缺省回落 `balanced`。
- planner reduce prompt 同时读取 `StudyPlanBuildRequest.diagnostic_profile` 并按固定优先级合并：用户时间约束 > 诊断得出的必要补基础 > 学习方式 preference 派生配置 > 额外例题、测试、review。`foundation_needed=true` 会进入 `planner_strategy.foundation_required`，即使 `fast_track` 也必须保留前置补基础任务；`weak_topics` 要更靠前更细，`weak_area` 决定概念、计算、应用或记忆的加强方向，`explanation_style` 决定任务 description 风格。该能力仅改变 prompt、preview metadata 和保存追溯，不新增表、不改前端和结构化输出 schema。
- `validate_preview()` 除结构校验外，还会校验生成质量底线：`quiz` 和 `test` 都必须位于当天最后；每个二级任务必须引用资料 chunk；完成型目标每日时长不得明显低于可用时间，最后一天必须包含综合自测。每日任务时长超过 `daily_available_minutes` 时，只有 preview capacity 已明确 `feasibility_status = over_capacity` 且 `warnings` 包含 `PLAN_OVER_CAPACITY` 才允许返回，由前端展示容量 warning；结构非法、日期越界、引用缺失和范围外资料仍返回 `GENERATION_SCHEMA_INVALID`。
- 资料解析层的公式 OCR、图表理解、图片页补全，以及模型 provider 的 `responses.parse` 兼容配置，不属于 study-mode 生命周期模块职责，后续应分别在 materials/parser 和 model provider 任务中处理。

## 模型调用兼容性

- 学习计划配置解析和计划生成仍统一依赖 `ModelProvider.generate_structured()`，业务层不直接关心具体模型供应商。
- `OpenAIModelProvider.generate_structured()` 优先使用 OpenAI Responses API 的结构化解析；当兼容模型服务对 `responses.parse` 返回 404 时，会回退到 Chat Completions，并通过 JSON Schema 提示词和 `response_format={"type":"json_object"}` 获取 JSON，再交给原 Pydantic schema 校验。
- 回退只处理“接口形态不存在”的 404；普通网络、鉴权或服务端错误仍返回 `GENERATION_FAILED`，JSON 解析或 schema 校验失败仍返回 `GENERATION_SCHEMA_INVALID`。

## 不变量

- S02 确认任务树保存和替换都必须在任何计划、任务、打卡写入前完成完整性校验；失败返回 `VALIDATION_ERROR` 或资料 scope 的 `NOT_FOUND`，不得留下部分写入。
- S02 不新增业务表；幂等修复新增 `study_plans.idempotency_key_hash` 和唯一索引迁移，baseline migration 不回改。
- 计划保存只写 `study_plans`、`study_tasks`、`study_subtasks`。
- 未携带 `Idempotency-Key` 的保存请求允许创建多份计划；携带 key 的保存请求必须在数据库唯一约束竞争后恢复为原计划或返回 `IDEMPOTENCY_CONFLICT`，不得暴露 500。
- 计划保存不生成 `handout`、`task_test` 或任何 `ai_generated_contents`。
- 已完成/进行中的二级任务，或已绑定 `ai_generated_contents` 的二级任务，会阻止替换并返回 `STATE_CONFLICT`。
- 每份范围内已解析资料必须进入至少一个 batch；coverage 返回 `expected_material_ids`、`processed_material_ids` 和 `batch_count`。
- Preview 和保存追溯中的 capacity 以最终任务树为事实来源：`estimated_total_minutes = sum(tasks[].subtasks[].estimated_minutes)`，`available_total_minutes = daily_available_minutes * duration_days`；超出容量时必须返回 `PLAN_OVER_CAPACITY` warning。

## 验证

- `uv run python -m alembic upgrade head`：通过，执行 `20260709_0001 -> 20260712_0002 -> 20260712_0003`，其中 `20260712_0003` 新增 `study_plans.idempotency_key_hash` 和唯一索引。
- `uv run python -m pytest tests/modules/study_plans/test_study_plan_quality.py tests/modules/study_plans/test_study_plan_diagnostic_api.py -q`：覆盖 preference -> planner_strategy 派生、unknown/缺省回落 balanced、fast_track + 基础薄弱仍保留补基础、mastery 高强度、sprint 高测评 / review，以及保存追溯中的 `planner_strategy`。
- `uv run python -m pytest tests/modules/study_mode/test_subsystem_schema_contract.py tests/modules/study_plans -q`：`68 passed in 18.11s`，覆盖 schema 契约、计划保存幂等、确认任务树校验和原子替换。
- `uv run python -m pytest tests/modules/study_plans tests/modules/checkins tests/modules/learning_execution tests/modules/todos_calendar tests/integration -q`：`125 passed in 28.53s`，覆盖计划、执行、打卡、日历和集成链路。
- `uv run python -m pytest -q`：`316 passed in 41.41s`。
- 历史真实模型验收报告保留在 `docs/planning/phase-1-validation/`，但不属于本次幂等修复提交范围。
