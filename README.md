# CourseNexus 课枢

CourseNexus 课枢是一个面向大学生多课程学习场景的 Agent 学习助手平台。系统围绕课程资料构建学习工作台，帮助学生把分散资料转化为可追溯、可执行的学习路径。

## 当前状态

当前仓库处于本地 POC 基座阶段，已完成：

- `frontend/`：React + TypeScript/TSX + Vite 7 最小集成工作台，包含 API client、token 管理、路由壳、课程列表和课程详情空工作台。
- `backend/`：FastAPI 后端基础设施，包含鉴权、课程、资料上传 / 解析、资料上下文、课程问答、生成编排和学习计划基础接口。
- `docs/`：PRD、架构、API / 数据契约、工程规范、阶段状态和路线图入口。
- SQLite baseline migration 可创建 PRD v0.1 的核心业务表。
- 本地资料上下文 RAG 基础设施已接入 Docling、LlamaIndex、Chroma `PersistentClient` 和 OpenAI-compatible embedding 配置；Chroma 索引是可从 SQLite `MaterialChunk` 重建的派生存储。

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

## 首次启动 Quick Start

以下步骤面向 Windows PowerShell，适用于新开发者从零克隆并启动本地开发环境。如果仓库已经克隆，从仓库根目录开始执行即可。

### 1. 克隆仓库并安装前端依赖

```powershell
git clone https://github.com/cyruan815/CourseNexus.git
Set-Location CourseNexus
corepack enable
corepack prepare pnpm@11.7.0 --activate
pnpm install
```

如果本机已经安装兼容的 pnpm 11，可以跳过两个 `corepack` 命令。

### 2. 创建后端 Conda 环境

```powershell
Set-Location backend
conda env create -f environment.yml
conda run -n course-nexus python -m playwright install chromium
Set-Location ..
```

前两条命令会创建名为 `course-nexus` 的 Python 3.12 环境、安装后端依赖，并额外下载 PDF 导出所需的 Playwright Chromium。Python 包安装不会自动下载浏览器，因此首次创建环境或 Playwright 升级后都应执行 Chromium 安装命令。环境已经存在时不要重复创建，按后文“环境准备”中的更新命令同步依赖。

### 3. 创建本地配置

```powershell
Copy-Item .env.example .env
notepad .env
```

首次启动至少确认：

- `SECRET_KEY` 已替换为本地开发值。
- `VITE_API_BASE_URL=http://localhost:8000`，末尾不要再添加 `/api/v1`，业务请求路径已经包含该前缀。
- `CORS_ALLOWED_ORIGINS=http://localhost:5173`；浏览器直连后端时，后端只接受该配置中列出的前端来源，多个来源用英文逗号分隔。
- 仅体验账号、课程和基础页面时，可以暂时不填写模型密钥。
- 要进行真实资料解析、向量索引和检索，需填写 `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL` 和 `EMBEDDING_MODEL`。
- 要进行真实课程资料问答，还需填写 `COURSE_QA_API_KEY`、`COURSE_QA_BASE_URL` 和 `COURSE_QA_MODEL`。

真实 `.env` 不得提交到 Git，也不要把任何密钥写入 `VITE_` 开头的变量。

### 4. 初始化数据库

从仓库根目录执行：

```powershell
pnpm backend:migrate
```

执行成功后会在 `backend/course_nexus.db` 创建或升级本地 SQLite 数据库。

### 5. 启动后端和前端

打开两个 PowerShell 终端，并确保二者当前目录都是仓库根目录。

终端 1：

```powershell
pnpm backend:dev
```

该脚本会固定使用 `course-nexus` Conda 环境，通过 Uvicorn 启动 FastAPI，并启用代码热更新和实时终端日志。服务运行期间终端会持续被占用；按 `Ctrl+C` 停止后端。

终端 2：

```powershell
pnpm frontend:dev
```

启动后访问：

- 前端页面：<http://localhost:5173>
- 后端 OpenAPI：<http://localhost:8000/docs>
- 后端健康检查：<http://localhost:8000/api/v1/health>

也可以在第三个 PowerShell 终端验证健康检查：

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health | ConvertTo-Json -Depth 5
```

响应中的 `data.status` 应为 `ok`。

### 后端日志

后端使用 Python 标准库 `logging`，时间明确使用带 `+08:00` 偏移的北京时间。交互式终端按级别为日志级别和事件名着色，并只显示单行根因摘要；重定向输出或设置 `NO_COLOR` 时自动关闭颜色。Uvicorn 不重复打印已由应用记录的请求异常 traceback，完整追溯仍写入 `backend/logs/course-nexus.log`。日志文件默认每个 `20 MiB`，保留 `20` 个备份，总上限约 `420 MiB`。

可在根目录 `.env` 调整：

```dotenv
LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_MAX_BYTES=20971520
LOG_BACKUP_COUNT=20
SLOW_REQUEST_MS=3000
```

从仓库根目录按错误级别或请求 ID 查询：

```powershell
Select-String -Path backend/logs/course-nexus.log -Pattern 'ERROR'
Select-String -Path backend/logs/course-nexus.log -Pattern 'req_具体请求ID'
```

日志不得包含密码、Token、API Key、完整资料、完整问题、prompt 或模型响应。正式长期留存应接入外部日志平台，本地轮转文件用于近期排查。

### 6. 验证前端构建

```powershell
pnpm frontend:build
Set-Location frontend
pnpm preview
```

构建预览默认位于 <http://localhost:4173>。预览期间后端仍需保持运行；完成后按 `Ctrl+C` 停止服务并返回仓库根目录。

### 7. 开始开发前阅读

开始领取任务前，依次阅读：

- [AGENTS.md](./AGENTS.md)：仓库协作和提交约束。
- [docs/index.md](./docs/index.md)：产品、架构、API 和工程文档入口。
- [工程协作规范](./docs/engineering/collaboration.md)：分支策略、提交规范、PR 与 Review 规则。

## 环境准备

前置工具：

- Node.js 24 或兼容版本。
- 后端 Mindmap 生成也需要根目录已执行 `pnpm install`，因为 Markdown 预处理通过官方 `markmap-lib` Node helper 完成；Node 命令可用 `MARKMAP_NODE_COMMAND` 配置。
- pnpm 11 或兼容版本。
- Conda。
- 后端 Python 版本固定为 3.12，由 [backend/environment.yml](./backend/environment.yml) 管理。

创建后端项目专属 conda 环境：

```powershell
cd backend
conda env create -f environment.yml
conda activate course-nexus
python -m playwright install chromium
```

如果环境已经存在，更新后端依赖：

```powershell
cd backend
conda env update -f environment.yml --prune
conda activate course-nexus
python -m playwright install chromium
```

安装前端依赖：

```powershell
pnpm install
```

`backend/environment.yml` 会创建 Python 3.12 环境，并通过 `pip -e ".[dev]"` 安装后端运行依赖和测试依赖。若未使用 conda，也可以在 Python 3.12 环境中手动安装后端依赖：

```powershell
cd backend
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

`playwright` Python 包和 Chromium 浏览器二进制是两部分依赖；只执行 Conda / pip 安装仍会导致讲义 PDF 导出失败。Chromium 下载通常只需在首次安装或 Playwright 版本升级后执行一次。

环境变量：

```powershell
Copy-Item .env.example .env
```

本仓库按长期 monorepo 管理，环境变量示例统一放在根目录 [.env.example](./.env.example)。真实 `.env` 只放在根目录且不得提交。后端会读取根目录 `.env`；前端 Vite 也配置为读取根目录 `.env`，但只有 `VITE_` 开头的变量会进入浏览器。API Key、密钥、模型服务地址等敏感配置不要写成 `VITE_` 变量。

模型服务按业务用途独立配置，每个用途都有自己的 `*_API_KEY`、`*_BASE_URL` 和 `*_MODEL`。当前固定前缀为 `EMBEDDING`、`COURSE_QA`、`QUIZ`、`FLASHCARD`、`MINDMAP`、`OUTLINE`、`KNOWLEDGE_LIST`、`STUDY_PLAN_PARSER`、`STUDY_PLAN_GENERATOR`、`HANDOUT` 和 `TASK_TEST`。这些服务可以来自不同供应商，只需兼容 OpenAI SDK 接口；新功能不得复用旧的 `OPENAI_*` 共享配置。

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

根目录 `backend:*` 和 `test` 脚本会通过 `conda run -n course-nexus` 使用项目专属 Python 3.12 环境，避免调用系统 Python；其中 `backend:dev` 额外启用 `--no-capture-output`，实时显示 Uvicorn 启动信息和后端日志。

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
- 当前后端验证基线为 `pnpm backend:test`，最近一次记录为 `192 passed`。

## 协作规则

- 开始任务前先读 [AGENTS.md](./AGENTS.md) 和 [docs/index.md](./docs/index.md)。
- 架构、数据契约、工程约定变化必须同步更新 `docs/`。
- 不要把长期决策只留在聊天记录里。
