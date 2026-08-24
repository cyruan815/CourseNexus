# S02 学习计划生命周期实现说明

## 状态

- 日期：2026-07-12
- 状态：已实现并通过自动化验证。
- 范围：单课程学习计划生成、自然语言配置解析、开始前设置配置补问、学前诊断、诊断后 capacity 统计、确认保存、幂等、重生成预览、原子替换和软删除。

## 代码入口

| 层 | 文件 | 责任 |
| --- | --- | --- |
| Router | `backend/app/modules/study_plans/router.py` | 注册学习计划 API，按用途注入配置解析 / 诊断题 / 计划生成 `ModelProvider`，读取 `Idempotency-Key`。 |
| Service | `backend/app/modules/study_plans/service.py` | 权限、配置解析补问字段、诊断题生成、诊断 profile 归纳、全材料预览、保存事务、幂等、替换、重生成和软删除。 |
| Planner | `backend/app/modules/study_plans/planner.py` | map/reduce prompt、结构化生成调用、coverage 和预览校验。 |
| Task tree rules | `backend/app/modules/study_plans/task_tree_rules.py` | Study Plan 层任务树不变量校验，包括每日唯一测试和测试覆盖范围。 |
| Repository | `backend/app/modules/study_plans/repository.py` | active 查询、幂等查询、任务树查询、flush-only 写入和替换辅助。 |
| Schemas | `backend/app/modules/study_plans/schemas.py` | 配置解析、诊断题、诊断 profile、预览、保存、替换和重生成请求/响应结构。 |

## 数据流

1. 自然语言配置回填：`POST /api/v1/courses/{course_id}/study-plan-config-parses` 使用 `study_plan_parser` 模型配置调用 `ModelProvider.generate_structured()` 输出可编辑字段，不写数据库。响应中的 `unresolved_fields` / `unresolved_field_prompts` 表示必须让用户补齐的字段，`needs_confirmation_fields` / `needs_confirmation_field_prompts` 表示建议确认的字段，`field_options` 提供学习方式等中文选项。
2. 开始前设置：前端在同一页面顶部展示配置补问与确认控件，并在下方展示学前诊断。学习目标和资料范围来自第一步，开始前设置页只读展示；如需修改，应返回第一步并重新解析配置、重新生成诊断题。后端 API 字段 `confirmed_config` 表示自然语言解析结果经用户补齐/确认后的有效配置，不代表独立配置确认页。
3. 学前诊断题：`POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions` 使用 `study_plan_diagnostic` 模型配置，根据 `goal_text + confirmed_config + material_scope + chunk excerpts` 选择 3 个资料内 topic 候选；后端映射回当前 chunk、去重并补齐为 3 道 topic mastery 题，同时固定补 weak_area 和 diagnostic_note。
4. 诊断 profile：`POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles` 不调用模型，只校验 question version、topic_id 与当前资料范围匹配关系，并把 3 个 topic mastery 答案、weak_area 和 diagnostic_note 归纳为 `diagnostic_profile`。
5. 预览：`preview_study_plan()` 调用 `iter_material_context_batches()` 读取范围内所有已解析资料批次，再用 `run_material_coverage()` 包住 planner map/reduce，并使用 `study_plan_generator` 模型配置生成计划。map 与 reduce 使用独立的 provider：reduce 使用 `STUDY_PLAN_GENERATOR_*`，map 可通过 `STUDY_PLAN_MAP_*` 配置独立的 API key、base URL 和模型；map 配置未填写时回退到 generator provider，保证旧配置兼容。当前示例组合为 map=`deepseek-v4-flash`、reduce=`deepseek-v4-pro`。`planner.derive_planner_strategy()` 会先把英文 `preference`、可选 `preference_overrides` 和可选 `diagnostic_profile` 合并为 `planner_strategy`，写入 reduce prompt 和 `generation_metadata`。P5a 同步通过 `material_context.summarize_material_quality_for_scope()` 读取同一 `material_scope` 内 parsed 资料的 `parse_quality` / `parse_diagnostics_json`，并写入 `generation_metadata.material_quality.warnings`。`recommended_daily_minutes` 基于 map 阶段材料单元估算；`capacity.estimated_total_minutes` 在 reduce 后基于最终 `tasks[].subtasks[].estimated_minutes` 重新统计。map 阶段支持配置 `STUDY_PLAN_MAP_CONCURRENCY` 的有界并发，默认值为 `1`、允许范围为 `1..5`；只有模型 map 调用并发，资料读取、reduce、后处理、校验和保存保持串行。并发完成顺序不作为业务顺序，runner 按输入 `batch_index` 恢复结果后再交给 reduce。任意 batch 失败都会使本次 preview 失败，不将部分结果交给 reduce；未开始的 future 会被取消。preview 会记录 map/reduce/validation 阶段耗时、batch 数量、并发度和 retry attempt；结构化模型日志还会记录 `prompt_tokens`、`completion_tokens`、`total_tokens` 和 `usage_status`，不记录 prompt 或资料正文。
6. 确认保存：`StudyPlanSaveRequest.client_flow` 默认为 `legacy`；旧客户端不传 `client_flow` 且不传 `tasks` 时，后端先生成真实 preview 再保存。新向导必须传 `client_flow = "wizard_v1"` 并提交 preview 中展示、用户确认后的非空 exact `tasks`；缺失或空数组返回 `422 PREVIEW_TASKS_REQUIRED`，不会进入兼容 preview 生成。显式 `tasks` 会在写库前校验一级/二级任务结构、日期范围、排序连续性，以及所有关联资料是否属于当前用户、当前课程、本次 `material_scope` 且已解析可用；保存追溯中的 `parsed_config_json.tasks_source` 对确认任务树保持 `confirmed`，`parsed_config_json.preference_overrides` 保存原始局部覆盖值，`parsed_config_json.planner_strategy` 由当前 `preference + preference_overrides + diagnostic_profile` 重新派生，`parsed_config_json.capacity` 始终按最终 `tasks` 重新计算。
7. 幂等：保存接口读取 `Idempotency-Key`，将 `key_hash` 写入 `StudyPlan.idempotency_key_hash`，并在 `StudyPlan.parsed_config_json.idempotency` 保存 `key_hash` 与 `request_hash`；同键同请求返回既有 bundle，同键不同请求返回 `IDEMPOTENCY_CONFLICT`。数据库唯一索引 `(user_id, course_id, idempotency_key_hash)` 负责兜底并发重复提交；软删除计划仍占用原 key，不允许复用。
8. 替换：`PUT /api/v1/study-plans/{plan_id}` 先校验无进度、无绑定生成内容和确认任务树完整性，再用 `id + user_id + expected_updated_at + active/deleted` 条件 UPDATE 获取替换权；影响 0 行返回 `STATE_CONFLICT`，影响 1 行后才在同一事务中删除旧任务树、写入新任务树并重算打卡。
9. 重生成：`POST /api/v1/study-plans/{plan_id}/regeneration-previews` 使用 `study_plan_generator` 模型配置，先读取 `StudyPlan.parsed_config_json.confirmed_config` 和顶层追溯配置，再叠加请求覆盖项，只返回 preview，不写数据库。合并规则为：请求字段优先；未传 `diagnostic_profile` 时继承已保存诊断 profile，显式传入新 profile（包括空对象）时覆盖；未传 `preference_overrides` 时继承保存值，显式传入对象时覆盖，显式 `{}` 时清空保存覆盖；只传 `duration_days` 时基于有效 `start_date` 重新推导 `end_date`，只传 `end_date` 时重新计算 `duration_days`，避免复用旧日期造成范围冲突。
10. 删除：`DELETE /api/v1/study-plans/{plan_id}` 写 `status = deleted`、`deleted_at`、`updated_at`，默认 list/detail 隐藏。

## 计划质量约束

- 配置解析 prompt 会说明相对日期规则：用户写明“今天是 YYYY年M月D日”且使用“两天学完 / N 天学完”时，可推导 `start_date` 与 `end_date`。`parse_study_plan_config()` 在模型返回后还会用 `_resolve_config_dates()` 做确定性补全，避免明确日期语义被模型漏填；无法解析或存在歧义的 `start_date`、`duration_days`、`preference` 会进入补问字段，由前端在开始前设置页让用户补齐或确认。
- planner map prompt 负责把资料 chunk 按章节/页码顺序抽成细粒度知识单元，要求保留公式、例子、接口、设备、调制/编码/复用、安全隐患等可学习细节，并要求每个知识单元携带 `citation_chunk_ids`。
- planner reduce prompt 负责把知识单元排成可执行计划。生成标题时必须使用课程名称原文；完成型目标需要尽量利用每日可用时间，并通过复习、练习、输出任务和最终 quiz/test 补足学习闭环。
- planner reduce prompt 明确目录页、主要内容页、版权页、感谢页和章节小结页不能作为普通 `learn` 任务引用；小结页只允许进入 `review` 或 `quiz/test` 的辅助引用。`preview_study_plan()` 在校验前会做确定性后处理：仅当 chunk 的结构化 heading 或正文首个非空行完整匹配受控元信息标题时，才把它识别为元信息；不再用 `summary` / `总结` 子串扫描正文，因此 `Summary Statistics`、`数据总结方法` 等正常知识内容不会被误删。若 `learn` 同时引用正文 chunk 和元信息 chunk，只保留正文引用；保存确认任务树时也会复用该清理规则。
- planner reduce prompt 现在会读取 `StudyPlanBuildRequest.preference` 派生出的 `planner_strategy`，并显式使用 `content_depth`、`example_intensity`、`assessment_intensity`、`review_intensity` 控制讲解深度、例题、测评和 review 强度。映射为：`fast_track=concise/low/low/low`、`balanced=standard/standard/standard/standard`、`mastery=detailed/high/high/high`、`sprint=focused/standard/high/high`；`advanced` 兼容为 `sprint`，未知或缺省回落 `balanced`。
- planner reduce prompt 同时读取 `StudyPlanBuildRequest.diagnostic_profile` 并按固定优先级合并：用户时间约束 > 诊断得出的必要补基础 > 学习方式 preference 派生配置 > 额外例题、测试、review。`diagnostic_profile` 来自开始前设置页的学前诊断答案归纳。`foundation_needed=true` 会进入 `planner_strategy.foundation_required`，即使 `fast_track` 也必须保留前置补基础任务；`weak_topics` 要更靠前更细，`weak_area` 决定概念、计算、应用或记忆的加强方向，`explanation_style` 决定任务 description 风格。该能力仅改变 prompt、preview metadata 和保存追溯，不新增表、不改前端和结构化输出 schema。
- `validate_preview()` 除结构校验外，还会校验生成质量底线：每个一级任务必须且只能包含一个 `quiz` / `test`，并且该测试必须是当天最后一个二级任务；每个二级任务必须引用资料 chunk；完成型目标每日时长不得明显低于可用时间。非最后一天的测试覆盖当天前置 `learn` / `review` 的资料和 chunk；最后一天的测试是全计划综合测试，覆盖全计划所有非测试任务的资料和 chunk，不再额外安排当天测试。每日任务时长超过 `daily_available_minutes` 时，只有 preview capacity 已明确 `feasibility_status = over_capacity` 且 `warnings` 包含 `PLAN_OVER_CAPACITY` 才允许返回，由前端展示容量 warning；结构非法、日期越界、引用缺失和范围外资料仍返回 `GENERATION_SCHEMA_INVALID`。
- Study Mode 只消费 materials 已持久化的解析质量摘要，不直接调用 parser，也不解释 Docling 内部类型。`parse_quality = partial` 或 `unknown` 会转成 `MATERIAL_PARSE_PARTIAL` / `MATERIAL_PARSE_QUALITY_UNKNOWN`；`parse_diagnostics_json.warnings[]` 中 `severity = "warning"` 的条目会转成 `MATERIAL_PARSE_DIAGNOSTIC_WARNING`，原始 parser code/message 保存在 `details.diagnostic_code` 和 `details.diagnostic_message`；`severity = "info"` 不升级为 preview warning。
- 资料解析质量 warning 只写入 `generation_metadata.material_quality.warnings`，不得写入 `capacity.warnings`。P5a 不新增 block 策略，`NO_PARSED_MATERIAL` 和 `MATERIAL_COVERAGE_INCOMPLETE` 保持原有阻断语义。
- 资料解析层的公式 OCR、图表理解、图片页补全，以及模型 provider 的 `responses.parse` 兼容配置，不属于 study-mode 生命周期模块职责，后续应分别在 materials/parser 和 model provider 任务中处理。

## 模型调用兼容性

- 学习计划配置解析和计划生成仍统一依赖 `ModelProvider.generate_structured()`，业务层不直接关心具体模型供应商。
- `OpenAIModelProvider.generate_structured()` 优先使用 OpenAI Responses API 的结构化解析；当兼容模型服务对 `responses.parse` 返回 404 时，会回退到 Chat Completions，并通过 JSON Schema 提示词和 `response_format={"type":"json_object"}` 获取 JSON，再交给原 Pydantic schema 校验。
- 回退只处理“接口形态不存在”的 404；普通网络、鉴权或服务端错误仍返回 `GENERATION_FAILED`，JSON 解析或 schema 校验失败仍返回 `GENERATION_SCHEMA_INVALID`。
- `OpenAIModelProvider` 会从 Chat Completions 的 `usage.prompt_tokens` / `completion_tokens` 和 Responses API 的 `usage.input_tokens` / `output_tokens` 统一提取 token 指标；响应没有 usage 时记录 `usage_status=unavailable`，不自行估算。真实资料验证入口为 `backend/scripts/measure_study_plan_token_usage.py`，报告放在 `docs/domains/study-mode/validation/`。

## 不变量

- S02 确认任务树保存和替换都必须在任何计划、任务、打卡写入前完成完整性校验；失败返回 `VALIDATION_ERROR` 或资料 scope 的 `NOT_FOUND`，不得留下部分写入。该校验复用 Study Plan 层的每日唯一测试规则，防止前端绕过 preview 提交缺少测试、多测试、测试不在最后或覆盖范围不完整的任务树。`client_flow = "wizard_v1"` 的保存请求必须额外在 preview 生成前校验 `tasks` 非空，失败返回 `PREVIEW_TASKS_REQUIRED`。
- S02 不新增业务表；幂等修复新增 `study_plans.idempotency_key_hash` 和唯一索引迁移，baseline migration 不回改。
- 计划保存只写 `study_plans`、`study_tasks`、`study_subtasks`。
- 未携带 `Idempotency-Key` 的保存请求允许创建多份计划；携带 key 的保存请求必须在数据库唯一约束竞争后恢复为原计划或返回 `IDEMPOTENCY_CONFLICT`，不得暴露 500。
- 计划保存不生成 `handout`、`task_test` 或任何 `ai_generated_contents`。
- 已完成/进行中的二级任务，或已绑定 `ai_generated_contents` 的二级任务，会阻止替换并返回 `STATE_CONFLICT`。
- 每份范围内已解析资料必须进入至少一个 batch；coverage 返回 `expected_material_ids`、`processed_material_ids` 和 `batch_count`。
- Preview 和保存追溯中的 capacity 以最终任务树为事实来源：`estimated_total_minutes = sum(tasks[].subtasks[].estimated_minutes)`，`available_total_minutes = daily_available_minutes * duration_days`；总时长超出总容量或任一天任务时长超过 `daily_available_minutes` 时，都必须返回 `PLAN_OVER_CAPACITY` warning。
- Preview 的资料解析质量 warning 以当前 material-context scope 内 parsed 资料为事实来源，只进入 `generation_metadata.material_quality.warnings`；不得改变 capacity 计算，也不得把显式未 parsed 资料升级为新的 P5a 阻断。

## 验证

- `uv run python -m compileall app/modules/material_context app/modules/study_plans/service.py`：通过，覆盖 touched 后端模块语法检查。
- `uv run python -m pytest tests/modules/material_context/test_material_context_batches.py tests/modules/study_plans/test_study_plan_foundation.py -q`：`10 passed in 2.00s`，覆盖 P5a material-context 解析质量摘要、preview `generation_metadata.material_quality.warnings` 接入，并确认解析 warning 不进入 `capacity.warnings`。
- `uv run python -m pytest tests/modules/study_plans/test_study_plan_lifecycle.py tests/modules/study_plans/test_study_plan_lifecycle_api.py -q`：`50 passed in 18.43s`，覆盖 P10 重生成 preview 继承已保存 `diagnostic_profile`、显式 profile 覆盖、只传 `duration_days` 重新推导 `end_date`，以及 preview 不写计划 / 任务 / 打卡记录。
- `uv run python -m pytest tests/modules/study_plans/test_study_plan_quality.py tests/modules/study_plans/test_study_plan_lifecycle_api.py -q`：`37 passed in 15.48s`，覆盖 `client_flow` 默认 `legacy`、`wizard_v1` 缺失 / 空 `tasks` 返回 `PREVIEW_TASKS_REQUIRED`、旧客户端兼容保存和新向导 exact tasks 保存。
- `uv run python -m alembic upgrade head`：通过，执行 `20260709_0001 -> 20260712_0002 -> 20260713_0003 -> 20260713_0004`，其中 `20260713_0004` 新增 `study_plans.idempotency_key_hash` 和唯一索引。
- `uv run python -m pytest tests/modules/study_plans/test_study_plan_quality.py tests/modules/study_plans/test_study_plan_diagnostic_api.py -q`：覆盖 preference -> planner_strategy 派生、unknown/缺省回落 balanced、fast_track + 基础薄弱仍保留补基础、mastery 高强度、sprint 高测评 / review，以及保存追溯中的 `planner_strategy`。
- `uv run python -m pytest tests/modules/study_mode/test_subsystem_schema_contract.py tests/modules/study_plans -q`：`68 passed in 18.11s`，覆盖 schema 契约、计划保存幂等、确认任务树校验和原子替换。
- `uv run python -m pytest tests/modules/study_plans tests/modules/checkins tests/modules/learning_execution tests/modules/todos_calendar tests/integration -q`：`125 passed in 28.53s`，覆盖计划、执行、打卡、日历和集成链路。
- `uv run python -m pytest -q`：`316 passed in 41.41s`。

## 2026-07-14 前端 C10 计划重生成 / 替换 / 删除接入

`frontend/src/pages/StudyPlanDetailPage.tsx` 已接入 S02 生命周期接口，入口集中在学习计划详情页，不新增独立路由。

- 点击“重新生成”会展开详情页内生命周期面板。用户可调整 `goal_text`、`start_date`、`end_date`、`daily_available_minutes` 和 `preference`；前端只提交这些本次覆盖字段到 `POST /api/v1/study-plans/{plan_id}/regeneration-previews`。
- 重生成 preview 只展示新任务树摘要，不写入数据库；用户确认前不会替换当前计划，也不会生成讲义、任务测试题或导出文件。
- 点击“确认替换计划”调用 `PUT /api/v1/study-plans/{plan_id}`。请求体使用后端返回 preview 的 `title`、`tasks`、`material_scope` 和生成追溯字段，并强制 `client_flow = "wizard_v1"`；`expected_updated_at` 来自当前详情页 `plan.updated_at`，用于后端原子并发校验。
- 替换成功后，前端用返回的 `StudyPlanDetail` 更新当前页面；替换失败不会清空旧计划。`STATE_CONFLICT` 统一解释为计划已有学习进度、已有绑定生成内容或已被其他请求更新，前端提示刷新或新建计划，不提供强制覆盖按钮。
- 点击“删除计划”先进入二次确认。确认后调用 `DELETE /api/v1/study-plans/{plan_id}`，成功回到 `/courses/{course_id}`。删除仍是后端软删除，不删除课程资料、问答历史或已存在的生成内容。
- C10 不修改 `frontend/src/pages/GeneratedContentDetailPage.tsx`、`frontend/src/features/generated-content/` 或对应测试；若替换被已绑定生成内容阻止，前端只展示冲突提示。

前端测试入口：

- `frontend/tests/pages/study-plan-pages.test.tsx` 覆盖重生成 preview、确认替换 payload、删除二次确认和返回课程。
- `frontend/tests/features/study-plans/api.test.ts` 覆盖生命周期 adapter 的 path / method / body。

当前本地 Vitest 仍可能在收集阶段被 `entities ./decode` exports 问题阻断；C10 提交以 `frontend:build`、`git diff --check` 和后续依赖修复后的 Vitest 共同验证。
## 2026-07-13 计划保存参数快照补充

- 保存和替换计划时，`parsed_config_json.task_snapshot` 会保存每个二级任务的排序、类型、关联资料和必要生成参数；quiz/test 子任务额外保存 `generation_parameters.task_test`。
- 该参数快照用于后续 task-test 按需生成的默认参数，避免计划写着“10 道选择题和 3 道计算题”但实际请求只生成 3 题。
- Preview 在结构校验前会确定性归一化同一天的二级任务顺序：`learn/review` 保持在前，`quiz/test` 移到当天最后并重排 `sort_order`；质量门仍保留“自测任务必须排在当天最后”的兜底校验。
- 真实模型输出的二级任务类型别名会在 schema 层归一化为规范枚举：`practice` / `exercise` / `drill` / `assessment` 归一到 `quiz`，`exam` / `final-test` / `comprehensive-test` 归一到 `test`；入库和 API 响应仍只保存 `learn` / `review` / `quiz` / `test`。
- 保存计划阶段仍只写 `study_plans`、`study_tasks` 和 `study_subtasks`，不创建 `AIGeneratedContent`、`SourceCitation` 或导出文件。
- `generation_parameters.task_test` 接受规范对象，也兼容模型常见别名：按题型计数对象 `{"single_choice": 10, "short_answer": 3}`、题型计数列表 `[{"question_count": 10, "question_type": "single_choice"}, {"question_count": 3, "question_type": "short_answer"}]`、`question_types` / `items` / `question_type_counts` 内嵌 `{type,count}` 或 `{question_type,question_count}` 对象并可带 `total_question_count`，以及题量文案映射 `{"10道选择题": "single_choice", "3道计算题": "short_answer"}`；也兼容 `task_test: "single_choice"` 搭配同级 `question_count` 的模型 shorthand。保存快照前统一归一化为 `question_count`、`question_types`、可选 `question_type_counts` 和 `difficulty`。当 `question_type_counts` 存在时，`question_count` 自动等于各题型数量总和，`question_types` 自动等于题型顺序去重结果。
- 非法 `generation_parameters.task_test` 在保存/替换时返回 `VALIDATION_ERROR`；旧计划中若存在脏默认参数，运行 task-test 生成时返回 `GENERATION_SCHEMA_INVALID` 并保存 failed 生成记录。
- task-test 按需生成合并计划默认参数和本次请求时，显式 per-type counts 会覆盖快照分布；仅覆盖 `difficulty` 会保留快照分布；显式传 `question_count` 或字符串数组 `question_types` 但未传 per-type counts 时，会清掉快照里的 `question_type_counts`，退回旧的总题数 + 题型白名单契约。

## 2026-07-14 每日唯一测试约束

新生成和新保存的 study-mode 计划必须保持学习闭环：每个一级任务 `StudyTask` 必须且只能包含一个测评型 subtask，`subtask_type` 为 `quiz` 或 `test`，并且它必须是该一级任务的最后一个二级任务。`learn` / `review` 子任务用于讲义学习、回顾和练习，必须排在测评型子任务之前。

该约束的含义：

- 任务类型边界必须稳定：`learn` 是学习讲义任务，用于学习新内容；`review` 是复习讲义任务，只能回顾此前已经安排学习过的内容；`quiz` / `test` 是测试题任务。
- `learn` / `review` 不得携带 `generation_parameters.task_test`，也不得在标题或描述中写“几道选择题、几道计算题”等明确测试题量；题量要求必须放入当天最后的 `quiz` / `test`。
- planner preview 阶段会提示模型按每日唯一测试规则输出，并在 `validate_preview()` 中拒绝非法任务树。
- 保存 exact tasks 和替换计划时仍要校验最终任务树；如果某个一级任务没有测试、存在多个测试、测试不在最后或覆盖范围不完整，应返回稳定校验错误，而不是保存半闭环计划。
- 非最后一天测试是“当日测试”，其 `related_material_ids` 和 `citation_chunk_ids` 必须覆盖当天前置 `learn` / `review` 的资料并集和 chunk 并集。
- 最后一天测试是“全计划综合测试”，其 `related_material_ids` 和 `citation_chunk_ids` 必须覆盖全计划所有非测试任务的资料并集和 chunk 并集；最后一天不再额外安排当天测试。
- quiz/test 子任务继续通过 `POST /api/v1/study-subtasks/{subtask_id}/task-tests` 按需生成 `task_test`；learn/review 子任务通过 `POST /api/v1/study-subtasks/{subtask_id}/handouts` 按需生成 `handout`。
- 前端可把新计划的一级任务最后一个子任务视为测试入口，但读取历史计划时仍应容忍异常顺序：按后端返回的 `subtask_type` 决定展示“生成讲义”或“生成任务测试题”，不要只靠位置判断能力。

测试入口：`backend/tests/modules/study_plans/test_study_plan_quality.py` 覆盖 preview 规则；`test_study_plan_lifecycle.py` 覆盖保存/替换与 `task_snapshot.generation_parameters.task_test`；`test_study_plan_api.py` 覆盖 API 保存非法任务树返回 `VALIDATION_ERROR`。
