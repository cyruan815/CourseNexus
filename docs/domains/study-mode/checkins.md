# S05 学习打卡与完成比例实现

## 代码入口

- `backend/app/modules/checkins/models.py`：复用 `checkin_records` 表和 `(user_id, checkin_date)` 唯一约束。
- `backend/app/modules/checkins/schemas.py`：`CheckinRead`、`CheckinRangeRead` 和 streak summary DTO。
- `backend/app/modules/checkins/repository.py`：按用户和日期聚合 `study_subtasks`，排除已删除课程和已删除计划。
- `backend/app/modules/checkins/service.py`：完成比例、颜色等级、连续天数和 `recalculate_checkin()`。
- `backend/app/modules/checkins/router.py`：单日和日期范围只读查询 API。
- 前端个人中心：`frontend/src/pages/ProfilePage.tsx`，展示当前用户、今日完成比例、当前年度打卡热力图和 streak summary。
- 前端 API 适配：`frontend/src/features/profile/api.ts`。
- 测试入口：`backend/tests/modules/checkins/`、`backend/tests/integration/test_checkin_lifecycle_sync.py`、`backend/tests/integration/test_subtask_completion_transaction.py`、`frontend/tests/pages/profile-page.test.tsx`。

## 数据流

写入路径只来自计划生命周期和二级任务完成事务。服务先统计当前用户指定日期下未删除课程、未删除计划中的二级任务数量，再计算完成数量、比例和颜色等级，最后对 `checkin_records` 做同日唯一记录的插入或更新。

查询路径保持只读：`GET /api/v1/checkins/{date}` 如果没有持久化记录，会临时按当前任务事实计算 DTO 并返回，但不插入数据库。范围查询只返回已经形成的持久化记录。

2026-07-14 前端个人中心第一版接入上述只读查询：页面不提供手动打卡，不自行重算 streak，不把缺失日期补写到后端；缺失日期仅在近 14 天颜色条中按 0 级空白展示。

2026-07-15 前端个人中心将颜色条升级为当前年度打卡热力图：页面按本地年份查询 `YYYY-01-01` 至 `YYYY-12-31` 的范围记录，用周列、星期行和月份标签展示全年日期。后端范围查询仍只返回已持久化记录；前端仅把缺失日期渲染为 `color_level=0` 的空白格，不补写、不伪造任务完成事实。热力图颜色按 `color_level` 映射到绿色深浅，`0` 和 `1` 继续共用灰色。

## 派生算法

```text
completion_ratio = completed_subtask_count / total_subtask_count
无任务时 completion_ratio = 0.0000
Decimal 固定保留四位小数
```

颜色等级：

- `0`：无任务，`has_tasks=false`。
- `1`：有任务但完成数为 0，`has_tasks=true`。
- `2`：`0 < ratio < 0.4`。
- `3`：`0.4 <= ratio < 0.8`。
- `4`：`0.8 <= ratio < 1.0`。
- `5`：全部完成。

`color_level=0` 和 `color_level=1` 是不同后端状态。当前前端可以把两者渲染成同一个颜色，后续如需区分只调整前端颜色映射，不需要改表或迁移。

连续天数统计在范围查询 summary 中派生：当天 `total_subtask_count > 0` 且 `completed_subtask_count > 0` 即计入 streak，不要求 100% 完成。`longest_streak_days` 是查询范围内最长连续完成段；`current_streak_days` 是查询结果最后一条记录所在连续段长度，如果最后一条记录是无任务日或有任务但未完成，则为 0。无任务日会中断当前连续段；范围查询只基于已经持久化的记录计算，缺失日期不会被补齐，两个完成日之间只要日期不相邻就视为中断。空结果返回 `task_days=0`、`completed_days=0`、`current_streak_days=0`、`longest_streak_days=0`。

## 事务与失败策略

`recalculate_checkin(db, user_id, checkin_date, flush_only=True)` 不提交事务，供 S04 completion 和 S02 lifecycle 在同一事务内调用。外层任一步失败时 rollback，计划任务状态和打卡记录一起回滚。`flush_only=False` 用于独立重算时自行 commit。

## 复杂度

单日重算按该用户该日期二级任务数量聚合，时间复杂度 O(n)。范围查询按持久化记录数量排序返回，时间复杂度 O(k log k)，k 为范围内已有记录数。

## 已知限制

- 不提供手动打卡 POST。
- 不做排行榜或奖励体系。
- 范围查询不补齐没有持久化记录的日期。
