# S05 学习打卡与完成比例验收记录

## 范围

本次完成后端 S05：按用户和日期重算唯一打卡记录，提供单日和日期范围查询，返回完成比例、颜色等级和连续天数 summary。

## 已验证能力

- `recalculate_checkin()` 会按当前事实重算，不做增量累计。
- 同一用户同一日期只保留一条 `CheckinRecord`。
- 已删除课程和已删除计划不计入统计。
- 单日 GET 在记录缺失时返回只读计算 DTO，不写数据库。
- 范围 GET 返回持久化记录和 summary。
- streak 按“当天有任务且完成过任意二级任务”计算。
- `color_level=0` 表示无任务，`has_tasks=false`。
- `color_level=1` 表示有任务但未开始，`has_tasks=true`。
- 0/1 后端语义不合并；当前 UI 可映射为同色。
- S02 保存、替换、删除计划会同步重算受影响日期。

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

- 不提供手动打卡。
- 不新增表或 migration。
- 不做排行榜、奖励和复杂统计报表。
- 不修改前端颜色映射，只记录 0/1 可暂用同色的产品口径。