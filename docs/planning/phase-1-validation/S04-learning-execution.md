# S04 计划学习执行与任务完成验收记录

## 范围

本次完成后端 S04：执行上下文查询、二级任务完成/取消完成、父一级任务状态汇总、计划状态汇总，以及同事务调用 S05 打卡重算。

## 已验证能力

- `GET /api/v1/study-subtasks/{subtask_id}/execution-context` 返回当前二级任务所在业务日期的同计划任务列表。
- 执行上下文不返回完整计划树。
- 关联资料校验用户和课程归属，跨课程资料返回 `STATE_CONFLICT`。
- `PUT /api/v1/study-subtasks/{subtask_id}/completion` 使用 `{completed: boolean}` 期望状态。
- 重复完成/取消完成幂等，重复完成不刷新 `completed_at`。
- 取消完成回到 `not_started` 并清空 `completed_at`。
- completion 事务内汇总一级任务、计划状态，并调用 S05 重算打卡。
- 打卡重算失败时，二级任务、一级任务、计划和打卡记录全部 rollback。
- S03 下一次查询能反映完成后的状态。

## 验证命令

```powershell
uv run python -m alembic upgrade head
uv run python -m pytest tests/modules/checkins tests/modules/learning_execution tests/modules/todos_calendar tests/modules/study_plans tests/integration/test_checkin_lifecycle_sync.py tests/integration/test_subtask_completion_transaction.py -q
git diff --check
```

## 实际结果

- Alembic：退出码 0。
- Pytest：`67 passed in 18.00s`。
- `git diff --check`：退出码 0；仅出现 LF/CRLF 换行提示。

## 未涉及范围

- 未修改前端。
- 未新增 migration。
- 未修改 S03 只读聚合逻辑。
- 本验收记录产生于 S04 合并时，当时未接入 S06 讲义或任务测试生成；当前 S06 已接入，`execution-context` 会返回最近一次成功生成的 `handout_content_id` / `task_test_content_id`，详见 `docs/domains/study-mode/task-content.md`。
