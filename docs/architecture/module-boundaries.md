# Module Topology and Boundaries v0.1

> 本文合并记录功能模块拓扑和模块边界。它回答“系统拆成哪些模块、模块之间怎么依赖、每个模块拥有哪类数据、哪些耦合被禁止”。关键流程见 [runtime-flows.md](runtime-flows.md)，数据字段以 [../api-data/data-model.md](../api-data/data-model.md) 为准。

## 1. 拆分原则

CourseNexus 后端采用 FastAPI 单体应用，但单体不等于随意耦合。模块按“业务能力 + 数据所有权 + 状态流转”划分，而不是按页面或数据库表机械拆分。

核心原则：

- `users` 提供用户身份，`courses` 提供课程归属边界。
- `materials` 是所有 AI 能力的上下文来源，不负责生成。
- `generation-orchestrator` 只编排生成请求，不拥有具体生成能力的内部规则。
- Quiz、Flashcard、Mindmap、复习提纲、知识点清单、今日讲义、任务测试题都是独立生成模块。
- `generated-content` 是生成结果的统一存储，不负责生成逻辑。
- `study-plans` 生成计划和任务结构，不负责日历聚合和任务执行 UI 状态。
- `todos-calendar` 是只读聚合，不拥有写模型。
- `learning-execution` 负责任务执行状态，不负责计划生成。
- `checkins` 只根据任务完成事实维护学习打卡记录。

## 1.1 当前已落地边界（2026-07-09）

当前基础设施阶段已经落地以下模块边界：

- `users` / `courses`：提供本地账号、token 校验、当前用户依赖和课程归属校验。
- `materials`：拥有资料元数据、本地文件存储、上传校验、解析状态和 `MaterialChunk` 写入。
- `material-context`：作为问答、生成、学习计划共用的上下文解析入口；调用方不得绕过它直接拼装 chunk。
- `course-qa`：拥有会话、消息和课程问答引用保存；不负责 Flashcard、Mindmap、Quiz 或学习计划。
- `model-provider`：所有需要调用 LLM 的地方必须通过 provider 边界；OpenAI 调用统一集中在 OpenAI SDK provider 实现中。
- `generation-orchestrator`：当前负责生成请求编排、上下文解析、占位生成器调用、`AIGeneratedContent` 和 `SourceCitation` 保存。
- `study-plans`：当前只负责单课程计划预览、保存和任务结构写入，不负责执行页、日历聚合、打卡或讲义 / 任务测试题生成。
- `frontend`：当前只承担最小集成验证工作台，不承载完整资料上传 UI、资料范围选择 UI 或课程问答 UI。

## 2. 模块拓扑图

```mermaid
flowchart TB
    U["users<br/>账号 / 登录态 / 当前用户"]
    C["courses<br/>课程归属边界"]
    M["materials<br/>上传 / 解析 / 切片 / 资料范围"]
    MC["material-context<br/>可检索上下文 / 引用候选"]
    GO["generation-orchestrator<br/>生成请求编排 / 状态 / 幂等"]
    GC["generated-content<br/>AIGeneratedContent / SourceCitation"]

    subgraph GEN["独立 AI 生成模块"]
        QA["course-qa<br/>课程问答"]
        QZ["quiz-generator<br/>课程自测 Quiz"]
        FC["flashcard-generator<br/>Flashcard"]
        MM["mindmap-generator<br/>Mindmap"]
        OL["outline-generator<br/>复习提纲"]
        KL["knowledge-list-generator<br/>知识点清单"]
        HO["handout-generator<br/>今日讲义"]
        TT["task-test-generator<br/>任务测试题"]
    end

    SP["study-plans<br/>单课程计划 / 一级任务 / 二级任务"]
    TC["todos-calendar<br/>今日待办 / 大日历 / 课程日历"]
    LE["learning-execution<br/>今日任务执行 / 二级任务完成"]
    CK["checkins<br/>学习完成记录 / 打卡颜色"]
    EX["exports<br/>PDF 导出"]

    U --> C
    C --> M
    M --> MC
    C --> SP
    MC --> GO
    GO --> QA
    GO --> QZ
    GO --> FC
    GO --> MM
    GO --> OL
    GO --> KL
    GO --> HO
    GO --> TT
    QA --> GC
    QZ --> GC
    FC --> GC
    MM --> GC
    OL --> GC
    KL --> GC
    HO --> GC
    TT --> GC
    SP --> TC
    SP --> LE
    LE --> HO
    LE --> TT
    LE --> CK
    LE --> TC
    GC --> EX
```

一句话读图：课程和资料提供上下文；生成编排把上下文交给各独立 AI 生成模块；生成结果统一落到 `AIGeneratedContent` 和 `SourceCitation`；学习计划和执行链路使用生成能力，但不把生成逻辑内嵌到计划模块。

## 3. 模块分层

| 层级 | 模块 | 架构角色 |
| --- | --- | --- |
| 身份与归属层 | `users`、`courses` | 定义“当前用户是谁”和“这份数据属于哪门课程”。 |
| 资料上下文层 | `materials`、`material-context` | 把资料转成可检索、可引用的上下文。 |
| 生成编排层 | `generation-orchestrator` | 处理生成请求、幂等、状态、失败重试和调用独立生成模块。 |
| 独立生成能力层 | `course-qa`、`quiz-generator`、`flashcard-generator`、`mindmap-generator`、`outline-generator`、`knowledge-list-generator`、`handout-generator`、`task-test-generator` | 每个能力只关心自己的输入、生成规则和输出结构。 |
| 内容存储层 | `generated-content` | 统一保存 AI 生成内容和引用来源。 |
| 计划任务层 | `study-plans`、`learning-execution` | 生成任务结构并驱动任务执行状态。 |
| 只读聚合层 | `todos-calendar` | 聚合今日待办、大日历和课程日历视图。 |
| 派生记录层 | `checkins`、`exports` | 根据任务或内容生成派生结果。 |

## 4. 模块边界表

| 模块 | 负责什么 | 拥有 / 主要写入 | 对外输出 | 不负责什么 |
| --- | --- | --- | --- | --- |
| `users` | 注册、登录、退出、修改密码、当前用户识别。 | `User`、登录态。 | 当前用户上下文、登录状态。 | 不查询课程、资料、计划等业务对象。 |
| `courses` | 课程创建、编辑、删除、列表、详情、课程归属校验。 | `Course`。 | 可访问课程、课程基础信息、课程归属判断。 | 不解析资料，不生成内容，不处理任务状态。 |
| `materials` | 文件 / 链接资料、一级目录、上传状态、解析状态、资料切片和资料预览定位。 | `MaterialFolder`、`CourseMaterial`、`MaterialChunk`。 | 已解析资料、资料范围、切片定位信息。 | 不生成回答、卡片、导图或计划。 |
| `material-context` | 根据课程、资料范围、任务上下文筛选可用切片，生成引用候选。 | 可不单独建表，读取 `MaterialChunk`。 | 检索结果、上下文片段、引用候选。 | 不调用模型，不保存生成内容。 |
| `generation-orchestrator` | 接收生成请求、校验权限、校验资料范围、处理幂等、维护生成状态、调用具体生成模块。 | 生成请求状态，可复用 `AIGeneratedContent.generation_status`。 | 生成任务状态、错误码、生成模块调用结果。 | 不写具体业务算法，不直接渲染结果。 |
| `course-qa` | 基于课程资料问答，保存对话消息和引用来源。 | `Conversation`、`Message`、`SourceCitation`。 | `answer_text`、`answer_type`、引用列表。 | 不生成 Flashcard、Mindmap 或学习计划。 |
| `quiz-generator` | 基于资料范围生成课程自测 Quiz。 | `AIGeneratedContent(content_type=quiz)`、`SourceCitation`。 | 题目、选项、答案、解析、引用。 | 不处理任务测试题入口。 |
| `flashcard-generator` | 基于资料范围生成记忆卡片。 | `AIGeneratedContent(content_type=flashcard)`、`SourceCitation`。 | 卡片正面、背面、标签、引用。 | 不处理 Mindmap、Quiz、计划任务。 |
| `mindmap-generator` | 基于资料范围生成知识结构图。 | `AIGeneratedContent(content_type=mindmap)`、`SourceCitation`。 | 节点、边、层级、引用。 | 不关心前端图形库实现。 |
| `outline-generator` | 基于资料范围生成复习提纲。 | `AIGeneratedContent(content_type=outline)`、`SourceCitation`。 | 章节化提纲、重点、复习建议、引用。 | 不生成计划任务。 |
| `knowledge-list-generator` | 基于资料范围生成知识点清单。 | `AIGeneratedContent(content_type=knowledge_list)`、`SourceCitation`。 | 知识点、解释、重要程度、引用。 | 不维护学习掌握度模型。 |
| `handout-generator` | 基于当前二级任务和关联资料生成今日讲义。 | `AIGeneratedContent(content_type=handout)`、`SourceCitation`。 | 讲义正文、重点解释、引用。 | 不更新二级任务完成状态。 |
| `task-test-generator` | 基于测试类二级任务和关联资料生成任务测试题。 | `AIGeneratedContent(content_type=task_test)`、`SourceCitation`。 | 测试题、答案、解析、引用。 | 不等同课程自测 Quiz。 |
| `generated-content` | 统一保存和查询 AI 生成内容、内容类型、生成状态、结构化 JSON 和引用。 | `AIGeneratedContent`、`SourceCitation`。 | 生成内容详情、历史记录、引用来源。 | 不决定具体生成算法，不更新任务完成状态。 |
| `study-plans` | 自然语言配置回填、计划预览、保存单课程计划、生成一级任务和二级任务。 | `StudyPlan`、`StudyTask`、`StudySubTask`。 | 计划结构、任务结构。 | 不提前生成讲义、任务测试题或学习笔记。 |
| `todos-calendar` | 首页今日待办、首页大日历、全局当日待办弹窗、课程内计划学习模式日历查询。 | 不拥有主写模型，读取任务表。 | 日期摘要、课程分组、任务跳转参数。 | 不创建、编辑、删除或重新生成学习计划。 |
| `learning-execution` | 查询今日任务、展示执行上下文、更新二级任务完成状态。 | `StudySubTask.status`、派生更新 `StudyTask.status`。 | 今日任务、任务完成结果、执行页上下文。 | 不生成计划，不管理资料。 |
| `checkins` | 根据当日二级任务完成比例维护学习完成记录和颜色等级。 | `CheckinRecord`。 | `completion_ratio`、`color_level`。 | 不做完整统计报表，不做手动打卡。 |
| `exports` | 将已生成讲义或任务测试题导出 PDF。 | 导出文件或导出记录。 | PDF 文件或下载信息。 | 不生成讲义正文或测试题正文。 |

## 5. 独立生成模块的统一契约

所有独立生成模块都遵守同一条最小契约：

```mermaid
sequenceDiagram
    participant Caller as 调用方<br/>课程详情 / 执行页
    participant Orchestrator as generation-orchestrator
    participant Context as material-context
    participant Generator as 具体生成模块
    participant Store as generated-content

    Caller->>Orchestrator: submit(course_id, material_scope, params, idempotency_key)
    Orchestrator->>Context: resolve_context(course_id, material_scope, task_context?)
    Context-->>Orchestrator: chunks + citation_candidates
    Orchestrator->>Generator: generate(chunks, params)
    Generator-->>Orchestrator: structured_content + citations
    Orchestrator->>Store: save AIGeneratedContent + SourceCitation
    Store-->>Caller: content_id + generation_status
```

统一约束：

- 生成模块不能直接读未校验权限的数据。
- 生成模块不能绕过 `material-context` 使用资料。
- 生成模块不能直接写其他模块状态。
- 生成结果必须结构化保存，不能只返回临时文本。
- 引用必须落到 `SourceCitation`，不能伪造没有资料来源的引用。
- 生成失败必须保存或返回 `generation_status = failed` 和稳定错误码。

## 6. 依赖方向

允许的依赖方向：

- `users -> courses -> materials -> material-context -> generation-orchestrator -> generator -> generated-content`
- `courses -> study-plans -> learning-execution -> checkins`
- `study-plans -> todos-calendar`
- `learning-execution -> todos-calendar`
- `generated-content -> exports`

禁止的依赖方向：

- 具体生成模块互相依赖，例如 Flashcard 调 Mindmap 或 Mindmap 读 Quiz。
- 生成模块直接修改学习计划或任务完成状态。
- 日历聚合模块写 `StudyPlan` 或 `StudySubTask`。
- 前端绕过 API 直接依赖数据库字段细节。
- 任意模块绕过 `user_id` 和 `course_id` 归属校验。

## 7. 数据归属原则

- `User` 是数据隔离根对象。
- `Course` 是学习上下文根对象。
- `CourseMaterial`、`Conversation`、`AIGeneratedContent`、`StudyPlan`、`StudyTask`、`StudySubTask` 必须能追溯到 `Course` 和 `User`。
- `StudyPlan` 本期只绑定一个 `course_id`，不使用 `course_ids`。
- `SourceCitation` 必须关联真实资料，保留资料名快照、页码或页序号、命中文本片段。
- 软删除数据默认不进入前端列表、检索上下文、日历聚合或今日待办。

## 8. 禁止越界事项

- 禁止业务接口只凭前端传入的 ID 查询数据而不校验当前用户归属。
- 禁止 Agent 或生成模块生成没有 `material_id` 的伪引用。
- 禁止 `StudyPlan` 在本期绑定多门课程。
- 禁止首页今日待办和首页大日历承担计划创建、编辑或重新生成能力。
- 禁止计划保存阶段提前生成今日讲义或任务测试题正文。
- 禁止把 Flashcard、Mindmap、Quiz 等能力写成一个互相耦合的大生成模块。
- 禁止为了短期实现绕开 [../api-data/index.md](../api-data/index.md) 中定义的状态、错误码和契约。

## 9. 后续分工方式

当项目基座完成并进入具体模块开发时，应基于本文拆分任务：

1. 先确认模块负责人和模块边界是否稳定。
2. 再确认该模块涉及的 API、数据对象、状态枚举和验收标准。
3. 如果模块需要长期独立维护，按 [../domains/index.md](../domains/index.md) 的规则创建模块文档。
4. 模块开发任务只能细化本模块职责，不应把其他模块内部实现写入自己的任务范围。
