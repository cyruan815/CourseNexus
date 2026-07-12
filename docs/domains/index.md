# Domains

## 概述

本目录是业务功能实现知识库入口，用于沉淀稳定的领域知识、业务术语、实际代码入口、实现架构、状态流转、关键算法和跨模块规则。

项目已经进入功能并行开发阶段。每个任务开始时必须确定对应领域文档路径；实现过程中同步更新，任务验收时领域文档与代码、测试一起交付。领域文档不替代 PRD、全局架构或 API 契约，而是回答“这个功能在当前代码中如何工作”。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [index.md](index.md) | 领域知识库入口、创建触发条件、目录结构和交付要求。 | 2026-07-11 |
| [implementation-template.md](implementation-template.md) | 前后端领域实现文档模板，后端包含架构与算法强制章节。 | 2026-07-10 |
| [auth/index.md](auth/index.md) | 注册、登录、登录态和前端认证入口实现。 | 2026-07-11 |
| [courses/index.md](courses/index.md) | 课程首页工作台和后续课程管理实现。 | 2026-07-11 |
| [course-workspace/index.md](course-workspace/index.md) | 课程详情工作台、资料范围、问答、生成内容和学习计划入口实现。 | 2026-07-12 |
| [materials/index.md](materials/index.md) | 资料上传、一级文件夹归类、逐文件范围、解析索引和前端工作区实现。 | 2026-07-10 |
| [courses/index.md](courses/index.md) | 课程创建、列表和统一学期选项契约。 | 2026-07-12 |
| [study-mode/plan-lifecycle.md](study-mode/plan-lifecycle.md) | S02 学习计划生命周期：配置回填、全材料预览、保存幂等、替换、重生成和软删除。 | 2026-07-11 |
| [study-mode/plan-builder-wizard.md](study-mode/plan-builder-wizard.md) | Study Mode 计划生成向导：目标输入、配置确认、学前诊断、preview 页面和字段契约设计。 | 2026-07-12 |
| [study-mode/todos-calendar.md](study-mode/todos-calendar.md) | S03 今日待办与日历聚合：五个只读查询、日期摘要、课程分组和零写边界。 | 2026-07-11 |
| [study-mode/task-content.md](study-mode/task-content.md) | S06 任务讲义与任务测试题：按需生成、幂等复用、材料范围、测试题硬约束和失败记录。 | 2026-07-12 |

## 相关链接

- [../index.md](../index.md)：项目长期知识库总入口。
- [../product/prd.md](../product/prd.md)：产品需求权威入口。
- [../architecture/module-boundaries.md](../architecture/module-boundaries.md)：全局模块边界说明。
- [../api-data/index.md](../api-data/index.md)：API、数据模型和契约入口。

## 维护规则

- 模块负责人和任务范围确定后，任务实现必须创建或更新对应领域文档，不能等整个阶段结束后集中补写。
- 领域目录按业务能力聚合，不按单个组件、router 或数据库表机械拆分。
- 每个领域至少有 `index.md`；复杂领域可继续拆分 `architecture.md`、`frontend.md` 和具体功能文档。
- 同一个小功能所需的代码、测试和领域文档进入同一提交或同一组连续小提交。
- 模块文档必须与全局模块边界、API / 数据契约和 PRD 保持一致。
- 不得把临时实现细节写成长期领域规则。

## 领域文档最小内容

所有领域实现文档至少记录：

- 业务目标、用户场景、范围和非目标。
- 模块负责人、实际代码入口和目录边界。
- 上下游依赖、公开接口和禁止依赖。
- 数据对象、状态流转、权限和错误处理。
- 当前实现流程、关键设计决策和已知限制。
- 自动化测试、手工验收和运行排障入口。
- 可执行自动化测试代码保留在项目标准测试目录，例如 `backend/tests/`、`frontend/tests/`；领域文档只记录测试入口、覆盖范围和运行命令，不复制测试代码。
- 真实文件回归报告、手工验收记录、模型效果验证和阶段性领域验证证据放入对应的 `docs/domains/<domain>/validation/`；跨领域的全局验收才进入共享工程或规划分区。
- 大型测试样本、生成文件、日志原件和包含敏感信息的数据不得提交到 `docs/`；文档只记录可复现条件、摘要、哈希和脱敏结果。

后端功能还必须记录：

- 组件关系或 Mermaid 架构图，以及请求、数据和状态的数据流。
- 核心算法的输入、输出、不变量、步骤或伪代码。
- 查询排序、去重、聚合、批处理、事务、幂等和补偿规则。
- 时间复杂度、空间复杂度，或模型 token、批次、文件大小等资源预算。
- AI 功能的 prompt 职责、结构化 schema、map/reduce、材料覆盖和引用约束。
- 算法失败、第三方失败、部分写入和重试时的处理方式。

## 第一阶段领域划分

| 领域目录 | 主要内容 |
| --- | --- |
| `auth/` | 账号、登录态和前端认证接入。 |
| `courses/` | 课程管理和首页课程工作台。 |
| `course-workspace/` | 课程详情布局和共享资料范围。 |
| `materials/` | 资料上传、一级文件夹归类、解析、索引、逐文件范围选择和前端资料工作区。 |
| `course-qa/` | 课程资料问答、会话、消息和引用。 |
| `generated-content/` | 公共生成编排及 Quiz、Flashcard、Mindmap、Outline、Knowledge List。 |
| `study-mode/` | 计划生成、日历聚合、任务执行、打卡、任务内容和 PDF 导出。 |

具体文件所有权以第一阶段任务书的“领域文档交付映射”为准。
