# Flashcard Generation

Flashcard uses one structured model call over the complete selected material context. `card_style`, `include_formulas`, and `focus` are generation preferences communicated in the prompt rather than cross-batch filtering rules.

The backend limits the returned array to `card_count`, validates and trims front/back text and tags, rejects duplicate fronts, and adds `card_001...`, `mastery_status="unknown"`, and continuous `sort_order`. Cards contain no source or citation fields.
# 2026-07-13 质量与渲染更新

- `FlashcardDraft.explanation` 是可选兼容字段，用于易混点或补充语境。
- Prompt 要求每张卡只测试一个原子知识点，避免提纲段落和重复正面。
- `FlashcardResult.tsx` 提供单卡翻转、导航、打乱、掌握/未掌握和错卡重练；所有状态仅在页面内存。
