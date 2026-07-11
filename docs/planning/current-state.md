# Current State

## 日期

2026-07-11

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
   - 已完成G01公共生成链路：用途模型提供器注入、生成器工厂注册、全材料批次读取、真实引用过滤和ID回填、成功内容与引用原子保存。
   - 生成POST、课程历史和详情均返回稳定`source_citations`数组；失败记录不保存部分JSON或引用。
   - 已覆盖跨用户课程/资料、无资料、非法参数、模型/schema/coverage失败、重复请求、引用去重和真实数据库回滚。
   - 已提供 Flashcard、Mindmap、Quiz、Outline、Knowledge List 的占位生成器，用于验证模块边界和存储契约。
   - 已实现单课程学习计划预览、保存、列表和详情接口。
   - 学习计划当前只生成计划 / 任务结构，不提前生成今日讲义、任务测试题或执行页内容。
   - 已完成 S01 计划学习模式表结构契约测试，确认现有 13 张核心表可支撑第一阶段计划、任务、打卡、生成内容和导出闭环；S01 不新增业务表、不创建 migration。

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
- Flashcard、Mindmap、Quiz 等能力的真实 LLM 结构化生成提示词和质量验收。
- 图片 OCR 质量验收和复杂版面回归夹具。
- S01 文档同步后的后续 S02-S07 业务实现：真实学习计划生成 / 编辑 / 删除、今日待办、大日历、执行页、打卡同步、今日讲义、任务测试题和 PDF 导出。
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
3. 为 Flashcard、Mindmap、Quiz 和学习计划分别设计业务 schema、prompt、质量验收和保存流程。
4. 补齐图片 OCR 质量验收、复杂 PDF/PPT/DOCX 版面夹具和长耗时后台任务。
5. 继续沿用“小功能完成 -> 小测试 -> 小提交”的版本管理规则。
