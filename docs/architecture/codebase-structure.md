# Codebase Structure v0.1

> 本文是 CourseNexus 的代码结构架构文档。它回答“仓库应该怎么组织、前端和后端怎么分层、每个功能模块应该落在哪、哪些依赖方向不能反过来”。工程基座的执行范围见 [../engineering/project-skeleton.md](../engineering/project-skeleton.md)。

## 1. 结构目标

代码结构要服务三个目标：

1. 前后端分离，便于 1 名前端和 2 名后端并行开发。
2. 后端保持 FastAPI 单体，但模块边界清晰，避免业务能力互相粘连。
3. AI 生成能力独立落位，Flashcard、Mindmap、Quiz 等能力可以单独替换生成逻辑、提示词、输出结构和测试。

## 2. 仓库根目录

```text
.
├── README.md
├── AGENTS.md
├── docs/
├── frontend/
└── backend/
```

| 目录 | 说明 |
| --- | --- |
| `docs/` | 项目长期知识库，产品、架构、API / 数据、工程规范都在这里维护。 |
| `frontend/` | React + TypeScript/TSX + Vite 前端应用。 |
| `backend/` | Python + FastAPI 后端应用。 |

根目录不放业务代码。业务实现只能进入 `frontend/` 或 `backend/`。

## 3. 前端结构

```text
frontend/
├── src/
│   ├── api/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── hooks/
│   ├── pages/
│   ├── router/
│   ├── types/
│   └── utils/
└── tests/
```

| 目录 | 职责 | 不放什么 |
| --- | --- | --- |
| `src/app/` | 应用装配、全局 provider、启动级配置。 | 不放业务页面。 |
| `src/router/` | 路由表、登录保护、页面跳转规则。 | 不写页面业务逻辑。 |
| `src/api/` | HTTP client、请求封装、错误码映射、API 类型适配。 | 不直接写 UI 状态。 |
| `src/pages/` | 页面级入口：登录、首页、课程详情、计划生成、大日历、执行页、个人中心。 | 不堆放跨页面复用逻辑。 |
| `src/features/` | 按业务能力组织的前端功能模块。 | 不放全局通用组件。 |
| `src/components/` | 跨页面复用 UI 组件。 | 不写接口请求和业务状态。 |
| `src/hooks/` | 通用 hooks 或薄业务 hooks。 | 不放大型页面流程。 |
| `src/types/` | 前端共享类型，优先对齐 API 契约。 | 不定义后端私有模型。 |
| `src/utils/` | 通用工具函数。 | 不放业务规则。 |

## 4. 前端 feature 建议

```text
frontend/src/features/
├── auth/
├── courses/
├── materials/
├── course-qa/
├── generated-content/
├── study-plans/
├── todos-calendar/
├── learning-execution/
└── profile/
```

说明：

- `generated-content/` 负责生成内容列表、详情页公共壳和按 `content_type` 分发展示。
- Flashcard、Mindmap、Quiz 等具体展示可以作为 `generated-content/` 内的子视图或子组件，不需要互相依赖。
- `todos-calendar/` 只处理首页今日待办、大日历、全局当日待办弹窗和课程内日历视图。
- `learning-execution/` 只处理计划执行页，不拥有计划生成逻辑。

## 5. 后端结构

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── modules/
│   ├── integrations/
│   └── shared/
├── migrations/
└── tests/
```

| 目录 | 职责 | 不放什么 |
| --- | --- | --- |
| `app/main.py` | FastAPI 应用入口和路由装配。 | 不写业务逻辑。 |
| `app/api/` | API router 聚合、依赖注入、统一错误处理。 | 不直接写 SQL 或复杂流程。 |
| `app/core/` | 配置、日志、错误码、安全、鉴权基础。 | 不放业务模块规则。 |
| `app/db/` | SQLAlchemy base、session、数据库连接。 | 不放业务查询。 |
| `app/modules/` | 业务模块主目录。 | 不放跨模块通用基础设施。 |
| `app/integrations/` | parser、LLM、PDF、文件存储等外部或可替换能力适配。 | 不写业务状态。 |
| `app/shared/` | 跨模块共享的小型类型、工具和基础响应结构。 | 不沉淀业务规则。 |
| `migrations/` | Alembic migration。 | 不写业务生成逻辑。 |
| `tests/` | 后端测试。 | 不放运行时代码。 |

## 6. 后端模块模板

每个业务模块建议采用统一内部结构：

```text
app/modules/<module_name>/
├── router.py
├── schemas.py
├── service.py
├── repository.py
├── models.py
└── errors.py
```

| 文件 | 职责 |
| --- | --- |
| `router.py` | 模块 API 路由，负责 HTTP 入参和依赖注入。 |
| `schemas.py` | Pydantic 请求 / 响应模型。 |
| `service.py` | 模块业务规则和跨 repository 编排。 |
| `repository.py` | 模块数据访问。 |
| `models.py` | SQLAlchemy 模型；也可按项目实际集中管理，但归属必须清楚。 |
| `errors.py` | 模块错误码或错误映射。 |

简单模块可以少文件，但不应把路由、业务规则和数据访问混成一个文件。

## 7. 后端模块落位

```text
app/modules/
├── users/
├── courses/
├── materials/
├── material_context/
├── generation/
│   ├── orchestrator/
│   └── generators/
│       ├── course_qa/
│       ├── quiz/
│       ├── flashcard/
│       ├── mindmap/
│       ├── outline/
│       ├── knowledge_list/
│       ├── handout/
│       └── task_test/
├── generated_content/
├── study_plans/
├── todos_calendar/
├── learning_execution/
├── checkins/
└── exports/
```

关键落位规则：

- `generation/orchestrator/` 只处理生成请求编排、幂等、状态、错误和调用具体 generator。
- `generation/generators/*` 下每个目录是独立生成能力。
- Flashcard、Mindmap、Quiz 等 generator 不互相 import。
- `generated_content/` 统一保存 `AIGeneratedContent` 和 `SourceCitation`。
- `study_plans/` 生成计划和任务结构，不生成讲义或任务测试题正文。
- `todos_calendar/` 是只读聚合模块。
- `learning_execution/` 更新任务完成状态，并触发 `checkins/`。

## 8. 后端依赖方向

允许方向：

```text
api -> modules -> repositories -> db
modules -> integrations
generation/orchestrator -> generation/generators/*
generation/generators/* -> generated_content
learning_execution -> checkins
study_plans -> todos_calendar(read model)
```

禁止方向：

```text
generation/generators/flashcard -> generation/generators/mindmap
generation/generators/mindmap -> generation/generators/quiz
todos_calendar -> study_plans write model
integrations -> modules
repositories -> service
frontend -> database
```

## 9. 测试结构

```text
backend/tests/
├── modules/
│   ├── users/
│   ├── courses/
│   ├── materials/
│   ├── generation/
│   ├── study_plans/
│   └── learning_execution/
└── integration/
```

```text
frontend/tests/
├── features/
├── pages/
└── integration/
```

测试优先覆盖：

- 权限和数据归属。
- 资料状态流转。
- 独立生成模块的输入 / 输出 / 失败。
- 计划保存与任务结构。
- 二级任务完成的幂等和打卡更新。
- 前端 loading、empty、error、generating 状态。

## 10. 与 engineering/project-skeleton 的关系

本文是代码结构的架构权威。`docs/engineering/project-skeleton.md` 只说明“项目基座第一阶段要先具备哪些能力”和 walking skeleton 的验收范围。

如果两者冲突：

1. 代码目录和模块落位以本文为准。
2. 基座实施顺序和最小验收范围以 engineering 文档为准。
3. 修改结构时先更新本文，再更新 engineering 中的执行说明。
