# 任务说明书 A：课程工作台与学习计划前端

## 1. 目标与角色

本任务由同学 A 在固定分支 `feature/frontend` 完成。目标是持续完善课程工作台中的资料、问答、课程摘要和学习计划体验，并保证该工作与五类生成内容结果页的开发互不抢占文件。

同学 A 是课程工作台和学习计划前端的唯一文件负责人；不负责 Quiz、Flashcard、Mindmap、复习提纲、知识点清单五类结果的专属渲染页面。

## 2. 开始前置条件与分支规则

1. 先阅读根目录 `AGENTS.md`、`docs/index.md`、`docs/engineering/index.md`、`docs/api-data/contracts.md` 和 `docs/domains/course-workspace/`。
2. 当前 PR #6 未合并时，只允许向该 PR 补充已确认的 Review 修复；不得把新的前端功能继续堆入该 PR。
3. PR #6 的已知正确性门槛：
   - 保存学习计划必须提交用户刚刚预览和确认的 `title`、`tasks` 与 `client_flow = "wizard_v1"`，不得在保存时走 legacy 路径重新生成任务树。
   - `daily_available_minutes` 的前端输入和本地校验下限必须为 30 分钟，与后端一致。
4. PR #6 合并后，从最新 `main` rebase 更新本地 `feature/frontend`；后续任务继续在该固定分支按小功能拆分 commit。
5. 不得直接 push、创建 PR、提交 GitHub review / comment、批准或合并；所有远程写操作必须先获得项目负责人的明确确认。

## 3. 文件所有权

### 3.1 同学 A 可以新增或修改

```text
frontend/src/pages/CourseDetailPage.tsx
frontend/src/pages/course-detail.css
frontend/src/pages/StudyPlanCreatePage.tsx
frontend/src/pages/StudyPlanDetailPage.tsx
frontend/src/pages/study-plan.css
frontend/src/features/study-plans/
frontend/src/features/materials/
frontend/src/features/course-workspace/
frontend/src/features/courses/
frontend/tests/pages/course-detail.test.tsx
frontend/tests/pages/study-plan-pages.test.tsx
frontend/tests/features/study-plans/
frontend/tests/features/materials/
docs/domains/course-workspace/
docs/domains/materials/
docs/api-data/frontend-integration.md（仅在真实前端接入改变契约说明时）
```

`frontend/src/router/AppRouter.tsx` 仅限维护课程工作台和学习计划既有路由；新增或修改前先确认没有与同学 B 的统一生成内容详情路由冲突。现有 `/generated-contents/:generatedContentId` 路由不得删除、改名或改为五类单独路由。

### 3.2 同学 A 不得修改

```text
frontend/src/pages/GeneratedContentDetailPage.tsx
frontend/src/pages/generated-content-detail.css
frontend/src/features/generated-content/
frontend/tests/pages/generated-content-detail.test.tsx
frontend/tests/features/generated-content/
docs/domains/generated-content/
```

这些路径由同学 B 独占。若课程工作台需要新的生成入口、参数表单或回调，不得直接改动同学 B 的文件；先以 Issue、任务卡或明确接口约定提出需求，再安排一次最小集成提交。

### 3.3 双方共同保护的文件

以下文件在并行期默认冻结。任何人需要修改时，必须先向项目负责人说明影响、取得指定文件负责人确认，并安排独立的小提交：

```text
frontend/src/api/client.ts
frontend/src/api/errors.ts
frontend/src/api/types.ts
frontend/src/app/
frontend/src/router/AppRouter.tsx
frontend/package.json
pnpm-lock.yaml
```

不得为了局部页面方便而修改全局鉴权、HTTP 解包、主题 Provider、路由或依赖版本。

## 4. 落地目录和组件边界

学习计划相关代码必须集中在以下边界中，页面只承担路由装配和布局，API / 类型 / 可复用 UI 不继续堆入 `CourseDetailPage.tsx`：

```text
frontend/src/features/study-plans/
  api.ts                     # 学习计划 API 适配
  types.ts                   # 请求、preview、详情的前端类型
  components/                # 可复用的预览、任务树、状态组件
frontend/src/pages/
  StudyPlanCreatePage.tsx    # 创建、preview、确认保存
  StudyPlanDetailPage.tsx    # 只读详情与后续入口占位
  study-plan.css
```

课程详情页只承担以下职责：加载课程工作台数据、组织资料范围、挂载资料区 / 问答区 / 计划摘要 / 通用生成入口，以及在成功生成内容后刷新历史列表。不要把学习计划表单、五类生成结果的专属 renderer 或复杂资料管理逻辑写进同一个页面文件。

## 5. 学习计划实现约束

### 5.1 创建和保存流程

创建页的状态流转必须为：

```text
加载课程 → 填写配置 → 生成 preview → 用户查看 / 确认
→ 保存该 preview 的 exact tasks → 跳转计划详情
```

- 请求和响应字段使用 `snake_case`。
- `material_scope` 只能使用资料 ID 范围；文件夹不能作为 Agent 范围。
- 保存新向导必须使用 `client_flow = "wizard_v1"`，携带 preview 的标题和原样任务树；不得保存时重新请求生成。
- 生成 preview 后任何影响请求体的字段变化，都必须使 preview 过期并禁用保存。
- `daily_available_minutes` 最小 30；开始日期不得晚于结束日期。
- 保存请求必须考虑 `Idempotency-Key` 契约：同一次用户保存操作复用同一 key，网络失败后的重试不得重复创建计划。
- 对 `NO_PARSED_MATERIAL`、`MATERIAL_COVERAGE_INCOMPLETE`、`PREVIEW_TASKS_REQUIRED`、`IDEMPOTENCY_CONFLICT`、`STATE_CONFLICT`、`UNAUTHORIZED` 和通用错误提供可理解的恢复提示；逻辑判断依据为 `error.code`，不是中文错误文案。

### 5.2 详情和边界

- 详情页只读取 `GET /api/v1/study-plans/{plan_id}` 并展示计划、一级任务和二级任务。
- 枚举值必须有未知值兜底；时间、状态、空任务、加载和接口失败均需可见。
- 未接入的重新生成、完成打卡、学习执行、讲义和任务测试题必须明确 disabled / 待接入，不能伪造接口或本地状态。
- 计划保存阶段绝不提前生成讲义或任务测试题正文。

## 6. 与同学 B 的唯一集成面

课程详情的通用生成入口可继续调用既有生成 API 并刷新历史列表，但不得改造为五类结果页。若需要把生成前参数面板接入课程详情，采用以下受控交接方式：

1. 先由项目负责人确定最小 props / 回调契约，例如 `courseId`、`materialScope` 与 `onCreated(content)`。
2. 同学 B 在自己目录实现可嵌入组件；同学 A 仅在 `CourseDetailPage.tsx` 做一次接线。
3. 该接线作为独立 commit，提交前双方都检查 diff；不与学习计划、资料区或结果 renderer 改动混在一起。

在没有该书面交接前，同学 A 不得修改同学 B 的生成内容结果文件；同学 B 也不得修改 `CourseDetailPage.tsx`。

## 7. 测试、文档与提交

- 每个可验证小功能单独 commit，使用 Conventional Commits，例如 `feat(study-plans): 保存已确认的预览任务树`。
- 新增或改变 API 请求边界时，添加 / 更新 API adapter 测试；页面交互使用 Vitest 覆盖成功、加载、空、失败、禁用和关键状态变化。
- 本任务至少运行受影响测试；合入前运行：

```powershell
pnpm frontend:test
pnpm frontend:build
```

- 真实实现完成后同步更新 `docs/domains/course-workspace/`；若资料流程改变，同时更新 `docs/domains/materials/`。文档必须记录实际代码入口、组件边界、状态流转、API 数据流、异常降级和测试入口。
- commit 前检查 `git status`、`git diff` / `git diff --staged`、文件范围、敏感信息和测试结果。仅本地提交，不自动 push。

## 8. 验收清单

- [ ] PR #6 只含 Review 修复并通过重新审查后再合并。
- [ ] 新学习计划保存的任务树与用户确认的 preview 一致。
- [ ] 每日学习时长前后端都拒绝小于 30 分钟的值。
- [ ] 课程工作台、资料、问答和学习计划均有 loading / empty / error / disabled 或 pending 状态。
- [ ] 未修改同学 B 独占的生成内容结果路径。
- [ ] 前端测试、构建、领域文档和小步提交证据完整。
