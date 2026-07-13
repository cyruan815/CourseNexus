# Current State

## 2026-07-13 Generation POC Refactor

G01-G06 now use complete selected-material context with one structured model call per request. Total context overflow is explicit, item-level citations and generation citation writes are removed, and API responses keep `source_citations=[]`. Mindmap uses backend `markmap-lib@0.18.12` preprocessing and persists `root`, `features`, and used `assets` for frontend `markmap-view` rendering. Older batch/map-reduce generation notes below are historical and do not describe the current five-module path.

## 日期

2026-07-12

## 当前阶段结论

CourseNexus 当前已从“空项目骨架”推进到“本地 POC 基础设施可验证”阶段。当前主线不是完整产品前端，而是稳定后端链路和可分发的模块边界。

当前已打通的后端基础链路：

```text
注册 / 登录 -> 创建课程 -> 上传资料 -> 解析 -> 写入 MaterialChunk -> Chroma 索引 -> retrieve_relevant_context() / iter_material_context_batches()
```

前端当前只作为最小集成验证工作台，交付 API client、token 管理、路由壳、课程列表和课程详情空工作台。资料上传面板、资料范围选择器、问答面板等完整交互已经从基础设施主线移出，后续在 Materials / Context / QA 接口稳定后作为独立前端任务分发。

## 已完成

1. 文档知识库
   - 已建立 `docs/product/`、`docs/architecture/`、`docs/api-data/`、`docs/engineering/`、`docs/domains/` 和 `docs/planning/`。
   - 已沉淀 PRD、架构概览、部署拓扑、模块边界、数据表契约、工程约定和项目骨架说明。
   - 当前 API 接入入口为 [../api-data/frontend-integration.md](../api-data/frontend-integration.md)。

2. 工程和运行环境
   - 根目录提供 monorepo 级 `README.md`、`package.json`、`pnpm-workspace.yaml`、`pnpm-lock.yaml`、`.gitignore` 和 `.env.example`。
   - 已创建 Conda 环境 `course-nexus`，Python 版本为 3.12。
   - 前端使用 React + TypeScript/TSX + Vite 7。
   - 后端使用 FastAPI + SQLAlchemy 2 ORM + Alembic + SQLite。
   - 常规业务数据操作优先使用 SQLAlchemy 2 ORM；复杂统计、聚合、排行榜或特殊性能优化可使用 SQLAlchemy Core 或原生 SQL。

3. 后端横切基础
   - 已实现统一成功响应 `{data, meta}`。
   - 已实现统一错误响应、请求 ID、数据库 session 依赖和健康检查。
   - 已实现本地账号注册、登录、当前用户识别和退出接口。
   - token 采用本地签发校验，并已预留过期时间 `exp`。

4. 课程和资料基础
   - 已实现课程创建、列表、详情、更新和删除接口。
   - 已实现课程资料上传、资料链接记录、资料列表、详情和删除接口。
   - 本地文件存储已具备路径穿越防护、文件大小上限配置和真实 MIME / 文本内容校验。
   - 已实现 `.txt` / `.md` 解析、Docling adapter 路由、解析失败状态、重试解析和 `MaterialChunk` 写入。
   - 上传校验支持 `.txt`、`.md`、`.pdf`、`.docx`、`.pptx`、`.png`、`.jpg`、`.jpeg`；图片 OCR 质量验证后置。

5. 资料上下文和问答基础
   - 已保留 `material_context.resolve_context()` 兼容入口；生产课程问答已改用 `retrieve_relevant_context()`。
   - 已实现 `retrieve_relevant_context()` 问答 Top-K 检索接口，基于 user/course/material/folder 硬过滤并回查 SQLite 权威 chunk。
   - 已实现 `iter_material_context_batches()` 指定材料全覆盖接口和 `run_material_coverage()` 覆盖执行器。
   - 已实现 LlamaIndex + Chroma `PersistentClient` 本地向量索引、fake index、OpenAI embedding factory 和重建命令 `python -m app.commands.rebuild_rag_index --all` / `--material-id <id>`。
   - 已实现课程问答接口、会话列表、消息列表、回答保存和 `SourceCitation` 保存；生产问答路径已接入 `retrieve_relevant_context()`，无检索命中返回 `no_source`，引用只保存模型返回 id 与检索命中 id 的交集。
   - 模型调用统一通过 OpenAI SDK provider 边界；已支持调用方自定义 Pydantic schema 的结构化输出；测试和本地无 key 场景使用 mock provider。
   - 本地 RAG 技术栈为 FastAPI + LlamaIndex + Docling + Chroma + OpenAI API；RAGFlow 仅作为 future 方案。

6. 生成和计划基础
   - 已完成 G01 公共生成链路：用途模型提供器注入、生成器工厂注册、完整材料上下文、总 token 检查、单次模型调用和 `AIGeneratedContent` 保存。
   - 生成 POST、课程历史和详情均返回稳定 `source_citations` 数组；五类 POC 内容固定为空，失败记录不保存部分 JSON。
   - 已覆盖跨用户课程/资料、无资料、上下文超限、非法参数、模型/schema 失败、重复请求和真实数据库回滚。
   - 已实现 Flashcard、Mindmap、Quiz、Outline、Knowledge List 的最终结构化生成器，覆盖稳定 ID/顺序、无逐条引用和失败记录；Mindmap 额外保存 `markmap-lib` 预处理结果。
   - 已实现单课程学习计划自然语言配置回填、全材料预览、用户调整后保存、幂等、重生成预览、原子替换、软删除、列表和详情接口。
   - 学习计划当前只生成计划 / 任务结构，不提前生成今日讲义、任务测试题或执行页内容。
   - 已完成 S01 计划学习模式表结构契约测试，确认现有 13 张核心表可支撑第一阶段计划、任务、打卡、生成内容和导出闭环；S01 不新增业务表、不创建 migration。
   - 已完成 S02 学习计划生命周期后端实现和文档同步，包含学前诊断问题/profile 接口、diagnostic_profile 影响 planner、preference 派生 planner_strategy、诊断后 capacity 闭环、确认任务树保存/替换/删除；S02 不新增表、不新增列、不修改 migration。
   - 已完成 S03 今日待办与日历聚合后端实现：五个只读 GET 接口、首页嵌套待办、月历 3 条摘要、课程详情页今日任务和计划详情复用；S03 不新增表、不修改 migration、不实现 S04-S07。
   - 已完成 S04/S05 学习执行与打卡后端实现：执行上下文、二级任务幂等完成、父任务/计划状态汇总、打卡重算、单日查询、范围查询和 streak summary。
   - 已完成 S06 任务内容生成后端实现：为 learn/review 二级任务按需生成 handout，为 quiz/test 二级任务按需生成 task_test，复用 `ai_generated_contents` 并绑定 `study_subtask_id`。

7. 前端最小集成工作台
   - 已建立前端 API client、鉴权 token 管理和路由壳。
   - 已实现登录页、课程列表和课程详情空工作台。
   - 课程详情页只保留资料区、问答区、生成内容区、学习计划入口等挂载区域，不实现完整业务交互。

8. 测试覆盖
   - 后端已覆盖健康检查、schema、鉴权、课程、资料上传 / 解析、资料上下文、问答、生成、学习计划和两条集成链路。
   - 前端已覆盖 API client、鉴权字段契约、路由壳、课程列表和课程详情空工作台。

## 当前未完成

- 资料上传面板、资料范围选择器、资料状态列表等完整前端资料交互。
- 课程问答面板、引用列表、追问交互等完整前端问答体验。
- Study Mode 执行页任务测试题轻量只读展示；后端 `task_test` 内容生成已实现，前端仍需接入最近成功内容读取、题目/答案/解析/引用展示和畸形内容兜底。
- 任务测试题作答、判分、attempt 历史和反馈闭环；该能力后续按 P9 / phase-1 S08 单独设计，不属于 P2 只读展示。
- Flashcard、Mindmap、Quiz 等能力的真实材料人工质量验收和前端交互完善。
- 图片 OCR 质量验收和复杂版面回归夹具。
- S07 PDF 导出业务实现。
- 生产级鉴权、刷新 token、对象存储、异步任务队列、可观测性和部署配置。

## 当前验证命令

后端验证：

```powershell
pnpm backend:test
```

RAG 维护和持久化验证：

```powershell
cd backend
conda run -n course-nexus python -m app.commands.rebuild_rag_index --all
conda run -n course-nexus python -m pytest tests/integrations/test_llama_index_chroma.py::test_chroma_persists_and_filters_course -q
```

最近一次后端完整验证：

- G01隔离环境后端全量：`256 passed`（2026-07-12）。
- G01 generation + generated-content回归：`82 passed`。
- `pnpm backend:migrate`：Alembic `upgrade head` 成功。
- Chroma persistence smoke：`1 passed in 3.82s`。

S01 计划学习模式契约验证：

- `uv run python -m pytest tests/modules/study_mode/test_subsystem_schema_contract.py -q`：`8 passed in 0.53s`。
- `uv run python -m pytest tests/test_schema_metadata.py -q --tb=short`：`2 passed in 0.40s`。
- `uv run python -m alembic upgrade head`：成功，未产生新 revision。

S02 学习计划生命周期验证：

- `uv run python -m alembic upgrade head`：成功，未产生新 revision。
- `uv run python -m pytest tests/modules/study_plans tests/modules/material_context tests/integration/test_full_material_plan_flow.py tests/integration/test_material_context_to_plan_flow.py -q`：`49 passed in 16.80s`。


S03 今日待办与日历聚合验证：

- `uv run python -m pytest tests/modules/todos_calendar tests/integration/test_plan_calendar_flow.py -q`：`18 passed in 3.97s`。

S04/S05 学习执行与打卡验证：

- `uv run python -m alembic upgrade head`：成功。
- `uv run python -m pytest tests/modules/checkins tests/modules/learning_execution tests/modules/todos_calendar tests/modules/study_plans tests/integration/test_checkin_lifecycle_sync.py tests/integration/test_subtask_completion_transaction.py -q`：`67 passed`。

S06 任务内容生成验证：

- `uv run python -m pytest tests/modules/generation/test_handout_generator.py tests/modules/generation/test_task_test_generator.py -q`：`4 passed`。
- `uv run python -m pytest tests/modules/learning_execution/test_task_content_api.py -q`：`5 passed`。
- `uv run python -m pytest tests/integration/test_task_content_generation_flow.py tests/modules/generation/test_orchestrator_contract.py tests/modules/generation/test_orchestrator_service.py tests/modules/learning_execution tests/modules/checkins -q`：已通过。
前端验证：

```powershell
pnpm frontend:test
pnpm frontend:build
```

仓库级验证入口：

```powershell
pnpm test
```

## 下一步重点

1. 在后端接口稳定后，将资料上传 UI、资料范围选择和问答面板拆成独立前端任务。
2. 基于 [../engineering/rag-consumer-guide.md](../engineering/rag-consumer-guide.md)，将具体生成能力分批迁移到新上下文接口。
3. 为 Flashcard、Mindmap 和 Quiz 补充真实课程材料质量验收和前端交互。
4. 推进 S07：基于已生成讲义和任务测试题导出 PDF。
5. 补齐图片 OCR 质量验收、复杂 PDF/PPT/DOCX 版面夹具和长耗时后台任务。
6. 继续沿用“小功能完成 -> 小测试 -> 小提交”的版本管理规则。

## 2026-07-12 S04/S05 当前状态

S04 学习执行上下文和二级任务完成事务已在后端实现。S05 打卡重算、单日查询、范围查询和连续天数 summary 已实现。S04 completion 与 S05 重算处于同一事务；S02 计划保存、替换和删除也会同步重算受影响日期。

未涉及前端、migration 或 S03 写逻辑。

## 2026-07-12 S06 当前状态

S06 任务内容生成已在后端实现。`learn` / `review` 二级任务可按需生成 `handout`，`quiz` / `test` 二级任务可按需生成 `task_test`。生成范围严格来自二级任务 `related_material_ids_json`，使用全材料分批覆盖，不走 Top-K。成功内容和进入生成流程后的失败记录均写入 `ai_generated_contents`，并通过 `study_subtask_id` 绑定二级任务。

未涉及前端、migration、PDF 导出或学生作答保存。前端剩余工作是 P2 轻量只读展示；S07 继续负责 PDF 导出；学生作答、判分、attempt 历史和反馈闭环已拆到后续作答反馈任务（phase-1 S08 / 新优先级 P9）。
