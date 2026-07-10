# Frontend Integration Guide v0.1

## 1. 阶段定位

基础设施阶段的前端只作为最小集成验证工作台，用来验证登录态、课程选择、资料上传、资料范围、问答和计划基础接口是否能被浏览器侧接入。

本阶段不追求完整产品体验、视觉完善度或复杂前端状态管理。所有核心能力必须能通过后端接口、后端测试或命令独立运行，不能依赖前端页面作为唯一验证方式。

## 2. 接入基线

- API 前缀固定为 `/api/v1`。
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
    "term": "2026 Spring",
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
  "term": "2026 Spring"
}
```

响应 `data`：`CourseRead`，字段同课程列表单项。

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
  "term": "2026 Spring"
}
```

响应 `data`：`CourseRead`。

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
  "source_url": "https://example.com/course"
}
```

响应 `data`：`MaterialRead`，其中 `source_type = "url"`、`material_type = "link"`、`parse_status = "uploaded"`。

### 3.14 资料详情

`GET /api/v1/materials/{material_id}`

要求：Bearer token。只能访问当前用户自己的资料。

响应 `data`：`MaterialRead`。

### 3.15 资料删除

`DELETE /api/v1/materials/{material_id}`

要求：Bearer token。当前实现为软删除。

响应 `data`：`MaterialRead`，其中 `parse_status = "deleted"` 且 `deleted_at` 非空。

### 3.16 资料解析 / 解析重试

`POST /api/v1/materials/{material_id}/parse-retries`

要求：Bearer token。当前实现为同步解析本地 `.md` / `.txt` 文件；后续支持后台任务时，响应语义需单独更新。

响应 `data`：`MaterialRead`。

成功时：

- `parse_status = "parsed"`。
- `parse_error = null`。
- 后端已写入有序 `MaterialChunk`，供后续资料上下文、问答和计划基础能力使用。

失败时：

- HTTP 仍返回成功响应和 `MaterialRead`。
- `parse_status = "parse_failed"`。
- `parse_error` 保存稳定错误码，例如 `PARSE_FAILED` 或 `UNSUPPORTED_FILE_TYPE`。

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
    "folder_ids": [],
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
    "folder_ids": [],
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
    "folder_ids": [],
    "material_ids": []
  },
  "error_code": null,
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

这些类型当前只是后续功能接入点，返回 deterministic placeholder 结构，不代表最终生成质量或前端渲染协议。

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
    "folder_ids": [],
    "material_ids": []
  },
  "parameters": {}
}
```

响应 `data`：`GeneratedContentRead`。

主要错误码：

| 错误码 | 场景 |
| --- | --- |
| `VALIDATION_ERROR` | `content_type` 未注册。 |
| `NO_PARSED_MATERIAL` | 当前资料范围没有可用 parsed chunk。 |

生成器失败时，当前后端会保存 `generation_status = "failed"` 且 `error_code = "GENERATION_FAILED"` 的生成内容记录。

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
    "folder_ids": [],
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
    "folder_ids": [],
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
