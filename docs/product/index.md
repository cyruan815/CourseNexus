# Product

## 概述

本目录记录 CourseNexus 的产品需求入口、PRD 指向和后续产品范围变化。任何影响产品行为、业务流程、页面验收或非目标范围的变更，都必须更新本分区。

`prd.md` 是 Agent 查找产品需求的权威入口；完整 PRD 原文位于 [PRD/README.md](PRD/README.md)。

## 文档清单

| 文件名 | 摘要 | 最后更新 |
| --- | --- | --- |
| [prd.md](prd.md) | 产品需求权威入口，指向完整 PRD 文档包并摘要当前产品口径。 | 2026-07-09 |
| [PRD/README.md](PRD/README.md) | PRD v0.3 文档包说明、阅读顺序和关键产品口径。 | 2026-07-09 |

## 相关链接

- [../index.md](../index.md)：项目长期知识库总入口。
- [../architecture/index.md](../architecture/index.md)：架构、模块边界和 ADR 入口。
- [../api-data/index.md](../api-data/index.md)：API、数据模型和契约入口。

## 维护规则

- `prd.md` 必须始终是产品需求权威入口。
- PRD 文档包移动、重命名或升级版本时，必须先更新 `prd.md`。
- 产品行为变化、MVP 范围变化、验收口径变化时，必须同步更新本分区。
- 后续如需用户流程、验收标准、非目标范围等独立文档，可以在本分区扩展；当前 v0.1 不额外创建文件。
