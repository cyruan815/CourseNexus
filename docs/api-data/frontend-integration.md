# Frontend Integration Guide v0.1

## 1. 阶段定位

基础设施阶段的前端只作为最小集成验证工作台，用来验证登录态、课程选择、资料上传、资料范围、问答和计划基础接口是否能被浏览器侧接入。

本阶段不追求完整产品体验、视觉完善度或复杂前端状态管理。所有核心能力必须能通过后端接口、后端测试或命令独立运行，不能依赖前端页面作为唯一验证方式。

## 2. 接入基线

- API 前缀固定为 `/api/v1`。
- 本地 Vite 开发服务器通过 `frontend/vite.config.ts` 将 `/api` 代理到 `http://127.0.0.1:8000`；浏览器侧仍使用相对路径请求后端，避免手动配置 `VITE_API_BASE_URL` 才能注册、登录或读取课程。
- JSON 字段统一使用 `snake_case`。
- 成功响应统一为 `{ "data": ..., "meta": ... }`，前端业务代码只消费 `data`。
- 错误响应统一为 `{ "error": { "code": "...", "message": "...", "details": ... }, "meta": ... }`。
- 前端只根据 HTTP status 和稳定 `error.code` 做逻辑判断，不解析中文 `message`。
- 登录态使用 Bearer token，请求头格式为 `Authorization: Bearer <access_token>`。
- POC 阶段前端 token 存储 key 为 `course_nexus_token`；收到 `UNAUTHORIZED` 时必须清理该 token 并回到登录态。
- 前端不得直接调用 OpenAI API；所有模型调用只通过后端接口完成。

## 3. 当前已落地接口

### 3.1 注册

`POST /api/v1/auth/register`

请求：

```json
{
  "username": "student@example.com",
  "password": "password123",
  "nickname": "学生 A"
}
```

响应 `data`：

```json
{
  "access_token": "token",
  "token_type": "bearer",
  "expires_at": "2026-07-10T12:00:00+00:00",
  "user": {
    "id": "usr_123",
    "username": "student@example.com",
    "nickname": "学生 A",
    "avatar_url": null,
    "status": "active",
    "created_at": "2026-07-09T12:00:00+00:00"
  }
}
```

### 3.2 登录

`POST /api/v1/auth/login`

请求：

```json
{
  "username": "student@example.com",
  "password": "password123"
}
```

响应 `data` 与注册接口一致。

### 3.3 当前用户

`GET /api/v1/auth/me`

要求：Bearer token。

响应 `data`：

```json
{
  "id": "usr_123",
  "username": "student@example.com",
  "nickname": "学生 A",
  "avatar_url": null,
  "status": "active",
  "created_at": "2026-07-09T12:00:00+00:00"
}
```

### 3.4 登出

`POST /api/v1/auth/logout`

要求：Bearer token。

响应 `data`：

```json
{
  "logged_out": true
}
```

### 3.5 课程列表

`GET /api/v1/courses`

要求：Bearer token。

响应 `data`：

```json
[
  {
    "id": "crs_123",
    "user_id": "usr_123",
    "name": "高等数学",
    "description": "微积分与线性代数复习",
    "teacher": "王老师",
    "term": "2025-2026-spring",
    "status": "active",
    "created_at": "2026-07-09T12:00:00+00:00",
    "updated_at": "2026-07-09T12:00:00+00:00",
    "deleted_at": null
  }
]
```

### 3.6 创建课程

`POST /api/v1/courses`

要求：Bearer token。

请求：

```json
{
  "name": "高等数学",
  "description": "微积分与线性代数复习",
  "teacher": "王老师",
  "term": "2025-2026-spring"
}
```

响应 `data`：`CourseRead`，字段同课程列表单项。

`term` 可省略或提交 `null`；前端创建表单默认显示“未选择”并提交 `null`，不得提供自由文本输入。

### 3.6.1 课程学期选项

`GET /api/v1/course-terms`

要求：Bearer token。

响应 `data`：

```json
[
  { "value": "2027-2028-autumn", "label": "2027-2028 秋季" },
  { "value": "2027-2028-spring", "label": "2027-2028 春季" },
  { "value": "2026-2027-autumn", "label": "2026-2027 秋季" },
  { "value": "2026-2027-spring", "label": "2026-2027 春季" },
  { "value": "2025-2026-autumn", "label": "2025-2026 秋季" },
  { "value": "2025-2026-spring", "label": "2025-2026 春季" },
  { "value": "2024-2025-autumn", "label": "2024-2025 秋季" },
  { "value": "2024-2025-spring", "label": "2024-2025 春季" }
]
```

`value` 是课程接口保存和筛选使用的稳定值，`label` 用于界面展示。选项增加时前端必须以接口结果为准。

### 3.7 课程详情

`GET /api/v1/courses/{course_id}`

要求：Bearer token。只能访问当前用户自己的课程。

响应 `data`：`CourseRead`。

### 3.8 更新课程

`PATCH /api/v1/courses/{course_id}`

要求：Bearer token。请求字段均可选。

请求：

```json
{
  "name": "高等数学复习",
  "description": "期末复习资料",
  "teacher": "王老师",
  "term": "2025-2026-spring"
}
```

响应 `data`：`CourseRead`。

`term` 可提交 `null` 以清除已选学期；提交非选项值返回 `422 VALIDATION_ERROR`。

### 3.9 删除课程

`DELETE /api/v1/courses/{course_id}`

要求：Bearer token。当前实现为软删除。

响应 `data`：`CourseRead`，其中 `status = "deleted"` 且 `deleted_at` 非空。

### 3.10 资料对象字段

资料相关接口返回的 `MaterialRead` 字段如下：

```json
{
  "id": "mat_123",
  "course_id": "crs_123",
  "user_id": "usr_123",
  "folder_id": null,
  "name": "notes.md",
  "material_type": "markdown",
  "source_type": "file",
  "file_url": "usr_123/crs_123/mat_123/source.md",
  "source_url": null,
  "file_size": 7,
  "mime_type": "text/markdown",
  "parse_status": "uploaded",
  "parse_error": null,
  "parse_quality": "unknown",
  "parse_diagnostics_json": null,
  "page_count": null,
  "created_at": "2026-07-09T12:00:00+00:00",
  "updated_at": "2026-07-09T12:00:00+00:00",
  "deleted_at": null
}
```

当前支持的文件资料类型：

- `.md`：`material_type = "markdown"`，`mime_type = "text/markdown"`。
- `.txt`：`material_type = "text"`，`mime_type = "text/plain"`。
- `.pdf`：`material_type = "pdf"`，`mime_type = "application/pdf"`。
- `.docx`：`material_type = "word"`，`mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"`。
- `.pptx`：`material_type = "ppt"`，`mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"`。
- `.png` / `.jpg` / `.jpeg`：`material_type = "image"`，`mime_type` 为对应图片类型。

`name` 是用户可见的原始上传文件名，可包含中文；`file_url` 是后端内部存储路径，文件名固定为 ASCII 的 `source.<ext>`，前端不得用 `file_url` 推导展示名。

当前上传大小上限由后端 `MAX_UPLOAD_FILE_SIZE_BYTES` 配置控制，默认 `52428800`，即 50 MiB。

`parse_status` 当前可能值：

| 状态 | 含义 |
| --- | --- |
| `uploaded` | 已创建资料记录，尚未解析。 |
| `parsing` | 正在同步解析。 |
| `parsed` | 已解析并写入 `MaterialChunk`。 |
| `parse_failed` | 解析失败，`parse_error` 保存稳定错误码。 |
| `deleted` | 已软删除，不进入列表和上下文。 |

`parse_quality` 当前可能值：

| 状态 | 含义 |
| --- | --- |
| `unknown` | 尚未解析、解析失败、历史数据或 parser 没有足够诊断信息。 |
| `complete` | 本轮成功，且 parser 未观察到失败页或 warning。 |
| `partial` | 存在可用 chunk，但 parser 检测到部分成功、失败页或 warning。 |

`parse_status = "parsed"` 只表示资料内容可消费，不等同于完整解析；完整性统一读取 `parse_quality` 和 `parse_diagnostics_json`。

### 3.10.1 资料一级文件夹

文件夹仅用于资料归类、排序和列表过滤，不能作为 Agent 资料范围。`MaterialScope` 只接受具体 `material_ids`。

- `GET /api/v1/courses/{course_id}/material-folders`：返回当前课程未删除的 `MaterialFolderRead[]`。
- `POST /api/v1/courses/{course_id}/material-folders`：创建文件夹，请求为 `{ "name": "第一周", "sort_order": 1 }`；`sort_order` 可省略。
- `PATCH /api/v1/material-folders/{folder_id}`：重命名或调整顺序，请求至少包含 `name` 或 `sort_order`。
- `DELETE /api/v1/material-folders/{folder_id}`：软删除文件夹及其中全部资料，并清理这些资料的 RAG 向量。前端需在二次确认后调用接口；成功后移除文件夹及其中资料并清理当前 `MaterialScope` 中对应 ID，失败时保留当前页面数据并展示后端错误。后端在 RAG 或数据库提交失败时回滚 SQLite，并用 SQLite chunk 快照补偿恢复已清理向量；补偿也失败时返回 `502 INDEXING_FAILED`，`details.rebuild_required = true`。
- `PATCH /api/v1/materials/{material_id}/folder`：请求 `{ "folder_id": "fld_123" }`；传 `null` 表示移动到未分类。

文件夹和资料必须属于当前用户的同一课程。文件夹列表按 `sort_order`、创建时间和 ID 排序。

### 3.11 课程资料列表

`GET /api/v1/courses/{course_id}/materials`

要求：Bearer token。只能列出当前用户拥有的课程资料；软删除资料不返回。

响应 `data`：`MaterialRead[]`。

### 3.12 文件资料上传

`POST /api/v1/courses/{course_id}/materials`

要求：Bearer token。请求格式为 `multipart/form-data`。

请求字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | File | 是 | 支持 `.md` / `.txt` / `.pdf` / `.docx` / `.pptx` / `.png` / `.jpg` / `.jpeg`。文本文件必须为 UTF-8。 |
| `folder_id` | string | 否 | 上传后所属一级文件夹；省略时进入未分类。 |

响应 `data`：`MaterialRead`，初始 `parse_status = "uploaded"`。

主要错误码：

| 错误码 | 场景 |
| --- | --- |
| `VALIDATION_ERROR` | 文件名为空、包含路径、路径穿越或保留设备名。 |
| `UNSUPPORTED_FILE_TYPE` | 扩展名不支持，或文本文件无法按 UTF-8 解码。 |
| `FILE_TOO_LARGE` | 文件大小超过 `MAX_UPLOAD_FILE_SIZE_BYTES`。 |
| `NOT_FOUND` | 课程不存在或不属于当前用户。 |

### 3.13 链接资料创建

`POST /api/v1/courses/{course_id}/material-links`

要求：Bearer token。

请求：

```json
{
  "name": "Course Site",
  "source_url": "https://example.com/course",
  "folder_id": "fld_123"
}
```

响应 `data`：`MaterialRead`，其中 `source_type = "url"`、`material_type = "link"`、`parse_status = "uploaded"`。

### 3.14 资料详情

`GET /api/v1/materials/{material_id}`

要求：Bearer token。只能访问当前用户自己的资料。

响应 `data`：`MaterialRead`。

### 3.14.1 重命名资料

`PATCH /api/v1/materials/{material_id}`

要求：Bearer token。只能重命名当前用户自己的未删除资料。

请求：

```json
{
  "name": "第一章 物理层.pdf"
}
```

响应 `data`：更新后的 `MaterialRead`。后端会去除名称首尾空格；空名称或超过 255 字符返回 `VALIDATION_ERROR`。

重命名只修改用户可见的 `name` 和 `updated_at`，不修改 `file_url`、`source_url`、解析状态、chunk 或向量索引，也不回写历史 `SourceCitation.material_name`。

### 3.15 资料删除

`DELETE /api/v1/materials/{material_id}`

要求：Bearer token。当前实现为软删除。

响应 `data`：`MaterialRead`，其中 `parse_status = "deleted"` 且 `deleted_at` 非空。

### 3.16 资料解析 / 解析重试

`POST /api/v1/materials/{material_id}/parse-retries`

要求：Bearer token。当前实现为同步解析本地 `.md`、`.txt`、`.pdf`、`.docx`、`.pptx` 和图片；后续支持后台任务时，响应语义需单独更新。

响应 `data`：`MaterialRead`。

成功时：

- `parse_status = "parsed"`。
- `parse_error = null`。
- `parse_quality` 为 `complete`、`partial` 或 `unknown`。
- `page_count` 和 `parse_diagnostics_json` 返回 parser 本轮诊断；非分页文本的 `page_count = null` 是正常结果。
- 后端已写入有序 `MaterialChunk`，供后续资料上下文、问答和计划基础能力使用。

失败时：

- HTTP 仍返回成功响应和 `MaterialRead`。
- `parse_status = "parse_failed"`。
- `parse_error` 保存稳定错误码，例如 `PARSE_FAILED` 或 `UNSUPPORTED_FILE_TYPE`。
- `parse_quality = "unknown"`、`page_count = null`、`parse_diagnostics_json = null`，不保留上一轮成功诊断。

前端最小工作台只需要展示 `uploaded`、`parsing`、`parsed`、`parse_failed`、未知状态兜底，以及在 `parse_failed` 时提供重试入口。

### 3.17 课程对话列表

`GET /api/v1/courses/{course_id}/conversations`

要求：Bearer token。只返回当前用户当前课程下 active、未删除对话。

响应 `data` 单项字段：

```json
{
  "id": "cnv_123",
  "user_id": "usr_123",
  "course_id": "crs_123",
  "title": "What is Alpha?",
  "source_page": "course_detail",
  "status": "active",
  "created_at": "2026-07-09T12:00:00+00:00",
  "updated_at": "2026-07-09T12:00:00+00:00",
  "deleted_at": null
}
```

### 3.18 对话消息列表

`GET /api/v1/conversations/{conversation_id}/messages`

要求：Bearer token。只能读取当前用户自己的对话。

响应 `data` 单项字段：

```json
{
  "id": "msg_123",
  "conversation_id": "cnv_123",
  "course_id": "crs_123",
  "role": "assistant",
  "content": "回答正文",
  "answer_type": "grounded",
  "generation_status": "success",
  "error_code": null,
  "material_scope_json": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "created_at": "2026-07-09T12:00:00+00:00"
}
```

### 3.19 课程问答

`POST /api/v1/courses/{course_id}/qa/questions`

要求：Bearer token。当前后端在无 `COURSE_QA_API_KEY` 时使用 deterministic mock provider；配置课程问答专用的 `COURSE_QA_API_KEY`、`COURSE_QA_BASE_URL` 和 `COURSE_QA_MODEL` 后，通过后端 `OpenAIModelProvider` 使用 OpenAI Python SDK 接口规范。该配置与 Embedding 及其他生成功能相互独立。

请求：

```json
{
  "conversation_id": null,
  "question": "What is Alpha?",
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "source_page": "course_detail"
}
```

响应 `data`：

```json
{
  "conversation_id": "cnv_123",
  "user_message_id": "msg_user",
  "assistant_message_id": "msg_assistant",
  "answer_text": "回答正文",
  "answer_type": "grounded",
  "source_citations": [
    {
      "material_id": "mat_123",
      "chunk_id": "chk_123",
      "material_name": "notes.md",
      "page": null,
      "page_index": 0,
      "hit_text": "Alpha"
    }
  ]
}
```

`answer_type` 规则：

- `grounded`：当前资料范围存在检索命中，回答基于检索到的真实 `MaterialChunk`。
- `no_source`：当前资料范围没有可用 parsed chunk，或存在 parsed chunk 但本次问题没有相关检索命中；`source_citations = []`，前端不得展示伪引用。

追问时传入同一课程下的 `conversation_id`；跨课程或跨用户复用会返回 `NOT_FOUND`。

### 3.20 生成内容对象字段

生成内容相关接口返回的 `GeneratedContentRead` 字段如下：

```json
{
  "id": "gen_123",
  "user_id": "usr_123",
  "course_id": "crs_123",
  "study_subtask_id": null,
  "source_message_id": null,
  "content_type": "outline",
  "title": "Outline",
  "content": "Alpha",
  "content_json": {
    "items": ["Alpha"]
  },
  "generation_status": "success",
  "material_scope_json": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "error_code": null,
  "source_citations": [
    {
      "id": "cit_123",
      "material_id": "mat_123",
      "chunk_id": "chk_123",
      "material_name": "notes.md",
      "page": null,
      "page_index": 0,
      "hit_text": "Alpha",
      "sort_order": 1
    }
  ],
  "created_at": "2026-07-09T12:00:00+00:00",
  "updated_at": "2026-07-09T12:00:00+00:00",
  "deleted_at": null
}
```

当前已注册的基础生成类型：

- `flashcard`
- `mindmap`
- `quiz`
- `outline`
- `knowledge_list`

G01已稳定五类入口共用的全材料、引用和失败契约；这些类型当前仍返回deterministic placeholder业务结构，直到G02-G06分别替换，不代表最终生成质量。

`source_citations`在生成POST、历史和详情中始终存在；无引用固定为`[]`。`page_index=0`且`page=null`表示来源没有可展示页码，前端显示“页码未知”，不得显示“第0页”。

### 3.21 生成内容列表

`GET /api/v1/courses/{course_id}/generated-contents`

要求：Bearer token。只返回当前用户当前课程下未删除生成内容。

响应 `data`：`GeneratedContentRead[]`。

### 3.22 生成内容详情

`GET /api/v1/generated-contents/{generated_content_id}`

要求：Bearer token。只能访问当前用户自己的生成内容。

响应 `data`：`GeneratedContentRead`。

### 3.23 统一生成入口

`POST /api/v1/courses/{course_id}/generations`

要求：Bearer token。当前实现通过 `generation/orchestrator` 统一解析资料上下文、调用注册 generator、保存 `AIGeneratedContent` 和真实 `SourceCitation`。

请求：

```json
{
  "content_type": "outline",
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "parameters": {}
}
```

响应 `data`：`GeneratedContentRead`。

主要错误码：

| 错误码 | 场景 |
| --- | --- |
| `VALIDATION_ERROR` | `content_type`未注册，或具体生成器参数非法；不创建历史记录。 |
| `NO_PARSED_MATERIAL` | 当前资料范围没有可用 parsed chunk。 |

模型、schema或材料覆盖失败会保存`generation_status="failed"`记录，`error_code`分别为`GENERATION_FAILED`、`GENERATION_SCHEMA_INVALID`或`MATERIAL_COVERAGE_INCOMPLETE`；失败记录的`content_json=null`且`source_citations=[]`。重复请求会创建不同ID，当前没有持久化幂等键或retry-by-id接口。

### 3.24 学习计划预览

`POST /api/v1/courses/{course_id}/study-plans/preview`

要求：Bearer token。当前实现为确定性基础规则，不调用模型，不代表最终 AI 计划算法。

请求：

```json
{
  "goal_text": "期末复习",
  "start_date": "2026-07-10",
  "end_date": "2026-07-12",
  "daily_available_minutes": 60,
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  }
}
```

响应 `data`：

```json
{
  "course_id": "crs_123",
  "title": "Linear Algebra 学习计划",
  "goal_text": "期末复习",
  "start_date": "2026-07-10",
  "end_date": "2026-07-12",
  "daily_available_minutes": 60,
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "tasks": [
    {
      "title": "第 1 天学习任务",
      "task_date": "2026-07-10",
      "sort_order": 1,
      "subtasks": [
        {
          "title": "学习: Intro",
          "subtask_type": "learn",
          "description": "Alpha",
          "related_material_ids": ["mat_123"],
          "sort_order": 1
        }
      ]
    }
  ]
}
```

主要错误码：

| 错误码 | 场景 |
| --- | --- |
| `NO_PARSED_MATERIAL` | 当前资料范围没有可用 parsed chunk。 |
| `NOT_FOUND` | 课程或显式资料范围不属于当前用户。 |

### 3.25 学习计划保存

`POST /api/v1/courses/{course_id}/study-plans`

要求：Bearer token。请求体同预览接口。保存时只写 `StudyPlan`、`StudyTask`、`StudySubTask`，不提前生成今日讲义或任务测试题内容。

响应 `data`：

```json
{
  "plan": {
    "id": "sp_123",
    "course_id": "crs_123",
    "status": "active"
  },
  "tasks": [],
  "subtasks": []
}
```

实际响应字段以 `StudyPlanRead`、`StudyTaskRead`、`StudySubTaskRead` 为准，包含创建时间、更新时间、排序和状态字段。

### 3.26 课程学习计划列表

`GET /api/v1/courses/{course_id}/study-plans`

要求：Bearer token。只返回当前用户当前课程下未删除学习计划。

响应 `data`：`StudyPlanRead[]`。

### 3.27 学习计划详情

`GET /api/v1/study-plans/{plan_id}`

要求：Bearer token。只能读取当前用户自己的计划。

响应 `data`：与学习计划保存接口一致，包含 `plan`、`tasks`、`subtasks`。

## 4. 待后续任务落地的接口入口

以下接口是基础设施计划中的前端接入入口。后端实现完成后，必须在本文件补充请求体、响应 `data`、错误码和前端展示兜底。

| 能力 | 接口入口 |
| --- | --- |
| 今日待办聚合 | 待后续计划执行阶段定义 |
| 首页大日历聚合 | 待后续计划执行阶段定义 |

## 5. 前端最小工作台验收口径

- 前端页面只需要覆盖基础集成路径：登录、课程列表、课程详情选择、资料上传、资料范围选择、问答提交和引用展示。
- 每个核心能力必须先有后端 service/router 测试，再用前端测试验证接入边界。
- 前端组件测试优先验证请求参数、状态兜底、错误码处理和路由跳转，不以视觉完整度作为基础设施阶段验收重点。
- 若前端展示与后端契约不一致，以本分区和后端 schema 为准，并优先修正文档或接口契约。
