# Architecture Decision Records

## 概述

本目录记录 CourseNexus 的长期架构决策。ADR 用于解释为什么选择某个技术方案，而不是记录临时任务计划。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [0001-tech-stack.md](0001-tech-stack.md) | Accepted；v0.1 技术栈与本地 POC 架构选择。 | 2026-07-09 |
| [0002-foundation-runtime-dependencies.md](0002-foundation-runtime-dependencies.md) | Accepted；基础设施阶段运行依赖、Vite 7 主版本和 OpenAI SDK 接入边界。 | 2026-07-09 |
| [0003-local-rag-stack.md](0003-local-rag-stack.md) | Accepted；本地资料上下文与 RAG 采用 LlamaIndex、Docling、Chroma 和用途级独立 OpenAI-compatible API，RAGFlow 作为 future 方案。 | 2026-07-10 |

## 相关链接

- [../index.md](../index.md)：架构分区入口。
- [../overview.md](../overview.md)：架构文档 v0.1。
- [../module-boundaries.md](../module-boundaries.md)：模块拓扑与边界说明。
- [../../api-data/index.md](../../api-data/index.md)：API、数据模型和契约入口。

## 维护规则

- 引入或替换核心框架、数据库、ORM、鉴权方式、文件存储、后台任务方案或模型服务集成方式时，必须新增或更新 ADR。
- 改变前后端分离方式、模块边界、API 版本策略、错误码体系或数据迁移策略时，必须新增或更新 ADR。
- ADR 文件名使用四位递增编号和短横线标题，例如 `0001-tech-stack.md`。
- 每个 ADR 至少包含 `Status`、`Context`、`Options`、`Decision`、`Reasons`、`Consequences`。
- ADR 状态使用 `Proposed`、`Accepted`、`Deprecated`、`Superseded`。
