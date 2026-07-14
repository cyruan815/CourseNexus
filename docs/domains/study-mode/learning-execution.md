# S04 计划学习执行与任务完成实现

## 代码入口

- `backend/app/modules/learning_execution/schemas.py`：执行上下文、任务级问答和 completion DTO。
- `backend/app/modules/learning_execution/repository.py`：二级任务、父任务、计划、课程、同日任务和关联资料查询。
- `backend/app/modules/learning_execution/service.py`：执行上下文组装、任务级问答资料范围派生、父任务/计划状态汇总和 completion 事务。
- `backend/app/modules/learning_execution/router.py`：执行上下文、任务级问答和二级任务完成 API。
- `frontend/src/features/study-plans/api.ts`：执行上下文、任务级问答和二级任务完成 API adapter。
- `frontend/src/features/study-plans/types.ts`：执行上下文、任务级问答、执行任务树、关联资料和 completion 返回类型。
- `frontend/src/pages/StudyPlanDetailPage.tsx`：从学习计划详情页进入具体二级任务执行页。
- `frontend/src/pages/StudyTaskExecutionPage.tsx`：计划执行页基础，读取当天执行上下文，支持任务级 AI 问答，并完成 / 取消完成当前二级任务。
- `frontend/src/router/AppRouter.tsx`：受保护路由 `/study-subtasks/:subtaskId`。
- 测试入口：`backend/tests/modules/learning_execution/test_task_qa_api.py`、`backend/tests/modules/learning_execution/`、`backend/tests/integration/test_subtask_completion_transaction.py`。
- 前端测试入口：`frontend/tests/features/study-plans/api.test.ts`、`frontend/tests/pages/study-plan-pages.test.tsx`。

## 执行上下文

`GET /api/v1/study-subtasks/{subtask_id}/execution-context` 从当前二级任务追溯父一级任务、计划和课程，并校验资源属于当前用户。计划或课程已删除时按不存在处理。

响应只返回当前二级任务父任务的 `task_date` 当天、同一计划内的一级任务和二级任务，不返回完整计划树。`execution_date` 使用父任务业务日期，允许用户从日历进入历史或未来任务。

关联资料读取 `related_material_ids_json`。字段必须是字符串数组；跨课程或跨用户资料触发 `STATE_CONFLICT`；缺失资料按 `availability=deleted` 返回占位。S06 已接入后，`handout_content_id` 和 `task_test_content_id` 来自当前二级任务最近一次未删除且 `generation_status=success` 的 `handout` / `task_test` 内容；没有成功内容时返回 `null`，最新 failed 记录不会覆盖既有成功内容 ID。执行页拿到 `task_test_content_id` 后，可以调用 `GET /api/v1/generated-contents/{generated_content_id}/exports/markdown` 下载只读测试题 Markdown；拿到 `handout_content_id` 后，可以调用 `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf` 下载任务讲义 PDF。导出不改变二级任务完成状态，也不写打卡记录。

前端执行页只以 execution context 为事实来源：

- 左侧展示当天同一计划内的一级任务和二级任务，按 `sort_order` 排序，高亮 `current_subtask_id`。
- 中间展示当前二级任务标题、类型、描述、状态和完成 / 取消完成按钮。
- 右侧展示 AI 助教、当前二级任务关联资料、最近成功生成内容 ID 的只读状态和打卡进度。AI 助教只提交 `conversation_id` 和 `question`，不允许前端改写资料范围。
- 页面不接受用户修改资料范围，不在前端拼接完整计划树，不在 C8 中生成讲义或任务测试题正文。
- `/study-subtasks/:subtaskId` 是轻量执行页入口；计划详情页只通过二级任务 ID 跳转到该路由。

2026-07-14 前端执行页布局约束：右侧 `AI 助教` 卡片内部把回答/提示区域放在上方可滚动区域，提问输入框和提交按钮固定在助教卡片底部；右侧 `任务摘要` 模块贴近右栏底部并保持精简资料列表。中间列的“完成任务 / 取消完成”按钮保持在当前任务内容流末端，内容短时落在中间面板底部，内容长时需要滚到底部才能看到，避免悬浮遮挡预览内容。切换二级任务时，前一个任务的内容生成可以在后台继续；蓝色提示会自动消退，黄色“后台生成中”只在真实生成状态存在时展示。生成失败状态不加载旧内容，成功内容只按当前二级任务 ID 显示。

## 执行页任务级问答

`POST /api/v1/study-subtasks/{subtask_id}/qa/questions` 支持执行页围绕当前二级任务提问。请求体只包含 `conversation_id` 和 `question`，不允许前端覆盖资料范围。服务层先通过 `repository.get_execution_target()` 校验当前用户拥有该二级任务、父任务、计划和课程，再把 `StudySubTask.related_material_ids_json` 转成 `MaterialScope(include_all_parsed_materials=False, material_ids=...)`。

该接口复用 `course_qa.ask_course_question()` 的检索、模型回答、消息保存和引用保存链路，但传入以下任务执行页约束：

- `CourseQuestionCreate.source_page = "task_execution"`，新建 `Conversation.source_page` 固定为 `task_execution`。
- `allowed_conversation_source_pages = {"task_execution"}`，因此跨课程、跨用户或课程详情页 `course_detail` 对话复用都返回 `NOT_FOUND`。
- `material_scope_metadata` 写入 `subtask_id` 和 `task_id`；Course QA 保存用户消息后再补写实际 `used_material_ids`。
- 模型问题会附加课程、计划、一级任务、二级任务标题、类型和描述作为任务上下文；数据库中的用户消息仍保存原始问题。

返回结构复用课程问答响应，包含 `conversation_id`、`user_message_id`、`assistant_message_id`、`answer_text`、`answer_type`、`source_citations` 和 `used_material_ids`。`answer_text` 中的 `[[cite:N]]` 与 `source_citations[N-1]` 对应；执行页和课程详情页复用 `features/course-qa/InlineCitationAnswer`，将标记显示为行内序号角标，悬停后展示资料名、页码和 `hit_text` 引用片段，不直接暴露原始标记。当前二级任务没有 parsed chunk 或没有相关命中时返回 `answer_type="no_source"`，引用和实际使用资料均为空数组，不调用伪引用兜底。

任务级问答只写 `conversations`、`messages` 和有真实命中的 `source_citations`。它不修改二级任务状态，不汇总一级任务或计划状态，也不写 `checkin_records`。前端执行页在右侧 AI 助教区维护本页 `conversation_id`，下一次追问复用该 ID；提问失败只影响助教区，不影响完成打卡、讲义生成或任务测试题生成。

`PUT /api/v1/study-subtasks/{subtask_id}/completion` 接收期望状态：

```json
{"completed": true}
```

完成时二级任务写为 `completed` 并设置 UTC `completed_at`。取消完成时二级任务写回 `not_started` 并清空 `completed_at`。重复提交同一状态返回 `changed=false`，不会重复累计，也不会刷新已完成任务的 `completed_at`。

前端 completion 调用固定提交 `{ "completed": boolean }`，不把按钮当作无状态 toggle。成功后用返回的 `subtask`、`task`、`plan` 和 `checkin` 快照更新执行页局部状态；失败时按 `error.code` 展示可恢复提示。`STATE_CONFLICT` 提示用户刷新后再试，`NOT_FOUND` 表示任务不存在或无权限，`UNAUTHORIZED` 由统一 API client 清理登录态。

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
- completion API 不生成讲义或任务测试题；S06 按需生成入口和 execution-context 内容 ID 规则见 [task-content.md](task-content.md)。`POST /api/v1/study-subtasks/{subtask_id}/qa/questions` 也不生成 `AIGeneratedContent`，只保存问答对话和真实引用。
- 不新增 migration，不修改前端。
## 2026-07-13 执行页生成与 QA 兼容补充

- 执行页任务级问答仍只接受 `conversation_id` 和 `question`。`OpenAIModelProvider.answer_question()` 优先走 Responses API；当兼容模型服务对 `/responses` 返回 404 时，后端自动回退 Chat Completions。非 404 错误、JSON/schema 失败和无资料兜底语义保持不变。
- task-test 生成参数读取顺序为：计划 `parsed_config_json.task_snapshot` 中的 `generation_parameters.task_test` 默认值先入底，再由本次请求 `parameters` 显式字段覆盖。
- 若历史计划中的默认参数已损坏，生成入口返回 `GENERATION_SCHEMA_INVALID`，并写入一条 `AIGeneratedContent(generation_status=failed, error_code=GENERATION_SCHEMA_INVALID)`，便于执行页重试和报告追踪。
