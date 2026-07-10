# S02 学习计划生成、编辑与生命周期

## 0. 业务功能说明

- **业务场景**：学生有“几天内掌握某章”“考前两周完成复习”等目标，希望系统把目标转换为每天可以执行的安排。
- **用户能力**：输入自然语言目标，自动回填起止日期、每日时长和偏好；选择资料；查看并调整计划预览；保存、编辑、重新生成或删除单课程计划。
- **业务结果**：系统生成按日期排列的一级任务和二级任务，并保证保存操作要么完整成功、要么不留下半个计划。
- **业务边界**：计划生成阶段只创建任务结构，不提前生成今日讲义、任务测试题或学习笔记；本期不做多课程联合排程和冲突优化。

## 1. 任务信息

- 编号与名称：`S02` 学习计划生成、编辑与生命周期。
- 负责人角色：计划学习模式后端开发者。
- 目标：把当前确定性占位计划升级为基于真实全材料的单课程计划，并支持自然语言配置回填、可调整预览、原子保存、编辑替换、重生成预览和软删除。
- 前置依赖：S01 契约与无 migration 结论已合并；`iter_material_context_batches()`、`run_material_coverage()`、`ModelProvider.generate_structured()` 可用；当前 preview/save/list/detail API 及测试通过。
- 范围外事项：不实现待办/日历查询、任务完成、打卡、讲义、任务测试题、PDF；不实现多课程联合计划和冲突优化；不修改前端。

## 2. 实现范围

### 2.1 实施步骤

1. 先为自然语言解析、全材料覆盖、预览校验、保存事务、幂等、编辑替换、重生成和删除写失败测试。
2. 在 `study_plans/schemas.py` 增加严格的配置解析、生成中间结果、预览和写入 schema；保留当前请求字段兼容。
3. 创建 `study_plans/planner.py`，只负责 plan map/reduce，不直接访问数据库或提交事务。
4. 将 `preview_study_plan()` 从 `resolve_context(limit=20)` 迁移到 `iter_material_context_batches()` + `run_material_coverage()`；每个 batch 调用结构化 provider，最终 reduce 成完整预览。
5. 自然语言配置解析仅回填可编辑字段，不落库、不直接创建计划；无法确定的字段返回 `null` 并列入 `unresolved_fields`。
6. 保存接口接受用户调整后的任务树；若旧客户端未传 `tasks`，后端先调用真实预览再保存，保持兼容。
7. repository 去除内部 `commit()`；service 对计划、一级任务、二级任务执行一次提交，任何失败统一 rollback。
8. 使用 `Idempotency-Key` 派生稳定 `plan_id`，在 `parsed_config_json.idempotency` 保存 `key_hash` 与 `request_hash`；同键同请求返回既有 bundle，同键不同请求返回 `IDEMPOTENCY_CONFLICT`。
9. 编辑采用 `PUT` 原子替换计划配置及任务结构；只允许所有二级任务均为 `not_started` 且无任务绑定生成内容时替换，避免丢失进度。
10. 重生成只返回新预览，不改数据库；用户确认后再调用 `PUT`。
11. 删除写 `status = deleted`、`deleted_at`、`updated_at`；任务通过所属计划过滤退出列表、日历和执行入口。
12. 每次保存或替换后计算计划状态为 `active`；计划完成态由 S04 在所有二级任务完成后派生。

### 2.2 精确文件边界

创建：

- `backend/app/modules/study_plans/planner.py`：计划 map/reduce 与 prompt 构造。
- `backend/tests/modules/study_plans/test_study_plan_lifecycle.py`：service 生命周期测试。
- `backend/tests/modules/study_plans/test_study_plan_lifecycle_api.py`：新增/扩展 API 测试。
- `backend/tests/integration/test_full_material_plan_flow.py`：多资料、多 batch 覆盖集成测试。

修改：

- `backend/app/modules/study_plans/schemas.py`。
- `backend/app/modules/study_plans/repository.py`。
- `backend/app/modules/study_plans/service.py`。
- `backend/app/modules/study_plans/router.py`。
- `backend/tests/modules/study_plans/test_study_plan_foundation.py`：移除只针对占位轮转规则的断言，保留权限与基础保存回归。
- `backend/tests/modules/study_plans/test_study_plan_api.py`：保留当前四接口兼容回归。

禁止修改：

- `backend/app/modules/todos_calendar/**`、`learning_execution/**`、`checkins/**`、`exports/**`。
- `backend/app/modules/generation/generators/**`。
- `backend/app/modules/generation/orchestrator/contracts.py`、`registry.py`。
- `backend/migrations/**`、`backend/app/db/models.py`、`frontend/**`。

### 2.3 计划生成规则

- `material_scope` 严格复用共享结构；`include_all_parsed_materials = true` 时两个 ID 数组必须为空。
- 每份范围内已解析资料必须进入至少一个 map batch；任一 batch 失败则整个预览失败，不返回伪完整计划。
- map 输出 `PlanMaterialUnit[]`：`topic`、`summary`、`difficulty`、`estimated_minutes`、`related_material_ids`、`citation_chunk_ids`。
- reduce 输出日期连续且位于 `[start_date, end_date]` 的 `StudyTaskPreview[]`；每天至少一个二级任务，二级任务类型只能为 `learn|review|quiz|test`。
- 每日二级任务 `estimated_minutes` 总和不得超过 `daily_available_minutes`；该值只用于生成校验，不新增数据库列，写入二级任务 `description` 的结构化说明不允许，最终预览返回该字段但保存时把整份生成配置写入 `parsed_config_json`。
- `related_material_ids` 必须非空、去重、属于请求材料范围；引用 chunk 必须来自本次 batch。
- 测试任务不是每日必需；如存在，必须排在当天二级任务最后。
- 计划预览不写 `study_plans`，因此不会产生未确认 draft 记录。

### 2.4 事务与替换规则

- repository 只执行 `add`、`delete`、`select`、`flush`，不调用 `commit()`。
- service 在一次事务中写计划、任务和子任务；外键、校验或 flush 失败时调用 `rollback()`，数据库中不得出现半份计划。
- `PUT` 替换时先锁定并校验当前计划，再删除旧二级任务、旧一级任务，更新计划，写入新任务树，最后一次提交。
- SQLite POC 使用单 session 事务；测试通过注入第二个写入异常证明 rollback。后续 PostgreSQL 可在 repository 查询中增加 `FOR UPDATE`，本任务不引入数据库专有语法。
- 删除操作重复调用：第一次返回已删除计划摘要；第二次因默认查询隐藏返回 `NOT_FOUND`，不恢复数据。

## 3. 字段与接口

### 3.1 复用与新增 Pydantic 类型

- 复用：`MaterialScope`、`StudyPlanRead`、`StudyTaskRead`、`StudySubTaskRead`、`StudyPlanBundleRead`。
- 新增：`PlanPreference = Literal["balanced", "fast_track", "mastery", "advanced"]`。
- 新增：`StudyPlanConfigParseRequest`、`StudyPlanParsedConfig`、`StudyPlanConfigParseResponse`。
- 新增：`PlanMaterialUnit`、`PlanBatchExtraction`、`StudyPlanReduction`。
- 扩展：`StudySubTaskPreview` 新增 `estimated_minutes: int`、`citation_chunk_ids: list[str]`。
- 扩展：`StudyPlanPreview` 新增 `preference`、`coverage`；保留当前所有顶层字段。
- 新增：`StudyPlanSaveRequest`、`StudyPlanReplaceRequest`，共享同一任务树校验器。

`coverage` 精确结构：

```json
{
  "expected_material_ids": ["mat_1", "mat_2"],
  "processed_material_ids": ["mat_1", "mat_2"],
  "batch_count": 3
}
```

### 3.2 当前已实现 API 的兼容扩展

#### `POST /api/v1/courses/{course_id}/study-plans/preview`

请求：

```json
{
  "goal_text": "两周掌握传输层并完成章节测试",
  "start_date": "2026-07-11",
  "end_date": "2026-07-24",
  "daily_available_minutes": 60,
  "preference": "mastery",
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
  "course_id": "crs_1",
  "title": "计算机网络传输层学习计划",
  "goal_text": "两周掌握传输层并完成章节测试",
  "start_date": "2026-07-11",
  "end_date": "2026-07-24",
  "daily_available_minutes": 60,
  "preference": "mastery",
  "material_scope": {
    "include_all_parsed_materials": true,
    "folder_ids": [],
    "material_ids": []
  },
  "coverage": {
    "expected_material_ids": ["mat_1", "mat_2"],
    "processed_material_ids": ["mat_1", "mat_2"],
    "batch_count": 3
  },
  "tasks": [
    {
      "title": "可靠传输基础",
      "task_date": "2026-07-11",
      "sort_order": 1,
      "subtasks": [
        {
          "title": "理解滑动窗口",
          "subtask_type": "learn",
          "description": "学习窗口推进、确认与重传关系",
          "related_material_ids": ["mat_1"],
          "estimated_minutes": 45,
          "citation_chunk_ids": ["chk_1"],
          "sort_order": 1
        }
      ]
    }
  ]
}
```

错误：`NOT_FOUND` 404、`NO_PARSED_MATERIAL` 400、`MATERIAL_COVERAGE_INCOMPLETE` 409、`GENERATION_FAILED` 502、`GENERATION_SCHEMA_INVALID` 500、`VALIDATION_ERROR` 422。

#### `POST /api/v1/courses/{course_id}/study-plans`

请求包含上述配置和用户最终确认的 `title`、`tasks`。`tasks` 暂时可省略以兼容当前客户端；省略时后端生成一次真实预览并保存。请求头 `Idempotency-Key` 为新客户端必传，长度 8-128。

响应仍为：

```json
{
  "plan": {"id": "sp_1", "course_id": "crs_1", "status": "active"},
  "tasks": [{"id": "tsk_1", "task_date": "2026-07-11", "status": "not_started"}],
  "subtasks": [{"id": "sub_1", "task_id": "tsk_1", "status": "not_started"}]
}
```

新增错误：`IDEMPOTENCY_CONFLICT` 409。当前 list/detail API 路径和响应不变。

### 3.3 本任务新增 API

#### `POST /api/v1/courses/{course_id}/study-plan-config-parses`

请求：

```json
{
  "goal_text": "从 2026-07-11 到 2026-07-24，每天 60 分钟精通传输层",
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
  "goal_text": "精通传输层",
  "start_date": "2026-07-11",
  "end_date": "2026-07-24",
  "daily_available_minutes": 60,
  "preference": "mastery",
  "material_scope": {
    "include_all_parsed_materials": true,
    "folder_ids": [],
    "material_ids": []
  },
  "unresolved_fields": []
}
```

无法可靠解析时对应字段为 `null` 并出现在 `unresolved_fields`；只要结构化解析成功就返回 200，由用户手动补齐。模型调用失败返回 `GENERATION_FAILED` 502，schema 无效返回 `GENERATION_SCHEMA_INVALID` 500。

#### `POST /api/v1/study-plans/{plan_id}/regeneration-previews`

请求与 preview 相同，但字段均可省略；省略字段继承已保存计划配置。响应为完整 `StudyPlanPreview`，不写数据库。计划已删除、跨用户或不存在返回 `NOT_FOUND`；已有进度返回 `STATE_CONFLICT` 409。

#### `PUT /api/v1/study-plans/{plan_id}`

请求为完整 `StudyPlanReplaceRequest`，包含 `expected_updated_at`、配置和最终任务树：

```json
{
  "expected_updated_at": "2026-07-10T10:00:00+00:00",
  "title": "传输层冲刺计划",
  "goal_text": "掌握传输层",
  "start_date": "2026-07-11",
  "end_date": "2026-07-20",
  "daily_available_minutes": 60,
  "preference": "fast_track",
  "material_scope": {
    "include_all_parsed_materials": true,
    "folder_ids": [],
    "material_ids": []
  },
  "tasks": []
}
```

`tasks` 必须至少一项。响应为替换后的 `StudyPlanBundleRead`。`expected_updated_at` 不匹配、已有执行进度或任务绑定生成内容时返回 `STATE_CONFLICT` 409。

#### `DELETE /api/v1/study-plans/{plan_id}`

无 body。响应：

```json
{
  "id": "sp_1",
  "status": "deleted",
  "deleted_at": "2026-07-10T12:00:00+00:00"
}
```

### 3.4 前端接入状态

- 当前四接口可继续由 F07 使用，但真实计划新字段在契约合并前不得接入。
- 本任务四个新增/扩展接口均属于“后端未实现候选”；必须先合并 `contracts.md` 和 OpenAPI schema，再由前端负责人更新类型。

## 4. 测试计划

### 4.1 service 测试

`backend/tests/modules/study_plans/test_study_plan_lifecycle.py` 覆盖：

- 自然语言字段完整解析与缺失字段回填。
- 两份资料、三个 batch 全部进入 map；结果 `expected == processed`。
- 任一资料未覆盖返回 `MATERIAL_COVERAGE_INCOMPLETE`。
- provider 失败与 schema 失败映射稳定错误码。
- 调整预览后保存的标题、日期、排序、任务类型和材料 ID 与请求一致。
- 同幂等键同请求返回同一 plan；同键不同请求冲突。
- 在第二个子任务 flush 时注入异常，断言计划/任务/子任务均未落库。
- 替换无进度计划成功；有已完成子任务或已绑定生成内容时冲突。
- 重生成不改变数据库；删除后 list/detail 均隐藏。
- 跨用户计划、课程、材料访问返回 `NOT_FOUND`。

### 4.2 API 与集成测试

`backend/tests/modules/study_plans/test_study_plan_lifecycle_api.py` 覆盖 401、422、404、409、成功 envelope 和兼容旧请求。

`backend/tests/integration/test_full_material_plan_flow.py` 使用 Fake `ModelProvider` 和多份已解析资料，断言：

- preview 处理所有材料；
- 保存只新增计划三级结构，`ai_generated_contents` 数量仍为 0；
- list/detail 返回同一结构；
- regeneration preview 后 `PUT` 原子替换；
- 删除后聚合前置查询看不到计划。

### 4.3 命令与预期

```powershell
cd backend
conda run -n course-nexus python -m pytest tests/modules/study_plans/test_study_plan_lifecycle.py -q
conda run -n course-nexus python -m pytest tests/modules/study_plans/test_study_plan_lifecycle_api.py -q
conda run -n course-nexus python -m pytest tests/integration/test_full_material_plan_flow.py -q
conda run -n course-nexus python -m pytest tests/modules/study_plans tests/integration/test_material_context_to_plan_flow.py -q
```

预期：全部命令退出码为 0；测试无 live network；旧 preview/save/list/detail 回归继续通过；失败注入后数据库无半保存记录。

## 5. 验收标准

### 5.1 自动化验收

- [ ] 自然语言解析结果可编辑且缺失项明确。
- [ ] 多资料、多 batch 覆盖集合完全一致。
- [ ] 保存和替换均只有一次 commit，失败完全 rollback。
- [ ] 幂等重放不创建重复计划。
- [ ] 保存阶段没有 `handout` 或 `task_test` 记录。
- [ ] 跨用户、已删除、状态冲突和 schema 失败测试通过。

### 5.2 人工验收

- [ ] 使用两份真实已解析材料生成 3 天计划，预览每天任务可手动调整并成功保存。
- [ ] 保存后进入详情，字段与最终确认预览一致。
- [ ] 未开始计划可重生成、替换；已有完成进度时明确拒绝替换。
- [ ] 删除后课程计划列表不再显示，数据库保留软删除记录。
- [ ] 前端负责人确认只在契约合并后开始接新增字段和路径。

## 6. 交付物

- `planner.py`、更新后的 study plan router/schema/service/repository。
- 三个精确测试文件及回归测试调整。
- API、数据、架构、当前状态文档。
- 中文真实材料验收记录 `docs/planning/phase-1-validation/S02-plan-lifecycle.md`。
- 建议独立提交：`feat(study-plans): 支持自然语言配置回填`；`feat(study-plans): 基于全材料生成可调整预览`；`fix(study-plans): 原子保存计划任务结构`；`feat(study-plans): 支持计划替换重生成与删除`。

## 7. 文档同步

- 新建或更新 `docs/domains/study-mode/plan-lifecycle.md`：记录 router/service/repository/provider 分层和代码入口、目标解析与全材料计划生成数据流、prompt/schema、map/reduce 覆盖、任务排程算法及伪代码、预览到保存的幂等策略、编辑/重生成替换事务、不变量、复杂度与批次/token 预算、失败补偿和测试证据。
- 产品行为没有改变，不改 PRD 原意；若最终偏好枚举经产品调整，再同步对应 PRD 字段章节。
- 更新 `docs/architecture/runtime-flows.md`：真实全材料计划生成、确认后保存和替换事务。
- 更新 `docs/api-data/contracts.md`、`api-conventions.md`：新增路径、请求、响应、幂等和错误码。
- 更新 `docs/api-data/data-model.md`、`table-schema.md`：说明 `parsed_config_json` 的精确结构，不增加列。
- 更新 `docs/planning/current-state.md`、`tech-debt-tracker.md`：关闭 AI 计划占位缺口。
- 不直接修改 `docs/api-data/frontend-integration.md`，向前端负责人提交契约变更清单。

## 8. 冲突与注意事项

### 8.1 冲突点

- `study_plans/**` 为本任务独占；不要格式化其他模块。
- `ModelProvider` 只消费当前公共协议，不从 `course_qa.router` 导入依赖函数。
- `material_context` 是公共边界，本任务只调用公开函数，不修改其 repository 或私有 scope 解析。
- 前端 F07 可能同时使用旧接口；扩展必须保持旧 body 可解析。

### 8.2 严格遵循项

- 全材料计划必须使用 `iter_material_context_batches()` 和 `run_material_coverage()`。
- 用户最终确认的配置和任务树优先于自然语言解析结果。
- 权限查询同时包含当前 `user_id`，跨用户不泄露存在性。
- 所有任务日期、排序、类型、材料关联在写库前完成 schema 和 service 双层校验。

### 8.3 一定不能做的事

- 不能继续使用 `resolve_context(limit=20)` 生成正式计划。
- 不能在预览阶段写 draft 计划或生成讲义/测试题。
- 不能用多个 repository commit 拼接一份计划。
- 不能在已有执行进度时静默删除并替换任务。
- 不能新增表、修改 migration、调用 OpenAI SDK 或直接查询 Chroma。
- 不能修改五类生成器、前端或首页聚合模块。

## 9. 完成检查表

- [ ] 实现范围全部完成。
- [ ] 当前四 API 保持兼容。
- [ ] 新增 API 请求、响应和错误码与契约一致。
- [ ] 全材料覆盖、事务、幂等、权限和冲突测试通过。
- [ ] 自动化测试不访问 live network。
- [ ] 人工真实材料验收有中文记录。
- [ ] 文档同步完成。
- [ ] `git diff --check` 通过。
- [ ] 修改文件未越过所有权边界。
- [ ] 每个可验证小功能已独立提交。
