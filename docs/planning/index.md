# Planning

## 概述

本目录记录 CourseNexus 的共享规划沉淀：当前状态、实现路线图、技术债和信息处理优化计划。

它不是临时 Agent 执行草稿目录。临时插件过程、个人执行记录和 superpowers 运行产物放入 `docs/superpowers/`，该目录不进入 git。凡是需要团队共享、后续继续维护或影响路线判断的内容，应进入本目录或其他正式 docs 分区。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [current-state.md](current-state.md) | 可靠单机 V1 当前能力、发布边界、验证结果和延期范围。 | 2026-10-01 |
| [v1-completion-matrix.md](v1-completion-matrix.md) | P/S/R/M 收口事项、对应 PR、验证证据、限制和延期项。 | 2026-10-01 |
| [implementation-roadmap.md](implementation-roadmap.md) | V1 发布动作及共享部署、规模和体验的后续路线。 | 2026-10-01 |
| [tech-debt-tracker.md](tech-debt-tracker.md) | 当前已知技术债、关闭证据、影响和接受边界。 | 2026-10-01 |
| [material-understanding-pipeline-tech-debt.md](material-understanding-pipeline-tech-debt.md) | TD-017：多格式分层解析、完整性审计、透明迁移、结构化切块与自适应检索的大型技术债。 | 2026-07-14 |
| [information-processing-optimization.md](information-processing-optimization.md) | 资料解析、切片、检索、引用、生成和学习反馈链路优化计划。 | 2026-07-09 |

## 相关链接

- [../index.md](../index.md)：项目长期知识库总入口。
- [../architecture/index.md](../architecture/index.md)：架构、模块边界和 ADR 入口。
- [../api-data/index.md](../api-data/index.md)：API、数据模型和契约入口。
- [../engineering/index.md](../engineering/index.md)：工程基线和协作规则入口。

## 维护规则

- 当前状态变化、阶段路线调整、技术债新增或关闭时，更新本目录。
- V1 完成状态以 `v1-completion-matrix.md` 为权威入口；临时 `tmp/` 评审稿不得覆盖正式状态。
- 本目录记录共享规划，不记录一次性聊天计划或个人草稿。
- 形成架构、API、数据契约或工程约定变更时，同步迁移或补充到对应正式分区。
