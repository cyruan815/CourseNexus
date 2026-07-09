# Information Processing Optimization

## 文档定位

本文记录 CourseNexus 资料处理与 AI 生成链路的优化计划。这里的“信息处理”不是临时 Agent 执行过程，而是课程资料从上传到解析、切片、检索、引用、生成、学习反馈的可维护流水线。

## 当前基线

当前系统已完成：

- `CourseMaterial`、`MaterialChunk`、`SourceCitation`、`AIGeneratedContent` 等核心表结构。
- 资料上下文层、生成编排层、独立生成模块的架构边界文档。
- 本地文件存储、parser、model、pdf adapter 的目录占位。

当前尚未完成：

- 真实资料上传。
- 文档解析和切片。
- 检索或上下文筛选。
- 模型调用和输出校验。
- 引用来源质量校验。
- 生成失败重试和质量反馈。

## 设计原则

1. 资料是事实根
   - 所有问答、生成、计划辅助内容都必须能追溯到课程资料。
   - 不能生成没有真实资料关联的引用来源。

2. 解析状态先于生成
   - 只有 `parse_status = parsed` 的资料可以进入上下文。
   - 解析失败必须保存状态和错误原因，允许用户重试。

3. chunk 是引用和检索的共同底座
   - chunk 必须记录材料、位置、页码或可定位信息。
   - 引用来源应指向 `CourseMaterial` 和可选 `MaterialChunk`。

4. 模型只产出候选结果
   - 模型输出必须经过 schema 校验、引用校验和状态落库。
   - 生成结果统一写入 `AIGeneratedContent`，引用统一写入 `SourceCitation`。

5. 生成能力彼此独立
   - Quiz、Flashcard、Mindmap、Outline、Knowledge List、Handout、Task Test 不互相调用。
   - 公共能力通过资料上下文层和生成编排层复用。

## 目标链路

```text
资料上传
  -> 文件记录与权限归属
  -> parser adapter 抽取文本
  -> chunk 生成与位置定位
  -> material-context 筛选资料范围
  -> generation orchestrator 调用独立生成器
  -> model adapter 生成结构化候选
  -> schema 校验与引用校验
  -> AIGeneratedContent / SourceCitation 落库
  -> 前端展示、重试、导出和学习反馈
```

## 分阶段优化

### P0：解析状态和错误原因

目标：

- 明确上传、解析中、解析成功、解析失败状态。
- 保存解析失败原因和重试入口。
- 阻止失败资料进入问答和生成。

验收：

- 每份资料都有可见状态。
- 解析失败不会静默影响生成质量。

### P1：chunk 质量和引用定位

目标：

- 设计 chunk 粒度、顺序、页码、字符位置和摘要字段。
- 保证引用来源能回到资料中的真实位置。

验收：

- Agent 回答和生成结果能展示来源资料。
- 引用不只停留在文件名层面。

### P2：上下文筛选

目标：

- 支持按课程、资料范围、文件夹、任务上下文筛选 chunk。
- 控制上下文长度和重复 chunk。

验收：

- 同一生成器可以消费不同资料范围。
- 上下文层不调用模型、不保存生成内容。

### P3：生成输出校验

目标：

- 为每类 `content_type` 建立结构化 schema。
- 校验模型输出字段、题目数量、选项、答案、节点边和引用。

验收：

- 输出结构不符合契约时保存失败状态。
- 前端不需要猜测模型输出形状。

### P4：质量反馈和重试

目标：

- 记录生成失败、引用不足、无资料、输出结构错误等原因。
- 支持用户重试或调整资料范围。

验收：

- 失败可解释、可重试、可追踪。
- 后续可以基于失败原因优化 prompt、parser 或 chunk 策略。

## 相关文档

- [../architecture/module-boundaries.md](../architecture/module-boundaries.md)
- [../architecture/runtime-flows.md](../architecture/runtime-flows.md)
- [../api-data/table-schema.md](../api-data/table-schema.md)
- [../engineering/development-conventions.md](../engineering/development-conventions.md)
