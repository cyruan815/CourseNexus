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

## 3. 当前状态

- G01：全材料批次、用途模型注入、生成器工厂、引用过滤与回填、原子持久化、历史/详情引用响应已经实现。
- G02-G06：仍由 deterministic placeholder 提供增量开发 fallback，不代表最终内容质量或业务 schema 已完成。
- 当前没有队列、取消、进度查询或持久化幂等键；重复请求生成独立记录。
- 前端已接入生成内容详情基础闭环：课程详情页生成内容列表中的记录可跳转到 `/generated-contents/:generatedContentId`，详情页调用 `GET /api/v1/generated-contents/{generated_content_id}`，展示标题、类型、状态、结构化结果基础视图和后端返回的真实引用来源。
- 前端详情页只渲染后端返回内容，不补造引用、统计或最终学习产品交互；`page = null` 且 `page_index = 0` 的引用位置展示为“页码未知”，不得解释为真实第 0 页。
- 生成失败记录展示 `error_code` 和失败态，不伪装成成功内容；引用为空时展示真实空态。

详细架构、算法、资源预算和失败策略见 [architecture.md](architecture.md)。

## 4. 前端状态与限制

- loading：详情加载中展示骨架。
- success：按 `content_type` 做基础结构化渲染，当前覆盖 `quiz`、`flashcard`、`mindmap`、`outline`、`knowledge_list`、`handout`、`task_test` 的可读兜底。
- failed：展示失败提示和 `error_code`，不展示伪结果。
- error：详情接口失败时展示后端错误信息。
- empty citation：`source_citations = []` 时展示“当前没有可展示的引用来源”。

当前前端详情页不是最终 Quiz 做题页、Flashcard 翻卡页、Mindmap 图形编辑页或 PDF 导出页；这些能力仍需等待对应生成器和计划学习模式后续接口闭环。
