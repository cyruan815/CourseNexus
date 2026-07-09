# CourseNexus 课枢

CourseNexus 课枢是一个面向大学生多课程学习场景的 Agent 学习助手平台。系统围绕课程资料构建学习工作台，帮助学生把分散资料转化为可追溯、可执行的学习路径。

## 当前状态

当前仓库处于本地 POC 基座阶段，已完成：

- `frontend/`：React + TypeScript/TSX + Vite 最小项目骨架。
- `backend/`：FastAPI 后端骨架、SQLAlchemy 数据模型、Alembic baseline migration。
- `docs/`：PRD、架构、API / 数据契约、工程规范入口。
- SQLite baseline migration 可创建 PRD v0.1 的 13 张核心业务表。

尚未实现完整业务 API、页面工作流、资料解析、Agent 生成、计划生成和 PDF 导出。

## 仓库结构

```text
.
├── AGENTS.md
├── README.md
├── docs/
├── frontend/
└── backend/
```

关键入口：

- [docs/index.md](./docs/index.md)：项目长期知识库总入口。
- [docs/product/prd.md](./docs/product/prd.md)：产品需求权威入口。
- [docs/architecture/index.md](./docs/architecture/index.md)：架构、模块边界和 ADR 入口。
- [docs/api-data/table-schema.md](./docs/api-data/table-schema.md)：v0.1 数据表字段契约。
- [docs/engineering/project-skeleton.md](./docs/engineering/project-skeleton.md)：项目基座范围。

## 技术栈

- Frontend：React、TypeScript/TSX、Vite、Vitest，包管理使用 pnpm。
- Backend：Python、FastAPI、SQLAlchemy、Alembic、pytest。
- Database：SQLite，本地 POC 使用；模型和 migration 保留 PostgreSQL 迁移空间。

## 环境准备

前置工具：

- Node.js 24 或兼容版本。
- pnpm 11 或兼容版本。
- Conda。
- 后端 Python 版本固定为 3.12，由 [backend/environment.yml](./backend/environment.yml) 管理。

创建后端项目专属 conda 环境：

```powershell
cd backend
conda env create -f environment.yml
conda activate course-nexus
```

如果环境已经存在，更新后端依赖：

```powershell
cd backend
conda env update -f environment.yml --prune
```

安装前端依赖：

```powershell
pnpm install
```

`backend/environment.yml` 会创建 Python 3.12 环境，并通过 `pip -e ".[dev]"` 安装后端运行依赖和测试依赖。若未使用 conda，也可以在 Python 3.12 环境中手动安装后端依赖：

```powershell
cd backend
python -m pip install -e ".[dev]"
```

环境变量：

```powershell
Copy-Item .env.example .env
```

本仓库按长期 monorepo 管理，环境变量示例统一放在根目录 [.env.example](./.env.example)。真实 `.env` 只放在根目录且不得提交。后端会读取根目录 `.env`；前端 Vite 也配置为读取根目录 `.env`，但只有 `VITE_` 开头的变量会进入浏览器。API Key、密钥、模型服务地址等敏感配置不要写成 `VITE_` 变量。

## 常用命令

从仓库根目录运行：

```powershell
pnpm frontend:dev
pnpm frontend:build
pnpm frontend:test
pnpm backend:dev
pnpm backend:test
pnpm backend:migrate
pnpm test
```

也可以进入子目录运行：

```powershell
cd frontend
pnpm dev
pnpm build
pnpm test -- --run
```

```powershell
cd backend
python -m uvicorn app.main:app --reload
python -m pytest
python -m alembic upgrade head
```

## 数据库

默认数据库地址为 `sqlite:///./course_nexus.db`，从 `backend/` 目录运行 migration 会生成 `backend/course_nexus.db`。该本地数据库文件被 `.gitignore` 忽略。

初始化或升级数据库：

```powershell
cd backend
python -m alembic upgrade head
```

当前 baseline migration：

- [backend/migrations/versions/20260709_0001_create_core_tables.py](./backend/migrations/versions/20260709_0001_create_core_tables.py)

## 验证

当前基座验证命令：

```powershell
pnpm test
```

已覆盖：

- 后端健康检查接口。
- SQLAlchemy metadata 可创建 13 张核心表。
- 前端最小应用壳渲染。

## 协作规则

- 开始任务前先读 [AGENTS.md](./AGENTS.md) 和 [docs/index.md](./docs/index.md)。
- 架构、数据契约、工程约定变化必须同步更新 `docs/`。
- 不要把长期决策只留在聊天记录里。
