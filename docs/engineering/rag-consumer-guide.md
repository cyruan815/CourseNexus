# RAG Consumer Guide

## 目的

本文定义业务功能如何接入材料上下文 RAG 基础设施。基础设施负责资料解析、索引、权限过滤、检索、完整上下文、批处理和覆盖核算；业务功能继续拥有自己的提示词、输出 schema、接口、持久化和 UI。

## 两类调用链

问答类：

```text
业务权限 -> retrieve_relevant_context -> ModelProvider -> 限定引用 -> 业务保存
```

五类独立 POC 生成：

```text
业务权限 -> resolve_generation_context -> 总 token 检查
         -> 单次模型调用 -> 功能自有 schema -> 业务保存
```

学习计划和任务内容等保留批处理的消费者：

```text
业务权限 -> iter_material_context_batches -> run_material_coverage
         -> 功能自有 map/reduce -> 业务保存
```

## 问答类接入

问答、解释、追问等 query-dependent 功能应调用 `retrieve_relevant_context()`。`course-qa` 已按该方式接入生产问答路径；后续同类功能必须传入当前用户、课程、问题文本、材料范围、`RagIndex` 和 `top_k`。

检索结果只返回命中的 `ContextChunk`。业务保存引用时只能使用 `context.chunks` 中的 `chunk_id`；模型返回的引用 id 必须与允许集合取交集，不能保存未检索到、已删除、跨用户或伪造的 chunk id，也不能在交集为空时回退保存第一个检索 chunk。

推荐顺序：

1. 业务模块先完成自己的权限和参数校验。
2. 调用 `retrieve_relevant_context()` 获取硬过滤后的上下文。
3. 如果没有可用资料或没有检索命中，直接返回 `no_source`。
4. 调用 `ModelProvider` 或功能自有模型适配器。
5. 将模型引用限制到 `{chunk.chunk_id for chunk in context.chunks}`。
6. 按业务模块自己的表结构保存回答和引用。

## 指定材料生成类接入

Quiz、Flashcard、Mindmap、Outline 和 Knowledge List 调用 `resolve_generation_context()`，一次取得稳定顺序的完整选定材料上下文。

业务功能在调用模型前检查 `MaterialGenerationContext.estimated_tokens`；超过 `MATERIAL_CONTEXT_MAX_TOKENS` 时返回 `MATERIAL_CONTEXT_TOO_LARGE`，不能静默截断，也不能用一次 Top-K 检索替代全材料覆盖。学习计划等其他消费者仍可使用批处理与覆盖执行器。

每个功能自行定义：

- prompt；
- Pydantic 输出 schema；
- 最终结构化模型输出；
- 业务 schema 校验和稳定 ID/顺序；
- API、数据库持久化和前端展示。

## 基础设施边界

业务模块可以依赖：

- `app.modules.material_context.schemas`；
- `app.modules.material_context.service.retrieve_relevant_context`；
- `app.modules.material_context.service.resolve_generation_context`；
- `app.modules.material_context.service.iter_material_context_batches`；
- `app.modules.material_context.coverage.run_material_coverage`；
- `app.integrations.rag.base.RagIndex`；
- `app.integrations.model_provider.base.ModelProvider`。

业务模块禁止直接导入或调用：

- `docling`；
- `llama_index`；
- `chromadb`；
- `app.integrations.parsers.docling_parser`；
- `app.integrations.rag.llama_index_chroma`。

这些依赖属于基础设施适配层，由 router、命令或依赖注入组装。

## 错误与测试

常见错误：

- `NOT_FOUND`：材料不属于当前用户/课程，或不是已解析可用资料。
- `RETRIEVAL_FAILED`：向量检索失败。
- `MATERIAL_CONTEXT_TOO_LARGE`：五类独立生成的完整上下文超过总 token 上限。
- `MATERIAL_COVERAGE_INCOMPLETE`：仍使用批处理策略的消费者没有覆盖所有预期材料。
- `GENERATION_FAILED`：模型调用执行失败。
- `GENERATION_SCHEMA_INVALID`：模型结构化输出不符合调用方 schema。

测试必须避免 live network：

- 用 `FakeRagIndex` 覆盖 `RagIndex`。
- 用 mock/fake `ModelProvider` 覆盖模型调用。
- 断言引用 id 是允许集合的子集。
- 断言完整材料功能的 expected/processed material ids 一致。
