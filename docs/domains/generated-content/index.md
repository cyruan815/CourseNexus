# Generated Content 领域

## 1. 业务定位

本领域统一承载课程资料生成结果、生成状态、资料范围快照和引用来源。G01 已建立五类独立生成器共用的编排与存储合同；Quiz、Flashcard、Mindmap、Outline 和 Knowledge List 的真实业务生成分别由 G02-G06 实现。

## 2. 代码入口

- 请求与生成编排：`backend/app/modules/generation/orchestrator/`
- 生成器注册入口：`backend/app/modules/generation/orchestrator/registry.py`
- 五类生成器目录：`backend/app/modules/generation/generators/`
- 历史、详情与引用响应：`backend/app/modules/generated_content/`
- 全材料上下文：`backend/app/modules/material_context/`
- 模型调用边界：`backend/app/integrations/model_provider/`
- 公共测试夹具：`backend/tests/modules/generation/conftest.py`
- 前端详情页：`frontend/src/pages/GeneratedContentDetailPage.tsx`
- 前端详情页样式：`frontend/src/pages/generated-content-detail.css`
- 前端生成内容 API 适配：`frontend/src/features/course-workspace/api.ts`
- 前端路由：`frontend/src/router/AppRouter.tsx`
- 本地开发 seed 命令：`backend/app/commands/seed_generated_content_demo.py`
- 本地开发 seed 测试：`backend/tests/commands/test_seed_generated_content_demo.py`

## 3. 当前状态

- G01：全材料批次、用途模型注入、生成器工厂、引用过滤与回填、原子持久化、历史/详情引用响应已经实现。
- G02-G06：仍由 deterministic placeholder 提供增量开发 fallback，不代表最终内容质量或业务 schema 已完成。
- 当前没有队列、取消、进度查询或持久化幂等键；重复请求生成独立记录。
- 前端已接入生成内容详情基础闭环：课程详情页生成内容列表中的记录可跳转到 `/generated-contents/:generatedContentId`，详情页调用 `GET /api/v1/generated-contents/{generated_content_id}`，展示标题、类型、状态、结构化结果基础视图和后端返回的真实引用来源。
- 前端详情页只渲染后端返回内容，不补造引用、统计或最终学习产品交互；`page = null` 且 `page_index = 0` 的引用位置展示为“页码未知”，不得解释为真实第 0 页。
- 生成失败记录展示 `error_code` 和失败态，不伪装成成功内容；引用为空时展示真实空态。
- 来源资料被用户永久删除后，生成内容及其 `SourceCitation` 快照继续保留；`material_id`、`chunk_id` 返回 null，详情页仍使用资料名、页码和命中文本展示历史来源。
- 为了在资料解析 / 索引未配置时手动查看前端详情页，后端提供仅限本地开发使用的 seed 命令。该命令创建或更新固定 demo 用户、课程、已解析占位资料、MaterialChunk、`outline` 生成内容和真实 `SourceCitation`，不新增正式 API，也不代表生产数据生成路径。

详细架构、算法、资源预算和失败策略见 [architecture.md](architecture.md)。

## 4. 前端状态与限制

- loading：详情加载中展示骨架。
- success：按 `content_type` 做基础结构化渲染，当前覆盖 `quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`、`handout`、`task_test` 的可读兜底。
- failed：展示失败提示和 `error_code`，不展示伪结果。
- error：详情接口失败时展示后端错误信息。
- empty citation：`source_citations = []` 时展示“当前没有可展示的引用来源”。

当前前端详情页不是最终 Quiz 做题页、Flashcard 翻卡页、Mindmap 图形编辑页或 PDF 导出页；这些能力仍需等待对应生成器和计划学习模式后续接口闭环。

## 5. 本地手动验收 seed

当本地无法完成资料解析或生成链路时，可运行开发态 seed，插入一条可点击的生成内容详情记录：

```powershell
cd backend
python -m app.commands.seed_generated_content_demo
```

默认登录账号为 `demo@example.com`，密码为 `password123`。命令会输出 `course_id`、`generated_content_id` 和前端路径 `/generated-contents/gen_demo_outline`。

使用规则：

- 只在本地开发数据库中运行，不作为正式产品功能。
- 重复运行是幂等的，会更新同一组固定 demo 记录，不堆积重复生成内容。
- 该 seed 直接写入 `User`、`Course`、`CourseMaterial`、`MaterialChunk`、`AIGeneratedContent` 和 `SourceCitation`，用于绕过暂不可用的解析 / 索引链路，验证前端详情页和后端详情接口。
- 如果后端服务不是从 `backend/` 目录启动，应在运行 seed 时使用同一个工作目录或显式配置相同 `DATABASE_URL`，避免写到另一个 SQLite 文件。
