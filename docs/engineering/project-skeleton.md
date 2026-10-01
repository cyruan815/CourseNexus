# Project Skeleton v0.1

## 项目基座目标

项目基座支撑一个可运行、可验证、可继续扩展的 CourseNexus 单机 V1，并为后续开发提供清晰目录、配置、鉴权、数据库、错误处理、日志、测试和文档入口。本文中的 walking skeleton 条目描述最低基线；当前能力状态以 [../planning/current-state.md](../planning/current-state.md) 为准。

## 推荐目录结构

代码结构的架构权威见 [../architecture/codebase-structure.md](../architecture/codebase-structure.md)。本文件只说明项目基座阶段应该先搭到什么程度，避免在 engineering 文档里复制一套可能漂移的目录结构。

基座阶段至少需要建立：

- `frontend/`：React + TypeScript/TSX + Vite 前端应用入口。
- `backend/`：Python + FastAPI 后端应用入口。
- `docs/`：长期知识库入口。
- 前端最小 `api`、`router`、`pages`、`features` 结构。
- 后端最小 `api`、`core`、`db`、`modules`、`integrations` 结构。
- 测试目录：`frontend/tests/`、`backend/tests/`。

## 当前初始化状态

截至 2026-07-12，仓库已完成以下基座初始化：

- 根目录保留 `README.md`、`AGENTS.md`、`docs/`、`frontend/`、`backend/`。
- 根目录提供 `package.json` 和 `pnpm-workspace.yaml`，用于统一运行前端和后端常用命令。
- `frontend/` 已创建 Vite 7 + React + TypeScript/TSX 最小应用入口，并保留 `api`、`app`、`components`、`features`、`hooks`、`pages`、`router`、`types`、`utils`、`tests` 目录。
- `frontend/` 已在 API client、token 管理和路由壳上实现课程资料、统一文件预览、问答引用、生成内容、学习计划、待办日历、执行与导出页面。
- `backend/` 已创建 FastAPI 应用入口、API router、SQLAlchemy base/session、Alembic migration、模块目录、integration 目录和测试目录。
- `backend/` 当前已实现鉴权、课程、资料上传 / 解析、资料上下文、课程问答、生成编排和学习计划基础接口。
- `backend/` 已建立 Python `logging` 统一日志入口，终端输出单行摘要，轮转文件保存完整异常，并通过请求 ID 串联接口与业务日志。
- 当前基础设施阶段重点是后端链路稳定，不实现资料上传面板、资料范围选择器或课程问答面板等完整前端业务交互。

## Walking Skeleton 范围

walking skeleton 应只证明端到端链路可用：

1. 前端能启动并访问一个受登录态保护的页面。
2. 后端能启动并暴露 `/api/v1` 基础接口。
3. 前端能调用后端并处理成功、未登录和错误响应。
4. 后端能连接 SQLite，并通过 ORM 读写最小数据。
5. 有基础账号登录态和当前用户识别。
6. 有课程列表和课程详情工作台，用于验证课程选择、前后端、数据库和错误处理。
7. 有最小测试和手动验收清单。

资料上传、资料范围选择和课程问答 UI 已在 V1 实现；后续体验增强不能削弱对应后端接口、测试和契约的独立稳定性。

## 当前阶段必须具备的基础能力

- 配置管理：区分开发配置、数据库地址、密钥占位和文件存储路径。
- 环境变量：不把密钥、初始密码或本地路径硬编码进业务代码。
- 日志：全部接口记录请求 ID、状态和耗时；关键业务、外部调用和失败状态记录结果、稳定错误码或原始异常。
- 错误处理：统一错误响应格式和稳定 `error.code`。
- 鉴权基础：多用户账号、密码哈希、登录态校验、当前用户依赖。
- 数据库连接：SQLAlchemy session 管理，SQLite 作为本地 POC。
- migration 机制：采用 Alembic 管理结构变化，但基座文档不生成具体 migration。
- 基础测试：后端 pytest，前端 Vitest，关键流程保留手动验收清单。
- lint / format：按项目最终工具链统一执行，避免不同成员格式漂移。
- 文档入口：`AGENTS.md` 和 `docs/index.md` 必须作为 Agent 入口。

## 当前验证入口

后端应优先在项目 Conda 环境中验证：

```powershell
conda run -n course-nexus python -m pytest backend
```

前端最小工作台验证：

```powershell
pnpm frontend:test
pnpm frontend:build
```

只修改文档时可以不运行完整测试，但提交说明必须写明未运行测试的原因。

## 当前阶段不做什么

- 不实现完整产品前端。
- 不实现资料上传面板、资料范围选择器、课程问答面板等完整前端交互。
- 不创建具体模块知识库。
- 不生成完整 OpenAPI 文件。
- 不引入缓存、微服务或复杂后台基础设施。
- 不建设教师端、管理员端、班级空间或多角色权限。
- 不提前实现多课程联合计划、复杂推荐或完整统计报表。
