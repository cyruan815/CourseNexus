# Study Mode 后端技术架构、数据流与字段说明

> 按 2026-07-16 当前代码实现整理。事实优先级：当前代码 > 当前领域文档 > 历史设计说明。

## 1. 一句话讲清

Study Mode 是 FastAPI 模块化单体中的学习闭环子系统。它从课程资料和用户目标生成计划，把计划持久化为“计划—每日任务—学习子任务”三层任务树，再将任务树投影为待办和日历；用户围绕具体子任务生成讲义、测验或提问，完成子任务时同步聚合任务、计划和打卡状态。

它的主数据是任务树，不是日历，也不是生成内容。

## 2. 总体架构

~~~mermaid
flowchart TB
    FE["React + TypeScript 前端"]
    subgraph API["FastAPI /api/v1"]
        SP["study_plans<br/>解析、诊断、预览、计划生命周期"]
        TC["todos_calendar<br/>待办和日历只读投影"]
        LE["learning_execution<br/>内容、问答、完成"]
        CK["checkins<br/>完成率和连续学习"]
    end
    MC["material_context<br/>资料校验、分批、检索"]
    MP["ModelProvider<br/>独立模型端点"]
    GEN["handout / task_test"]
    QA["course_qa"]
    DB[("SQLite")]
    CHROMA[("Chroma")]
    FILES[("本地资料")]

    FE --> API
    SP --> MC
    SP --> MP
    SP --> DB
    TC --> DB
    LE --> MC
    LE --> GEN
    LE --> QA
    LE --> CK
    LE --> DB
    GEN --> MP
    GEN --> DB
    QA --> CHROMA
    QA --> DB
    CK --> DB
    MC --> DB
    MC --> CHROMA
    MC --> FILES
~~~

| 模块 | 职责 | 写入 |
| --- | --- | --- |
| study_plans | 自然语言配置解析、诊断、预览、保存、替换、删除 | plans、tasks、subtasks |
| todos_calendar | 把任务树投影成今日待办、月历、课程日历 | 无，纯查询 |
| learning_execution | 执行上下文、讲义、测验、问答、完成/取消完成 | 子任务状态、内容、问答、引用 |
| checkins | 按日期计算完成率、颜色和连续学习 | checkin_records |

依赖模块：

- material_context：资料归属、解析状态、范围、分批和 Top-K 检索；
- materials：CourseMaterial 和 MaterialChunk；
- generated_content：AIGeneratedContent 和 SourceCitation；
- course_qa：资料问答、会话、消息、引用；
- model_provider：隔离具体模型 SDK，按用途加载配置。

## 3. 核心数据模型与存储

~~~text
StudyPlan
└── StudyTask：某一天的一组任务
    └── StudySubtask：真正执行、生成内容和完成打卡的最小单元
~~~

### 3.1 study_plans

主要字段：

- id、user_id、course_id；
- title、goal_text；
- start_date、end_date、daily_available_minutes；
- status；
- idempotency_key_hash；
- parsed_config_json；
- created_at、updated_at、deleted_at。

parsed_config_json 是计划的解释性快照，包含 confirmed_config、diagnostic_profile、material_scope、material_snapshot、coverage、capacity、generation_metadata、planner_strategy、task_snapshot、日期和可选请求哈希。

### 3.2 study_tasks

主要字段为 id、plan_id、course_id、title、task_date、status、sort_order。它表达“某一天做什么”，status 由所属子任务聚合。

### 3.3 study_subtasks

主要字段为 id、task_id、plan_id、course_id、title、type、description、related_material_ids_json、status、completed_at、sort_order。

重要设计：estimated_minutes、citation_chunk_ids、generation_parameters 不在子任务表中，而在 plan.parsed_config_json.task_snapshot 中。执行模块用 task.sort_order + subtask.sort_order 找到对应快照。

因此，关系表保存稳定且常查的业务状态，JSON 快照保留模型生成细节和可演进字段。

### 3.4 内容和引用

ai_generated_contents 主要保存 user/course/subtask、content_type、title、content、content_json、status、material_scope、error 和时间戳。

- handout：Markdown 正文在 content，格式元数据在 content_json；
- task_test：结构化题目在 content_json，并有关联 source_citations；
- failed：进入生成阶段后失败会保留记录，便于追踪和重试。

source_citations 保存 generated_content_id、material/chunk ID、资料名、页码、命中文本和顺序快照。

### 3.5 打卡

checkin_records 按 user_id + date 唯一，保存 total_subtask_count、completed_subtask_count、completion_ratio、color_level、has_tasks。

## 4. 课程资料如何进入 Study Mode

Study Mode 不解析文件，只消费资料域结果。

CourseMaterial 提供用户/课程归属、parse_status、parse_quality、diagnostics、deleted_at；MaterialChunk 提供 chunk_id、material_id、顺序、页码、标题和正文。

前端用 material_scope 传资料范围：

~~~json
{
  "include_all_parsed_materials": false,
  "material_ids": ["mat_1", "mat_2"]
}
~~~

后端校验资料属于当前用户和课程、未删除、已可消费。质量为 partial 或 unknown 时可以继续，但警告写进 generation_metadata.material_quality。

| 场景 | 资料使用方式 |
| --- | --- |
| 诊断、计划、讲义、测验 | 范围内全部资料按 token 预算分批 |
| 子任务问答 | 向量检索 Top-K chunk |

默认分批预算约 12000 个估算 token，课程问答默认 Top-K 为 8。

## 5. 计划创建完整数据流

~~~mermaid
sequenceDiagram
    participant FE as 前端向导
    participant SP as study_plans
    participant MC as material_context
    participant LLM as ModelProvider
    participant DB as SQLite

    FE->>SP: goal_text + material_scope
    SP->>LLM: study_plan_parser
    SP-->>FE: 结构化配置 + 待确认字段
    FE->>SP: 已确认配置
    SP->>MC: 全量资料上下文
    SP->>LLM: study_plan_diagnostic
    SP-->>FE: 诊断题
    FE->>SP: 诊断答案
    SP-->>FE: diagnostic_profile
    FE->>SP: 配置 + 画像
    SP->>MC: 校验并分批
    SP->>LLM: Map 各批资料
    SP->>LLM: Reduce 完整任务树
    SP-->>FE: preview + capacity + coverage
    FE->>SP: 完整 tasks + Idempotency-Key
    SP->>DB: 原子写入任务树和打卡
    SP-->>FE: 已保存计划
~~~

### 5.1 配置解析

POST /api/v1/courses/{course_id}/study-plan-config-parses

输入核心字段为 goal_text 和 material_scope。后端调用 study_plan_parser 得到结构化结果，再用确定性规则归一化日期、中文时长和偏好。响应可含 unresolved_fields、needs_confirmation_fields、field_labels、field_prompts、field_options、preference_overrides。此步不落库。

### 5.2 诊断

- POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions
- POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles

题目生成读取范围内全部资料，调用 study_plan_diagnostic，并校验主题能追溯到真实 chunk；失败时使用确定性回退。契约为 3 道 topic_mastery、1 道 weak_area、可选 1 道 diagnostic_note。

画像要求 3 个唯一主题答案和当前 v2 题目版本。none/heard 视为薄弱，多数薄弱时 foundation_needed=true，weak_area 映射为 explanation_style。结果不单独落表。

### 5.3 计划预览

POST /api/v1/courses/{course_id}/study-plans/preview

必须有 start_date，end_date 和 duration_days 至少一个。资料先按预算分批，每批 Map 成 PlanMaterialUnit，再 Reduce 成完整任务树；必要时进行一次修复性 Reduce。

模型输出还要经过确定性校验：

- 日期在计划范围内；
- material/chunk 引用在所选范围内；
- 每天恰好一个最终 quiz 或 test；
- 最后一天满足整体覆盖；
- learn/review 不携带测验参数；
- 超出容量时返回警告。

预览返回完整 tasks，但不写任务树。

### 5.4 保存

POST /api/v1/courses/{course_id}/study-plans，请求头为 Idempotency-Key。

wizard_v1 保存的是用户看到并确认的完整 tasks，不再次调用模型。后端再次验证任务树、归一化测验参数、计算请求哈希，然后在一个事务中写入 plan/task/subtask 并重算 checkin。

幂等语义：

- 同一键 + 同一请求：返回原计划；
- 同一键 + 不同请求：冲突；
- 无键时也拒绝明显重复计划；
- 软删除计划仍占用原幂等键。

## 6. 偏好和容量算法

| preference | 表达 | 示例 | 测验 | 复习 |
| --- | --- | --- | --- | --- |
| fast_track | concise | low | low | low |
| balanced | standard | standard | standard | standard |
| mastery | detailed | high | high | high |
| sprint | focused | standard | high | high |

preference_overrides 做字段级覆盖，诊断再补 foundation_required、weak_topics、weak_area、explanation_style。优先级为：时间硬约束 > 必要基础 > 偏好 > 额外例子/测试/复习。

~~~text
recommended_daily_minutes =
    max(30, ceil(mapped_estimated_total / duration_days))

available_total_minutes =
    daily_available_minutes × duration_days
~~~

容量状态为 ok、tight、over_capacity。超出时返回 PLAN_OVER_CAPACITY，让用户确认，不静默删任务。

## 7. 保存后的读模型

计划详情返回扁平结构：

~~~json
{"plan": {}, "tasks": [], "subtasks": []}
~~~

待办与日历接口：

- GET /api/v1/todos/today
- GET /api/v1/calendar/month
- GET /api/v1/calendar/days/{target_date}/todos
- GET /api/v1/courses/{course_id}/study-calendar
- GET /api/v1/courses/{course_id}/study-calendar/days/{target_date}

todos_calendar 不维护独立表，而是联查任务树、过滤越权和软删除数据、按日期和顺序构造 DTO。若持久化聚合状态与子任务推导状态冲突，返回 STATE_CONFLICT；GET 不静默修复。日历摘要最多 3 条。

## 8. 学习执行和内容生成

### 8.1 执行上下文与问答

GET /api/v1/study-subtasks/{subtask_id}/execution-context 返回计划、任务、子任务、业务日期、关联资料、最近成功 handout/task_test ID。

POST /api/v1/study-subtasks/{subtask_id}/qa/questions 只需传 conversation_id（可选）和 question。后端从子任务 related_material_ids_json 派生资料范围，course_qa 做 Top-K 检索，并保存会话、消息和引用；不修改完成状态。

### 8.2 讲义

POST /api/v1/study-subtasks/{subtask_id}/handouts，仅 learn/review 可用。

默认复用最近成功版本；force_regenerate=true 才新建。生成优先使用 task_snapshot.citation_chunk_ids，按资料批次调用模型，多批次再综合。每批和最终 Markdown 必须至少包含 SVG 或 Mermaid。正文存 content，元数据存 content_json；当前讲义不写 source_citations 行。

### 8.3 测验

POST /api/v1/study-subtasks/{subtask_id}/task-tests，仅 quiz/test 可用。

从快照读取 generation_parameters，使用全部允许资料批次结构化生成，并验证题数、题型分布、q_1 到 q_N 稳定 ID、A-D 选项、答案、重复题、chunk 归属。题目写入 content_json，引用写入 source_citations，题目中的 source_citation_ids 改写为数据库引用记录 ID。

讲义和测验进入生成后失败会保留 failed AIGeneratedContent；生成前的越权或类型错误不创建失败记录。

## 9. 完成状态和打卡事务

PUT /api/v1/study-subtasks/{subtask_id}/completion 接收目标状态，不是 toggle：

~~~json
{"completed": true}
~~~

同一状态重复请求返回 changed=false，不刷新 completed_at。

~~~mermaid
flowchart LR
    R["completion 请求"]
    S["更新 subtask"]
    T["聚合 task.status"]
    P["聚合 plan.status"]
    C["重算当日 checkin"]
    X["提交事务"]
    R --> S --> T --> P --> C --> X
~~~

任一步失败全部回滚。completion_ratio 使用 Decimal 四位精度，color_level 为 0–5。连续学习天数按“当天有任务且至少完成一个子任务”计算。

## 10. 替换、删除和并发

- POST /api/v1/study-plans/{plan_id}/regeneration-previews：生成替换预览；
- PUT /api/v1/study-plans/{plan_id}：用 expected_updated_at 乐观锁替换；
- DELETE /api/v1/study-plans/{plan_id}：软删除。

有学习进度或已绑定生成内容时不允许替换。替换通过原子 claim 后重建任务树，并重算旧、新日期 checkin。删除后日历自动过滤计划并重算相关日期。

## 11. API 响应和字段传输

成功响应：

~~~json
{
  "data": {},
  "meta": {
    "request_id": "req_xxx",
    "server_time": "2026-07-16T10:00:00Z",
    "api_version": "v1"
  }
}
~~~

错误响应：

~~~json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "可读错误",
    "details": {}
  },
  "meta": {"request_id": "req_xxx"}
}
~~~

前端 API client 附加 Bearer Token、序列化 JSON、解包 data，401 时清理 token。文件流不使用 JSON envelope。

### 11.1 传输—解析—存储总表

| 数据 | 来源 | 校验/解析 | 存储 |
| --- | --- | --- | --- |
| 自然语言目标 | goal_text | 模型结构化 + 日期/时长/偏好规则 | goal_text、parsed_config_json |
| 资料范围 | material_scope | 用户、课程、删除、解析状态 | plan 快照、subtask.related_material_ids_json |
| 诊断题 | chunks + 模型 | 主题必须追溯真实 chunk | 不单独落表 |
| 诊断答案 | 前端 | 版本、题数、主题唯一性 | diagnostic_profile 快照 |
| 计划预览 | Map/Reduce | 日期、容量、覆盖、引用、每日终测验 | 保存前不落库 |
| 任务树 | 确认后的 tasks | 保存时完整复验 | plans、tasks、subtasks |
| 生成细节 | preview | 参数归一化 | plan.task_snapshot |
| 待办/日历 | 任务树 | 联查、过滤、聚合 | 不落库 |
| 问答 | question + 任务资料范围 | Top-K + 引用校验 | conversations、messages、citations |
| 讲义 | 快照 + 全量批次 | Markdown、SVG/Mermaid | ai_generated_contents |
| 测验 | 参数 + 全量批次 | 题型、数量、答案、引用 | contents + citations |
| 完成 | completed 布尔值 | 权限、幂等、聚合 | subtask、task、plan、checkin |

## 12. 模型端点和失败策略

独立端点包括 study_plan_parser、study_plan_diagnostic、study_plan_generator、handout、task_test、course_qa；均可通过环境变量独立配置。仓库当前可运行示例使用 DeepSeek `deepseek-flash`，但 Provider Factory 不把模型名硬编码为业务规则。

当前是同步处理、没有任务队列。资源控制依赖资料分批、Top-K、超时重试、成功内容复用和显式 force_regenerate。

| 失败场景 | 策略 |
| --- | --- |
| 资料越权/删除/未解析 | 模型调用前拒绝 |
| 模型结构错误 | Schema 和领域规则拒绝，部分流程修复重试 |
| 引用范围外资料/chunk | 保存前拒绝 |
| 超容量 | 警告并等待用户确认 |
| 保存重试 | Idempotency-Key 返回原计划 |
| 并发替换 | expected_updated_at 冲突 |
| 内容生成中途失败 | 保存 failed 记录 |
| 完成传播失败 | 整个事务回滚 |
| GET 发现状态冲突 | STATE_CONFLICT，不静默修复 |

## 13. 当前契约漂移

1. 后端配置解析已有 preference_overrides、needs_confirmation_fields、field_labels/prompts/options；前端类型和页面未完整透传，细粒度自然语言偏好可能丢失。
2. 后端 CompletionCheckinRead 使用 total_subtask_count、completed_subtask_count、completion_ratio、color_level、has_tasks；前端仍残留 planned_subtask_count 等旧字段并依赖回退。
3. 日历 DTO 的 execution_url 当前固定为 null；实际依靠 first_incomplete_subtask_id/subtask_id 导航。
4. system-flow-guide 的部分日期追问描述已落后；当前创建页已实现 start date 和 duration 追问，应以代码和 plan-builder-wizard.md 为准。

## 14. 当前测试基线

2026-07-16 验证：

~~~text
uv run python -m pytest tests/modules/study_plans -q
128 passed
~~~

宽范围 Study Mode 测试：

~~~text
205 passed, 20 failed
~~~

失败主要是旧 mock/fixture 未跟上两项新规则：讲义至少包含 SVG/Mermaid；每天恰好一个最终 assessment。因此可以确认计划模块测试通过，但不能说整个 Study Mode 测试集全绿。

## 15. 代码入口

| 关注点 | 路径 |
| --- | --- |
| API 路由挂载 | backend/app/api/v1/router.py |
| 统一响应/错误 | backend/app/api/responses.py、backend/app/core/errors.py |
| 计划 API/编排 | backend/app/modules/study_plans/router.py、service.py |
| Map/Reduce 规划 | backend/app/modules/study_plans/planner.py |
| 任务树规则 | backend/app/modules/study_plans/task_tree_rules.py |
| 学习执行 | backend/app/modules/learning_execution/ |
| 待办日历 | backend/app/modules/todos_calendar/ |
| 打卡 | backend/app/modules/checkins/ |
| 资料上下文 | backend/app/modules/material_context/ |
| 讲义/测验 | backend/app/modules/handout/、task_test/ |
| 生成内容/引用 | backend/app/modules/generated_content/ |
| 课程问答 | backend/app/modules/course_qa/ |
| 前端类型/页面 | frontend/src/features/study-plans/、frontend/src/pages/StudyPlanCreatePage.tsx |

## 16. 推荐讲法

介绍时按这条主线：

1. 主数据是一棵计划任务树；
2. 解析、诊断、预览无状态，确认后才保存；
3. 计划/内容用全量分批，问答用 Top-K；
4. 日历是读模型，StudySubtask 是执行入口；
5. learn/review 生成讲义，quiz/test 生成测验；
6. 完成时一个事务聚合 subtask、task、plan、checkin；
7. 工程保障是幂等、快照、权限、输出校验、失败记录和乐观锁。

### 三分钟讲解稿

> Study Mode 后端是 FastAPI 模块化单体中的学习闭环子系统。核心数据是 StudyPlan、StudyTask、StudySubtask 三层任务树。用户先用自然语言描述目标，后端解析成结构化配置，再基于课程资料生成诊断题和学习画像。计划采用 Map/Reduce：资料按 token 预算分批抽取规划单元，再合并为完整日程；模型输出还必须通过日期、容量、资料引用和“每天恰好一个最终测验”等确定性规则。
>
> 解析、诊断和预览阶段不落任务树。用户确认后，前端把完整 tasks 和 Idempotency-Key 交给保存接口，后端在一个事务中写入计划、每日任务和子任务。关系表存稳定状态，estimated_minutes、chunk 引用和生成参数保留在 JSON 任务快照中。
>
> 保存后，todos_calendar 将任务树只读投影为待办和日历。用户进入子任务后，learning_execution 按类型提供讲义、测验或资料限定问答。最后，完成接口设置目标状态，并在同一事务中更新子任务、聚合任务和计划、重算打卡，形成闭环。

## 17. 相关领域文档

- [计划构建向导](plan-builder-wizard.md)
- [自然语言配置解析](natural-language-config-parse-plan.md)
- [诊断题](diagnostic-questions.md)
- [计划生命周期](plan-lifecycle.md)
- [待办与日历](todos-calendar.md)
- [学习执行](learning-execution.md)
- [打卡](checkins.md)
- [任务内容生成](task-content.md)
