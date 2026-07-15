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

- G01：完整选定材料上下文、总 token 检查、用途模型注入、生成器工厂、单次模型调用和 `AIGeneratedContent` 持久化已经实现。
- G02-G06：Quiz、Flashcard、Mindmap、Outline 和 Knowledge List 均已实现最终结构化 schema、稳定 ID/顺序和失败记录；五类业务 JSON 不包含 chunk/citation ID，顶层 `source_citations` 固定返回空数组。

具体实现文档：

- [quiz.md](quiz.md)
- [flashcard.md](flashcard.md)
- [mindmap.md](mindmap.md)
- [outline.md](outline.md)
- [knowledge-list.md](knowledge-list.md)
- 当前没有队列、取消、进度查询或持久化幂等键；重复请求生成独立记录。
- 前端已接入生成内容详情基础闭环：课程详情页生成内容列表中的记录可跳转到 `/generated-contents/:generatedContentId`，详情页调用 `GET /api/v1/generated-contents/{generated_content_id}`，展示标题、类型、状态和结构化结果基础视图。
- 生成内容支持所有者重命名与永久删除：`PATCH /api/v1/generated-contents/{id}` 仅更新规范化后的标题；`DELETE /api/v1/generated-contents/{id}` 在同一事务内物理删除关联 `source_citations` 和生成内容主记录，正文、结构化结果及生成内容引用快照均不可恢复。跨用户修改统一返回 `NOT_FOUND`。迁移 `20260715_0005` 会清理升级前遗留的软删除记录及其引用。
- 课程详情页的每条生成内容右侧提供三点菜单，前端展示“重命名”“删除”。重命名成功后就地替换该列表项，删除经二次确认后移除该项；请求失败时保留弹窗和原列表数据并显示错误。列表正文区域仍作为详情链接，菜单按钮不触发详情跳转。
- 课程详情页右侧将“学习工具”和生成内容列表放在同一个工作室卡片内，中间使用横向分隔线保持层级；生成内容列表不重复展示分区标题，占用剩余高度并独立滚动，响应式断点下整张卡片保持同一栏。
- 课程详情的生成内容列表不展示学习计划任务讲义：后端列表查询和前端渲染都排除 `content_type=handout` 且 `study_subtask_id` 非空的记录。该过滤只改变课程级列表可见性，任务执行页仍通过 execution-context 内容 ID 查看详情、重新生成和导出 PDF。
- 前端详情页只渲染后端返回内容，不补造引用或统计，也不展示生成信息和引用侧栏；五类 POC 生成内容不提供逐条引用，handout / task_test 的真实引用保留在后端与 API 中供内部追溯和导出。
- 2026-07-14 前端详情页增加 `task_test` 只读 renderer，用于计划学习执行页生成的任务测试题。它展示题目、选项、正确答案和解析，不提供作答、判分、保存记录或 attempt 历史；任务测试题仍不属于五类公共课程生成器。
- 生成失败记录展示 `error_code` 和失败态，不伪装成成功内容。
- 来源资料被用户永久删除后，已保存的生成内容继续保留；`material_scope_json` 是生成时选择范围快照，不是引用契约。
- 为了在资料解析 / 索引未配置时手动查看前端详情页，后端提供仅限本地开发使用的 seed 命令。该命令创建或更新固定 demo 用户、课程、已解析占位资料、MaterialChunk 和五类示例生成内容，不新增正式 API，也不代表生产数据生成路径。

详细架构、算法、资源预算和失败策略见 [architecture.md](architecture.md)。

## 4. 前端结果渲染

- loading：详情加载中展示骨架。
- success：`GeneratedContentDetailPage.tsx` 只负责加载、失败状态、元数据与 renderer 分派；五类独立 renderer 位于 `frontend/src/features/generated-content/renderers/`。
- failed：展示失败提示和 `error_code`，不展示伪结果。
- error：详情接口失败时展示后端错误信息。

Quiz 提供单题即时判题和本地正确率；Flashcard 提供翻卡、掌握/未掌握与错卡重练；Mindmap 直接使用 `markmap-view` 渲染后端预处理树；Outline 提供章节导航；Knowledge List 提供搜索和重要程度筛选。Quiz 作答、Flashcard 练习、Outline 展开和筛选状态仅存在页面内存；Flashcard 添加 / 删除卡片通过完整牌组替换接口写入后端。

`task_test` 使用 `TaskTestResult` 只读展示 `content_json.questions`，与课程自测 Quiz 的本地判题交互分开。它只服务计划学习执行页的任务测试题查看和 Markdown 导出，不保存学生答案。

### 已确认、待实施：五类详情页标题统一

课程详情页的生成内容卡片与点入后的详情页将共用同一个标题格式化入口，统一显示为“功能名 · 主题标题”，避免列表与详情页采用两套规则。五类功能的目标形式如下：

- `思维导图 · 第七章 物理层`
- `知识闪卡 · 第七章 物理层`
- `Quiz · 第七章 物理层`
- `复习提纲 · 第七章 物理层`
- `知识点清单 · 第七章 物理层`

实现时由详情页复用 `generatedContentTitle(contentType, storedTitle)`，后端继续只存储主题标题，功能名称及本地化展示由前端负责。多份材料使用生成阶段提炼出的共同主题；历史记录继续沿用现有兼容规则，过滤括号、数量描述和重复的功能名前缀。本项当前仅保存为已确认设计，尚未修改系统代码。

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
- 该 seed 直接写入 `User`、`Course`、`CourseMaterial`、`MaterialChunk` 和五类 `AIGeneratedContent`，不写 `SourceCitation`，用于绕过暂不可用的解析 / 索引链路，验证前端详情页和后端详情接口。
- 如果后端服务不是从 `backend/` 目录启动，应在运行 seed 时使用同一个工作目录或显式配置相同 `DATABASE_URL`，避免写到另一个 SQLite 文件。
