# Contracts v0.1

## 前后端契约基线

- 前端已承载 V1 浏览器闭环；已落地接口、请求体和响应字段以 [frontend-integration.md](frontend-integration.md) 为前端接入入口。
- 当前已落地的后端接口范围包括 Auth、Courses、Materials、Material Context、Course QA、Generation、Study Plans、Todos Calendar、Learning Execution、Checkins 和 S06 Task Content。
- 当前基础设施阶段不要求前端实现资料上传面板、资料范围选择器或课程问答面板；这些应在后续前端任务中基于稳定后端接口独立开发。
- 前端提交字段、后端返回字段统一使用 `snake_case`。
- 课程学期由 `GET /api/v1/course-terms` 提供统一选项；创建和更新课程只能提交选项中的 `value` 或 `null`，前端不得提供自由文本输入。
- `GET /api/v1/courses` 返回 `CourseListItemRead`：除课程基础字段外，列表项必须包含 `material_count` 与 `today_task_status`（`no_study_plan`、`no_task_today`、`has_task_today`）。这两个字段是首页课程卡片的只读聚合，不出现在课程创建、详情、更新和删除响应中。
- 课程卡片的今日状态由服务端按 `Asia/Shanghai` 自然日计算；资料数只统计未删除资料，今日任务只统计未删除学习计划下 `task_date` 为当天的一级任务。
- 成功响应统一包含 `data` 和 `meta`。
- 错误响应统一包含 `error.code`、`error.message`、`error.details` 和 `meta.request_id`。
- 前端根据 HTTP status 与 `error.code` 决定交互，不解析中文错误文案。
- 异步操作返回资源 ID 与状态，前端通过详情或状态接口刷新。
- 空列表返回 `[]`，不使用 `null` 表示空集合。
- `401` 触发重新登录；`403` 展示无权限；`404` 可用于不暴露他人数据是否存在。

## 运行模式契约

`GET /api/v1/health` 无需登录，成功响应 `data` 固定包含：

```json
{
  "status": "ok",
  "environment": "development",
  "mock_model_provider_enabled": false
}
```

`environment` 只可能为 `development`、`test`、`production`。Health 不返回 Secret、API Key、模型地址或模型名。前端读取 `mock_model_provider_enabled`；值为 `true` 时必须全局标识模拟模型模式，Health 不可用时不得阻塞应用壳。

模型用途未配置且未显式开启 Mock 时，依赖模型的接口返回 HTTP `503`：

```json
{
  "error": {
    "code": "MODEL_PROVIDER_NOT_CONFIGURED",
    "message": "模型服务未配置",
    "details": {"purpose": "course_qa"}
  },
  "meta": {"request_id": "req_..."}
}
```

`details.purpose` 仅标识逻辑用途，不暴露环境变量名或其他敏感配置。Mock 只允许在非生产环境由后端显式启用，客户端不能请求或切换 Mock。

## 模块间契约基线

- 资料模块只把 `active_parse_version_id` 指向的生效版本暴露给检索和 Agent；`parse_status = parsing` 时旧生效版本仍可用。
- 问答不得直接读取资料表或 chunk 表，必须通过 `material_context.retrieve_relevant_context()` 获取相关资料上下文。
- Quiz、Flashcard、Mindmap、Outline 和 Knowledge List 必须通过 `material_context.resolve_generation_context()` 获取完整材料上下文；学习计划、handout 和 task_test 等保留批处理策略的消费者使用 `iter_material_context_batches()`。
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
| `POST /api/v1/courses/{course_id}/study-plans/preview` | 已实现 | 基于全部已解析资料、英文 `preference` 和可选 `diagnostic_profile` 生成真实全材料 preview；响应包含 daily minutes、coverage、`generation_metadata.planner_strategy`、`generation_metadata.material_quality` 和 capacity。 |
| `POST /api/v1/courses/{course_id}/study-plans` | 已实现 | 保存计划、一级任务和二级任务结构，S02 继续扩展确认后的任务树保存。 |
| `GET /api/v1/courses/{course_id}/study-plans` | 已实现 | 查询课程下未删除计划列表。 |
| `GET /api/v1/study-plans/{plan_id}` | 已实现 | 查询单个计划及任务结构。 |

S02-S06 已实现接口和 S07 已实现 / 候选接口如下；候选接口在对应任务合并前仍视为未实现契约，前端不得提前调用或自行拼接路径：

| 任务 | 方法与路径 | 用途 |
| --- | --- | --- |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-config-parses` | 自然语言配置回填。 |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions` | 基于当前资料范围生成学前诊断问题。 |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles` | 将诊断答案归纳为 preview 可携带的 `diagnostic_profile`。 |
| S02 | `POST /api/v1/study-plans/{plan_id}/regeneration-previews` | 基于已保存计划和请求覆盖项生成不落库的新预览；继承保存的 `diagnostic_profile`，显式传入时覆盖。 |
| S02 | `PUT /api/v1/study-plans/{plan_id}` | 原子替换计划配置和任务结构。 |
| S02 | `DELETE /api/v1/study-plans/{plan_id}` | 软删除计划。 |
| S03 | `GET /api/v1/todos/today?date=YYYY-MM-DD` | 当前用户多课程今日待办，返回一级任务和嵌套二级任务。 |
| S03 | `GET /api/v1/calendar/month?month=YYYY-MM` | 全局月历日期摘要，含最多 3 条一级任务摘要和 `hidden_task_count`。 |
| S03 | `GET /api/v1/calendar/days/{date}/todos` | 全局当日待办，按课程和一级任务分组，含二级任务。 |
| S03 | `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM` | 单课程月历。 |
| S03 | `GET /api/v1/courses/{course_id}/study-calendar/days/{date}` | 单课程当日任务，作为课程详情页今日任务数据源。 |
| S04 | `GET /api/v1/study-subtasks/{subtask_id}/execution-context` | 执行页当日上下文。 |
| S04 | `POST /api/v1/study-subtasks/{subtask_id}/qa/questions` | 执行页任务级问答，资料范围固定为当前二级任务关联资料。 |
| S04 | `PUT /api/v1/study-subtasks/{subtask_id}/completion` | 幂等完成或取消完成。 |
| S05 | `GET /api/v1/checkins?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | 个人中心打卡日期范围。 |
| S05 | `GET /api/v1/checkins/{date}` | 单日打卡；无任务也返回稳定零值。 |
| S06 | `POST /api/v1/study-subtasks/{subtask_id}/handouts` | 为学习/复习任务按需生成讲义。 |
| S06 | `POST /api/v1/study-subtasks/{subtask_id}/task-tests` | 为测试/小测任务按需生成任务测试题。 |
| S07 | `GET /api/v1/generated-contents/{generated_content_id}/exports/markdown` | 已实现：导出成功的任务测试题 Markdown 文件。 |
| S07 | `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf` | 已实现：导出成功的今日讲义 PDF；轻量阶段不做任务测试题 PDF。 |

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
- Course QA 和 task test 的 `SourceCitation` 必须保存 `material_id`、`material_version_id`、`material_name`、页码或页序号、`hit_text`；新生成 handout 与五类独立 POC 生成不创建逐条引用。
- `material_name` 是快照字段，避免资料改名后历史引用展示异常。
- 历史引用定位失败时，前端仍可展示快照文本和定位失败提示。
- `StudySubTask.related_material_ids_json` 只能引用当前课程下当前用户可访问的资料。
- 成功生成内容的 `material_scope_json.source_materials` 由实际进入生成上下文的 chunk 去重构建，保存 `material_id` 与当时的 `material_name`；前端用它展示真实输入资料范围，不从模型文本推断来源。
- 成功生成内容的 `material_scope_json.material_versions` 与学习计划 `material_snapshot.material_versions` 保存实际读取的 `{material_id, version_id}`；后续重解析不得改写历史快照。

## 资料上下文契约

`MaterialScope` 是前端工作台、问答、生成和计划基础能力共用的资料范围结构：

```json
{
  "include_all_parsed_materials": true,
  "material_ids": []
}
```

规则：

- 默认 `include_all_parsed_materials = true`，返回当前课程下全部 `is_learning_ready = true` 资料的生效版本 chunk。
- 当 `include_all_parsed_materials = false` 时，只能通过 `material_ids` 显式选择一个或多个具体资料。
- `MaterialFolder` 只用于资料归类和列表浏览，不能作为 Agent 上下文选择范围，`MaterialScope` 不接受 `folder_ids`。
- 显式传入 `material_ids` 时，后端必须校验这些资料属于当前用户、当前课程、存在生效解析版本且未删除；否则返回 `NOT_FOUND`。
- 没有生效版本和已删除资料不得进入上下文结果；候选、失败和退休版本的 chunk 不得进入结果。

`retrieve_relevant_context()`、`resolve_generation_context()` 和 `iter_material_context_batches()` 使用的 `ContextChunk` 最小字段：

```json
{
  "material_id": "mat_123",
  "material_version_id": "mpv_123",
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

问答检索没有可用生效版本 chunk 时返回 `no_parsed_material = true`；有生效 chunk 但没有相关命中时返回空 `chunks`。两种情况调用方都应进入 `no_source` 兜底流程，不能调用模型生成无依据回答或保存伪引用。

`score` 只表示问答相关性检索的相似度；完整上下文和全材料批次读取可以返回 `null`。

## 独立生成公共契约

- `POST /api/v1/courses/{course_id}/generations`、`GET /api/v1/courses/{course_id}/generated-contents` 和 `GET /api/v1/generated-contents/{generated_content_id}` 路径保持不变；`PATCH /api/v1/generated-contents/{generated_content_id}/flashcards` 负责替换当前用户 Flashcard 的完整牌组；`PATCH /api/v1/generated-contents/{generated_content_id}/knowledge-items/{knowledge_item_id}/learning-state` 只更新当前用户某个知识点的 `learned` 布尔状态。
- 生成服务调用 `resolve_generation_context()`，按稳定顺序合并所有选定 parsed chunk，并在模型调用前检查总 token 上限。
- 注册类型固定为`quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`；G01完成公共链路，具体真实生成由G02-G06分别完成。
- `mindmap` 成功记录的 `content_json` 包含 `schema_version`、`renderer`、`root_node_id`、`nodes`、`edges`、`markmap_markdown` 和 `markmap_data`；Markdown 和 `markmap-lib` 预处理结果均保存在数据库 JSON 中，不对应本地文件路径。
- `quiz` 参数支持 `question_count`、仅含 `single_choice` 的 `question_types`、`difficulty` 和 `focus`。成功记录的 `content_json.questions` 使用稳定 `q_001...` ID，每题固定包含 A-D 四个选项、正确答案和解析。
- `flashcard` 参数支持 `card_count`、`card_style`、`include_formulas` 和 `focus`；成功记录写入 `content_json.cards`，`mastery_status` 固定为 `unknown`。
- Flashcard 牌组替换接收 1-100 张卡片，拒绝规范化后重复的正面，重新生成连续 ID 和顺序；前端必须以完整持久化牌组为写入基线，不能用打乱或错卡重练子集覆盖后端记录。
- `outline` 参数支持组织方式、章节数量、复习目标和详细度；成功记录写入 `content_json.sections`，不包含学习计划或任务字段。
- `knowledge_list` 参数支持数量、提取偏好、最低重要性和 focus；成功记录写入 `content_json.items`。最终 item 的 `learned` 默认为 `false`，历史 item 缺失时按 `false` 解释；学习状态接口只接受 `learned`，不允许借此修改知识点名称、定义、重要程度或章节。
- 每个最终业务条目使用稳定 `id`，列表型结果同时使用连续 `sort_order`；业务 JSON 不包含 `source_chunk_ids` 或 `source_citation_ids`。
- 生成 POST、历史和详情的 `GeneratedContentRead` 统一包含 `source_citations`；这五类内容固定返回 `[]`，包括数据库中可能仍存在旧引用行的历史记录。
- 五类内容的 `material_scope_json` 除基础范围字段外保存 `source_materials: [{material_id, material_name}]` 与 `material_versions: [{material_id, version_id}]` 快照；两者来自实际 `MaterialGenerationContext.chunks`，用于展示和追溯真实输入，不构成逐条引用。
- 新生成 Handout 不写 `source_citations`，其 Markdown 顶部来源说明与 `material_scope_json.source_materials` 都由实际 material-context batch 构建；Task Test 的真实 `source_citations` 继续按题保存并通过 API 与 Markdown 导出返回。
- 成功时只保存 `AIGeneratedContent`。模型、最终 schema 或 Markmap 预处理失败保存 failed 记录，不保存部分 JSON。

稳定错误语义：参数或未知类型 `422 VALIDATION_ERROR` 且不落库；无可用资料 `400 NO_PARSED_MATERIAL` 且不落库；总上下文超限返回 `400 MATERIAL_CONTEXT_TOO_LARGE` 且不调用模型、不落库；模型或最终 schema/Markmap 预处理失败保存 `GENERATION_FAILED` 或 `GENERATION_SCHEMA_INVALID` 记录。

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
    "conversation_id": "cnv_123",
    "user_message_id": "msg_user",
    "assistant_message_id": "msg_assistant",
    "answer_text": "回答正文",
    "answer_type": "grounded",
    "source_citations": [
      {
        "material_id": "mat_123",
        "chunk_id": "chk_123",
        "material_name": "chapter-01.pdf",
        "page": "3",
        "page_index": null,
        "hit_text": "命中文本片段"
      }
    ],
    "used_material_ids": ["mat_123"]
  },
  "meta": {
    "request_id": "req_123",
    "server_time": "2026-07-09T12:00:00+08:00",
    "api_version": "v1"
  }
}
```

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
| `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions` | 已实现 | 基于目标、确认配置和当前 parsed 资料范围生成固定 3 个 topic 掌握问题、1 个薄弱方向问题和 1 个可选补充输入；模型失败或输出不足时 fallback 补足；不写数据库。 |
| `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles` | 已实现 | 校验 topic 仍属于当前资料范围，并归纳 `prior_knowledge_level`、`foundation_needed`、`weak_topics`、`weak_area` 和 `explanation_style`；不写数据库。 |
| `POST /api/v1/courses/{course_id}/study-plans/preview` | 已实现 | 基于当前 `material_scope`、英文 `preference` 和可选 `diagnostic_profile` 生成 preview；请求可省略 `daily_available_minutes`，但当前 schema 仍要求 `start_date` 且要求 `end_date` 或 `duration_days` 至少一个。响应返回最终 `daily_available_minutes`、新的 `recommended_daily_minutes`、`daily_minutes_source`、`coverage`、派生后的 `generation_metadata.planner_strategy`、当前资料范围的 `generation_metadata.material_quality` 和基于最终任务树统计的 `capacity`。当前前端创建页把学情诊断作为生成 preview 的必填前置条件；若自然语言解析缺少日期范围，前端会在混合问卷中按缺失项补问开始日期和学习天数，并派生 `end_date` 后再调用 preview。 |
| `POST /api/v1/courses/{course_id}/study-plans` | 已实现 | 保存用户确认的任务树；请求体 `client_flow` 默认为 `legacy`。新向导必须传 `client_flow = "wizard_v1"` 和 preview 中确认后的非空 `tasks`；旧客户端省略 `tasks` 时仍先生成 preview。 |
| `POST /api/v1/study-plans/{plan_id}/regeneration-previews` | 已实现 | 基于已保存配置生成新 preview，不写数据库；请求覆盖项优先，未传 `diagnostic_profile` 时继承保存值。 |
| `PUT /api/v1/study-plans/{plan_id}` | 已实现 | 基于 `expected_updated_at` 原子替换配置和任务树。 |
| `DELETE /api/v1/study-plans/{plan_id}` | 已实现 | 软删除计划，默认列表和详情隐藏。 |


学前诊断接口统一使用 `question_version = "study_plan_diagnostic_v2"`。掌握程度枚举为 `none`、`heard`、`some`、`familiar`；薄弱方向枚举为 `concept`、`calculation`、`application`、`memorization`、`other`。诊断问题的 `topic_mastery` 固定为 3 道，topic 必须来自当前 `material_scope` 解析后的资料上下文；正常路径使用 `study_plan_diagnostic` 模型选择 topic 候选，模型失败、输出不足、重复或无法映射到资料时由后端 fallback 补足，并在 `generation_metadata.diagnostic_questions` 记录 `source` 和 `fallback_reason`。

前端创建页的 `StudyPlanPreviewRequest` 类型允许 `start_date`、`end_date` 和 `duration_days` 为空或省略，以表达“自然语言解析阶段尚未得到日期”的中间状态；但当前创建页在真正调用 preview 前会通过混合问卷补齐日期范围。后端 schema 在完成对应契约升级前仍可拒绝缺日期 preview，前端不得在日期缺失时直接提交 preview。

`study-plan-diagnostic-profiles` 会重新基于当前 `material_scope` 计算合法 topic 集。若请求中的 `question_version` 过期，或 `topic_mastery[].topic_id` 不属于当前资料范围，返回 `409 DIAGNOSTIC_STALE`，`details.invalid_topic_ids` 列出失效 topic。无可用 parsed 资料返回 `400 NO_PARSED_MATERIAL`。归纳出的 `diagnostic_profile` 可直接传给 `POST /api/v1/courses/{course_id}/study-plans/preview` 的 `diagnostic_profile` 字段；preview 会把英文 `preference` 派生为 `planner_strategy` 并与该 profile 一起写入 planner reduce prompt，用于影响 `content_depth`、例题强度、测评强度、review 强度、补基础、薄弱主题顺序和颗粒度、薄弱方向强化以及 description 解释风格；保存时继续追溯 `diagnostic_profile` 和 `planner_strategy`，不在本接口层提前生成讲义或任务测试题。

保存请求新增稳定字段 `client_flow`，可选值为 `legacy`、`wizard_v1`，默认 `legacy`。旧客户端不传 `client_flow` 且省略 `tasks` 时保留保存前生成 preview 的兼容路径；新向导必须传 `client_flow = "wizard_v1"`，并提交 preview 中展示和用户确认后的 exact `tasks`。当 `client_flow = "wizard_v1"` 且 `tasks` 缺失或为空数组时，后端返回 `422 PREVIEW_TASKS_REQUIRED`，不会进入兼容 preview 生成，也不会写入计划、任务、二级任务或打卡记录。`wizard_v1` 提交合法 `tasks` 时按确认任务树保存，`parsed_config_json.tasks_source = "confirmed"`。

保存接口支持 `Idempotency-Key`：key hash 写入 `study_plans.idempotency_key_hash`，request hash 保留在 `parsed_config_json.idempotency`；数据库通过 `(user_id, course_id, idempotency_key_hash)` 唯一索引兜底，同键同请求返回同一 plan bundle，同键不同请求返回 `IDEMPOTENCY_CONFLICT`，已软删除计划占用的 key 不可复用。保存和替换显式 `tasks` 时，后端必须在写库前校验任务树：至少一个一级任务、每个一级任务至少一个二级任务、任务日期位于计划日期范围、一级和二级 `sort_order` 从 1 连续递增，且所有 `related_material_ids` 属于当前用户、当前课程、本次 `material_scope` 并处于 parsed 可用状态；校验失败不得写入计划、任务、二级任务或打卡记录。替换接口通过数据库条件 UPDATE 原子校验 `expected_updated_at`，在已有进度、已绑定生成内容或 `expected_updated_at` 不匹配时返回 `STATE_CONFLICT`；失败请求不得删除或部分修改旧任务树和打卡记录。S02 不新增业务表，不在保存阶段生成讲义或任务测试题。Preview 和保存后的 `parsed_config_json.capacity` 均以最终任务树为事实来源：`estimated_total_minutes = sum(tasks[].subtasks[].estimated_minutes)`，`available_total_minutes = daily_available_minutes * duration_days`；超出容量时 `feasibility_status = "over_capacity"` 且 `warnings` 包含 `PLAN_OVER_CAPACITY`。`recommended_daily_minutes` 可继续基于 map 阶段资料规模估算，`study_plans.daily_available_minutes` 保存最终采用的每日学习时间。

Study Plan preview 额外返回资料解析质量摘要，位置固定为 `generation_metadata.material_quality.warnings`，不放入 `capacity.warnings`。该摘要只读取当前 `material_scope` 范围内生效解析版本的 `parse_quality` 和 `parse_diagnostics_json` 并映射为前端可展示 warning；`severity = "info"` 的 parser 诊断不升级为 warning。`NO_PARSED_MATERIAL` 和 `MATERIAL_COVERAGE_INCOMPLETE` 继续表示范围内没有可消费的生效版本。最小结构如下：

```json
{
  "generation_metadata": {
    "material_quality": {
      "warnings": [
        {
          "code": "MATERIAL_PARSE_PARTIAL",
          "message": "资料解析不完整，学习计划可能遗漏部分页面或内容",
          "material_id": "mat_123",
          "material_name": "chapter-01.pdf",
          "parse_quality": "partial",
          "page_no": null,
          "component": null,
          "details": {
            "parser": "docling",
            "profile": "pdf_text_first",
            "conversion_status": "partial_success",
            "failed_pages": [3]
          }
        }
      ]
    }
  }
}
```

已定义 warning code：`MATERIAL_PARSE_PARTIAL`、`MATERIAL_PARSE_QUALITY_UNKNOWN`、`MATERIAL_PARSE_DIAGNOSTIC_WARNING`。其中 parser 原始 warning code 保存在 `details.diagnostic_code`，原始 message 保存在 `details.diagnostic_message`。

重生成 preview 请求体字段均可选，支持覆盖 `goal_text`、`start_date`、`end_date`、`duration_days`、`daily_available_minutes`、`preference`、`preference_overrides`、`diagnostic_profile` 和 `material_scope`。未传字段继承已保存配置；未传 `diagnostic_profile` 时继承保存计划中的诊断 profile，显式传入新 profile（包括空对象）时覆盖；未传 `preference_overrides` 时继承保存的局部覆盖，显式传入对象时覆盖，显式 `{}` 时清空保存覆盖。只传 `duration_days` 时，后端必须基于保存的 `start_date` 或请求覆盖后的 `start_date` 重新推导 `end_date`，不得复用旧 `end_date` 造成范围冲突；只传 `end_date` 时重新计算 `duration_days`。接口只返回 `StudyPlanPreview`，不得写入 `StudyPlan`、`StudyTask`、`StudySubTask` 或 `CheckinRecord`。

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

### 执行页任务问答

`POST /api/v1/study-subtasks/{subtask_id}/qa/questions` 在计划执行页围绕当前二级任务发起问答。请求不接受 `material_scope`，后端固定使用当前 `StudySubTask.related_material_ids_json` 构造 `MaterialScope(include_all_parsed_materials=false, material_ids=...)`，并复用 Course QA 的检索、生成、引用保存和消息持久化链路。

请求体：

```json
{
  "conversation_id": null,
  "question": "这一节的关键公式是什么？"
}
```

响应 `data` 复用课程问答响应结构，并额外稳定返回实际使用的资料 ID：

```json
{
  "conversation_id": "cnv_123",
  "user_message_id": "msg_user",
  "assistant_message_id": "msg_assistant",
  "answer_text": "回答正文",
  "answer_type": "grounded",
  "source_citations": [],
  "used_material_ids": ["mat_123"]
}
```

规则：

- 新建对话时保存 `Conversation.source_page = "task_execution"`。
- 追问只能复用当前用户、当前课程且 `source_page = "task_execution"` 的对话；跨用户、跨课程或复用课程详情页对话均返回 `404 NOT_FOUND`。
- 用户消息的 `material_scope_json` 保存基础资料范围、`subtask_id`、`task_id` 和本次实际 `used_material_ids`。
- 当前二级任务关联资料没有 parsed chunk，或本次没有相关命中时返回 `answer_type = "no_source"`、`source_citations = []`、`used_material_ids = []`，不得伪造引用。
- 任务级问答不修改二级任务完成状态，不汇总一级任务或计划状态，也不写 `checkin_records`。

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
    "question_type_counts": [
      {"question_type": "single_choice", "question_count": 10},
      {"question_type": "short_answer", "question_count": 3}
    ],
    "difficulty": "medium"
  }
}
```

`question_count` 范围 1-20；`question_types` 支持 `single_choice`、`multiple_choice`、`true_false`、`short_answer`；`difficulty` 支持 `easy`、`medium`、`hard`。`question_type_counts` 可选，每项包含 `question_type` 和 `question_count`；一旦提供，后端会自动派生 `question_count = sum(question_type_counts[].question_count)`，并按顺序去重派生 `question_types`，显式提交的总题数或题型白名单若与分布冲突则返回参数校验错误。未提供 `question_type_counts` 时保持旧契约：`question_count + question_types` 仅表示总题数和题型白名单，不承诺平均分配。

`task_test.content_json.questions.length` 必须严格等于 `question_count`，题型必须来自请求白名单；当请求或计划默认参数包含 `question_type_counts` 时，实际输出中每种 `question_type` 的数量也必须精确匹配。题目 `id` / `sort_order` 必须从 1 连续，选择题选项和答案必须自洽；不满足时返回 `GENERATION_SCHEMA_INVALID`，不会保存部分成功题目。

成功响应统一为 `{data, meta}`，其中 `data` 是 `GeneratedContentRead`，至少包含 `id`、`course_id`、`study_subtask_id`、`content_type`、`title`、`content_json`、`generation_status`、`error_code`、`created_at` 和 `updated_at`。

`GeneratedContentRead` 的 `created_at`、`updated_at` 和可选 `deleted_at` 统一使用北京时间 ISO 8601 字符串，必须包含 `+08:00` 时区偏移，例如 `2026-07-15T22:18:10+08:00`。数据库中的无时区 SQLite 时间按 UTC 解释后再转换，客户端不得把无时区时间直接当作本地时间。

生成规则：

- `learn` / `review` 只能调用 handout endpoint；调用 task-test endpoint 返回 `STATE_CONFLICT`。
- `quiz` / `test` 只能调用 task-test endpoint；调用 handout endpoint 返回 `STATE_CONFLICT`。
- 材料范围严格来自 `StudySubTask.related_material_ids_json`，接口请求体不能覆盖资料范围。
- 后端使用 `MaterialScope(include_all_parsed_materials=false, material_ids=related_material_ids_json)`。
- S06 使用 `iter_material_context_batches()` 读取当前二级任务材料范围，不使用 Top-K 检索或旧 `resolve_context()`。`handout` 继续按材料批次 `run_material_coverage()` 后合并；`task_test` 汇总当前二级任务的全部材料批次后只调用一次 generator，生成固定 `question_count` 道题，不按 batch 拼接多套测试题。
- 默认请求幂等：同一 `study_subtask_id + content_type` 已有未删除 success 时直接返回最近成功内容，不调用模型、不新建 `AIGeneratedContent`。
- `force_regenerate=true` 时即使已有 success 也重新生成，并创建新的成功内容。
- failed 记录不作为幂等命中结果，也不阻止后续请求重新尝试生成。
- 成功和进入生成流程后的失败都写入 `ai_generated_contents`；权限、任务不存在和任务类型不匹配不会创建生成记录。
- execution-context 只返回最近一次成功内容 ID；最新 failed 记录不会覆盖 `handout_content_id` / `task_test_content_id`。
- 生成不会改变二级任务完成状态，不触发一级任务汇总，也不写 `checkin_records`。
- 前端可以基于成功 `task_test.content_json.questions` 提供本地逐题作答、提交后反馈和解析展示；该状态只存在浏览器内存，不新增 API 请求，不保存 attempt 历史，不参与任务完成、打卡、导出或后端判分。

错误码：401 `UNAUTHORIZED`；404 `NOT_FOUND`；409 `STATE_CONFLICT`；422 `VALIDATION_ERROR`；400 `NO_PARSED_MATERIAL`；409 `MATERIAL_COVERAGE_INCOMPLETE`；500 `GENERATION_SCHEMA_INVALID`；502 `GENERATION_FAILED`。

## S07 任务内容导出契约

### 任务测试题 Markdown 导出

`GET /api/v1/generated-contents/{generated_content_id}/exports/markdown`

要求：Bearer token。只能导出当前用户自己的、未删除且 `generation_status = "success"` 的 `task_test` 生成内容。接口返回文件流，不使用统一成功 envelope。

响应头：

- `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="task-test-{generated_content_id}.md"`

Markdown 内容包含标题、instructions、题目、选项、正确答案、解析和引用来源。题目中的 `source_citation_ids` 只和 `GeneratedContentRead.source_citations[].id` 匹配；匹配不到时写 `Sources: unavailable`，不得伪造引用。

错误码：

- 401 `UNAUTHORIZED`：未登录。
- 404 `NOT_FOUND`：生成内容不存在、已删除或不属于当前用户。
- 409 `EXPORT_UNSUPPORTED_CONTENT_TYPE`：当前 `content_type` 不是 `task_test`。
- 409 `EXPORT_CONTENT_NOT_READY`：当前 `generation_status` 不是 `success`。
- 500 `EXPORT_CONTENT_INVALID`：`content_json` 不是合法的任务测试题结构，例如缺少非空 `questions`。

### 今日讲义 PDF 导出

`GET /api/v1/generated-contents/{generated_content_id}/exports/pdf`

要求：Bearer token。只能导出当前用户自己的、未删除且 `generation_status = "success"` 的 `handout` 生成内容。接口返回文件流，不使用统一成功 envelope，不保存导出历史。

响应头：

- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="handout-{generated_content_id}.pdf"`

PDF 内容渲染 `GeneratedContentRead.content` 中的完整 Markdown 讲义，包括标题、正文、表格、数学公式和 callout；来源说明保留在 Markdown 顶部，不渲染逐段引用列表。轻量阶段仅支持任务讲义 PDF；`task_test` 调用 PDF 导出返回 `EXPORT_UNSUPPORTED_CONTENT_TYPE`，任务测试题使用 Markdown 导出。

错误码：

- 401 `UNAUTHORIZED`：未登录。
- 404 `NOT_FOUND`：生成内容不存在、已删除或不属于当前用户。
- 409 `EXPORT_UNSUPPORTED_CONTENT_TYPE`：当前 `content_type` 不是 `handout`。
- 409 `EXPORT_CONTENT_NOT_READY`：当前 `generation_status` 不是 `success`。
- 500 `EXPORT_CONTENT_INVALID`：`content_json` 不是合法的今日讲义结构。
- 500 `EXPORT_FAILED`：PDF 渲染或写出失败，不影响原 generated content。
## 2026-07-13 任务内容修复契约补充

- 学习计划保存和替换会在 `parsed_config_json.task_snapshot[].subtasks[].generation_parameters.task_test` 中追溯 quiz/test 子任务默认测试题参数；保存阶段只保存参数，不提前生成 `AIGeneratedContent`。
- 计划预览的模型输出可接受常见二级任务类型别名并在服务端归一化；对外响应、保存快照和数据库仍只使用规范值 `learn`、`review`、`quiz`、`test`。
- `POST /api/v1/study-subtasks/{subtask_id}/task-tests` 的请求 `parameters` 省略或为空时，后端优先读取计划快照中的 `task_test` 默认值；非法默认参数在生成阶段返回 `GENERATION_SCHEMA_INVALID` 并保存 failed 记录。
- 合并计划默认参数和本次请求时，本次请求显式传 `question_type_counts` 或其兼容别名会整体覆盖计划中的题型分布；本次请求只传 `difficulty` 时保留计划分布；本次请求显式传 `question_count` 或字符串数组形式的 `question_types`、但不传按题型计数时，会清掉计划里的 `question_type_counts`，退回“总题数 + 题型白名单”旧契约。
- 保存计划时会把模型输出的任务测试题参数别名归一化后写入快照；支持按题型计数对象、题型计数列表、`question_types` / `items` / `question_type_counts` 内嵌 `{type,count}` 或 `{question_type,question_count}` 对象、`task_test` 字符串 shorthand 搭配同级 `question_count`，以及题量文案到题型的映射，最终保存为规范 `question_count`、`question_types`、`question_type_counts` 和 `difficulty`。
- `task_test` 生成器使用 chunk id 校验逐题引用范围；保存成功后同一事务创建 `SourceCitation` 行，并将 `content_json.questions[].source_citation_ids` 回绑为 `SourceCitation.id`。前端逐题来源和 Markdown 导出都只按这些合法 ID 匹配，缺失时不得补造来源。新生成 `handout` 不创建 `SourceCitation`，其来源说明与真实资料范围都从实际 material-context batch 构建。
- 执行页 QA 的 `OpenAIModelProvider.answer_question()` 在兼容服务对 `/responses` 返回 404 时回退 Chat Completions；非 404 的鉴权、网络、限流或服务端错误语义不变。
- 今日讲义 PDF renderer 同时声明 `STSong-Light` 和 `Helvetica`：中文/CJK run 使用 `STSong-Light`，ASCII、数字、英文术语和公式 run 使用 `Helvetica`，避免 `Overview`、`Nyquist/Shannon` 等英文被中文 CID 字体逐字排版。
- 物理层讲义生成后会扫描已知术语误拼，例如 `Nyquest`、`Shanon`、`bandwith`；命中时按 `GENERATION_SCHEMA_INVALID` 拒绝，不静默落库。

## 2026-07-15 Handout Markdown / Callout 契约补充

本节补充 S06/S07 当前权威口径，并覆盖旧文中“今日讲义 PDF 包含结构化 sections/blocks”的历史描述。新生成 `handout` 为 Markdown-first：

- `GeneratedContentRead.content_type = "handout"`
- `GeneratedContentRead.content` 保存完整 Markdown 讲义正文
- `GeneratedContentRead.content_json = {"format":"markdown","schema_version":1}`
- `GeneratedContentRead.source_citations = []`，来源说明写在 Markdown 顶部

后端 handout prompt 约束模型输出标准 Markdown：行内公式 `$...$`，块级公式独立 `$$...$$`，禁止 `\(...\)` / `\[...\]` 和单独一行 `[` / `]` 包公式。教学提示块只能使用 GitHub alert 风格 blockquote，不输出 HTML。支持的 callout 类型固定为 `NOTE`、`EXAMPLE`、`SUMMARY`、`WARNING`、`TIP`。

Callout 示例：

```md
> [!SUMMARY] 核心结论
> 物理层负责定义接口、信号、传输介质和传输过程相关规则。
```

前端详情页和 PDF 导出都必须识别该契约。前端使用 `react-markdown + remark-gfm + remark-math + rehype-katex`；PDF 使用 `markdown-it-py` 生成 HTML 后转换受支持的 callout blockquote，并用本地 KaTeX + Playwright 输出 PDF。两端视觉都保留背景色、去掉左侧强调线、使用圆角。

`GET /api/v1/generated-contents/{generated_content_id}/exports/pdf` 对成功 handout 直接读取 Markdown 内容并渲染 PDF，不要求旧 `content_json` 结构合法；`task_test` 仍只支持 Markdown 导出，不支持 PDF。
