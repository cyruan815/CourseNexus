# ADR 0009：材料解析采用候选版本原子切换

- Status: Accepted
- Date: 2026-10-01

## Context

旧解析流程会在重解析开始时删除当前 SQLite 切片和 Chroma 向量，再解析、写入和索引新内容。解析器、Embedding、Chroma 或数据库切换中的任一阶段失败，都会让一份原本可学习的资料失去旧内容。`parse_status` 只能表达一次操作状态，也无法让引用、生成结果和学习计划说明实际使用的是哪一轮材料内容。

SQLite、Chroma 和本地文件系统不共享事务。当前单机 V1 仍需要保证：候选版本失败不能破坏旧的可用版本；候选和退休版本不能混入当前检索；历史引用与生成范围能追溯到实际输入版本。

## Options

1. 禁止已解析资料再次解析，以规避覆盖风险。
2. 继续原地替换切片，通过失败后重新解析或重建索引恢复。
3. 为每轮解析建立版本，在候选内容和向量完整后原子切换生效指针，失败时回退候选并保留旧版本。

## Decision

采用方案 3：

- `material_parse_versions` 保存每轮解析，状态为 `building`、`active`、`failed` 或 `retired`；同一材料最多存在一个 `building` 版本。
- `course_materials.active_parse_version_id` 是当前学习可用版本的唯一指针。`is_learning_ready` 由该指针和资料未删除状态派生，不再把 `parse_status = parsed` 当成唯一可用判据。
- `material_chunks.parse_version_id` 非空；切片 ID 包含解析版本，使候选、当前和退休切片可以同时保留且不会冲突。
- 新解析先创建 `building` 候选，保存候选切片，以 `parse_version_id` 写入 Chroma，并校验候选向量 ID 与 SQLite 切片 ID 完全一致；随后在一个数据库事务中把旧 `active` 改为 `retired`、候选改为 `active` 并切换材料指针。
- 解析、索引、完整性校验或切换失败时只删除候选切片和候选向量，候选标记为 `failed`。已有生效版本继续可学习，材料记录保存本次 `parse_error`；首次解析失败时没有生效版本，资料进入 `parse_failed`。
- `material-context` 的完整上下文、质量诊断和 Top-K 检索只接受 `active_parse_version_id` 对应的切片。向量查询除用户、课程和材料范围外，还使用当前生效切片 ID 硬过滤。
- `SourceCitation.material_version_id`、生成内容的材料范围快照和学习计划的材料快照记录实际输入版本。删除资料时版本外键与引用版本外键按既有快照规则清理。
- 退休和失败版本本轮不自动清理；Chroma 是派生存储，全量重建只重新写入当前生效版本。

## Reasons

- 候选构建与生效切换分离后，远端模型、解析器和向量库失败不会破坏已验证的学习内容。
- 一个明确的生效指针让 SQLite 完整上下文和 Chroma 检索使用同一版本边界，避免仅靠易变化的状态字符串推断。
- 版本化引用和范围快照能解释历史回答、生成内容和计划基于哪一轮材料，而不是把同一个 `material_id` 当作永远不变的内容。
- 保留退休版本便于本地 V1 排障和历史追溯；清理策略可以在有真实容量数据后单独设计。

## Consequences

- 数据库新增解析版本表、三个版本外键及对应索引；旧库升级会为已有有效切片创建生效版本。标记为已解析但没有切片的异常资料会改为不可用并记录 `MIGRATION_EMPTY_PARSE`。
- 迁移窗口中仍无版本的切片会进入独立 `retired` 恢复版本并记录 `MIGRATION_UNVERSIONED_CHUNKS`，不得静默并入当前生效内容。
- 前端必须区分“首次解析失败”和“更新失败但旧版本仍可用”，并允许对已有生效版本发起重新解析。
- 删除和目录移动的补偿快照必须携带 `parse_version_id`；启用 SQLite 外键时，删除材料会级联清理其解析版本与切片。
- 当前同步解析接口仍可能耗时；本决策不引入后台任务、版本清理 API、版本回滚 UI 或跨进程解析锁。

## References

- [资料上下文与 RAG 架构](../material-context-rag.md)
- [资料领域实现](../../domains/materials/index.md)
- [数据表契约](../../api-data/table-schema.md)
