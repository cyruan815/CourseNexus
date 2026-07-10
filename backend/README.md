# CourseNexus Backend

CourseNexus 的 FastAPI + SQLAlchemy + Alembic 后端。本文只作为后端协作开发和本地运行入口；业务需求、架构、API 与数据字段以仓库 `docs/` 为准。

## 当前范围

当前后端已经落地：

- 用户注册、登录和 Bearer token 鉴权；
- 课程创建、列表和详情；
- 资料上传、一级文件夹归类、解析、状态管理与本地文件存储；
- Docling 文档解析、`MaterialChunk`、Chroma 索引和资料范围检索；
- 基于检索结果的课程问答、回答记录和来源引用；
- 生成编排基础契约、生成记录以及学习计划基础接口；
- SQLite baseline migration、RAG 索引重建命令和自动化测试。

Quiz、Flashcard、Mindmap、Outline、Knowledge List 的真实生成器，以及完整计划学习子系统，仍由第一阶段后端任务书继续实现。

## 目录边界

```text
app/
├── api/           # API router 装配与公共依赖
├── commands/      # 本地维护命令
├── core/          # 配置、鉴权和请求级基础设施
├── db/            # SQLAlchemy models、session 和数据库基础设施
├── integrations/  # Docling、Chroma、模型、存储和 PDF 适配器
├── modules/       # 按业务能力划分的 router/service/schema/repository
└── shared/        # 跨模块稳定 DTO、响应和错误
migrations/        # Alembic migration
tests/             # API、模块、契约和集成测试
```

- 业务模块只能通过公开 service、协议或 DTO 协作，不得直接耦合其他模块内部实现。
- 业务模块不得直接 import Docling、LlamaIndex、Chroma 或 OpenAI SDK；外部依赖统一封装在 `integrations/`。
- 数据表、API 字段、状态和错误码变化必须先同步 `docs/api-data/`。
- migration 和共享 router 属于高冲突文件，按第一阶段共享契约的所有权规则修改。

## 环境准备

后端固定使用 Python 3.12 和项目专属 Conda 环境：

```powershell
cd backend
conda env create -f environment.yml
conda activate course-nexus
```

环境已存在时：

```powershell
cd backend
conda env update -f environment.yml --prune
```

## 开发命令

推荐从仓库根目录运行：

```powershell
pnpm backend:dev
pnpm backend:test
pnpm backend:migrate
```

也可以在已激活 `course-nexus` 环境的 `backend/` 目录运行：

```powershell
python -m uvicorn app.main:app --reload
python -m pytest
python -m alembic upgrade head
python -m app.commands.rebuild_rag_index --all
python -m app.commands.rebuild_rag_index --material-id <material_id>
```

提交前运行与改动匹配的测试；涉及共享契约、数据库、RAG 或跨模块行为时运行完整 `pnpm backend:test`。

## 配置

后端读取仓库根目录 `.env`，示例和中文说明见 [../.env.example](../.env.example)。真实 `.env` 不得提交，服务端密钥不得放入任何 `VITE_` 变量。

每个模型用途分别配置 `*_API_KEY`、`*_BASE_URL` 和 `*_MODEL`，并通过 `Settings.model_endpoint(purpose)` 读取。Embedding、课程问答、五类资料生成和计划学习功能可以使用不同的 OpenAI-compatible 服务，不得隐式共用其他用途的配置。

默认数据库为 `sqlite:///./course_nexus.db`。表结构以 `migrations/` 为准，字段契约以 `docs/api-data/table-schema.md` 为准；Chroma 是可从 SQLite `MaterialChunk` 重建的派生索引。

## 协作入口

- [第一阶段后端任务书](../docs/planning/phase-1-task-books/README.md)
- [共享协作契约](../docs/planning/phase-1-task-books/shared-contract.md)
- [RAG 消费者接入指南](../docs/engineering/rag-consumer-guide.md)
- [架构与模块边界](../docs/architecture/index.md)
- [API 与数据契约](../docs/api-data/index.md)
- [工程与完成标准](../docs/engineering/index.md)

README 不复制完整接口或表字段。发现 README 与 `docs/` 不一致时，以 `docs/` 为准并同步修正 README。
