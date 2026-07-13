# Knowledge List Generation

Knowledge List uses one structured model call over the complete selected material context. The backend preserves model order, filters items below `minimum_importance`, limits the array to `item_count`, validates unique nonblank names, and adds `kp_001...` plus continuous `sort_order`.

Knowledge items contain name, definition, importance, related section, ID, and sort order only. They contain no source or citation fields.
