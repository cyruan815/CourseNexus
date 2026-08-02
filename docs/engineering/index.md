# Engineering

## 概述

本目录记录 CourseNexus 的工程基线：项目骨架、开发约定、轻量协作规则和 Definition of Done。它服务项目负责人 / 架构师、2 名后端和 1 名前端的小团队协作，不追求复杂工程治理。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [project-skeleton.md](project-skeleton.md) | 项目基座目标、推荐目录结构、walking skeleton 和基础能力。 | 2026-07-12 |
| [development-conventions.md](development-conventions.md) | 命名、目录、代码风格、错误、日志、配置、测试、数据库和文档约定。 | 2026-07-14 |
| [collaboration.md](collaboration.md) | 小团队分工、分支、提交、评审、任务拆分和文档责任。 | 2026-08-02 |
| [definition-of-done.md](definition-of-done.md) | 代码、测试、文档、API / 数据契约和 Review 完成标准。 | 2026-07-12 |
| [rag-consumer-guide.md](rag-consumer-guide.md) | 业务功能接入材料上下文 RAG 的调用链、边界、错误和测试规则。 | 2026-07-10 |
| [frontend-ui-guidelines.md](frontend-ui-guidelines.md) | 前端亮色 UI 风格、色彩、排版、组件和场景规范。 | 2026-07-10 |

## 相关链接

- [../index.md](../index.md)：项目长期知识库总入口。
- [../architecture/index.md](../architecture/index.md)：架构、模块边界和 ADR 入口。
- [../api-data/index.md](../api-data/index.md)：API、数据模型和契约入口。
- [../product/prd.md](../product/prd.md)：产品需求权威入口。

## 维护规则

- 项目骨架、依赖基线、测试方式、开发约定或协作方式变化时，必须更新本分区。
- 工程文档只记录长期可复用的规则，不记录一次性任务计划。
- 工程约定必须与架构文档和 API / 数据契约保持一致。
- 本分区面向小团队轻量协作，不写复杂发布流程或大型团队治理。
