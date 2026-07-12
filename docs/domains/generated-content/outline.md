# Outline 生成模块

G05 将全部选定材料映射为带真实引用的复习章节，不创建学习计划或任务。参数支持 `source_order|topic|review_path`、1..30 节、复习目标和 `concise|standard|detailed`；summary 上限分别为 300、800、2000 字符。

每个材料批次调用一次结构化模型。reduce 按标题空白归一和 casefold 去重，过滤伪造引用，按组织策略排序并生成 `sec_001...`、连续 `sort_order` 和编号标题。结果保存于 `content_json.sections`，逐节引用关联顶层 `source_citations`。算法复杂度 `O(C log C)`，模型调用数等于批次数；空结果为 `GENERATION_SCHEMA_INVALID`，不保存部分内容。

代码位于 `backend/app/modules/generation/generators/outline/`，测试位于 `backend/tests/modules/generation/generators/outline/`。
