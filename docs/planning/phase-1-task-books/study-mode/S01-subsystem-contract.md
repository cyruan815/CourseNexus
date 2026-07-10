# S01 计划学习模式契约与迁移审计

## 0. 业务功能说明

- **业务场景**：计划学习模式会同时使用计划、每日任务、二级任务、日历、执行状态、打卡和生成内容，开发前必须先确认这些业务对象如何衔接。
- **用户能力**：S01 本身不提供独立页面，但它确保学生之后保存计划、查看日历、完成任务和查看打卡时使用同一套状态和数据，不出现字段不一致或半保存。
- **业务结果**：计划学习模式拥有稳定的业务边界、接口清单和数据基础，现有 13 张核心表可支撑第一阶段完整闭环。
- **业务边界**：S01 只做子系统契约与数据库审计，不实现计划生成、日历、任务完成、讲义或导出；S01-S05 可以与 G01 并行，只有 S06 依赖 G01。

## 1. 任务信息

- 编号与名称：`S01` 计划学习模式契约与迁移审计。
- 负责人角色：计划学习模式后端开发者。
- 目标：在不增加业务表的前提下，固定计划生成、聚合、执行、打卡、任务内容生成和导出的统一数据、接口、状态、事务与权限边界。
- 前置依赖：已合并的 baseline migration `backend/migrations/versions/20260709_0001_create_core_tables.py`；当前 `StudyPlan`、`StudyTask`、`StudySubTask`、`CheckinRecord`、`AIGeneratedContent`、`SourceCitation` SQLAlchemy model；`shared-contract.md`。
- 范围外事项：本任务不实现计划算法、待办查询、任务完成、生成器、PDF、前端页面；不修改五类独立生成器；不创建任何新业务表。

## 2. 实现范围

### 2.1 13 表逐字段审计

以下清单以当前 SQLAlchemy model、baseline migration 和 `table-schema.md` 为共同基线。实施 S01 时必须用 metadata 测试再次核对，字段缺失不得靠业务 JSON 中的同义键绕过。

| 表 | 当前字段 | 与计划学习模式的关系 | 审计结论 |
| --- | --- | --- | --- |
| `users` | `id`、`username`、`password_hash`、`nickname`、`avatar_url`、`status`、`created_at`、`updated_at`、`deleted_at` | `user_id` 权限根与打卡归属。 | 复用，无新增字段。 |
| `courses` | `id`、`user_id`、`name`、`description`、`teacher`、`term`、`status`、`created_at`、`updated_at`、`deleted_at` | 单课程计划归属；删除课程后子系统查询必须隐藏。 | 复用，无新增字段。 |
| `material_folders` | `id`、`user_id`、`course_id`、`name`、`sort_order`、`created_at`、`updated_at`、`deleted_at` | 仅用于资料归类和工作台浏览，不进入计划资料范围。 | 复用，无新增字段。 |
| `course_materials` | `id`、`course_id`、`user_id`、`folder_id`、`name`、`material_type`、`source_type`、`file_url`、`source_url`、`file_size`、`mime_type`、`parse_status`、`parse_error`、`page_count`、`created_at`、`updated_at`、`deleted_at` | 计划、讲义、任务测试题的材料边界；只允许 `parsed` 且未删除资料。 | 复用，无新增字段。 |
| `material_chunks` | `id`、`material_id`、`course_id`、`chunk_index`、`page`、`page_index`、`heading`、`content_text`、`embedding_id`、`created_at` | 全材料批次、引用快照的权威来源。 | 复用，无新增字段。 |
| `conversations` | `id`、`user_id`、`course_id`、`title`、`source_page`、`status`、`created_at`、`updated_at`、`deleted_at` | 执行页任务问答可复用，`source_page = task_execution`。 | 复用，无新增字段。 |
| `messages` | `id`、`conversation_id`、`course_id`、`role`、`content`、`answer_type`、`generation_status`、`error_code`、`material_scope_json`、`created_at` | 保存执行页问答，不承担任务状态。 | 复用，无新增字段。 |
| `source_citations` | `id`、`message_id`、`generated_content_id`、`material_id`、`chunk_id`、`material_name`、`page`、`page_index`、`hit_text`、`sort_order`、`created_at` | 讲义和任务测试题引用；必须关联真实资料并保留快照。 | 复用，无新增字段。 |
| `ai_generated_contents` | `id`、`user_id`、`course_id`、`study_subtask_id`、`source_message_id`、`content_type`、`title`、`content`、`content_json`、`generation_status`、`material_scope_json`、`error_code`、`created_at`、`updated_at`、`deleted_at` | 保存 `handout` 与 `task_test`；按二级任务关联。 | 复用，无 `handouts` 或 `task_tests` 表。 |
| `study_plans` | `id`、`user_id`、`course_id`、`title`、`goal_text`、`parsed_config_json`、`start_date`、`end_date`、`daily_available_minutes`、`status`、`created_at`、`updated_at`、`deleted_at` | 单课程计划主记录；偏好、材料范围、最终配置写入 `parsed_config_json`。 | 复用，无新增字段。 |
| `study_tasks` | `id`、`plan_id`、`course_id`、`title`、`task_date`、`start_time`、`end_time`、`status`、`sort_order`、`created_at`、`updated_at` | 日期级一级任务与日历聚合来源。 | 复用，无新增字段。 |
| `study_subtasks` | `id`、`task_id`、`plan_id`、`course_id`、`title`、`subtask_type`、`description`、`related_material_ids_json`、`status`、`completed_at`、`sort_order`、`created_at`、`updated_at` | 执行、完成、讲义、任务测试题、打卡统计的最小任务事实。 | 复用，无新增字段。 |
| `checkin_records` | `id`、`user_id`、`checkin_date`、`total_subtask_count`、`completed_subtask_count`、`completion_ratio`、`color_level`、`created_at`、`updated_at` | 用户自然日完成比例快照；已有 `(user_id, checkin_date)` 唯一约束。 | 复用，无新增字段。 |

### 2.2 migration 判断

本阶段结论为 **不创建 Alembic migration**，原因如下：

1. 自然语言解析结果、用户确认配置、偏好和材料范围均可稳定写入 `study_plans.parsed_config_json`。
2. 调整后的任务结构由现有三级表表达，不需要计划版本表。
3. 今日待办和日历是查询投影，不需要 `todos`、`calendar_events`。
4. 讲义和任务测试题已有 `study_subtask_id`、`content_type`、`content_json` 和生成状态字段。
5. 打卡每日唯一约束、计数、比例和 `0..5` 颜色等级均已存在。
6. PDF 可按请求流式返回，不需要 `export_records`。

只有出现现有列无法表达且已通过共享契约评审的持久化需求时，才允许 S01 负责人创建一个后续兼容 migration。该 migration 必须采用“新增 nullable 列 -> 数据回填 -> 后续版本收紧”的顺序，包含 `upgrade()`、`downgrade()`、metadata 测试和 SQLite 实际升级测试；不得修改 baseline migration。

### 2.3 子系统不变量

- 一个 `StudyPlan` 只绑定一个 `course_id`，并同时绑定当前 `user_id`。
- `StudyTask.course_id` 必须等于所属计划 `course_id`；`StudySubTask.plan_id/course_id` 必须与父任务和计划一致。
- `related_material_ids_json` 固定保存字符串 ID 数组，数组去重并保持用户确认顺序；所有 ID 必须属于同一课程。
- 计划状态只使用 `draft`、`active`、`completed`、`deleted`；任务状态只使用 `not_started`、`in_progress`、`completed`。
- 一级任务状态只由二级任务汇总，不能由客户端直接写。
- 软删除计划后，计划、任务和关联生成内容不物理删除；计划与任务不再进入列表和聚合查询。
- 完成或取消完成二级任务、一级任务汇总、计划完成态汇总、当日打卡重算必须处于一个数据库事务。
- 所有自然日按服务配置的 `Asia/Shanghai` 业务时区解释，API 日期仍传 `YYYY-MM-DD`。
- 前端不得在候选契约合并前接入 S02-S07 新接口；后端合并契约后再由前端负责人更新 `frontend-integration.md` 和前端类型。

### 2.4 精确文件边界

S01 实施允许：

- 创建 `backend/tests/modules/study_mode/test_subsystem_schema_contract.py`。
- 修改 `docs/api-data/contracts.md`、`docs/api-data/data-model.md`、`docs/api-data/table-schema.md`，只同步已确认的子系统契约和无迁移结论。
- 修改 `docs/architecture/module-boundaries.md`，仅在现状描述与本契约不一致时修正计划子系统依赖方向。
- 修改 `docs/planning/current-state.md`，记录 S01 审计完成。

S01 实施禁止：

- 修改 `backend/migrations/versions/20260709_0001_create_core_tables.py`。
- 修改 `backend/app/modules/generation/generators/{quiz,flashcard,mindmap,outline,knowledge_list}/**`。
- 修改 `frontend/**`、`docs/api-data/frontend-integration.md`。
- 创建计划版本、待办、日历、讲义、测试题、导出历史表。

## 3. 字段与接口

### 3.1 当前已实现 API

| 方法与路径 | 当前请求 | 当前响应 | 状态 |
| --- | --- | --- | --- |
| `POST /api/v1/courses/{course_id}/study-plans/preview` | `goal_text`、`start_date`、`end_date`、`daily_available_minutes`、`material_scope` | `StudyPlanPreview` | 已实现，当前为确定性占位计划，S02 替换内部实现。 |
| `POST /api/v1/courses/{course_id}/study-plans` | 与当前预览请求相同 | `plan + tasks + subtasks` | 已实现，S02 兼容扩展可调整任务保存。 |
| `GET /api/v1/courses/{course_id}/study-plans` | 无 body | `StudyPlanRead[]` | 已实现。 |
| `GET /api/v1/study-plans/{plan_id}` | 无 body | `plan + tasks + subtasks` | 已实现。 |

### 3.2 本子系统新增 API 候选总表

完整请求、响应和场景由对应任务书锁定；路径在契约合并前不得由前端自行猜测。

| 任务 | 方法与路径 | 用途 |
| --- | --- | --- |
| S02 | `POST /api/v1/courses/{course_id}/study-plan-config-parses` | 自然语言配置回填。 |
| S02 | `POST /api/v1/study-plans/{plan_id}/regeneration-previews` | 基于已保存计划生成不落库的可调整新预览。 |
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

### 3.3 统一错误码与 HTTP 状态

| HTTP | `error.code` | 子系统语义 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 无有效 Bearer token。 |
| 404 | `NOT_FOUND` | 资源不存在、已软删除或不向当前用户暴露。跨用户访问统一使用该码。 |
| 409 | `STATE_CONFLICT` | 已删除计划、错误任务类型、失败/生成中内容导出、不可替换的计划状态。 |
| 409 | `IDEMPOTENCY_CONFLICT` | 同一幂等键对应不同请求体。 |
| 409 | `MATERIAL_COVERAGE_INCOMPLETE` | 全材料生成未覆盖期望资料集合。 |
| 422 | `VALIDATION_ERROR` | 日期、枚举、计数、任务层级或请求结构无效。 |
| 400 | `NO_PARSED_MATERIAL` | 材料范围内没有可用已解析资料。 |
| 502 | `GENERATION_FAILED` | 模型或生成流程失败。 |
| 500 | `GENERATION_SCHEMA_INVALID` | 结构化输出无法通过目标 Pydantic schema。 |
| 500 | `PDF_EXPORT_FAILED` | PDF 渲染失败；S07 新增并同步 API 文档。 |

错误响应始终使用共享 envelope。任何接口都不得通过中文 `message` 区分业务分支。

### 3.4 后端未实现、仅占位能力

- `todos_calendar`、`learning_execution`、`exports` 当前只有 `__init__.py`，无 router/service/repository/schema。
- `checkins` 当前只有 model，无查询或重算 API。
- `handout`、`task_test` 当前只有包占位，无真实生成器。
- 上述能力在对应 S03-S07 完成前，前端只能显示 disabled/coming 状态，不得制造本地成功数据。

## 4. 测试计划

### 4.1 精确测试文件与场景

创建 `backend/tests/modules/study_mode/test_subsystem_schema_contract.py`，至少包含：

1. `test_baseline_has_exact_thirteen_core_tables`：断言表集合与当前 13 表完全一致。
2. `test_study_mode_reuses_existing_columns`：逐表断言本任务 2.1 列出的计划子系统字段存在。
3. `test_checkin_user_date_is_unique`：断言 `(user_id, checkin_date)` 唯一约束存在，并实际插入重复记录得到 `IntegrityError`。
4. `test_generated_content_supports_task_bound_types`：插入 `handout`、`task_test` 且关联 `study_subtask_id` 成功；插入未允许类型失败。
5. `test_no_todo_calendar_export_business_tables`：断言不存在 `todos`、`calendar_events`、`handouts`、`task_tests`、`export_records`。
6. `test_plan_and_task_enum_constraints`：非法计划状态、任务状态和二级任务类型被数据库约束拒绝。

### 4.2 命令与预期

```powershell
cd backend
conda run -n course-nexus python -m pytest tests/modules/study_mode/test_subsystem_schema_contract.py -q
conda run -n course-nexus python -m pytest tests/test_schema_metadata.py -q
conda run -n course-nexus python -m alembic upgrade head
```

预期：两组 pytest 均以退出码 0 完成；Alembic 升级到 `20260709_0001` 成功且不产生新 revision；SQLite metadata 中只有 13 张核心表。

## 5. 验收标准

### 5.1 自动化验收

- [ ] metadata 测试逐字段覆盖 13 表并全部通过。
- [ ] 重复用户日期打卡触发唯一约束。
- [ ] `handout`、`task_test` 能写入统一生成内容表。
- [ ] schema 中不存在待办、日历、讲义、任务测试题和导出记录独立表。
- [ ] `git diff --check` 通过。

### 5.2 人工验收

- [ ] 对照 baseline migration、SQLAlchemy models、`table-schema.md` 三处逐行核对字段、约束和索引，没有静默差异。
- [ ] API 候选已由计划子系统负责人和前端负责人确认；确认前前端未调用候选路径。
- [ ] G01 未合并时，S06 保持阻塞在公共生成契约，不修改其高冲突文件。

## 6. 交付物

- `backend/tests/modules/study_mode/test_subsystem_schema_contract.py`。
- 更新后的 `docs/api-data/contracts.md`、`data-model.md`、`table-schema.md`。
- 更新后的 `docs/architecture/module-boundaries.md` 和 `docs/planning/current-state.md`。
- 中文审计记录 `docs/planning/phase-1-validation/S01-schema-audit.md`，记录命令、日期、13 表结论和无 migration 结论。
- 建议独立提交：`test(study-mode): 固定计划子系统表结构契约`；`docs(study-mode): 记录子系统契约与迁移结论`。

## 7. 文档同步

- 新建或更新 `docs/domains/study-mode/index.md` 和 `docs/domains/study-mode/architecture.md`：记录计划、待办日历、执行、打卡、任务内容和导出的组件分层架构、代码归属、依赖方向、状态与数据流、事务所有权和公开接口；建立计划生成、排程、聚合、状态重算、打卡重算、内容生成和导出的算法目录，并标出复杂度/资源预算、失败补偿责任及公共契约测试证据。
- API、错误码和事务边界：更新 `docs/api-data/contracts.md`。
- 表、字段、唯一约束和无新增表结论：更新 `docs/api-data/data-model.md`、`docs/api-data/table-schema.md`。
- 模块依赖和只读聚合边界：必要时更新 `docs/architecture/module-boundaries.md`。
- 当前状态：更新 `docs/planning/current-state.md`。
- 不修改 PRD：S01 不改变产品行为，只把现有 PRD 落成实施契约。
- 不修改 `docs/api-data/frontend-integration.md`：该文件由前端负责人在契约合并后维护。

## 8. 冲突与注意事项

### 8.1 冲突点

- `backend/app/db/models.py` 与 `backend/migrations/versions/**` 由 S01 单一负责；本任务结论是不改动。
- `backend/app/api/router.py` 由计划学习模式开发者负责，但 S01 不注册业务 router。
- G01 负责 `generation/orchestrator/contracts.py` 和 `registry.py`；S01/S06 只能提出并消费已合并公开契约。
- 前端负责人独占 `frontend/**` 和 `frontend-integration.md`；新 API 合并后通过契约清单交接。

### 8.2 严格遵循项

- 统一 `/api/v1`、`snake_case`、成功/错误 envelope、Bearer token 和课程归属校验。
- 复用 `MaterialScope`，禁止增加 `selected_material_ids` 等同义字段。
- 计划生成、讲义、任务测试题使用全材料批次与覆盖核算。
- 所有历史引用保存真实 `material_id`、资料名快照、页码/页序号和命中文本。

### 8.3 一定不能做的事

- 不能修改 baseline migration 或靠删除本地数据库解决 schema 差异。
- 不能创建 `todos`、`calendar_events`、`handouts`、`task_tests`、`export_records`。
- 不能把 `StudyPlan` 改为多课程计划。
- 不能让聚合模块写计划和任务。
- 不能在计划保存阶段生成讲义或任务测试题。
- 不能修改五类独立生成器内部文件。

## 9. 完成检查表

- [ ] 实现范围全部完成。
- [ ] 13 表逐字段审计有自动化证据。
- [ ] migration 结论已记录且 baseline 未改动。
- [ ] 当前 API、新增候选 API、后端占位能力已明确区分。
- [ ] 目标自动化测试通过。
- [ ] 受影响模块回归通过。
- [ ] 文档同步完成。
- [ ] `git diff --check` 通过。
- [ ] 修改文件未越过所有权边界。
- [ ] 每个可验证小改动已独立提交。
