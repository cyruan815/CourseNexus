# Frontend Integration Guide v0.1

## 1. 阶段定位

基础设施阶段的前端只作为最小集成验证工作台，用来验证登录态、课程选择、资料上传、资料范围、问答和计划基础接口是否能被浏览器侧接入。

本阶段不追求完整产品体验、视觉完善度或复杂前端状态管理。所有核心能力必须能通过后端接口、后端测试或命令独立运行，不能依赖前端页面作为唯一验证方式。

## 2. 接入基线

- API 前缀固定为 `/api/v1`。
- 默认本地配置使用 `VITE_API_BASE_URL=http://localhost:8000`，浏览器直接请求后端；后端通过 `CORS_ALLOWED_ORIGINS`（默认 `http://localhost:5173`）响应跨域预检，并允许 `Authorization`、`Content-Type`、`Idempotency-Key` 和 `X-Request-ID` 请求头。多个允许来源使用英文逗号分隔。
- `frontend/vite.config.ts` 保留 `/api` 到 `http://127.0.0.1:8000` 的开发代理；只有将 `VITE_API_BASE_URL` 留空时，浏览器才使用该同源代理。生产环境必须由后端 CORS 配置或反向代理明确允许前端来源，不能依赖 Vite 代理。
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
    "deleted_at": null,
    "material_count": 3,
    "today_task_status": "has_task_today"
  }
]
```

课程列表单项使用 `CourseListItemRead`。其中 `material_count` 始终是非负整数，统计课程下当前未删除的资料；尚未解析的资料同样计入。`today_task_status` 始终存在，后端按 `Asia/Shanghai` 的自然日计算：

| 值 | 前端展示 | 判定 |
| --- | --- | --- |
| `no_study_plan` | 无学习计划 | 课程下没有未删除的学习计划。 |
| `no_task_today` | 今日无任务 | 存在未删除的学习计划，但今天没有一级任务。 |
| `has_task_today` | 今日有任务 | 今天至少存在一个属于未删除学习计划的一级任务。 |

首页课程卡片显示 `material_count` 为 `资料 N 份`。该摘要只在课程列表中返回；前端不得通过逐课程调用学习计划详情、按本地日期或按任务列表自行聚合。课程创建、详情、更新和删除仍返回不含摘要字段的 `CourseRead`。接口上线前可保留同步占位或在测试中使用本地 mock 字段。

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

响应 `data`：`CourseRead`，不包含课程列表专用的 `material_count` 与 `today_task_status`。

`name` 最多 20 个字符，`description` 最多 50 个字符，`teacher` 最多 10 个字符；超出任一上限返回 `422 VALIDATION_ERROR`。`term` 可省略或提交 `null`；前端创建表单默认显示“未选择”并提交 `null`，不得提供自由文本输入。

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

响应 `data`：基础 `CourseRead` 字段，不包含课程列表接口专用的 `material_count` 和 `today_task_status` 摘要字段。

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

响应 `data`：基础 `CourseRead` 字段，不包含课程列表接口专用的 `material_count` 和 `today_task_status` 摘要字段。

`name` 最多 20 个字符，`description` 最多 50 个字符，`teacher` 最多 10 个字符；超出任一上限返回 `422 VALIDATION_ERROR`。`term` 可提交 `null` 以清除已选学期；提交非选项值返回 `422 VALIDATION_ERROR`。

### 3.9 删除课程

`DELETE /api/v1/courses/{course_id}`

要求：Bearer token。当前实现为软删除。

响应 `data`：基础 `CourseRead` 字段，其中 `status = "deleted"` 且 `deleted_at` 非空；不包含课程列表接口专用的 `material_count` 和 `today_task_status` 摘要字段。

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
| `deleted` | 仅用于删除接口成功响应的最终快照；数据库中的资料记录已经物理删除。 |

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
- `DELETE /api/v1/material-folders/{folder_id}`：不可恢复地物理删除文件夹、其中全部资料记录、SQLite chunk、RAG 向量和原始上传文件。前端需在二次确认后调用接口；成功后移除文件夹及其中资料并清理当前 `MaterialScope` 中对应 ID，失败时保留当前页面数据并展示后端错误。历史问答和生成内容保留，其引用退化为不带 `material_id` / `chunk_id` 的资料名、页码和命中文本快照。
- `PATCH /api/v1/materials/{material_id}/folder`：请求 `{ "folder_id": "fld_123" }`；传 `null` 表示移动到未分类。

文件夹和资料必须属于当前用户的同一课程。文件夹列表按 `sort_order`、创建时间和 ID 排序。

### 3.11 课程资料列表

`GET /api/v1/courses/{course_id}/materials`

要求：Bearer token。只能列出当前用户拥有且仍存在的课程资料；已物理删除资料不返回。

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

### 3.14.2 PDF 资料原文预览

`GET /api/v1/materials/{material_id}/content`

要求：Bearer token。只能读取当前用户自己的本地 PDF 资料。成功时直接返回 `application/pdf` 文件流，`Content-Disposition` 为 `inline`，不包统一 `{data, meta}` envelope，并通过 `Cache-Control: private, no-store` 避免缓存私有资料。

当前非 PDF 或链接资料返回 `415 PREVIEW_UNSUPPORTED`；原文文件丢失或存储路径不可用返回 `404 PREVIEW_FILE_UNAVAILABLE`；资料不存在或不属于当前用户统一返回 `404 NOT_FOUND`。前端应使用带鉴权头的 `fetch` 读取 Blob，再用临时 object URL 在页面弹窗内展示；不得直接访问 `file_url`。

### 3.15 资料删除

`DELETE /api/v1/materials/{material_id}`

要求：Bearer token。当前实现为不可恢复的物理删除。

响应 `data`：删除前资料的最终 `MaterialRead` 快照，其中 `parse_status = "deleted"` 且 `deleted_at` 非空；响应返回后对应数据库记录、chunk、RAG 向量和原始上传文件均已删除。

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
  "source_citations": [
    {
      "material_id": "mat_123",
      "chunk_id": "chk_123",
      "material_name": "notes.md",
      "page": null,
      "page_index": 0,
      "hit_text": "Alpha"
    }
  ],
  "created_at": "2026-07-09T12:00:00+00:00"
}
```

用户消息和无来源回答的 `source_citations` 为 `[]`。历史回答与新回答使用同一引用快照契约，前端刷新后不得丢失引用。

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
  "answer_text": "回答正文 [[cite:1]]",
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
  ],
  "used_material_ids": ["mat_123"]
}
```

`answer_type` 规则：

- `grounded`：当前资料范围存在检索命中，回答基于检索到的真实 `MaterialChunk`。
- `no_source`：当前资料范围没有可用 parsed chunk，或存在 parsed chunk 但本次问题没有相关检索命中；`source_citations = []`，前端不得展示伪引用。

新回答的引用必须包含真实 `material_id` 和 `chunk_id`。来源资料后来被物理删除时，历史回答仍保留引用快照，但这两个字段返回 `null`。

`answer_text` 使用内部行内标记 `[[cite:N]]` 将论述绑定到 `source_citations[N-1]`。标记只允许由后端根据本次 Top-K 命中的真实 chunk 生成并重新编号；模型返回越界序号、未检索 chunk 或其他伪造标记时，后端必须删除该标记且不得保存引用。前端应将合法标记渲染为可交互角标，不直接向用户展示原始标记。

追问时传入同一课程下的 `conversation_id`；跨课程或跨用户复用会返回 `NOT_FOUND`。

### 3.19.1 执行页任务级问答

`POST /api/v1/study-subtasks/{subtask_id}/qa/questions`

要求：Bearer token。该接口用于计划执行页围绕当前二级任务提问，前端不提交 `material_scope`。后端会从当前二级任务的 `related_material_ids_json` 派生资料范围，并只在该范围内检索引用。

请求：

```json
{
  "conversation_id": null,
  "question": "这一节的关键公式是什么？"
}
```

响应 `data` 与课程问答一致：

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

前端规则：

- 新建执行页对话时传 `conversation_id = null`；追问时传上一次响应的 `conversation_id`。
- 执行页不要复用课程详情页的 conversation；后端会拒绝 `source_page = "course_detail"` 的对话。
- `answer_type = "no_source"` 时展示无资料或无命中兜底，`source_citations` 和 `used_material_ids` 会为空数组。
- 该接口不会改变二级任务完成状态，也不会触发打卡。 生成内容对象字段

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

G01-G06 已完成五类独立 POC 生成：后端按稳定顺序合并所选 parsed 资料、检查总上下文上限，并对对应类型调用一次结构化模型。

`source_citations` 在生成 POST、历史和详情中始终存在。Quiz、Flashcard、Mindmap、Outline、Knowledge List 固定返回 `[]`；Course QA 和 task_test 等保留引用能力的内容继续通过 API 返回真实引用，新生成 handout 固定返回空数组并把来源说明写在 Markdown 正文顶部。生成内容详情页不展示引用面板；task_test 引用用于内部追溯和导出。

### 3.21 生成内容列表

`GET /api/v1/courses/{course_id}/generated-contents`

要求：Bearer token。只返回当前用户当前课程下未删除生成内容。

响应 `data`：`GeneratedContentRead[]`。

### 3.22 生成内容详情

`GET /api/v1/generated-contents/{generated_content_id}`

要求：Bearer token。只能访问当前用户自己的生成内容。

响应 `data`：`GeneratedContentRead`。

### 3.22.1 重命名与删除生成内容

`PATCH /api/v1/generated-contents/{generated_content_id}`

要求：Bearer token。只能修改当前用户自己的未删除生成内容。请求体为 `{"title":"新的名称"}`；标题去除首尾空白后长度为 1-255，响应 `data` 为更新后的 `GeneratedContentRead`。重命名只修改 `title` 和 `updated_at`，不改变正文、结构化结果、生成状态、资料范围或引用快照。

`DELETE /api/v1/generated-contents/{generated_content_id}`

要求：Bearer token。只能删除当前用户自己的未删除生成内容。删除采用软删除，写入 `deleted_at` 和 `updated_at`；响应 `data` 为删除后的 `GeneratedContentRead`。删除后该记录不再出现在课程生成内容列表，详情接口返回 `404 NOT_FOUND`，数据库正文与历史引用快照保留。

### 3.22.2 替换 Flashcard 完整牌组

`PATCH /api/v1/generated-contents/{generated_content_id}/flashcards`

要求：Bearer token。只能修改当前用户自己的 `content_type="flashcard"` 记录。该接口执行完整牌组替换，不是单卡增量更新；前端必须提交后端已保存的完整牌组，不能提交打乱顺序或“只练未掌握”形成的当前练习子集。

请求：

```json
{
  "cards": [
    {
      "front": "问题",
      "back": "答案",
      "tags": ["概念"],
      "explanation": "补充解释"
    }
  ]
}
```

`cards` 必须包含 1-100 张卡片；正面按去除首尾空白、合并连续空白并忽略大小写后不可重复。保存时后端重新生成连续 `card_001...`、`sort_order` 和 `mastery_status="unknown"`，更新生成内容的 `updated_at`。响应 `data` 为更新后的 `GeneratedContentRead`。

主要错误码：

| 错误码 | 场景 |
| --- | --- |
| `VALIDATION_ERROR` | 牌组为空、超过 100 张、正面重复或单卡字段不合法。 |
| `NOT_FOUND` | 记录不存在、已删除或不属于当前用户。 |
| `INVALID_GENERATED_CONTENT_TYPE` | 目标记录不是 Flashcard。 |

翻卡、打乱、答对 / 答错和错卡重练仍是页面内存状态；只有添加和删除卡片会调用本接口持久化。保存失败时前端保留当前完整牌组并显示后端错误。

### 3.23 统一生成入口

`POST /api/v1/courses/{course_id}/generations`

要求：Bearer token。五类独立 POC 生成通过 `generation/orchestrator` 构造完整资料上下文、调用注册 generator 一次，并只保存 `AIGeneratedContent`，不创建 `SourceCitation`。

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
| `MATERIAL_CONTEXT_TOO_LARGE` | 完整选定材料超过总上下文上限；不调用模型且不创建历史记录。 |

模型、最终 schema 或 Markmap 预处理失败会保存 `generation_status="failed"` 记录，`error_code` 为 `GENERATION_FAILED` 或 `GENERATION_SCHEMA_INVALID`；失败记录的 `content_json=null` 且 `source_citations=[]`。重复请求会创建不同 ID，当前没有持久化幂等键或 retry-by-id 接口。

五类结果均使用稳定业务 ID 和连续 `sort_order`，业务 JSON 不包含 `source_chunk_ids` 或 `source_citation_ids`。Quiz 当前只生成 A-D 四选一单选题；新生成 Quiz 每个选项都有 `explanation`，错误选项解析只说明该选项自身错误的具体知识逻辑，不透露正确答案或正确结论；历史 Quiz 缺少逐项解析时前端不会编造错误原因。Flashcard 的 `mastery_status="unknown"` 只是初始展示值，当前没有掌握度写接口。

### 3.23.1 任务内容生成

`POST /api/v1/study-subtasks/{subtask_id}/handouts` 为 `learn` / `review` 二级任务生成任务讲义；`POST /api/v1/study-subtasks/{subtask_id}/task-tests` 为 `quiz` / `test` 二级任务生成任务测试题。两个接口都要求 Bearer token，成功响应 `data` 为 `GeneratedContentRead`，失败响应使用统一 error envelope。

讲义请求：

```json
{
  "force_regenerate": false,
  "parameters": {
    "language": "zh-CN",
    "detail_level": "standard"
  }
}
```

任务测试题请求：

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

默认重复请求会复用当前二级任务最近一次成功内容，不重新调用模型；`force_regenerate=true` 才会生成新内容。failed 记录不阻止重试，也不会被 execution-context 返回为内容 ID。

`task_test` 的 `question_count` 是成功内容硬约束：`content_json.questions.length` 必须严格等于请求值，题型必须来自 `question_types` 白名单，题目 `id` / `sort_order` 必须连续且唯一，选择题 options 和答案必须自洽，重复或高度相似题干会被拒绝。后端会汇总当前二级任务全部材料批次后只生成一套固定题量测试题，不按 batch 拼接多套题；如果模型输出无法满足约束，返回 `GENERATION_SCHEMA_INVALID` 并保存 failed 记录，不返回部分题目。

主要错误码：`STATE_CONFLICT` 表示二级任务类型不允许生成该内容；`NO_PARSED_MATERIAL` 表示当前二级任务没有可用解析上下文；`MATERIAL_COVERAGE_INCOMPLETE` 表示关联资料覆盖不完整；`GENERATION_SCHEMA_INVALID` 表示模型输出结构、测试题硬约束或引用不符合契约；`GENERATION_FAILED` 表示模型调用或未知生成失败。

### 3.23.2 任务测试题 Markdown 导出

`GET /api/v1/generated-contents/{generated_content_id}/exports/markdown` 导出已成功生成的 `task_test` Markdown 文件。接口要求 Bearer token，成功时直接返回 `text/markdown; charset=utf-8` 文件流，`Content-Disposition` 文件名为 `task-test-{generated_content_id}.md`，不包统一 `{data, meta}` envelope。

前端调用前应先通过 execution-context 获取 `task_test_content_id`，或通过 `GET /api/v1/generated-contents/{generated_content_id}` 确认内容为当前用户可访问的成功 `task_test`。错误响应仍使用统一 error envelope：`EXPORT_UNSUPPORTED_CONTENT_TYPE` 表示不是任务测试题；`EXPORT_CONTENT_NOT_READY` 表示生成未成功；`EXPORT_CONTENT_INVALID` 表示历史内容结构畸形；`NOT_FOUND` 表示内容不存在或不属于当前用户。


### 3.23.3 任务讲义 PDF 导出

`GET /api/v1/generated-contents/{generated_content_id}/exports/pdf` 导出已成功生成的 `handout` PDF 文件。接口要求 Bearer token，成功时直接返回 `application/pdf` 文件流，`Content-Disposition` 文件名为 `handout-{generated_content_id}.pdf`，不包统一 `{data, meta}` envelope。

前端调用前应先通过 execution-context 获取 `handout_content_id`，或通过 `GET /api/v1/generated-contents/{generated_content_id}` 确认内容为当前用户可访问的成功 `handout`。轻量阶段测试题不走 PDF；`task_test` 调用该接口会返回 `EXPORT_UNSUPPORTED_CONTENT_TYPE`。`EXPORT_CONTENT_NOT_READY` 表示生成未成功；`EXPORT_CONTENT_INVALID` 表示历史讲义结构畸形；`EXPORT_FAILED` 表示 PDF 渲染失败。后端 PDF renderer 会在导出用临时 HTML 中注入本地 KaTeX，对 `$...$` / `$$...$$` 公式完成打印前排版；这不等同于前端详情页自动具备数学渲染能力。

### 3.23.3 学习计划自然语言配置回填

`POST /api/v1/courses/{course_id}/study-plan-config-parses`

要求：Bearer token。接口不写数据库，只把 `goal_text` 和 `material_scope` 回填为配置确认页可用字段。

响应契约要点：

- 后端保留请求原始 `goal_text` 和 `material_scope`，模型只负责抽取日期、每日时间、学习方式和隐藏策略偏好。
- `preference` 为 `fast_track`、`balanced`、`mastery`、`sprint` 或 `null`；新向导进入 preview 前必须提交用户确认后的非空学习方式。
- `preference_overrides` 可包含 `content_depth`、`example_intensity`、`assessment_intensity`、`review_intensity`，用于后续策略追踪，不作为当前主控件。
- `recommended_daily_minutes` 固定由 preview 估算，配置回填阶段不猜测；没有每日时间时 `daily_available_minutes=null`、`daily_minutes_source=null`。
- `unresolved_fields` 只包含阻塞补充的用户配置字段，不包含 `recommended_daily_minutes`、`coverage`、`capacity` 等系统字段。
- `needs_confirmation_fields` 用于提示确认但不一定阻塞；当前至少包含 `preference`。
### 3.24 学前诊断问题

`POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions`

要求：Bearer token。后端根据 `goal_text`、确认后的学习设置和当前 `material_scope` 的 parsed 资料生成学前诊断问题；接口不写数据库，不做前端向导状态保存。

请求：

```json
{
  "goal_text": "我想三天深度掌握物理层",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_123"]
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

响应 `data` 固定包含 5 个问题：3 个 required `topic_mastery`、1 个 required `weak_area`、1 个 optional `diagnostic_note`。

```json
{
  "question_version": "study_plan_diagnostic_v2",
  "questions": [
    {
      "question_id": "topic_mastery_topic_xxx",
      "question_type": "topic_mastery",
      "question_text": "你对「Nyquist / Shannon 公式」了解多少？",
      "sort_order": 1,
      "required": true,
      "topic_id": "topic_xxx",
      "topic_title": "Nyquist / Shannon 公式",
      "options": [
        { "value": "none", "label": "完全不了解" },
        { "value": "heard", "label": "听说过，但不清楚" },
        { "value": "some", "label": "了解一些" },
        { "value": "familiar", "label": "比较熟悉" }
      ],
      "placeholder": null
    },
    {
      "question_id": "topic_mastery_topic_yyy",
      "question_type": "topic_mastery",
      "question_text": "你对「编码与调制」了解多少？",
      "sort_order": 2,
      "required": true,
      "topic_id": "topic_yyy",
      "topic_title": "编码与调制",
      "options": [
        { "value": "none", "label": "完全不了解" },
        { "value": "heard", "label": "听说过，但不清楚" },
        { "value": "some", "label": "了解一些" },
        { "value": "familiar", "label": "比较熟悉" }
      ],
      "placeholder": null
    },
    {
      "question_id": "topic_mastery_topic_zzz",
      "question_type": "topic_mastery",
      "question_text": "你对「传输介质」了解多少？",
      "sort_order": 3,
      "required": true,
      "topic_id": "topic_zzz",
      "topic_title": "传输介质",
      "options": [
        { "value": "none", "label": "完全不了解" },
        { "value": "heard", "label": "听说过，但不清楚" },
        { "value": "some", "label": "了解一些" },
        { "value": "familiar", "label": "比较熟悉" }
      ],
      "placeholder": null
    },
    {
      "question_id": "weak_area",
      "question_type": "weak_area",
      "question_text": "你最担心哪类内容？",
      "sort_order": 4,
      "required": true,
      "topic_id": null,
      "topic_title": null,
      "options": [
        { "value": "concept", "label": "概念理解" },
        { "value": "calculation", "label": "计算推导" },
        { "value": "application", "label": "做题应用" },
        { "value": "memorization", "label": "记忆重点" },
        { "value": "other", "label": "其他" }
      ],
      "placeholder": null
    },
    {
      "question_id": "diagnostic_note",
      "question_type": "diagnostic_note",
      "question_text": "还有什么想特别补的地方？",
      "sort_order": 5,
      "required": false,
      "topic_id": null,
      "topic_title": null,
      "options": [],
      "placeholder": "可选填写"
    }
  ],
  "generation_metadata": {
    "diagnostic_questions": {
      "source": "model",
      "fallback_reason": null,
      "model_topic_count": 3
    }
  }
}
```

规则：

- `topic_mastery` 问题数量固定为 3 个，来自当前资料范围。
- 模型失败、输出不足、重复或无法映射到资料时，后端使用资料内容 fallback 补足 3 题，并在 `generation_metadata.diagnostic_questions` 记录原因。
- 问题只表达当前掌握程度、薄弱方向和可选补充，不包含学习偏好、学习方式、讲课风格或资料范围问题。
- 当前资料范围没有 parsed chunk 时返回 `NO_PARSED_MATERIAL`。

### 3.25 学前诊断 Profile

`POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles`

要求：Bearer token。前端提交 exactly 3 个诊断答案，后端归纳成后续 preview 可携带的 `diagnostic_profile`。

请求：

```json
{
  "question_version": "study_plan_diagnostic_v2",
  "topic_mastery": [
    {
      "topic_id": "topic_xxx",
      "topic_title": "Nyquist / Shannon 公式",
      "mastery_level": "none"
    },
    {
      "topic_id": "topic_yyy",
      "topic_title": "编码与调制",
      "mastery_level": "heard"
    },
    {
      "topic_id": "topic_zzz",
      "topic_title": "传输介质",
      "mastery_level": "some"
    }
  ],
  "weak_area": "calculation",
  "diagnostic_note": "希望多讲公式怎么用",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_123"]
  }
}
```

响应 `data`：

```json
{
  "question_version": "study_plan_diagnostic_v2",
  "prior_knowledge_level": "little",
  "foundation_needed": true,
  "weak_topics": ["topic_xxx", "topic_yyy"],
  "weak_area": "calculation",
  "explanation_style": "step_by_step",
  "diagnostic_note": "希望多讲公式怎么用"
}
```

归纳规则：

- `topic_mastery` 必须 exactly 3 个，且 `topic_id` 不得重复。
- `mastery_level` 支持 `none`、`heard`、`some`、`familiar`。
- `weak_area` 支持 `concept`、`calculation`、`application`、`memorization`、`other`。
- `none` / `heard` 计为弱掌握；弱掌握超过一半时 `foundation_needed = true`。
- `weak_topics` 包含弱掌握 topic 的 `topic_id`。
- `explanation_style` 是后端从 `weak_area` 派生的内部兼容字段，不是前端讲课风格选择。
- `DIAGNOSTIC_STALE` 表示 `question_version` 或 topic 不再匹配当前资料范围；前端应回到诊断步骤重新获取问题和作答。

生成出的 profile 可原样放入 `POST /api/v1/courses/{course_id}/study-plans/preview` 请求。Preview 会用它影响 planner：`foundation_needed=true` 时前置补基础，`weak_topics` 会更靠前更细，`weak_area` 会强化概念、计算、应用或记忆方向；`explanation_style` 仅作为后端兼容字段进入 prompt。

```json
{
  "goal_text": "两天复习物理层核心内容",
  "start_date": "2026-07-12",
  "duration_days": 1,
  "daily_available_minutes": 60,
  "preference": "balanced",
  "diagnostic_profile": {
    "question_version": "study_plan_diagnostic_v2",
    "prior_knowledge_level": "little",
    "foundation_needed": true,
    "weak_topics": ["topic_xxx"],
    "weak_area": "calculation",
    "explanation_style": "step_by_step"
  },
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_123"]
  }
}
```

### 3.26 学习计划预览

`POST /api/v1/courses/{course_id}/study-plans/preview`

要求：Bearer token。后端基于当前资料范围和可选 `diagnostic_profile` 生成 preview；请求允许省略 `daily_available_minutes`，后端会在资料 map 后计算新的 `recommended_daily_minutes` 和最终采用的 `daily_available_minutes`。Capacity 在 planner reduce 后按最终任务树重新统计。

请求（未指定每日时间时）：

```json
{
  "goal_text": "期末复习",
  "start_date": "2026-07-10",
  "duration_days": 1,
  "preference": "sprint",
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  }
}
```

请求（前端手动修改每日时间时）：

```json
{
  "goal_text": "期末复习",
  "start_date": "2026-07-10",
  "duration_days": 1,
  "daily_available_minutes": 75,
  "daily_minutes_source": "user_modified",
  "preference": "sprint",
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  }
}
```

规则：

- `recommended_daily_minutes` 继续按 map 阶段资料规模估算：`max(30, ceil(mapped_estimated_total_minutes / duration_days))`。
- 未传 `daily_available_minutes` 时，`daily_available_minutes = recommended_daily_minutes`，`daily_minutes_source = "system_estimated"`。
- 传入 `daily_available_minutes` 时，后端保留该最终采用值；若 `daily_minutes_source = "user_modified"`，capacity 的 `available_total_minutes` 使用前端传入值计算。
- `capacity.estimated_total_minutes = sum(tasks[].subtasks[].estimated_minutes)`，即按最终 preview 任务统计，而不是 map 阶段材料单元估算。
- 当 `estimated_total_minutes > available_total_minutes` 时，`capacity.feasibility_status = "over_capacity"` 且 `capacity.warnings` 包含 `PLAN_OVER_CAPACITY`；前端应展示 warning 并引导用户增加每日时间、增加天数或降低学习强度。
- 接近容量时返回 `feasibility_status = "tight"`。
- 旧客户端继续可以传 `daily_available_minutes`；低于 30 分钟的请求会被校验拒绝。
- `preference` 请求和响应始终使用英文枚举：`fast_track`、`balanced`、`mastery`、`sprint`；前端可展示中文“快速通关 / 均衡学习 / 深入掌握 / 冲刺强化”，但不得把中文值写入 API。
- 后端会在 `generation_metadata.planner_strategy` 中返回派生后的 `content_depth`、`example_intensity`、`assessment_intensity`、`review_intensity`，并合并诊断得出的 `foundation_required`、`weak_topics`、`weak_area` 和 `explanation_style`。

响应 `data`：

```json
{
  "course_id": "crs_123",
  "title": "Linear Algebra 学习计划",
  "goal_text": "期末复习",
  "start_date": "2026-07-10",
  "end_date": "2026-07-10",
  "duration_days": 1,
  "daily_available_minutes": 60,
  "recommended_daily_minutes": 60,
  "daily_minutes_source": "system_estimated",
  "preference": "sprint",
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "capacity": {
    "estimated_total_minutes": 60,
    "available_total_minutes": 60,
    "feasibility_status": "tight",
    "warnings": []
  },
  "generation_metadata": {
    "schema_version": 1,
    "model_provider": "openai-compatible",
    "generated_at": "2026-07-12T10:00:00+08:00",
    "planner_strategy": {
      "preference": "sprint",
      "content_depth": "focused",
      "example_intensity": "standard",
      "assessment_intensity": "high",
      "review_intensity": "high",
      "foundation_required": false,
      "weak_topics": [],
      "weak_area": "other",
      "explanation_style": "plain_language"
    }
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
          "estimated_minutes": 60,
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
| `VALIDATION_ERROR` | 日期范围、资料范围或每日学习时间不合法，例如低于 30 分钟。 |

### 3.27 学习计划保存

`POST /api/v1/courses/{course_id}/study-plans`

要求：Bearer token。新向导保存时必须提交 `client_flow = "wizard_v1"`、preview 中展示过的配置和用户确认后的非空 `tasks`；后端保存 exact tasks，并在 `StudyPlan.parsed_config_json` 追溯 `confirmed_config`、`planner_strategy`、`recommended_daily_minutes`、`daily_minutes_source`、`capacity`、资料快照和生成元数据。保存时 capacity 会按最终提交的 `tasks[].subtasks[].estimated_minutes` 重新计算，避免旧客户端传入过期 capacity。旧客户端不传 `client_flow` 或使用默认 `legacy` 且省略 `tasks` 时，仍走保存前生成 preview 的兼容路径。保存阶段只写 `StudyPlan`、`StudyTask`、`StudySubTask`，不提前生成今日讲义或任务测试题内容。

请求体示例（新向导保存 exact preview tasks）：

```json
{
  "client_flow": "wizard_v1",
  "title": "Linear Algebra 学习计划",
  "goal_text": "期末复习",
  "start_date": "2026-07-10",
  "end_date": "2026-07-10",
  "duration_days": 1,
  "daily_available_minutes": 60,
  "recommended_daily_minutes": 60,
  "daily_minutes_source": "system_estimated",
  "preference": "sprint",
  "diagnostic_profile": {
    "question_version": "study_plan_diagnostic_v2"
  },
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "capacity": {
    "estimated_total_minutes": 60,
    "available_total_minutes": 60,
    "feasibility_status": "tight",
    "warnings": []
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
          "estimated_minutes": 60,
          "citation_chunk_ids": ["chk_123"],
          "sort_order": 1
        }
      ]
    }
  ]
}
```

`client_flow = "wizard_v1"` 但缺少 `tasks` 或提交 `tasks = []` 时，后端返回 `422 PREVIEW_TASKS_REQUIRED`。旧客户端兼容路径只适用于未声明新向导的保存请求。

前端基础创建页采用 `wizard_v1` 保存：保存按钮只在 preview 未过期时可用，请求体提交当前表单配置、preview `title`、preview 中展示过的 exact `tasks`，并携带 `Idempotency-Key`。同一份未变化 preview 的保存重试必须复用同一个幂等键；重新生成 preview 后才创建新的保存幂等键。诊断问题、诊断 profile、重生成、替换和删除接口虽已具备后端契约，但对应前端向导 / 编辑视图不在基础创建页内伪造。

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

### 3.28 课程学习计划列表

`GET /api/v1/courses/{course_id}/study-plans`

要求：Bearer token。只返回当前用户当前课程下未删除学习计划。

响应 `data`：`StudyPlanRead[]`。

### 3.29 学习计划详情

`GET /api/v1/study-plans/{plan_id}`

要求：Bearer token。只能读取当前用户自己的计划。

响应 `data`：与学习计划保存接口一致，包含 `plan`、`tasks`、`subtasks`。

### 3.30 学习计划重生成预览

`POST /api/v1/study-plans/{plan_id}/regeneration-previews`

要求：Bearer token。前端只提交用户本次修改的字段即可；后端会从已保存计划继承其余配置，并返回新的 `StudyPlanPreview`，不写数据库、不替换现有任务树。

请求体字段均可选：`goal_text`、`start_date`、`end_date`、`duration_days`、`daily_available_minutes`、`preference`、`diagnostic_profile`、`material_scope`。未传 `diagnostic_profile` 时继承保存计划中的诊断 profile；显式传入新的 `diagnostic_profile` 时覆盖，传 `{}` 表示清空诊断影响。

只修改学习天数时可只传：

```json
{
  "duration_days": 3
}
```

此时后端会用保存的 `start_date` 重新推导 `end_date`。如果同时覆盖 `start_date` 和 `duration_days`，则用新的 `start_date` 推导 `end_date`。前端不得把旧 `end_date` 和新的 `duration_days` 一起回填，除非两者确实描述同一个日期范围。

## 4. 已落地的 Study Mode 执行接口入口

以下接口后端已落地。前端接入时必须使用 `/api/v1` 全路径，并按统一成功 / 错误 envelope 处理 loading、empty、failed 与畸形内容兜底。

| 能力 | 接口入口 | 前端口径 |
| --- | --- | --- |
| 今日待办聚合 | `GET /api/v1/todos/today?date=YYYY-MM-DD` | 首页今日任务，只读聚合。 |
| 首页大日历 | `GET /api/v1/calendar/month?month=YYYY-MM`、`GET /api/v1/calendar/days/{date}/todos` | 月历摘要与日期弹窗，只读聚合。 |
| 课程日历 | `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM`、`GET /api/v1/courses/{course_id}/study-calendar/days/{date}` | 课程详情页日期摘要与今日任务。 |
| 执行上下文 | `GET /api/v1/study-subtasks/{subtask_id}/execution-context` | 返回当天任务、关联资料、最近成功 `handout_content_id` / `task_test_content_id`。 |
| 执行页任务问答 | `POST /api/v1/study-subtasks/{subtask_id}/qa/questions` | 请求体只含 `conversation_id` 和 `question`；后端固定使用当前二级任务关联资料范围。 |
| 二级任务完成 | `PUT /api/v1/study-subtasks/{subtask_id}/completion` | 请求体为 `{ "completed": boolean }`，不是 toggle。 |
| 今日讲义生成 | `POST /api/v1/study-subtasks/{subtask_id}/handouts` | 返回 `GeneratedContentRead`；默认复用最近一次 success，`force_regenerate=true` 重建。 |
| 任务测试题生成 | `POST /api/v1/study-subtasks/{subtask_id}/task-tests` | 返回 `GeneratedContentRead`；P2 只读展示通过 `task_test_content_id` 再调用 `GET /api/v1/generated-contents/{generated_content_id}` 读取详情。 |
| 任务测试题 Markdown 导出 | `GET /api/v1/generated-contents/{generated_content_id}/exports/markdown` | 返回 Markdown 文件流；只支持成功的 `task_test`，不保存作答、不判分、不生成 PDF。 |
| 今日讲义 PDF 导出 | `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf` | 返回 PDF 文件流；只支持成功的 `handout`，不保存导出历史，不支持任务测试题 PDF。 |

任务测试题后端生成和 Markdown 文件导出已实现；当前前端缺口是 P2 轻量只读展示。提交答案、判分、attempt 历史和反馈闭环属于后续 P9 / phase-1 S08，不在 P2 中引入。
## 5. 前端最小工作台验收口径

- 前端页面只需要覆盖基础集成路径：登录、课程列表、课程详情选择、资料上传、资料范围选择、问答提交和引用展示。
- 每个核心能力必须先有后端 service/router 测试，再用前端测试验证接入边界。
- 前端组件测试优先验证请求参数、状态兜底、错误码处理和路由跳转，不以视觉完整度作为基础设施阶段验收重点。
- 若前端展示与后端契约不一致，以本分区和后端 schema 为准，并优先修正文档或接口契约。
## 6. 2026-07-13 Study Mode 修复接入口径

- Course QA 和执行页任务级 QA 的前端接口、请求体和响应体不变；后端在 `/responses` 404 时会自动回退 Chat Completions，前端不需要区分模型接口形态。
- 学习计划保存后的 `parsed_config_json.task_snapshot` 会保留 quiz/test 子任务的 `generation_parameters.task_test` 默认参数。前端后续调用 task-test 生成时可省略 `parameters`，后端会使用计划默认值；若前端显式传入字段，则以请求值覆盖默认值。
- `GeneratedContentRead.source_citations` 是保留逐条引用能力的事实来源。新生成 handout 不再提供逐条引用；`task_test.content_json.questions[].source_citation_ids` 保存的是 `SourceCitation.id`，不是 chunk id，后端导出和内部追溯按 `source_citations[].id` 建映射。生成内容详情页不展示引用侧栏。
- 任务测试题 Markdown 导出在有效引用存在时不应出现 `Sources: unavailable`；若出现该文本，应视为引用链断裂或历史坏数据。
- 任务讲义 PDF 混排由后端 renderer 处理。后端生成阶段不正则改写数学公式；模型应按 prompt 输出 `$...$` / `$$...$$`。PDF renderer 在临时 HTML 中使用本地 KaTeX 排版公式；前端 Markdown 详情页若要漂亮显示公式，需要前端 renderer 另行接入数学渲染。

### 3.23.4 任务讲义详情前端展示契约

`handout` 是二级任务级讲义。前端应通过执行上下文和生成内容详情接口读取，不应自行从资料、chunk 或逐条引用拼装讲义正文。

推荐调用链：

1. `POST /api/v1/study-subtasks/{subtask_id}/handouts`：按需生成当前二级任务讲义。默认复用最近一次成功内容；`force_regenerate=true` 才重新生成。
2. `GET /api/v1/study-subtasks/{subtask_id}/execution-context`：读取当前二级任务上下文，其中 `handout_content_id` 指向最近一次成功生成的当前二级任务讲义。
3. `GET /api/v1/generated-contents/{generated_content_id}`：读取完整 `GeneratedContentRead` 供详情页展示。

`GeneratedContentRead` 中新生成 handout 的前端字段口径：

```json
{
  "content_type": "handout",
  "title": "Nyquist与Shannon公式讲义",
  "study_subtask_id": "sub_123",
  "content": "# Nyquist与Shannon公式讲义\n\n本讲义基于《Chap7 物理层.pdf》中“Nyquist与Shannon公式”相关内容生成。\n\n...",
  "content_json": {
    "format": "markdown",
    "schema_version": 1
  },
  "source_citations": []
}
```

前端展示规则：

- 讲义正文使用 `GeneratedContentRead.content` Markdown 渲染；不使用旧 `content_json.sections/blocks` 拼装，不使用 `dangerouslySetInnerHTML`。
- 标题直接使用 `GeneratedContentRead.title`；新生成内容应为 `{二级任务标题}讲义`。
- Markdown 正文顶部已包含来源说明句，例如 `本讲义基于《资料名1》《资料名2》中“二级任务标题”相关内容生成。`。
- 新生成 handout 不提供逐条 `source_citations`，详情页不要展示引用侧栏、引用列表、逐节来源入口，也不要显示“当前没有可展示的引用来源”空引用面板。
- 旧 `content_json.sections/blocks` 结构化 handout 不再作为新数据兼容目标；前端可以按通用畸形内容兜底处理。

`task_test` 暂时保持结构化 JSON 展示和逐题引用数据，不随 handout 改成 Markdown 直存；标题显示 `{二级任务标题}测试题`。逐题引用继续用于后端导出和内部追溯，生成内容详情页不展示引用侧栏。
