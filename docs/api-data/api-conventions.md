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
    "material_ids": []
  }
}
```

请求规则：

- 必填字段由接口契约明确声明。
- 前端不传空字符串代替缺失值；可选字段缺失时省略或传 `null`，由具体契约约定。
- 保存学习计划等已声明请求级幂等的接口应携带 `Idempotency-Key`；任务讲义和任务测试题当前使用“最近一次 success 复用 + `force_regenerate=true` 重建”，显式 `Idempotency-Key` 归入后续 P3 增强。

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
| `CURRENT_PASSWORD_MISMATCH` | 修改密码时当前密码不正确（HTTP 403）。 |
| `STATE_CONFLICT` | 当前状态不允许执行该操作。 |
| `UNSUPPORTED_FILE_TYPE` | 文件类型不支持。 |
| `MATERIAL_LINK_REMOVED` | 链接资料入口已停止支持：创建端点返回 410，历史 URL 资料解析重试返回 409。 |
| `FILE_TOO_LARGE` | 文件超过限制。 |
| `NO_PARSED_MATERIAL` | 当前范围没有已解析资料。 |
| `PARSE_FAILED` | 资料解析失败。 |
| `INDEXING_FAILED` | 资料索引写入、删除或重建失败。 |
| `RETRIEVAL_FAILED` | 资料向量检索失败。 |
| `MATERIAL_COVERAGE_INCOMPLETE` | 指定材料生成没有覆盖全部预期材料。 |
| `GENERATION_FAILED` | Agent 或 AI 内容生成失败。 |
| `GENERATION_SCHEMA_INVALID` | AI 结构化输出不符合调用方 schema。 |
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

- 保存学习计划读取并校验 `Idempotency-Key`；任务讲义和任务测试题当前不读取该 header，默认幂等语义是同一 `study_subtask_id + content_type` 复用最近一次 success，`force_regenerate=true` 时显式重建。
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

### S02 学习计划幂等规则

- `POST /api/v1/courses/{course_id}/study-plans` 读取 `Idempotency-Key`。
- 后端将 key 的 SHA-256 写入 `study_plans.idempotency_key_hash`，并在 `study_plans.parsed_config_json.idempotency` 保留 `key_hash` 与请求体 canonical `request_hash`。
- `(user_id, course_id, idempotency_key_hash)` 由数据库唯一索引兜底；并发重复提交不得创建重复计划、任务树或打卡派生。
- 同一用户、同一课程、同一 key 且同一请求体：返回既有计划 bundle，不重复创建计划。
- 同一用户、同一课程、同一 key 但请求体不同：返回 `409 IDEMPOTENCY_CONFLICT`。
- 已软删除计划仍占用原 key，后续不得复用该 `Idempotency-Key` 创建新计划。
- 未携带 `Idempotency-Key` 的旧客户端请求仍可保存，但不具备重复提交保护。

### S03 今日待办与日历只读查询约定

- S03 只使用 GET 接口，不提供待办或日历写接口。
- `date` 使用 `YYYY-MM-DD`，`month` 使用 `YYYY-MM`；非法日期或月份返回 `VALIDATION_ERROR`。
- 空日期、空月份返回空数组，不返回 404。
- 首页今日待办返回一级任务和嵌套二级任务，折叠/展开属于前端状态。
- 月历日期格最多返回 3 条 `task_summaries`，超出数量使用 `hidden_task_count`。
- 跨用户、已删除或不存在的课程返回 `NOT_FOUND`，不泄露目标课程信息。
- 所有 S03 查询必须零写入，不调用 `flush` 或 `commit`。
## S04/S05 API 约定补充

- completion 接口使用期望状态字段 `completed`，不得实现为 toggle。
- `completed_at` 使用 UTC datetime；打卡日期使用父一级任务的业务日期 `task_date`。
- `completion_ratio` 以字符串形式序列化 Decimal 四位小数，例如 `0.4000`。
- `color_level=0` 和 `color_level=1` 是不同语义状态：0 表示无任务，1 表示有任务但未开始。当前 UI 可以映射为同一颜色，但 API 不合并状态。
- checkins GET 接口只读，不因查询创建记录。
