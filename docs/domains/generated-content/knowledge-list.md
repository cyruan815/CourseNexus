# Knowledge List Generation

Knowledge List uses one structured model call over the complete selected material context. The backend preserves model order, filters items below `minimum_importance`, limits the array to `item_count`, validates unique nonblank names, and adds `kp_001...` plus continuous `sort_order`.

Knowledge items contain name, definition, importance, related section, ID, sort order, and the user-controlled `learned` boolean. They contain no source or citation fields. The model draft does not generate `learned`; the generator adds `learned = false` when constructing final items.
# 2026-07-13 质量与渲染更新

- Prompt 优先提取概念、原理、公式适用条件和易混点，避免把普通标题或元信息当作知识点。
- `KnowledgeListResult.tsx` 按稳定顺序展示，并提供本地搜索和重要程度筛选；不推断掌握度或引用。

# 2026-07-15 学习进度

- 每个 `content_json.items[*]` 使用 `learned: boolean` 保存当前所有者的学习状态；新生成条目默认为 `false`，历史条目缺失该字段时也按 `false` 处理，不需要数据库迁移。
- `PATCH /api/v1/generated-contents/{generated_content_id}/knowledge-items/{knowledge_item_id}/learning-state` 只接收 `{"learned": true|false}`。服务层检查所有权、内容类型、生成状态、JSON 结构和知识点 ID 后，更新目标条目并写回完整 `content_json`。
- 前端以完整清单计算 `已学习数量 / 总数` 和百分比，搜索、重要程度筛选不会改变总进度。
- 重要程度筛选右侧提供“未学习”按钮；激活后只显示 `learned != true` 的条目，并与搜索和重要程度条件按“并且”组合。该筛选同样不改变整体进度。
- 点击知识点完成按钮后先即时更新绿色状态；接口失败时回滚并显示错误。同一份清单一次只提交一个状态修改，降低并发写回完整 JSON 时相互覆盖的风险。
- 本实现适用于当前生成内容只属于一个用户的模型，不提供多人共享进度、掌握等级或学习历史。
