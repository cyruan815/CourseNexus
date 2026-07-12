# S04 计划学习执行与任务完成实现

## 代码入口

- `backend/app/modules/learning_execution/schemas.py`：执行上下文和 completion DTO。
- `backend/app/modules/learning_execution/repository.py`：二级任务、父任务、计划、课程、同日任务和关联资料查询。
- `backend/app/modules/learning_execution/service.py`：执行上下文组装、父任务/计划状态汇总和 completion 事务。
- `backend/app/modules/learning_execution/router.py`：执行上下文和二级任务完成 API。
- 测试入口：`backend/tests/modules/learning_execution/`、`backend/tests/integration/test_subtask_completion_transaction.py`。

## 执行上下文

`GET /api/v1/study-subtasks/{subtask_id}/execution-context` 从当前二级任务追溯父一级任务、计划和课程，并校验资源属于当前用户。计划或课程已删除时按不存在处理。

响应只返回当前二级任务父任务的 `task_date` 当天、同一计划内的一级任务和二级任务，不返回完整计划树。`execution_date` 使用父任务业务日期，允许用户从日历进入历史或未来任务。

关联资料读取 `related_material_ids_json`。字段必须是字符串数组；跨课程或跨用户资料触发 `STATE_CONFLICT`；缺失资料按 `availability=deleted` 返回占位。S06 已接入后，`handout_content_id` 和 `task_test_content_id` 来自当前二级任务最近一次未删除且 `generation_status=success` 的 `handout` / `task_test` 内容；没有成功内容时返回 `null`，最新 failed 记录不会覆盖既有成功内容 ID。

## 完成事务

`PUT /api/v1/study-subtasks/{subtask_id}/completion` 接收期望状态：

```json
{"completed": true}
```

完成时二级任务写为 `completed` 并设置 UTC `completed_at`。取消完成时二级任务写回 `not_started` 并清空 `completed_at`。重复提交同一状态返回 `changed=false`，不会重复累计，也不会刷新已完成任务的 `completed_at`。

事务顺序：

1. 查询并校验二级任务、父任务、计划、课程归属。
2. 写二级任务期望状态并 flush。
3. 根据父任务全部二级任务汇总一级任务状态并 flush。
4. 根据计划全部一级任务汇总计划状态并 flush。
5. 调用 `recalculate_checkin(..., flush_only=True)` 重算父任务日期打卡并 flush。
6. 最后统一 commit。

任一步异常都会 rollback，避免留下子任务完成但打卡未更新的半状态。

## 状态汇总规则

一级任务：

- 全部二级任务 `completed` -> `completed`。
- 全部二级任务 `not_started` -> `not_started`。
- 其他组合 -> `in_progress`。

计划：

- 全部一级任务 `completed` -> `completed`。
- 其他情况 -> `active`。

completion API 不直接写二级任务 `in_progress`。

## 边界

- 不修改 S02 计划生成逻辑。
- 不调用 S03 service，也不维护待办/日历缓存。
- completion API 不生成讲义或任务测试题；S06 按需生成入口和 execution-context 内容 ID 规则见 [task-content.md](task-content.md)。
- 不新增 migration，不修改前端。
