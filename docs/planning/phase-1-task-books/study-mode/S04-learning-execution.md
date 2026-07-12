# S04 计划学习执行与任务完成

## 0. 业务功能说明

- **业务场景**：学生从今日待办或课程日历进入某个二级任务，需要专注查看当天任务并记录实际完成情况。
- **用户能力**：查看当前日期的一级任务、二级任务和关联资料；将二级任务标记为完成或取消完成。
- **业务结果**：二级任务变化会自动汇总一级任务和整个计划状态，并同步当天学习完成比例；重复点击不会重复累计。
- **业务边界**：本任务不生成学习计划、讲义或测试题，不允许直接完成一级任务，也不返回整棵计划树干扰当天学习。

## 1. 任务信息

- 编号与名称：`S04` 计划学习执行与任务完成。
- 负责人角色：计划学习模式后端开发者。
- 目标：提供单个二级任务的执行上下文，并以幂等方式完成或取消完成二级任务，原子汇总一级任务、计划状态和当日打卡。
- 前置依赖：S01 状态与事务契约；S02 计划三级结构；S03 跳转 ID 契约；S05 必须在 S04 完成接口合并前提供 `recalculate_checkin()` 公共函数。
- 实施顺序：先完成执行上下文和纯状态汇总函数；再完成 S05 打卡重算；最后接通 completion 事务和 API。该顺序避免在学习执行模块内复制打卡规则。
- 范围外事项：不生成计划、讲义或任务测试题；不提供一级任务直接完成接口；不实现任务问答；不修改前端。

## 2. 实现范围

### 2.1 执行上下文

1. 通过 `subtask_id` 查询当前用户可访问的二级任务、父一级任务、计划和课程；计划/课程已删除均按不存在处理。
2. `execution_date` 使用父任务 `task_date`，不强制等于服务器当天，使用户可从日历进入历史或未来任务。
3. 左侧任务节点只返回同一计划、同一 `task_date` 下的一级任务和二级任务，不返回完整计划日期树。
4. 当前二级任务返回类型、描述、状态、完成时间和关联资料摘要。
5. `related_material_ids_json` 必须是字符串数组；查询时再次校验资料属于当前用户和课程。已删除资料保留 ID 和名称快照能力不足时返回 `availability = deleted`，不得把其他课程资料返回。
6. S04 响应预留 `handout_content_id`、`task_test_content_id`；S04 单独验收时固定返回 `null`。当前 S06 已接入，execution-context 通过 generated-content 查询填充当前二级任务最近一次 success 内容 ID；无 success 时为 `null`，failed 记录不作为内容 ID。

### 2.2 完成状态与汇总

- 请求使用期望状态 `completed: boolean`，而不是 toggle；重复发送同一请求得到同一结果。
- `completed = true`：二级任务状态设为 `completed`，`completed_at` 写当前 UTC datetime。
- `completed = false`：二级任务状态设为 `not_started`，`completed_at = null`。
- 本任务不通过完成接口写二级任务 `in_progress`；该状态只作为未来执行过程状态和汇总输入保留。
- 一级任务汇总：所有子任务 `completed` -> `completed`；所有子任务 `not_started` -> `not_started`；其他组合 -> `in_progress`。
- 计划汇总：所有一级任务 `completed` -> `completed`；否则保持/改为 `active`；`deleted` 计划不可操作。
- 每次请求都调用 S05 `recalculate_checkin(db, user_id, checkin_date=task.task_date, flush_only=True)`。即使二级任务状态没有变化也重算，以修复派生记录漂移。
- 响应返回 `changed`，只表示二级任务事实是否改变，不影响重算执行。

### 2.3 单事务规则

一次 completion 请求按以下顺序执行，且只有最后一步 `db.commit()`：

1. 查询并校验当前用户、计划、任务和二级任务。
2. 写入二级任务期望状态并 `flush()`。
3. 读取父任务全部二级任务并汇总一级任务状态，`flush()`。
4. 读取计划全部一级任务并汇总计划状态，`flush()`。
5. 调用 `recalculate_checkin(..., flush_only=True)` 完成同日唯一 upsert，`flush()`。
6. `commit()`，刷新响应对象。

任一步异常必须 `rollback()`；任务状态、计划状态和打卡要么全部更新，要么全部保持原值。

### 2.4 精确文件边界

创建：

- `backend/app/modules/learning_execution/schemas.py`。
- `backend/app/modules/learning_execution/repository.py`。
- `backend/app/modules/learning_execution/service.py`。
- `backend/app/modules/learning_execution/router.py`。
- `backend/tests/modules/learning_execution/test_learning_execution_service.py`。
- `backend/tests/modules/learning_execution/test_learning_execution_api.py`。
- `backend/tests/integration/test_subtask_completion_transaction.py`。

修改：

- `backend/app/modules/learning_execution/__init__.py`。
- `backend/app/api/router.py`：只注册 learning execution router。

只读依赖：

- `backend/app/modules/study_plans/models.py`。
- `backend/app/modules/materials/models.py`。
- S05 的 `backend/app/modules/checkins/service.py` 公共函数。

禁止修改：

- `backend/app/modules/study_plans/models.py`、S02 计划生成逻辑。
- `backend/app/modules/todos_calendar/**`。
- `backend/app/modules/generated_content/**`、`generation/**`、`exports/**`。
- `backend/migrations/**`、`frontend/**`。

## 3. 字段与接口

### 3.1 新增 Pydantic 类型

- `ExecutionMaterialRead`：`material_id`、`name`、`material_type`、`parse_status`、`availability`。
- `ExecutionSubTaskRead`：`subtask_id`、`title`、`subtask_type`、`description`、`status`、`completed_at`、`sort_order`。
- `ExecutionTaskRead`：`task_id`、`title`、`task_date`、`status`、`sort_order`、`subtasks`。
- `ExecutionContextRead`：课程、计划、执行日期、当日任务、当前二级任务、材料摘要及生成内容 ID。
- `SubTaskCompletionUpdate`：`completed: bool`。
- `SubTaskCompletionResult`：`changed`、二级任务、一级任务、计划与 `CheckinRead` 摘要。

### 3.2 当前已实现 API

本任务开始前没有 `learning_execution` router。S03 返回的 `course_id`、`plan_id`、`task_id`、`subtask_id` 仅是跳转参数，不提供写能力。

### 3.3 本任务新增 API

#### `GET /api/v1/study-subtasks/{subtask_id}/execution-context`

响应 `data`：

```json
{
  "course": {"course_id": "crs_1", "name": "计算机网络"},
  "plan": {"plan_id": "sp_1", "title": "传输层计划", "status": "active"},
  "execution_date": "2026-07-10",
  "tasks": [
    {
      "task_id": "tsk_1",
      "title": "可靠传输",
      "task_date": "2026-07-10",
      "status": "in_progress",
      "sort_order": 1,
      "subtasks": [
        {
          "subtask_id": "sub_1",
          "title": "理解滑动窗口",
          "subtask_type": "learn",
          "description": "学习窗口推进",
          "status": "not_started",
          "completed_at": null,
          "sort_order": 1
        }
      ]
    }
  ],
  "current_subtask_id": "sub_1",
  "related_materials": [
    {
      "material_id": "mat_1",
      "name": "传输层课件.pdf",
      "material_type": "pdf",
      "parse_status": "parsed",
      "availability": "available"
    }
  ],
  "handout_content_id": null,
  "task_test_content_id": null
}
```

错误：`UNAUTHORIZED` 401、`NOT_FOUND` 404、`STATE_CONFLICT` 409（任务层级 ID/课程冗余字段不一致）、`VALIDATION_ERROR` 422（关联材料 JSON 结构损坏）。

#### `PUT /api/v1/study-subtasks/{subtask_id}/completion`

请求：

```json
{
  "completed": true
}
```

响应 `data`：

```json
{
  "changed": true,
  "subtask": {
    "subtask_id": "sub_1",
    "status": "completed",
    "completed_at": "2026-07-10T12:00:00+00:00"
  },
  "task": {
    "task_id": "tsk_1",
    "status": "in_progress",
    "completed_subtask_count": 1,
    "total_subtask_count": 2
  },
  "plan": {"plan_id": "sp_1", "status": "active"},
  "checkin": {
    "checkin_date": "2026-07-10",
    "total_subtask_count": 5,
    "completed_subtask_count": 2,
    "completion_ratio": "0.4000",
    "color_level": 2
  }
}
```

重复同一请求返回 200、`changed = false`、相同状态和重算后的打卡。取消完成把 `completed` 设为 `false`。错误：`UNAUTHORIZED` 401、`NOT_FOUND` 404、`STATE_CONFLICT` 409、`VALIDATION_ERROR` 422。

### 3.4 后端未实现与占位字段

- S04 合并前两个路径均未实现，前端不得自行直接更新计划详情对象。
- `handout_content_id`、`task_test_content_id` 在 S04 单独验收时为 `null`；S06 合并后由 execution-context 返回当前二级任务最近一次成功生成内容 ID，没有成功内容时才为 `null`。
- 前端完成按钮必须等 completion 契约合并后再接；不允许用本地计数代替服务端打卡结果。

## 4. 测试计划

### 4.1 service 测试

`backend/tests/modules/learning_execution/test_learning_execution_service.py`：

1. execution context 只返回同一计划同一日期任务，不返回前后日期。
2. 关联材料只包含同课程资料；删除资料返回 `availability = deleted`；跨课程 ID 触发冲突。
3. 完成一个子任务：子任务完成、父任务部分完成、计划 active。
4. 完成父任务最后一个子任务：父任务 completed；完成计划最后一个任务后计划 completed。
5. 取消一个已完成子任务：父任务回到 in_progress/not_started，计划从 completed 回到 active。
6. 重复完成和重复取消：`changed = false`，计数不重复累计。
7. 输入已有 `in_progress` 子任务参与父级汇总，结果为 in_progress。
8. 跨用户、软删除计划、已删除课程均返回 `NOT_FOUND`。

### 4.2 API 与事务测试

`backend/tests/modules/learning_execution/test_learning_execution_api.py` 覆盖两个 API 的 200/401/404/409/422、统一 envelope 和时间字段。

`backend/tests/integration/test_subtask_completion_transaction.py`：

- 完成后立即查询 S03 今日待办、月历、当日弹窗和 S05 打卡，状态一致。
- 在打卡 flush 前注入异常，断言子任务、父任务、计划和原打卡全部未改变。
- 两次相同 completion 请求只存在一条 `(user_id, task_date)` 打卡记录。

### 4.3 命令与预期

```powershell
cd backend
conda run -n course-nexus python -m pytest tests/modules/learning_execution/test_learning_execution_service.py -q
conda run -n course-nexus python -m pytest tests/modules/learning_execution/test_learning_execution_api.py -q
conda run -n course-nexus python -m pytest tests/integration/test_subtask_completion_transaction.py -q
conda run -n course-nexus python -m pytest tests/modules/todos_calendar tests/modules/checkins tests/modules/learning_execution -q
```

预期：所有测试退出码 0；失败注入场景四类记录均保持原值；重复请求不增加打卡行数；无 live network。

## 5. 验收标准

### 5.1 自动化验收

- [ ] 执行上下文只包含所选任务日期。
- [ ] 完成与取消完成均幂等。
- [ ] 一级任务与计划汇总规则逐种组合通过。
- [ ] completion 与打卡更新处于同一事务。
- [ ] S03 下一次查询反映新状态，无同步写调用。
- [ ] 跨用户、软删除和层级不一致被拒绝。

### 5.2 人工验收

- [ ] 从今日待办点击二级任务，执行页左侧只显示该日期任务。
- [ ] 勾选一个二级任务后一级任务显示部分完成，打卡比例同步变化。
- [ ] 再次勾选不重复累计；取消完成后比例下降。
- [ ] 完成计划最后一个二级任务后计划状态变为 completed。
- [ ] 断开打卡写入并重试，失败请求不留下部分状态。

## 6. 交付物

- `learning_execution` schema/repository/service/router。
- service/API/事务集成测试。
- API、架构、当前状态文档更新。
- 中文验收记录 `docs/domains/study-mode/validation/S04-learning-execution.md`。
- 建议独立提交：`feat(execution): 新增当日任务执行上下文`；`feat(execution): 幂等更新二级任务完成状态`；`fix(execution): 原子汇总任务计划与打卡`。

## 7. 文档同步

- 新建或更新 `docs/domains/study-mode/learning-execution.md`：记录执行模块分层和代码入口、今日任务查询与完成写入数据流、期望状态幂等算法、二级到一级再到计划的状态聚合算法及伪代码、同事务打卡联动顺序、并发/回滚/补偿策略、复杂度和测试证据。
- 更新 `docs/architecture/module-boundaries.md`、`runtime-flows.md`：learning execution 写入范围和事务顺序。
- 更新 `docs/api-data/contracts.md`、`api-conventions.md`：两个接口、幂等、错误码和时间语义。
- 更新 `docs/api-data/data-model.md`：一级任务/计划派生状态规则；表结构不变。
- 更新 `docs/planning/current-state.md`。
- 不改 PRD 原意，不直接修改 `frontend-integration.md`；由前端负责人接收合并后的契约。

## 8. 冲突与注意事项

### 8.1 冲突点

- S05 拥有打卡计算规则；S04 只调用其公开 `recalculate_checkin()`，不能复制颜色阈值。
- S03 只读同一状态；S04 不调用 S03 service，也不维护聚合缓存。
- S06 将填充两个 generated content ID；S04 先保留 null 字段，不修改生成模块。
- `backend/app/api/router.py` 只追加 router include，不覆盖并行变更。

### 8.2 严格遵循项

- 权限必须从二级任务追溯计划 `user_id` 和课程归属。
- 客户端提交期望完成状态，不提交父任务或计划状态。
- 所有派生写入一次 commit，异常全部 rollback。
- `completed_at` 使用 UTC datetime，打卡日期使用父任务业务日期。

### 8.3 一定不能做的事

- 不能提供一级任务直接完成 API。
- 不能用 toggle 语义实现 completion。
- 不能在 repository 内分段 commit。
- 不能在学习执行模块复制打卡颜色阈值或创建第二条同日记录。
- 不能返回完整计划树、生成讲义/测试题、修改计划生成器或新增表。
- 不能修改前端或五类独立生成器。

## 9. 完成检查表

- [ ] 实现范围全部完成。
- [ ] S05 公共重算函数已集成。
- [ ] 两个 API 契约与错误码一致。
- [ ] 幂等、汇总、事务、权限和软删除测试通过。
- [ ] S03/S05 相邻模块回归通过。
- [ ] 文档同步完成。
- [ ] `git diff --check` 通过。
- [ ] 修改文件未越过所有权边界。
- [ ] 每个可验证小功能已独立提交。
