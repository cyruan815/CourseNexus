# Study Mode 内容生成异步 Job 设计方案

## 文档状态

- **状态**：待负责人确认，尚未实现
- **日期**：2026-08-25
- **适用范围**：Study Mode 任务讲义与任务测试题生成
- **关联实现**：`task-content.md` 中的“任务之间并发生成（阶段一）”
- **目标**：将当前前端任务级并发升级为可恢复、可限流、可重试的后端异步生成任务

## 1. 背景与问题

当前执行页已经允许不同二级任务同时发起生成。每个请求仍然保持一个同步 HTTP 连接，直到模型调用和内容保存全部完成：

```text
前端点击生成
  -> POST 讲义 / 测试题接口
  -> 后端执行模型调用
  -> 保存 GeneratedContent
  -> 返回 GeneratedContentRead
```

这个阶段可以满足“讲义 A、B、C 同时生成”，但生成过程由浏览器连接承载，存在以下限制：

- 页面刷新后无法恢复正在生成的任务。
- 关闭页面或浏览器取消请求时，任务可能中断。
- 后端没有统一的任务队列和并发上限。
- 没有持久化的 `pending` / `running` / `failed` 状态。
- 多个客户端同时请求同一任务时，可能重复调用模型。
- 长时间模型调用可能受到 HTTP、代理或浏览器超时影响。
- 失败重试依赖用户再次点击，无法统一处理 429、超时和短暂服务错误。

## 2. 目标与非目标

### 2.1 目标

- 创建任务后立即返回 `job_id`，不让 HTTP 请求长时间等待模型。
- 让讲义 A、B、C 分别拥有独立且可查询的生成状态。
- 页面刷新后可以恢复任务状态和已生成内容。
- 后端统一控制总并发、单用户并发和模型用途并发。
- 对模型超时、429 和可重试错误提供有限次数的自动重试。
- 保证同一个二级任务同一内容类型不会重复创建活动 Job。
- 保留现有 `GeneratedContent` 作为最终内容存储，不改变讲义和测试题内容结构。

### 2.2 非目标

本方案不重新设计：

- PDF 上传、解析和 chunk 存储。
- material-context 查询和资料范围规则。
- handout 的 Markdown schema。
- task-test 的结构化 schema。
- Study Plan 的 map/reduce 算法。
- 测试题作答历史和后端判分。

## 3. 目标架构

```text
前端点击生成
    |
    v
POST 创建 generation job
    |
    +--> 立即返回 job_id、status=pending
    |
    v
后台 worker 从队列领取 Job
    |
    +--> running: 读取已解析 chunk，调用现有 handout / task-test 流程
    |
    +--> succeeded: 保存 GeneratedContent，写入 result_content_id
    |
    +--> failed: 保存稳定错误码和错误信息
    |
    v
前端轮询 Job 状态或接收 SSE 更新
```

Job 只负责编排和状态；现有生成器继续负责内容生成和 schema 校验。这样可以降低对当前 handout、task-test 和 material-context 代码的影响。

## 4. Job 状态模型

### 4.1 状态

```text
pending -> running -> succeeded
pending -> running -> failed
pending -> canceled
running -> retrying -> running
running -> failed
```

建议状态含义：

| 状态 | 含义 |
| --- | --- |
| `pending` | 已创建，等待 worker 获取 |
| `running` | worker 正在执行模型生成 |
| `retrying` | 发生可重试错误，等待下一次尝试 |
| `succeeded` | 已成功保存 `GeneratedContent` |
| `failed` | 已达到失败条件，不再自动执行 |
| `canceled` | 用户或系统取消，未产生可用结果 |

### 4.2 建议数据表

建议新增表：`content_generation_jobs`。

字段建议：

| 字段 | 作用 |
| --- | --- |
| `job_id` | Job 主键，例如 `job_...` |
| `user_id` | 创建者和权限归属 |
| `course_id` | 课程归属 |
| `plan_id` | 学习计划归属 |
| `subtask_id` | 二级任务归属 |
| `content_type` | `handout` 或 `task_test` |
| `status` | 当前 Job 状态 |
| `progress_stage` | `queued`、`material_context`、`generating`、`saving` 等阶段 |
| `result_content_id` | 成功时关联 `ai_generated_contents.id` |
| `error_code` | 稳定错误码 |
| `error_message` | 脱敏后的可展示错误 |
| `retry_count` | 已执行重试次数 |
| `idempotency_key` | 防止重复创建的请求键 |
| `created_at` | 创建时间 |
| `started_at` | 首次执行时间 |
| `finished_at` | 成功、失败或取消时间 |
| `updated_at` | 最近更新时间 |

建议索引：

- `(user_id, status, created_at)`：查询用户未完成 Job。
- `(subtask_id, content_type, status)`：查询同一任务活动 Job。
- `idempotency_key`：请求幂等控制。

建议约束：同一 `subtask_id + content_type` 在活动状态（`pending`、`running`、`retrying`）下最多存在一个 Job。`force_regenerate` 的并发语义需要负责人确认后再落到约束中。

## 5. API 设计

### 5.1 创建 Job

可以保留现有接口路径，将其语义改为“提交生成任务”，也可以新增异步路径。兼容性优先时建议保留现有路径，并新增明确的 Job 返回结构：

```http
POST /api/v1/study-subtasks/{subtask_id}/handouts
POST /api/v1/study-subtasks/{subtask_id}/task-tests
```

返回示例：

```json
{
  "job_id": "job_123",
  "status": "pending",
  "subtask_id": "subtask_123",
  "content_type": "handout"
}
```

另一个可选方案是新增：

```http
POST /api/v1/content-generation-jobs
```

由请求体指定 `subtask_id` 和 `content_type`。该方案边界更统一，但会引入新的公共 API。两种方案不能在未确认前同时实现。

### 5.2 查询 Job

```http
GET /api/v1/content-generation-jobs/{job_id}
```

返回示例：

```json
{
  "job_id": "job_123",
  "status": "running",
  "progress_stage": "generating",
  "subtask_id": "subtask_123",
  "content_type": "handout",
  "result_content_id": null,
  "error_code": null,
  "retry_count": 0
}
```

可选接口：

```http
GET  /api/v1/study-subtasks/{subtask_id}/content-generation-jobs
POST /api/v1/content-generation-jobs/{job_id}/retry
POST /api/v1/content-generation-jobs/{job_id}/cancel
```

第一版不一定需要全部提供。查询和创建是必需接口，重试、取消和历史列表应按负责人确认的产品范围决定。

## 6. 后端执行拆分

当前同步生成服务建议拆为两个职责：

```text
submit_generation_job()
run_generation_job()
```

### 6.1 提交阶段

提交阶段在 HTTP 请求内完成：

1. 校验当前用户、课程、计划、二级任务和内容类型。
2. 校验关联资料范围和已解析状态。
3. 检查同一任务是否已经有活动 Job。
4. 生成 `idempotency_key` 并创建 Job。
5. 将 Job 放入 worker 队列。
6. 立即返回 `job_id`。

### 6.2 执行阶段

worker 执行：

1. 原子地把 `pending` Job 标记为 `running`。
2. 读取当前任务允许的已解析 chunk。
3. 调用现有 handout 或 task-test generator。
4. 成功时保存 `AIGeneratedContent` 和必要的引用。
5. 将 `result_content_id` 写回 Job，并标记 `succeeded`。
6. 失败时保存失败记录、稳定错误码和重试信息。

现有 map/reduce、资料上下文和 schema 校验逻辑不需要重写，只需要从同步请求路径迁移到 `run_generation_job()` 可调用的执行函数。

## 7. Worker 与并发策略

建议第一版设置可配置的后端并发上限，例如：

```text
CONTENT_GENERATION_MAX_CONCURRENCY=3
```

行为示例：

```text
job A: running
job B: running
job C: running
job D: pending
```

建议分别评估：

- 全局最大并发数。
- 单用户最大并发数。
- handout 和 task-test 是否共用额度。
- 不同模型用途是否分别限流。
- 429、超时和服务暂时不可用时的退避策略。

实现选项：

| 方案 | 优点 | 风险 / 代价 |
| --- | --- | --- |
| Redis + Celery/RQ/Arq | 队列、重试和 worker 生态成熟 | 新增 Redis、worker 和部署配置 |
| 数据库 Job 表 + 独立 worker | 依赖少，状态天然持久化 | SQLite 写锁和抢占任务需要仔细设计 |
| FastAPI `BackgroundTasks` | 改动小，适合短任务 | 服务重启丢任务，不适合可靠后台生成 |

若目标包含页面关闭后继续执行、重启恢复和稳定重试，不建议将 `BackgroundTasks` 作为最终方案。

## 8. 前端改动

当前前端已经按 `subtask_id` 隔离状态。迁移到 Job 后需要：

- 保存 `job_id -> subtask_id` 和 `job_id -> content_type` 映射。
- 提交成功后立即显示 `pending`，不等待同步生成结果。
- 轮询 `GET /content-generation-jobs/{job_id}`，或采用 SSE 接收状态更新。
- `succeeded` 后读取 `result_content_id` 并加载内容。
- `failed` 后只显示对应任务的错误。
- 页面加载时查询当前用户未完成 Job，恢复各任务状态。
- 同一任务存在活动 Job 时显示已有状态，不重复创建。
- 按确认的范围增加重试、取消和失败详情。

轮询实现简单、依赖少，适合作为第一版；SSE 实时性更好，但需要额外处理连接恢复和代理配置。两者应在实现前确认。

## 9. 失败、重试与补偿

建议规则：

- 模型超时：有限次数重试，使用指数退避。
- HTTP 429：按 `Retry-After` 或指数退避重试。
- 网络暂时不可用：重试并记录次数。
- schema 校验失败：默认直接失败；是否重试需要按生成器特点确认。
- 权限、资料缺失和参数错误：不重试。
- worker 重启：启动时扫描超时的 `running` Job，标记为可重试或失败。
- 生成成功但 Job 更新失败：通过结果关联和补偿扫描避免重复生成。
- 用户重复点击：返回已有活动 Job，而不是创建新 Job。
- `force_regenerate=true`：是否允许覆盖活动 Job，必须明确产品语义。

取消只能保证未开始或尚未进入不可中断模型调用的 Job 不再执行。已经发出的模型请求未必能被供应商真正取消。

## 10. 对现有系统的影响

### 10.1 需要修改

- `learning_execution` router 和 service。
- Job 数据模型、migration 和 repository。
- Study Mode 前端 API adapter 和执行页。
- worker 启动方式与部署配置。
- 日志、指标和任务排障入口。
- 后端 API、前端页面和集成测试。

### 10.2 原则上不修改

- 资料上传和 PDF 解析。
- chunk 存储和 material-context 查询。
- handout / task-test 内容 schema。
- 计划的 map/reduce 算法。
- 任务完成和打卡事务。

### 10.3 主要风险

- Job 状态和 `GeneratedContent` 可能短暂不一致。
- SQLite 可能产生写锁竞争，尤其是多个 Job 同时完成时。
- 重试设计不严谨会产生重复内容或重复费用。
- 并发上限过高会导致模型 API 429、超时和成本上升。
- API 返回结构变化会影响现有前端和其他调用方。
- 新增 Redis / worker 会增加本地开发和部署复杂度。
- 取消操作无法保证中断已经发出的模型请求。

## 11. 需要负责人确认的决策

以下事项在编码前必须确认：

1. 只把讲义改成 Job，还是讲义和测试题一起改？
2. 页面关闭或刷新后，任务是否必须继续执行并可恢复？
3. 初始最大并发数设为 3、5，还是仅配置不设产品固定值？
4. 是否设置单用户并发上限？
5. 是否允许取消任务？取消需要保证到什么程度？
6. 自动重试哪些错误，最多几次？
7. 采用 Redis 队列，还是数据库 Job 表 + 独立 worker？
8. 是否允许新增表和 migration？
9. 保留现有同步 API 兼容入口，还是直接切换返回结构？
10. 前端采用轮询还是 SSE？
11. Job 历史保存多久，是否需要清理任务？
12. 是否记录排队耗时、模型耗时、重试次数和 token 指标？

## 12. 建议实施顺序

### 阶段 0：方案确认

- 确认状态、字段、API、并发数、重试和队列技术。
- 确认数据库变更和公共 API 变更的负责人审批边界。

### 阶段 1：后端 Job 基础能力

- 新增模型、migration、repository 和状态转换。
- 实现创建 Job、查询 Job 和 worker 执行。
- 使用测试 provider 验证成功、失败、重复提交和重试。

### 阶段 2：前端迁移

- 将同步等待改为提交 Job + 查询状态。
- 接入刷新恢复、任务级错误、重试和必要的取消入口。

### 阶段 3：可靠性验证

- A、B、C 同时提交且结果归属正确。
- 页面刷新后状态可以恢复。
- 一个任务失败不影响其他任务。
- 重复点击不会创建多个活动 Job。
- worker 重启后任务能按规则恢复或失败。
- 并发上限和 429 / 超时重试符合配置。

## 13. 验收标准

- 创建请求在短时间内返回 `job_id`，不等待模型完成。
- A、B、C 可以独立排队、运行和完成。
- 完成顺序不影响 `subtask_id` 与最终内容的对应关系。
- 刷新页面后仍能看到未完成 Job 的状态。
- 同一个任务同一内容类型不会产生多个活动 Job。
- 一个 Job 失败不会改变其他 Job 的状态。
- 并发数、重试次数和退避策略可配置并有日志记录。
- 现有 `GeneratedContent` 内容结构和资料范围规则保持不变。
