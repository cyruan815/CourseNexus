# S03 今日待办与日历聚合

## 0. 业务功能说明

- **业务场景**：学生保存多门课程的单课程计划后，需要在首页知道今天学什么，并在日历中查看未来和历史任务。
- **用户能力**：查看首页今日待办、首页大日历、某一天按课程和一级任务分组的全部任务，以及课程详情页中当前课程今天的计划任务。
- **业务结果**：多个单课程计划按日期聚合展示，学生可以从首页或日历直接进入对应任务的计划执行页。
- **业务边界**：今日待办和日历只负责查看、汇总和跳转，不创建、编辑、删除或重新生成计划，也不新增待办或日历业务表。

## 1. 任务信息

- 编号与名称：`S03` 今日待办与日历聚合。
- 负责人角色：计划学习模式后端开发者。
- 目标：基于现有计划、一级任务和二级任务提供首页今日待办、全局月历、全局当日待办、课程月历和课程当日任务五类只读投影，并支撑前端的折叠、跳转和计划详情入口。
- 前置依赖：S01 子系统契约已合并；S02 保存的任务层级、日期、排序和软删除规则稳定；当前用户与课程归属依赖可用。
- 范围外事项：不创建、编辑、重生成或删除计划；不更新任务状态；不写打卡；不创建待办或日历表；不实现前端页面。

## 2. 实现范围

### 2.1 只读聚合规则

1. 所有数据从 `study_plans -> study_tasks -> study_subtasks` 联表派生。
2. 默认排除 `StudyPlan.status = deleted`、`StudyPlan.deleted_at is not null`、已删除课程和非当前用户课程。
3. `active` 与 `completed` 计划的历史任务都可查询；完成态不等于隐藏。
4. 首页今日待办以一级任务为列表项，返回所属课程、计划、二级任务计数、二级任务列表与跳转所需 ID；前端默认折叠二级任务，点击一级任务卡片只展开/折叠，点击二级任务才进入计划学习执行页。
5. 首页今日待办和当日详情的稳定排序固定为 `course_name`、一级任务 `sort_order`、二级任务 `sort_order`。
6. 全局月历每个日期返回课程数、一级任务数、二级任务数、已完成二级任务数和派生状态，同时返回最多 3 条一级任务摘要；超出部分用 `hidden_task_count` 表示，不返回完整二级任务树。
7. 全局当日待办按课程分组；课程内按一级任务分组，每个一级任务携带可折叠的二级任务列表和计划详情所需 `plan_id`。
8. 课程月历只读取路径中的 `course_id`；课程当日查询只返回该课程任务。
9. 课程详情页使用课程当日查询展示“当前课程今天的一级任务和二级任务”，同一课程同一天有多个一级任务时先按一级任务分组再显示二级任务；前端默认展开二级任务，不在 S03 支持切换其他日期。
10. 日期为空时返回空数组或零摘要，不返回 404。
11. 所有日期参数使用 `YYYY-MM-DD`，月份使用 `YYYY-MM`；无效日期返回 `VALIDATION_ERROR`。
12. 派生状态算法固定：二级任务总数为 0 时一级任务摘要为 `not_started`；完成数为 0 是 `not_started`；完成数等于总数是 `completed`；其余是 `in_progress`。查询结果同时返回数据库状态，若二者不一致，测试失败并记录一致性错误，不在只读查询中修复。
13. S04 更新事务提交后，下一次聚合查询自然反映新状态；本模块不维护缓存和同步表。
14. 大日历日期弹窗中的“计划详情”按钮复用既有 `GET /api/v1/study-plans/{plan_id}` 计划详情接口；S03 不新增计划详情接口。

### 2.2 精确文件边界

创建：

- `backend/app/modules/todos_calendar/schemas.py`。
- `backend/app/modules/todos_calendar/repository.py`。
- `backend/app/modules/todos_calendar/service.py`。
- `backend/app/modules/todos_calendar/router.py`。
- `backend/tests/modules/todos_calendar/test_todos_calendar_service.py`。
- `backend/tests/modules/todos_calendar/test_todos_calendar_api.py`。

修改：

- `backend/app/modules/todos_calendar/__init__.py`：仅导出模块公共符号。
- `backend/app/api/router.py`：注册 `todos_calendar.router`，不调整其他 router 顺序和实现。
- `backend/tests/integration/test_course_workspace_flow.py`：只追加保存计划后查询聚合的回归，若该文件同期被他人修改则创建 `backend/tests/integration/test_plan_calendar_flow.py`，不得覆盖他人内容。

禁止修改：

- `backend/app/modules/study_plans/**` 的写逻辑。
- `backend/app/modules/learning_execution/**`、`checkins/**`、`generation/**`、`exports/**`。
- `backend/app/db/models.py`、`backend/migrations/**`、`frontend/**`。

### 2.3 repository 与 service 边界

- repository 可使用 SQLAlchemy ORM/Core 完成分组计数，但必须显式过滤 `user_id`、计划软删除和课程删除。
- repository 返回内部 dataclass/row，不返回 HTTP dict。
- service 负责派生状态、按课程分组和 Pydantic 输出，不执行任何 `add`、`delete`、`flush`、`commit`。
- router 只解析 path/query、注入当前用户和 session，并使用统一 success envelope。

## 3. 字段与接口

### 3.1 类型

新增 Pydantic 类型：

- `SubTaskTodoRead`：`subtask_id`、`title`、`subtask_type`、`description`、`status`、`sort_order`、`execution_url`。
- `TaskTodoRead`：`task_id`、`plan_id`、`course_id`、`course_name`、`title`、`task_date`、`status`、`derived_status`、`completed_subtask_count`、`total_subtask_count`、`first_incomplete_subtask_id`、`subtasks`。
- `CourseTodoGroupRead`：`course_id`、`course_name`、`plan_ids`、`tasks`。
- `CalendarTaskSummaryRead`：`task_id`、`plan_id`、`course_id`、`course_name`、`title`、`status`、`derived_status`、`sort_order`。
- `CalendarDaySummaryRead`：`date`、`course_count`、`task_count`、`subtask_count`、`completed_subtask_count`、`status`、`task_summaries`、`hidden_task_count`。
- `CalendarMonthRead`：`month`、`days`。

所有集合空值固定返回 `[]`；计数固定返回整数 `0`。`execution_url` 可由后端返回稳定路径，也可返回 `null` 交给前端按 `subtask_id` 拼接；本任务必须至少提供二级任务跳转所需 ID。

### 3.2 当前已实现 API

本任务开始前没有 `todos_calendar` API。现有 plan list/detail 只作为数据来源，不改变请求和响应。

### 3.3 本任务新增 API

#### `GET /api/v1/todos/today?date=2026-07-10`

- `date` 可选；省略时按 `Asia/Shanghai` 当前自然日。
- 响应按 `course_name`、一级任务 `sort_order`、二级任务 `sort_order` 稳定排序。
- 首页前端默认折叠 `subtasks`；点击一级任务卡片只展开/折叠，点击二级任务进入计划学习执行页。

```json
{
  "date": "2026-07-10",
  "tasks": [
    {
      "task_id": "tsk_1",
      "plan_id": "sp_1",
      "course_id": "crs_1",
      "course_name": "计算机网络",
      "title": "可靠传输",
      "task_date": "2026-07-10",
      "status": "in_progress",
      "derived_status": "in_progress",
      "completed_subtask_count": 1,
      "total_subtask_count": 2,
      "first_incomplete_subtask_id": "sub_2",
      "subtasks": [
        {
          "subtask_id": "sub_1",
          "title": "理解滑动窗口",
          "subtask_type": "learn",
          "description": "学习窗口推进",
          "status": "completed",
          "sort_order": 1,
          "execution_url": null
        }
      ]
    }
  ]
}
```

`first_incomplete_subtask_id` 在全部完成或无二级任务时为 `null`。错误：`UNAUTHORIZED` 401、`VALIDATION_ERROR` 422。

#### `GET /api/v1/calendar/month?month=2026-07`

响应：

```json
{
  "month": "2026-07",
  "days": [
    {
      "date": "2026-07-10",
      "course_count": 2,
      "task_count": 5,
      "subtask_count": 12,
      "completed_subtask_count": 4,
      "status": "in_progress",
      "task_summaries": [
        {
          "task_id": "tsk_1",
          "plan_id": "sp_1",
          "course_id": "crs_1",
          "course_name": "计算机网络",
          "title": "可靠传输",
          "status": "in_progress",
          "derived_status": "in_progress",
          "sort_order": 1
        }
      ],
      "hidden_task_count": 2
    }
  ]
}
```

只返回当月至少有一个一级任务的日期；`task_summaries` 最多 3 条，`hidden_task_count = task_count - task_summaries.length`；无任务月份 `days = []`。错误：`UNAUTHORIZED` 401、`VALIDATION_ERROR` 422。

#### `GET /api/v1/calendar/days/{date}/todos`

响应：

```json
{
  "date": "2026-07-10",
  "courses": [
    {
      "course_id": "crs_1",
      "course_name": "计算机网络",
      "plan_ids": ["sp_1"],
      "tasks": [
        {
          "task_id": "tsk_1",
          "plan_id": "sp_1",
          "course_id": "crs_1",
          "course_name": "计算机网络",
          "title": "可靠传输",
          "task_date": "2026-07-10",
          "status": "in_progress",
          "derived_status": "in_progress",
          "completed_subtask_count": 1,
          "total_subtask_count": 2,
          "first_incomplete_subtask_id": "sub_2",
          "subtasks": [
            {
              "subtask_id": "sub_1",
              "title": "理解滑动窗口",
              "subtask_type": "learn",
              "description": "学习窗口推进",
              "status": "completed",
              "sort_order": 1,
              "execution_url": null
            }
          ]
        }
      ]
    }
  ]
}
```

无任务日期 `courses = []`。大日历日期弹窗使用本接口展示当日待办；一级任务卡片负责展开/折叠二级任务，一级任务上的计划详情按钮使用 `plan_id` 调用既有学习计划详情接口。错误：`UNAUTHORIZED` 401、`VALIDATION_ERROR` 422。

#### `GET /api/v1/courses/{course_id}/study-calendar?month=2026-07`

响应字段与全局月历相同，但增加 `course_id`、`course_name`，且 `course_count` 固定为 `1`。课程不存在、已删除或跨用户返回 `NOT_FOUND` 404；无任务月份返回空 `days`。

#### `GET /api/v1/courses/{course_id}/study-calendar/days/{date}`

响应：

```json
{
  "course_id": "crs_1",
  "course_name": "计算机网络",
  "date": "2026-07-10",
  "tasks": []
}
```

`tasks` 使用完整 `TaskTodoRead`，包含二级任务。该接口服务课程详情页“今日任务”区域，前端默认以今天作为 `date` 调用，并默认展开二级任务；S03 不实现课程详情页日期切换。错误：`NOT_FOUND` 404、`VALIDATION_ERROR` 422、`UNAUTHORIZED` 401。

### 3.4 后端未实现与前端接入

- 上述五个路径在本任务合并前均为后端未实现候选。
- 前端首页、全局日历和课程日历必须等待 `contracts.md` 与 router 合并后再接入；等待期间只能显示明确占位，不得从计划详情自行拼出跨课程假数据。
- 本任务不提供任何 POST/PATCH/PUT/DELETE 待办或日历接口。`计划详情` 按钮复用既有学习计划详情接口，由前端根据 `plan_id` 打开左右展开弹窗：左侧展示当日一二级任务，右侧展示完整计划起止日期和任务树。

## 4. 测试计划

### 4.1 service 测试文件与场景

`backend/tests/modules/todos_calendar/test_todos_calendar_service.py`：

1. 两用户、三课程、多个计划同日任务只返回当前用户数据。
2. 今日待办聚合多个单课程计划，返回一级任务、二级任务列表、计数、状态、首个未完成子任务正确，能支撑前端默认折叠。
3. 月份边界覆盖月初、月末和闰年二月，不包含相邻月份。
4. 全局日历按日期去重课程数，不把同课程两个计划计为两门课程；日期格只返回最多 3 条一级任务摘要和正确的 `hidden_task_count`。
5. 全局当日待办按课程分组，任务/子任务排序稳定，顺序为 `course_name -> task.sort_order -> subtask.sort_order`。
6. 课程日历只返回指定课程；课程当日查询返回当前课程当天的一级任务和二级任务，支持同日多个一级任务分组。
7. 无任务日期、无任务月份返回空集合。
8. 软删除计划、已删除课程及其任务全部隐藏。
9. `status` 与子任务派生状态不一致时 service 抛 `STATE_CONFLICT`，证明只读层不静默修复。
10. 同一课程同一天存在多个计划时，响应保留 `plan_id` 供计划详情按钮使用，但不要求展示 `plan_title`。
11. 对 service 调用前后比较 session `new/dirty/deleted` 均为空，数据库行数不变。

### 4.2 API 测试文件与场景

`backend/tests/modules/todos_calendar/test_todos_calendar_api.py`：

- 五个 API 的 success envelope、空状态、401、404、422。
- `/todos/today` 返回一级任务和二级任务数组，且不返回需要前端展示的计划名字段。
- `/calendar/month` 的 `task_summaries` 最多 3 条，`hidden_task_count` 正确。
- `/courses/{course_id}/study-calendar/days/{date}` 能作为课程详情页今日任务数据源。
- 非法 `date=2026-02-30`、`month=2026-13` 返回 `VALIDATION_ERROR`。
- 跨用户课程返回 `NOT_FOUND`，响应不泄露课程名。
- 查询完成前后不新增任何表记录。

### 4.3 命令与预期

```powershell
cd backend
conda run -n course-nexus python -m pytest tests/modules/todos_calendar/test_todos_calendar_service.py -q
conda run -n course-nexus python -m pytest tests/modules/todos_calendar/test_todos_calendar_api.py -q
conda run -n course-nexus python -m pytest tests/modules/study_plans tests/modules/todos_calendar -q
```

预期：全部测试退出码 0；聚合查询前后业务表行数相同；没有网络调用；旧计划 API 回归通过。

## 5. 验收标准

### 5.1 自动化验收

- [ ] 今日待办能合并当前用户多个单课程计划，并返回可折叠二级任务数据。
- [ ] 月历日期格只返回最多 3 条一级任务摘要和 `hidden_task_count`，不包含完整二级任务数组。
- [ ] 全局当日查询按课程和一级任务分组，并带二级任务执行跳转 ID 与计划详情 `plan_id`。
- [ ] 课程日历不会返回其他课程任务；课程详情页今日任务能展示当前课程当天的一二级任务。
- [ ] 空日期、空月份、软删除、跨用户和非法日期测试通过。
- [ ] 所有查询零写入、零 commit。

### 5.2 人工验收

- [ ] 准备两门课程同日任务，首页今日待办同时显示两门课的一级任务，展开后能看到二级任务。
- [ ] 月历日期格可看到课程数、任务数、完成摘要和最多 3 条一级任务标题，点击日期后弹窗数据按课程和一级任务分组。
- [ ] 课程详情页今日任务只看到当前课程当天的一二级任务，二级任务默认展开。
- [ ] 删除一个计划后刷新三类视图，该计划任务全部消失。
- [ ] 大日历当日弹窗的计划详情按钮可用 `plan_id` 复用既有学习计划详情接口，前端负责人确认按已合并字段接入，不从中文文案推导状态。

## 6. 交付物

- `todos_calendar` 的 schema/repository/service/router。
- service/API 测试和计划聚合集成回归。
- API、架构、当前状态文档更新。
- 中文验收记录 `docs/domains/study-mode/validation/S03-todos-calendar.md`。
- 建议独立提交：`feat(todos): 新增今日待办只读聚合`；`feat(calendar): 新增全局月历与当日分组查询`；`feat(calendar): 新增课程计划日历查询`。

## 7. 文档同步

- 新建或更新 `docs/domains/study-mode/todos-calendar.md`：记录只读聚合模块分层和代码入口、五类查询的数据流、用户/课程过滤、日期边界、分组与排序算法及伪代码、空集合不变量、SQL/索引使用、查询次数与时间/空间复杂度、失败策略和测试证据。
- 更新 `docs/architecture/module-boundaries.md`、`runtime-flows.md`：明确 `todos-calendar` 零写模型。
- 更新 `docs/api-data/contracts.md`、`api-conventions.md`：五个 GET 路径、日期格式、空集合、错误码、首页折叠所需二级任务数组、月历 3 条摘要和 `hidden_task_count`。
- `table-schema.md` 只补充查询索引使用说明，不新增表或列。
- 更新 `docs/planning/current-state.md`。
- 如本任务实现后仍与产品 PRD 或前端接入口径存在差异，需要同步产品/接口文档；本任务书记录的是 S03 当前确认口径。
- 不直接修改 `frontend-integration.md`，向前端负责人交付已合并接口示例。

## 8. 冲突与注意事项

### 8.1 冲突点

- `backend/app/api/router.py` 是共享热点，只添加一次 include，不重排其他 Agent 的 router。
- S04 会写同一任务状态；S03 repository 必须只读，双方通过表状态契约交接。
- 前端会并行实现页面；前端必须等后端契约合并。

### 8.2 严格遵循项

- 所有查询按当前用户、课程归属、计划软删除过滤。
- 首页和日历只查看与跳转，不提供计划生命周期操作。
- 日期摘要和详情接口分离，避免月历返回完整任务树。
- 状态取数据库事实并校验派生一致性。

### 8.3 一定不能做的事

- 不能创建 `todos`、`calendar_events` 或任何日历写模型。
- 不能在查询中修复任务、计划或打卡状态。
- 不能提供创建、编辑、删除、重生成计划入口。
- 不能把多课程聚合误实现成多课程 StudyPlan。
- 不能修改 migration、五类生成器、前端文件或 S02 事务逻辑。

## 9. 完成检查表

- [ ] 实现范围全部完成。
- [ ] 五个只读 API 契约已实现。
- [ ] service 与 API 测试通过。
- [ ] 权限、软删除、空状态、日期边界和零写入已覆盖。
- [ ] 受影响计划模块回归通过。
- [ ] 文档同步完成。
- [ ] `git diff --check` 通过。
- [ ] 修改文件未越过所有权边界。
- [ ] 每个可验证小功能已独立提交。
