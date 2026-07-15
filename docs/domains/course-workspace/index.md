# Course Workspace 课程详情工作台

## Frontend Interaction Notes

- 2026-07-13: In the course detail workspace, the default material scope follows the PRD and backend contract: no explicit partial selection means the current course's full parsed material set and sends `{ include_all_parsed_materials: true, material_ids: [] }`. If a partial selection is cleared to empty, the frontend returns to the full parsed-material scope instead of sending `{ include_all_parsed_materials: false, material_ids: [] }`.
- 2026-07-13: The left material list can represent the default full parsed-material scope with all visible checkboxes empty. If the user explicitly checks every parsed material, the top "全部已解析资料" checkbox also becomes checked; clearing the final individual checkbox returns to the default full-scope state with visible checkboxes empty.
- 2026-07-13: The Q&A material scope label updates immediately when the left material selection changes. Partial selections render a single-line label that keeps the fixed prefix `资料范围：已选择` and suffix `共 N 份资料` visible while allowing the middle material-name list to ellipsize.
- 2026-07-13: The Q&A panel keeps a continuous local message list: user questions are appended immediately, assistant answers append after the API returns, the send button shows loading while the request is pending, and failed answers keep the user message plus an assistant error bubble. Assistant answers render Markdown through `react-markdown` without dangerous HTML, covering paragraphs, lists, bold text, headings and code blocks.
- 2026-07-13: Course detail headers render readable academic terms by mapping `AUTUMN` / `autumn` to `秋季` and `SPRING` / `spring` to `春季`, while keeping the year prefix. The course description is intentionally omitted from this page header.
- 2026-07-13: The Q&A card is a fixed work surface: the conversation area owns scrolling, and the material-scope line plus question input stay anchored at the card bottom. The question textarea starts at about two rows, grows up to about five rows, then scrolls internally.
- 2026-07-13: The study-plan area shows at most one plan, selected by latest `updated_at` / `created_at`. Existing plans render as a rounded bordered summary card that links to `/courses/{course_id}/study-plans/{plan_id}`; the action row stays right-aligned and includes a blue "查看更多" entry to `/calendar?courseId={course_id}`. The calendar route is an integration point for later course-filtered calendar behavior, not a fully closed study-mode calendar in this task.
- 2026-07-13: The study-plan create page now saves through the new wizard contract: `client_flow = "wizard_v1"`, exact preview `tasks`, and an `Idempotency-Key` header. The page still keeps diagnostic, regeneration, replacement, execution, and calendar views as follow-up front-end work instead of pretending those flows are complete.
- 2026-07-14: `/calendar?courseId={course_id}` now opens the real single-course study calendar. It reads the S03 course month endpoint for date summaries and the course day endpoint after the user selects a date; it remains read-only and links tasks back to existing study plan detail pages instead of inventing an execution route.
- 2026-07-14: The home workbench mini calendar intentionally stays compact: each day cell shows one task title line with ellipsis plus one independent progress line. Multi-task per-day expansion belongs to the full calendar page, not the mini calendar.
- 2026-07-15: Calendar day task details display primary task progress as `completed/total` only. Subtask rows omit description bodies and render as a divider-separated list inside the parent task block, not as individual bordered cards.
- 2026-07-15: Grounded answers render backend `[[cite:N]]` markers as small inline citation buttons. Hovering a marker shows the source material name, page and saved `hit_text` snapshot. Historical messages use the same `source_citations` contract; legacy answers with citations but no inline markers append their markers at the end instead of losing the sources.

## 概述

课程详情工作台承载单门课程内的资料管理、资料范围、课程问答、AI 学习工具入口、AI 生成内容记录和学习计划入口。当前前端已经从静态预览进入后端接入阶段：正式课程详情页读取后端课程、资料、生成内容、学习计划，并可以基于当前资料范围发送课程问答和触发基础生成接口。

## 业务目标

- 让学生在单门课程内管理资料，并明确哪些资料会进入问答和生成上下文。
- 让学生基于课程资料向 Agent 提问，并展示后端返回的回答、answer_type 和引用来源。
- 让学生从右侧学习工具触发后端已注册的生成类型，并在生成内容列表中看到记录。
- 在学习计划未创建时提供制定计划入口；已有计划时展示最近更新的计划摘要，并提供跳转到课程计划日历的入口。

## 当前范围

已实现：

- 正式路由 `/courses/:courseId` 读取 `GET /api/v1/courses/{course_id}`。
- 左侧资料区复用 `MaterialWorkspace`，读取资料文件夹、资料列表，并支持上传、解析、重试、删除和资料范围选择。首页创建课程成功后跳转到课程详情页时，会通过路由 state 触发一次可关闭的上传资料提示。
- 中间问答区调用 `POST /api/v1/courses/{course_id}/qa/questions`，传入当前 `material_scope`，展示回答、`grounded` / `no_source` 状态和真实引用来源。
- 回答中的 `[[cite:N]]` 引用标记渲染为行内序号角标，鼠标悬停后显示资料名、页码和引用片段；历史消息接口返回同一引用快照，刷新后仍可查看。
- 问答区以连续消息形式展示当前会话内的用户消息和 AI 消息；发送中只使用发送按钮 loading 表示，失败时保留用户问题并追加短错误气泡。
- 课程详情页顶部不展示课程简介；学期字段在前端统一转换为用户可读季节标签。
- 右侧工具区调用 `POST /api/v1/courses/{course_id}/generations`，支持后端当前注册的 `quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`；支持生成的工具以整张卡片作为操作入口，不再额外显示内嵌“生成”按钮。
- AI 生成内容列表读取 `GET /api/v1/courses/{course_id}/generated-contents`，列表记录整张卡片可进入生成内容详情页 `/generated-contents/:generatedContentId`。
- 今日待办 / 学习计划区域读取 `GET /api/v1/courses/{course_id}/study-plans`；无计划时展示“制定学习计划”入口，有计划时按 `updated_at` / `created_at` 优先展示最近更新的一条计划摘要，摘要以圆角边框卡片形式链接到计划详情，不在卡片内展开多计划列表。“查看更多”入口跳转 `/calendar?courseId={course_id}`，进入本课程只读学习日历。
- 课程详情页顶部主题切换按钮已接入本地浅色 / 深色模式骨架；个人中心和制定学习计划入口仍以待接入禁用态展示。今日待办查看和 AI 生成内容“查看全部”在没有真实页面或接口闭环前不渲染占位按钮。
- 开发预览路由 `/preview/course-detail` 仅在 `import.meta.env.DEV` 下注册，用 mock 数据预览布局，不影响正式登录保护和正式路由。

未实现：

- 资料预览视图和引用点击定位；当前悬浮卡片只展示后端保存的引用快照。
- 对话历史选择、会话管理完整 UI 和跨会话切换。
- Quiz、Flashcard、Mindmap、复习提纲、知识点清单的最终专属学习交互页；当前仅有生成内容基础详情页。
- 计划今日待办的真实当日任务聚合和任务执行入口。
- 保存回答为笔记入口。

## 代码入口

- 页面入口：`frontend/src/pages/CourseDetailPage.tsx`
- 本课程日历入口：`frontend/src/pages/CalendarPage.tsx`
- 开发预览页：`frontend/src/pages/CourseDetailPreviewPage.tsx`
- 路由：`frontend/src/router/AppRouter.tsx`
- 样式：`frontend/src/pages/course-detail.css`
- 课程工作台 API：`frontend/src/features/course-workspace/api.ts`
- 课程工作台类型：`frontend/src/features/course-workspace/types.ts`
- 资料工作区：`frontend/src/features/materials/MaterialWorkspace.tsx`
- 生成内容详情页：`frontend/src/pages/GeneratedContentDetailPage.tsx`

## 模块边界

- `CourseDetailPage` 负责课程详情页级数据编排：课程、生成内容、学习计划、问答请求和当前资料范围。
- `features/course-workspace/api.ts` 只封装课程工作台相关后端接口，不直接处理 UI 状态。
- `MaterialWorkspace` 仍归属 `materials` 领域，课程详情页只传入 `courseId`、`materialScope`、`onMaterialScopeChange` 和可选的创建后上传提示开关。
- 问答、生成和学习计划只通过后端公开 API 使用资料范围；前端不得直接读取资料 chunk 或伪造引用来源。

## 状态流转

- 课程 loading：展示课程详情骨架。
- 课程 error：展示课程加载失败 alert。
- 资料区：沿用 `materials` 领域状态，包括 loading、empty、error、ready 和 mutating。若从首页创建课程成功后进入详情页，资料区初次挂载时展示“上传课程资料”提示，用户可以上传文件，也可以直接关闭；普通进入课程详情页不自动弹出。
- 问答区：无回答时展示空态；输入为空或发送中禁用发送；发送后立即追加用户消息，按钮进入 loading；成功后追加 AI 回答和引用；失败时保留用户消息并追加 assistant error 气泡，不用全局工作区错误替代聊天记录。
- 生成内容：页面加载时读取列表；点击支持的工具后进入 pending；成功后把返回的 `GeneratedContentRead` 插入列表；失败时展示工作区错误提示。
- 学习计划：无计划时展示制定计划入口；有计划时展示最近更新的一条可点击摘要卡片，并提供新建计划和查看更多入口；不伪造今日任务。

## 关键决策

- PRD 的三栏结构是信息架构依据，但视觉不照搬线框图；采用亮色课程工作台风格。
- 学习计划入口与今日待办合并：无计划时是小型行动入口，有计划后展示课程内最近更新计划摘要卡片；“查看更多”跳转 `/calendar?courseId={course_id}`，由 `CalendarPage` 读取课程月历和当日任务聚合。
- 资料范围使用后端 `MaterialScope` 结构，一级文件夹只作为浏览归类，不作为 Agent 上下文范围。
- 创建课程与上传资料解耦：创建课程只写入课程基础信息；创建成功后由课程详情页弹出可关闭的上传资料提示，引导用户继续补资料，但不阻塞课程创建结果。
- 右侧工具只接后端当前注册生成类型：`quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`。后端当前没有一键生成 `note` 的工具闭环，“学习笔记”不再作为学习工具卡片展示；历史 `note` 内容类型仍保留为保存问答后的兼容类型。
- 功能模块保持 2 列网格；支持生成的卡片整卡触发生成，不展示额外“生成入口”徽标；“知识点清单”作为重点复习入口跨整行展示。
- 课程详情页桌面工作台高度贴合当前视口，资料列表和 AI 生成内容列表作为局部滚动区，避免页面级滚动条挤压三栏工作台。
- 问答区同样采用局部滚动：对话历史在卡片中部滚动，底部资料范围和输入区不随长对话或长输入被顶出卡片。
- 没有 PRD / 后端闭环的“查看全部”和今日待办查看动作不保留假入口；需要对应列表页、聚合接口或交互闭环后再接入。
- 生成接口当前后端仍可能由 deterministic placeholder 提供具体类型 fallback，前端详情页只做基础结构化展示和引用展示，不把结果渲染成最终学习产品页面。

## PRD / 后端 / 前端一致性缺口

当前后端已有但前端未完全实现：

- 对话列表和消息列表 API 已有，当前会加载最新对话及其带引用消息，但前端尚未提供会话列表、跨历史会话切换和完整会话管理 UI。
- 生成内容详情 API 已接入基础详情页，但尚未提供各内容类型的最终专属学习交互。
- 学习计划预览、保存、列表和详情 API 已有；课程详情页已接入计划列表摘要、创建入口和详情入口，创建页保存已使用 `wizard_v1` 确认任务树契约，本课程日历已接入课程维度 S03 只读聚合接口。

PRD 要求但当前后端能力不足或未形成完整接口：

- 资料预览和引用定位视图需要前后端进一步定义可打开的资料预览 URL、页码定位和片段定位协议。
- 首页大日历、全局当日待办弹窗、计划执行页和任务完成同步仍缺前端页面；对应聚合接口以后端 `todos-calendar` 契约为准。本课程计划学习模式日历已接入课程维度 S03 只读接口。
- Quiz、Flashcard、Mindmap、复习提纲、知识点清单当前后端生成器是占位实现，未达到 PRD 中专属结构化结果和交互页面要求。
- 保存回答为笔记的前端入口和后端专用操作尚未形成完整闭环；数据模型支持 `note`，但课程详情页暂未接。

## 测试与验证

- API 测试：`frontend/tests/features/course-workspace/api.test.ts`
- 页面测试：`frontend/tests/pages/course-detail.test.tsx`
- 行内引用测试覆盖新回答角标、悬浮引用片段、页码展示、历史消息引用恢复和旧回答兼容。
- 路由测试：`frontend/tests/pages/app-router.test.tsx`
- 当前阶段验证命令：

```powershell
pnpm frontend:test
pnpm frontend:build
```

Windows 沙盒中如果出现 `esbuild spawn EPERM`，需要提权重跑验证命令；这是环境权限问题，不是源码错误。
