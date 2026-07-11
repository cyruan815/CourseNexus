# S03 今日待办与日历聚合验收记录

## 验收日期

2026-07-11

## 验收结论

S03 实现首页今日待办、全局月历、全局当日待办、课程月历和课程当日任务五类只读查询。不新增业务表、字段或 migration；所有查询从 S02 计划任务树派生，不写数据库。

## 已实现接口

- `GET /api/v1/todos/today?date=YYYY-MM-DD`
- `GET /api/v1/calendar/month?month=YYYY-MM`
- `GET /api/v1/calendar/days/{date}/todos`
- `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM`
- `GET /api/v1/courses/{course_id}/study-calendar/days/{date}`

## 产品口径确认

- 首页今日待办返回一级任务和二级任务数组，前端默认折叠二级任务。
- 大日历日期格返回计数、最多 3 条一级任务摘要和 `hidden_task_count`。
- 大日历日期弹窗按课程和一级任务分组，二级任务点击进入后续 S04 执行页。
- 课程详情页今日任务只展示当前课程今天的一二级任务，前端默认展开二级任务。
- 计划详情按钮复用 S02 `GET /api/v1/study-plans/{plan_id}`。

## 验证命令

```powershell
cd D:\Projects\CourseNexus\backend
uv run python -m pytest tests/modules/todos_calendar tests/integration/test_plan_calendar_flow.py -q
```

结果：`18 passed in 3.97s`。

## 边界确认

- 不创建 `todos` 或 `calendar_events`。
- 不修改学习计划写逻辑。
- 不修改 migration 或 `backend/app/db/models.py`。
- 不更新任务完成状态。
- 不写打卡。
- 不生成讲义、任务测试题或 PDF。
- 不修改前端。

## 已知问题

- `execution_url` 当前返回 `null`，前端可先使用 `subtask_id` 拼接后续 S04 执行页；S04 落地后可再评审是否返回稳定 URL。
- S03 只读查询发现一级任务状态与二级任务派生状态不一致时返回 `STATE_CONFLICT`，不在查询中修复数据。