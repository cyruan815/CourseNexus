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

## 4. 待后续任务落地的接口入口

以下接口是基础设施计划中的前端接入入口。后端实现完成后，必须在本文件补充请求体、响应 `data`、错误码和前端展示兜底。

| 能力 | 接口入口 |
| --- | --- |
| 课程资料列表 | `GET /api/v1/courses/{course_id}/materials` |
| 文件资料上传 | `POST /api/v1/courses/{course_id}/materials` |
| 链接资料创建 | `POST /api/v1/courses/{course_id}/material-links` |
| 资料详情 | `GET /api/v1/materials/{material_id}` |
| 资料删除 | `DELETE /api/v1/materials/{material_id}` |
| 解析重试 | `POST /api/v1/materials/{material_id}/parse-retries` |
| 课程对话列表 | `GET /api/v1/courses/{course_id}/conversations` |
| 对话消息列表 | `GET /api/v1/conversations/{conversation_id}/messages` |
| 课程问答 | `POST /api/v1/courses/{course_id}/qa/questions` |
| 生成内容列表 | `GET /api/v1/courses/{course_id}/generated-contents` |
| 生成内容详情 | `GET /api/v1/generated-contents/{content_id}` |
| 统一生成入口 | `POST /api/v1/courses/{course_id}/generations` |
| 学习计划预览 | `POST /api/v1/courses/{course_id}/study-plans/preview` |
| 学习计划保存 | `POST /api/v1/courses/{course_id}/study-plans` |
| 课程学习计划列表 | `GET /api/v1/courses/{course_id}/study-plans` |
| 学习计划详情 | `GET /api/v1/study-plans/{plan_id}` |

## 5. 前端最小工作台验收口径

- 前端页面只需要覆盖基础集成路径：登录、课程列表、课程详情选择、资料上传、资料范围选择、问答提交和引用展示。
- 每个核心能力必须先有后端 service/router 测试，再用前端测试验证接入边界。
- 前端组件测试优先验证请求参数、状态兜底、错误码处理和路由跳转，不以视觉完整度作为基础设施阶段验收重点。
- 若前端展示与后端契约不一致，以本分区和后端 schema 为准，并优先修正文档或接口契约。
