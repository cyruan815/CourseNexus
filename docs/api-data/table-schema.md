# Table Schema v0.1

## 目的

本文把 PRD 第 13 章字段字典转换为 CourseNexus v0.1 后端可落地的数据表字段契约。它服务于 SQLAlchemy model、Alembic migration、API schema 和前后端联调。

本文不替代 [data-model.md](data-model.md)。`data-model.md` 说明核心实体、关系、状态和数据归属原则；本文说明 v0.1 POC 需要创建哪些表、字段、约束和索引。

## 设计口径

- 当前数据库使用 SQLite，但字段设计避免依赖 SQLite 专有能力，保留 PostgreSQL 迁移空间。
- 表名使用 `snake_case` 复数形式；API 字段和 Pydantic schema 继续使用 `snake_case`。
- ID 使用后端生成的不透明字符串，建议 UUID 或 ULID，不使用自增 ID 暴露业务含义。
- `created_at`、`updated_at`、`deleted_at` 使用 ISO 8601 datetime 语义；数据库层可用 timezone-aware datetime。
- 主要业务表使用软删除；默认查询必须过滤 `deleted_at is null` 或对应删除状态。
- `user_id` 是权限隔离的核心字段；即使可以经由课程间接追溯到用户，常用业务表也保留 `user_id` 冗余以便过滤和防止越权。
- 结构化 AI 内容 v0.1 优先写入 `ai_generated_contents.content_json`，暂不强制拆 `quiz`、`flashcard`、`mindmap` 独立表。

## 表清单

| 表名 | 实体 | 归属模块 | 说明 |
| --- | --- | --- | --- |
| `users` | `User` | `users` | 用户账号与个人资料。 |
| `courses` | `Course` | `courses` | 课程基础信息。 |
| `material_folders` | `MaterialFolder` | `materials` | 课程资料一级目录。 |
| `course_materials` | `CourseMaterial` | `materials` | 文件或链接资料。 |
| `material_chunks` | `MaterialChunk` | `materials` | 资料解析后的检索切片。 |
| `conversations` | `Conversation` | `course-qa` | 课程问答会话。 |
| `messages` | `Message` | `course-qa` | 用户消息或助手消息。 |
| `source_citations` | `SourceCitation` | `course-qa` / `generated-content` | 引用来源快照。 |
| `ai_generated_contents` | `AIGeneratedContent` | `generated-content` | AI 生成内容统一记录。 |
| `study_plans` | `StudyPlan` | `study-plans` | 单课程学习计划。 |
| `study_tasks` | `StudyTask` | `study-plans` | 每日一级任务。 |
| `study_subtasks` | `StudySubTask` | `study-plans` / `learning-execution` | 二级学习任务。 |
| `checkin_records` | `CheckinRecord` | `checkins` | 每日学习完成记录。 |

## S01 计划学习模式表结构审计

S01 已用 `backend/tests/modules/study_mode/test_subsystem_schema_contract.py` 对计划学习模式依赖的 13 张核心表做 metadata 契约测试。审计结论：

- 当前表集合必须严格等于 `users`、`courses`、`material_folders`、`course_materials`、`material_chunks`、`conversations`、`messages`、`source_citations`、`ai_generated_contents`、`study_plans`、`study_tasks`、`study_subtasks`、`checkin_records`。
- S01 不新增 Alembic migration，不修改 `backend/migrations/versions/20260709_0001_create_core_tables.py`。
- `checkin_records` 必须保留 `(user_id, checkin_date)` 唯一约束，支持每用户每日一条打卡记录。
- `ai_generated_contents.content_type` 必须支持 `handout` 和 `task_test`，并通过 `study_subtask_id` 绑定二级任务。
- `study_plans.status`、`study_tasks.status`、`study_subtasks.subtask_type` 必须由数据库约束拒绝非法枚举值。
- schema 中不得出现 `todos`、`calendar_events`、`handouts`、`task_tests`、`export_records` 独立业务表。
## PRD 数据对象落库状态

本节依据 PRD 第 13 章“数据对象清单”和“字段字典”整理。当前已在 `backend/` 创建 SQLAlchemy models 和 Alembic baseline migration，并已可通过 SQLite 建出以下 v0.1 核心业务表。这里的状态只表示数据表结构状态，不代表对应业务 API、service、repository 已完成。

### PRD 要求且 v0.1 应建表

| PRD 数据对象 | v0.1 表名 | 当前状态 | 归属模块 | 后续缺口 |
| --- | --- | --- | --- | --- |
| `User` | `users` | 已建表 | `users` | 还需实现注册、登录、密码哈希、当前用户识别和权限依赖。 |
| `Course` | `courses` | 已建表 | `courses` | 还需实现课程 CRUD、归属校验和软删除隐藏规则。 |
| `MaterialFolder` | `material_folders` | 已建表并已接入 API | `materials` | 已实现一级目录创建、列表、重命名、排序、删除回未分类和资料移动。 |
| `CourseMaterial` | `course_materials` | 已建表 | `materials` | 还需实现上传、链接保存、解析状态流转、重试和资料预览。 |
| `MaterialChunk` | `material_chunks` | 已建表 | `materials` | 还需实现资料解析切片、索引写入和重新解析后的旧切片处理。 |
| `Conversation` | `conversations` | 已建表 | `course-qa` | 还需实现会话创建、连续追问和课程内会话查询。 |
| `Message` | `messages` | 已建表 | `course-qa` | 还需实现消息保存、生成失败记录和重试策略。 |
| `SourceCitation` | `source_citations` | 已建表 | `course-qa` / `generated-content` | 问答与G01生成链路已实现真实引用、快照保存和未知位置降级；G02-G06继续提供逐条目引用。 |
| `AIGeneratedContent` | `ai_generated_contents` | 已建表 | `generated-content` | 还需实现生成编排、内容保存、历史列表、详情查询和 PDF 导出入口。 |
| `StudyPlan` | `study_plans` | 已建表 | `study-plans` | 还需实现自然语言配置回填、计划预览、保存和删除。 |
| `StudyTask` | `study_tasks` | 已建表 | `study-plans` | 还需实现保存计划时生成一级任务和任务状态汇总。 |
| `StudySubTask` | `study_subtasks` | 已建表 | `study-plans` / `learning-execution` | 还需实现二级任务生成、完成状态幂等更新和关联资料校验。 |
| `CheckinRecord` | `checkin_records` | 已建表 | `checkins` | 还需实现按二级任务完成比例幂等更新打卡记录。 |

实现要求：

- `backend/migrations/versions/20260709_0001_create_core_tables.py` 是当前 13 张表的 baseline migration。
- 如果后续为了 walking skeleton 临时只接入部分表对应的 API，必须在任务说明中明确已接入和暂缓的业务能力，并同步更新本文。
- 上线前必须满足 PRD 第 18.2 节“数据库：完成真实数据库表结构和必要索引”的要求。

### PRD 提到但 v0.1 不单独建表

| PRD 对象 / 功能 | 当前没有的独立表 | v0.1 落库方式 | 不单独建表原因 |
| --- | --- | --- | --- |
| `Quiz` | `quizzes`、`quiz_questions` | `ai_generated_contents.content_type = quiz`，题目写入 `content_json.questions`。 | PRD 允许 Quiz 作为 `AIGeneratedContent.content_json` 中的结构化数据；v0.1 暂无答题记录、错题本或题库复用要求。 |
| `Flashcard` | `flashcards` | `ai_generated_contents.content_type = flashcard`，卡片写入 `content_json.cards`。 | PRD 明确本期不做复杂间隔复习算法；卡片级长期掌握度可后续再拆。 |
| `Mindmap` | `mindmaps`、`mindmap_nodes`、`mindmap_edges` | `ai_generated_contents.content_type = mindmap`，节点和边写入 `content_json`。 | PRD 建议 Mindmap 保存在 `AIGeneratedContent.content_json` 中；v0.1 不需要节点级编辑或图查询。 |
| 复习提纲 | `outlines`、`outline_sections` | `ai_generated_contents.content_type = outline`，章节结构写入 `content_json.sections`。 | PRD 将复习提纲归入 AI 生成内容历史记录，不要求独立提纲表。 |
| 知识点清单 | `knowledge_lists`、`knowledge_list_items` | `ai_generated_contents.content_type = knowledge_list`，知识点写入 `content_json.items`。 | v0.1 只需展示生成结果和引用来源，不做知识点级掌握模型。 |
| 保存为笔记 | `notes` | `ai_generated_contents.content_type = note`，正文写入 `content`，来源消息用 `source_message_id`。 | PRD 明确不新增 Note 对象。 |
| 今日讲义 | `handouts` | `ai_generated_contents.content_type = handout`，并关联 `study_subtask_id`。 | PRD 要求按需生成并绑定二级任务，不要求独立讲义表。 |
| 任务测试题 | `task_tests`、`task_test_questions` | `ai_generated_contents.content_type = task_test`，题目写入 `content_json.questions`，并关联 `study_subtask_id`。 | PRD 要求进入任务测试题页面后按需生成，不在计划保存时提前生成。 |
| 首页今日待办 / 首页大日历 | `todos`、`calendar_events` | 从 `study_tasks` 和 `study_subtasks` 按日期只读聚合。 | PRD 明确首页今日待办和大日历只负责查看与跳转，不创建独立任务模型。 |
| PDF 导出 | `export_records` | v0.1 可直接基于已生成内容导出 PDF 文件。 | PRD 只要求支持导出，不要求保留导出历史。 |
| 埋点事件 | `analytics_events` | v0.1 可先接入日志或外部埋点，不纳入核心业务表。 | PRD 要求核心事件可上报并验证字段，但不要求本地业务库保存埋点明细。 |

## 通用字段约定

| 字段 | 类型 | Null | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | 主键，不透明 ID。 |
| `created_at` | datetime | 否 | 当前时间 | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 | 更新时间；创建时等于 `created_at`。 |
| `deleted_at` | datetime | 是 | null | 软删除时间；无软删除需求的表可不设置。 |

实现规则：

- 有 `updated_at` 的表，更新业务字段时必须同步更新。
- 有 `deleted_at` 的表，删除接口默认写入 `deleted_at`，不物理删除业务数据。
- 软删除数据默认不进入列表、检索上下文、日历聚合、今日待办和生成上下文。

## 枚举

| 枚举 | 值 |
| --- | --- |
| `user_status` | `active`、`disabled` |
| `course_status` | `active`、`archived`、`deleted` |
| `material_type` | `pdf`、`ppt`、`word`、`markdown`、`image`、`text`、`link` |
| `source_type` | `file`、`url` |
| `parse_status` | `uploaded`、`parsing`、`parsed`、`parse_failed`、`deleted` |
| `parse_quality` | `unknown`、`complete`、`partial` |
| `conversation_status` | `active`、`deleted` |
| `message_role` | `user`、`assistant`、`system` |
| `answer_type` | `grounded`、`partial_grounded`、`no_source` |
| `generation_status` | `pending`、`generating`、`success`、`failed` |
| `content_type` | `quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`、`note`、`handout`、`task_test` |
| `plan_status` | `draft`、`active`、`completed`、`deleted` |
| `task_status` | `not_started`、`in_progress`、`completed` |
| `subtask_type` | `learn`、`review`、`quiz`、`test` |

数据库实现可使用 string column + application-level enum 校验；迁移 PostgreSQL 后再评估是否使用原生 enum。

## users

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 用户 ID。 |
| `username` | string | 否 | 无 | UNIQUE | 登录账号。 |
| `password_hash` | string | 否 | 无 |  | 密码哈希，不存明文。 |
| `nickname` | string | 是 | null |  | 用户昵称。 |
| `avatar_url` | string | 是 | null |  | 头像地址。 |
| `status` | enum `user_status` | 否 | `active` | INDEX | 用户状态。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |
| `deleted_at` | datetime | 是 | null | INDEX | 删除时间。 |

规则：

- 登录使用 `username` + 密码。
- `password_hash` 只能保存哈希值，不允许保存明文或可逆加密结果。
- `username` 全局唯一；如果后续支持账号恢复或硬删除，需要单独评审唯一约束策略。

## courses

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 课程 ID。 |
| `user_id` | string | 否 | 无 | FK -> `users.id`, INDEX | 所属用户。 |
| `name` | string | 否 | 无 | INDEX(`user_id`, `name`) | 课程名称。 |
| `description` | text | 是 | null |  | 课程简介。 |
| `teacher` | string | 是 | null |  | 教师。 |
| `term` | string | 是 | null |  | 学期标准值；API 仅允许课程学期选项接口返回的值或 `null`。 |
| `status` | enum `course_status` | 否 | `active` | INDEX | 课程状态。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |
| `deleted_at` | datetime | 是 | null | INDEX | 删除时间。 |

规则：

- `material_count` 是查询派生字段，不在 `courses` 表持久化。
- 当前用户下课程名允许重复，前端通过教师、学期、创建时间等信息辅助区分。
- `term` 默认且允许为 `null`。当前标准值为 `2024-2025` 至 `2027-2028` 学年的 `autumn`、`spring` 编码；数据库保持字符串列以便后续扩展，规范性由创建和更新 API 校验。
- 删除课程写入 `deleted_at` 并将 `status` 置为 `deleted`；关联资料、对话、生成内容、计划和任务默认隐藏。

## material_folders

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 目录 ID。 |
| `user_id` | string | 否 | 无 | FK -> `users.id`, INDEX | 所属用户，冗余便于权限过滤。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程。 |
| `name` | string | 否 | 无 | INDEX(`course_id`, `name`) | 目录名称。 |
| `sort_order` | integer | 是 | null | INDEX(`course_id`, `sort_order`) | 展示排序，从 1 开始。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |
| `deleted_at` | datetime | 是 | null | INDEX | 删除时间。 |

规则：

- v0.1 只支持一级目录，不设置 `parent_id`。
- 目录必须归属于一门课程，且课程必须属于当前用户。
- 删除目录时不删除目录下资料，应将 `course_materials.folder_id` 置空，资料回到未分类。
- 目录只用于资料归类和列表浏览，不属于 Agent `MaterialScope`；资料范围只能使用具体 `material_ids`。

## course_materials

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 资料 ID。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程。 |
| `user_id` | string | 否 | 无 | FK -> `users.id`, INDEX | 上传用户。 |
| `folder_id` | string | 是 | null | FK -> `material_folders.id`, INDEX | 所属一级目录；null 表示未分类。 |
| `name` | string | 否 | 无 | INDEX(`course_id`, `name`) | 展示名称，允许重名。 |
| `material_type` | enum `material_type` | 否 | 无 | INDEX | 资料类型。 |
| `source_type` | enum `source_type` | 否 | 无 | INDEX | 来源类型。 |
| `file_url` | string | 是 | null |  | 内部文件地址；文件资料必填，文件名使用 ASCII `source.<ext>`，展示名使用 `name`。 |
| `source_url` | string | 是 | null |  | 原始链接；链接资料必填。 |
| `file_size` | integer | 是 | null |  | 文件大小，单位 byte。 |
| `mime_type` | string | 是 | null |  | MIME 类型。 |
| `parse_status` | enum `parse_status` | 否 | `uploaded` | INDEX(`course_id`, `parse_status`) | 解析状态。 |
| `parse_error` | text | 是 | null |  | 解析失败原因。 |
| `parse_quality` | enum `parse_quality` | 否 | `unknown` |  | 当前解析结果的完整性判断。 |
| `parse_diagnostics_json` | json | 是 | null |  | Parser、profile、页覆盖、失败页和 warning。 |
| `page_count` | integer | 是 | null |  | Parser 报告的文档总页数；非分页文本为 null。 |
| `created_at` | datetime | 否 | 当前时间 | INDEX | 上传时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |
| `deleted_at` | datetime | 是 | null | INDEX | 删除时间。 |

规则：

- `source_type = file` 时 `file_url` 必填；`source_type = url` 时 `source_url` 必填。
- 只有 `parse_status = parsed` 且未软删除的资料可进入检索、问答、生成和计划上下文。
- `parse_status = parsed` 可与 `parse_quality = partial` 同时存在：资料有可消费 chunk，但不能据此声称完整覆盖原文档。
- 历史已解析数据和没有诊断能力的 parser 使用 `parse_quality = unknown`，不得自动回填为 `complete`。
- 删除资料写入 `deleted_at` 并将 `parse_status` 置为 `deleted`；历史引用继续通过 `source_citations.material_name` 展示快照。

`parse_diagnostics_json` 契约：

```json
{
  "parser": "docling",
  "profile": "pdf_text_first",
  "conversion_status": "partial_success",
  "page_count": 59,
  "processed_pages": [1, 2, 3],
  "pages_with_content": [1, 2],
  "pages_with_chunks": [1, 2],
  "failed_pages": [3],
  "warnings": [
    {
      "code": "OCR_MEMORY_ERROR",
      "message": "OCR 内存分配失败",
      "page_no": 3,
      "component": "rapidocr",
      "severity": "warning"
    }
  ]
}
```

页码数组使用一基页码并按升序去重。API 只返回稳定 warning code、安全消息、组件名和页码，不返回本地文件路径或异常堆栈。

## material_chunks

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 切片 ID。 |
| `material_id` | string | 否 | 无 | FK -> `course_materials.id`, INDEX | 所属资料。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程，冗余便于检索过滤。 |
| `chunk_index` | integer | 否 | 无 | UNIQUE(`material_id`, `chunk_index`) | 同资料内递增切片序号。 |
| `page` | string | 是 | null | INDEX | 真实页码；PDF 可用。 |
| `page_index` | integer | 是 | null | INDEX | 页序号；PPT 或无法识别页码时使用。 |
| `heading` | string | 是 | null |  | 标题或章节。 |
| `content_text` | text | 否 | 无 |  | 切片文本，检索基础。 |
| `embedding_id` | string | 是 | null | INDEX | 向量索引 ID，视实现而定。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |

规则：

- 切片必须能反向定位到原资料和课程。
- 重新解析资料时，新切片替换旧切片；如果历史引用定位到旧切片失败，前端仍展示引用快照。
- v0.1 不强制在 SQLite 内保存向量；`embedding_id` 可指向外部或本地向量索引。

## conversations

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 对话 ID。 |
| `user_id` | string | 否 | 无 | FK -> `users.id`, INDEX | 所属用户。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程。 |
| `title` | string | 是 | null |  | 对话标题，可由首问生成。 |
| `source_page` | string | 是 | null | INDEX | 来源页面，如 `course_detail`、`task_execution`。 |
| `status` | enum `conversation_status` | 否 | `active` | INDEX | 对话状态。 |
| `created_at` | datetime | 否 | 当前时间 | INDEX | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |
| `deleted_at` | datetime | 是 | null | INDEX | 删除时间。 |

规则：

- 一个对话只能属于一门课程。
- 连续追问必须复用同一个 `conversation_id`。
- 删除课程后，对话默认隐藏。

## messages

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 消息 ID。 |
| `conversation_id` | string | 否 | 无 | FK -> `conversations.id`, INDEX | 所属对话。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程，冗余便于权限过滤。 |
| `role` | enum `message_role` | 否 | 无 | INDEX | 消息角色。 |
| `content` | text | 否 | 无 |  | 消息正文。 |
| `answer_type` | enum `answer_type` | 是 | null | INDEX | 助手回答类型。 |
| `generation_status` | enum `generation_status` | 是 | null | INDEX | 助手消息生成状态。 |
| `error_code` | string | 是 | null | INDEX | 失败错误码。 |
| `material_scope_json` | json | 是 | null |  | 提问时资料范围，用户消息建议保存。 |
| `created_at` | datetime | 否 | 当前时间 | INDEX | 创建时间。 |

规则：

- 用户消息发送后即保存。
- 助手消息生成失败时也应保存失败状态和错误码。
- `role = assistant` 时可设置 `answer_type` 和 `generation_status`；`role = user` 时通常为空。

## source_citations

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 引用 ID。 |
| `message_id` | string | 是 | null | FK -> `messages.id`, INDEX | 关联消息。 |
| `generated_content_id` | string | 是 | null | FK -> `ai_generated_contents.id`, INDEX | 关联 AI 生成内容。 |
| `material_id` | string | 否 | 无 | FK -> `course_materials.id`, INDEX | 来源资料。 |
| `chunk_id` | string | 是 | null | FK -> `material_chunks.id`, INDEX | 来源切片。 |
| `material_name` | string | 否 | 无 |  | 资料名快照。 |
| `page` | string | 是 | null |  | 真实页码。 |
| `page_index` | integer | 是 | null |  | 页序号。 |
| `hit_text` | text | 否 | 无 |  | 命中文本片段。 |
| `sort_order` | integer | 是 | null | INDEX | 展示顺序，从 1 开始。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |

规则：

- `message_id` 与 `generated_content_id` 至少一个非空。
- 不允许生成没有 `material_id` 的伪引用。
- `material_name` 是快照字段，资料改名或删除后仍用于历史展示。
- 数据库约束保留`page`和`page_index`至少一个非空。无分页Text/Markdown引用兼容保存`page=null,page_index=0`；0是未知位置哨兵，前端展示“页码未知”，不得解释为真实第0页。
- 生成内容引用的`sort_order`从1连续递增；历史兼容数据允许为null，读取时使用`ASC NULLS LAST`和引用ID保证SQLite/PostgreSQL顺序一致。

## ai_generated_contents

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 生成内容 ID。 |
| `user_id` | string | 否 | 无 | FK -> `users.id`, INDEX | 所属用户。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程。 |
| `study_subtask_id` | string | 是 | null | FK -> `study_subtasks.id`, INDEX | 关联二级任务，任务讲义 / 测试使用。 |
| `source_message_id` | string | 是 | null | FK -> `messages.id`, INDEX | 来源消息，保存为笔记时可用。 |
| `content_type` | enum `content_type` | 否 | 无 | INDEX(`course_id`, `content_type`) | 内容类型。 |
| `title` | string | 否 | 无 |  | 标题，可自动生成。 |
| `content` | text | 是 | null |  | 正文内容，文本类内容使用。 |
| `content_json` | json | 是 | null |  | 结构化内容，Quiz、Flashcard、Mindmap 等使用。 |
| `generation_status` | enum `generation_status` | 否 | `pending` | INDEX | 生成状态。 |
| `material_scope_json` | json | 是 | null |  | 生成时资料范围，便于复现。 |
| `error_code` | string | 是 | null | INDEX | 失败错误码。 |
| `created_at` | datetime | 否 | 当前时间 | INDEX | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |
| `deleted_at` | datetime | 是 | null | INDEX | 删除时间。 |

规则：

- 保存为笔记统一使用 `content_type = note`，不新增 Note 表。
- 今日讲义使用 `content_type = handout`，并关联 `study_subtask_id`。
- 计划执行中的任务测试题使用 `content_type = task_test`，并关联测试类 `study_subtask_id`。
- 课程详情页生成的课程自测 Quiz 使用 `content_type = quiz`。
- 引用来源统一通过 `source_citations.generated_content_id` 关联。

## study_plans

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 计划 ID。 |
| `user_id` | string | 否 | 无 | FK -> `users.id`, INDEX | 所属用户。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程，本期单课程计划。 |
| `title` | string | 否 | 无 | INDEX(`course_id`, `title`) | 计划名称。 |
| `goal_text` | text | 否 | 无 |  | 用户自然语言目标原文。 |
| `parsed_config_json` | json | 是 | null |  | 自然语言解析后的配置，可编辑后保存。 |
| `start_date` | date | 否 | 无 | INDEX | 开始日期。 |
| `end_date` | date | 否 | 无 | INDEX | 结束日期，不早于开始日期。 |
| `daily_available_minutes` | integer | 否 | 无 |  | 每日可用学习时长，单位分钟。 |
| `status` | enum `plan_status` | 否 | `draft` | INDEX | 计划状态。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |
| `deleted_at` | datetime | 是 | null | INDEX | 删除时间。 |

规则：

- 本期明确只支持单课程计划，不使用 `course_ids`。
- 多门课程计划通过创建多个 `study_plans` 实现。
- 保存计划时生成任务结构，不提前生成讲义和任务测试题正文。

## study_tasks

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 一级任务 ID。 |
| `plan_id` | string | 否 | 无 | FK -> `study_plans.id`, INDEX | 所属计划。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程，冗余便于查询。 |
| `title` | string | 否 | 无 |  | 一级任务标题。 |
| `task_date` | date | 否 | 无 | INDEX(`course_id`, `task_date`) | 任务日期，用于日历展示。 |
| `start_time` | time | 是 | null |  | 开始时间，本期可为空。 |
| `end_time` | time | 是 | null |  | 结束时间，本期可为空。 |
| `status` | enum `task_status` | 否 | `not_started` | INDEX | 一级任务状态。 |
| `sort_order` | integer | 否 | 无 | INDEX(`plan_id`, `task_date`, `sort_order`) | 当日排序，从 1 开始。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |

规则：

- 一级任务状态由下属二级任务完成情况自动计算。
- 首页大日历日期格只展示日期级任务摘要；完整知识点列表由弹窗按课程展开。
- 如果所属 `study_plans` 软删除，查询层必须隐藏对应任务。

## study_subtasks

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 二级任务 ID。 |
| `task_id` | string | 否 | 无 | FK -> `study_tasks.id`, INDEX | 所属一级任务。 |
| `plan_id` | string | 否 | 无 | FK -> `study_plans.id`, INDEX | 所属计划，冗余便于查询。 |
| `course_id` | string | 否 | 无 | FK -> `courses.id`, INDEX | 所属课程，冗余便于查询。 |
| `title` | string | 否 | 无 |  | 二级任务标题。 |
| `subtask_type` | enum `subtask_type` | 否 | 无 | INDEX | 任务类型。 |
| `description` | text | 是 | null |  | 任务说明。 |
| `related_material_ids_json` | json | 是 | null |  | 关联资料 ID 列表。 |
| `status` | enum `task_status` | 否 | `not_started` | INDEX | 完成状态。 |
| `completed_at` | datetime | 是 | null | INDEX | 完成时间。 |
| `sort_order` | integer | 否 | 无 | INDEX(`task_id`, `sort_order`) | 排序，从 1 开始。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |

规则：

- 计划学习执行页左侧只展示今日二级任务。
- 学习类二级任务可按需生成今日讲义。
- 测试类二级任务进入任务测试题页面 / 视图后再生成任务测试题。
- 完成状态更新必须幂等，并同步一级任务状态、今日待办、日历聚合和 `checkin_records`。
- `related_material_ids_json` 只能引用当前课程下当前用户可访问的资料。

## checkin_records

| 字段 | 类型 | Null | 默认值 | 约束 / 索引 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | string | 否 | 后端生成 | PK | 学习完成记录 ID。 |
| `user_id` | string | 否 | 无 | FK -> `users.id`, UNIQUE(`user_id`, `checkin_date`) | 所属用户。 |
| `checkin_date` | date | 否 | 无 | UNIQUE(`user_id`, `checkin_date`) | 日期。 |
| `total_subtask_count` | integer | 否 | `0` |  | 当日二级任务总数。 |
| `completed_subtask_count` | integer | 否 | `0` |  | 当日已完成二级任务数。 |
| `completion_ratio` | decimal | 否 | `0` |  | 完成比例，范围 0-1。 |
| `color_level` | integer | 否 | `0` | INDEX | 学习打卡颜色等级，v0.1 使用 0-5。 |
| `created_at` | datetime | 否 | 当前时间 |  | 创建时间。 |
| `updated_at` | datetime | 否 | 当前时间 |  | 更新时间。 |

规则：

- 每个用户每天最多一条记录。
- 学习打卡不是用户手动点击生成，而是由当日二级任务完成比例派生。
- 无任务时 `total_subtask_count = 0`、`completed_subtask_count = 0`、`completion_ratio = 0`、`color_level = 0`。
- 二级任务状态变化时，应幂等更新当天记录，重复完成同一任务不能重复累计。

## content_json 结构约定

`ai_generated_contents.content_json` 保存结构化生成结果。v0.1 先以 JSON 契约稳定前后端，不强制拆独立表。

### quiz

```json
{
  "questions": [
    {
      "id": "q_...",
      "question_type": "single_choice",
      "question_text": "题干",
      "options": [
        {
          "id": "A",
          "text": "选项"
        }
      ],
      "correct_answer": "A",
      "explanation": "答案解析",
      "source_citation_ids": ["cit_..."],
      "sort_order": 1
    }
  ]
}
```

规则：

- `question_type` 支持 `single_choice`、`multiple_choice`、`true_false`、`short_answer`。
- 课程自测和任务测试题都可复用该结构，通过 `content_type` 区分场景。
- 每道题应尽量关联引用来源；不能生成伪引用。

### flashcard

```json
{
  "cards": [
    {
      "id": "card_...",
      "front": "卡片正面",
      "back": "卡片背面",
      "tags": ["概念"],
      "mastery_status": "unknown",
      "source_citation_ids": ["cit_..."],
      "sort_order": 1
    }
  ]
}
```

规则：

- `mastery_status` 支持 `unknown`、`not_mastered`、`mastered`。
- v0.1 不实现复杂间隔复习算法。

### mindmap

```json
{
  "root_node_id": "node_1",
  "nodes": [
    {
      "id": "node_1",
      "label": "节点名称",
      "summary": "节点说明",
      "level": 1,
      "source_citation_ids": ["cit_..."]
    }
  ],
  "edges": [
    {
      "from": "node_1",
      "to": "node_2",
      "relation": "child"
    }
  ]
}
```

规则：

- 节点必须有稳定 ID，便于前端展开收起。
- 边表示节点之间的父子或关联关系。

### outline

```json
{
  "sections": [
    {
      "id": "sec_...",
      "title": "章节标题",
      "summary": "重点说明",
      "review_suggestion": "复习建议",
      "source_citation_ids": ["cit_..."],
      "sort_order": 1
    }
  ]
}
```

### knowledge_list

```json
{
  "items": [
    {
      "id": "kp_...",
      "name": "知识点",
      "definition": "定义说明",
      "importance": "high",
      "related_section": "关联章节",
      "source_citation_ids": ["cit_..."],
      "sort_order": 1
    }
  ]
}
```

规则：

- `importance` v0.1 建议使用 `high`、`medium`、`low`，前端必须对未知值兜底。

## 其他技术候选表

以下表不是 PRD 第 13 章定义的核心数据对象。v0.1 可以先不建，只有当实现方式需要持久化对应技术状态时再补充设计和 migration。

| 候选表 | v0.1 处理方式 | 后续建表触发条件 |
| --- | --- | --- |
| `idempotency_records` | 可由服务层、请求日志或轻量存储实现，不作为核心业务表。 | 需要跨进程幂等、任务恢复或并发生成保障。 |
| `sessions` | 可使用 Bearer token 或等价 session 机制，不在业务数据模型中固定。 | 需要服务端会话管理、设备管理或强制下线。 |
| `material_parse_jobs` | v0.1 可先用 `course_materials.parse_status` 和 `parse_error` 表达解析状态。 | 需要独立解析队列、重试次数、任务锁或后台任务恢复。 |
| `generation_jobs` | v0.1 可先用 `messages.generation_status` 和 `ai_generated_contents.generation_status` 表达生成状态。 | 需要统一生成任务队列、排队状态、取消任务或异步任务恢复。 |

## 最小索引建议

| 场景 | 建议索引 |
| --- | --- |
| 当前用户课程列表 | `courses(user_id, status, updated_at)` |
| 课程资料列表 | `course_materials(course_id, folder_id, parse_status, created_at)` |
| 可检索资料范围 | `course_materials(course_id, parse_status, deleted_at)` |
| 资料切片检索过滤 | `material_chunks(course_id, material_id, chunk_index)` |
| 课程对话列表 | `conversations(course_id, status, updated_at)` |
| 对话消息列表 | `messages(conversation_id, created_at)` |
| 生成内容历史 | `ai_generated_contents(course_id, content_type, generation_status, created_at)` |
| 课程计划列表 | `study_plans(course_id, status, start_date, end_date)` |
| 首页今日待办 / 日历 | `study_tasks(course_id, task_date, status)`、`study_subtasks(course_id, status)` |
| 用户打卡日历 | `checkin_records(user_id, checkin_date)` |

索引可以在实际 migration 中按查询路径调整；新增或删除关键索引需要同步更新本文。

## 迁移和实现规则

- 首次落库时，以上表和字段作为 v0.1 baseline migration。
- 后续字段变化必须通过 Alembic migration 管理，并同步更新本文。
- 新增字段优先采用兼容路径：先加 nullable 字段，再回填，再收紧约束。
- 枚举新增必须同步前端兜底；枚举删除、重命名或语义变化视为破坏性变更。
- 外键删除行为由业务服务控制，默认不使用数据库级级联物理删除业务数据。
- 所有根据 ID 查询业务资源的接口，都必须同时校验当前 `user_id` 的访问权限。
