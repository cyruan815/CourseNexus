# Study Mode 计划生成向导设计

## 状态

- 日期：2026-07-14
- 状态：设计已确认；后端每日学习时间自动估算、配置补问字段、学前诊断接口、diagnostic_profile 影响 planner 策略、preference 派生 `planner_strategy` 和诊断后 capacity 闭环已实施。前端完整自然语言向导尚未接入，当前主页面仍是手动配置 + preview 的契约稳定版。
- 范围：从用户点进学习计划生成开始，到自然语言配置解析、开始前设置中的配置补问与学前诊断、计划 preview、确认保存和进入计划详情为止的前端页面流、配置字段、学前诊断、后端契约和状态失效规则。

## 2026-07-14 前端 C13 落地说明

当前前端创建页已按“目标输入 + 资料范围 + 必选学情诊断 + 预览确认”落地，不再把开始日期、结束日期、每日时长和学习方式作为首屏大表单展示，也不再在前端单独补问日期。

- 自然语言解析出的 `start_date`、`duration_days` / `end_date`、`daily_available_minutes` 和 `preference` 会作为确认配置进入诊断题请求。
- 由于后端 `StudyPlanBuildRequest` 当前仍强制要求 `start_date`，并要求 `end_date` 或 `duration_days` 至少一个，而诊断 profile 还不补回日期或天数，若自然语言没有解析出日期，preview 可能仍由后端返回校验错误。后续应由后端诊断题或 build 契约承接缺失日期，不再回到前端日期兜底表单。
- 学情诊断在创建页为必填；没有 `diagnostic_profile` 时不生成 preview。
- `daily_available_minutes` 不必填；只有自然语言明确解析出有效分钟数时才提交，否则由后端估算。
- 计划 preview 使用大 Modal 展示，Modal 内完成重新生成和保存；保存仍提交 `client_flow = "wizard_v1"` 与用户看到的 exact preview tasks。
- “指定资料”模式从 0 份已选开始，未勾选任何 parsed 资料时前端提示必须选择至少一份资料。
- 预览和详情页的任务说明改为用户阅读结构：按 `含义 / 条件 / 步骤 / 练习检查` 等片段分行；详情页隐藏内部 `mat_xxx` 资料 ID。

## 已实施入口：每日学习时间规则

2026-07-12 已落地后端 daily minutes 规则，范围仅包含 `recommended_daily_minutes` / `daily_available_minutes` / `daily_minutes_source`、capacity 和保存追溯，不包含每日测试任务、诊断向导前端、讲义或测试题幂等。

- Schema：`backend/app/modules/study_plans/schemas.py` 中 `StudyPlanBuildRequest.daily_available_minutes` 允许省略；传入时后端校验最低 30 分钟。
- Preview 服务：`backend/app/modules/study_plans/service.py::preview_study_plan` 在资料 map 之后按 `max(30, ceil(estimated_total_minutes / duration_days))` 计算新的 `recommended_daily_minutes`；未传每日时间时采用推荐值，传入 `user_modified` 时保留前端值。
- Prompt 边界：`backend/app/modules/study_plans/planner.py::_build_map_prompt` 在每日时间尚未解析时标记为 `auto`，reduce 阶段只接收已解析的最终每日时间。
- 保存追溯：`StudyPlan.parsed_config_json` 写入 `confirmed_config`、`recommended_daily_minutes`、`daily_minutes_source` 和 `capacity`；`study_plans.daily_available_minutes` 存最终采用值。
- 测试入口：`backend/tests/modules/study_plans/test_study_plan_quality.py`、`test_study_plan_lifecycle.py`、`test_study_plan_lifecycle_api.py`。

## 已实施入口：学前诊断后端接口

2026-07-13 已升级为学前诊断题 v2，范围包含后端 API、schema、独立模型 purpose、资料范围校验、模型输出校验、确定性 fallback、profile 归纳和文档；不包含开始前设置页前端 UI，不新增诊断 session 表。详细设计见 [diagnostic-questions.md](diagnostic-questions.md)。

- Router：`backend/app/modules/study_plans/router.py` 暴露 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions` 和 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles`。
- Schema：`backend/app/modules/study_plans/schemas.py` 定义 `StudyPlanDiagnosticQuestionRequest`、`StudyPlanDiagnosticQuestionsResponse`、`StudyPlanDiagnosticProfileRequest` 和 `StudyPlanDiagnosticProfileResponse`；`question_version` 固定为 `study_plan_diagnostic_v2`。
- 模型配置：新增 purpose `study_plan_diagnostic`，使用 `STUDY_PLAN_DIAGNOSTIC_API_KEY`、`STUDY_PLAN_DIAGNOSTIC_BASE_URL`、`STUDY_PLAN_DIAGNOSTIC_MODEL`，不得复用 parser 或 planner 配置。
- Service：`backend/app/modules/study_plans/service.py::build_study_plan_diagnostic_questions` 复用 `iter_material_context_batches()` 校验资料属于当前用户、当前课程且已解析；正常路径由 LLM 根据 `goal_text + confirmed_config + material_scope + chunk excerpts` 选择 topic 候选，后端映射回当前 chunk、去重并固定输出 3 道 `topic_mastery`。
- Fallback：模型失败、输出不足 3 个、重复或无法映射到当前资料范围时，后端从模型已通过校验的 seed、chunk heading、正文片段和首个 chunk 拆分补足到 3 道；`generation_metadata.diagnostic_questions` 记录 `source` 和 `fallback_reason`。
- Profile 归纳：`build_study_plan_diagnostic_profile` 要求 exactly 3 个 `topic_mastery` 答案，校验 `question_version` 和 `topic_id` 是否仍属于当前资料范围；不匹配返回 `DIAGNOSTIC_STALE`。`none` / `heard` 视为弱掌握，弱掌握超过一半时 `foundation_needed=true`，`weak_topics` 保留弱 topic id。
- 薄弱方向：前端只展示 `weak_area` 问题，不展示讲课风格选择。后端可继续从 `weak_area` 派生内部 `explanation_style` 供现有 planner 兼容使用，不能把它当作用户选择的讲课风格。
- 数据流：诊断 profile 响应可直接作为 `StudyPlanBuildRequest.diagnostic_profile` 传给 `POST /api/v1/courses/{course_id}/study-plans/preview`；preview 会把 diagnostic_profile 摘要写入 planner reduce prompt，影响补基础、任务顺序、主题颗粒度、薄弱方向强化和 description 表达。
- 失败与补偿：无 parsed 资料返回 `NO_PARSED_MATERIAL`；资料范围越界沿用 material context 的 `NOT_FOUND` / 覆盖错误；旧诊断答案或版本不匹配返回 `DIAGNOSTIC_STALE`，前端应回到学前诊断重新作答。
- 复杂度与资源预算：正常路径 1 次结构化模型调用；topic 校验和 fallback 扫描当前资料范围批次，时间复杂度 O(chunks + fragments)，最多返回 3 个 topic，不写数据库。
- 测试入口：任务七前只做编译级验证；密钥配置后应补充 `backend/tests/modules/study_plans/test_study_plan_diagnostic_api.py` 对模型正常、模型失败 fallback、exactly 3、旧 topic 拒绝和 profile 继续传入 preview 的覆盖。
## 已实施入口：diagnostic_profile 影响 planner

2026-07-12 已落地 diagnostic_profile 到 planner reduce prompt 的策略注入。范围仅包含后端 planner prompt、preview 链路测试和领域文档；不新增数据库表，不改前端，不新增核心依赖，不绕过 `ModelProvider.generate_structured()` 和现有 map/reduce 流程。

- Planner：`backend/app/modules/study_plans/planner.py::_build_reduce_prompt` 会展开 `StudyPlanBuildRequest.diagnostic_profile` 摘要，包含 `foundation_needed`、`weak_topics`、`weak_area`、`explanation_style` 和 `diagnostic_note`。
- 补基础：`foundation_needed=true` 时，reduce prompt 明确要求前置补基础任务，优先放在第一天或最早可行日期；因现有 schema 不新增 `foundation` 类型，任务仍使用 `learn` / `review`，在标题或 description 中体现“补基础”。
- 薄弱主题：`weak_topics` 对应主题需更靠前、更细，能在任务标题、description 或排序中看到差异。
- 薄弱方向：`concept` 强化概念解释，`calculation` 强化公式、步骤推导和计算练习，`application` 强化例题和应用任务，`memorization` 强化重点记忆、回顾和检查。
- 解释风格：`explanation_style` 进入 reduce prompt，要求任务 description 匹配 `plain_language`、`step_by_step`、`example_first` 或 `exam_focused` 的描述风格。
- 测试入口：`backend/tests/modules/study_plans/test_study_plan_quality.py` 覆盖 reduce prompt 内容和四类 `weak_area` 规则；`backend/tests/modules/study_plans/test_study_plan_diagnostic_api.py` 用同一份资料、不同 diagnostic_profile 验证 preview 传给 planner 的策略不同。

## 已实施入口：学习方式 preference 派生 planner_strategy

2026-07-12 已落地学习方式 preference 到 planner 可用底层策略的稳定派生。范围包含后端派生函数、planner reduce prompt、preview metadata、保存追溯、测试和文档；不新增数据库表、不新增请求字段，不把中文学习方式写入后端契约。

- 派生入口：`backend/app/modules/study_plans/planner.py::derive_planner_strategy` 使用 `_PREFERENCE_PLANNER_STRATEGIES` 将 `fast_track`、`balanced`、`mastery`、`sprint` 派生为 `content_depth`、`example_intensity`、`assessment_intensity`、`review_intensity`；历史 `advanced` 兼容为 `sprint`，未知或缺省回落 `balanced`。
- Prompt：`planner.py::_build_reduce_prompt` 会写入 `planner_strategy`，明确要求 planner 使用四个派生字段，并声明合并优先级：用户时间约束 > 诊断得出的必要补基础 > 学习方式 preference 派生配置 > 额外例题、测试、review。
- 诊断合并：`diagnostic_profile.foundation_needed=true` 会派生为 `foundation_required=true`；即使 `preference=fast_track`，prompt 也要求保留前置补基础任务，压缩拓展讲解和重复练习而不是删除补基础。
- 追溯：`backend/app/modules/study_plans/service.py::preview_study_plan` 将 `planner_strategy` 写入 `generation_metadata`；`_saved_config` 和 `confirmed_config` 保存同一派生结果，供后续讲义、任务测试和 review 生成直接读取。
- 前端契约：UI 展示中文“快速通关 / 均衡学习 / 深入掌握 / 冲刺强化”，API 请求和响应仍只使用英文枚举 `fast_track`、`balanced`、`mastery`、`sprint`。
- 测试入口：`backend/tests/modules/study_plans/test_study_plan_quality.py` 覆盖映射、unknown/default 回落、mastery/sprint 强度和 prompt；`backend/tests/modules/study_plans/test_study_plan_diagnostic_api.py` 覆盖 fast_track/诊断补基础策略可保留补基础和保存追溯。


## 已实施入口：诊断后 capacity 闭环

2026-07-12 已落地诊断影响 planner 后的 capacity 闭环。范围仅包含 preview/save 容量统计、模型输出校验边界、测试和文档；不新增数据库表，不写 migration，不新增核心依赖。

- Preview 服务：`backend/app/modules/study_plans/service.py::preview_study_plan` 在 reduce 得到最终 `coverage_result.value.tasks` 后，用最终二级任务分钟数重算 `capacity.estimated_total_minutes`，公式为 `sum(preview.tasks[].subtasks[].estimated_minutes)`。
- 每日建议值：`recommended_daily_minutes` 继续使用 map 阶段材料单元规模估算，避免模型 reduce 输出的任务拆分反过来改变系统建议值；`daily_available_minutes` 仍按用户输入或系统估算解析。
- 容量状态：`available_total_minutes = daily_available_minutes * duration_days`；当最终任务总时长超出容量时，`feasibility_status = "over_capacity"` 且 `warnings` 包含 `PLAN_OVER_CAPACITY`；接近容量时保持 `tight`。
- Preview 校验：`backend/app/modules/study_plans/planner.py::validate_preview` 继续硬校验结构非法、日期越界、任务类型、测验排序、引用缺失和范围外资料；其中每个一级任务必须且只能有一个 `quiz/test`，且必须是当天最后一个二级任务，不允许“阶段练习 + 综合测试”这类多个 assessment。仅当 preview 已携带 `over_capacity` 和 `PLAN_OVER_CAPACITY` 时，允许每日任务时长超出用户每日可用时间，由 capacity warning 交给前端展示和引导调整。
- 保存追溯：`backend/app/modules/study_plans/service.py::_resolve_save_payload_daily_minutes` 和 `_saved_config` 都以最终提交的 `tasks` 重新计算 capacity，`StudyPlan.parsed_config_json.capacity` 不信任旧客户端传入的过期 capacity。
- 测试入口：`backend/tests/modules/study_plans/test_study_plan_diagnostic_api.py` 覆盖同一资料和时间约束下，`foundation_needed=true` 让最终任务分钟数增加，并使 capacity 从 `tight` 变为 `over_capacity`；同时覆盖保存后 `parsed_config_json.capacity` 追溯最终 capacity。

## 目标

计划生成向导要把“用户想怎么学”和“用户现在会多少”分开处理。

- 自然语言解析和配置补问回答“用户想怎么学”。
- 学前诊断回答“用户现在会多少”。
- 计划 preview 基于配置和诊断共同生成。
- 确认保存时，保存用户实际看到并确认的 preview 任务，不重新生成另一份计划。

## 非目标

- 不在本任务中实现资料解析漏页、OCR 降级或 material diagnostics。
- 不在本任务中实现正式任务讲义、测试题或 review 内容生成，只为后续生成提供配置和诊断输入。
- 不把讲义详细程度、例题数量、测试数量作为前端主界面独立选项。
- 第一版不实现异步 preview 任务队列，也不引入独立持久化的 `preview_id`。

## 总体方案

第一版采用方案 A：

- preview 不单独入库，也不返回长期有效的 `preview_id`。
- 前端在保存时提交“用户刚刚看到的任务列表 + 补齐后的有效配置 + 诊断 profile + 资料快照标识”。
- 后端保存新流程提交的 exact preview tasks，不在保存接口里重新调用大模型生成计划。
- 旧客户端如果没有提交 tasks，可以保留原有保存时生成的兼容路径；新向导必须提交 tasks。
- 保存接口需要幂等保护，避免用户连续点击导致重复计划。

## 页面流

推荐使用同一页面内的轻量步骤状态，而不是多个孤立页面或重弹窗。

```text
/courses/:courseId/study-plans/new

goal_input
  -> setup(config_supplement + diagnostic)
  -> preview
  -> saved plan detail
```

前端可展示轻量步骤条：

```text
输入目标 / 开始前设置 / 计划预览
```

这里的 stepper 是页面内的进度提示和状态机，不是独立路由。用户能看到当前处在哪一步，但页面主体仍是同一个计划生成工作流。

## Step 1：输入目标和选择资料

用户在第一步完成自然语言输入、资料勾选或资料上传。

页面职责：

- 输入学习目标。
- 选择参与计划生成的资料范围。
- 上传新资料后，等待资料解析状态满足计划生成要求。

前端提交：

```json
{
  "goal_text": "我要两天学完计网第七章，今天是2026年7月12日",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_xxx"]
  }
}
```

后端调用：

```text
POST /api/v1/courses/{course_id}/study-plan-config-parses
```

资料范围约束：

- 只能使用当前课程、当前用户有权限访问且解析完成的资料。
- `material_ids` 需要去重，且不能为空。
- `include_all_parsed_materials=true` 表示使用当前课程下“此刻已解析完成”的资料集合，后续新上传资料不会自动改变已生成计划的范围。
- 资料处于 parsing、failed 或不属于当前课程时，不能进入下一步，需要给出明确提示。

## Step 2：开始前设置

开始前设置页合并展示两类内容：

```text
配置补问与确认
学前诊断
```

本流程不再设置独立的“配置确认页”。自然语言解析缺失或不确定的关键字段由 `study-plan-config-parses` 响应中的 `unresolved_field_prompts`、`needs_confirmation_field_prompts` 和 `field_options` 驱动，前端在开始前设置页顶部用对应控件让用户补齐或确认。

配置补问区围绕 5 个字段：

```text
学习目标
学习日期 / 学习天数
每日学习时间
学习方式
资料范围
```

学习目标和资料范围在第一步确定；开始前设置页不直接修改学习目标。若用户要改学习目标或资料范围，应返回第一步重新输入或重新选择，并重新调用配置解析、重新生成诊断题。资料范围不是普通本地字段，变化后必须重新解析配置并重新估算学习时间，因为资料范围影响知识点数量、预计总学习时长、学前诊断题目和最终计划内容。

### 前端展示字段

开始前设置页所有用户可见文案必须使用中文。API 内部字段名和枚举值继续保留英文契约，但前端不得直接展示 `start_date`、`duration_days`、`daily_available_minutes`、`preference`、`material_scope`、`balanced`、`include_all_parsed_materials` 等内部值。配置解析响应会额外返回中文展示辅助字段：`field_labels`、`unresolved_field_prompts`、`needs_confirmation_field_prompts` 和 `field_options`，前端应优先使用这些中文 label、message 和 option label。

| 字段 | 开始前设置页处理 | 说明 |
| --- | --- | --- |
| `goal_text` | 只读展示；如需修改返回第一步 | 用户学习目标，来自第一步自然语言输入。 |
| `start_date` / `duration_days` | 缺失或不确定时补问/确认 | 后端按本地日期计算 `end_date`。 |
| `daily_available_minutes` | 明确填写时保留；缺失时可不阻断，后续由资料 map 后估算 | 每日学习时间低于 30 分钟时前端阻止提交，后端也校验。 |
| `preference` | 始终建议确认，缺失时必选 | 学习方式：快速、均衡、深入、冲刺。 |
| `material_scope` | 只读展示；如需修改返回第一步 | 修改后触发重新解析、重新生成诊断题和 preview。 |

日期来源规则：

- 请求中以 `start_date + duration_days` 作为唯一可编辑来源。
- `end_date = start_date + duration_days - 1` 由后端按用户本地日期计算。
- 响应可以同时返回 `start_date`、`duration_days` 和 `end_date`，供前端展示。

### 每日学习时间规则

每日学习时间需要区分“系统建议值”和“最终采用值”。

```json
{
  "recommended_daily_minutes": 90,
  "daily_available_minutes": 60,
  "daily_minutes_source": "user_modified",
  "estimated_total_minutes": 180,
  "available_total_minutes": 120,
  "feasibility_status": "tight"
}
```

字段含义：

| 字段 | 说明 |
| --- | --- |
| `recommended_daily_minutes` | 系统根据资料内容量、学习天数和最低时长估算出的建议每日分钟数。 |
| `daily_available_minutes` | 最终采用的每日学习时间，前端始终展示且允许用户修改。 |
| `daily_minutes_source` | `user_text`、`system_estimated` 或 `user_modified`。 |
| `estimated_total_minutes` | 当前资料范围和学习方式下的预计总学习分钟数。 |
| `available_total_minutes` | `daily_available_minutes * duration_days`。 |
| `feasibility_status` | `ok`、`tight` 或 `over_capacity`，用于提示时间是否充足。 |

如果用户自然语言中明确说了每天学多久：

```text
daily_available_minutes = 用户输入的分钟数
recommended_daily_minutes = 系统根据资料估算出的建议值
daily_minutes_source = user_text
```

如果用户没有说明每天学多久：

```text
recommended_daily_minutes = max(30, ceil(资料总预计学习分钟数 / 学习天数))
daily_available_minutes = recommended_daily_minutes
daily_minutes_source = system_estimated
```

用户在开始前设置页补齐或确认后：

```text
daily_available_minutes = 用户修改值
daily_minutes_source = user_modified
```

最低每日学习时间为 30 分钟。该值是系统底线，不作为前端主配置项展示；低于 30 分钟时前端应阻止提交，后端也要校验。

### 资料范围变化后的字段保留规则

资料范围变化后，前端重新调用配置解析 / 估算接口。字段合并规则：

```text
用户手动修改过的学习目标、日期、学习方式、每日学习时间优先保留。
系统估算字段可以被新结果覆盖。
如果每日学习时间是 user_modified，则保留用户值，同时展示新的系统建议值。
```

示例提示：

```text
资料范围已变化。根据新资料，系统建议每日学习 90 分钟；你当前保留的是 60 分钟。
```

## 学习方式

前端只展示 4 个用户可理解的学习方式：

| 前端文案 | 后端值 | 说明 |
| --- | --- | --- |
| 快速通关 | `fast_track` | 快速过一遍，轻讲义、少测试。 |
| 均衡学习 | `balanced` | 默认学习方式，讲义、例题、测试适中。 |
| 深入掌握 | `mastery` | 更详细讲义，更多例题、review 和阶段测试。 |
| 冲刺强化 | `sprint` | 面向复习/备考，强调重点回顾、易错点和测试。 |

`sprint` 是新写入值。当前后端已有 `advanced` 枚举值，实施时需要兼容读取历史 `advanced`，并在展示和新写入时映射为 `sprint`。历史数据迁移可后续单独处理。

### 学习方式说明文案

开始前设置页和 preview 页都要展示一段自然语言说明。

快速：

```text
会优先提炼核心概念和重点结论，减少长讲义和复杂测试，适合快速建立框架。
```

均衡：

```text
会按正常节奏安排讲义、例题、复习和小测，适合日常学习。
```

深入：

```text
会安排更完整的讲义、更充分的例题、更频繁的 review 和阶段测试，适合真正掌握这一章。
```

冲刺：

```text
会压缩铺垫，增加重点回顾、易错点整理和测试任务，适合考前复习或查漏补缺。
```

### 底层派生配置

这些字段不作为前端主配置暴露，而是由 `preference` 和学前诊断派生。

| preference | content_depth | example_intensity | assessment_intensity | review_intensity |
| --- | --- | --- | --- | --- |
| `fast_track` | `concise` | `low` | `low` | `low` |
| `balanced` | `standard` | `standard` | `standard` | `standard` |
| `mastery` | `detailed` | `high` | `high` | `high` |
| `sprint` | `focused` | `standard` | `high` | `high` |

诊断结果可以在此基础上做微调。例如用户选择快速但诊断显示基础薄弱，计划可以保留快速节奏，但第一个任务仍要补基础，并减少后续扩展内容。

冲突优先级：

```text
用户时间约束
  > 诊断得出的必要补基础
  > 学习方式 preference
  > 额外例题、测试、review
```

如果容量不足，后端应返回 warning 或 over-capacity 状态，不能静默突破用户每日时间。

### 学前诊断

学前诊断每次新建计划都要做，不需要 `diagnostic_required` 字段。

学前诊断只问用户当前掌握程度和薄弱方向，不问学习偏好、资料范围、是否全量讲解，也不出资料知识测验题。

在产品页面上，前端把配置补问、学前诊断、薄弱方向和可选补充合并为“开始前设置”。但接口职责仍然拆开：学习设置缺失项由 `study-plan-config-parses` 的补问字段处理；诊断题由 `study-plan-diagnostic-questions` 处理。

页面标题建议：

```text
开始前设置
```

### 诊断问题结构

学前诊断所有用户可见文案必须使用中文。`question_type`、`topic_id`、`mastery_level`、`weak_area` 等字段仍是英文机器契约；前端展示问题类型时使用后端返回的 `question_type_label`，展示选项时使用 `options[].label`，不得直接展示英文枚举值。

v2 固定使用：

```text
3 个核心知识点掌握问题
1 个薄弱方向问题
1 个可选补充输入
```

知识点掌握问题由 LLM 根据 `goal_text + confirmed_config + material_scope + chunk excerpts` 选择 topic 候选。这里的 `confirmed_config` 是 API 字段名，表示“自然语言解析结果 + 用户在开始前设置页补齐/确认后的有效配置”，不是独立配置确认页产物。后端负责校验、映射和 fallback。最终前端永远接收 3 道 `topic_mastery`；即使资料较少，也允许后端从同一 chunk 拆出 3 个偏泛但资料内的主题。

示例：

```text
你对「Nyquist / Shannon 公式」了解多少？
A. 完全不了解
B. 听说过，但不清楚
C. 了解一些
D. 比较熟悉
```

薄弱方向问题：

```text
你最担心哪类内容？
A. 概念理解
B. 计算推导
C. 做题应用
D. 记忆重点
E. 其他
```

可选补充：

```text
还有什么想特别补的地方？
```

### 诊断问题请求

```json
{
  "goal_text": "我想三天深度掌握物理层",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_xxx"]
  },
  "confirmed_config": {
    "start_date": "2026-07-13",
    "duration_days": 3,
    "preference": "mastery",
    "daily_available_minutes": null,
    "daily_minutes_source": null
  }
}
```

### 前端诊断输出

```json
{
  "question_version": "study_plan_diagnostic_v2",
  "topic_mastery": [
    {
      "topic_id": "topic_physical_layer_basics",
      "topic_title": "物理层的基本功能",
      "mastery_level": "heard"
    },
    {
      "topic_id": "topic_nyquist_shannon",
      "topic_title": "Nyquist / Shannon 公式",
      "mastery_level": "none"
    },
    {
      "topic_id": "topic_signal_encoding",
      "topic_title": "编码与调制",
      "mastery_level": "some"
    }
  ],
  "weak_area": "calculation",
  "diagnostic_note": "希望多讲公式怎么用"
}
```

枚举值：

| 字段 | 可选值 |
| --- | --- |
| `mastery_level` | `none`、`heard`、`some`、`familiar` |
| `weak_area` | `concept`、`calculation`、`application`、`memorization`、`other` |

### 诊断归纳结果

诊断答案归纳为计划生成使用的 profile：

```json
{
  "question_version": "study_plan_diagnostic_v2",
  "prior_knowledge_level": "little",
  "foundation_needed": true,
  "weak_topics": ["topic_nyquist_shannon"],
  "weak_area": "calculation",
  "explanation_style": "step_by_step"
}
```

`explanation_style` 是后端从 `weak_area` 派生的内部兼容字段，不是前端新增讲课风格选择。

诊断结果影响：

- 第一个任务是否需要补基础；
- 弱掌握 topic 是否更靠前、更细；
- 薄弱方向对应的概念、计算、应用或记忆强化；
- 后续生成内容的 description 表达。

### 诊断复用和失效

同一次新建计划流程内，诊断答案可以复用，不需要每次点击“重新生成”都重新问。

以下变化会使诊断失效：

- `material_scope` 变化；
- `goal_text` 或目标知识点变化；
- 后端诊断问题版本 `question_version` 变化；
- 后端检测到诊断答案里的 `topic_id` 不属于当前资料快照。

日期、学习天数、每日学习时间和学习方式变化时，诊断答案默认保留，但 preview 需要重新生成。
## Step 3：计划预览

Preview 页展示同一组核心配置：

```text
学习目标
学习日期 / 学习天数
每日学习时间
学习方式
资料范围
```

其下展示学习方式说明文案。例如用户选择深入：

```text
本计划会偏深入：每天会安排较完整的讲义学习，穿插例题讲解和复习任务；关键知识点会有小测，最后会有综合测试，帮助你确认是否真的掌握。
```

Preview 页还展示：

- 每日任务列表；
- 每个任务预计分钟数；
- 是否有补基础任务；
- 是否有 review；
- 是否有测试任务；
- 资料覆盖 warning；
- 容量 warning，例如时间偏紧或超出每日学习时间。

用户可执行：

```text
返回修改配置
返回修改诊断
重新生成
确认保存计划
```

## 后端接口契约（已实施）

后端接口统一使用 `/api/v1` 前缀；诊断问题和诊断 profile 已拆成两个端点实现。

```text
POST /api/v1/courses/{course_id}/study-plan-config-parses
POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions
POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles
POST /api/v1/courses/{course_id}/study-plans/preview
POST /api/v1/courses/{course_id}/study-plans
```

前端需要先获取诊断问题列表，再把答案归纳成 `diagnostic_profile` 并传给 preview。
### Preview 请求

计划 preview 请求需要包含确认后的配置和诊断 profile。

```json
{
  "goal_text": "我要两天学完计网第七章",
  "start_date": "2026-07-12",
  "duration_days": 2,
  "daily_available_minutes": 90,
  "recommended_daily_minutes": 90,
  "daily_minutes_source": "system_estimated",
  "preference": "balanced",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_xxx"]
  },
  "diagnostic_profile": {
    "question_version": "study_plan_diagnostic_v2",
    "prior_knowledge_level": "little",
    "foundation_needed": true,
    "weak_topics": ["topic_nyquist_shannon"],
    "weak_area": "calculation",
    "explanation_style": "step_by_step"
  }
}
```

Preview 响应返回：

```json
{
  "config": {
    "start_date": "2026-07-12",
    "duration_days": 2,
    "end_date": "2026-07-13",
    "daily_available_minutes": 90,
    "recommended_daily_minutes": 90,
    "daily_minutes_source": "system_estimated",
    "preference": "balanced"
  },
  "tasks": [
    {
      "date": "2026-07-12",
      "title": "补基础：物理层的作用和基本概念",
      "estimated_minutes": 30,
      "task_type": "foundation",
      "source_topic_ids": ["physical_layer_basics"]
    }
  ],
  "material_snapshot": {
    "mode": "selected",
    "material_ids": ["mat_xxx"],
    "snapshot_hash": "sha256:..."
  },
  "coverage": {
    "covered_topic_ids": ["physical_layer_basics"],
    "missing_topic_ids": [],
    "warnings": []
  },
  "capacity": {
    "estimated_total_minutes": 180,
    "available_total_minutes": 180,
    "feasibility_status": "ok",
    "warnings": []
  },
  "generation_metadata": {
    "schema_version": 1,
    "model_provider": "openai-compatible",
    "generated_at": "2026-07-12T10:00:00+08:00"
  }
}
```

### 保存请求

方案 A 下，保存请求必须提交 preview 中展示过的任务。后端保存这些任务，不再生成新任务。

```json
{
  "idempotency_key": "uuid-from-frontend",
  "config": {
    "goal_text": "我要两天学完计网第七章",
    "start_date": "2026-07-12",
    "duration_days": 2,
    "end_date": "2026-07-13",
    "daily_available_minutes": 90,
    "recommended_daily_minutes": 90,
    "daily_minutes_source": "system_estimated",
    "preference": "balanced"
  },
  "material_snapshot": {
    "mode": "selected",
    "material_ids": ["mat_xxx"],
    "snapshot_hash": "sha256:..."
  },
  "diagnostic_profile": {
    "question_version": "study_plan_diagnostic_v2",
    "prior_knowledge_level": "little",
    "foundation_needed": true,
    "weak_topics": ["topic_nyquist_shannon"],
    "weak_area": "calculation",
    "explanation_style": "step_by_step"
  },
  "tasks": [
    {
      "date": "2026-07-12",
      "title": "补基础：物理层的作用和基本概念",
      "estimated_minutes": 30,
      "task_type": "foundation",
      "source_topic_ids": ["physical_layer_basics"]
    }
  ],
  "coverage": {
    "covered_topic_ids": ["physical_layer_basics"],
    "missing_topic_ids": [],
    "warnings": []
  },
  "generation_metadata": {
    "schema_version": 1,
    "model_provider": "openai-compatible",
    "generated_at": "2026-07-12T10:00:00+08:00"
  }
}
```

保存成功后，写入 `StudyPlan.parsed_config_json` 的结构建议为：

```json
{
  "schema_version": 1,
  "confirmed_config": {},
  "diagnostic_profile": {},
  "material_snapshot": {},
  "coverage": {},
  "capacity": {},
  "generation_metadata": {}
}
```

`tasks` 应写入正式计划任务表或现有等价结构；`parsed_config_json` 只保留生成上下文和追溯信息。后续讲义、测试、review 生成使用 `confirmed_config`、`planner_strategy`、`diagnostic_profile`、任务类型和来源 topic。

## 状态失效矩阵

| 用户动作 | 配置估算 | 诊断问题 / 答案 | preview |
| --- | --- | --- | --- |
| 返回第一步修改资料范围 | 重新解析并重新估算 | 失效 | 失效 |
| 返回第一步修改学习目标或目标知识点 | 重新解析并重新估算 | 可能失效；目标 topic 变化时失效 | 失效 |
| 在开始前设置补齐/修改开始日期或学习天数 | 重新估算 | 保留 | 失效 |
| 在开始前设置补齐/修改每日学习时间 | 保留配置，重算容量 | 保留 | 失效 |
| 在开始前设置确认/修改学习方式 | 重算派生配置和容量 | 保留 | 失效 |
| 修改诊断答案 | 保留 | 更新 profile | 失效 |
| 点击重新生成 preview | 保留 | 保留 | 重新生成 |

第一版可以由前端状态机管理 stale 状态，并由后端做一致性校验；后续如果需要跨设备恢复，再引入服务端 wizard draft。

## 后端算法调整

### 配置解析

自然语言配置解析仍负责抽取：

- 学习目标；
- 开始日期和学习天数；
- 用户明确给出的每日学习时间；
- 学习方式偏好；
- unresolved fields。

如果用户未给每日学习时间，配置解析不再随便补固定默认值，而是等待资料分析后的系统估算。

### 每日时间估算

系统估算需要依赖资料内容量。

伪代码：

```text
units = map material chunks into learning units
estimated_total_minutes = sum(unit.estimated_minutes)
recommended_daily_minutes = max(30, ceil(estimated_total_minutes / duration_days))
daily_available_minutes = user_time or recommended_daily_minutes
available_total_minutes = daily_available_minutes * duration_days
```

### 计划生成

reduce prompt 需要区分：

- 用户明确时间或手动修改时间：尽量贴近日学习时间；
- 系统估算时间：按估算值生成，但不强行塞满不必要任务；
- `foundation_needed = true`：第一天增加补基础任务；
- `weak_topics`：相关主题更靠前、更细；
- `preference`：决定讲义、例题、测试和 review 强度。

模型输出后需要做结构化校验。若出现每日任务时长低于最低要求、枚举值非法、任务日期越界或缺少核心字段，后端可以把校验失败原因反馈给 generator 重试 1 次。

### 诊断后的容量校验

诊断可能让 planner 新增补基础、例题、测试或 review，因此 preview 的 capacity 必须以 reduce 后最终任务为准，而不是只看 map 阶段材料单元估算。

```text
estimated_total_minutes = sum(preview.tasks[].subtasks[].estimated_minutes)
available_total_minutes = daily_available_minutes * duration_days

if estimated_total_minutes > available_total_minutes:
  feasibility_status = over_capacity
  warnings += PLAN_OVER_CAPACITY
elif estimated_total_minutes >= round(available_total_minutes * 0.8):
  feasibility_status = tight
else:
  feasibility_status = ok
```

`recommended_daily_minutes` 仍可基于 map 阶段材料规模估算，避免模型输出任务时长造成每日建议值不稳定。Preview 不因最终总时长超出容量直接失败；结构非法、日期越界、引用缺失和范围外资料仍必须失败。若每日任务时长超过 `daily_available_minutes`，只有在 capacity 已明确返回 `over_capacity` 和 `PLAN_OVER_CAPACITY` 时才允许返回 preview，前端必须展示该 warning。

前端提示应给出可操作建议：

- 增加每日学习时间；
- 增加学习天数；
- 改成快速模式；
- 保留当前时间，但减少额外例题、测试或 review。

## 错误处理

| 场景 | 建议错误码 | 前端处理 |
| --- | --- | --- |
| 日期或学习天数非法 | `INVALID_DATE_RANGE` | 停在开始前设置的配置补问区，提示修改日期或天数。 |
| 每日学习时间低于 30 分钟 | `DAILY_MINUTES_TOO_LOW` | 阻止继续，提示最低 30 分钟。 |
| 没有可用资料 | `NO_PARSED_MATERIAL` | 提示先上传并等待解析完成。 |
| 资料不属于当前课程或用户 | `NOT_FOUND` | 移除非法资料并提示重新选择。 |
| 资料还在解析或解析失败 | `NO_PARSED_MATERIAL` | 提示等待解析完成或重新上传可解析资料。 |
| 诊断答案和当前资料快照不匹配 | `DIAGNOSTIC_STALE` | 返回学前诊断重新回答。 |
| preview 容量超出 | `PLAN_OVER_CAPACITY` warning | 展示 warning 和调整建议，可以允许用户修改后重试。 |
| 模型输出枚举或结构非法 | `GENERATION_SCHEMA_INVALID` | 展示生成失败并允许重新生成。 |
| 保存请求未提交 tasks | 兼容路径 / 后续 `PREVIEW_TASKS_REQUIRED` | 当前旧客户端仍兼容保存前生成 preview；新向导强制 tasks 属于 P6 口径收紧。 |
| 保存请求幂等键重复 | 成功返回 / `IDEMPOTENCY_CONFLICT` | 同 key 同请求返回既有计划；同 key 不同请求返回冲突。 |

## 测试重点

- 自然语言无每日时间时，系统按资料总预计分钟数和学习天数估算，最低 30 分钟。
- 用户自然语言给出每日时间时，解析为 `user_text`，但仍返回 `recommended_daily_minutes`。
- 用户前端修改每日时间后，保存为 `user_modified`。
- 请求只提交 `start_date + duration_days`，后端正确计算 `end_date`。
- 资料范围变化会重新解析配置，并使诊断问题和 preview 失效。
- `include_all_parsed_materials=true` 使用当前已解析资料快照，后续上传资料不改变旧计划。
- 非当前课程资料、解析中资料和解析失败资料不能进入生成流程。
- 学前诊断固定返回 3 个 topic 问题；模型不足或失败时由后端基于资料内容 fallback 补足。
- 学前诊断只包含掌握程度和薄弱方向，不包含学习方式或资料范围问题。
- `fast_track`、`balanced`、`mastery`、`sprint` 映射到正确的底层生成 profile。
- 历史 `advanced` 能被读取并展示为冲刺，新写入使用 `sprint`。
- 诊断显示基础薄弱时，即使选择快速模式，第一个任务仍能补基础。
- 诊断增加补基础、例题或测试后，如果总时长超出容量，返回 `PLAN_OVER_CAPACITY`。
- preview 保存时提交 exact tasks，后端不重新生成任务。
- 同一个 `idempotency_key` 重复保存不会创建重复计划。
- 生成出的每日任务分钟数尊重 `daily_available_minutes`，不足或超出时返回结构化 warning。
## 2026-07-13 task-test 默认参数追溯补充

保存 preview exact tasks 时，后端会为 quiz/test 子任务写入 `generation_parameters.task_test`。若任务描述包含“10 道选择题和 3 道计算题”等明确数量，保存前会解析为结构化默认参数，例如 `question_count=13`、`question_types=["single_choice", "short_answer"]`、`difficulty="medium"`。如果模型已经输出 `{ "single_choice": 10, "short_answer": 3 }` 这类题型计数字段，保存前会归一化为同一标准结构。该参数只用于后续任务测试题按需生成的默认值，保存计划阶段不生成测试题正文，也不写 `AIGeneratedContent`。

后续 `POST /api/v1/study-subtasks/{subtask_id}/task-tests` 省略 `parameters` 时使用计划默认值；请求显式传入字段时覆盖默认值。非法 `generation_parameters.task_test` 在保存/替换阶段返回 `VALIDATION_ERROR`，不会落入 500。

## 2026-07-13 前端 C2 诊断向导落地

`/courses/:courseId/study-plans/new` 已接入 Step 3 的最小闭环：创建页内嵌 `DiagnosticWizard`，先请求后端诊断题，再提交答案生成 `diagnostic_profile`，最后把该 profile 合入 preview 请求。诊断是可跳过的可选增强项；未生成 profile 时，preview 请求只携带基础配置和资料范围。当前第一版仍固定 `material_scope = { include_all_parsed_materials: true, material_ids: [] }`，不提供资料范围选择；因此前端在 `goal_text` 变化或重新获取诊断题时主动清空诊断结果，日期和每日时长变化只标记 preview 过期。

前端不会在本地推导 `prior_knowledge_level`、`foundation_needed`、`weak_topics` 或 `explanation_style`，这些字段必须来自 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles` 的响应。若后端返回 `NO_PARSED_MATERIAL` 或 `DIAGNOSTIC_STALE`，向导停留在诊断区域并提示用户上传/等待解析或重新获取题目。

创建页会将当前表单草稿按 courseId 写入浏览器 `localStorage`，刷新后恢复目标、日期、每日时长和已生成的诊断 profile；保存成功后清理草稿。preview 结果仍只保存在页面内存中，后续如需刷新后继续等待同一次生成，应把 preview 改造成后端异步任务或持久化 draft/preview 资源。

## 2026-07-13 前端 C3 配置解析回填落地

`/courses/:courseId/study-plans/new` 已接入 Step 1/2 的自然语言配置解析辅助。用户在学习目标文本框输入一句目标后，可以点击“自动解析配置”；前端调用 `POST /api/v1/courses/{course_id}/study-plan-config-parses`，请求体只包含当前 `goal_text` 和固定 `material_scope`，不写数据库、不保存计划。

回填规则：

- 后端明确返回的 `goal_text`、`start_date`、`end_date`、`daily_available_minutes` 和 `preference` 会回填到可编辑表单。
- 后端只返回 `start_date + duration_days` 且 schema 未带 `end_date` 时，前端按确定性日期范围推导展示用 `end_date`；无法推导时不猜测。
- `unresolved_fields` 只展示当前创建页真实可编辑且仍无有效值的字段；`recommended_daily_minutes`、`daily_minutes_source`、`diagnostic_profile`、`material_snapshot`、`coverage`、`capacity` 和 `generation_metadata` 等系统追溯字段不得展示为“需手动补齐”。用户手动编辑对应字段后，从未解析提示中移除该字段。
- 解析回填改变了 preview 请求体，因此已有 preview 会立即标记为过期并禁用保存。
- 回填 `goal_text` 会清空已有 `diagnostic_profile`；仅回填日期、每日时长或学习方式时保留诊断结果，但仍要求重新生成 preview。

测试入口：`frontend/tests/pages/study-plan-pages.test.tsx` 增加配置解析回填用例；当前本地 Vitest 仍可能被 `entities ./decode` exports 问题挡在收集前，验证时需如实记录。

资料范围选择尚未在 C3 完成；当前创建页仍固定使用全部已解析资料。该能力属于 C4 完整创建向导的配置确认范围，或可作为 C4 前置小提交先落地，提交给后端时必须使用 `MaterialScope` 的资料 ID 结构，不能使用文件夹作为 Agent 范围。

## 2026-07-14 前端 C4 资料范围选择落地

`/courses/:courseId/study-plans/new` 已接入资料范围选择。创建页通过 `listMaterials(courseId)` 获取课程资料，`StudyPlanMaterialScopeSelector` 只允许选择 `parse_status = "parsed"` 的资料；解析中、待解析和解析失败资料不可勾选。用户可以选择“全部已解析资料”，也可以选择具体资料 ID，前端始终提交 `MaterialScope`，不提交文件夹 ID。

C4 后，`POST /study-plan-config-parses`、`POST /study-plan-diagnostic-questions`、`POST /study-plan-diagnostic-profiles`、`POST /study-plans/preview` 和保存请求都复用创建页当前 `materialScope`。资料范围变化会清空配置解析未补齐提示、清空已有 `diagnostic_profile`，并把现有 preview 标记为过期以禁用保存。创建页草稿同时持久化 `materialScope`，刷新后恢复。

测试入口：`frontend/tests/pages/study-plan-pages.test.tsx` 覆盖指定已解析资料进入 parse 和 preview 请求。当前本地 Vitest 仍受 `entities ./decode` exports 问题影响，可能在收集测试前失败；`frontend:build` 可用于验证 TS/Vite 编译。

## 2026-07-14 每日唯一测试计划规则

计划生成阶段负责保证每日测试结构，不把该规则下沉到 learning_execution、handout generator 或 task_test generator。

当前 planner reduce prompt 要求：

- 每个一级任务必须且只能安排一个 `quiz` / `test`。
- 该 `quiz` / `test` 必须是当天最后一个二级任务。
- 非最后一天的测试是当日测试，覆盖当天前置 `learn` / `review`。
- 最后一天的测试是全计划综合测试，覆盖全计划所有已安排的 `learn` / `review`，最后一天不再额外安排当天测试。

Preview 校验由 `backend/app/modules/study_plans/planner.py::validate_preview()` 调用 `backend/app/modules/study_plans/task_tree_rules.py::validate_daily_assessment_contract()` 完成。覆盖范围不修改生成器逻辑，而是体现在计划数据本身：非最后一天测试的 `related_material_ids` / `citation_chunk_ids` 必须覆盖当天前置学习任务的并集；最后一天综合测试必须覆盖全计划所有非测试任务的并集。

因此后续讲义生成仍只认 `learn` / `review`，任务测试题生成仍只认 `quiz` / `test`，生成 API、数据库表和 migration 均不需要改变。
