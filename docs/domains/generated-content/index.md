# Generated Content 领域

## 1. 业务定位

本领域统一承载课程资料生成结果、生成状态、资料范围快照和引用来源。G01 已建立五类独立生成器共用的编排与存储合同；Quiz、Flashcard、Mindmap、Outline 和 Knowledge List 的真实业务生成分别由 G02-G06 实现。

## 2. 代码入口

- 请求与生成编排：`backend/app/modules/generation/orchestrator/`
- 生成器注册入口：`backend/app/modules/generation/orchestrator/registry.py`
- 五类生成器目录：`backend/app/modules/generation/generators/`
- 历史、详情与引用响应：`backend/app/modules/generated_content/`
- 全材料上下文：`backend/app/modules/material_context/`
- 模型调用边界：`backend/app/integrations/model_provider/`
- 公共测试夹具：`backend/tests/modules/generation/conftest.py`

## 3. 当前状态

- G01：全材料批次、用途模型注入、生成器工厂、引用过滤与回填、原子持久化、历史/详情引用响应已经实现。
- G02-G06：仍由 deterministic placeholder 提供增量开发 fallback，不代表最终内容质量或业务 schema 已完成。
- 当前没有队列、取消、进度查询或持久化幂等键；重复请求生成独立记录。

详细架构、算法、资源预算和失败策略见 [architecture.md](architecture.md)。
