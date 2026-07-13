# Mindmap Generation

Mindmap uses one structured model call over the complete selected material context. The model returns one complete graph with a root ID, nodes, and child/related edges.

The backend rejects duplicate or missing node IDs, invalid endpoints, multiple roots or parents, cycles, unreachable nodes, discontinuous levels, and graphs beyond `max_nodes` or `max_depth`. It remaps model IDs to stable `node_001...` IDs and deterministically serializes child edges to `markmap_markdown`.

The backend then uses official `markmap-lib@0.18.12`:

```ts
const transformer = new Transformer();
const { root, features } = transformer.transform(markdown);
const assets = transformer.getUsedAssets(features);
```

The result is persisted as `content_json.markmap_data = { root, features, assets }`. The frontend uses `markmap-view` with `markmap_data.root` and the returned assets; it does not run `markmap-lib` again. Nodes contain no citation fields.

The frontend now declares `markmap-view@0.18.12` directly. `MindmapResult.tsx` creates the view, awaits `setData(markmap_data.root)`, then fits the completed render. It exposes fit/zoom/expand/collapse controls and falls back to persisted business nodes if SVG initialization fails. It never transforms `markmap_markdown` in the browser.

The initial view applies `fold: 1` to a cloned root tree, so only the center title is visible when the artifact opens. The persisted backend tree is not mutated; users can expand the root interactively or use the full-expand control, and full-collapse returns to the single-title view.

The generator treats child edges as the authoritative hierarchy. It derives every final node `level` by breadth-first traversal from `root_node_id` instead of trusting the model-provided draft level, while still rejecting multiple parents, cycles, unreachable nodes, and derived depth beyond `max_depth`. This removes intermittent `Mindmap levels must be continuous` failures caused by otherwise valid model graphs with inconsistent level annotations.
