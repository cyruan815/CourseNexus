# AGENTS.md

## 项目身份

CourseNexus 课枢是一个面向大学生多课程学习场景的 Agent 学习助手平台。系统围绕课程资料构建学习工作台，帮助学生把分散资料转化为可追溯、可执行的学习路径。

当前项目处于从 0 搭建本地 POC 的早期阶段。前端采用 React + TypeScript/TSX + Vite，后端采用 Python + FastAPI，当前数据库使用 SQLite，后续稳定后可迁移到 PostgreSQL。

## 知识库入口

- [docs/index.md](docs/index.md)：项目长期知识库总入口。
- [docs/product/index.md](docs/product/index.md)：产品需求和 PRD 入口。
- [docs/architecture/index.md](docs/architecture/index.md)：架构、模块边界和 ADR 入口。
- [docs/api-data/index.md](docs/api-data/index.md)：API、数据模型和契约入口。
- [docs/engineering/index.md](docs/engineering/index.md)：项目骨架、开发约定和协作规则入口。
- [docs/domains/index.md](docs/domains/index.md)：未来模块知识库入口。

## Agent 行为约束

- 开始任务前先读 `docs/index.md`，再按任务类型阅读相关分区入口。
- 涉及产品、架构、API、数据契约、模块边界、工程规范的改变，必须同步更新 `docs/`。
- 不要把长期决策只留在聊天记录里。
- 不要不读 docs 就直接修改代码。
- 不要引入核心依赖但不写 ADR。
- 不要绕过模块边界直接耦合其他模块内部实现。
- 不要把 `AGENTS.md` 写成百科全书；新增长期知识应进入 `docs/`。
