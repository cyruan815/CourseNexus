# Knowledge List Generation

Knowledge List uses one structured model call over the complete selected material context. The backend preserves model order, filters items below `minimum_importance`, limits the array to `item_count`, validates unique nonblank names, and adds `kp_001...` plus continuous `sort_order`.

Knowledge items contain name, definition, importance, related section, ID, and sort order only. They contain no source or citation fields.
# 2026-07-13 质量与渲染更新

- Prompt 优先提取概念、原理、公式适用条件和易混点，避免把普通标题或元信息当作知识点。
- `KnowledgeListResult.tsx` 按稳定顺序展示，并提供本地搜索和重要程度筛选；不推断掌握度或引用。
