# 第一阶段共享协作契约

## 1. 适用范围

本文件是三名并行开发者的共同执行边界。任务书可以补充细节，但不得覆盖本文件。任何字段重命名、枚举语义改变、公共接口改变、数据库表变更或模块归属变化，都必须先通过共享契约变更，再进入功能实现。

## 2. 权威文档与代码

开始任务前必须按顺序阅读：

1. `AGENTS.md` 和 `docs/index.md`。
2. `docs/product/prd.md` 及任务涉及的 `docs/product/PRD/` 子文档。
3. `docs/architecture/overview.md`、`module-boundaries.md`、`runtime-flows.md`。
4. `docs/api-data/api-conventions.md`、`contracts.md`、`data-model.md`、`table-schema.md`。
5. `docs/engineering/development-conventions.md`、`definition-of-done.md`、`collaboration.md`。
6. `docs/engineering/rag-consumer-guide.md`，适用于所有问答和材料生成功能。

当前代码中的 Pydantic schema 和已注册 router 是“当前已实现接口”的事实来源；长期目标和缺口以 docs 为准。两者不一致时不得静默选一边，必须先在任务提交中同步修正文档或契约。

## 3. 固定 API 契约

### 3.1 通用规则

- API 前缀固定为 `/api/v1`。
- JSON 字段固定使用 `snake_case`。
- 成功响应固定为 `{ "data": ..., "meta": { "request_id", "server_time", "api_version" } }`。
- 错误响应固定为 `{ "error": { "code", "message", "details" }, "meta": { "request_id" } }`。
- 前端逻辑只能依赖稳定的 `error.code`，不得解析中文 `message`。
- 登录后业务接口使用 Bearer token，并校验当前用户的数据归属。
- 新增可选字段属于兼容变更；删除、重命名、类型变化、枚举语义变化属于破坏性变更。

### 3.2 材料范围

所有问答、独立生成和学习计划材料分析统一使用以下结构，不得增加同义字段：

```json
{
  "include_all_parsed_materials": true,
  "folder_ids": [],
  "material_ids": []
}
```

语义固定如下：

- `include_all_parsed_materials = true`：使用当前课程全部已解析且未删除资料；此时 `folder_ids` 和 `material_ids` 必须为空。
- `include_all_parsed_materials = false`：使用 `folder_ids` 与 `material_ids` 的并集；两者都为空时返回 `NO_PARSED_MATERIAL`。
- 材料范围是硬过滤条件，任何功能不得检索、生成或引用范围外资料。
- 只有 `parse_status = parsed` 且未软删除的资料可进入上下文。

### 3.3 两类上下文消费方式

- 问答类调用 `retrieve_relevant_context()`，目标是相关性；引用必须是本次命中 `chunk_id` 的子集。
- 指定材料生成调用 `iter_material_context_batches()` 和 `run_material_coverage()`，目标是覆盖全部选定材料；不得用一次 Top-K 检索替代。
- 业务模块不得直接导入 Docling、LlamaIndex、Chroma 或其具体适配器。
- 所有模型调用必须经过 `ModelProvider`；生产模块不得直接实例化 OpenAI SDK client。

### 3.4 第一阶段幂等边界

- 二级任务完成接口通过提交期望状态 `completed: boolean` 实现天然幂等，不使用 toggle。
- S02 计划保存可以按任务书约定使用稳定 `plan_id` 和请求哈希实现持久化幂等，但不得把幂等元数据暴露为产品字段。
- 通用材料生成以及 Handout/Task Test 当前没有可靠的幂等持久化字段；第一阶段只做前端请求中防重复，显式重新生成创建新历史记录。
- 严禁用进程内字典、缓存或被污染的业务 `content_json` 冒充跨进程 durable idempotency。若要补齐，必须单独评审技术表、migration 和跨模块所有权。

## 4. 固定字段、状态和存储规则

| 领域 | 固定字段或枚举 |
| --- | --- |
| 资料解析 | `uploaded`、`parsing`、`parsed`、`parse_failed`、`deleted` |
| 回答类型 | `grounded`、`partial_grounded`、`no_source` |
| 生成状态 | `pending`、`generating`、`success`、`failed` |
| 生成内容类型 | `quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`、`note`、`handout`、`task_test` |
| 计划状态 | `draft`、`active`、`completed`、`deleted` |
| 任务状态 | `not_started`、`in_progress`、`completed` |
| 二级任务类型 | `learn`、`review`、`quiz`、`test` |

必须遵循：

- 一个 `StudyPlan` 只绑定一个 `course_id`；不得实现多课程联合计划。
- Quiz、Flashcard、Mindmap、Outline、Knowledge List、Note、Handout、Task Test 统一保存到 `ai_generated_contents`。
- 上述结构化内容保存到 `content_json`，不得新建 `quizzes`、`flashcards`、`mindmaps`、`handouts` 或 `task_tests` 表。
- 今日待办和日历是从 `study_tasks`、`study_subtasks` 派生的只读聚合，不得新建 `todos` 或 `calendar_events` 写模型。
- 历史引用必须保存 `material_name`、`page`/`page_index`、`hit_text` 快照；不得生成没有真实 `material_id` 的引用。
- 计划保存时只保存计划和任务结构；讲义和任务测试题只在执行阶段按需生成。
- 完成二级任务必须幂等，并在同一事务边界内重算一级任务状态和当日 `CheckinRecord`。

## 5. 文件所有权与冲突控制

| 开发者 | 独占写入范围 | 不得写入 |
| --- | --- | --- |
| 前端 | `frontend/**`；自身任务涉及的前端联调文档 | `backend/**`、migration、后端 schema |
| 独立生成 | `backend/app/modules/generation/generators/{quiz,flashcard,mindmap,outline,knowledge_list}/**`、对应测试；G01 明确列出的公共生成契约文件 | `study_plans`、`todos_calendar`、`learning_execution`、`checkins`、`exports`、`handout`、`task_test` |
| 计划学习模式 | `study_plans`、`todos_calendar`、`learning_execution`、`checkins`、`exports`、`generation/generators/{handout,task_test}/**` 及对应测试 | 五类独立生成器内部文件、前端文件 |

高冲突文件采用单一负责人：

| 文件或区域 | 负责人 | 规则 |
| --- | --- | --- |
| `backend/app/api/router.py` | 计划学习模式开发者 | 仅在新增计划子系统 router 时修改；独立生成开发者复用现有 generation router。 |
| `backend/app/modules/generation/orchestrator/contracts.py` | 独立生成开发者（G01） | 计划学习模式只能消费，不得并行改名或改变签名。 |
| `backend/app/modules/generation/orchestrator/registry.py` | 独立生成开发者（G01） | 必须提供可扩展注册能力；计划学习模式通过公开注册协议接入 Handout/Task Test。 |
| `backend/app/db/models.py` | 计划学习模式开发者（S01） | 仅当确需新增模型 import 时修改；不得为五类生成内容新增表。 |
| `backend/migrations/versions/**` | 计划学习模式开发者（S01） | 第一阶段其他开发者不得创建 migration。 |
| `docs/api-data/table-schema.md` | 计划学习模式开发者（S01） | 独立生成开发者只使用现有 `content_json` 契约；需要变化时先提交契约提案。 |
| `docs/api-data/frontend-integration.md` | 前端开发者 | 后端开发者通过各自 API 文档提供变更，不直接并行改此文件。 |

出现共享文件需求时：先在任务分支提交一份契约说明或最小 patch 请求，由负责人合并；不得三方同时编辑后再依靠人工解决大段冲突。

## 6. 测试要求

所有后端任务必须至少包含：

- service 单元测试；
- router/API 测试；
- 当前用户归属和跨用户拒绝测试；
- 状态冲突、空材料、模型失败和 schema 校验失败测试；
- Fake `RagIndex`、Mock/Fake `ModelProvider`，自动化测试不得访问 live network；
- 与上下游边界相关的 contract 或 integration test。

所有前端任务必须至少包含：

- API client 契约测试；
- 组件/页面 loading、success、empty、error、disabled 状态测试；
- 401 清理会话与跳转登录测试；
- 用户关键操作测试，避免只断言静态文案；
- 桌面主视口和窄屏降级布局检查；
- 对未知枚举和缺失可选字段的兜底测试。

每份任务书必须列出精确测试文件、命令、预期结果和手工验收步骤。真实 OpenAI 或真实 PDF 端到端测试应写中文 Markdown 日志，但不能替代可重复自动化测试。

## 7. 文档同步矩阵

| 变更类型 | 必须同步的 docs |
| --- | --- |
| 产品行为或验收口径 | `docs/product/` 对应文档；未经产品确认不得改 PRD 原意 |
| 模块边界、依赖方向、数据归属 | `docs/architecture/module-boundaries.md`、必要时 `runtime-flows.md` |
| API 路径、请求、响应、错误码 | `docs/api-data/contracts.md`、`api-conventions.md`、前端联调文档 |
| 表、列、约束、索引、枚举 | `docs/api-data/data-model.md`、`table-schema.md`、Alembic migration |
| 当前完成状态或技术债 | `docs/planning/current-state.md`、`tech-debt-tracker.md` |
| 开发命令、测试或协作方式 | `docs/engineering/` 对应文档 |

## 8. 严禁事项

- 严禁绕过课程归属校验，仅凭资源 ID 查询或修改数据。
- 严禁在前端自行猜测或转换后端字段；类型必须来自显式 API 类型定义。
- 严禁静默修改 `material_scope`、状态枚举、响应 envelope 或错误码语义。
- 严禁为五类生成内容、讲义、任务测试题、待办或日历建立 PRD 未要求的独立业务表。
- 严禁生成器之间互相调用或直接修改学习计划、任务完成状态。
- 严禁计划子系统直接查询 Chroma、拼接 chunk 或直接调用 OpenAI SDK。
- 严禁前端为尚未实现的后端能力制造假成功数据；允许明确的 disabled/coming placeholder。
- 严禁把 live API key、用户资料正文、完整问题正文或密码写入测试日志和埋点。
- 严禁提交与当前任务无关的重构、格式化全仓文件或回退其他开发者变更。
- 严禁将多个可独立验证的小功能压成一个大提交。

## 9. 交付前检查

- 核对本任务实际修改文件全部位于所有权范围。
- 核对新增 API 和字段已进入文档并有前端可消费示例。
- 核对 migration 可升级，必要时可降级，并通过 schema metadata 测试。
- 核对 `git diff --check`、目标测试和受影响模块回归测试均通过。
- 在任务书验收表逐项记录证据；失败项不得标记完成。
