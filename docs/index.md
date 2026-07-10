# CourseNexus Docs

## 概述

`docs/` 是 CourseNexus 课枢的长期项目知识库，由开发者和 Agent 共同使用。它不是 README 的附属说明，而是产品、架构、API、数据契约、模块边界、工程规范和协作方式的权威上下文。

当前文档基线为 v0.1，目标是支撑后续项目基座框架、walking skeleton 和前后端分工，不提前展开具体功能模块开发文档。

## 推荐阅读顺序

1. 先读 [../AGENTS.md](../AGENTS.md)，了解 Agent 接手项目的入口和行为约束。
2. 再读本文件，确认 `docs/` 的分区职责。
3. 做产品或验收相关任务时，读 [product/index.md](product/index.md)。
4. 做架构、模块拆分、技术选型或跨模块修改时，读 [architecture/index.md](architecture/index.md)。
5. 做 API、数据模型、前后端联调或契约变更时，读 [api-data/index.md](api-data/index.md)。
6. 做项目基座、开发约定、协作和完成标准时，读 [engineering/index.md](engineering/index.md)。
7. 做阶段规划、当前状态、路线图或技术债整理时，读 [planning/index.md](planning/index.md)。
8. 做具体业务模块前，先读 [domains/index.md](domains/index.md)，再按模块创建独立知识库。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [product/index.md](product/index.md) | 产品目标、PRD 和 AI 资料业务范围入口。 | 2026-07-10 |
| [architecture/index.md](architecture/index.md) | 架构文档、模块边界、资料上下文 / RAG 和技术决策入口。 | 2026-07-10 |
| [api-data/index.md](api-data/index.md) | API 规范、数据模型和契约入口。 | 2026-07-09 |
| [engineering/index.md](engineering/index.md) | 项目骨架、开发约定和轻量协作规范入口。 | 2026-07-09 |
| [planning/index.md](planning/index.md) | 当前状态、实现路线图、技术债、第一阶段并行任务书和信息处理优化计划入口。 | 2026-07-10 |
| [domains/index.md](domains/index.md) | 业务领域实现知识库入口，记录各功能实际架构、算法、状态和代码入口。 | 2026-07-10 |

## 相关链接

- [../AGENTS.md](../AGENTS.md)：Agent 接手项目的入口、阅读顺序和行为约束。
- [../README.md](../README.md)：项目简介和仓库级入口。
- [product/prd.md](product/prd.md)：产品需求权威入口。
- [product/ai-material-business.md](product/ai-material-business.md)：AI 资料业务线，两类业务及共同约束。
- [architecture/material-context-rag.md](architecture/material-context-rag.md)：本地资料上下文与 RAG 架构。

## 维护规则

- 产品行为、业务范围、验收口径变化时，更新 `product/`。
- 架构风格、模块边界、核心依赖、数据归属规则变化时，更新 `architecture/`。
- API、字段、状态、错误码、数据契约变化时，更新 `api-data/`。
- 项目骨架、开发约定、测试验收、协作方式变化时，更新 `engineering/`。
- 当前状态、路线图、技术债和共享优化计划变化时，更新 `planning/`。
- 具体模块进入开发后，必须在 `domains/` 下创建或更新对应领域文档；只记录已经确认的实现，未稳定内容标为设计约束或已知问题。
- 长期决策必须沉淀到文档，不只保留在聊天记录、临时计划或代码注释中。
