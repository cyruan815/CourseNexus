# API and Data

## 概述

本目录记录 CourseNexus v0.1 的 API 规范、数据模型和前后端 / 模块间契约。涉及接口、字段、状态、错误码、数据归属和契约变更时，必须更新本分区。

本分区覆盖账号、课程、资料与解析、课程 Agent 问答、AI 生成内容、单课程学习计划、任务 / 待办 / 日历、任务执行、个人中心和学习打卡；数据表字段契约见本分区，实际 migration 位于 `backend/migrations/`，本分区不生成 OpenAPI 文件。

## 文档清单

- [mindmap-frontend-handoff.md](mindmap-frontend-handoff.md)：G04 Mindmap 的数据库 JSON 路径、生成/历史/详情接口、Markmap 渲染输入、引用关联和联调验收。

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [api-conventions.md](api-conventions.md) | API 风格、请求响应、错误码、分页、鉴权、幂等、时间 / ID / 状态字段和版本策略。 | 2026-07-09 |
| [data-model.md](data-model.md) | 核心实体、关系、数据归属、状态字段、软删除、审计字段和迁移规则。 | 2026-07-09 |
| [table-schema.md](table-schema.md) | v0.1 后端数据表、字段、约束、索引和结构化 JSON 契约。 | 2026-07-09 |
| [contracts.md](contracts.md) | 前后端契约、模块间契约、跨模块数据引用原则和契约变更规则。 | 2026-07-09 |
| [frontend-integration.md](frontend-integration.md) | 前端最小集成验证工作台的后端接口接入指南。 | 2026-07-13 |

## 相关链接

- [../index.md](../index.md)：项目长期知识库总入口。
- [../product/prd.md](../product/prd.md)：产品需求权威入口。
- [../architecture/index.md](../architecture/index.md)：架构、模块边界和 ADR 入口。
- [../engineering/development-conventions.md](../engineering/development-conventions.md)：开发约定。

## 维护规则

- API、字段、状态、错误码、权限规则或数据契约变化前，先更新本分区。
- 后端建模、migration 和前后端联调以 [table-schema.md](table-schema.md) 作为 v0.1 表字段契约。
- 前端接入后端能力时，以 [frontend-integration.md](frontend-integration.md) 作为已落地接口和请求 / 响应字段入口。
- 课程是资料、问答、生成内容、计划和任务的基础归属对象。
- 本期支持多用户，但不做多角色权限；所有数据必须按当前登录用户隔离。
- 资料只有 `parsed` 后才能进入检索、问答、生成和计划上下文。
- 学习计划只绑定单个 `course_id`；首页今日待办和首页大日历只聚合多个单课程计划。
- 引用来源必须结构化保存，不能只拼接到文本里，不能生成伪引用。
