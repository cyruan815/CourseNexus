# Current State

## 日期

2026-07-09

## 已完成

1. 文档知识库
   - 已建立 `docs/product/`、`docs/architecture/`、`docs/api-data/`、`docs/engineering/`、`docs/domains/` 和 `docs/planning/`。
   - 已沉淀 PRD、架构概览、部署拓扑、模块边界、数据表契约、工程约定和项目骨架说明。
   - `docs/superpowers/` 作为本地插件过程产物目录，不进入 git。

2. 工程基座
   - 根目录提供 monorepo 级 `README.md`、`package.json`、`pnpm-workspace.yaml`、`pnpm-lock.yaml`、`.gitignore` 和 `.env.example`。
   - 根目录 `.gitignore` 统一管理忽略规则，子项目不维护独立 `.gitignore`。
   - 根目录 `.env.example` 统一声明本地环境变量；真实 `.env` 不提交。

3. 前端骨架
   - 已创建 React + TypeScript/TSX + Vite 项目。
   - 已建立 `src/app`、`src/api`、`src/components`、`src/features`、`src/pages`、`src/router`、`src/types`、`src/utils` 等目录。
   - 当前只实现最小应用壳和基础渲染测试。

4. 后端骨架
   - 已创建 FastAPI 后端项目。
   - 已建立 `app/api`、`app/core`、`app/db`、`app/modules`、`app/integrations`、`app/shared`、`migrations` 和 `tests`。
   - 已引入 SQLAlchemy、Alembic、pydantic-settings、pytest。
   - 后端通过 `app/core/config.py` 读取根目录 `.env`。

5. 数据库基线
   - 已根据 PRD v0.1 建立 13 张核心业务表的 SQLAlchemy models 和 Alembic baseline migration。
   - 当前 SQLite baseline 可创建用户、课程、资料、切片、问答、引用、生成内容、学习计划、任务和打卡相关表。

## 当前未完成

- 尚未实现真实登录、注册和鉴权。
- 尚未实现业务 API、service、repository。
- 尚未实现资料上传、解析、切片和检索。
- 尚未接入模型服务、生成编排、引用校验和失败重试。
- 尚未实现前端真实页面工作流。
- 尚未实现学习计划生成、执行页、今日待办、大日历和 PDF 导出。

## 当前验证

当前基座验证命令：

```powershell
pnpm test
```

已覆盖：

- 后端健康检查接口。
- SQLAlchemy metadata 可创建 13 张核心业务表。
- 前端最小应用壳渲染。

## 下一步重点

1. 建立后端基础横切能力：配置、错误响应、请求 ID、数据库 session 依赖、鉴权占位。
2. 实现用户和课程最小 API，形成前后端 walking skeleton。
3. 实现资料上传记录和解析状态流转，不急于接完整解析器。
4. 在真实业务 API 前补齐 schema、repository、service 分层模板和测试约定。
