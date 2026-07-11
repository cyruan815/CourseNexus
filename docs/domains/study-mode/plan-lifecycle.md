# S02 学习计划生命周期实现说明

## 状态

- 日期：2026-07-12
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

## 计划质量约束

- 配置解析 prompt 会说明相对日期规则：用户写明“今天是 YYYY年M月D日”且使用“两天学完 / N 天学完”时，可推导 `start_date` 与 `end_date`。`parse_study_plan_config()` 在模型返回后还会用 `_normalize_relative_config()` 做确定性补全，避免明确日期语义被模型漏填。
- planner map prompt 负责把资料 chunk 按章节/页码顺序抽成细粒度知识单元，要求保留公式、例子、接口、设备、调制/编码/复用、安全隐患等可学习细节，并要求每个知识单元携带 `citation_chunk_ids`。
- planner reduce prompt 负责把知识单元排成可执行计划。生成标题时必须使用课程名称原文；完成型目标需要尽量利用每日可用时间，并通过复习、练习、输出任务和最终 quiz/test 补足学习闭环。
- `validate_preview()` 除结构校验外，还会校验生成质量底线：`quiz` 和 `test` 都必须位于当天最后；每个二级任务必须引用资料 chunk；完成型目标每日时长不得明显低于可用时间，最后一天必须包含综合自测。
- 资料解析层的公式 OCR、图表理解、图片页补全，以及模型 provider 的 `responses.parse` 兼容配置，不属于 study-mode 生命周期模块职责，后续应分别在 materials/parser 和 model provider 任务中处理。
## 模型调用兼容性

- 学习计划配置解析和计划生成仍统一依赖 `ModelProvider.generate_structured()`，业务层不直接关心具体模型供应商。
- `OpenAIModelProvider.generate_structured()` 优先使用 OpenAI Responses API 的结构化解析；当兼容模型服务对 `responses.parse` 返回 404 时，会回退到 Chat Completions，并通过 JSON Schema 提示词和 `response_format={"type":"json_object"}` 获取 JSON，再交给原 Pydantic schema 校验。
- 回退只处理“接口形态不存在”的 404；普通网络、鉴权或服务端错误仍返回 `GENERATION_FAILED`，JSON 解析或 schema 校验失败仍返回 `GENERATION_SCHEMA_INVALID`。

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
- `uv run python -m pytest tests/integrations/test_openai_structured_output.py tests/integrations/test_openai_model_provider.py -q`：`7 passed in 1.31s`，覆盖 Responses API 结构化输出和 Chat Completions JSON fallback。
- `uv run python %TEMP%\course_nexus_os12_report.py`：通过，使用真实 `study_plan_parser` / `study_plan_generator` 配置生成 `docs/planning/phase-1-validation/os-ch12-real-model-preview-2026-07-12.md` 验收报告。
