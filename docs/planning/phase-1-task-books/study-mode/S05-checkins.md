# S05 学习打卡与完成比例

## 0. 业务功能说明

- **业务场景**：学生希望在个人中心直观看到每天完成了多少计划任务，以及一段时间内的学习坚持情况。
- **用户能力**：查看某一天或一段日期范围的任务总数、已完成数、完成比例和打卡颜色等级。
- **业务结果**：打卡由真实二级任务完成情况自动生成，完成越多颜色越深；完成或取消任务后数据自动重算。
- **业务边界**：学生不能手动制造打卡；本任务不做排行榜、连续天数奖励、复杂统计报表或由前端自行计算颜色。

## 1. 任务信息
- 编号与名称：`S05` 学习打卡与完成比例。
- 负责人角色：计划学习模式后端开发者。
- 目标：按用户自然日幂等重算唯一 `CheckinRecord`，提供个人中心单日和日期范围查询。
- 前置依赖：S01 表契约和 S02 计划生命周期。先独立实现并测试 `recalculate_checkin()`，再由 S04 completion 事务调用；不以 S04 已实现为前置条件。
- 范围外：不做手动打卡、连续天数、排行榜、统计报表、前端配色值。

## 2. 实现范围
### 2.1 计算与颜色
- 统计当前用户指定日期下、未删除课程和未删除计划的全部二级任务。
- `completion_ratio = completed_subtask_count / total_subtask_count`，使用 `Decimal` 四位小数。
- 固定映射：无任务 `0`；有任务且 0% `1`；`0% < ratio < 40%` 为 `2`；`40% <= ratio < 80%` 为 `3`；`80% <= ratio < 100%` 为 `4`；100% 为 `5`。
- 同一用户同一日期只保留一行；重复重算更新同一行，不做增量加减。
- `recalculate_checkin(db, *, user_id, checkin_date, flush_only)` 是公共入口。`flush_only=True` 不提交，供 S04 同事务调用。
- 并发首次插入使用 nested transaction/savepoint 捕获唯一约束冲突，再查询并更新既有记录。
- S02 替换计划时重算旧日期与新日期并集；删除计划时重算该计划全部任务日期，均与生命周期写入同事务。

### 2.2 精确文件边界
创建：
- `backend/app/modules/checkins/schemas.py`
- `backend/app/modules/checkins/repository.py`
- `backend/app/modules/checkins/service.py`
- `backend/app/modules/checkins/router.py`
- `backend/tests/modules/checkins/test_checkin_service.py`
- `backend/tests/modules/checkins/test_checkin_api.py`
- `backend/tests/integration/test_checkin_lifecycle_sync.py`

修改：
- `backend/app/modules/checkins/__init__.py`
- `backend/app/api/router.py`：只注册 checkins router。
- `backend/app/modules/learning_execution/service.py`：调用公共重算函数。
- `backend/app/modules/study_plans/service.py`：替换/删除计划时重算受影响日期。

禁止修改：`checkins/models.py`、`db/models.py`、migration、生成模块、前端、五类生成器。

## 3. 字段与接口
### 3.1 复用字段
- 复用 `checkin_records` 全部现有字段和 `(user_id, checkin_date)` 唯一约束；不新增 migration。
- 新增 `CheckinRead`：`id`、`checkin_date`、两个计数、字符串形式 `completion_ratio`、`color_level`、`has_tasks`、时间戳。
- `has_tasks` 是响应派生字段，不落库；`total_subtask_count > 0` 时为 true。

### 3.2 当前 API
- 当前无 checkins API；当前仅有 SQLAlchemy model。

### 3.3 新增 API
`GET /api/v1/checkins/{date}`：
```json
{
  "id": "chkrec_1",
  "checkin_date": "2026-07-10",
  "total_subtask_count": 5,
  "completed_subtask_count": 2,
  "completion_ratio": "0.4000",
  "color_level": 3,
  "has_tasks": true,
  "created_at": "2026-07-10T12:00:00+00:00",
  "updated_at": "2026-07-10T12:00:00+00:00"
}
```
- 记录尚未形成时按当前任务事实计算只读 DTO 后返回，不在 GET 请求中写数据库；无任务也返回零值 DTO，避免前端区分 404。持久化记录只由计划保存/替换/删除和 S04 completion 写流程重算。

`GET /api/v1/checkins?start_date=2026-07-01&end_date=2026-07-31`：
```json
{
  "start_date": "2026-07-01",
  "end_date": "2026-07-31",
  "items": [],
  "summary": {"task_days": 0, "completed_days": 0}
}
```
- 日期范围必填，闭区间，最长 366 天；只返回已形成记录，按日期升序。
- 错误：401 `UNAUTHORIZED`；422 `VALIDATION_ERROR`；500 `INTERNAL_ERROR`。无跨用户资源 ID 参数。
- 两个接口在契约合并前均为后端未实现候选；前端个人中心必须等待合并。

## 4. 测试计划
### 4.1 精确场景
`test_checkin_service.py`：无任务、0%、1/5、2/5、4/5、5/5 六档；重复重算同 ID；取消完成比例下降；软删除计划不计数；两个课程同日合并；并发插入只留一行。

`test_checkin_api.py`：单日、范围、空范围、366/367 天边界、非法日期、401、统一 envelope、Decimal 序列化。

额外断言：单日 GET 在记录缺失时返回计算结果，但数据库行数不变化，禁止查询接口产生写副作用。

`test_checkin_lifecycle_sync.py`：S04 完成/取消与打卡同事务；S02 替换/删除后旧、新日期准确；打卡 flush 失败时任务和计划 rollback。

### 4.2 命令与预期
```powershell
cd backend
conda run -n course-nexus python -m pytest tests/modules/checkins/test_checkin_service.py -q
conda run -n course-nexus python -m pytest tests/modules/checkins/test_checkin_api.py -q
conda run -n course-nexus python -m pytest tests/integration/test_checkin_lifecycle_sync.py -q
conda run -n course-nexus python -m pytest tests/modules/learning_execution tests/modules/checkins -q
```
预期：退出码均为 0；每个用户日期最多一行；颜色边界与上表完全一致；无网络调用。

## 5. 验收标准
### 5.1 自动化
- [ ] 六种颜色等级边界全部覆盖。
- [ ] 重复完成、取消、重算不重复累计。
- [ ] 多课程同日按用户合并，跨用户隔离。
- [ ] 替换/删除计划同步重算受影响日期。
- [ ] S04 失败事务不误更新打卡。

### 5.2 人工
- [ ] 5 个任务完成 1 个显示 level 2，完成 5 个显示 level 5。
- [ ] 无任务日期显示 `has_tasks=false`、level 0。
- [ ] 取消一个任务后刷新个人中心，计数和颜色立即下降。
- [ ] 删除计划后对应日期按剩余计划任务重算。

## 6. 交付物
- checkins schema/repository/service/router 与三组测试。
- API、数据、运行流程和当前状态文档。
- `docs/domains/study-mode/validation/S05-checkins.md` 中文验收记录。
- 建议提交：`feat(checkins): 幂等重算每日学习完成记录`；`feat(checkins): 新增打卡查询接口`；`fix(checkins): 同步计划生命周期与打卡`。

## 7. 文档同步
- 新建或更新 `docs/domains/study-mode/checkins.md`：记录打卡模块分层和代码入口、按用户日期重算的数据流、完成比例与颜色等级算法及伪代码、Decimal 舍入不变量、upsert 与并发一致性、查询/写入复杂度、失败补偿和测试证据。
- 更新 `docs/api-data/contracts.md`、`api-conventions.md`：接口、Decimal 和颜色映射。
- 更新 `docs/api-data/data-model.md`、`table-schema.md`：明确现有字段语义，无 schema 变化。
- 更新 `docs/architecture/runtime-flows.md` 和 `docs/planning/current-state.md`。
- 不改 PRD 原意；不直接改 `frontend-integration.md`，由前端负责人接收契约。

## 8. 冲突与注意事项
### 严格遵循
- S04 只调用公共重算函数；颜色规则只在 checkins 模块实现。
- 打卡日期来自任务 `task_date`，不是请求到达 UTC 日期。
- 查询和写入始终使用当前 `user_id`。

### 一定不能做
- 不能提供手动打卡 POST、按增量计数或新增表。
- 不能把无任务和 0% 完成映射为同一颜色等级。
- 不能在 S04 事务内再次 commit。
- 不能修改前端、五类生成器或 baseline migration。

## 9. 完成检查表
- [ ] 实现、测试、人工验收和文档同步完成。
- [ ] 唯一约束、颜色边界、事务回滚证据齐全。
- [ ] 相邻 S02/S04 回归通过。
- [ ] `git diff --check` 通过且未越权修改。
- [ ] 每个小功能独立提交。
