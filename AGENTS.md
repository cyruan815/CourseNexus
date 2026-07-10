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
- [docs/domains/index.md](docs/domains/index.md)：业务功能实现知识库及架构、算法沉淀规范入口。

## Agent 行为约束

- 开始任务前先读 `docs/index.md`，再按任务类型阅读相关分区入口。
- 涉及产品、架构、API、数据契约、模块边界、工程规范的改变，必须同步更新 `docs/`。
- 具体业务功能进入实现后，必须在 `docs/domains/` 对应领域同步沉淀实际代码入口、实现架构、状态流转、关键决策和测试入口；后端功能还必须记录核心算法、数据流、复杂度或资源预算以及失败与补偿策略。
- 每完成一个可验证的小功能、小修复或小文档规范变更，都要单独提交一次 git；不要把多个小功能攒到一个完整大功能结束后再合并成一次提交。
- git message 使用 Angular / Conventional Commits 结构；`feat`、`fix`、`docs`、`test` 等模板字段保持英文，说明性内容使用中文。
- 提交前必须运行与本次小改动匹配的验证命令；如果只是文档变更，应至少说明未运行测试的原因。
- 不要把长期决策只留在聊天记录里。
- 不要不读 docs 就直接修改代码。
- 不要引入核心依赖但不写 ADR。
- 不要绕过模块边界直接耦合其他模块内部实现。
- 不要把 `AGENTS.md` 写成百科全书；新增长期知识应进入 `docs/`。
