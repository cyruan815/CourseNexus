# F07 学习计划基础界面

## 0. 业务功能说明

- **业务场景**：学生希望围绕一门课程设定学习目标、起止日期和每天可用时间，并先查看计划是否合理再保存。
- **用户能力**：填写计划配置、选择课程资料范围、生成计划预览、确认保存、查看课程内计划列表和计划任务详情。
- **业务结果**：一个学习目标被转化为按日期排列的一级任务和二级任务，保存后形成后续日历与执行模式的数据基础。
- **业务边界**：本任务只接入当前已有的预览、保存、列表和详情接口；自然语言自动回填、计划编辑/重生成、日历、任务执行、打卡和讲义在后端完成前只占位。

## 1. 任务信息
- 编号：`F07`；负责人：前端开发者。
- 目标：只接当前计划 preview/save/list/detail，形成单课程配置、预览、保存和查看闭环。
- 前置：F01-F04/F03 scope；study-plans 四个现有接口。
- 当前基线：后端为确定性基础规则，非最终 AI；前端只有计划 slot。
- 范围外：自然语言独立解析、编辑/删除/重生成、日历、今日待办、执行、完成、打卡、讲义/PDF。

## 2. 实现范围
1. 先写四 API、配置校验、预览、保存快照、列表/详情和占位测试。
2. 路由新增 `/courses/:courseId/study-plans/new` 与 `/courses/:courseId/study-plans/:planId`，均受 F01 保护。
3. 表单输入 `goal_text,start_date,end_date,daily_available_minutes`，scope 只读自 F03；不展示无 API 的自动回填成功态。
4. 校验目标非空、end>=start、minutes 为正整数、显式 scope 非空；提交中防重。
5. preview POST 显示 title/date/minutes/tasks/subtasks；未知 subtask_type/status 兜底。
6. 用户修改配置后将旧 preview 标记过期并禁用保存，必须重新 preview。
7. 保存使用产生当前 preview 的不可变 request snapshot；成功使用真实 plan/tasks/subtasks 跳计划详情，不跳未实现日历。
8. 课程详情右栏加载 plan list；空态进入新建；点击真实 plan_id 进入 detail。
9. detail GET 展示 plan/tasks/subtasks；不允许勾完成或编辑。
10. 日历/执行等为后端未实现仅占位：入口 disabled、零请求、不造任务状态。

### 精确文件边界
- 创建：`features/study-plans/{api,types,StudyPlanForm,StudyPlanPreview,StudyPlanList,StudyPlanDetail,planValidation,planErrors}.ts(x)`。
- 创建：`pages/{StudyPlanCreatePage,StudyPlanDetailPage}.tsx`。
- 修改：`router/AppRouter.tsx`、`course-workspace/CourseWorkspaceSlots.tsx`、相关 CSS。
- 测试：`tests/features/study-plans/{api,form,preview,list,detail}.test.ts(x)`、`tests/pages/{study-plan-create,study-plan-detail}.test.tsx`、app-router 回归。
- 创建 `tests/manual/F07-study-plan-foundation.md`。
- 禁止：todos-calendar/learning-execution 假 API；修改后端/任务状态。

## 3. 字段与接口
### 当前已实现 API
- `POST /api/v1/courses/{course_id}/study-plans/preview`：`StudyPlanRequest` -> `StudyPlanPreview`。
- `POST /api/v1/courses/{course_id}/study-plans`：同请求 -> `{plan,tasks,subtasks}`。
- `GET /api/v1/courses/{course_id}/study-plans` -> `StudyPlanRead[]`。
- `GET /api/v1/study-plans/{plan_id}` -> `{plan,tasks,subtasks}`。
- Request：`goal_text,start_date,end_date,daily_available_minutes,material_scope`；不发送 preference/parsed config 假字段。
- Preview：`course_id,title,goal_text,start_date,end_date,daily_available_minutes,material_scope,tasks[{title,task_date,sort_order,subtasks[{title,subtask_type,description,related_material_ids,sort_order}]}]`。
- Read DTO 采用后端字段：plan 的 IDs/日期/status/审计字段；task 的 `plan_id,task_date,status,sort_order`；subtask 的 `task_id,plan_id,subtask_type,related_material_ids_json,status,completed_at,sort_order`。
- 错误：`NO_PARSED_MATERIAL,NOT_FOUND,VALIDATION_ERROR`；状态未知兜底。
### 本任务新增前端接口
- `previewStudyPlan,saveStudyPlan,listStudyPlans,fetchStudyPlan`；保存接受 preview 对应 request snapshot。
### 本任务新增 API / 后端未实现仅占位
- 不新增 API；自然语言 parse、plan edit/delete/regenerate、日历/执行/完成/打卡/讲义/export 均未注册。

## 4. 测试计划
- `api.test.ts`：四路径、body、scope、拆包、course/plan ID。
- `form.test.tsx`：四字段校验、日期/minutes、显式空、loading、防重、修改使 preview 过期。
- `preview.test.tsx`：任务排序、subtask 类型、空 tasks、未知枚举/缺描述。
- `list.test.tsx`：四态、真实 plan 路由、未知 status、401/404。
- `detail.test.tsx`：plan/tasks/subtasks 关联与排序、空态、无完成/edit 请求。
- 页面/路由测试：保存精确 snapshot，成功跳 detail；失败保留 preview；日历/执行 disabled 零请求。
- 命令：`pnpm --dir frontend test -- --run tests/features/study-plans tests/pages/study-plan-create.test.tsx tests/pages/study-plan-detail.test.tsx tests/pages/app-router.test.tsx`。
- 预期：退出码 0、无 live network；全量测试/build 成功。

## 5. 验收标准
### 自动化
- [ ] preview/save/list/detail 均有契约和页面行为测试。
- [ ] 修改配置后不能保存旧 preview；保存用精确 snapshot；单课程 ID 固定。
- [ ] 日历/执行等占位零请求；未知枚举/可选字段兜底。
### 人工
- [ ] 从课程详情进入新建，选 parsed scope，预览后保存并进真实详情。
- [ ] 修改日期后旧预览失效；保存失败保留预览可重试。
- [ ] 刷新 list/detail 一致；日历/执行按钮禁用且无请求。
- [ ] 1440/390 下表单、日期、任务树和长标题不重叠。

## 6. 交付物
- 四 API、创建/详情页、表单/预览/list/detail、路由、验证/错误、测试和 F07 人工记录。
- 建议按 preview、save、list/detail、占位/测试小提交。

## 7. 文档同步
- 更新 frontend-integration：四接口、request snapshot、确定性基础规则与未实现入口。
- 更新 current-state；计划团队新增 API 后先更新 contracts 再替换占位。

## 8. 冲突与注意事项
- 跨团队依赖 S02 保持基础接口兼容；S03-S07 提供日历/执行/完成/导出后端契约。
- 严格遵循：一个 plan 一个 course_id；保存只存任务结构；首页/日历只读。
- 一定不能做：把 preview 当已保存；保存后假跳日历；猜 execution API；提前生成讲义/测试题。

## 9. 完成检查表
- [ ] 范围、测试、回归/build、双视口验收、docs/diff/所有权完成。
- [ ] 只接四个当前 API，未造日历/执行成功；小功能独立提交。
