# Infrastructure Execution Summary

## 日期

2026-07-09

> 2026-07-10 后续更新：本地 RAG 基础设施已落地，课程问答生产路径已从 `resolve_context()` 迁移到 `retrieve_relevant_context()`；最新状态以 [current-state.md](current-state.md) 为准。

## 目的

本文记录本轮基础设施执行实际完成了什么、哪些边界被调整、哪些文档被修改，以及当前可交给后续任务分发的基础能力。

本轮执行目标不是完成完整产品前端，而是搭建 CourseNexus 本地 POC 的后端基础设施和最小前端集成工作台，保证后续 Flashcard、Mindmap、Quiz、完整课程问答前端、资料上传前端和计划学习模式可以基于稳定接口继续分发开发。

## 执行范围

已确认并执行的当前主线：

```text
注册 / 登录 -> 创建课程 -> 上传资料 -> 解析 -> 写入 MaterialChunk -> Chroma 索引 -> retrieve_relevant_context() -> ask_question() -> 保存回答和引用
```

当前前端范围收窄为：

- API client。
- token 管理。
- 路由壳。
- 登录页。
- 课程列表。
- 课程详情空工作台。

以下能力已移出当前基础设施主线，作为后续独立前端任务：

- 资料上传面板。
- 资料范围选择器。
- 资料状态列表。
- 课程问答面板。
- 引用列表和追问交互。

## 主要完成内容

### 1. 环境和工程入口

- 创建项目 Conda 环境 `course-nexus`。
- Python 固定为 3.12。
- 更新根目录脚本，使 `backend:*` 和 `pnpm test` 通过 `conda run -n course-nexus` 调用后端 Python，避免误用系统 Python 或 Conda base。
- 前端使用 Vite 7，并通过构建验证。

### 2. 后端横切基础

- 建立统一成功响应 `{data, meta}`。
- 建立统一错误响应和稳定错误码。
- 建立请求 ID 中间件。
- 建立数据库 session 依赖。
- 建立鉴权依赖和当前用户获取。

### 3. 本地账号和鉴权

- 实现注册、登录、当前用户、退出接口。
- 实现密码哈希。
- 实现本地 token 签发和校验。
- token 已预留 `exp` 过期字段，便于后续升级生命周期管理。

### 4. 课程基础能力

- 实现课程创建、列表、详情、更新、删除接口。
- 所有课程数据按 `user_id` 做归属校验。
- 前端最小工作台可展示课程列表并进入课程详情页壳。

### 5. 资料上传、存储、解析和切片

- 实现课程资料上传接口。
- 实现资料链接记录接口。
- 实现资料列表、详情、删除、重试解析接口。
- 建立本地文件存储适配层。
- 文件上传安全兜底包括：
  - 文件名路径穿越拒绝。
  - Windows 设备名拒绝。
  - 文件大小上限配置。
  - 文本类真实 MIME / 内容校验。
- 实现 `.txt` / `.md` 解析。
- 实现 `MaterialChunk` 写入。
- 解析失败会写入 `parse_failed` 和错误信息。

### 6. 资料上下文层

- 新增 `material_context.resolve_context()`，并在 2026-07-10 进一步拆分出 `retrieve_relevant_context()` 和 `iter_material_context_batches()`。
- 统一处理课程归属、逐文件资料范围、已解析过滤和 chunk 返回；文件夹只用于归类。
- 问答通过相关性检索获取资料上下文；指定材料生成和学习计划通过全材料批次入口获取资料，不直接拼接资料表或 chunk 表。

### 7. 课程问答基础链路

- 实现课程会话、消息和问答接口。
- 实现回答保存。
- 实现 `SourceCitation` 引用保存。
- 无可用资料时返回 `no_source`，不生成伪引用。
- 所有真实 LLM 调用统一经由 `model_provider` 适配层；OpenAI SDK 只在 `backend/app/integrations/model_provider/openai.py` 中直接导入。

### 8. 生成编排和生成内容存储

- 建立 `generation-orchestrator`。
- 建立 generator registry 和统一生成合同。
- 实现 `AIGeneratedContent` 保存、列表和详情。
- 实现生成内容引用保存。
- 当前提供 Flashcard、Mindmap、Quiz、Outline、Knowledge List 的占位生成器，用于验证边界和存储合同。
- 真实 LLM 提示词、结构化生成质量和前端渲染属于后续分发任务。

### 9. 学习计划基础接口

- 实现单课程学习计划预览。
- 实现学习计划保存。
- 实现课程下学习计划列表。
- 实现学习计划详情。
- 当前计划模块只负责计划和任务结构，不提前生成今日讲义、任务测试题、执行页内容或打卡记录。

### 10. 集成测试和统一验证

- 增加后端集成测试，覆盖课程资料问答主链路：
  - 注册。
  - 登录。
  - 创建课程。
  - 上传资料。
  - 解析资料。
  - 写入 chunk。
  - 提问。
  - 保存回答和引用。
- 增加后端集成测试，覆盖资料上下文到学习计划基础链路。
- 修复根目录测试脚本，使 `pnpm test` 可以作为统一验证入口。

## 当前验证结果

最后一次完成审计时运行：

```powershell
pnpm test
```

结果：

- 后端：75 passed。
- 前端：8 个测试文件，21 passed。

同时运行：

```powershell
pnpm frontend:build
```

结果：

- Vite 7.3.6 构建通过。

## 本轮修改过的文档

### 仓库入口文档

| 文件 | 修改内容 |
| --- | --- |
| `README.md` | 更新当前状态、技术栈、Conda 环境、根目录脚本行为、验证范围和当前未完成范围。 |

### Architecture

| 文件 | 修改内容 |
| --- | --- |
| `docs/architecture/adr/0002-foundation-runtime-dependencies.md` | 新增基础设施运行依赖 ADR，记录 Vite 7、OpenAI SDK、`python-multipart` 和依赖边界。 |
| `docs/architecture/adr/index.md` | 增加 ADR 0002 的入口。 |
| `docs/architecture/module-boundaries.md` | 补充当前已落地模块边界，包括 `model-provider`、`material-context`、`generation-orchestrator`、`study-plans` 和前端最小工作台边界。 |
| `docs/architecture/runtime-flows.md` | 更新当前基础设施落地链路；修正课程问答实际链路为 `course_qa -> material_context -> model_provider`；记录生成和计划基础链路。 |

### API / Data

| 文件 | 修改内容 |
| --- | --- |
| `docs/api-data/frontend-integration.md` | 新增并持续补充前端接入指南，记录 Auth、Courses、Materials、QA、Generation、Study Plans 等接口契约。 |
| `docs/api-data/contracts.md` | 补充前后端契约基线、当前已落地接口范围、资料上下文契约和当前前端后置任务边界。 |
| `docs/api-data/index.md` | 增加 `frontend-integration.md` 入口。 |

### Engineering

| 文件 | 修改内容 |
| --- | --- |
| `docs/engineering/development-conventions.md` | 补充数据库访问策略、前端基础设施阶段约定、Conda 后端脚本约定和小步提交规则。 |
| `docs/engineering/project-skeleton.md` | 更新项目骨架当前状态、前端最小工作台范围、后端已落地基础接口和验证命令。 |

### Planning

| 文件 | 修改内容 |
| --- | --- |
| `docs/planning/current-state.md` | 从早期骨架状态更新为当前基础设施可验证状态，记录已完成能力、未完成能力和验证命令。 |
| `docs/planning/implementation-roadmap.md` | 收窄当前基础设施前端边界，标注阶段 0 至阶段 7 的当前完成状态和后续范围。 |
| `docs/planning/infrastructure-execution-summary.md` | 本文件，记录本轮执行总结、修改文档清单和后续分发入口。 |

## 相关非 docs 但影响文档口径的文件

| 文件 | 说明 |
| --- | --- |
| `package.json` | 根目录 `backend:*` 和 `test` 脚本改为通过 `conda run -n course-nexus` 执行。 |
| `backend/environment.yml` | 定义 `course-nexus` Conda 环境，Python 3.12。 |
| `.env.example` | 补充基础设施阶段所需配置示例。 |

## 提交记录摘要

本轮分支 `codex/execute-infrastructure-plan` 上按小功能粒度提交：

```text
docs(adr): 记录基础设施运行依赖
feat(api): 建立统一响应和请求 ID 基础
feat(auth): 实现本地账号鉴权基础
feat(courses): 实现课程 API 基础
feat(frontend): 建立路由和 API 客户端基础
docs(api): 明确前端集成工作台接口契约
fix(frontend): 对齐鉴权字段契约
feat(courses): 搭建课程列表和详情页壳
feat(materials): 实现资料上传和记录基础
feat(materials): 实现资料解析和切片基础
feat(context): 建立资料上下文解析接口
docs(planning): 收窄基础设施前端验收边界
feat(course-qa): 实现课程问答基础链路
feat(generation): 建立生成编排和内容存储基础
feat(study-plans): 建立单课程计划基础接口
test(integration): 覆盖课程资料问答和计划基础链路
docs(planning): 更新基础设施实现状态和边界
fix(scripts): 使用项目 conda 环境运行后端命令
```

此前已落到 `main` 的准备提交：

```text
build(env): 配置项目 conda 环境
docs(engineering): 明确数据库查询实现策略
```

## 后续可分发任务入口

后续任务可以基于当前基础设施拆分为：

- 资料上传前端：基于 Materials API、解析状态和 `material_scope` 契约开发。
- 课程问答前端：基于 QA API、Conversation / Message / SourceCitation 契约开发。
- Flashcard：基于 `generation-orchestrator` 和 `AIGeneratedContent(content_type=flashcard)` 开发真实生成器和前端视图。
- Mindmap：基于 `content_type=mindmap` 开发真实生成器和图形视图。
- Quiz：基于 `content_type=quiz` 开发结构化题目生成和渲染。
- PDF / PPT / Word 解析：基于 parser adapter 扩展，不改变 `MaterialChunk` 下游合同。
- 计划学习模式：基于 `study-plans` 基础接口继续开发执行页、日历聚合、打卡和按需生成讲义 / 测试题。
