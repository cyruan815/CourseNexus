# 任务说明书 B：五类生成内容结果页前端

## 1. 目标与角色

本任务由同学 B（原五类生成材料功能开发者）在固定分支 `feature/generation` 完成。目标是把后端已持久化的五类生成内容变成可阅读、可交互、可恢复的前端结果页：

- `quiz`：课程自测题
- `flashcard`：记忆卡片
- `mindmap`：思维导图
- `outline`：复习提纲
- `knowledge_list`：知识点清单

本任务只处理“生成成功后查看结果”的前端渲染。不接入或修改课程详情页的生成入口，不实现资料选择、生成前配置表单、学习计划、任务执行、讲义或任务测试题页面。

## 2. 开始前置条件与分支规则

1. 先阅读根目录 `AGENTS.md`、`docs/index.md`、`docs/api-data/contracts.md`、`docs/api-data/frontend-integration.md`、`docs/api-data/mindmap-frontend-handoff.md` 和 `docs/domains/generated-content/`。
2. 从最新 `main` 更新本地 `feature/generation` 后开始；使用 rebase 同步，不使用普通 merge。
3. 本任务的后端公开读取接口已经稳定：

```text
GET /api/v1/generated-contents/{generated_content_id}
```

4. 五类结果统一复用现有路由 `/generated-contents/:generatedContentId`。不得为五类内容新增五条路由，也不得修改 `CourseDetailPage.tsx`。
5. 不得直接 push、创建 PR、提交 GitHub review / comment、批准或合并；所有远程写操作必须先获得项目负责人的明确确认。

## 3. 文件所有权

### 3.1 同学 B 可以新增或修改

```text
frontend/src/pages/GeneratedContentDetailPage.tsx
frontend/src/pages/generated-content-detail.css
frontend/src/features/generated-content/
frontend/tests/pages/generated-content-detail.test.tsx
frontend/tests/features/generated-content/
docs/domains/generated-content/
docs/api-data/mindmap-frontend-handoff.md（仅在已确认的前端渲染契约变化时）
```

`GeneratedContentDetailPage.tsx` 应逐步收敛为路由参数、加载 / 错误页壳和 renderer 分派入口；五类具体 UI 放入 `features/generated-content/`，不要继续把所有类型分支堆在页面文件中。

### 3.2 同学 B 严禁修改

```text
frontend/src/pages/CourseDetailPage.tsx
frontend/src/pages/course-detail.css
frontend/src/pages/StudyPlanCreatePage.tsx
frontend/src/pages/StudyPlanDetailPage.tsx
frontend/src/pages/study-plan.css
frontend/src/features/study-plans/
frontend/src/features/materials/
frontend/tests/pages/course-detail.test.tsx
frontend/tests/pages/study-plan-pages.test.tsx
docs/domains/course-workspace/
docs/domains/materials/
```

特别说明：即使发现课程详情页的生成按钮、历史卡片或刷新逻辑不足，也只能记录为交接需求；不得直接修改 `CourseDetailPage.tsx`。该文件由同学 A 独占，避免与课程工作台 / 学习计划开发产生冲突。

### 3.3 共享文件冻结规则

并行期默认不得修改以下共享文件：

```text
frontend/src/features/course-workspace/api.ts
frontend/src/features/course-workspace/types.ts
frontend/src/api/
frontend/src/app/
frontend/src/router/AppRouter.tsx
frontend/package.json
pnpm-lock.yaml
```

本任务直接消费既有 `getGeneratedContent()` 和 `GeneratedContent` 基础类型；页面专用 JSON 类型、判别器和 UI state 类型放在 `features/generated-content/`。若发现通用 API 类型确实缺字段，先提交书面契约差异和最小修改建议，由项目负责人指定一次独立集成提交，不能自行修改共享文件。

## 4. 落地目录和分派结构

建议采用以下结构。允许按代码复用情况微调，但必须保持“五类 renderer 相互独立、详情页只负责壳和分派”的方向：

```text
frontend/src/features/generated-content/
  renderers/
    QuizResult.tsx
    FlashcardResult.tsx
    MindmapResult.tsx
    OutlineResult.tsx
    KnowledgeListResult.tsx
    UnknownContentResult.tsx
  components/
    GeneratedContentStatus.tsx
    GeneratedContentEmptyState.tsx
  types.ts
  guards.ts
  GeneratedContentRenderer.tsx
  generated-content.css

frontend/src/pages/
  GeneratedContentDetailPage.tsx
  generated-content-detail.css

frontend/tests/features/generated-content/
  quiz-result.test.tsx
  flashcard-result.test.tsx
  mindmap-result.test.tsx
  outline-result.test.tsx
  knowledge-list-result.test.tsx
  generated-content-renderer.test.tsx
```

`GeneratedContentRenderer` 以 `content_type` 作唯一分派依据。未知内容类型、损坏 JSON 或缺少必要字段必须降级为明确空 / 错误提示，不能让整个详情页崩溃。

## 5. 数据契约与五类渲染要求

五类记录均来自 `AIGeneratedContent.content_json`，包含稳定 ID 与连续 `sort_order`。前端只能展示后端返回字段，不得自行补造 chunk、引用、统计、答案或资料来源。五类独立 POC 的 `source_citations` 固定为 `[]`，必须展示真实空态。

### 5.1 Quiz

- 当前只支持单选题；每题为 A-D 四个选项、正确答案、解析、难度、稳定 ID 与顺序。
- 页面可以提供本地作答、提交本页答案、显示正确 / 错误和解析；这些状态只存在浏览器内存，不创建答题记录、不写后端、不形成错题本。
- loading、生成失败、空题目和未知题型都需有兜底。

### 5.2 Flashcard

- 卡片展示正面、背面、标签、稳定 ID、顺序和 `mastery_status = "unknown"`。
- 可以实现本地翻卡、上一张 / 下一张、进度指示；不得把翻卡或“掌握 / 未掌握”写回后端，也不得声称已经实现间隔复习。
- 公式、长文本和无标签卡片必须可读、可降级。

### 5.3 Mindmap

- 后端返回业务图 `nodes` / `edges`、`root_node_id`、`markmap_markdown` 和预处理后的 `markmap_data`。
- 前端不得再次调用 `markmap-lib` 的 `Transformer.transform()`，不得推断引用。
- 完整 Markmap SVG 渲染需要 `markmap-view`；若该依赖尚未获得项目负责人确认，不得自行修改 `frontend/package.json` 或锁文件。此时先实现节点 / 边的结构化只读降级视图，并在任务报告中明确缺口。
- 获准接入 `markmap-view` 后，使用后端返回的 `markmap_data.root` 和 assets；支持的 fit、展开、折叠仅为本地视图操作，不实现节点编辑、图数据保存或课程详情接入。

### 5.4 Outline

- 按后端 `sections` 的 `sort_order` 展示章节标题、摘要、复习建议和稳定 ID。
- 可以提供本地展开 / 折叠和阅读进度，不写后端、不修改学习计划。
- 不把提纲错误地展示成课程日历、任务清单或引用列表。

### 5.5 Knowledge List

- 按 `items` 的 `sort_order` 展示名称、定义、重要程度、相关章节和稳定 ID。
- 可以提供本地筛选、搜索或重要程度视觉标记；不得持久化掌握度，也不得伪造引用。

## 6. 状态、错误与安全约束

详情页和每个 renderer 都必须覆盖：

```text
loading → 请求详情中的骨架
success → 对应类型的结构化结果
failed → 后端 error_code 与明确失败状态
error → 详情接口失败、401、403、404 等恢复提示
empty / invalid → content_json 为空、字段缺失或未知 content_type 的降级视图
```

- 前端仅根据 `error.code` 做逻辑判断；错误文案必须提示下一步。
- `UNAUTHORIZED` 交由既有 API client 清理登录态；不得在 renderer 内复制鉴权逻辑。
- 不直接调用数据库、不读取资料正文、不自行计算 RAG、不给无引用内容添加假引用。
- 不渲染后端未承诺的 HTML；文本内容按 React 默认转义处理。

## 7. 禁止的功能扩大

本任务不包含以下内容，发现需求时先提请项目负责人拆新任务：

- 课程详情页中发起生成、选择资料范围或生成参数配置。
- 计划任务执行、讲义、任务测试题、完成打卡、日历、导出或 PDF。
- Quiz 结果持久化、判分历史、错题本、Flashcard 间隔复习、Mindmap 节点编辑或协作。
- 修改后端 schema、生成器、公共 API、全局主题、路由结构或共享 HTTP client。

## 8. 测试、文档与提交

- 每个 renderer 至少有一组结构化成功数据、一组空 / 损坏数据和一组失败或未知状态测试。
- 详情页测试覆盖由 URL 加载资源、按 `content_type` 分派、失败记录、空引用和返回课程链接。
- Mindmap 测试必须证明前端直接消费 `markmap_data`，不重新转换 Markdown。
- 每个可验证小功能独立 commit，例如：

```text
feat(generated-content): 新增闪卡翻阅结果页
feat(generated-content): 接入思维导图只读渲染
test(generated-content): 覆盖 Quiz 本地作答状态
```

- 每次提交前运行受影响的 Vitest 文件；准备交付前运行：

```powershell
pnpm frontend:test
pnpm frontend:build
```

- 同步更新 `docs/domains/generated-content/index.md` 和对应 `quiz.md`、`flashcard.md`、`mindmap.md`、`outline.md`、`knowledge-list.md`，记录实际组件入口、渲染架构、客户端状态、API 数据流、失败降级和测试入口。
- commit 前检查 `git status`、`git diff` / `git diff --staged`、文件范围、敏感信息和验证结果；只做本地 commit，不自动 push。

## 9. 验收清单

- [ ] 五类内容均复用 `/generated-contents/:generatedContentId`，没有新增五条路由。
- [ ] 未修改 `CourseDetailPage.tsx`、学习计划、资料区或同学 A 独占路径。
- [ ] 五类 renderer 的结构化数据、失败、空 / 损坏 JSON 和未知类型都可安全显示。
- [ ] Quiz / Flashcard / Mindmap 的交互状态仅本地存在，没有伪造后端能力。
- [ ] Mindmap 不重新调用 `markmap-lib`；新增 `markmap-view` 依赖前已获得明确确认。
- [ ] 不为五类 POC 伪造来源引用。
- [ ] 测试、构建、领域文档和小步提交证据完整。
