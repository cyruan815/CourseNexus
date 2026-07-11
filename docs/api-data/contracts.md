# Contracts v0.1

## 前后端契约基线

- 基础设施阶段的前端是最小集成验证工作台；已落地接口、请求体和响应字段以 [frontend-integration.md](frontend-integration.md) 为前端接入入口。
- 当前已落地的后端接口范围包括 Auth、Courses、Materials、Material Context、Course QA、Generation 和 Study Plans。
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

S01 只固定计划学习模式的子系统契约和数据库审计结论，不实现新的业务 API，也不创建 migration。当前已落地的计划接口仍只有：

| 方法与路径 | 状态 | 说明 |
| --- | --- | --- |
| `POST /api/v1/courses/{course_id}/study-plans/preview` | 已实现 | 当前为确定性占位计划，S02 替换为真实全材料生成。 |
| `POST /api/v1/courses/{course_id}/study-plans` | 已实现 | 保存计划、一级任务和二级任务结构，S02 继续扩展确认后的任务树保存。 |
| `GET /api/v1/courses/{course_id}/study-plans` | 已实现 | 查询课程下未删除计划列表。 |
| `GET /api/v1/study-plans/{plan_id}` | 已实现 | 查询单个计划及任务结构。 |

S02-S07 的候选接口在对应任务合并前均视为未实现契约，前端不得提前调用或自行拼接路径：

| 任务 | 方法与路径 | 用途 |
| --- | --- | --- |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-config-parses` | 自然语言配置回填。 |
| S02 | `POST /api/v1/study-plans/{plan_id}/regeneration-previews` | 基于已保存计划生成不落库的新预览。 |
| S02 | `PUT /api/v1/study-plans/{plan_id}` | 原子替换计划配置和任务结构。 |
| S02 | `DELETE /api/v1/study-plans/{plan_id}` | 软删除计划。 |
| S03 | `GET /api/v1/todos/today?date=YYYY-MM-DD` | 当前用户多课程今日待办。 |
| S03 | `GET /api/v1/calendar/month?month=YYYY-MM` | 全局月历日期摘要。 |
| S03 | `GET /api/v1/calendar/days/{date}/todos` | 全局当日待办，按课程分组。 |
| S03 | `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM` | 单课程月历。 |
| S03 | `GET /api/v1/courses/{course_id}/study-calendar/days/{date}` | 单课程当日任务。 |
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
| `POST /api/v1/courses/{course_id}/study-plans/preview` | 已实现 | 基于全部已解析资料生成 preview，返回 `coverage`。 |
| `POST /api/v1/courses/{course_id}/study-plans` | 已实现 | 保存用户确认的任务树；支持旧客户端省略 `tasks` 时先生成 preview。 |
| `POST /api/v1/study-plans/{plan_id}/regeneration-previews` | 已实现 | 生成新 preview，不写数据库。 |
| `PUT /api/v1/study-plans/{plan_id}` | 已实现 | 基于 `expected_updated_at` 原子替换配置和任务树。 |
| `DELETE /api/v1/study-plans/{plan_id}` | 已实现 | 软删除计划，默认列表和详情隐藏。 |

保存接口支持 `Idempotency-Key`：同键同请求返回同一 plan bundle；同键不同请求返回 `IDEMPOTENCY_CONFLICT`。替换接口在已有进度、已绑定生成内容或 `expected_updated_at` 不匹配时返回 `STATE_CONFLICT`。S02 不新增表、不修改 migration，不在保存阶段生成讲义或任务测试题。