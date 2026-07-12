# Contracts v0.1

## 前后端契约基线

- 基础设施阶段的前端是最小集成验证工作台；已落地接口、请求体和响应字段以 [frontend-integration.md](frontend-integration.md) 为前端接入入口。
- 当前已落地的后端接口范围包括 Auth、Courses、Materials、Material Context、Course QA、Generation、Study Plans、Todos Calendar、Learning Execution、Checkins 和 S06 Task Content。
- 当前基础设施阶段不要求前端实现资料上传面板、资料范围选择器或课程问答面板；这些应在后续前端任务中基于稳定后端接口独立开发。
- 前端提交字段、后端返回字段统一使用 `snake_case`。
- 课程学期由 `GET /api/v1/course-terms` 提供统一选项；创建和更新课程只能提交选项中的 `value` 或 `null`，前端不得提供自由文本输入。
- 成功响应统一包含 `data` 和 `meta`。
- 错误响应统一包含 `error.code`、`error.message`、`error.details` 和 `meta.request_id`。
- 前端根据 HTTP status 与 `error.code` 决定交互，不解析中文错误文案。
- 异步操作返回资源 ID 与状态，前端通过详情或状态接口刷新。
- 空列表返回 `[]`，不使用 `null` 表示空集合。
- `401` 触发重新登录；`403` 展示无权限；`404` 可用于不暴露他人数据是否存在。

## 模块间契约基线

- 资料模块只把 `parse_status = parsed` 的资料暴露给检索和 Agent。
- 问答不得直接读取资料表或 chunk 表，必须通过 `material_context.retrieve_relevant_context()` 获取相关资料上下文。
- 指定材料生成和学习计划不得直接读取资料表或 chunk 表，必须通过 `material_context.iter_material_context_batches()` 获取全材料批次。
- Agent 模块不得跨课程混用上下文。
- 无资料命中时，Agent 必须返回 `answer_type = no_source`，并禁止伪引用。
- AI 生成内容统一写入 `AIGeneratedContent`，通过 `content_type` 区分用途。
- 保存为笔记统一使用 `content_type = note`，不新增 Note 对象。
- 学习计划模块只生成计划和任务结构，不提前生成讲义或任务测试题。
- 今日讲义和任务测试题按需生成，并绑定 `study_subtask_id`。
- 任务完成状态更新后必须同步一级任务状态和 `CheckinRecord`。
- 首页今日待办和首页大日历是只读聚合入口，不提供创建、编辑或重新生成计划能力。

## 计划学习模式 S01 子系统契约

S01 只固定计划学习模式的子系统契约和数据库审计结论，不实现新的业务 API，也不创建 migration。当前已落地的基础计划接口包括：

| 方法与路径 | 状态 | 说明 |
| --- | --- | --- |
| `POST /api/v1/courses/{course_id}/study-plans/preview` | 已实现 | 当前为确定性占位计划，S02 替换为真实全材料生成。 |
| `POST /api/v1/courses/{course_id}/study-plans` | 已实现 | 保存计划、一级任务和二级任务结构，S02 继续扩展确认后的任务树保存。 |
| `GET /api/v1/courses/{course_id}/study-plans` | 已实现 | 查询课程下未删除计划列表。 |
| `GET /api/v1/study-plans/{plan_id}` | 已实现 | 查询单个计划及任务结构。 |

S02-S06 已实现接口和 S07 候选接口如下；候选接口在对应任务合并前仍视为未实现契约，前端不得提前调用或自行拼接路径：

| 任务 | 方法与路径 | 用途 |
| --- | --- | --- |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-config-parses` | 自然语言配置回填。 |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions` | 基于当前资料范围生成学前诊断问题。 |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles` | 将诊断答案归纳为 preview 可携带的 `diagnostic_profile`。 |
| S02 | `POST /api/v1/study-plans/{plan_id}/regeneration-previews` | 基于已保存计划生成不落库的新预览。 |
| S02 | `PUT /api/v1/study-plans/{plan_id}` | 原子替换计划配置和任务结构。 |
| S02 | `DELETE /api/v1/study-plans/{plan_id}` | 软删除计划。 |
| S03 | `GET /api/v1/todos/today?date=YYYY-MM-DD` | 当前用户多课程今日待办，返回一级任务和嵌套二级任务。 |
| S03 | `GET /api/v1/calendar/month?month=YYYY-MM` | 全局月历日期摘要，含最多 3 条一级任务摘要和 `hidden_task_count`。 |
| S03 | `GET /api/v1/calendar/days/{date}/todos` | 全局当日待办，按课程和一级任务分组，含二级任务。 |
| S03 | `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM` | 单课程月历。 |
| S03 | `GET /api/v1/courses/{course_id}/study-calendar/days/{date}` | 单课程当日任务，作为课程详情页今日任务数据源。 |
| S04 | `GET /api/v1/study-subtasks/{subtask_id}/execution-context` | 执行页当日上下文。 |
| S04 | `PUT /api/v1/study-subtasks/{subtask_id}/completion` | 幂等完成或取消完成。 |
| S05 | `GET /api/v1/checkins?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | 个人中心打卡日期范围。 |
| S05 | `GET /api/v1/checkins/{date}` | 单日打卡；无任务也返回稳定零值。 |
| S06 | `POST /api/v1/study-subtasks/{subtask_id}/handouts` | 为学习/复习任务按需生成讲义。 |
| S06 | `POST /api/v1/study-subtasks/{subtask_id}/task-tests` | 为测试/小测任务按需生成任务测试题。 |
| S07 | `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf` | 流式导出成功的讲义或任务测试题。 |

计划学习模式统一遵守以下边界：

- `StudyPlan` 本期只绑定一个 `course_id` 和当前 `user_id`。
- `StudyTask.course_id` 必须等于所属计划课程；`StudySubTask.plan_id/course_id` 必须与父任务和计划一致。
- `StudySubTask.related_material_ids_json` 固定保存字符串 ID 数组，所有 ID 必须属于同一课程。
- 计划状态只使用 `draft`、`active`、`completed`、`deleted`；任务状态只使用 `not_started`、`in_progress`、`completed`。
- 一级任务状态由二级任务汇总，客户端不得直接写一级任务完成状态。
- 完成或取消完成二级任务、一级任务汇总、计划完成态汇总和当日打卡重算必须处于一个数据库事务。
- 自然日按服务配置的 `Asia/Shanghai` 业务时区解释，API 日期仍传 `YYYY-MM-DD`。

S01 阶段明确不新增 `todos`、`calendar_events`、`handouts`、`task_tests`、`export_records` 独立业务表；这些能力由现有表查询投影、统一生成内容表或请求派生文件承载。
## 跨模块数据引用原则

- 跨模块引用 ID 时，必须同时保证当前用户有权访问被引用资源。
- `SourceCitation` 必须保存 `material_id`、`material_name`、页码或页序号、`hit_text`。
- `material_name` 是快照字段，避免资料改名后历史引用展示异常。
- 历史引用定位失败时，前端仍可展示快照文本和定位失败提示。
- `StudySubTask.related_material_ids_json` 只能引用当前课程下当前用户可访问的资料。

## 资料上下文契约

`MaterialScope` 是前端工作台、问答、生成和计划基础能力共用的资料范围结构：

```json
{
  "include_all_parsed_materials": true,
  "material_ids": []
}
```

规则：

- 默认 `include_all_parsed_materials = true`，返回当前课程下全部 `parsed` 且未删除资料的 chunk。
- 当 `include_all_parsed_materials = false` 时，只能通过 `material_ids` 显式选择一个或多个具体资料。
- `MaterialFolder` 只用于资料归类和列表浏览，不能作为 Agent 上下文选择范围，`MaterialScope` 不接受 `folder_ids`。
- 显式传入 `material_ids` 时，后端必须校验这些资料属于当前用户、当前课程、已解析且未删除；否则返回 `NOT_FOUND`。
- 未解析、解析失败和已删除资料不得进入上下文结果。

`retrieve_relevant_context()` 和 `iter_material_context_batches()` 返回的 `ContextChunk` 最小字段：

```json
{
  "material_id": "mat_123",
  "chunk_id": "chk_123",
  "chunk_index": 0,
  "material_name": "notes.md",
  "page": null,
  "page_index": null,
  "heading": "Intro",
  "content_text": "Alpha",
  "score": 0.82
}
```

问答检索没有可用 parsed chunk 时返回 `no_parsed_material = true`；有 parsed chunk 但没有相关命中时返回空 `chunks`。两种情况调用方都应进入 `no_source` 兜底流程，不能调用模型生成无依据回答或保存伪引用。

`score` 只表示问答相关性检索的相似度；全材料批次读取可以返回 `null`。

## 独立生成公共契约

- `POST /courses/{course_id}/generations`、课程生成历史和生成详情路径保持不变。
- 生成服务只使用`iter_material_context_batches()`，每份选定parsed资料必须进入至少一个batch。
- 注册类型固定为`quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`；G01完成公共链路，具体真实生成由G02-G06分别完成。
- 每个最终业务条目使用稳定`id`；具体生成器返回“条目ID到chunk ID候选”，公共层过滤越界ID并回填`source_citation_ids`。
- 生成POST、历史和详情的`GeneratedContentRead`统一包含`source_citations`；无引用固定返回`[]`。
- 成功内容和引用处于同一数据库事务。模型、schema和覆盖失败保存failed记录，不保存部分JSON或引用。
- 当前引用位置约束要求`page`或`page_index`至少一个非空；无分页资料兼容保存`page=null,page_index=0`，0表示未知位置而非真实第0页。

稳定错误语义：参数或未知类型`422 VALIDATION_ERROR`且不落库；无可用资料`400 NO_PARSED_MATERIAL`且不落库；模型、schema和覆盖失败分别保存`GENERATION_FAILED`、`GENERATION_SCHEMA_INVALID`、`MATERIAL_COVERAGE_INCOMPLETE`记录。

## 请求 / 响应示例格式

Agent 提问请求示例：

```json
{
  "course_id": "crs_123",
  "conversation_id": null,
  "question": "这份课件的核心概念是什么？",
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "source_page": "course_detail"
}
```

Agent 回答响应示例：

```json
{
  "data": {
    "answer_text": "回答正文",
    "answer_type": "grounded",
    "created_message_id": "msg_123",
    "source_citations": [
      {
        "material_id": "mat_123",
        "material_name": "chapter-01.pdf",
        "page": 3,
        "page_index": null,
        "hit_text": "命中文本片段"
      }
    ]
  },
  "meta": {
    "request_id": "req_123",
    "server_time": "2026-07-09T12:00:00+08:00",
    "api_version": "v1"
  }
}
```

## 契约变更规则

- API 契约变更前先更新本分区，再实现。
- 新增字段必须说明默认值、是否可为空和前端展示兜底。
- 修改状态枚举必须同步状态流转、错误处理和验收口径。
- 权限规则变更必须明确影响哪些资源和接口。
- 引用来源字段不可随意弱化；资料名快照、页码或页序号、命中文本片段是 v0.1 最小展示契约。

## 向后兼容要求

- 新增可选字段时，前端不得因未知字段失败。
- 后端删除或重命名字段前，应提供迁移期兼容字段。
- 枚举新增时，前端必须展示兜底状态。
- 错误码新增时，前端默认按通用错误处理。
- 字段类型变化、枚举语义变化、权限语义变化视为破坏性变更，必须单独评审。

## 计划学习模式 S02 生命周期契约

S02 已实现以下接口，前端可在契约评审后接入：

| 方法与路径 | 状态 | 说明 |
| --- | --- | --- |
| `POST /api/v1/courses/{course_id}/study-plan-config-parses` | 已实现 | 自然语言配置回填；不写数据库。 |
| `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions` | 已实现 | 基于当前 parsed 资料范围生成 1 到 3 个 topic 掌握问题、1 个薄弱方向问题和 1 个可选补充输入；不写数据库。 |
| `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles` | 已实现 | 校验 topic 仍属于当前资料范围，并归纳 `prior_knowledge_level`、`foundation_needed`、`weak_topics`、`weak_area` 和 `explanation_style`；不写数据库。 |
| `POST /api/v1/courses/{course_id}/study-plans/preview` | 已实现 | 基于全部已解析资料、英文 `preference` 和可选 `diagnostic_profile` 生成 preview；请求可省略 `daily_available_minutes`，响应返回最终 `daily_available_minutes`、新的 `recommended_daily_minutes`、`daily_minutes_source`、`coverage`、派生后的 `generation_metadata.planner_strategy` 和基于最终任务树统计的 `capacity`。 |
| `POST /api/v1/courses/{course_id}/study-plans` | 已实现 | 保存用户确认的任务树；支持旧客户端省略 `tasks` 时先生成 preview。 |
| `POST /api/v1/study-plans/{plan_id}/regeneration-previews` | 已实现 | 生成新 preview，不写数据库。 |
| `PUT /api/v1/study-plans/{plan_id}` | 已实现 | 基于 `expected_updated_at` 原子替换配置和任务树。 |
| `DELETE /api/v1/study-plans/{plan_id}` | 已实现 | 软删除计划，默认列表和详情隐藏。 |


学前诊断接口统一使用 `question_version = "study_plan_diagnostic_v1"`。掌握程度枚举为 `none`、`heard`、`some`、`familiar`；薄弱方向枚举为 `concept`、`calculation`、`application`、`memorization`、`other`。诊断问题的 topic 来自当前 `material_scope` 解析后的资料上下文；若只能稳定提取 1 到 2 个 topic，后端不会补足到 3 个。

`study-plan-diagnostic-profiles` 会重新基于当前 `material_scope` 计算合法 topic 集。若请求中的 `question_version` 过期，或 `topic_mastery[].topic_id` 不属于当前资料范围，返回 `409 DIAGNOSTIC_STALE`，`details.invalid_topic_ids` 列出失效 topic。无可用 parsed 资料返回 `400 NO_PARSED_MATERIAL`。归纳出的 `diagnostic_profile` 可直接传给 `POST /api/v1/courses/{course_id}/study-plans/preview` 的 `diagnostic_profile` 字段；preview 会把英文 `preference` 派生为 `planner_strategy` 并与该 profile 一起写入 planner reduce prompt，用于影响 `content_depth`、例题强度、测评强度、review 强度、补基础、薄弱主题顺序和颗粒度、薄弱方向强化以及 description 解释风格；保存时继续追溯 `diagnostic_profile` 和 `planner_strategy`，不在本接口层提前生成讲义或任务测试题。

保存接口支持 `Idempotency-Key`：key hash 写入 `study_plans.idempotency_key_hash`，request hash 保留在 `parsed_config_json.idempotency`；数据库通过 `(user_id, course_id, idempotency_key_hash)` 唯一索引兜底，同键同请求返回同一 plan bundle，同键不同请求返回 `IDEMPOTENCY_CONFLICT`，已软删除计划占用的 key 不可复用。保存和替换显式 `tasks` 时，后端必须在写库前校验任务树：至少一个一级任务、每个一级任务至少一个二级任务、任务日期位于计划日期范围、一级和二级 `sort_order` 从 1 连续递增，且所有 `related_material_ids` 属于当前用户、当前课程、本次 `material_scope` 并处于 parsed 可用状态；校验失败不得写入计划、任务、二级任务或打卡记录。替换接口通过数据库条件 UPDATE 原子校验 `expected_updated_at`，在已有进度、已绑定生成内容或 `expected_updated_at` 不匹配时返回 `STATE_CONFLICT`；失败请求不得删除或部分修改旧任务树和打卡记录。S02 不新增业务表，不在保存阶段生成讲义或任务测试题。Preview 和保存后的 `parsed_config_json.capacity` 均以最终任务树为事实来源：`estimated_total_minutes = sum(tasks[].subtasks[].estimated_minutes)`，`available_total_minutes = daily_available_minutes * duration_days`；超出容量时 `feasibility_status = "over_capacity"` 且 `warnings` 包含 `PLAN_OVER_CAPACITY`。`recommended_daily_minutes` 可继续基于 map 阶段资料规模估算，`study_plans.daily_available_minutes` 保存最终采用的每日学习时间。

## 计划学习模式 S03 今日待办与日历契约

S03 已实现五个只读 GET 接口，前端可在契约评审后接入：

| 方法与路径 | 状态 | 说明 |
| --- | --- | --- |
| `GET /api/v1/todos/today?date=YYYY-MM-DD` | 已实现 | 首页今日待办；返回当前用户多课程一级任务和嵌套二级任务，前端默认折叠二级任务。 |
| `GET /api/v1/calendar/month?month=YYYY-MM` | 已实现 | 全局月历；每个日期返回计数、最多 3 条 `task_summaries` 和 `hidden_task_count`。 |
| `GET /api/v1/calendar/days/{date}/todos` | 已实现 | 大日历日期弹窗；按课程分组，每组包含一级任务和二级任务。 |
| `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM` | 已实现 | 课程月历；只返回当前课程日期摘要，日期行 `course_count = 1`。 |
| `GET /api/v1/courses/{course_id}/study-calendar/days/{date}` | 已实现 | 课程详情页今日任务数据源；前端传今天，不在 S03 提供日期切换。 |

`TaskTodoRead` 最小字段：`task_id`、`plan_id`、`course_id`、`course_name`、`title`、`task_date`、`status`、`derived_status`、`completed_subtask_count`、`total_subtask_count`、`first_incomplete_subtask_id`、`subtasks`。`SubTaskTodoRead` 返回 `subtask_id`、`title`、`subtask_type`、`description`、`status`、`sort_order`、`execution_url`；当前 `execution_url` 可为 `null`，前端可用 `subtask_id` 拼接 S04 执行页。

计划详情按钮复用 S02 `GET /api/v1/study-plans/{plan_id}`，S03 不新增计划详情接口。S03 不提供任何 POST/PATCH/PUT/DELETE 待办或日历接口，不创建 `todos` 或 `calendar_events` 写模型。
## S04/S05 学习执行与打卡契约

### 执行上下文

`GET /api/v1/study-subtasks/{subtask_id}/execution-context` 返回当前二级任务所在业务日期的执行上下文。响应 `data` 包含 `course`、`plan`、`execution_date`、当天 `tasks`、`current_subtask_id`、`related_materials`、`handout_content_id` 和 `task_test_content_id`。两个 generated content id 来自当前二级任务最近一次成功生成的 `handout` / `task_test`；没有成功内容时返回 `null`。

### 二级任务完成

`PUT /api/v1/study-subtasks/{subtask_id}/completion` 请求体固定为 `{ "completed": boolean }`，表示期望状态，不是 toggle。重复提交同一状态返回 200 和 `changed=false`。取消完成会把二级任务状态改回 `not_started` 并清空 `completed_at`。

### 打卡查询

`GET /api/v1/checkins/{target_date}` 返回单日打卡 DTO；如果持久化记录不存在，后端只读计算当前事实并返回，不写入 `checkin_records`。

`GET /api/v1/checkins?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` 返回闭区间内已有持久化记录和 summary。summary 中 `current_streak_days` / `longest_streak_days` 按“当天有任务且完成过任意二级任务”计算。无任务日和有任务但未完成日都会中断当前连续段；范围内缺失的持久化记录不会被补齐，相邻完成日必须日期连续才会合并为同一 streak。若查询结果最后一条记录不是完成日，`current_streak_days=0`；空结果返回 0 值 summary。

错误码：401 `UNAUTHORIZED`；404 `NOT_FOUND`；409 `STATE_CONFLICT`；422 `VALIDATION_ERROR`。

## S06 任务内容生成契约

S06 已实现两个按需生成接口，前端可在契约评审后接入：

| 方法与路径 | 状态 | 说明 |
| --- | --- | --- |
| `POST /api/v1/study-subtasks/{subtask_id}/handouts` | 已实现 | 为 `learn` / `review` 二级任务生成今日讲义。 |
| `POST /api/v1/study-subtasks/{subtask_id}/task-tests` | 已实现 | 为 `quiz` / `test` 二级任务生成任务测试题。 |

`HandoutGenerationRequest` 请求体：

```json
{
  "force_regenerate": false,
  "parameters": {
    "language": "zh-CN",
    "detail_level": "standard"
  }
}
```

`detail_level` 支持 `brief`、`standard`、`deep`。`parameters` 可省略，后端使用默认参数。`force_regenerate` 可省略，默认 `false`。

`TaskTestGenerationRequest` 请求体：

```json
{
  "force_regenerate": false,
  "parameters": {
    "question_count": 5,
    "question_types": ["single_choice", "short_answer"],
    "difficulty": "medium"
  }
}
```

`question_count` 范围 1-20；`question_types` 支持 `single_choice`、`multiple_choice`、`true_false`、`short_answer`；`difficulty` 支持 `easy`、`medium`、`hard`。

成功响应统一为 `{data, meta}`，其中 `data` 是 `GeneratedContentRead`，至少包含 `id`、`course_id`、`study_subtask_id`、`content_type`、`title`、`content_json`、`generation_status`、`error_code`、`created_at` 和 `updated_at`。

生成规则：

- `learn` / `review` 只能调用 handout endpoint；调用 task-test endpoint 返回 `STATE_CONFLICT`。
- `quiz` / `test` 只能调用 task-test endpoint；调用 handout endpoint 返回 `STATE_CONFLICT`。
- 材料范围严格来自 `StudySubTask.related_material_ids_json`，接口请求体不能覆盖资料范围。
- 后端使用 `MaterialScope(include_all_parsed_materials=false, material_ids=related_material_ids_json)`。
- S06 使用 `iter_material_context_batches()` 和 `run_material_coverage()`，不使用 Top-K 检索或旧 `resolve_context()`。
- 默认请求幂等：同一 `study_subtask_id + content_type` 已有未删除 success 时直接返回最近成功内容，不调用模型、不新建 `AIGeneratedContent`。
- `force_regenerate=true` 时即使已有 success 也重新生成，并创建新的成功内容。
- failed 记录不作为幂等命中结果，也不阻止后续请求重新尝试生成。
- 成功和进入生成流程后的失败都写入 `ai_generated_contents`；权限、任务不存在和任务类型不匹配不会创建生成记录。
- execution-context 只返回最近一次成功内容 ID；最新 failed 记录不会覆盖 `handout_content_id` / `task_test_content_id`。
- 生成不会改变二级任务完成状态，不触发一级任务汇总，也不写 `checkin_records`。

错误码：401 `UNAUTHORIZED`；404 `NOT_FOUND`；409 `STATE_CONFLICT`；422 `VALIDATION_ERROR`；400 `NO_PARSED_MATERIAL`；409 `MATERIAL_COVERAGE_INCOMPLETE`；500 `GENERATION_SCHEMA_INVALID`；502 `GENERATION_FAILED`。
