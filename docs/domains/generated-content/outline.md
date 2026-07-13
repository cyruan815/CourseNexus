# Outline Generation

Outline uses one structured model call over the complete selected material context. The prompt communicates organization, review goal, detail level, and requested section count. The model array order is preserved.

The backend limits sections, applies the detail-level summary length, validates unique nonblank titles, and adds numbered titles, `sec_001...`, and continuous `sort_order`. Sections contain no source order key or citation fields.
# 2026-07-13 质量与渲染更新

- Prompt 要求各章节承担不同复习目的，避免重复摘要，并明确禁止日历、任务和学习计划语义。
- `OutlineResult.tsx` 使用紧凑章节导航聚焦单节内容，展示摘要和复习建议；阅读状态不持久化。
