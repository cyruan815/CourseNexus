# CourseNexus 课枢

CourseNexus 课枢是一个面向大学生多课程学习场景的 Agent 学习助手平台。系统围绕课程资料构建学习工作台，帮助学生把分散资料转化为可追溯、可执行的学习路径。

## 当前状态

当前仓库处于本地 POC 基座阶段，已完成：

- `frontend/`：React + TypeScript/TSX + Vite 7 最小集成工作台，包含 API client、token 管理、路由壳、课程列表和课程详情空工作台。
- `backend/`：FastAPI 后端基础设施，包含鉴权、课程、资料上传 / 解析、资料上下文、课程问答、生成编排和学习计划基础接口。
- `docs/`：PRD、架构、API / 数据契约、工程规范、阶段状态和路线图入口。
- SQLite baseline migration 可创建 PRD v0.1 的核心业务表。
- 本地资料上下文 RAG 基础设施已接入 Docling、LlamaIndex、Chroma `PersistentClient` 和 OpenAI embedding 配置；Chroma 索引是可从 SQLite `MaterialChunk` 重建的派生存储。

当前基础设施阶段不实现完整产品前端。资料上传面板、资料范围选择器和课程问答面板已后置为独立前端任务；Flashcard / Quiz / Mindmap 等真实业务提示词、AI 学习计划算法、计划执行页、今日待办、大日历和 PDF 导出仍未实现。

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

- Frontend：React、TypeScript/TSX、Vite 7、Vitest，包管理使用 pnpm。
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

根目录 `backend:*` 和 `test` 脚本会通过 `conda run -n course-nexus` 使用项目专属 Python 3.12 环境，避免调用系统 Python。

也可以进入子目录运行：

```powershell
cd frontend
pnpm dev
pnpm build
pnpm test -- --run
```

```powershell
cd backend
conda activate course-nexus
python -m uvicorn app.main:app --reload
python -m pytest
python -m alembic upgrade head
python -m app.commands.rebuild_rag_index --all
python -m app.commands.rebuild_rag_index --material-id <material_id>
```

## 数据库

默认数据库地址为 `sqlite:///./course_nexus.db`，从 `backend/` 目录运行 migration 会生成 `backend/course_nexus.db`。该本地数据库文件被 `.gitignore` 忽略。

初始化或升级数据库：

```powershell
cd backend
conda activate course-nexus
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

- 后端健康检查、schema、鉴权、课程、资料上传 / 解析、Docling 路由、RAG 索引与检索、资料上下文、覆盖执行器、参考消费者、问答、生成、学习计划和集成链路。
- 前端 API client、鉴权字段契约、路由壳、课程列表和课程详情空工作台。

资料支持状态：

- 上传安全校验支持 `.txt`、`.md`、`.pdf`、`.docx`、`.pptx`、`.png`、`.jpg`、`.jpeg`。
- `.txt` / `.md` 走本地纯文本解析器；`.pdf` / `.docx` / `.pptx` / 图片格式走 Docling adapter。
- 图片 OCR 已进入 adapter 路由，但 OCR 质量和版面回归夹具仍显式后置。
- 当前后端验证基线为 `pnpm backend:test`，最近一次记录为 `155 passed`。

## 协作规则

- 开始任务前先读 [AGENTS.md](./AGENTS.md) 和 [docs/index.md](./docs/index.md)。
- 架构、数据契约、工程约定变化必须同步更新 `docs/`。
- 不要把长期决策只留在聊天记录里。
