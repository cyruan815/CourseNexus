# Flashcard Generation

Flashcard uses one structured model call over the complete selected material context. `card_style`, `include_formulas`, and `focus` are generation preferences communicated in the prompt rather than cross-batch filtering rules.

The backend limits the returned array to `card_count`, validates and trims front/back text and tags, rejects duplicate fronts, and adds `card_001...`, `mastery_status="unknown"`, and continuous `sort_order`. Cards contain no source or citation fields.
