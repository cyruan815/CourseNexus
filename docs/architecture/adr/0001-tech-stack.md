# ADR 0001: v0.1 Technology Stack

## Status

Accepted.

## Context

CourseNexus 当前目标是把 PRD 中的真实学习闭环落地为可运行的本地 POC。系统需要支持多用户账号、课程资料管理、资料解析、基于资料的 Agent 问答、AI 生成内容、单课程学习计划、今日待办 / 大日历和学习完成记录。

当前团队规模较小，现阶段优先保证开发速度、数据归属清晰、状态可追踪和后续可迁移。

## Options

1. React + Vite 前端，FastAPI 单体后端，SQLite 数据库。
2. 前后端一体框架。
3. 后端按多个服务拆分。
4. 当前阶段直接搭建生产级数据库、缓存和任务基础设施。

## Decision

v0.1 选择：

- 前端：React + TypeScript/TSX + Vite，包管理使用 pnpm。
- 后端：Python + FastAPI，环境管理使用 conda。
- 数据库：SQLite 用于当前本地 POC，后续保留 PostgreSQL 迁移空间。
- ORM 与迁移：默认采用 SQLAlchemy + Alembic 作为基线。
- 架构形态：FastAPI 单体应用，按业务能力分包。
- 缓存：不引入缓存。
- 鉴权：本地多用户账号，按 `user_id` 做数据隔离，不做多角色权限。
- API 风格：JSON REST API，基础前缀为 `/api/v1`。
- 部署方式：本地 POC。
- 测试策略：后端 pytest，前端 Vitest，并保留关键流程手动验收清单。

## Reasons

- FastAPI 适合 Python 生态下的资料解析、Agent 编排、异步状态接口和后续模型服务集成。
- React + TSX + Vite 适合实现课程详情、三栏布局、大日历、计划执行页等交互密集页面。
- SQLite 足够支撑本地 POC，可降低启动成本。
- SQLAlchemy + Alembic 有利于从 SQLite 演进到 PostgreSQL。
- 单体按模块分包可以保持边界清晰，同时避免过早拆分服务。
- 不引入缓存可以减少一致性负担，当前 PRD 更强调状态、引用来源和权限校验。
- 单学生角色、多用户隔离符合本期产品范围。

## Consequences

- 所有接口必须显式校验当前用户是否拥有目标课程、资料、对话、生成内容、计划或任务。
- 数据模型应避免依赖 SQLite 专有能力，为 PostgreSQL 迁移保留空间。
- 长耗时任务在 v0.1 内先通过状态字段、错误码和重试入口表达。
- 首页大日历和今日待办通过查询层聚合多个单课程计划任务，不改变 `StudyPlan` 单课程约束。
- 生成内容统一落到 `AIGeneratedContent`，引用统一落到 `SourceCitation`。
- 如果后续资料规模、并发或生成任务量上升，需要重新评估数据库、后台任务、对象存储和缓存方案，并新增 ADR。
