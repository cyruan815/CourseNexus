# Outline Generation

Outline uses one structured model call over the complete selected material context. The prompt communicates organization, review goal, detail level, and requested section count. The model array order is preserved.

The backend limits sections, applies the detail-level summary length, validates unique nonblank titles, and adds numbered titles, `sec_001...`, and continuous `sort_order`. Sections contain no source order key or citation fields.
