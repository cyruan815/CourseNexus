# Mindmap Frontend Handoff

## Responsibility Split

The backend generates and validates the graph, serializes Markdown, and preprocesses Markdown with `markmap-lib`. The frontend renders the preprocessed tree with `markmap-view`.

## API

Generate with `POST /api/v1/courses/{course_id}/generations` and `content_type="mindmap"`. Reopen the same persisted result through course generation history or `GET /api/v1/generated-contents/{id}`.

## Stored Contract

```json
{
  "schema_version": "1.0",
  "renderer": "markmap",
  "root_node_id": "node_001",
  "nodes": [
    {"id": "node_001", "label": "Operating Systems", "summary": "Root", "level": 1}
  ],
  "edges": [],
  "markmap_markdown": "- Operating Systems",
  "markmap_data": {
    "root": {"content": "Operating Systems", "children": []},
    "features": {},
    "assets": {"styles": [], "scripts": []}
  }
}
```

`nodes` and `edges` are the business graph. `markmap_markdown` is the deterministic textual projection. `markmap_data` is the exact `markmap-lib` preprocessing result used for rendering.

## Rendering

1. Load any entries in `markmap_data.assets.styles` and `scripts` using Markmap-compatible asset loaders.
2. Create the SVG container.
3. Pass `markmap_data.root` to `Markmap.create` from `markmap-view`.
4. Use the view API for fit, expand, collapse, and updates.

The frontend must not call `Transformer.transform` again and must not infer citations. Generated-content API responses keep `source_citations: []`.
