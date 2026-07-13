# 学习计划基础界面接入

## 当前范围

前端已将学习计划从课程详情摘要入口推进到基础创建 / 详情闭环，但只接入已确认契约。

- 创建页路由：`/courses/:courseId/study-plans/new`，页面入口为 `frontend/src/pages/StudyPlanCreatePage.tsx`。
- 详情页路由：`/courses/:courseId/study-plans/:planId`，页面入口为 `frontend/src/pages/StudyPlanDetailPage.tsx`。
- 学习计划 API 独立封装在 `frontend/src/features/study-plans/api.ts`，类型在 `frontend/src/features/study-plans/types.ts`。
- 课程详情左侧学习计划卡片读取 `GET /api/v1/courses/{course_id}/study-plans`；无计划时跳转创建页，有计划时计划标题跳转详情页。

## 创建页状态流转

- 用户手动填写 `goal_text`、`start_date`、`end_date`、`daily_available_minutes`。
- `material_scope` 当前固定为 `{ include_all_parsed_materials: true, material_ids: [] }`。
- `preference` 当前固定发送英文枚举 `balanced`；学情诊断后端契约已存在，但本基础页暂不接入诊断向导。
- 点击“生成预览”调用 `POST /api/v1/courses/{course_id}/study-plans/preview`。
- 前端保存产生预览时的请求快照；若表单字段在预览后变化，旧预览标记为过期并禁用保存。
- 点击“保存计划”调用 `POST /api/v1/courses/{course_id}/study-plans`，请求携带 `Idempotency-Key`，并提交 `client_flow = "wizard_v1"`、preview `title` 与 preview 中展示过的 `tasks`；保存成功后跳转计划详情页。同一份未变化 preview 的保存重试复用同一个幂等键，只有重新生成 preview 后才创建新的保存幂等键。

## 详情页状态流转

- 调用 `GET /api/v1/study-plans/{plan_id}` 获取 `plan`、`tasks`、`subtasks` 后只读展示。
- 任务状态、子任务类型做中文 fallback；未知枚举保留原值展示。
- 完成打卡、计划重新生成、导出、学习执行入口、学情诊断均保持 disabled / 后续接入；不调用本页尚未形成前端闭环的接口。

## 测试入口

- API 测试：`frontend/tests/features/study-plans/api.test.ts`
- 页面测试：`frontend/tests/pages/study-plan-pages.test.tsx`
- 路由测试：`frontend/tests/pages/app-router.test.tsx`
- 课程详情入口测试：`frontend/tests/pages/course-detail.test.tsx`
