# Knowledge List 生成模块

G06 从全部选定材料生成去重、按重要性排序且逐项可追溯的知识点清单。参数支持 1..200 项、`balanced|definitions|formulas|pitfalls` 提取偏好、最低重要性和可选 focus。

每个材料批次调用一次结构化模型。reduce 按名称空白归一和 casefold 合并，定义保留互补信息但不超过 1200 字符，importance 取最高值，引用取真实 chunk 并集。过滤后按 high/medium/low、focus、材料支持和首次出现顺序排序，生成 `kp_001...` 和连续 `sort_order`。

结果保存于 `content_json.items`，不包含掌握度、考试频率或计划字段。算法复杂度 `O(C log C)`，模型调用数等于批次数；最低重要性过滤后为空时返回稳定 `GENERATION_SCHEMA_INVALID`，不保存部分数据。

代码和测试分别位于 `backend/app/modules/generation/generators/knowledge_list/` 与 `backend/tests/modules/generation/generators/knowledge_list/`。
