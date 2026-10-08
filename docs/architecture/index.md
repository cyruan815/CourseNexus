# Architecture

## 概述

本目录记录 CourseNexus v0.1 的产品架构、技术架构、功能模块拓扑、模块边界和关键运行链路。它的目标是让项目负责人、后端、前端和 Agent 接手后，能快速理解系统为什么这样拆、组件之间怎么连、哪些地方必须保持解耦。

当前架构口径是：前后端分离、本地 POC、FastAPI 单体后端按业务能力分包、SQLite 当前存储并保留 PostgreSQL 迁移空间、不引入缓存、不做多角色权限。资料上下文与 RAG 在 FastAPI 进程内采用 LlamaIndex + Docling + Chroma `PersistentClient`，不使用 Docker；embedding 和各类生成通过用途级独立的 OpenAI-compatible endpoint 提供。问答使用范围过滤后的 Top-K 检索，指定材料生成功能按顺序覆盖全部选中资料。RAGFlow 仅作为 future 方案。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [overview.md](overview.md) | 产品架构 L1：系统上下文、能力分层、核心设计原则和非目标。 | 2026-07-09 |
| [topology.md](topology.md) | 技术架构 L1：本地 POC 部署形态、后端容器拓扑、信任边界和数据/文件流向。 | 2026-07-09 |
| [codebase-structure.md](codebase-structure.md) | 代码结构架构：仓库目录、前端分层、后端分层、模块落位和依赖方向。 | 2026-07-09 |
| [module-boundaries.md](module-boundaries.md) | 功能模块拓扑与模块边界：账号、共享模型配置、课程、资料、Agent、独立 AI 生成模块、计划、日历、执行和打卡的依赖关系与禁止耦合事项。 | 2026-10-08 |
| [runtime-flows.md](runtime-flows.md) | 关键运行链路：资料解析、问答、独立生成、计划生成、任务执行、日历聚合和导出。 | 2026-07-09 |
| [material-context-rag.md](material-context-rag.md) | 资料上传、解析、索引、检索和引用架构，以及问答与指定材料生成两条链路。 | 2026-07-10 |
| [adr/index.md](adr/index.md) | 架构决策记录入口、命名规则和当前 ADR 清单。 | 2026-07-09 |
| [adr/0001-tech-stack.md](adr/0001-tech-stack.md) | v0.1 技术栈与本地 POC 架构选择。 | 2026-07-09 |
| [adr/0003-local-rag-stack.md](adr/0003-local-rag-stack.md) | 本地资料上下文与 RAG 核心依赖和运行边界。 | 2026-07-10 |
| [adr/0006-handout-pdf-rendering.md](adr/0006-handout-pdf-rendering.md) | 今日讲义 PDF 导出采用 Markdown/HTML/Playwright Chromium 打印链路。 | 2026-07-13 |
| [adr/0007-frontend-handout-mermaid-svg.md](adr/0007-frontend-handout-mermaid-svg.md) | 前端讲义以 sanitize 白名单渲染原始 SVG，并保留严格模式 Mermaid 历史兼容；新生成讲义只使用安全内联 SVG。 | 2026-10-01 |
| [adr/0009-versioned-material-parsing.md](adr/0009-versioned-material-parsing.md) | 材料重解析使用候选版本、完整性校验和生效指针原子切换。 | 2026-10-01 |

## 推荐阅读顺序

1. 先读 [overview.md](overview.md)，理解 CourseNexus 是什么系统以及能力为什么这样分层。
2. 再读 [topology.md](topology.md)，理解本地 POC 的技术组件、部署关系和信任边界。
3. 要搭项目基座或判断代码应该放在哪里时，读 [codebase-structure.md](codebase-structure.md)。
4. 需要拆任务或接手模块时，读 [module-boundaries.md](module-boundaries.md)。
5. 需要实现或排查主流程时，读 [runtime-flows.md](runtime-flows.md)。
6. 实现资料解析、检索、问答或指定材料生成时，读 [material-context-rag.md](material-context-rag.md)。
7. 需要判断技术选型或修改核心依赖时，读 [adr/index.md](adr/index.md)。

## 相关链接

- [../index.md](../index.md)：项目长期知识库总入口。
- [../product/prd.md](../product/prd.md)：产品需求权威入口。
- [../api-data/index.md](../api-data/index.md)：API、数据模型和契约入口。
- [../engineering/index.md](../engineering/index.md)：项目骨架、开发约定和协作规则入口。
- [../domains/index.md](../domains/index.md)：未来模块知识库入口。

## 维护规则

- 架构风格、模块边界、核心依赖或数据归属规则变化时，必须更新本分区。
- 引入核心依赖、改变数据库、改变鉴权方式、改变前后端契约时，必须新增或更新 ADR。
- 新增 AI 生成能力时，优先按“独立生成模块”接入：读取资料上下文，生成结构化结果并写入 `AIGeneratedContent`，不直接耦合其他生成模块；只有产品契约要求来源追溯时才写入真实 `SourceCitation`。
- 本分区只维护长期架构知识；具体模块进入开发后，若需要独立领域知识库，再按 [../domains/index.md](../domains/index.md) 创建。
