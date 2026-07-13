# ADR 0005: Simplified Complete-Context Generation POC

## Status

Accepted

## Context

Quiz、Flashcard、Mindmap、Outline 和 Knowledge List 原实现按材料分批调用模型，再执行 map/reduce、候选去重和逐条引用回填。该实现能够追溯来源，但模型调用次数、编排复杂度和失败补偿超过当前 POC 验证五类内容可用性的需要。

当前 POC 优先验证完整资料能否生成可展示、可保存、可重新打开的结构化结果。Course QA、学习计划、handout 和 task_test 仍有各自的检索、批处理或引用要求，不应因五类独立生成的简化而改变。

## Options

1. 保留多批次 map/reduce 和逐条引用，继续优化原实现。
2. 五类独立生成改为完整上下文单次模型调用，超限时要求用户减少资料；其他消费者保持现有策略。
3. 使用 Top-K 或静默截断控制上下文大小。

## Decision

选择方案 2。

五类独立生成通过 `material-context.resolve_generation_context()` 按稳定顺序读取全部选定 parsed chunk，使用 tokenizer 计算完整上下文 token，并在限制内对对应模型执行一次结构化调用。超限返回 `MATERIAL_CONTEXT_TOO_LARGE`，不调用模型、不截断、不改用 Top-K。

五类业务 JSON 不包含 `source_chunk_ids` 或 `source_citation_ids`，成功时只写 `AIGeneratedContent`；公共响应外壳继续返回 `source_citations=[]`。现有 `source_citations` 表、Course QA、学习计划、handout 和 task_test 的检索、批处理及引用行为保持不变。

Mindmap preprocessing runs in the backend through official `markmap-lib`; the persisted preprocessed tree is rendered by frontend `markmap-view`.

## Reasons

- 一次请求对应一次模型调用，能够直接验证五类生成的产品可行性和成本。
- 完整上下文避免跨批次去重、引用合并和 reduce 语义漂移。
- 明确超限比静默截断或 Top-K 更符合“覆盖全部选中资料”的产品约束。
- 将决策限定到五类独立生成，可以保留主系统公共上下文能力以及 Study Mode 已实现的批处理与真实引用链路。

## Consequences

- 生成器、测试和文档显著简化，历史与详情仍复用统一生成内容接口。
- 大型资料范围可能在模型调用前失败，用户需要减少选择范围。
- 五类 POC 当前不提供题目、卡片、节点、章节或知识点级来源追溯。
- `material-context` 同时维护相关性检索、完整生成上下文和全材料批次三个公共入口；新增逻辑不得覆盖或改变既有消费者语义。
- ADR 0003 的分批生成约束继续适用于学习计划、handout、task_test 等保留批处理的消费者；本 ADR 仅覆盖五类独立 POC。
