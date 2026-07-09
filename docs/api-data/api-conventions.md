# API Conventions v0.1

## API 风格

- API 使用 JSON REST 风格。
- 基础前缀为 `/api/v1`。
- 普通请求使用 JSON；文件上传使用 `multipart/form-data`。
- API 字段统一使用 `snake_case`，与 PRD 字段口径保持一致。
- 本文件定义约定，不替代后续具体接口设计。

## URL 命名规则

- 路径使用资源名复数，例如 `/courses`、`/materials`、`/study-plans`、`/study-tasks`。
- 嵌套路径表达归属，例如 `/courses/{course_id}/materials`、`/courses/{course_id}/conversations`。
- 动作类资源使用明确命令名，例如 `/materials/{material_id}/parse-retries`、`/study-subtasks/{subtask_id}/completion`。
- 不在 URL 中暴露数据库实现细节。

## 请求格式

```json
{
  "course_id": "crs_...",
  "material_scope": {
    "include_all_parsed_materials": true,
    "folder_ids": [],
    "material_ids": []
  }
}
```

请求规则：

- 必填字段由接口契约明确声明。
- 前端不传空字符串代替缺失值；可选字段缺失时省略或传 `null`，由具体契约约定。
- 创建、生成、保存计划等可能重复提交的请求应携带 `Idempotency-Key`。

## 响应格式

成功响应：

```json
{
  "data": {},
  "meta": {
    "request_id": "req_...",
    "server_time": "2026-07-09T12:00:00+08:00",
    "api_version": "v1"
  }
}
```

错误响应：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数不合法",
    "details": {}
  },
  "meta": {
    "request_id": "req_..."
  }
}
```

前端只能依赖稳定的 `error.code` 做逻辑判断，不依赖中文 `message`。

## 错误码

| 错误码 | 含义 |
| --- | --- |
| `VALIDATION_ERROR` | 请求参数不合法。 |
| `UNAUTHORIZED` | 未登录或登录失效。 |
| `FORBIDDEN` | 已登录但无权访问目标数据。 |
| `NOT_FOUND` | 资源不存在，或出于权限原因不暴露存在性。 |
| `CONFLICT` | 资源冲突。 |
| `STATE_CONFLICT` | 当前状态不允许执行该操作。 |
| `UNSUPPORTED_FILE_TYPE` | 文件类型不支持。 |
| `FILE_TOO_LARGE` | 文件超过限制。 |
| `NO_PARSED_MATERIAL` | 当前范围没有已解析资料。 |
| `PARSE_FAILED` | 资料解析失败。 |
| `GENERATION_FAILED` | Agent 或 AI 内容生成失败。 |
| `IDEMPOTENCY_CONFLICT` | 幂等键对应的请求内容冲突。 |
| `RATE_LIMITED` | 请求过于频繁。 |
| `INTERNAL_ERROR` | 服务端内部错误。 |

## 分页规则

- 普通列表默认使用 cursor pagination。
- 请求参数：`limit`、`cursor`。
- 响应 `meta` 返回 `next_cursor`、`has_more`。
- `limit` 默认 20，最大 100。
- 首页日历、今日待办、课程内日历优先按 `date`、`month` 或 `date_range` 查询，不强行分页。

## 鉴权与权限

- 登录后业务接口要求有效登录态，可使用 Bearer token 或等价 session。
- `401 UNAUTHORIZED` 表示未登录或登录失效。
- `403 FORBIDDEN` 表示登录有效但无权访问目标数据。
- 本期不做多角色权限；权限核心是数据归属校验。
- 当前用户只能访问自己的课程、资料、对话、生成内容、计划、任务和打卡记录。

## 幂等约定

- 创建课程、保存计划、生成 AI 内容、生成讲义、生成任务测试题等接口应支持 `Idempotency-Key`。
- 完成或取消完成二级任务必须幂等，重复请求不能重复累计完成数。
- `CheckinRecord` 按 `user_id + checkin_date` 唯一更新。
- 幂等冲突返回 `IDEMPOTENCY_CONFLICT`。

## 时间、ID、状态字段

- ID 使用后端生成的不透明字符串，建议 UUID 或 ULID，不向前端暴露自增语义。
- `created_at`、`updated_at`、`deleted_at` 使用 ISO 8601 datetime。
- 业务日期使用 `YYYY-MM-DD`。
- 状态枚举以 PRD 为准：`parse_status`、`generation_status`、`content_type`、`task_status`、`subtask_type`、`plan_status`。
- 前端必须容忍未知枚举值并展示兜底状态。

## 版本策略

- v0.1 API 固定在 `/api/v1`。
- 新增可选字段属于兼容变更。
- 删除字段、重命名字段、改变字段类型、改变枚举语义、改变权限规则属于破坏性变更。
- 破坏性变更必须提供迁移期兼容方案或进入新的 API 版本。
