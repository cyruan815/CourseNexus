# 学习计划基础界面接入

## 当前范围

前端已将学习计划从课程详情摘要入口推进到基础创建 / 详情闭环，但只接入已确认契约。

- 创建页路由：`/courses/:courseId/study-plans/new`，页面入口为 `frontend/src/pages/StudyPlanCreatePage.tsx`。
- 详情页路由：`/courses/:courseId/study-plans/:planId`，页面入口为 `frontend/src/pages/StudyPlanDetailPage.tsx`。
- 学习计划 API 独立封装在 `frontend/src/features/study-plans/api.ts`，类型在 `frontend/src/features/study-plans/types.ts`。
- 课程详情左侧学习计划卡片读取 `GET /api/v1/courses/{course_id}/study-plans`；无计划时跳转创建页，有计划时计划标题跳转详情页。
- 2026-07-13 C1 已将前端学习计划 API/type 适配层扩展到 S02 生命周期接口：配置解析、学前诊断问题、诊断 profile、preview、保存、列表、详情、重生成 preview、替换和删除。该变更只提供 adapter，不在现有页面启用诊断、重生成、替换或删除交互。
- 2026-07-13 C3 已在创建页接入配置自动解析回填：用户输入自然语言目标后，前端调用 `POST /api/v1/courses/{course_id}/study-plan-config-parses`，把后端明确解析出的目标、日期、每日时长和学习方式回填到可编辑表单；`unresolved_fields` 只展示当前页面真实可编辑且仍无有效值的字段，系统追溯字段不展示为“需手动补齐”。
- 2026-07-15 创建页改为自动生成闭环：用户只在首屏输入自然语言目标；提交后前端自动解析配置并获取学情诊断题，中间卡片展示轻量问卷准备动画；随后同一张卡片切换为混合问卷，把缺失日期 / 天数补问和后端 LLM 学情诊断题放在一起；问卷提交后自动生成诊断 profile、调用 preview、保存 `wizard_v1` exact tasks。计划生成等待态展示日历拆分动画，生成完成后把本次 preview tasks 回填到日历格子供用户预览，并由用户点击“进入计划”跳转计划详情页。等待态只表现前端等待状态，不代表新增后端日志流接口。

## 创建页状态流转

- 用户先填写自然语言 `goal_text`，点击“提交”。当前创建页不再展示资料范围选择器、开始日期、结束日期、每日时长和学习方式的大表单；资料范围默认使用本课程全部已解析资料，仍会在进入流程前校验至少有一份 parsed 资料。
- 提交目标后，前端用当前 `goal_text` 和当前 `material_scope` 请求配置解析，再用解析后的配置请求学情诊断题。等待期间中间卡片展示轻量问卷准备动画，只保留标题、说明和沿卡片边框持续流动的等待动效，不显示伪日志或步骤文字，不提供伪造后端能力。
- 问卷阶段把前端补问和后端诊断题合并展示。当前后端 `StudyPlanBuildRequest` 仍要求 `start_date`，并要求 `end_date` 或 `duration_days` 至少一个；诊断 profile 还不返回日期或天数。因此自然语言解析后若仍缺少完整日期范围，前端在问卷顶部同时展示开始日期和学习天数补问：开始日期提供 A 今天 / B 明天 / C 下周一 / D 自定义开始日期，学习天数提供 A 2 天 / B 3 天 / C 7 天 / D 自定义学习天数。前端用日历日期运算派生 `end_date`，并把最终 `start_date + end_date` 放入 preview / save 请求。每日学习时长仍不作为必填项。
- `daily_available_minutes` 不作为创建页必填项；只有自然语言解析出有效每日时长时才随 preview 请求提交，否则省略，让后端按资料量估算。`preference` 未解析时使用默认 `balanced`。
- 提交问卷前必须回答所有必填诊断题，并补齐完整学习日期范围；否则不调用 profile、preview 或 save。
- 点击“提交问卷”后前端自动依次调用 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles`、`POST /api/v1/courses/{course_id}/study-plans/preview` 和 `POST /api/v1/courses/{course_id}/study-plans`；用户不再看到手动预览 Modal、重新生成按钮或保存按钮。
- 创建页对 preview/save 的关键 `ApiError.code` 使用可恢复提示：`NO_PARSED_MATERIAL` 引导先上传或等待资料解析完成，`MATERIAL_COVERAGE_INCOMPLETE` 引导调整资料范围，`PREVIEW_TASKS_REQUIRED` 引导重新生成预览，`IDEMPOTENCY_CONFLICT` 引导重新生成预览后保存，`STATE_CONFLICT` 引导刷新或重新创建计划，避免直接把后端技术 message 暴露给用户。
- 保存请求携带 `Idempotency-Key`，并提交 `client_flow = "wizard_v1"`、preview `title` 与 preview exact `tasks`；保存成功后跳转计划详情页。当前自动闭环每次提交问卷只发起一次保存尝试，失败后停留在问卷阶段供用户重试。

## 详情页状态流转

- 调用 `GET /api/v1/study-plans/{plan_id}` 获取 `plan`、`tasks`、`subtasks` 后只读展示。
- 任务状态、子任务类型做中文 fallback；未知枚举保留原值展示。
- 学习执行入口已跳转 `/study-subtasks/{subtask_id}`，由执行页读取 execution context 并完成 / 取消完成二级任务。
- 计划重新生成已接入详情页内生命周期面板：用户调整目标、日期、每日学习时长和学习方式后调用 `POST /api/v1/study-plans/{plan_id}/regeneration-previews`；该 preview 不落库。
- 用户确认替换时调用 `PUT /api/v1/study-plans/{plan_id}`，提交新 preview 的 `title`、exact `tasks`、`material_scope`、`client_flow = "wizard_v1"` 和当前详情的 `expected_updated_at`。后端若返回 `STATE_CONFLICT`，前端只提示刷新或新建计划，不强行覆盖。
- 删除计划已接入二次确认；确认后调用 `DELETE /api/v1/study-plans/{plan_id}`，成功回到课程详情页。删除是软删除，不删除课程资料或已有生成内容。
- 导出计划仍保持 disabled / 后续接入；学习计划自身没有前端伪造导出。C11 只在执行页为已有成功 `handout` 提供 PDF 导出、为已有成功 `task_test` 提供 Markdown 导出。

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

`types.ts` 对齐后端 S02/S03/S04/S06 schema：`StudyPlanPreviewRequest` 支持 `end_date` 或 `duration_days` 描述日期范围，`daily_available_minutes` 可省略以使用后端推荐值；诊断题、诊断答案、诊断 profile、配置解析、重生成 preview、替换请求、today todos、全局 calendar、单课程 study calendar、learning execution、任务级问答、handout/task-test 和 export 均有独立类型。

2026-07-14 前端计划详情页改为课程计划页结构：`StudyPlanDetailPage` 先读取当前 `GET /api/v1/study-plans/{plan_id}`，同时读取 `GET /api/v1/courses/{course_id}/study-plans` 作为左侧计划列表；左侧按 `updated_at/created_at` 倒序列出本课程多个计划，点击计划卡走 `/courses/{course_id}/study-plans/{plan_id}` 路由切换；右侧保留原计划详情、重生成、删除、开始学习和任务结构内容。该页面仍是工作台页，外层固定视口，左侧计划列表和右侧详情各自滚动。

## 2026-07-14 C5 本课程计划日历前端接入

`frontend/src/pages/CalendarPage.tsx` 已识别 `/calendar?courseId={course_id}` 并进入本课程日历模式；无 `courseId` 时继续保留全局大日历占位，等待 C7。

- `frontend/src/features/study-plans/api.ts::fetchCourseStudyCalendar(courseId, month)` 调用 `GET /api/v1/courses/{course_id}/study-calendar?month=YYYY-MM`。
- `frontend/src/features/study-plans/api.ts::fetchCourseStudyCalendarDay(courseId, date)` 调用 `GET /api/v1/courses/{course_id}/study-calendar/days/{date}`。
- 月视图只展示后端日期摘要；点击日期后才读取当天任务树。
- 任务卡在有可执行二级任务时优先跳转 `/study-subtasks/{subtask_id}`，没有可执行子任务时退回计划详情；日历页本身仍不写完成状态。

测试入口：

- `frontend/tests/features/study-plans/api.test.ts`
- `frontend/tests/pages/calendar-page.test.tsx`

## 2026-07-13 C2 学情诊断向导前端接入

历史阶段：创建页曾从占位的“学情诊断 disabled”切换为真实轻量向导，入口为 `frontend/src/features/study-plans/components/DiagnosticWizard.tsx`。2026-07-15 后当前创建页已改为单页混合问卷，不再挂载该组件。

- 点击“开始学情诊断”调用 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions`，请求发送当前 `goal_text`、当前 `material_scope` 和 `confirmed_config`。`confirmed_config` 包含前端已确认或已解析出的 `start_date`、`duration_days`、`preference`、`daily_available_minutes` 和 `daily_minutes_source`；字段可为 `null`。
- 向导按后端返回的 `sort_order` 展示题目；`topic_mastery` 和 `weak_area` 使用单选，`diagnostic_note` 使用可选文本输入。
- 点击“提交诊断”调用 `POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles`，只把用户答案、`question_version` 和 `material_scope` 交给后端归纳，前端不伪造 profile。
- 后端返回的 `StudyPlanDiagnosticProfile` 保存在创建页状态中；后续点击“生成预览”时作为 `diagnostic_profile` 放入 `StudyPlanPreviewRequest`。
- 学情诊断在创建页为必填；未完成诊断时不允许生成 preview。
- 修改 `goal_text` 或 `material_scope` 会清空已有诊断 profile；解析回填每日时长、学习方式或已识别日期只会让 preview 过期，默认保留诊断结果。
- 创建页会按 courseId 将 `goal_text`、已识别日期、每日时长、资料范围和已生成的诊断 profile 写入浏览器 `localStorage` 草稿；刷新页面后恢复这些输入，保存计划成功后清理草稿。用户修改 `goal_text` 时，前端会清空旧目标解析出的日期、天数、每日时长和学习方式，避免新目标缺少日期时被旧草稿误判为已补齐。preview 结果本身不持久化，刷新期间仍在运行的后端 preview 请求不会自动回填到新页面。
- `NO_PARSED_MATERIAL` 在向导内提示先上传并等待资料解析完成；`DIAGNOSTIC_STALE` 提示重新获取问题并作答；其他错误透传 API message 或显示通用失败提示。

已知性能观察：真实 preview 依赖 `study_plan_generator` 模型执行 map/reduce 两段结构化生成；本地日志中 `deepseek-v4-flash` 单次 preview 曾耗时约 184-196 秒，其中两段 `generate_structured` 分别约 86-100 秒。诊断 questions/profile 接口本身通常为毫秒级，不是 preview 慢的主要来源。

验证入口：

- `frontend/tests/pages/study-plan-pages.test.tsx` 覆盖诊断题加载、答题、profile 生成以及 preview payload 携带 `diagnostic_profile`。
## 2026-07-14 C4 创建向导资料范围选择落地

历史阶段：创建页曾将 C2/C3 阶段“固定全部已解析资料”的临时约束替换为真实资料范围选择器，入口为 `frontend/src/features/study-plans/components/StudyPlanMaterialScopeSelector.tsx`。2026-07-15 自动闭环版本暂不在首屏展示资料范围选择器，当前默认使用全部已解析资料。

- 创建页通过 `frontend/src/features/materials/api.ts::listMaterials(courseId)` 读取当前课程资料，只允许 `parse_status = "parsed"` 的资料进入 Agent 生成范围；解析中、待解析或解析失败的资料只展示状态，不可勾选。
- 支持两种 `MaterialScope`：全部已解析资料 `{ include_all_parsed_materials: true, material_ids: [] }`，以及指定资料 `{ include_all_parsed_materials: false, material_ids: [...] }`。前端不提交文件夹 ID，文件夹仍只用于资料管理归类。
- 配置解析、学前诊断问题、诊断 profile、preview 和 save 都读取同一份 `materialScope`。因此用户切换资料范围后，后续所有请求都会使用最新选择。
- 资料范围变化会清空当前配置解析未补齐提示、清空已有 `diagnostic_profile`，并把已生成 preview 标记为过期，从而禁用保存，要求用户重新生成 preview。
- 创建页草稿会随 courseId 持久化 `materialScope`，刷新后恢复用户选择；保存计划成功后仍清理草稿。
- 历史测试入口曾覆盖“指定已解析资料进入 parse 和 preview 请求”、必选诊断、预览 Modal、保存幂等键复用和重新生成后幂等键刷新；当前页面测试改为覆盖混合问卷、日期补问、自动 profile/preview/save 和失败恢复提示。

## 2026-07-14 C13 创建页流程重构

创建页已按后端诊断承接未解析信息的方向重构，前端不再为日期和每日时长单独补问。

- 页面主体只保留自然语言学习目标、资料范围选择器、必填学情诊断和生成预览入口；不再展示开始日期、结束日期、每日时长、学习方式的大表单。
- 当前后端 preview / save 构建请求仍要求日期范围；当前端没有从自然语言解析出日期时，不再展示“必要信息补齐”区域，而是让诊断 / 后端承担缺失信息。若后端尚未支持缺日期 preview，前端会展示后端返回的错误。
- 每日学习时长不再由创建页要求用户填写；只有自然语言解析出有效分钟数时才提交 `daily_available_minutes` 与 `daily_minutes_source = "user_text"`，否则由后端估算并在 preview 响应中展示“每日建议”。
- `DiagnosticWizard` 语义从“可选”改为“必填 / 已完成”，并接收创建页传入的 `confirmedConfig` 后发送给 `study-plan-diagnostic-questions`。目标或资料范围变化会清空已有诊断结果。
- 预览展示改为 Mantine 大 Modal；Modal 内展示任务树、日期、每日建议时长和容量提示，并提供“重新生成”和“保存计划”。创建页不再保留右侧工作台预览栏。
- 保存仍走 `wizard_v1 + exact preview tasks + Idempotency-Key`，不在保存时重新生成计划。
- 预览 Modal 和计划详情页共用防御式任务说明展示：只有描述开头附近明确出现“短标签 + 冒号”的结构化片段时才分行，例如 `目标：`、`方法：`、`检查：`、`含义：`、`步骤：`；普通任务描述保持原文展示；子任务类型 badge 固定宽度，避免“学习 / 复习 / 练习”被压成单字。
- 计划详情页不再展示 `related_material_ids_json` 这类内部资料 ID；后续若后端返回资料名快照，再展示用户可理解的资料名称。
- 计划详情页的重生成配置区、替换预览区和任务结构区按同一右侧详情滚动流排列，不再让任务结构卡片内部单独滚动；创建页 preview 失败提示放在“生成计划预览”按钮下方，靠近触发动作。

## 2026-07-15 创建页自动闭环修正

C13 的“预览确认 Modal”已被当前创建页自动流程取代，代码入口仍是 `frontend/src/pages/StudyPlanCreatePage.tsx`。

- 首屏只保留自然语言目标输入；点击“提交”后自动调用配置解析和诊断题生成。
- 等待配置解析 / 诊断题生成时，中间卡片展示轻量问卷准备动画，只保留标题、说明和沿卡片边框持续流动的等待动效；等待 profile / preview / save 链路时，中间卡片展示日历拆分动画，保留月份左右切换用于预览计划落点，不提供年月浮层或伪造后端进度日志。
- 计划生成等待页不再读取当前课程已有计划日历摘要，也不展示已有计划占用。保存完成前日历保持空格子；保存完成后前端把本次 preview tasks 回填到对应日期小格，并显示“进入计划”按钮，由用户确认预览后手动跳转计划详情页。
- 创建页不再挂载工作台顶栏；页面内只保留“返回上一步”和“回到课程详情”。“返回上一步”用于从问卷阶段回到目标输入阶段，并清空已生成问卷和当前错误。
- 解析后缺少日期范围时，补问作为问卷题目展示，不恢复旧大表单：开始日期为 A 今天 / B 明天 / C 下周一 / D 自定义；学习天数为 A 2 天 / B 3 天 / C 7 天 / D 自定义。只要日期范围不完整，这两组轻量单选题会一起出现在问卷顶部，选完后仍保留在问卷中供用户确认或改选，前端派生 `end_date`。
- 后端返回的学情诊断题和前端日期补问在同一张问卷中展示；用户点击“提交问卷”后，前端自动生成诊断 profile、生成 preview、保存计划并跳转详情页。
- 当前创建页不再挂载 `DiagnosticWizard`、`StudyPlanMaterialScopeSelector`、预览 Modal、重新生成按钮或手动保存按钮；页面测试入口仍为 `frontend/tests/pages/study-plan-pages.test.tsx`。
