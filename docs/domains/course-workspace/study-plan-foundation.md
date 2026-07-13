# 学习计划基础界面接入

## 当前范围

前端已将学习计划从课程详情摘要入口推进到基础创建 / 详情闭环，但只接入已确认契约。

- 创建页路由：`/courses/:courseId/study-plans/new`，页面入口为 `frontend/src/pages/StudyPlanCreatePage.tsx`。
- 详情页路由：`/courses/:courseId/study-plans/:planId`，页面入口为 `frontend/src/pages/StudyPlanDetailPage.tsx`。
- 学习计划 API 独立封装在 `frontend/src/features/study-plans/api.ts`，类型在 `frontend/src/features/study-plans/types.ts`。
- 课程详情左侧学习计划卡片读取 `GET /api/v1/courses/{course_id}/study-plans`；无计划时跳转创建页，有计划时计划标题跳转详情页。
- 2026-07-13 C1 已将前端学习计划 API/type 适配层扩展到 S02 生命周期接口：配置解析、学前诊断问题、诊断 profile、preview、保存、列表、详情、重生成 preview、替换和删除。该变更只提供 adapter，不在现有页面启用诊断、重生成、替换或删除交互。
- 2026-07-13 C3 已在创建页接入配置自动解析回填：用户输入自然语言目标后，前端调用 `POST /api/v1/courses/{course_id}/study-plan-config-parses`，把后端明确解析出的目标、日期、每日时长和学习方式回填到可编辑表单；`unresolved_fields` 只展示当前页面真实可编辑且仍无有效值的字段，系统追溯字段不展示为“需手动补齐”。

## 创建页状态流转

- 用户手动填写 `goal_text`、`start_date`、`end_date`、`daily_available_minutes`。
- 用户也可以点击“自动解析配置”，用当前 `goal_text` 和固定 `material_scope` 请求配置解析；解析结果只作为表单回填，用户仍需确认后再生成 preview。
- `material_scope` 当前固定为 `{ include_all_parsed_materials: true, material_ids: [] }`；资料范围选择器应进入 C4 完整创建向导或独立前置小提交，且只能提交具体资料 ID，不能提交文件夹 ID。
- `preference` 由创建页学习方式控件维护，默认 `balanced`，解析回填可更新为 `fast_track`、`balanced`、`mastery` 或 `sprint`；API 仍只发送英文枚举，界面展示中文标签。
- 点击“生成预览”调用 `POST /api/v1/courses/{course_id}/study-plans/preview`。
- 前端保存产生预览时的请求快照；若表单字段在预览后变化，旧预览标记为过期并禁用保存。
- 配置解析回填属于会改变 preview 请求体的操作；如果已有 preview，回填后必须标记为过期并禁用保存。
- 点击“保存计划”调用 `POST /api/v1/courses/{course_id}/study-plans`，请求携带 `Idempotency-Key`，并提交 `client_flow = "wizard_v1"`、preview `title` 与 preview 中展示过的 `tasks`；保存成功后跳转计划详情页。同一份未变化 preview 的保存重试复用同一个幂等键，只有重新生成 preview 后才创建新的保存幂等键。

## 详情页状态流转

- 调用 `GET /api/v1/study-plans/{plan_id}` 获取 `plan`、`tasks`、`subtasks` 后只读展示。
- 任务状态、子任务类型做中文 fallback；未知枚举保留原值展示。
- 学习执行入口已跳转 `/study-subtasks/{subtask_id}`，由执行页读取 execution context 并完成 / 取消完成二级任务。
- 计划重新生成已接入详情页内生命周期面板：用户调整目标、日期、每日学习时长和学习方式后调用 `POST /api/v1/study-plans/{plan_id}/regeneration-previews`；该 preview 不落库。
- 用户确认替换时调用 `PUT /api/v1/study-plans/{plan_id}`，提交新 preview 的 `title`、exact `tasks`、`material_scope`、`client_flow = "wizard_v1"` 和当前详情的 `expected_updated_at`。后端若返回 `STATE_CONFLICT`，前端只提示刷新或新建计划，不强行覆盖。
- 删除计划已接入二次确认；确认后调用 `DELETE /api/v1/study-plans/{plan_id}`，成功回到课程详情页。删除是软删除，不删除课程资料或已有生成内容。
- 导出计划仍保持 disabled / 后续接入；学习计划自身没有前端伪造导出。

## 测试入口

- API 测试：`frontend/tests/features/study-plans/api.test.ts`
- 页面测试：`frontend/tests/pages/study-plan-pages.test.tsx`
- 路由测试：`frontend/tests/pages/app-router.test.tsx`
- 课程详情入口测试：`frontend/tests/pages/course-detail.test.tsx`

## API 适配层覆盖范围

`frontend/src/features/study-plans/api.ts` 当前封装的真实后端接口：

- `POST /api/v1/courses/{course_id}/study-plan-config-parses`
- `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions`
- `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles`
- `POST /api/v1/courses/{course_id}/study-plans/preview`
- `POST /api/v1/courses/{course_id}/study-plans`，保存时由调用方传入并复用 `Idempotency-Key`
- `GET /api/v1/courses/{course_id}/study-plans`
- `GET /api/v1/study-plans/{plan_id}`
- `POST /api/v1/study-plans/{plan_id}/regeneration-previews`
- `PUT /api/v1/study-plans/{plan_id}`
- `DELETE /api/v1/study-plans/{plan_id}`

`types.ts` 对齐后端 S02/S03 schema：`StudyPlanPreviewRequest` 支持 `end_date` 或 `duration_days` 描述日期范围，`daily_available_minutes` 可省略以使用后端推荐值；诊断题、诊断答案、诊断 profile、配置解析、重生成 preview、替换请求、today todos、全局 calendar 和单课程 study calendar 均有独立类型。learning execution、handout/task-test 和 export 接口暂不放入 `features/study-plans`，后续按对应上下文建立边界。

## 2026-07-14 C5 本课程计划日历前端接入

`frontend/src/pages/CalendarPage.tsx` 已识别 `/calendar?courseId={course_id}` 并进入本课程日历模式；无 `courseId` 时继续保留全局大日历占位，等待 C7。

- `frontend/src/features/study-plans/api.ts::fetchCourseStudyCalendar(courseId, month)` 调用 `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM`。
- `frontend/src/features/study-plans/api.ts::fetchCourseStudyCalendarDay(courseId, date)` 调用 `GET /api/v1/courses/{course_id}/study-calendar/days/{date}`。
- 月视图只展示后端日期摘要；点击日期后才读取当天任务树。
- 任务卡只链接到既有计划详情 `/courses/{course_id}/study-plans/{plan_id}`，不提前接入 C8 执行页或任务完成写操作。

测试入口：

- `frontend/tests/features/study-plans/api.test.ts`
- `frontend/tests/pages/calendar-page.test.tsx`

## 2026-07-13 C2 学情诊断向导前端接入

创建页已经从占位的“学情诊断 disabled”切换为真实轻量向导，入口为 `frontend/src/features/study-plans/components/DiagnosticWizard.tsx`，由 `frontend/src/pages/StudyPlanCreatePage.tsx` 挂载。

- 点击“开始学情诊断”调用 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions`，请求只发送当前 `goal_text` 和固定 `material_scope`。
- 向导按后端返回的 `sort_order` 展示题目；`topic_mastery` 和 `weak_area` 使用单选，`diagnostic_note` 使用可选文本输入。
- 点击“提交诊断”调用 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles`，只把用户答案、`question_version` 和 `material_scope` 交给后端归纳，前端不伪造 profile。
- 后端返回的 `StudyPlanDiagnosticProfile` 保存在创建页状态中；后续点击“生成预览”时作为 `diagnostic_profile` 放入 `StudyPlanPreviewRequest`。
- 学情诊断是可选增强项；未完成诊断时，创建页仍允许直接生成 preview，且请求体不携带 `diagnostic_profile`。
- 修改 `goal_text` 或重新获取诊断题会清空已有诊断 profile；修改日期或每日时长只会让 preview 过期，默认保留诊断结果。
- 配置解析回填 `goal_text` 时同样清空已有诊断 profile；仅回填日期、每日时长或学习方式时保留已生成 profile，但旧 preview 仍过期。
- 创建页会按 courseId 将 `goal_text`、日期、每日时长和已生成的诊断 profile 写入浏览器 `localStorage` 草稿；刷新页面后恢复这些输入，保存计划成功后清理草稿。preview 结果本身不持久化，刷新期间仍在运行的后端 preview 请求不会自动回填到新页面。
- `NO_PARSED_MATERIAL` 在向导内提示先上传并等待资料解析完成；`DIAGNOSTIC_STALE` 提示重新获取问题并作答；其他错误透传 API message 或显示通用失败提示。

已知性能观察：真实 preview 依赖 `study_plan_generator` 模型执行 map/reduce 两段结构化生成；本地日志中 `deepseek-v4-flash` 单次 preview 曾耗时约 184-196 秒，其中两段 `generate_structured` 分别约 86-100 秒。诊断 questions/profile 接口本身通常为毫秒级，不是 preview 慢的主要来源。

验证入口：

- `frontend/tests/pages/study-plan-pages.test.tsx` 覆盖诊断题加载、答题、profile 生成以及 preview payload 携带 `diagnostic_profile`。
## 2026-07-14 C4 创建向导资料范围选择落地

创建页已将 C2/C3 阶段“固定全部已解析资料”的临时约束替换为真实资料范围选择器。入口为 `frontend/src/features/study-plans/components/StudyPlanMaterialScopeSelector.tsx`，由 `frontend/src/pages/StudyPlanCreatePage.tsx` 挂载并维护 `materialScope` 状态。

- 创建页通过 `frontend/src/features/materials/api.ts::listMaterials(courseId)` 读取当前课程资料，只允许 `parse_status = "parsed"` 的资料进入 Agent 生成范围；解析中、待解析或解析失败的资料只展示状态，不可勾选。
- 支持两种 `MaterialScope`：全部已解析资料 `{ include_all_parsed_materials: true, material_ids: [] }`，以及指定资料 `{ include_all_parsed_materials: false, material_ids: [...] }`。前端不提交文件夹 ID，文件夹仍只用于资料管理归类。
- 配置解析、学前诊断问题、诊断 profile、preview 和 save 都读取同一份 `materialScope`。因此用户切换资料范围后，后续所有请求都会使用最新选择。
- 资料范围变化会清空当前配置解析未补齐提示、清空已有 `diagnostic_profile`，并把已生成 preview 标记为过期，从而禁用保存，要求用户重新生成 preview。
- 创建页草稿会随 courseId 持久化 `materialScope`，刷新后恢复用户选择；保存计划成功后仍清理草稿。
- 测试入口：`frontend/tests/pages/study-plan-pages.test.tsx` 增加“指定已解析资料进入 parse 和 preview 请求”的用例。当前本地 Vitest 仍受 `entities ./decode` exports 问题阻塞在测试收集前，需以 build 和后续依赖修复后的 Vitest 共同验证。
