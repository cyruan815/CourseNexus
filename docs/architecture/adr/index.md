# Architecture Decision Records

## 概述

本目录记录 CourseNexus 的长期架构决策。ADR 用于解释为什么选择某个技术方案，而不是记录临时任务计划。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [0001-tech-stack.md](0001-tech-stack.md) | Accepted；v0.1 技术栈与本地 POC 架构选择。 | 2026-07-09 |
| [0002-foundation-runtime-dependencies.md](0002-foundation-runtime-dependencies.md) | Accepted；基础设施运行依赖、显式 Mock 边界、生产配置校验和 OpenAI SDK 接入边界。 | 2026-10-01 |
| [0003-local-rag-stack.md](0003-local-rag-stack.md) | Accepted；本地资料上下文与 RAG 采用 LlamaIndex、Docling、Chroma 和用途级独立 OpenAI-compatible API，并统一本地路径与进程级索引生命周期。 | 2026-10-01 |
| [0004-frontend-ui-foundation.md](0004-frontend-ui-foundation.md) | Accepted；前端 UI 基础设施采用 Mantine、Tabler Icons、TanStack Query 和 dayjs。 | 2026-07-10 |
| [0005-simplified-generation-poc.md](0005-simplified-generation-poc.md) | Accepted；五类独立 POC 使用完整材料上下文单次生成，不保存逐条引用。 | 2026-07-13 |
| [0006-handout-pdf-rendering.md](0006-handout-pdf-rendering.md) | Accepted；今日讲义 PDF 导出采用 Markdown/HTML/Playwright Chromium 打印链路。 | 2026-07-13 |
| [0007-frontend-handout-mermaid-svg.md](0007-frontend-handout-mermaid-svg.md) | Accepted；可信本地 POC 的前端讲义使用 Mermaid 和 rehype-raw 渲染 Mermaid 图表与原始 SVG。 | 2026-07-15 |
| [0008-frontend-unified-file-preview.md](0008-frontend-unified-file-preview.md) | Accepted；前端统一文件预览器使用格式适配器直接只读渲染 PDF、DOCX、PPTX、图片和文本。 | 2026-10-01 |
| [0009-versioned-material-parsing.md](0009-versioned-material-parsing.md) | Accepted；材料重解析采用候选版本构建、向量完整性校验和生效指针原子切换。 | 2026-10-01 |

## 相关链接

- [../index.md](../index.md)：架构分区入口。
- [../overview.md](../overview.md)：架构文档 v0.1。
- [../module-boundaries.md](../module-boundaries.md)：模块拓扑与边界说明。
- [../../api-data/index.md](../../api-data/index.md)：API、数据模型和契约入口。

## 维护规则

- 引入或替换核心框架、数据库、ORM、鉴权方式、文件存储、后台任务方案或模型服务集成方式时，必须新增或更新 ADR。
- 改变前后端分离方式、模块边界、API 版本策略、错误码体系或数据迁移策略时，必须新增或更新 ADR。
- ADR 文件名使用四位递增编号和短横线标题，例如 `0001-tech-stack.md`。
- 每个 ADR 至少包含 `Status`、`Context`、`Options`、`Decision`、`Reasons`、`Consequences`。
- ADR 状态使用 `Proposed`、`Accepted`、`Deprecated`、`Superseded`。
