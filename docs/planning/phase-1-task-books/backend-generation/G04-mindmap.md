# G04 Mindmap - Simplified POC

Use one complete-context structured call returning one complete graph. Strictly validate the graph and requested limits, remap stable IDs, serialize child edges to Markdown, then run official `markmap-lib` preprocessing in the backend.

Persist `nodes`, `edges`, `markmap_markdown`, and `markmap_data.root/features/assets`. The frontend uses `markmap-view`; nodes contain no citations.
