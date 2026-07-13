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

`nodes` and `edges` are the business graph. `markmap_markdown` is the deterministic textual projection. `markmap_data.root` and `features` come from `markmap-lib`; `assets` is the JSON-safe projection containing style entries and external script entries. Function-valued `iife` loader hooks are intentionally not persisted because JSON cannot preserve executable functions.

## Rendering

1. Sanitize and load the serializable entries in `markmap_data.assets.styles` and `scripts` using the `markmap-view` asset loaders. The frontend accepts inline styles and HTTPS stylesheets/scripts, and ignores malformed or legacy `iife` entries.
2. Create the SVG container.
3. Create the `markmap-view` instance, then pass `markmap_data.root` directly to `instance.setData()` and fit after rendering completes.
4. Use the view API for fit, expand, collapse, and updates.

The frontend declares `markmap-view@0.18.12` as a direct dependency. Asset loading completes before the view is created. If asset loading or initialization fails, it renders the persisted `nodes` and `edges` as a read-only fallback. It must not import `markmap-lib` or call `Transformer.transform()`.

The frontend must not call `Transformer.transform` again and must not infer citations. Generated-content API responses keep `source_citations: []`.
