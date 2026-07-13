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
