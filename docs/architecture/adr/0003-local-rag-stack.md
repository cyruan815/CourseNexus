# ADR 0003: Local Material Context and RAG Stack

## Status

Accepted.

## Context

CourseNexus 已有 FastAPI 单体、资料上传、`.txt` / `.md` 基础解析、`MaterialChunk`、`material-context`、课程问答、生成编排和模型 provider 边界，但当前上下文实现只按条件顺序读取 SQLite chunk，没有复杂文档解析、embedding、向量索引或语义检索。

产品中的 AI 资料业务分为两类：

1. 选定材料范围内的 RAG 问答，需要范围硬过滤、相关性检索和真实引用。
2. 指定材料生成，包括学习计划、Flashcard、Quiz、Mindmap、提纲、知识点清单、今日讲义和任务测试题，需要覆盖全部选中资料并输出结构化内容。

当前目标是小团队、本地 POC、易于开发和获得较好效果。所有基础设施在开发机本地运行，不使用 Docker；可以调用 OpenAI API。

## Options

1. 在 FastAPI 单体内采用 LlamaIndex + Docling + Chroma + OpenAI API，自建资料上下文与 RAG。
2. 在 FastAPI 单体内手写解析、切片、embedding、检索和生成编排算法。
3. 部署 RAGFlow，把解析、索引和检索交给外部 RAG 平台。
4. 使用 Qdrant 替代 Chroma，并运行独立向量数据库服务。

## Decision

当前选择方案 1：

- FastAPI 继续作为唯一后端进程和业务编排入口。
- Docling 负责复杂文档解析和结构化、token-aware 切片。
- LlamaIndex 负责 node / metadata 组织、embedding 和 retriever 编排。
- Chroma 通过 Python `PersistentClient` 嵌入后端进程，将向量持久化到本地目录，不启动 Chroma Server。
- OpenAI API 提供 embedding 和生成模型；调用必须位于 integration / provider 边界。
- SQLite 的 `CourseMaterial` / `MaterialChunk` 是权威业务数据，Chroma 是可重建的派生检索索引。
- 问答使用带 `user_id`、`course_id` 和 `material_scope` metadata filter 的 Top-K 语义检索。
- 指定材料生成从 SQLite 顺序读取全部选中 chunk，使用分批 map-reduce，不使用普通 Top-K 检索替代材料覆盖。
- RAGFlow 记录为 future 备选，不加入当前依赖、运行环境或接口。

当前实现使用 LlamaIndex 的细粒度包，而不是安装包含多余集成的 `llama-index` starter 包：

- `llama-index-core`
- `llama-index-vector-stores-chroma`
- `llama-index-embeddings-openai`
- `docling`
- `chromadb`

实际依赖版本在实现任务中通过 Python 3.12 / Windows / Conda 兼容性验证后锁定；升级跨主版本必须重新运行解析、持久化、metadata filter 和引用契约测试。

## Reasons

- 现有模块边界已经具备 `materials -> material-context -> course-qa / generation / study-plans` 形状，可原位升级，不需要拆服务。
- Docling 能在本地解析 PDF、DOCX、PPTX、图片等格式，并保留布局、页码、标题和表格信息，明显优于继续扩展纯文本 parser。
- LlamaIndex 提供成熟 ingestion、node、embedding 和 retriever 组件，减少手写 RAG 算法与胶水代码。
- Chroma `PersistentClient` 满足本地 POC 的持久化和 metadata filter 需求，不需要 Docker、独立端口或额外服务运维。
- OpenAI embedding 和生成模型能减少本地模型环境与硬件要求，适合当前效果优先的选择。
- 两条上下文接口分别优化相关性和覆盖率，避免“一次 Top-K 检索”遗漏指定材料生成所需内容。
- 保留内部 DTO 和 integration 边界能让现有业务、权限、生成记录及引用模型继续工作，这一边界主要服务当前正确性和可测试性，而不是为技术替换做过度设计。

## Consequences

- `material-context` 必须新增相关性检索和全材料分批读取两个明确接口。
- 资料只有在解析、SQLite chunk 写入和 Chroma 索引均成功后才进入 `parsed` 可用状态。
- 删除或重新解析资料必须同步删除 / 替换 Chroma 中该 `material_id` 的记录。
- Chroma metadata 必须包含 `user_id`、`course_id`、`material_id`、`chunk_id`、顺序和引用定位字段。
- 业务模块不得直接 import LlamaIndex、Docling、Chroma 或 OpenAI SDK；这些依赖限定在 `app/integrations/`。
- 模型输出必须转换为项目内部 DTO，并对指定生成能力执行 Pydantic 结构校验。
- 本地开发首次运行 Docling 可能下载模型文件，embedding 和真实生成需要 `OPENAI_API_KEY` 和网络。
- Chroma 目录需要加入 `.gitignore`，并提供从 SQLite 重建索引的维护命令。
- FastAPI 同步进程承担解析和索引时会有较长请求；当前用状态字段和重试表达，不在本 ADR 中引入队列。
- 如果未来改用 RAGFlow、Qdrant Server 或其他外部检索服务，必须新增 ADR，并保持 `material-context` 的业务接口和权限语义。

## References

- [资料上下文与 RAG 架构](../material-context-rag.md)
- [AI 资料业务线](../../product/ai-material-business.md)
- [LlamaIndex Ingestion Pipeline](https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/)
- [Docling Chunking](https://docling-project.github.io/docling/concepts/chunking/)
- [Chroma PersistentClient](https://docs.trychroma.com/reference/python/client)
- [Chroma Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering)
- [OpenAI Embeddings](https://platform.openai.com/docs/api-reference/embeddings)
- [RAGFlow](https://github.com/infiniflow/ragflow)
